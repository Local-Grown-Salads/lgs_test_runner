from sheet_runner.executor import generate_dashboard, generate_html_report

fake_results = {
    "passed": 1,
    "failed": 1,
    "total": 2,
    "worksheet_name": "Agronomist_SDK",
    "details": [
        {
            "test_name": "test_1",
            "function": "func",
            "expected": "1",
            "actual": "1",
            "passed": True,
            "message": "PASS",
        },
        {
            "test_name": "test_2",
            "function": "func",
            "expected": "2",
            "actual": "3",
            "passed": False,
            "message": "expected 2, got 3",
        },
    ],
}

# 1. Generate a test report
report_file = generate_html_report(fake_results)
print(f"✅ Report saved to: {report_file}")

# 2. Generate the dashboard
dashboard_file = generate_dashboard()
print(f"✅ Dashboard generated at: {dashboard_file}")
