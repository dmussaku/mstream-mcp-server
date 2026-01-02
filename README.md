# mstream-mcp-server

A Model Context Protocol (MCP) server that exposes streaming media functionality for clients. This repository provides the scaffolding for developing and running the server with modern Python tooling.

## Prerequisites

- Python 3.10 or later
- Recommended: a virtual environment (``python -m venv .venv``)

## Setup

1. Clone the repository and create/activate your virtual environment.
2. Install the package along with development dependencies:
   ```bash
   pip install -e .[dev]
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

The MCP server implementation should live under `src/mstream_mcp_server/`. Add your server entrypoint there, then execute it (for example) with:

```bash
python -m mstream_mcp_server
```

Adjust the module path and command based on your server implementation.
