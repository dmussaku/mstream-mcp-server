from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

from .api.client import APIError, AsyncMStreamClient
from .api.models import (
    BatchConfig,
    Job,
    JobCreateRequest,
    SchemaDefinition,
    Service,
    ServiceCreateRequest,
)


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


def create_mcp_server(
    config: ServerConfig, *, logger: logging.Logger | None = None
) -> FastMCP:
    """Build the MCP server with tools mapped to the mstream API client."""

    app_logger = logger or logging.getLogger("mstream_mcp_server")
    client = _build_client(config)

    mcp_server = FastMCP(config.server_name)

    @mcp_server.tool()
    async def list_jobs() -> dict[str, Any]:
        jobs = await client.list_jobs()
        return _success_response({"jobs": [_job_to_dict(job) for job in jobs]})

    @mcp_server.tool()
    async def create_job(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = _parse_job_create_request(payload)
        except ValueError as exc:
            return _error_response(str(exc))

        try:
            job = await client.create_job(request)
            return _success_response({"job": _job_to_dict(job)})
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("create_job failed: %s", exc)
            return _error_response(
                str(exc), status_code=exc.status_code, details=exc.details
            )

    @mcp_server.tool()
    async def stop_job(job_id: str) -> dict[str, Any]:
        if not _is_non_empty_string(job_id):
            return _error_response("job_id is required.")
        try:
            job = await client.stop_job(job_id)
            return _success_response({"job": _job_to_dict(job)})
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("stop_job failed: %s", exc)
            return _error_response(
                str(exc), status_code=exc.status_code, details=exc.details
            )

    @mcp_server.tool()
    async def restart_job(job_id: str) -> dict[str, Any]:
        if not _is_non_empty_string(job_id):
            return _error_response("job_id is required.")
        try:
            job = await client.restart_job(job_id)
            return _success_response({"job": _job_to_dict(job)})
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("restart_job failed: %s", exc)
            return _error_response(
                str(exc), status_code=exc.status_code, details=exc.details
            )

    @mcp_server.tool()
    async def list_services() -> dict[str, Any]:
        try:
            services = await client.list_services()
            return _success_response(
                {"services": [_service_to_dict(service) for service in services]}
            )
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("list_services failed: %s", exc)
            return _error_response(
                str(exc), status_code=exc.status_code, details=exc.details
            )

    @mcp_server.tool()
    async def get_service(service_id: str) -> dict[str, Any]:
        if not _is_non_empty_string(service_id):
            return _error_response("service_id is required.")
        try:
            service = await client.get_service(service_id)
            return _success_response({"service": _service_to_dict(service)})
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("get_service failed: %s", exc)
            return _error_response(
                str(exc), status_code=exc.status_code, details=exc.details
            )

    @mcp_server.tool()
    async def create_service(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = _parse_service_create_request(payload)
        except ValueError as exc:
            return _error_response(str(exc))

        try:
            service = await client.create_service(request)
            return _success_response({"service": _service_to_dict(service)})
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("create_service failed: %s", exc)
            return _error_response(
                str(exc), status_code=exc.status_code, details=exc.details
            )

    @mcp_server.tool()
    async def delete_service(service_id: str) -> dict[str, Any]:
        if not _is_non_empty_string(service_id):
            return _error_response("service_id is required.")
        try:
            await client.delete_service(service_id)
            return _success_response(
                {"service_id": service_id}, message="Service deleted."
            )
        except APIError as exc:  # pragma: no cover - runtime path
            app_logger.error("delete_service failed: %s", exc)
            return _error_response(
                str(exc), status_code=exc.status_code, details=exc.details
            )

    _register_lifecycle_handlers(mcp_server, client, app_logger, config.server_name)
    return mcp_server


def _register_lifecycle_handlers(
    server: FastMCP,
    client: AsyncMStreamClient,
    logger: logging.Logger,
    server_name: str,
) -> None:
    server.app.state.mstream_client = client
    name = server_name or getattr(server, "name", "mstream-mcp-server")

    @server.app.on_event("startup")
    async def _on_startup() -> None:
        logger.info("Starting %s with API base %s", name, client.base_url)

    @server.app.on_event("shutdown")
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
    )


def _parse_job_create_request(payload: dict[str, Any]) -> JobCreateRequest:
    if not isinstance(payload, dict):
        raise ValueError("create_job payload must be an object.")

    name = payload.get("name")
    if not _is_non_empty_string(name):
        raise ValueError("name is required for create_job.")

    input_schema = _parse_schema_definition(payload.get("input_schema"), "input_schema")
    output_schema = _parse_optional_schema(
        payload.get("output_schema"), "output_schema"
    )
    batch_config = _parse_optional_batch(payload.get("batch_config"), "batch_config")
    metadata = _parse_metadata(payload.get("metadata"))

    return JobCreateRequest(
        name=name,
        input_schema=input_schema,
        output_schema=output_schema,
        batch_config=batch_config,
        metadata=metadata,
    )


def _parse_service_create_request(payload: dict[str, Any]) -> ServiceCreateRequest:
    if not isinstance(payload, dict):
        raise ValueError("create_service payload must be an object.")

    name = payload.get("name")
    endpoint = payload.get("endpoint")
    if not _is_non_empty_string(name):
        raise ValueError("name is required for create_service.")
    if not _is_non_empty_string(endpoint):
        raise ValueError("endpoint is required for create_service.")

    schemas_payload = payload.get("schemas")
    schemas: list[SchemaDefinition] = []
    if schemas_payload is not None:
        if not isinstance(schemas_payload, list):
            raise ValueError("schemas must be a list of schema definitions.")
        schemas = [
            _parse_schema_definition(schema_payload, "schemas[]")
            for schema_payload in schemas_payload
        ]

    metadata = _parse_metadata(payload.get("metadata"))
    return ServiceCreateRequest(
        name=name, endpoint=endpoint, schemas=schemas, metadata=metadata
    )


def _parse_schema_definition(data: Any, field_name: str) -> SchemaDefinition:
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be an object.")
    schema = SchemaDefinition.from_dict(data)
    if not _is_non_empty_string(schema.name):
        raise ValueError(f"{field_name}.name is required.")
    if not schema.fields:
        raise ValueError(f"{field_name}.fields must contain at least one field.")
    return schema


def _parse_optional_schema(data: Any, field_name: str) -> SchemaDefinition | None:
    if data is None:
        return None
    return _parse_schema_definition(data, field_name)


def _parse_optional_batch(data: Any, field_name: str) -> BatchConfig | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be an object.")
    batch = BatchConfig.from_dict(data)
    if batch.batch_size <= 0:
        raise ValueError(f"{field_name}.batch_size must be greater than zero.")
    return batch


def _parse_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata must be an object when provided.")
    return value


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _job_to_dict(job: Job) -> dict[str, Any]:
    return job.to_dict()


def _service_to_dict(service: Service) -> dict[str, Any]:
    return service.to_dict()


def _success_response(
    data: dict[str, Any], message: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return payload


def _error_response(
    message: str, *, status_code: int | None = None, details: Any | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": False, "error": message}
    if status_code is not None:
        payload["status_code"] = status_code
    if details:
        payload["details"] = details
    return payload


__all__ = ["ServerConfig", "TransportAdapter", "create_mcp_server", "setup_logging"]
