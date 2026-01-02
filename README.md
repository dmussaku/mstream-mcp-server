# mstream-mcp-server

An MCP server for https://github.com/makarski/mstream

## Prerequisites

- Python 3.11 or later
- Recommended: a virtual environment (``python -m venv .venv``)

## Setup

1. Clone the repository and create/activate your virtual environment.
2. Install the package along with development dependencies:
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
