# Contributing

## Contribution Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

**Note:** Direct pushes to `main` are not allowed. All contributions must come through pull requests, which will be reviewed and merged by the maintainer.

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
uv run pytest
```

### Run Server Locally

```bash
uv run uvicorn sheet_runner:app --reload --port 8000
```

Then add `apps_script.js` to your sheet (Extensions → Apps Script) to get a "Run Tests" button.

## Docker (Local Testing)

### With Test Database

For testing services that require a database:

```bash
# Start Postgres and the test runner
docker compose up -d

# Check logs
docker compose logs -f test-runner

# Tear down
docker compose down -v
```

This spins up:
- PostgreSQL with test schema (`Agronomist SDK/init.sql`)
- Test runner connected to the database

### Standalone (No Database)

For testing without database dependencies:

```bash
docker build -t sheet-test-runner .
docker run -p 8000:8000 \
  -e GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}' \
  -e SPREADSHEET_ID=your_spreadsheet_id \
  sheet-test-runner
```

## Service Fixtures

Each service has its own folder matching the spreadsheet worksheet name:

```
Agronomist SDK/
├── fixtures.py   # Client setup and teardown
├── init.sql      # Database schema and seed data
└── README.md     # Fixture documentation
```

See `Agronomist SDK/README.md` for details on test data and fixture setup.

## Deployment

Deployment is fully automated via GitHub Actions. When a PR is merged to `main`, the CI/CD pipeline handles deployment automatically. Contributors do not need to configure or manage deployment.

### For Maintainers

The following secrets must be configured in the repository (Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `SSH_PRIVATE_KEY` | Private key for server access |
| `SSH_HOST` | Server IP or hostname |
| `SSH_USER` | SSH username |
| `WORK_DIR` | Deployment path (e.g., `/home/user/sheet_script`) |

### Service Account (Server)

The production server uses a service account for Google Sheets access:

1. Google Cloud Console → IAM → Service Accounts → Create
2. Download JSON key
3. Share the spreadsheet with the service account email
4. Set `GOOGLE_SERVICE_ACCOUNT_JSON` in the server environment
