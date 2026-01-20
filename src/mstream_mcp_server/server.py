from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .api.client import APIError, AsyncMStreamClient
from .api.models import (
    Job,
    Service,
)
from .config import ServerConfig


class TransportAdapter:
    """Base transport adapter used to host the MCP application."""

    async def serve(self, mcp_server: FastMCP) -> None:  # pragma: no cover - interface
        raise NotImplementedError


def setup_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    return logging.getLogger("mstream_mcp_server")


def create_mcp_server(config: ServerConfig, *, logger: logging.Logger | None = None) -> FastMCP:
    """Build the MCP server with tools mapped to the mstream API client."""

    app_logger = logger or logging.getLogger("mstream_mcp_server")
    client = _build_client(config)

    mcp_server = FastMCP(config.server_name)
    # Expose the underlying client for lifecycle management and testing.
    mcp_server._mstream_client = client  # type: ignore[attr-defined]

    @mcp_server.tool()
    async def list_jobs() -> dict[str, Any]:
        jobs = await client.list_jobs()
        return _success_response({"jobs": [_job_to_dict(job) for job in jobs]})

    @mcp_server.tool()
    async def list_services() -> dict[str, Any]:
        try:
            services = await client.list_services()
            return _success_response({"services": [_service_to_dict(service) for service in services]})
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("list_services failed: %s", exc)
            return _error_response(str(exc), status_code=exc.status_code, details=exc.details)

    @mcp_server.tool()
    async def get_service(service_id: str) -> dict[str, Any]:
        if not _is_non_empty_string(service_id):
            return _error_response("service_id is required.")
        try:
            service = await client.get_service(service_id)
            return _success_response({"service": _service_to_dict(service)})
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("get_service failed: %s", exc)
            return _error_response(str(exc), status_code=exc.status_code, details=exc.details)

    _register_lifecycle_handlers(mcp_server, client, app_logger, config.server_name)
    return mcp_server


def _register_lifecycle_handlers(
    server: FastMCP,
    client: AsyncMStreamClient,
    logger: logging.Logger,
    server_name: str,
) -> None:
    # Get the streamable HTTP app to set state and register lifecycle handlers
    app = server.streamable_http_app()
    app.state.mstream_client = client
    # Surface the app so callers can re-use it without re-instantiation (primarily for tests).
    server._streamable_http_app = app  # type: ignore[attr-defined]
    name = server_name or getattr(server, "name", "mstream-mcp-server")

    @app.on_event("startup")
    async def _on_startup() -> None:
        logger.info("Starting %s with API base %s", name, client.base_url)

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        logger.info("Shutting down %s", name)
        await client.aclose()


def _build_client(config: ServerConfig) -> AsyncMStreamClient:
    return AsyncMStreamClient(
        base_url=config.api_base_url,
        port=config.api_port,
        auth_token=config.api_auth_token,
        timeout=config.api_timeout,
        max_retries=config.api_max_retries,
        backoff_factor=config.api_backoff_factor,
        transport=config.transport,
    )


def _job_to_dict(job: Job) -> dict[str, Any]:
    return job.to_dict()


def _service_to_dict(service: Service) -> dict[str, Any]:
    return service.to_dict()


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _success_response(data: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return payload


def _error_response(message: str, *, status_code: int | None = None, details: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": False, "error": message}
    if status_code is not None:
        payload["status_code"] = status_code
    if details:
        payload["details"] = details
    return payload


__all__ = ["TransportAdapter", "create_mcp_server", "setup_logging"]
