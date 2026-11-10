"""Google Sheets client, parsing, and cell operations."""

import json
import os
import re
from typing import Any

import gspread
from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# Colors for status cells
GREEN = {"red": 0.7, "green": 0.9, "blue": 0.7}
RED = {"red": 0.95, "green": 0.7, "blue": 0.7}

TOKEN_FILE = "token.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_client() -> gspread.Client:
    """Get authenticated gspread client.

    Supports:
    - GOOGLE_SERVICE_ACCOUNT_FILE env var pointing to JSON file (for Docker/server)
    - token.json file (for local OAuth)
    """
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_file and os.path.exists(sa_file):
        creds = ServiceAccountCredentials.from_service_account_file(sa_file, scopes=SCOPES)
        return gspread.authorize(creds)

    if os.path.exists(TOKEN_FILE):
        creds = OAuthCredentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return gspread.authorize(creds)

    raise HTTPException(
        500,
        "No credentials found. Set GOOGLE_SERVICE_ACCOUNT_FILE or run OAuth flow locally.",
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
