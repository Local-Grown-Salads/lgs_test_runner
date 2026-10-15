# Sheet Test Runner

Run tests defined in a Google Sheet and update results directly in the spreadsheet. Green cells for pass, red for fail.

## Spreadsheet Format

Your Google Sheet needs these columns:

| test_name | service | input | expected | status |
|-----------|---------|-------|----------|--------|
| add_basic | add | 1, 2 | 3 | |
| concat_test | concat | "hello", " world" | hello world | |

- **test_name**: descriptive name
- **service**: function to call (see `services.py`)
- **input**: comma-separated arguments
- **expected**: expected return value
- **status**: updated automatically with PASS/FAIL

## Local Development

### Setup

```bash
# Install dependencies
uv sync

# Set up Google OAuth credentials (one-time)
# 1. Go to Google Cloud Console
# 2. Create OAuth 2.0 credentials (Desktop app)
# 3. Download JSON as client_secrets.json

# Create .env
cp .env.example .env
# Edit with your spreadsheet ID
```

### Run Tests

```bash
uv run python runner.py
```

First run opens browser for Google auth. Token is saved for future runs.

### Run Server (for Sheets integration)

```bash
uv run python server.py
```

Then add `apps_script.js` to your sheet (Extensions → Apps Script) to get a "Run Tests" button.

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

## Server Deployment

### GitHub Secrets

Add these in repo Settings → Secrets → Actions:

| Secret | Description |
|--------|-------------|
| `SSH_PRIVATE_KEY` | Private key for server access |
| `SSH_HOST` | Server IP or hostname |
| `SSH_USER` | SSH username |
| `WORK_DIR` | Deployment path (e.g., `/home/user/sheet_script`) |

### Server Setup

```bash
# 1. Create .env with service account credentials
cat > /path/to/sheet_script/.env << 'EOF'
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
SPREADSHEET_ID=your_spreadsheet_id
WORKSHEET_NAME=TestCases
EOF

# 2. Install systemd service
sudo cp sheet-test-runner.service /etc/systemd/system/
sudo nano /etc/systemd/system/sheet-test-runner.service  # update paths/user
sudo systemctl daemon-reload
sudo systemctl enable sheet-test-runner
sudo systemctl start sheet-test-runner

# 3. Check status
sudo systemctl status sheet-test-runner
```

### Service Account Setup

For server deployment (no browser), use a service account:

1. Google Cloud Console → IAM → Service Accounts → Create
2. Download JSON key
3. Share your spreadsheet with the service account email
4. Add JSON to `.env` as `GOOGLE_SERVICE_ACCOUNT_JSON`
