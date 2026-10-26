#!/usr/bin/env python3
"""
Sheet Test Runner

Reads test cases from a Google Spreadsheet, runs them against services,
and updates the sheet with results (green = pass, red = fail).

Spreadsheet DSL Format:
-----------------------
| test_name | service | input      | expected | status |
|-----------|---------|------------|----------|--------|
| add_basic | add     | 1, 2       | 3        |        |
| add_neg   | add     | -1, 5      | 4        |        |
| concat    | concat  | "a", "b"   | ab       |        |

- test_name: descriptive name for the test
- service: function name from services.py (add, subtract, multiply, concat)
- input: comma-separated arguments (numbers or quoted strings)
- expected: expected return value
- status: left blank, will be updated with PASS/FAIL and colored green/red
"""

import json
import os
import re
import sys
from typing import Any

import gspread
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from services import get_service

# Google Sheets API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# Colors for status cells (RGB 0-1 scale)
GREEN = {"red": 0.7, "green": 0.9, "blue": 0.7}  # Light green for PASS
RED = {"red": 0.95, "green": 0.7, "blue": 0.7}  # Light red for FAIL

TOKEN_FILE = "token.json"


def get_sheets_client() -> gspread.Client:
    """Authenticate using OAuth 2.0 (opens browser on first run)."""
    load_dotenv()

    creds = None

    # Load saved token if it exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid creds, do OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_file = os.getenv("GOOGLE_OAUTH_FILE", "credentials.json")
            if not os.path.exists(creds_file):
                print(f"Error: OAuth credentials file not found: {creds_file}")
                print("\nTo set up (FREE, no billing required):")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create a project")
                print("3. Enable 'Google Sheets API'")
                print("4. Go to Credentials → Create Credentials → OAuth client ID")
                print("5. Choose 'Desktop app'")
                print("6. Download JSON → save as 'credentials.json' here")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return gspread.authorize(creds)


def parse_input(input_str: str) -> list[Any]:
    """
    Parse input string into a list of arguments.

    Examples:
        "1, 2" -> [1.0, 2.0]
        '"hello", "world"' -> ["hello", "world"]
        "3.14, 2" -> [3.14, 2.0]
    """
    if not input_str or not input_str.strip():
        return []

    args = []
    # Split by comma but respect quoted strings
    pattern = r"""(?:"[^"]*"|'[^']*'|[^,]+)"""
    parts = re.findall(pattern, input_str)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check if it's a quoted string
        if (part.startswith('"') and part.endswith('"')) or (
            part.startswith("'") and part.endswith("'")
        ):
            args.append(part[1:-1])
        else:
            # Try to parse as number
            try:
                if "." in part:
                    args.append(float(part))
                else:
                    args.append(int(part))
            except ValueError:
                # Keep as string if not a number
                args.append(part)

    return args


def normalize_value(value: Any) -> Any:
    """Normalize a value for comparison."""
    if isinstance(value, str):
        value = value.strip()
        # Try to parse as number for comparison
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value


def run_test(service_name: str, input_str: str, expected_str: str) -> tuple[bool, str]:
    """
    Run a single test case.

    Returns:
        (passed, message)
    """
    try:
        service_fn = get_service(service_name)
        args = parse_input(input_str)
        result = service_fn(*args)
        expected = normalize_value(expected_str)

        # Normalize result for comparison
        result_normalized = normalize_value(str(result))

        if result_normalized == expected:
            return True, f"PASS (got {result})"
        else:
            return False, f"FAIL (expected {expected}, got {result})"

    except Exception as e:
        return False, f"ERROR: {e}"


def update_cell_color(worksheet, row: int, col: int, color: dict):
    """Update a cell's background color."""
    worksheet.format(f"{gspread.utils.rowcol_to_a1(row, col)}", {"backgroundColor": color})


def extract_spreadsheet_id(value: str) -> str:
    """Extract spreadsheet ID from a URL or return as-is if already an ID."""
    # Match Google Sheets URL pattern
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    if match:
        return match.group(1)
    return value.strip()


def main():
    """Main entry point."""
    load_dotenv()

    spreadsheet_id_raw = os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id_raw:
        print("Error: SPREADSHEET_ID not set in .env")
        sys.exit(1)

    spreadsheet_id = extract_spreadsheet_id(spreadsheet_id_raw)

    worksheet_name = os.getenv("WORKSHEET_NAME")

    print("Connecting to Google Sheets...")
    client = get_sheets_client()

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except gspread.SpreadsheetNotFound:
        print(f"Error: Spreadsheet not found: {spreadsheet_id}")
        print("Make sure the spreadsheet is shared with your service account email")
        sys.exit(1)

    if worksheet_name:
        worksheet = spreadsheet.worksheet(worksheet_name)
    else:
        worksheet = spreadsheet.sheet1

    print(f"Reading from worksheet: {worksheet.title}")

    # Get all records (assumes first row is header)
    records = worksheet.get_all_records()

    if not records:
        print("No test cases found in spreadsheet")
        return

    # Find required columns
    headers = list(records[0].keys())
    required = ["test_name", "service", "input", "expected", "status"]
    missing = [h for h in required if h not in headers]
    if missing:
        print(f"Error: Missing required columns: {missing}")
        print(f"Found columns: {headers}")
        print(f"Expected columns: {required}")
        sys.exit(1)

    status_col = headers.index("status") + 1  # 1-indexed for gspread

    print(f"\nRunning {len(records)} test(s)...\n")

    passed = 0
    failed = 0

    for i, record in enumerate(records):
        row = i + 2  # +2 because row 1 is header, and gspread is 1-indexed
        test_name = record["test_name"]
        service = record["service"]
        input_val = str(record["input"])
        expected = str(record["expected"])

        print(f"  [{test_name}] {service}({input_val}) == {expected} ... ", end="")

        success, message = run_test(service, input_val, expected)

        # Update status cell
        worksheet.update_cell(row, status_col, "PASS" if success else "FAIL")
        update_cell_color(worksheet, row, status_col, GREEN if success else RED)

        if success:
            print("✓ PASS")
            passed += 1
        else:
            print(f"✗ {message}")
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
