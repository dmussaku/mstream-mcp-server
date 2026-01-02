"""Configuration handling for the MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass

from httpx import AsyncBaseTransport


@dataclass
class ServerConfig:
    """Configuration for wiring the MCP layer to the mstream API."""

    api_base_url: str = "http://localhost"
    api_port: int | None = None
    api_auth_token: str | None = None
    api_timeout: float = 10.0
    api_max_retries: int = 3
    api_backoff_factor: float = 0.5
    server_name: str = "mstream-mcp-server"
    transport: AsyncBaseTransport | None = None

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Create configuration from environment variables."""
        return cls(
            api_base_url=os.getenv("MSTREAM_API_BASE_URL", "http://localhost"),
            api_port=int(os.getenv("MSTREAM_API_PORT", "8700")),
            api_auth_token=os.getenv("MSTREAM_API_TOKEN"),
            api_timeout=float(os.getenv("MSTREAM_API_TIMEOUT", "10.0")),
            api_max_retries=int(os.getenv("MSTREAM_API_MAX_RETRIES", "3")),
            api_backoff_factor=float(os.getenv("MSTREAM_API_BACKOFF_FACTOR", "0.5")),
        )


__all__ = ["ServerConfig"]
