"""Exact attached World Markdown for Combat participants."""

from __future__ import annotations

import re

from application_state.combat_encounters.types import CombatEntity
from application_state.errors import ApplicationStateNotFoundError, ApplicationStateValidationError
from graph_memory.evidence.source_artifact import build_worldbuilding_source_artifact_id
from pydantic import BaseModel

from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    get_source_artifact,
    load_source_input_bytes,
)

_SOURCE_PREFIX = "artifact:worldbuilding:"


class CombatCorpusSheet(BaseModel):
    participant_id: str
    source_artifact_id: str
    content_sha256: str
    markdown: str


def claims_registered_sheet(entity: CombatEntity) -> bool:
    return (entity.statblock_artifact_id or "").startswith(_SOURCE_PREFIX)


def read_attached_sheet(*, world_id: str, entity: CombatEntity) -> CombatCorpusSheet:
    artifact_id = entity.statblock_artifact_id
    digest = entity.corpus_fingerprint or ""
    if entity.source != "imported" or not artifact_id or not claims_registered_sheet(entity):
        raise ApplicationStateNotFoundError("Participant has no registered corpus sheet")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ApplicationStateValidationError("Corpus sheet requires an exact SHA-256 fingerprint")
    try:
        artifact = get_source_artifact(artifact_id)
        if (
            artifact.world_id != world_id
            or artifact.artifact_kind != "worldbuilding_markdown"
            or artifact.visibility_state != "internal"
            or not artifact.workspace_document_id
            or not artifact.workspace_document_revision
        ):
            raise ApplicationStateNotFoundError("Participant corpus sheet is unavailable in this World")
        expected_id = build_worldbuilding_source_artifact_id(
            workspace_document_id=artifact.workspace_document_id,
            workspace_document_revision=artifact.workspace_document_revision,
            content_sha256=digest,
        )
        if artifact.source_artifact_id != expected_id or artifact_id != expected_id or (
            (artifact.content_sha256 or "").removeprefix("sha256:") != digest
        ):
            raise ApplicationStateValidationError("Corpus sheet differs from the saved source revision")
        markdown = load_source_input_bytes(artifact).decode("utf-8")
    except SourceArtifactRegistryError as exc:
        raise ApplicationStateNotFoundError("Participant corpus sheet is unavailable") from exc
    return CombatCorpusSheet(
        participant_id=entity.id, source_artifact_id=artifact_id,
        content_sha256=digest, markdown=markdown,
    )
