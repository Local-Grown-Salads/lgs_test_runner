

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
    """Generates an HTML report and saves it to a history folder."""
    
    # Create a reports folder if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    sheet_name = results['worksheet_name']
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Format the sheet name cleanly (e.g., "Agronomist SDK Test" -> "Agronomist_SDK_Test")
    clean_name = sheet_name.replace(" ", "_").replace("-", "_")

    # Save a historical copy with "Report" in the name
    history_filename = reports_dir / f"{clean_name}_Report_{timestamp}.html"
    
    # Also save a "latest" copy
    latest_filename = reports_dir / f"{clean_name}_Latest_Report.html"

    # Locate the templates directory relative to this file
    template_dir = Path(__file__).parent / "templates"

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")

    # Render the HTML
    html_content = template.render(
        results=results, date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # Write the historical file
    with open(history_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # Write the latest file
    with open(latest_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(history_filename)


def generate_dashboard() -> str:
    """Scans the reports folder and generates an index.html dashboard."""
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return "No reports directory found."
        
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html")
    
    reports = []
    # Find all HTML files in the reports folder
    for file in reports_dir.glob("*.html"):
        # Skip the "_Latest_Report" files so we only show the history
        if "Latest_Report" in file.name:
            continue
            
        # Extract a readable name and date from the filename
        # Example: Agronomist_SDK_Report_2026-11-17_21-55-24.html
        parts = file.stem.rsplit("_", 2)
        if len(parts) >= 3:
            name = parts[0].replace("_", " ")
            date_str = f"{parts[1]} {parts[2].replace('-', ':')}"
        else:
            name = file.stem
            date_str = ""
            
        reports.append({
            "filename": file.name,
            "name": name,
            "date": date_str
        })
        
    # Sort reports by filename (which includes the date) in reverse order (newest first)
    reports.sort(key=lambda x: x["filename"], reverse=True)
    
    # Render the dashboard
    html_content = template.render(reports=reports)
    
    # Save it to the reports folder
    dashboard_file = reports_dir / "index.html"
    with open(dashboard_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return str(dashboard_file)