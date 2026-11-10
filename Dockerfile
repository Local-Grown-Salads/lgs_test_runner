FROM python:3.12-slim

WORKDIR /app

# Install git for repo cloning
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY repos.json ./

# Install dependencies
RUN uv sync --no-dev

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "uvicorn", "sheet_runner:app", "--host", "0.0.0.0", "--port", "8000"]
