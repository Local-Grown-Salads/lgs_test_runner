"""
FastAPI application for running tests from Google Sheets.

Run with: uv run uvicorn sheet_runner:app --reload --port 8000
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import gspread
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# FIXED: Imported both process_worksheet and generate_html_report here
from sheet_runner.executor import process_worksheet, generate_html_report
from sheet_runner.sheets import extract_spreadsheet_id, get_sheets_client

load_dotenv()

app = FastAPI(title="Sheet Test Runner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# TODO: Move to models.py if we add more endpoints
class RunRequest(BaseModel):
    spreadsheet_id: str | None = None
    worksheet_name: str | None = None


class BatchRequest(BaseModel):
    spreadsheet_id: str | None = None


class RunResult(BaseModel):
    passed: int
    failed: int
    total: int
    worksheet_name: str | None = None
    details: list[dict[str, Any]]


class BatchResult(BaseModel):
    worksheets: list[RunResult]
    total_passed: int
    total_failed: int
    total_tests: int


@app.post("/run", response_model=RunResult)
async def run_tests(request: RunRequest):
    """Run all tests from a single worksheet."""
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
    result = process_worksheet(worksheet)
    
    # Generate the report
    report_file = generate_html_report(result)
    print(f"Report generated: {report_file}")
    
    return RunResult(**result)


@app.post("/batch", response_model=BatchResult)
async def batch_run_tests(request: BatchRequest):
    """Run tests from all worksheets in parallel."""
    spreadsheet_id = request.spreadsheet_id or os.getenv("SPREADSHEET_ID")

    if not spreadsheet_id:
        raise HTTPException(400, "No spreadsheet_id provided")

    spreadsheet_id = extract_spreadsheet_id(spreadsheet_id)
    client = get_sheets_client()

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except gspread.SpreadsheetNotFound:
        raise HTTPException(404, f"Spreadsheet not found: {spreadsheet_id}")

    worksheets = spreadsheet.worksheets()

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        results = await asyncio.gather(
            *[loop.run_in_executor(executor, process_worksheet, ws) for ws in worksheets]
        )

    # Generate the report for each worksheet
    for r in results:
        report_file = generate_html_report(r)
        print(f"Report generated: {report_file}")

    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_tests = sum(r["total"] for r in results)

    return BatchResult(
        worksheets=[RunResult(**r) for r in results],
        total_passed=total_passed,
        total_failed=total_failed,
        total_tests=total_tests,
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)