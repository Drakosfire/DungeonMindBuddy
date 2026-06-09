from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.statblocks.v2_contract import StatBlockDraftResponse, StatBlockGeneratorHealth

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_generated_fixture_validates_as_draft_response() -> None:
    response = StatBlockDraftResponse.model_validate(
        _load_fixture("generated_draft_response.fixture.json")
    )

    assert response.success is True
    assert response.draft is not None
    assert response.draft.draft_id == "draft-generated-ember-wolf"
    assert response.draft.combat_defaults.primary_actions


def test_rendered_fixture_validates_as_draft_response() -> None:
    response = StatBlockDraftResponse.model_validate(
        _load_fixture("rendered_draft_response.fixture.json")
    )

    assert response.success is True
    assert response.draft is not None
    assert response.draft.lifecycle_state == "live_draft"
    assert response.draft.review_status == "warnings"


def test_production_shaped_fixture_exposes_explicit_combat_and_provenance_fields() -> (
    None
):
    response = StatBlockDraftResponse.model_validate(
        _load_fixture("production_shaped_draft_response.fixture.json")
    )

    assert response.draft is not None
    assert response.draft.combat_defaults.passive_perception == 12
    assert response.draft.combat_defaults.speed_summary == "30 ft., swim 20 ft."
    assert (
        response.draft.combat_defaults.effective_speed_summary == "30 ft., swim 20 ft."
    )
    assert (
        response.draft.combat_defaults.senses_summary
        == "darkvision 60 ft., passive Perception 12"
    )
    assert response.draft.combat_defaults.suggested_tactics == [
        "Skirmish from reed cover.",
        "Use swim speed to flank along marsh channels.",
    ]
    assert (
        response.draft.provenance.request_id == "prod-smoke-generate-from-prompt-basic"
    )
    assert (
        response.draft.provenance.generation_info["contract"]
        == "command_board_draft_v2"
    )
    assert response.draft.provenance.source_refs[0].id == "source-prod-smoke-prompt"
    assert response.draft.provenance.source_refs[0].kind == "prompt"
    assert response.draft.provenance.source_refs[0].label == "Production smoke prompt"
    assert (
        response.draft.provenance.source_refs[0].reason == "Live deploy smoke coverage"
    )


def test_successful_response_requires_draft() -> None:
    with pytest.raises(ValidationError, match="must include draft"):
        StatBlockDraftResponse.model_validate(
            {"success": True, "draft": None, "error": None}
        )


def test_error_response_requires_error() -> None:
    response = StatBlockDraftResponse.model_validate(
        {
            "success": False,
            "draft": None,
            "error": {
                "code": "unauthorized",
                "message": "Internal key was rejected.",
                "details": {"status": 401},
            },
            "timestamp": "2026-06-09T12:10:00Z",
        }
    )

    assert response.error is not None
    assert response.error.code == "unauthorized"


def test_failed_response_without_error_is_invalid() -> None:
    with pytest.raises(ValidationError, match="must include error"):
        StatBlockDraftResponse.model_validate(
            {"success": False, "draft": None, "error": None}
        )


def test_health_payload_validates() -> None:
    health = StatBlockGeneratorHealth.model_validate(
        {
            "status": "ok",
            "service": "statblockgenerator",
            "contract": "command_board_draft_v2",
            "version": "0.1.0",
            "generator_ready": True,
            "openai_configured": True,
            "supports": ["generate-draft", "render-draft"],
            "timestamp": "2026-06-09T12:00:00Z",
        }
    )

    assert health.status == "ok"
    assert health.contract == "command_board_draft_v2"
    assert health.generator_ready is True
    assert health.openai_configured is True
    assert health.supports == ["generate-draft", "render-draft"]


def test_request_models_expose_production_request_fields() -> None:
    from src.statblocks.v2_contract import (
        OutputOptions,
        SourceRef,
        StatBlockDraftRenderRequest,
        StatBlockDraftRequest,
    )

    request = StatBlockDraftRequest(
        request_id="request-1",
        mode="revise_existing",
        prompt="Tighten this creature for a marsh ambush.",
        revision_instructions=["Lower damage", "Keep mobility"],
        source_refs=[
            SourceRef(
                id="src-1",
                kind="corpus",
                label="Marsh notes",
                reason="Encounter context",
            )
        ],
        output_options=OutputOptions(include_review_warnings=True, persist=False),
    )
    render_request = StatBlockDraftRenderRequest(
        request_id="render-1", statblock={"name": "Rendered"}
    )

    assert request.request_id == "request-1"
    assert request.prompt == "Tighten this creature for a marsh ambush."
    assert request.revision_instructions == ["Lower damage", "Keep mobility"]
    assert request.source_refs[0].id == "src-1"
    assert request.output_options.include_review_warnings is True
    assert request.output_options.persist is False
    assert render_request.request_id == "render-1"
