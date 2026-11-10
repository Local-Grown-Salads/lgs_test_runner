# Sheet Test Runner

Run tests defined in a Google Sheet and update results directly in the
spreadsheet. Green cells for pass, red for fail.

[Spreadsheet Link](https://docs.google.com/spreadsheets/d/1kZuKg0KHtIkCM1o7iJk0AMCoPPv2sKD-N5NHA21_LNE/edit?usp=sharing)

## How to use

Enter tests in the spreadsheet for your preferred service above, and then hit
the button that says "Test Runner".

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

| test_name   | function | input             | expected    | status |
| ----------- | -------- | ----------------- | ----------- | ------ |
| add_basic   | add      | 1, 2              | 3           |        |
| concat_test | concat   | "hello", " world" | hello world |        |

Each worksheet can contain tests for a different service. Use `/batch` to run
all worksheets in parallel.

### Column Definitions

- **test_name**: descriptive name for the test case
- **function**: function to call (must exist in `services.py`)
- **input**: comma-separated arguments (see format below)
- **expected**: expected return value
- **status**: leave blank — updated automatically with PASS/FAIL

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

## Running the Server

For Sheets integration via webhook:

```bash
uv run python server.py
```

Then add `apps_script.js` to your sheet (Extensions → Apps Script) to get a "Run
Tests" button.

### Endpoints

- `POST /run` — Run tests from a single worksheet
- `POST /batch` — Run tests from all worksheets in parallel (for nightly runs)
- `GET /health` — Health check

## Contributing

Contributions are welcome via pull requests. See
[CONTRIBUTING.md](CONTRIBUTING.md) for local development setup.

Deployment is handled automatically by GitHub Actions when PRs are merged.
