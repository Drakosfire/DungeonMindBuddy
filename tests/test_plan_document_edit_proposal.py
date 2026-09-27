"""The Agent proposes Plan edits; it never receives document write authority."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from apps.live_control_server.models.plan_document_edit_proposal import (
    PlanDocumentEditProposalRequest,
)
from apps.live_control_server.routes import live
from apps.live_control_server.services import plan_document_edit_proposal as service


_EMPTY_SHA = hashlib.sha256(b"").hexdigest()


class _FakeGenerationClient:
    def __init__(self, *, parsed: dict | None = None, failure: bool = False) -> None:
        self.requests: list = []
        self.parsed = parsed or {
            "replacement_markdown": "The Shacks wait beneath Hempholm.\n\n> [!READ-ALOUD]\n> Rain taps the roofs.",
            "summary": "Draft the opening frame",
            "assumptions": ["Rain is proposed atmosphere, not established canon."],
            "cannot_complete_reason": None,
        }
        self.failure = failure

    async def generate_structured(self, request):
        self.requests.append(request)
        if self.failure:
            raise RuntimeError("model unavailable")
        return SimpleNamespace(
            parsed=self.parsed,
            observation=SimpleNamespace(
                response_model="observed-test-model",
                resolved_model="test-model",
                latency_ms=314,
                input_tokens=80,
                cached_input_tokens=10,
                output_tokens=30,
                cost_usd=0.002,
                provider_attempt_count=1,
                transport_retry_count=0,
                conformance_retry_count=0,
            ),
        )


def _request(**overrides) -> PlanDocumentEditProposalRequest:
    data = {
        "document_id": "plan-1",
        "world_id": "of-conks-j1-fresh-rehearsal",
        "session": 1,
        "base_revision": 2,
        "base_content_sha256": _EMPTY_SHA,
        "draft_markdown": "",
        "draft_sha256": _EMPTY_SHA,
        "target_kind": "replace_selection",
        "selected_text": "Opening frame",
        "instruction": "Write a brief opening frame.",
        "conversation_history": [{"role": "user", "content": "What is Hempholm?"}],
    }
    data.update(overrides)
    return PlanDocumentEditProposalRequest.model_validate(data)


def _authority(monkeypatch: pytest.MonkeyPatch, *, revision: int = 2, world: str = "of-conks-j1-fresh-rehearsal"):
    record = SimpleNamespace(
        kind="plan", status="active", campaign_id=world, world_id=world, target_session=1
    )
    snapshot = SimpleNamespace(
        record=record, loaded_revision=revision, content_sha256=_EMPTY_SHA
    )
    monkeypatch.setattr(service, "get_world_container", lambda *_: object())
    monkeypatch.setattr(service, "get_workspace_document_snapshot", lambda *_: snapshot)
    return snapshot


def test_proposal_is_inert_and_binds_exact_document_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    fake = _FakeGenerationClient()
    result = service.propose_plan_document_edit(
        root=tmp_path, request=_request(), generation_client=fake, model="test-model"
    )
    assert result.document_id == "plan-1"
    assert result.world_id == "of-conks-j1-fresh-rehearsal"
    assert result.base_revision == 2
    assert result.draft_sha256 == _EMPTY_SHA
    assert result.target_kind == "replace_selection"
    assert result.selected_text_sha256 == hashlib.sha256(b"Opening frame").hexdigest()
    assert result.model == "observed-test-model"
    assert result.model_observed is True
    assert result.model_latency_ms == 314
    assert result.wall_latency_ms >= 0
    assert result.usage == {
        "input_tokens": 80,
        "cached_input_tokens": 10,
        "output_tokens": 30,
        "cost_usd": 0.002,
        "provider_attempt_count": 1,
        "transport_retry_count": 0,
        "conformance_retry_count": 0,
    }
    assert "[!READ-ALOUD]" in result.replacement_markdown
    assert len(fake.requests) == 1
    assert '"current_plan_markdown":""' in fake.requests[0].user_prompt


@pytest.mark.parametrize(
    ("overrides", "authority_kwargs", "code"),
    [
        ({"world_id": "another-world"}, {}, "plan_target_mismatch"),
        ({"session": 2}, {}, "plan_target_mismatch"),
        ({"base_revision": 1}, {}, "plan_base_stale"),
        ({"base_content_sha256": "a" * 64}, {}, "plan_base_stale"),
        ({"draft_sha256": "a" * 64}, {}, "draft_digest_mismatch"),
        ({"selected_text": ""}, {}, "plan_target_missing"),
    ],
)
def test_bad_binding_fails_before_model_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    overrides: dict,
    authority_kwargs: dict,
    code: str,
) -> None:
    _authority(monkeypatch, **authority_kwargs)
    fake = _FakeGenerationClient()
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_plan_document_edit(
            root=tmp_path,
            request=_request(**overrides),
            generation_client=fake,
            model="test-model",
        )
    assert caught.value.code == code
    assert fake.requests == []


def test_model_failure_and_refusal_never_return_confirmable_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    with pytest.raises(service.PlanDocumentEditProposalError, match="could not produce"):
        service.propose_plan_document_edit(
            root=tmp_path,
            request=_request(),
            generation_client=_FakeGenerationClient(failure=True),
            model="test-model",
        )
    refusal = _FakeGenerationClient(
        parsed={
            "replacement_markdown": "",
            "summary": "Cannot comply",
            "assumptions": [],
            "cannot_complete_reason": "Insufficient target context",
        }
    )
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_plan_document_edit(
            root=tmp_path, request=_request(), generation_client=refusal, model="test-model"
        )
    assert caught.value.code == "proposal_refused"


def test_missing_execution_observation_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)

    class _NoObservationClient:
        async def generate_structured(self, _request):
            return SimpleNamespace(parsed=_FakeGenerationClient().parsed, observation=None)

    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_plan_document_edit(
            root=tmp_path,
            request=_request(),
            generation_client=_NoObservationClient(),
            model="test-model",
        )
    assert caught.value.code == "proposal_observation_missing"


def test_route_exposes_proposal_only_after_verified_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    fake = _FakeGenerationClient()
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(service, "_resolve_model", lambda: "test-model")
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: fake)
    valid = live.post_plan_document_edit_proposal(_request())
    assert valid.schema_version == "dmb_plan_document_edit_proposal_v1"
    assert len(fake.requests) == 1

    with pytest.raises(HTTPException) as caught:
        live.post_plan_document_edit_proposal(_request(base_revision=1))
    assert caught.value.status_code == 409
    assert caught.value.detail["code"] == "plan_base_stale"
    assert len(fake.requests) == 1
