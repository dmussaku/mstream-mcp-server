from __future__ import annotations

import asyncio
from collections.abc import Mapping, MutableMapping
from typing import Any

import httpx
from httpx import BaseTransport

from .models import (
    BatchConfig,
    ErrorResponse,
    Job,
    JobCreateRequest,
    SchemaDefinition,
    Service,
    ServiceCreateRequest,
)

IDEMPOTENT_METHODS = {"GET", "DELETE"}


class APIError(Exception):
    """Raised when the API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class AsyncMStreamClient:
    """Async HTTP client for interacting with the mstream MCP server."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost",
        port: int | None = None,
        auth_token: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        transport: BaseTransport | None = None,
    ) -> None:
        base = base_url.rstrip("/")
        self.base_url = f"{base}:{port}" if port is not None else base
        self.max_retries = max(0, max_retries)
        self.backoff_factor = max(0.0, backoff_factor)

        default_headers: MutableMapping[str, str] = {"Accept": "application/json"}
        if auth_token:
            default_headers["Authorization"] = f"Bearer {auth_token}"
        if headers:
            default_headers.update(headers)

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=default_headers,
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> AsyncMStreamClient:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_jobs(self) -> list[Job]:
        response = await self._request("GET", "/jobs")
        payload = response.json()
        job_items = self._extract_list(payload, "jobs")
        return [Job.from_dict(item) for item in job_items]

    async def create_job(self, job_request: JobCreateRequest) -> Job:
        response = await self._request("POST", "/jobs", json=job_request.to_dict())
        return Job.from_dict(response.json())

    async def stop_job(self, job_id: str) -> Job:
        response = await self._request("POST", f"/jobs/{job_id}/stop")
        return Job.from_dict(response.json())

    async def restart_job(self, job_id: str) -> Job:
        response = await self._request("POST", f"/jobs/{job_id}/restart")
        return Job.from_dict(response.json())

    async def list_services(self) -> list[Service]:
        response = await self._request("GET", "/services")
        payload = response.json()
        service_items = self._extract_list(payload, "services")
        return [Service.from_dict(item) for item in service_items]

    async def create_service(self, request: ServiceCreateRequest) -> Service:
        response = await self._request("POST", "/services", json=request.to_dict())
        return Service.from_dict(response.json())

    async def get_service(self, service_id: str) -> Service:
        response = await self._request("GET", f"/services/{service_id}")
        return Service.from_dict(response.json())

    async def delete_service(self, service_id: str) -> None:
        await self._request("DELETE", f"/services/{service_id}")

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        attempts = self.max_retries + 1 if method in IDEMPOTENT_METHODS else 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                response = await self._client.request(method, path, **kwargs)
                if response.is_success:
                    return response

                if method in IDEMPOTENT_METHODS and response.status_code >= 500 and attempt < attempts - 1:
                    await self._sleep(attempt)
                    continue

                raise self._build_api_error(response)
            except httpx.HTTPError as exc:  # Network/timeout errors
                last_error = exc
                if method not in IDEMPOTENT_METHODS or attempt >= attempts - 1:
                    raise APIError(str(exc)) from exc
                await self._sleep(attempt)

        raise APIError(str(last_error or "Request failed"))

    async def _sleep(self, attempt: int) -> None:
        delay = self.backoff_factor * (2**attempt)
        if delay:
            await asyncio.sleep(delay)

    @staticmethod
    def _build_api_error(response: httpx.Response) -> APIError:
        details: Any = None
        message = f"HTTP {response.status_code}"
        try:
            details = response.json()
            error = ErrorResponse.from_response(response.status_code, details)
            message = error.message or message
            return APIError(message, status_code=response.status_code, details=error.details)
        except Exception:
            # Fall back to plain text body when JSON parsing fails.
            text_body = response.text
            if text_body:
                message = f"{message}: {text_body}"
        return APIError(message, status_code=response.status_code, details=details)

    @property
    def client(self) -> httpx.AsyncClient:
        """Expose the underlying httpx.AsyncClient for advanced usage."""

        return self._client

    @staticmethod
    def _extract_list(payload: Any, key: str) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict) and isinstance(payload.get(key), list):
            return [item for item in payload[key] if isinstance(item, dict)]
        raise APIError(f"Unexpected response format while reading {key}.")

    @property
    def timeout(self) -> httpx.Timeout:
        return self._client.timeout

    @property
    def headers(self) -> Mapping[str, str]:
        return self._client.headers


__all__ = [
    "APIError",
    "AsyncMStreamClient",
    "BatchConfig",
    "ErrorResponse",
    "Job",
    "JobCreateRequest",
    "SchemaDefinition",
    "Service",
    "ServiceCreateRequest",
]
