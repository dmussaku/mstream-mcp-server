from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest

from mstream_mcp_server.config import ServerConfig
from mstream_mcp_server.server import create_mcp_server


def _mock_api_transport() -> tuple[httpx.MockTransport, dict[str, Any]]:
    state: dict[str, Any] = {
        "jobs": [
            {"id": "job-1", "status": "running", "name": "demo-job"},
            {"id": "job-2", "status": "queued", "name": "queued-job"},
        ],
        "services": [
            {
                "id": "svc-1",
                "name": "search",
                "endpoint": "http://svc/search",
                "schemas": [],
            }
        ],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        def respond(status_code: int, json_body: Any | None = None) -> httpx.Response:
            return httpx.Response(status_code=status_code, json=json_body)

        if method == "GET" and path == "/jobs":
            return respond(200, {"jobs": state["jobs"]})

        if method == "GET" and path == "/services":
            return respond(200, {"services": state["services"]})

        if method == "GET" and path.startswith("/services/"):
            service_id = path.split("/")[-1]
            service = next((svc for svc in state["services"] if svc["id"] == service_id), None)
            if not service:
                return respond(404, {"message": "not found"})
            return respond(200, service)

        return respond(404, {"message": "not found"})

    return httpx.MockTransport(handler), state


@pytest.fixture
async def mcp_server_with_state() -> AsyncGenerator[tuple[Any, dict[str, Any]], None]:
    transport, state = _mock_api_transport()
    config = ServerConfig(api_base_url="http://mock.api", transport=transport)
    server = create_mcp_server(config)
    try:
        yield server, state
    finally:
        client = getattr(server, "_mstream_client", None)
        if client:
            await client.aclose()


def _unwrap(response: Any) -> dict[str, Any]:
    if isinstance(response, tuple) and len(response) == 2 and isinstance(response[1], dict):
        return response[1]
    if isinstance(response, dict):
        return response
    return {}


@pytest.mark.anyio
async def test_list_jobs_tool_end_to_end(
    mcp_server_with_state: tuple[Any, dict[str, Any]],
) -> None:
    server, _ = mcp_server_with_state
    raw_response = await server.call_tool("list_jobs", {})
    response = _unwrap(raw_response)

    assert response["success"] is True
    assert len(response["data"]["jobs"]) == 2
    assert response["data"]["jobs"][0]["id"] == "job-1"
