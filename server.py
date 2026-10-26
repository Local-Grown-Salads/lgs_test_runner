#!/usr/bin/env python3
"""
Webhook server for running tests from Google Sheets.

Run with: uv run uvicorn server:app --reload --port 8000
"""

import json
import os
import re
from typing import Any

import gspread
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.transport.requests import Request
from pydantic import BaseModel

from services import get_service

load_dotenv()

app = FastAPI(title="Sheet Test Runner")

# Allow requests from Google Apps Script
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Colors for status cells
GREEN = {"red": 0.7, "green": 0.9, "blue": 0.7}
RED = {"red": 0.95, "green": 0.7, "blue": 0.7}

TOKEN_FILE = "token.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class RunRequest(BaseModel):
    spreadsheet_id: str | None = None
    worksheet_name: str | None = None


class RunResult(BaseModel):
    passed: int
    failed: int
    total: int
    details: list[dict[str, Any]]


def get_sheets_client() -> gspread.Client:
    """Get authenticated gspread client.

    Supports:
    - GOOGLE_SERVICE_ACCOUNT_JSON env var (for Docker/server)
    - token.json file (for local OAuth)
    """
    # Option 1: Service account JSON from env (for server/Docker)
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        creds_dict = json.loads(sa_json)
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)

    # Option 2: Local OAuth token file
    if os.path.exists(TOKEN_FILE):
        creds = OAuthCredentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return gspread.authorize(creds)

    raise HTTPException(
        500,
        "No credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON env var or run 'uv run python runner.py' locally first.",
    )


def extract_spreadsheet_id(value: str) -> str:
    """Extract spreadsheet ID from URL or return as-is."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    return match.group(1) if match else value.strip()


def parse_input(input_str: str) -> list[Any]:
    """Parse input string into arguments."""
    if not input_str or not input_str.strip():
        return []

    args = []
    pattern = r"""(?:"[^"]*"|'[^']*'|[^,]+)"""
    parts = re.findall(pattern, input_str)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if (part.startswith('"') and part.endswith('"')) or (
            part.startswith("'") and part.endswith("'")
        ):
            args.append(part[1:-1])
        else:
            try:
                args.append(int(part) if "." not in part else float(part))
            except ValueError:
                args.append(part)
    return args


def normalize_value(value: Any) -> Any:
    """Normalize value for comparison."""
    if isinstance(value, str):
        value = value.strip()
        try:
            return int(value) if "." not in value else float(value)
        except ValueError:
            return value
    return value


def run_test(service_name: str, input_str: str, expected_str: str) -> tuple[bool, str, Any]:
    """Run a single test. Returns (passed, message, actual_result)."""
    try:
        service_fn = get_service(service_name)
        args = parse_input(input_str)
        result = service_fn(*args)
        expected = normalize_value(expected_str)
        result_normalized = normalize_value(str(result))

        if result_normalized == expected:
            return True, "PASS", result
        else:
            return False, f"expected {expected}, got {result}", result
    except Exception as e:
        return False, f"ERROR: {e}", None


@app.post("/run", response_model=RunResult)
async def run_tests(request: RunRequest):
    """Run all tests from the spreadsheet."""
    spreadsheet_id = request.spreadsheet_id or os.getenv("SPREADSHEET_ID")
    worksheet_name = request.worksheet_name or os.getenv("WORKSHEET_NAME")

    if not spreadsheet_id:
        raise HTTPException(400, "No spreadsheet_id provided")

    spreadsheet_id = extract_spreadsheet_id(spreadsheet_id)
    client = get_sheets_client()

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except gspread.SpreadsheetNotFound:
        raise HTTPException(404, f"Spreadsheet not found: {spreadsheet_id}")

    worksheet = spreadsheet.worksheet(worksheet_name) if worksheet_name else spreadsheet.sheet1
    records = worksheet.get_all_records()

    if not records:
        return RunResult(passed=0, failed=0, total=0, details=[])

    headers = list(records[0].keys())
    status_col = headers.index("status") + 1

    passed = 0
    failed = 0
    details = []

    for i, record in enumerate(records):
        row = i + 2
        test_name = record["test_name"]
        service = record["service"]
        input_val = str(record["input"])
        expected = str(record["expected"])

        success, message, actual = run_test(service, input_val, expected)

        # Update sheet
        worksheet.update_cell(row, status_col, "PASS" if success else "FAIL")
        worksheet.format(
            f"{gspread.utils.rowcol_to_a1(row, status_col)}",
            {"backgroundColor": GREEN if success else RED},
        )

        if success:
            passed += 1
        else:
            failed += 1

        details.append(
            {
                "test_name": test_name,
                "service": service,
                "input": input_val,
                "expected": expected,
                "actual": actual,
                "passed": success,
                "message": message,
            }
        )

    return RunResult(passed=passed, failed=failed, total=len(records), details=details)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
