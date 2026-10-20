"""Shared result and error models for document processing."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PreparedDocumentResult:
    """JSON-ready output consumed by the separate reasoning module."""

    schema_version: str
    document_id: str
    source: dict[str, str]
    text: str
    metadata: dict[str, Any]
    warnings: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the result as ordinary JSON-serializable Python values."""
        return {
            "schema_version": self.schema_version,
            "document_id": self.document_id,
            "source": self.source,
            "text": self.text,
            "metadata": self.metadata,
            "warnings": self.warnings,
        }


class ProcessingError(Exception):
    """An expected processing failure safe to report to an API client."""

    def __init__(self, code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
