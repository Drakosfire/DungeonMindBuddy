from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.statblocks.lifecycle_artifact import (
    StatblockBreadcrumb,
    artifact_from_draft_response,
)
from src.statblocks.v2_contract import StatBlockDraftResponse

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture_response(
    name: str = "generated_draft_response.fixture.json",
) -> StatBlockDraftResponse:
    return StatBlockDraftResponse.model_validate(
        json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    )


def test_draft_response_maps_to_statblock_draft_artifact() -> None:
    response = _fixture_response()
    fixed_now = datetime(2026, 6, 9, 13, 0, tzinfo=UTC)
    breadcrumb = StatblockBreadcrumb(
        label="Command Board", source="planner", target="statblock-workbench"
    )

    artifact = artifact_from_draft_response(
        response,
        created_by="agent",
        breadcrumbs=[breadcrumb],
        now=lambda: fixed_now,
        artifact_id_factory=lambda: "artifact-fixed-id",
    )

    assert response.draft is not None
    assert artifact.artifact_id == "artifact-fixed-id"
    assert artifact.draft_id == response.draft.draft_id
    assert artifact.title == "Ember Wolf"
    assert artifact.markdown == response.draft.markdown
    assert artifact.structured_statblock == response.draft.statblock
    assert artifact.combat_defaults == response.draft.combat_defaults
    assert artifact.warnings == response.draft.warnings
    assert artifact.provenance == response.draft.provenance
    assert artifact.source_refs == response.draft.provenance.source_refs
    assert artifact.breadcrumbs == [breadcrumb]
    assert artifact.created_by == "agent"
    assert artifact.created_at == "2026-06-09T13:00:00+00:00"
    assert artifact.updated_at == "2026-06-09T13:00:00+00:00"


def test_artifact_status_defaults_are_lifecycle_safe() -> None:
    artifact = artifact_from_draft_response(
        _fixture_response("rendered_draft_response.fixture.json"),
        created_by="planning_task",
        now=lambda: datetime(2026, 6, 9, 13, 5, tzinfo=UTC),
        artifact_id_factory=lambda: "artifact-rendered-id",
    )

    assert artifact.review_status == "warnings"
    assert artifact.lifecycle_state == "live_draft"
    assert artifact.storage_status == "not_stored"
    assert artifact.corpus_status == "not_promoted"
    assert artifact.breadcrumbs == []


def test_artifact_title_falls_back_to_statblock_name_then_draft_id() -> None:
    response = _fixture_response()
    assert response.draft is not None
    response.draft.combat_defaults.name = None
    response.draft.statblock["name"] = "Fallback Statblock Name"

    statblock_title_artifact = artifact_from_draft_response(
        response,
        created_by="human",
        now=lambda: datetime(2026, 6, 9, 14, 0, tzinfo=UTC),
        artifact_id_factory=lambda: "artifact-title-1",
    )
    assert statblock_title_artifact.title == "Fallback Statblock Name"

    response.draft.statblock.pop("name")
    draft_id_title_artifact = artifact_from_draft_response(
        response,
        created_by="human",
        now=lambda: datetime(2026, 6, 9, 14, 0, tzinfo=UTC),
        artifact_id_factory=lambda: "artifact-title-2",
    )
    assert draft_id_title_artifact.title == "draft-generated-ember-wolf"


def test_unsuccessful_response_cannot_map_to_artifact() -> None:
    response = StatBlockDraftResponse.model_validate(
        {
            "success": False,
            "draft": None,
            "error": {"code": "failed", "message": "generation failed"},
        }
    )

    with pytest.raises(ValueError, match="only successful"):
        artifact_from_draft_response(response, created_by="agent")
