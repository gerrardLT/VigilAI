"""
Artifact persistence helpers for shared agent sessions.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .models import AgentArtifact
from .repository import AgentPlatformRepository


class ArtifactDraft(BaseModel):
    artifact_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ArtifactService:
    def __init__(self, repository: AgentPlatformRepository):
        self.repository = repository

    def persist(self, session_id: str, drafts: list[ArtifactDraft]) -> list[AgentArtifact]:
        artifacts: list[AgentArtifact] = []
        for draft in drafts:
            artifacts.append(
                self.repository.create_artifact(
                    session_id,
                    artifact_type=draft.artifact_type,
                    title=draft.title,
                    content=draft.content,
                    payload=draft.payload,
                )
            )
        return artifacts

    def list_for_session(self, session_id: str) -> list[AgentArtifact]:
        return self.repository.list_artifacts(session_id)
