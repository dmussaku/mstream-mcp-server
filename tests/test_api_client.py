from __future__ import annotations

from typing import Any

import httpx
import pytest

from mstream_mcp_server.api.client import APIError, AsyncMStreamClient
from mstream_mcp_server.api.models import (
    BatchConfig,
    JobCreateRequest,
    SchemaDefinition,
    SchemaField,
)


def _sample_schema() -> SchemaDefinition:
    return SchemaDefinition(
        name="input",
        fields=[SchemaField(name="prompt", type="string", required=True)],
    )


def _make_client(handler: httpx.MockTransport | None = None, **kwargs: Any) -> AsyncMStreamClient:
    transport = handler if isinstance(handler, httpx.MockTransport) else None
    return AsyncMStreamClient(base_url="http://example.com", transport=transport, **kwargs)


@pytest.mark.anyio
async def test_list_jobs_success() -> None:
    jobs_payload = [
        {"id": "job-1", "status": "running", "name": "demo", "extra": "ok"},
        {"id": "job-2", "status": "queued", "name": None},
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs"
        return httpx.Response(200, json={"jobs": jobs_payload})

    async with _make_client(httpx.MockTransport(handler)) as client:
        jobs = await client.list_jobs()

    assert [job.id for job in jobs] == ["job-1", "job-2"]
    assert jobs[0].metadata["extra"] == "ok"


@pytest.mark.anyio
async def test_retries_for_idempotent_methods() -> None:
    attempts = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(500, json={"message": "temporary"})
        return httpx.Response(200, json={"jobs": []})

    async with _make_client(httpx.MockTransport(handler), max_retries=1, backoff_factor=0) as client:
        jobs = await client.list_jobs()

    assert jobs == []
    assert attempts["count"] == 2


@pytest.mark.anyio
async def test_non_idempotent_requests_do_not_retry() -> None:
    attempts = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(500, json={"message": "fail"})

    request = JobCreateRequest(name="job", input_schema=_sample_schema())

    with pytest.raises(APIError) as excinfo:
        async with _make_client(httpx.MockTransport(handler), max_retries=3, backoff_factor=0) as client:
            await client.create_job(request)

    assert excinfo.value.status_code == 500
    assert attempts["count"] == 1


@pytest.mark.anyio
async def test_api_error_details_are_preserved() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "invalid", "detail": "bad request"})

    async with _make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(APIError) as excinfo:
            await client.list_jobs()

    error = excinfo.value
    assert error.status_code == 400
    assert error.details["detail"] == "bad request"


def test_job_create_request_payload_contract() -> None:
    request = JobCreateRequest(
        name="demo",
        input_schema=_sample_schema(),
        output_schema=None,
        batch_config=BatchConfig(batch_size=10, max_concurrency=5),
        metadata={"priority": "high"},
    )
    assert request.to_dict() == {
        "name": "demo",
        "input_schema": {
            "name": "input",
            "fields": [
                {
                    "name": "prompt",
                    "type": "string",
                    "required": True,
                    "description": None,
                }
            ],
            "version": None,
            "description": None,
        },
        "batch_config": {
            "batch_size": 10,
            "max_concurrency": 5,
            "timeout_seconds": None,
        },
        "priority": "high",
    }
