from __future__ import annotations

import argparse
import asyncio
import logging
import os

import uvicorn
from mcp.server.fastmcp import FastMCP

from .server import ServerConfig, TransportAdapter, create_mcp_server, setup_logging


class HTTPTransportAdapter(TransportAdapter):
    """HTTP adapter for hosting the MCP server via uvicorn."""

    def __init__(
        self, host: str, port: int, *, logger: logging.Logger | None = None
    ) -> None:
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger(__name__)

    async def serve(self, mcp_server: FastMCP) -> None:
        config = uvicorn.Config(
            app=mcp_server.app,
            host=self.host,
            port=self.port,
            log_config=None,
            log_level=self.logger.level or logging.INFO,
        )
        server = uvicorn.Server(config)
        self.logger.info("Starting HTTP transport on %s:%s", self.host, self.port)
        await server.serve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the mstream MCP server over HTTP transport."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MSTREAM_SERVER_HOST", "0.0.0.0"),
        help=(
            "Host for the MCP HTTP server "
            "(default: %(default)s or MSTREAM_SERVER_HOST)."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MSTREAM_SERVER_PORT", "8000")),
        help=(
            "Port for the MCP HTTP server "
            "(default: %(default)s or MSTREAM_SERVER_PORT)."
        ),
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("MSTREAM_API_BASE_URL", "http://localhost"),
        help="Base URL for the upstream mstream API (default: %(default)s).",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=int(os.getenv("MSTREAM_API_PORT", "8700")),
        help="Port for the upstream mstream API (default: %(default)s).",
    )
    parser.add_argument(
        "--api-token",
        default=os.getenv("MSTREAM_API_TOKEN"),
        help="Bearer token to include for mstream API authentication.",
    )
    parser.add_argument(
        "--api-timeout",
        type=float,
        default=float(os.getenv("MSTREAM_API_TIMEOUT", "10.0")),
        help="Request timeout for mstream API calls in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--api-max-retries",
        type=int,
        default=int(os.getenv("MSTREAM_API_MAX_RETRIES", "3")),
        help="Maximum retries for idempotent API calls (default: %(default)s).",
    )
    parser.add_argument(
        "--api-backoff-factor",
        type=float,
        default=float(os.getenv("MSTREAM_API_BACKOFF_FACTOR", "0.5")),
        help="Backoff factor for API retry delays (default: %(default)s).",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("MSTREAM_LOG_LEVEL", "INFO"),
        help="Log level for the MCP server and transport (default: %(default)s).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logger = setup_logging(args.log_level)

    server_config = ServerConfig(
        api_base_url=args.api_base_url,
        api_port=args.api_port,
        api_auth_token=args.api_token,
        api_timeout=args.api_timeout,
        api_max_retries=args.api_max_retries,
        api_backoff_factor=args.api_backoff_factor,
    )

    mcp_server = create_mcp_server(server_config, logger=logger)
    adapter = HTTPTransportAdapter(args.host, args.port, logger=logger)
    asyncio.run(adapter.serve(mcp_server))


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["HTTPTransportAdapter", "main"]
