"""Test execution logic."""

import datetime
from pathlib import Path
from typing import Any

import gspread
from jinja2 import Environment, FileSystemLoader

from sheet_runner.repo_manager import RepoManager
from sheet_runner.sheets import GREEN, RED, normalize_value, parse_input

# Global repo manager instance
repo_manager = RepoManager()


def run_test(
    worksheet_name: str, func_name: str, input_str: str, expected_str: str
) -> tuple[bool, str, Any]:
    """Run a single test. Returns (passed, message, actual_result)."""
    ctx = None
    try:
        ctx = repo_manager.get_function(worksheet_name, func_name)
        args = parse_input(input_str)
        result = ctx.func(*args)
        expected = normalize_value(expected_str)
        result_normalized = normalize_value(str(result))

        if result_normalized == expected:
            return True, "PASS", result
        else:
            return False, f"expected {expected}, got {result}", result
    except Exception as e:
        return False, f"ERROR: {e}", None
    finally:
        if ctx:
            ctx.teardown()


def process_worksheet(worksheet: gspread.Worksheet) -> dict[str, Any]:
    """Process all tests in a worksheet. Returns result dict."""
    records = worksheet.get_all_records()

    if not records:
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "worksheet_name": worksheet.title,
            "details": [],
        }

    headers = list(records[0].keys())
    status_col = headers.index("status") + 1

    passed = 0
    failed = 0
    details = []

    for i, record in enumerate(records):
        row = i + 2
        test_name = record["test_name"]
        function = record["function"]
        input_val = str(record["input"])
        expected = str(record["expected"])

        success, message, actual = run_test(worksheet.title, function, input_val, expected)

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
                "function": function,
                "input": input_val,
                "expected": expected,
                "actual": actual,
                "passed": success,
                "message": message,
            }
        )

    return {
        "passed": passed,
        "failed": failed,
        "total": len(records),
        "worksheet_name": worksheet.title,
        "details": details,
    }


def generate_html_report(results: dict) -> str:
    """Generates an HTML report from the results dictionary using a Jinja2 template."""
    filename = f"{results['worksheet_name']}_report.html"

    # Locate the templates directory relative to this file
    template_dir = Path(__file__).parent / "templates"

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")

    # Render the HTML
    html_content = template.render(
        results=results, date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # Write the file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filename
