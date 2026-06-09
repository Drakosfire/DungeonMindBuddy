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
            "ok": True,
            "status": "ok",
            "service": "statblockgenerator",
            "version": "v2",
            "timestamp": "2026-06-09T12:00:00Z",
        }
    )

    assert health.ok is True
    assert health.status == "ok"
