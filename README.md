# Sheet Test Runner

Run tests defined in a Google Sheet and update results directly in the spreadsheet. Green cells for pass, red for fail.

## Workflow

```
┌─────────────────────┐
│   Google Sheet      │
│  (test definitions) │
└──────────┬──────────┘
           │
           │ pull test cases
           ▼
┌─────────────────────┐
│     runner.py       │
│  - parses input     │
│  - calls services   │
│  - compares output  │
└──────────┬──────────┘
           │
           │ update status column
           ▼
┌─────────────────────┐
│   Google Sheet      │
│  (PASS/FAIL + color)│
└─────────────────────┘
```

## Spreadsheet Format

Your Google Sheet needs these columns:

| test_name | service | input | expected | status |
|-----------|---------|-------|----------|--------|
| add_basic | add | 1, 2 | 3 | |
| concat_test | concat | "hello", " world" | hello world | |

### Column Definitions

- **test_name**: descriptive name for the test case
- **service**: function to call (must exist in `services.py`)
- **input**: comma-separated arguments (see format below)
- **expected**: expected return value
- **status**: leave blank — updated automatically with PASS/FAIL

### Input Cell Format

The `input` column accepts comma-separated arguments:

| Type | Format | Example |
|------|--------|---------|
| Integer | bare number | `1, 2, 3` |
| Float | number with decimal | `3.14, 2.0` |
| String | quoted | `"hello", "world"` |
| Mixed | combine types | `1, "foo", 3.5` |

**Examples:**

```
1, 2                    → [1, 2]           (integers)
"hello", " world"       → ["hello", " world"] (strings)
3.14, 2                 → [3.14, 2]        (float + int)
"prefix", 100, "suffix" → ["prefix", 100, "suffix"]
```

## Quick Start

```bash
# Install dependencies
uv sync

# Create .env with your spreadsheet ID
cp .env.example .env

# Run tests
uv run python runner.py
```

First run opens browser for Google auth. Token is saved for future runs.

## Adding Services

Edit `services.py` to add functions:

```python
def my_function(a: int, b: int) -> int:
    return a + b

SERVICES = {
    "my_function": my_function,
    # ...
}
```

## Running the Server

For Sheets integration via webhook:

```bash
uv run python server.py
```

Then add `apps_script.js` to your sheet (Extensions → Apps Script) to get a "Run Tests" button.

## Contributing

Contributions are welcome via pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup.

Deployment is handled automatically by GitHub Actions when PRs are merged.
