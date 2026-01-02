from __future__ import annotations

from mstream_mcp_server.api.models import (
    BatchConfig,
    ErrorResponse,
    Job,
    SchemaDefinition,
    SchemaField,
    Service,
)


def test_schema_round_trip_with_metadata() -> None:
    schema_dict = {
        "name": "output",
        "fields": [
            {"name": "text", "type": "string", "required": True, "example": "hi"},
            {"name": "score", "type": "number", "required": False},
        ],
        "version": "1.0",
        "description": "Response schema",
        "precision": "high",
    }
    schema = SchemaDefinition.from_dict(schema_dict)

    assert schema.fields[0].metadata == {"example": "hi"}
    assert schema.to_dict() == {
        "name": "output",
        "fields": [
            {
                "name": "text",
                "type": "string",
                "required": True,
                "description": None,
                "example": "hi",
            },
            {
                "name": "score",
                "type": "number",
                "required": False,
                "description": None,
            },
        ],
        "version": "1.0",
        "description": "Response schema",
        "precision": "high",
    }


def test_job_response_contract() -> None:
    payload = {
        "id": "job-123",
        "status": "running",
        "name": "demo-job",
        "input_schema": {
            "name": "input",
            "fields": [{"name": "prompt", "type": "string", "required": True}],
        },
        "batch_config": {"batch_size": 5, "timeout_seconds": 30},
        "metadata_key": "metadata_value",
    }
    job = Job.from_dict(payload)

    assert job.to_dict() == {
        "id": "job-123",
        "status": "running",
        "name": "demo-job",
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
            "batch_size": 5,
            "max_concurrency": None,
            "timeout_seconds": 30.0,
        },
        "metadata_key": "metadata_value",
    }


def test_service_response_contract() -> None:
    payload = {
        "id": "svc-1",
        "name": "search",
        "endpoint": "http://service/api",
        "status": "healthy",
        "schemas": [
            {
                "name": "input",
                "fields": [
                    {
                        "name": "query",
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                    }
                ],
            }
        ],
        "labels": ["default"],
    }
    service = Service.from_dict(payload)

    assert service.to_dict() == {
        "id": "svc-1",
        "name": "search",
        "endpoint": "http://service/api",
        "status": "healthy",
        "schemas": [
            {
                "name": "input",
                "fields": [
                    {
                        "name": "query",
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                    }
                ],
                "version": None,
                "description": None,
            }
        ],
        "labels": ["default"],
    }


def test_batch_config_round_trip() -> None:
    config = BatchConfig.from_dict(
        {"batch_size": 10, "max_concurrency": 3, "timeout_seconds": 2.5}
    )
    assert config.to_dict() == {
        "batch_size": 10,
        "max_concurrency": 3,
        "timeout_seconds": 2.5,
    }


def test_error_response_parsing() -> None:
    error = ErrorResponse.from_response(404, {"message": "missing", "code": "not_found"})
    assert error.status_code == 404
    assert error.message == "missing"
    assert error.details == {"message": "missing", "code": "not_found"}
