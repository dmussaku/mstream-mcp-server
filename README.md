# mstream-mcp-server

An MCP server for https://github.com/makarski/mstream

## Prerequisites

- Python 3.11 or later
- Recommended: a virtual environment (``python -m venv .venv``)

## Available Tools

This MCP server provides the following tools for managing mstream jobs and services:

### Job Management
- **`list_jobs`** - List all configured mstream jobs with their current status, metadata, and configuration
- **`create_job`** - Create a new mstream job with input/output schemas and batch configuration
- **`stop_job`** - Stop a running mstream job by job ID
- **`restart_job`** - Restart a stopped mstream job by job ID

### Service Management  
- **`list_services`** - List all registered mstream services
- **`get_service`** - Get details of a specific service by service ID
- **`create_service`** - Register a new service with mstream, including endpoint and schema definitions
- **`delete_service`** - Remove a service from mstream by service ID

### Usage Examples

```bash
# List all jobs
list_jobs()

# Create a new job with schema
create_job({
  "name": "data-processing-job",
  "input_schema": {
    "name": "input",
    "fields": [
      {"name": "data", "type": "string", "required": true}
    ]
  },
  "batch_config": {
    "batch_size": 100,
    "max_concurrency": 5
  }
})

# Stop a job
stop_job("job-123")

# Create a service
create_service({
  "name": "my-service",
  "endpoint": "http://localhost:8080/process",
  "schemas": [{
    "name": "request",
    "fields": [{"name": "input", "type": "string", "required": true}]
  }]
})
```

## Setup

1. Clone the repository and create/activate your virtual environment.
   ```bash
   python -m venv .venv
   ```
3. Install the package along with development dependencies:
   ```bash
   pip install -e .[dev]
   ```

   ```zsh
   pip install -e ".[dev]"
   ```

## Development

- Format and lint the codebase:
  ```bash
  ruff check .
  black .
  ```
- Type checking:
  ```bash
  mypy .
  ```
- Run tests:
  ```bash
  pytest
  ```

## Running the server

The HTTP transport entrypoint is accessible via `python -m mstream_mcp_server`. Example:

```bash
python -m mstream_mcp_server --host 0.0.0.0 --port 8000 --api-base-url http://localhost --api-port 8700
```

Configuration may also be provided via environment variables:

- `MSTREAM_SERVER_HOST` / `MSTREAM_SERVER_PORT`: bind address for the MCP HTTP server.
- `MSTREAM_API_BASE_URL` / `MSTREAM_API_PORT`: address of the upstream mstream API.
- `MSTREAM_API_TOKEN`: bearer token for API authentication.
- `MSTREAM_API_TIMEOUT`, `MSTREAM_API_MAX_RETRIES`, `MSTREAM_API_BACKOFF_FACTOR`: HTTP client tuning.
- `MSTREAM_LOG_LEVEL`: logging verbosity for the server and transport.

## VS Code Configuration

Add the following to your VS Code `settings.json` to connect to the mstream MCP server:

```json
{
  "mcp.servers": {
    "mstream": {
      "type": "http",
      "url": "http://localhost:<PORT>/mcp",
      "transport": {
        "type": "http"
      }
    }
  }
}
```
