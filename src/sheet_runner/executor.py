"""Test execution logic."""

from typing import Any

import gspread

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





import datetime

def generate_html_report(results: dict) -> str:
    """Generates an HTML report from the results dictionary."""
    filename = f"{results['worksheet_name']}_report.html"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LGS Test Report - {results['worksheet_name']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px; }}
            h1 {{ color: #333; }}
            .summary {{ background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            .pass {{ color: green; font-weight: bold; }}
            .fail {{ color: red; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #007bff; color: white; }}
            tr:hover {{ background-color: #f1f1f1; }}
        </style>
    </head>
    <body>
        <h1>LGS Test Report: {results['worksheet_name']}</h1>
        <div class="summary">
            <p><strong>Date:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Total Tests:</strong> {results['total']}</p>
            <p><strong>Passed:</strong> <span class="pass">{results['passed']}</span></p>
            <p><strong>Failed:</strong> <span class="fail">{results['failed']}</span></p>
        </div>
        
        <table>
            <tr>
                <th>Test Name</th>
                <th>Function</th>
                <th>Expected</th>
                <th>Actual</th>
                <th>Status</th>
            </tr>
    """
    
    for detail in results['details']:
        status = '<span class="pass">PASS</span>' if detail['passed'] else f'<span class="fail">FAIL: {detail["message"]}</span>'
        html += f"""
            <tr>
                <td>{detail['test_name']}</td>
                <td>{detail['function']}</td>
                <td>{detail['expected']}</td>
                <td>{detail['actual']}</td>
                <td>{status}</td>
            </tr>
        """
        
    html += """
        </table>
    </body>
    </html>
    """
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
        
    return filename