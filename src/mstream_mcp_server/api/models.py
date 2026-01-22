from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


@dataclass
class KafkaCursor:
    """Kafka-specific cursor information."""
    topic: str
    partition: int
    offset: int
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KafkaCursor:
        return cls(
            topic=data["topic"],
            partition=data["partition"], 
            offset=data["offset"]
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source": "kafka",
            "topic": self.topic,
            "partition": self.partition,
            "offset": self.offset
        }


@dataclass
class MongoDBCursor:
    """MongoDB-specific cursor information."""
    data: dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MongoDBCursor:
        return cls(data=data.get("data", {}))
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source": "mongodb",
            "data": self.data
        }


@dataclass
class UnknownCursor:
    """Unknown cursor type with raw byte information."""
    raw_bytes: int
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnknownCursor:
        return cls(
            raw_bytes=data.get("raw_bytes", 0),
            raw_data={k: v for k, v in data.items() if k not in {"source", "raw_bytes"}}
        )
    
    def to_dict(self) -> dict[str, Any]:
        result = {
            "source": "unknown",
            "raw_bytes": self.raw_bytes
        }
        result.update(self.raw_data)
        return result


# Type alias for all possible cursor types
CursorType = Union[KafkaCursor, MongoDBCursor, UnknownCursor]


@dataclass
class SchemaField:
    """Represents a single field in a schema."""

    name: str
    type: str
    required: bool = False
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaField:
        return cls(
            name=data.get("name", ""),
            type=data.get("type", ""),
            required=bool(data.get("required", False)),
            description=data.get("description"),
            metadata={
                key: value for key, value in data.items() if key not in {"name", "type", "required", "description"}
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "description": self.description,
            **self.metadata,
        }


@dataclass
class SchemaDefinition:
    """Describes an input or output schema."""

    name: str
    fields: list[SchemaField]
    version: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaDefinition:
        return cls(
            name=data.get("name", ""),
            fields=[SchemaField.from_dict(item) for item in data.get("fields", []) if isinstance(item, dict)],
            version=data.get("version"),
            description=data.get("description"),
            metadata={
                key: value for key, value in data.items() if key not in {"name", "fields", "version", "description"}
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fields": [field.to_dict() for field in self.fields],
            "version": self.version,
            "description": self.description,
            **self.metadata,
        }


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int
    max_concurrency: int | None = None
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchConfig:
        return cls(
            batch_size=int(data.get("batch_size", 0)),
            max_concurrency=(
                int(data["max_concurrency"])
                if "max_concurrency" in data and data["max_concurrency"] is not None
                else None
            ),
            timeout_seconds=(
                float(data["timeout_seconds"])
                if "timeout_seconds" in data and data["timeout_seconds"] is not None
                else None
            ),
            metadata={
                key: value
                for key, value in data.items()
                if key not in {"batch_size", "max_concurrency", "timeout_seconds"}
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_size": self.batch_size,
            "max_concurrency": self.max_concurrency,
            "timeout_seconds": self.timeout_seconds,
            **self.metadata,
        }


@dataclass
class Job:
    """Represents a job lifecycle and configuration."""

    id: str
    status: str
    name: str | None = None
    input_schema: SchemaDefinition | None = None
    output_schema: SchemaDefinition | None = None
    batch_config: BatchConfig | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        return cls(
            id=str(data.get("id", "")),
            status=data.get("status", ""),
            name=data.get("name"),
            input_schema=(
                SchemaDefinition.from_dict(data["input_schema"]) if isinstance(data.get("input_schema"), dict) else None
            ),
            output_schema=(
                SchemaDefinition.from_dict(data["output_schema"])
                if isinstance(data.get("output_schema"), dict)
                else None
            ),
            batch_config=(
                BatchConfig.from_dict(data["batch_config"]) if isinstance(data.get("batch_config"), dict) else None
            ),
            metadata={
                key: value
                for key, value in data.items()
                if key
                not in {
                    "id",
                    "status",
                    "name",
                    "input_schema",
                    "output_schema",
                    "batch_config",
                }
            },
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "status": self.status,
            "name": self.name,
            **self.metadata,
        }
        if self.input_schema:
            payload["input_schema"] = self.input_schema.to_dict()
        if self.output_schema:
            payload["output_schema"] = self.output_schema.to_dict()
        if self.batch_config:
            payload["batch_config"] = self.batch_config.to_dict()
        return payload


@dataclass
class JobCreateRequest:
    """Payload used to create a job."""

    name: str
    input_schema: SchemaDefinition
    output_schema: SchemaDefinition | None = None
    batch_config: BatchConfig | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "input_schema": self.input_schema.to_dict(),
            **self.metadata,
        }
        if self.output_schema:
            payload["output_schema"] = self.output_schema.to_dict()
        if self.batch_config:
            payload["batch_config"] = self.batch_config.to_dict()
        return payload


@dataclass
class Service:
    """Represents a service registered with the mstream server."""

    id: str
    name: str
    endpoint: str
    status: str | None = None
    schemas: list[SchemaDefinition] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Service:
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            endpoint=data.get("endpoint", ""),
            status=data.get("status"),
            schemas=[SchemaDefinition.from_dict(item) for item in data.get("schemas", []) if isinstance(item, dict)],
            metadata={
                key: value for key, value in data.items() if key not in {"id", "name", "endpoint", "status", "schemas"}
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "endpoint": self.endpoint,
            "status": self.status,
            "schemas": [schema.to_dict() for schema in self.schemas],
            **self.metadata,
        }


@dataclass
class ServiceCreateRequest:
    """Payload used to register a new service."""

    name: str
    endpoint: str
    schemas: list[SchemaDefinition] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "schemas": [schema.to_dict() for schema in self.schemas],
            **self.metadata,
        }


@dataclass
class ErrorResponse:
    """Represents an error returned by the API."""

    status_code: int
    message: str
    details: dict[str, Any] | None = None

    @classmethod
    def from_response(cls, status_code: int, data: Any) -> ErrorResponse:
        if isinstance(data, dict):
            return cls(
                status_code=status_code,
                message=str(data.get("message") or data.get("detail") or ""),
                details=data,
            )
        return cls(status_code=status_code, message=str(data))


@dataclass
class CursorInfo:
    """Wrapper for cursor information that handles different source types.
    
    This matches the Rust API's tagged union structure and provides type-safe
    access to cursor data based on the source type.
    """
    
    cursor: CursorType
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CursorInfo:
        """Create CursorInfo from API response dictionary."""
        if not isinstance(data, dict):
            return cls(cursor=UnknownCursor(raw_bytes=0, raw_data={"error": "invalid_data"}))
        
        # Handle tagged union format from Rust API
        source = data.get("source", "unknown").lower()
        
        try:
            if source == "kafka":
                return cls(cursor=KafkaCursor.from_dict(data))
            elif source == "mongodb":
                return cls(cursor=MongoDBCursor.from_dict(data))
            else:  # unknown or any other type
                return cls(cursor=UnknownCursor.from_dict(data))
        except (KeyError, TypeError, ValueError) as e:
            # Fallback to unknown cursor if parsing fails
            return cls(cursor=UnknownCursor(
                raw_bytes=len(str(data).encode()),
                raw_data={"parse_error": str(e), "original_data": data}
            ))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching Rust API format."""
        return self.cursor.to_dict()
    
    @property
    def is_kafka(self) -> bool:
        """Check if this is a Kafka cursor."""
        return isinstance(self.cursor, KafkaCursor)
    
    @property
    def is_mongodb(self) -> bool:
        """Check if this is a MongoDB cursor."""
        return isinstance(self.cursor, MongoDBCursor)
    
    @property
    def is_unknown(self) -> bool:
        """Check if this is an unknown cursor type."""
        return isinstance(self.cursor, UnknownCursor)
    
    def as_kafka(self) -> KafkaCursor | None:
        """Get as Kafka cursor if applicable."""
        return self.cursor if isinstance(self.cursor, KafkaCursor) else None
    
    def as_mongodb(self) -> MongoDBCursor | None:
        """Get as MongoDB cursor if applicable."""
        return self.cursor if isinstance(self.cursor, MongoDBCursor) else None
    
    def as_unknown(self) -> UnknownCursor | None:
        """Get as unknown cursor if applicable."""
        return self.cursor if isinstance(self.cursor, UnknownCursor) else None


@dataclass
class Checkpoint:
    """Represents a checkpoint for job progress tracking."""

    job_name: str
    updated_at: str
    cursor: CursorInfo
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        cursor_data = data.get("cursor", {})
        return cls(
            job_name=data.get("job_name", ""),
            updated_at=data.get("updated_at", ""),
            cursor=CursorInfo.from_dict(cursor_data),
            metadata={
                key: value for key, value in data.items() 
                if key not in {"job_name", "updated_at", "cursor"}
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_name": self.job_name,
            "updated_at": self.updated_at,
            "cursor": self.cursor.to_dict(),
            **self.metadata,
        }
