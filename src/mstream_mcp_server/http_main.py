"""Main entry point for the HTTP transport."""

from __future__ import annotations

import asyncio

from .config import ServerConfig
from .server import create_mcp_server, setup_logging
from .transports.http import HTTPTransportAdapter, _parse_args


def main() -> None:
    """Main entry point for the mstream MCP server over HTTP transport."""
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


__all__ = ["main"]
