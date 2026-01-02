"""STDIO transport adapter for the MCP server."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ..server import TransportAdapter


class STDIOTransportAdapter(TransportAdapter):
    """
    Placeholder for a future STDIO transport.

    The Model Context Protocol supports STDIO-based transports for local tools.
    This adapter reserves the interface so that it can be implemented without
    changing the server wiring.
    """

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    async def serve(self, mcp_server: FastMCP) -> None:  # pragma: no cover - stub
        self.logger.warning("STDIO transport is not implemented yet. Use HTTP transport instead.")
        raise NotImplementedError("STDIO transport adapter has not been implemented.")


__all__ = ["STDIOTransportAdapter"]
