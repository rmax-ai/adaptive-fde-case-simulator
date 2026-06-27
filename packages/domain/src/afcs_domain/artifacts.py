from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    """Supported file types for simulation artifacts."""

    PDF = "pdf"
    DOCX = "docx"
    MD = "md"
    YAML = "yaml"
    JSON = "json"
    PYTHON = "python"
    MARKDOWN = "markdown"
    TEXT = "text"
    OTHER = "other"


class Artifact(BaseModel):
    """An artifact created or uploaded during a simulation session."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    artifact_type: ArtifactType
    name: str
    content: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"extra": "forbid"}

    def update_content(self, content: str) -> None:
        """Replace artifact content and bump the updated_at timestamp."""
        self.content = content
        self.updated_at = datetime.now(UTC)
