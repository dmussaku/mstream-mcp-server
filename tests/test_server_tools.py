from __future__ import annotations

import json
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

        if method == "POST" and path == "/jobs":
            payload = json.loads(request.content.decode() or "{}")
            new_job = {
                "id": f"job-{len(state['jobs']) + 1}",
                "status": "running",
                **payload,
            }
            state["jobs"].append(new_job)
            return respond(200, new_job)

        if method == "POST" and path.endswith("/stop"):
            job_id = path.split("/")[-2]
            return respond(
                200, {"id": job_id, "status": "stopped", "name": f"{job_id}-name"}
            )

        if method == "POST" and path.endswith("/restart"):
            job_id = path.split("/")[-2]
            return respond(
                200, {"id": job_id, "status": "running", "name": f"{job_id}-name"}
            )

        if method == "GET" and path == "/services":
            return respond(200, {"services": state["services"]})

        if method == "POST" and path == "/services":
            payload = json.loads(request.content.decode() or "{}")
            new_service = {
                "id": f"svc-{len(state['services']) + 1}",
                **payload,
            }
            state["services"].append(new_service)
            return respond(200, new_service)

        if method == "GET" and path.startswith("/services/"):
            service_id = path.split("/")[-1]
            service = next(
                (svc for svc in state["services"] if svc["id"] == service_id), None
            )
            if not service:
                return respond(404, {"message": "not found"})
            return respond(200, service)

        if method == "DELETE" and path.startswith("/services/"):
            service_id = path.split("/")[-1]
            state["services"] = [
                svc for svc in state["services"] if svc["id"] != service_id
            ]
            return respond(200, {})

        return respond(404, {"message": "not found"})

    return httpx.MockTransport(handler), state


@pytest.fixture
async def mcp_server_with_state() -> tuple[Any, dict[str, Any]]:
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
    return response


@pytest.mark.anyio
async def test_list_jobs_tool_end_to_end(
    mcp_server_with_state: tuple[Any, dict[str, Any]]
) -> None:
    server, _ = mcp_server_with_state
    raw_response = await server.call_tool("list_jobs", {})
    response = _unwrap(raw_response)

    assert response["success"] is True
    assert len(response["data"]["jobs"]) == 2
    assert response["data"]["jobs"][0]["id"] == "job-1"


@pytest.mark.anyio
async def test_create_job_tool_end_to_end(
    mcp_server_with_state: tuple[Any, dict[str, Any]]
) -> None:
    server, state = mcp_server_with_state
    payload = {
        "name": "new-job",
        "input_schema": {
            "name": "input",
            "fields": [{"name": "text", "type": "string", "required": True}],
        },
    }
    raw_response = await server.call_tool("create_job", {"payload": payload})
    response = _unwrap(raw_response)

    assert response["success"] is True
    created_job = response["data"]["job"]
    assert created_job["name"] == "new-job"
    assert len(state["jobs"]) == 3


@pytest.mark.anyio
async def test_service_tools_flow(
    mcp_server_with_state: tuple[Any, dict[str, Any]]
) -> None:
    server, state = mcp_server_with_state
    create_raw = await server.call_tool(
        "create_service",
        {
            "payload": {
                "name": "index",
                "endpoint": "http://svc/index",
                "schemas": [
                    {
                        "name": "input",
                        "fields": [
                            {"name": "doc", "type": "string", "required": True}
                        ],
                    }
                ],
            }
        },
    )
    create_response = _unwrap(create_raw)
    assert create_response["success"] is True
    service_id = create_response["data"]["service"]["id"]

    list_response = _unwrap(await server.call_tool("list_services", {}))
    assert list_response["success"] is True
    assert any(svc["id"] == service_id for svc in list_response["data"]["services"])

    get_response = _unwrap(
        await server.call_tool("get_service", {"service_id": service_id})
    )
    assert get_response["success"] is True
    assert get_response["data"]["service"]["id"] == service_id

    delete_response = _unwrap(
        await server.call_tool("delete_service", {"service_id": service_id})
    )
    assert delete_response["success"] is True
    assert all(svc["id"] != service_id for svc in state["services"])


@pytest.mark.anyio
async def test_create_job_validation_error(
    mcp_server_with_state: tuple[Any, dict[str, Any]]
) -> None:
    server, _ = mcp_server_with_state
    response = _unwrap(
        await server.call_tool("create_job", {"payload": {"input_schema": {}}})
    )

    assert response["success"] is False
    assert "name is required" in response["error"]
