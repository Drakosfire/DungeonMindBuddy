"""Shared World proposal model policy and retired non-World HTTP boundary."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.routes import live
from apps.live_control_server.services import plan_document_edit_proposal as service


def test_plan_proposal_selects_current_conversation_model() -> None:
    assert service._resolve_model() == "gpt-6-luna"


@pytest.mark.parametrize(
    ("actions", "expected"),
    [
        ({"hermes_graph_agent": "conversation", "structured_generation": "structured"}, "conversation-model"),
        ({"structured_generation": "structured"}, "legacy-model"),
    ],
)
def test_plan_proposal_selector_prefers_conversation_with_legacy_fallback(monkeypatch, actions, expected) -> None:
    calls = []

    def policy(*, strict):
        calls.append(strict)
        return {"actions": actions, "models": {"conversation": "conversation-model", "structured": "legacy-model"}}

    monkeypatch.setattr(service, "load_buddy_model_policy", policy)
    assert service._resolve_model() == expected
    assert calls == [True]


@pytest.mark.parametrize("role", [None, "missing-role", ""])
def test_configured_invalid_conversation_role_does_not_fall_back(monkeypatch, role) -> None:
    monkeypatch.setattr(service, "load_buddy_model_policy", lambda **_: {
        "actions": {"hermes_graph_agent": role, "structured_generation": "structured"},
        "models": {"structured": "legacy-model"},
    })
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service._resolve_model()
    assert caught.value.code == "model_policy_unavailable"


def test_plan_proposal_missing_and_malformed_policy_remain_strict(monkeypatch, tmp_path) -> None:
    path = tmp_path / "MODEL_POLICY.json"
    monkeypatch.setattr("src.model_policy.buddy_model_policy_path", lambda: path)
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service._resolve_model()
    assert caught.value.code == "model_policy_unavailable"
    path.write_text("{ malformed", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        service._resolve_model()


def test_unowned_plan_producer_is_absent_from_mounted_http_and_openapi(monkeypatch):
    monkeypatch.setattr(service.GenerationClient,'from_env',lambda:pytest.fail('Retired endpoint dispatched a provider'))
    app=FastAPI()
    app.include_router(live.router)
    with TestClient(app) as client:
        response=client.post('/api/live/plan-document-edit/propose',json={'instruction':'No legacy execution'})
        assert response.status_code==404
        paths=client.get('/openapi.json').json()['paths']
    assert '/api/live/plan-document-edit/propose' not in paths
    assert 'post' in paths['/api/live/world-plan-edit/propose']
