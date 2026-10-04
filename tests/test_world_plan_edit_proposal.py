"""World-only Plan edits are inert proposals bound to the exact saved Plan."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Lock
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.live_control_server.models.plan_document_edit_proposal import (
    WorldPlanDocumentEditProposalRequest,
)
from apps.live_control_server.routes import live, workspace_documents
from apps.live_control_server.services import plan_document_edit_proposal as service
from apps.live_control_server.services.workspace_document_registry import (
    WorldOwnedCommittedRevisionV2,
)
from apps.live_control_server.services.world_container_registry import create_world_container
from application_state.agent_conversation.types import (
    CompletedPlanAskPair,
    ConversationCommand,
    HistoricalReference,
    PlanAskContextBasis,
    SubmittedGraphRequestIntentV1,
    SubmittedPrimaryWorkIntentV1,
    SubmittedTurnIntentV1,
    TurnProvenance,
    TurnResult,
    TurnSubmission,
)
from application_state.agent_conversation import AgentConversationService
from application_state.errors import ApplicationStateConflictError
from application_state.plan_action_dialogue.service import PlanActionDialogueService
from application_state.plan_action_dialogue.types import (
    CompletedPlanActionContext,
    PlanActionBasis,
    PlanActionPlayableTargetReceipt,
    PlanActionReservation,
)
from apps.live_control_server.services.plan_playable_body_target import PlayableTarget, resolve_playable_body_target


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _request(**overrides) -> WorldPlanDocumentEditProposalRequest:
    data = {
        "idempotency_key": str(uuid4()),
        "document_id": "plan-1",
        "world_id": "world-1",
        "base_revision": 2,
        "base_content_sha256": _sha("SAVED SERVER PROSE"),
        "draft_markdown": "# Current local draft\n",
        "draft_sha256": _sha("# Current local draft\n"),
        "target_kind": "replace_selection",
        "selected_text": "local draft",
        "instruction": "Make this more suspenseful.",
        "conversation_history": [{"role": "user", "content": "Start the scene."}],
    }
    data.update(overrides)
    return WorldPlanDocumentEditProposalRequest.model_validate(data)


_CARD_DRAFT = (
    "<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n"
    "## First\n"
    "The same authored body.\n\n"
    "<!-- dmb-playable-element:v1 kind=scene id=scene:second -->\n"
    "## Second\n"
    "The same authored body.\n"
)


def _playable_request(*, target_id: str = "scene:first", idempotency_key: str | None = None):
    kind = target_id.split(":", 1)[0]
    resolved = resolve_playable_body_target(_CARD_DRAFT, PlayableTarget(kind=kind, id=target_id))
    return _request(
        idempotency_key=idempotency_key or str(uuid4()),
        draft_markdown=_CARD_DRAFT,
        draft_sha256=_sha(_CARD_DRAFT),
        target_kind="replace_playable_body",
        selected_text="",
        playable_target={"kind": kind, "id": target_id},
        body_serialization_version=resolved.body_serialization_version,
        target_body_markdown=resolved.target_body_markdown,
        target_body_sha256=resolved.target_body_sha256,
    )


class _FakeGenerationClient:
    def __init__(self, replacement_markdown: str = "The shutters rattle in the wind.") -> None:
        self.requests: list = []
        self.replacement_markdown = replacement_markdown

    async def generate_structured(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            parsed={
                "replacement_markdown": self.replacement_markdown,
                "summary": "Add a tense beat",
                "assumptions": ["The sound is proposed atmosphere."],
                "cannot_complete_reason": None,
            },
            observation=SimpleNamespace(
                response_model="observed-test-model",
                resolved_model="test-model",
                latency_ms=314,
                input_tokens=80,
                output_tokens=30,
                cost_usd=0.002,
            ),
        )


class _FakeActionStore:
    def __init__(self) -> None:
        self.reservations = []
        self.finished = []
        self.action_id = None
        self.existing = None
        self.lookup_results = None
        self.race_action = None
        self.reserve_error = None
        self.plan_context = []
        self.context_calls = []
        self.context_error = None

    def get_by_key(self, _world_id, _key):
        if self.lookup_results:
            return self.lookup_results.pop(0)
        return self.existing

    def reserve(self, request):
        self.reservations.append(request)
        if self.reserve_error is not None:
            raise self.reserve_error
        if self.race_action is not None:
            return self.race_action, False
        self.action_id = uuid4()
        return SimpleNamespace(
            action_id=self.action_id,
            idempotency_key=request.idempotency_key,
            dispatch_token=uuid4(),
            fence=1,
            status="pending",
        ), True

    def completed_context(self, basis, *, limit=6):
        self.context_calls.append((basis, limit))
        if self.context_error is not None:
            raise self.context_error
        return self.plan_context

    def finish(self, **kwargs):
        self.finished.append(kwargs)
        return SimpleNamespace(status=kwargs["status"])


class _FakeAskContextService:
    def __init__(self, pairs=None, *, error=None) -> None:
        self.pairs = pairs or []
        self.error = error
        self.calls = []

    def list_completed_plan_ask_context(self, world_id, basis, *, limit=6):
        self.calls.append((world_id, basis, limit))
        if self.error is not None:
            raise self.error
        return self.pairs


def _authority(
    monkeypatch: pytest.MonkeyPatch,
    *,
    world_id: str = "world-1",
    document_world_id: str = "world-1",
    kind: str = "plan",
    status: str = "active",
    revision: int = 2,
    saved_markdown: str = "SAVED SERVER PROSE",
):
    world = SimpleNamespace(world_id=world_id)
    snapshot = WorldOwnedCommittedRevisionV2(
        world_id=document_world_id,
        document_id="plan-1",
        kind=kind,
        status=status,
        object_revision=revision,
        work_revision_id=str(UUID("00000000-0000-4000-8000-000000000001")),
        revision_n=3,
        markdown=saved_markdown,
        content_sha256=_sha(saved_markdown),
        title="Plan",
    )
    monkeypatch.setattr(service, "get_world_container", lambda *_: world)
    monkeypatch.setattr(service, "get_committed_playable_revision", lambda *_args, **_kwargs: snapshot)
    ask_reader = _FakeAskContextService()
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)
    return snapshot


def _plan_basis(snapshot) -> PlanActionBasis:
    return PlanActionBasis(
        world_id="world-1",
        document_id="plan-1",
        object_revision=snapshot.object_revision,
        work_revision_id=UUID(snapshot.work_revision_id),
        revision_n=snapshot.revision_n,
        content_sha256=snapshot.content_sha256,
    )


def _stored_action(
    request: WorldPlanDocumentEditProposalRequest,
    basis: PlanActionBasis,
    *,
    status: str = "pending",
    request_fingerprint: str | None = None,
):
    playable_receipt = None
    if request.target_kind == "replace_playable_body":
        assert request.playable_target is not None
        assert request.target_body_sha256 is not None
        resolved = resolve_playable_body_target(
            request.draft_markdown,
            PlayableTarget(kind=request.playable_target.kind, id=request.playable_target.id),
        )
        playable_receipt = PlanActionPlayableTargetReceipt(
            schema_version="dmb_plan_playable_target_receipt_v1",
            kind=resolved.target.kind,
            id=resolved.target.id,
            marker_grammar_version=resolved.marker_grammar_version,
            body_scope=resolved.body_scope,
            range_semantics_version=resolved.range_semantics_version,
            body_serialization_version=resolved.body_serialization_version,
            target_body_sha256=resolved.target_body_sha256,
        )
    return SimpleNamespace(
        action_id=uuid4(),
        idempotency_key=request.idempotency_key,
        request_fingerprint=request_fingerprint or service._action_fingerprint(request, basis, playable_receipt),
        action_type="compose" if request.target_kind == "insert_at_caret" else "revise",
        basis=basis,
        draft_matches_basis=request.draft_sha256 == basis.content_sha256,
        draft_sha256=request.draft_sha256,
        target_kind=request.target_kind,
        selected_text_sha256=(
            None if request.target_kind in {"insert_at_caret", "replace_playable_body"} else _sha(request.selected_text)
        ),
        playable_target_receipt=playable_receipt,
        instruction=request.instruction,
        status=status,
        assistant_summary="Stored proposal summary" if status == "completed" else None,
        dispatch_token=uuid4(),
        fence=1,
    )


def _legacy_action_fingerprint(
    request: WorldPlanDocumentEditProposalRequest, basis: PlanActionBasis
) -> str:
    return service.action_request_fingerprint(
        {
            "basis": basis.model_dump(mode="json"),
            "action_type": "compose" if request.target_kind == "insert_at_caret" else "revise",
            "draft_sha256": request.draft_sha256,
            "target_kind": request.target_kind,
            "selected_text_sha256": _sha(request.selected_text),
            "instruction": request.instruction,
            "conversation_history": [
                item.model_dump(mode="json") for item in request.conversation_history
            ],
        }
    )


def _completed_plan_pair(
    basis: PlanActionBasis,
    *,
    action_id: UUID,
    sequence: int,
    accepted_at: datetime,
    instruction: str,
    summary: str,
) -> CompletedPlanActionContext:
    return CompletedPlanActionContext(
        action_id=action_id,
        action_type="revise",
        basis=basis,
        instruction=instruction,
        assistant_summary=summary,
        action_sequence=sequence,
        accepted_at=accepted_at,
    )


def _completed_ask_pair(
    *,
    record_id: UUID,
    sequence: int,
    accepted_at: datetime,
    question: str,
    answer: str,
) -> CompletedPlanAskPair:
    return CompletedPlanAskPair(
        source_sequence=sequence,
        source_record_id=record_id,
        accepted_at=accepted_at,
        question=question,
        answer=answer,
    )


@pytest.mark.parametrize(
    ("authority", "overrides", "expected_code"),
    [
        ({"world_id": "another-world"}, {}, "plan_target_mismatch"),
        ({"document_world_id": "another-world"}, {}, "plan_target_mismatch"),
        ({"kind": "runbook"}, {}, "plan_target_mismatch"),
        ({"status": "discarded"}, {}, "plan_target_mismatch"),
        ({}, {"base_revision": 1}, "plan_base_stale"),
        ({}, {"base_content_sha256": "a" * 64}, "plan_base_stale"),
        ({}, {"draft_sha256": "a" * 64}, "draft_digest_mismatch"),
        ({}, {"selected_text": "   "}, "plan_target_missing"),
        ({}, {"target_kind": "insert_at_caret", "selected_text": "selected"}, "plan_target_invalid"),
    ],
)
def test_invalid_world_plan_binding_fails_before_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    authority: dict,
    overrides: dict,
    expected_code: str,
) -> None:
    _authority(monkeypatch, **authority)
    fake = _FakeGenerationClient()

    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=_request(**overrides),
            generation_client=fake,
            model="test-model",
            action_store=_FakeActionStore(),
        )

    assert caught.value.code == expected_code
    assert fake.requests == []


def test_world_request_forbids_session_and_campaign_authority_fields() -> None:
    with pytest.raises(ValueError):
        _request(session=1)
    with pytest.raises(ValueError):
        _request(campaign_id="world-1")


@pytest.mark.parametrize("failure_point", ["get_by_key", "reserve"])
def test_raw_action_store_database_errors_return_stable_503(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure_point: str
) -> None:
    _authority(monkeypatch)
    fake = _FakeGenerationClient()

    class _BrokenStore:
        def get_by_key(self, _world_id, _key):
            if failure_point == "get_by_key":
                raise psycopg.OperationalError("test connection failure")
            return None

        def reserve(self, _request):
            raise psycopg.OperationalError("test connection failure")

    monkeypatch.setattr(service, "PlanActionDialogueService", _BrokenStore)
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=_request(target_kind="insert_at_caret", selected_text=""),
            generation_client=fake,
            model="test-model",
        )

    assert caught.value.status_code == 503
    assert caught.value.code == "action_store_unavailable"
    assert fake.requests == []


def test_raw_action_status_database_error_returns_stable_503(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)

    class _BrokenStore:
        def list_status(self, _basis):
            raise psycopg.OperationalError("test connection failure")

    monkeypatch.setattr(service, "PlanActionDialogueService", _BrokenStore)
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.get_world_plan_action_projection(
            root=tmp_path,
            world_id="world-1",
            document_id="plan-1",
        )

    assert caught.value.status_code == 503
    assert caught.value.code == "action_store_unavailable"


def test_world_proposal_uses_only_explicit_draft_context_and_returns_exact_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = _authority(monkeypatch)
    fake = _FakeGenerationClient()
    action_store = _FakeActionStore()
    ask_reader = _FakeAskContextService()
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)
    result = service.propose_world_plan_document_edit(
        root=tmp_path,
        request=_request(),
        generation_client=fake,
        model="test-model",
        action_store=action_store,
    )

    assert result.schema_version == "dmb_world_plan_document_edit_proposal_v1"
    assert result.action_id == action_store.action_id
    assert result.document_id == "plan-1"
    assert result.world_id == "world-1"
    assert not hasattr(result, "session")
    assert result.base_revision == 2
    assert result.base_content_sha256 == snapshot.content_sha256
    assert result.draft_sha256 == _sha("# Current local draft\n")
    assert result.selected_text_sha256 == _sha("local draft")
    assert result.model == "observed-test-model"
    assert result.replacement_markdown == "The shutters rattle in the wind."
    assert len(fake.requests) == 1
    assert fake.requests[0].deadline_ms == 60_000
    assert action_store.reservations[0].basis.object_revision == 2
    assert action_store.reservations[0].basis.revision_n == 3
    assert action_store.reservations[0].draft_matches_basis is False
    assert action_store.finished[0]["status"] == "completed"
    context = json.loads(fake.requests[0].user_prompt)
    assert context["current_plan_markdown"] == "# Current local draft\n"
    assert "SAVED SERVER PROSE" not in fake.requests[0].user_prompt
    assert context["conversation_history"] == []
    assert "Start the scene." not in fake.requests[0].user_prompt
    basis = action_store.reservations[0].basis
    assert action_store.context_calls == [(basis, 6)]
    assert ask_reader.calls == [("world-1", PlanAskContextBasis.model_validate(
        basis.model_dump(mode="python")
    ), 6)]


def test_playable_body_proposal_persists_and_echoes_exact_target_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = _authority(monkeypatch)
    request = _playable_request()
    fake = _FakeGenerationClient("A reviewed body replacement.")
    action_store = _FakeActionStore()
    ask_reader = _FakeAskContextService()
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)

    result = service.propose_world_plan_document_edit(
        root=tmp_path,
        request=request,
        generation_client=fake,
        model="test-model",
        action_store=action_store,
    )

    assert result.schema_version == "dmb_world_plan_document_edit_proposal_v2"
    assert result.idempotency_key == request.idempotency_key
    assert result.action_id == action_store.action_id
    assert result.target_kind == "replace_playable_body"
    assert result.playable_target == request.playable_target
    assert result.selected_text_sha256 is None
    assert result.target_body_sha256 == request.target_body_sha256
    assert result.marker_grammar_version == "v1"
    assert result.body_scope == "heading_body"
    assert result.range_semantics_version == "plan-playable-ranges-v1"
    assert result.body_serialization_version == "plan-playable-body-markdown-v1"
    receipt = action_store.reservations[0].playable_target_receipt
    assert receipt.kind == "scene" and receipt.id == "scene:first"
    assert receipt.target_body_sha256 == request.target_body_sha256
    assert receipt.marker_grammar_version == "v1"
    assert receipt.body_scope == "heading_body"
    context = json.loads(fake.requests[0].user_prompt)
    assert context["playable_target"] == {"kind": "scene", "id": "scene:first"}
    assert context["target_body_markdown"] == request.target_body_markdown
    assert result.base_content_sha256 == snapshot.content_sha256
    assert ask_reader.calls


def test_same_key_different_playable_id_conflicts_before_current_plan_read_or_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = _authority(monkeypatch)
    first = _playable_request(target_id="scene:first")
    different = _playable_request(target_id="scene:second", idempotency_key=str(first.idempotency_key))
    stored = _stored_action(first, _plan_basis(snapshot))
    store = _FakeActionStore()
    store.existing = stored
    fake = _FakeGenerationClient()

    def current_plan_read_must_not_happen(*_args, **_kwargs):
        pytest.fail("same-key target conflict must be decided before the current Plan read")

    monkeypatch.setattr(service, "get_committed_playable_revision", current_plan_read_must_not_happen)
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=different,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )

    assert caught.value.code == "action_idempotency_conflict"
    assert fake.requests == []
    assert store.reservations == []


def test_same_key_different_playable_id_loses_reservation_race_before_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = _authority(monkeypatch)
    first = _playable_request(target_id="scene:first")
    different = _playable_request(target_id="scene:second", idempotency_key=str(first.idempotency_key))
    raced = _stored_action(first, _plan_basis(snapshot))
    store = _FakeActionStore()
    store.reserve_error = ApplicationStateConflictError("unique idempotency key")
    store.lookup_results = [None, raced]
    fake = _FakeGenerationClient()

    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=different,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )

    assert caught.value.code == "action_idempotency_conflict"
    assert fake.requests == []
    assert store.context_calls == []


@pytest.mark.parametrize("fingerprint_version", ["legacy", "current"])
def test_same_key_retry_reconciles_typed_receipt_after_plan_advances(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fingerprint_version: str
) -> None:
    _authority(monkeypatch)
    original_request = _request()
    request = _request(
        idempotency_key=str(original_request.idempotency_key),
        conversation_history=[{"role": "user", "content": "changed untrusted history"}],
    )
    action_store = _FakeActionStore()
    basis = service._validate_world_authority(tmp_path, original_request)
    fingerprint = (
        _legacy_action_fingerprint(original_request, basis)
        if fingerprint_version == "legacy"
        else service._action_fingerprint(original_request, basis)
    )
    action_store.existing = _stored_action(
        original_request, basis, request_fingerprint=fingerprint
    )
    ask_reader = _FakeAskContextService()
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)
    monkeypatch.setattr(
        service,
        "get_committed_playable_revision",
        lambda *_args, **_kwargs: pytest.fail("idempotency hit must not rebind to current Plan basis"),
    )
    fake = _FakeGenerationClient()
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=action_store,
        )
    assert caught.value.code == "action_pending"
    assert fake.requests == []
    assert action_store.reservations == []
    assert action_store.context_calls == []
    assert ask_reader.calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"instruction": "Change the scene in another way."},
        {"draft_markdown": "# A different draft\n", "draft_sha256": _sha("# A different draft\n")},
        {"selected_text": "different local selection"},
        {"base_revision": 3},
        {"base_content_sha256": "e" * 64},
        {"document_id": "another-plan"},
        {"target_kind": "insert_at_caret", "selected_text": ""},
    ],
)
def test_same_key_retry_rejects_changed_typed_intent_before_context_or_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    changes: dict,
) -> None:
    _authority(monkeypatch)
    original = _request()
    basis = service._validate_world_authority(tmp_path, original)
    store = _FakeActionStore()
    store.existing = _stored_action(original, basis)
    ask_reader = _FakeAskContextService()
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)
    fake = _FakeGenerationClient()

    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=_request(
                idempotency_key=str(original.idempotency_key),
                **changes,
            ),
            generation_client=fake,
            model="test-model",
            action_store=store,
        )

    assert caught.value.code == "action_idempotency_conflict"
    assert fake.requests == []
    assert store.reservations == []
    assert store.context_calls == []
    assert ask_reader.calls == []


def test_legacy_caret_receipt_uses_null_selection_digest_and_rejects_nonempty_selection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    original = _request(target_kind="insert_at_caret", selected_text="")
    basis = service._validate_world_authority(tmp_path, original)
    action = _stored_action(
        original,
        basis,
        request_fingerprint=_legacy_action_fingerprint(original, basis),
    )
    store = _FakeActionStore()
    store.existing = action
    fake = _FakeGenerationClient()

    with pytest.raises(service.PlanDocumentEditProposalError) as pending:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=_request(
                idempotency_key=str(original.idempotency_key),
                target_kind="insert_at_caret",
                selected_text="",
            ),
            generation_client=fake,
            model="test-model",
            action_store=store,
        )
    assert pending.value.code == "action_pending"
    assert action.selected_text_sha256 is None

    with pytest.raises(service.PlanDocumentEditProposalError) as conflict:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=_request(
                idempotency_key=str(original.idempotency_key),
                target_kind="insert_at_caret",
                selected_text="not empty",
            ),
            generation_client=fake,
            model="test-model",
            action_store=store,
        )
    assert conflict.value.code == "plan_target_invalid"
    assert fake.requests == []


@pytest.mark.parametrize("race_kind", ["reserve_loser", "legacy_fingerprint_conflict"])
def test_reservation_race_reconciles_typed_receipt_without_reading_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    race_kind: str,
) -> None:
    _authority(monkeypatch)
    request = _request()
    basis = service._validate_world_authority(tmp_path, request)
    fingerprint = (
        _legacy_action_fingerprint(request, basis)
        if race_kind == "legacy_fingerprint_conflict"
        else service._action_fingerprint(request, basis)
    )
    raced_action = _stored_action(request, basis, request_fingerprint=fingerprint)
    store = _FakeActionStore()
    ask_reader = _FakeAskContextService()
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)
    if race_kind == "reserve_loser":
        store.race_action = raced_action
    else:
        store.reserve_error = ApplicationStateConflictError("unique idempotency key")
        store.lookup_results = [None, raced_action]
    fake = _FakeGenerationClient()

    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )

    assert caught.value.code == "action_pending"
    assert fake.requests == []
    assert store.context_calls == []
    assert ask_reader.calls == []


def test_proposal_merges_only_the_latest_six_server_owned_pairs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    request = _request(
        conversation_history=[
            {"role": "user", "content": "CLIENT-POISON-QUESTION"},
            {"role": "assistant", "content": "CLIENT-POISON-ANSWER"},
        ]
    )
    basis = service._validate_world_authority(tmp_path, request)
    origin = datetime(2026, 1, 1, tzinfo=UTC)
    store = _FakeActionStore()
    store.plan_context = [
        _completed_plan_pair(
            basis,
            action_id=UUID(int=100 + sequence),
            sequence=sequence,
            accepted_at=origin + timedelta(seconds=sequence * 2 - 1),
            instruction=f"PLAN-USER-{sequence}",
            summary=f"PLAN-ASSISTANT-{sequence}",
        )
        for sequence in range(1, 5)
    ]
    asks = [
        _completed_ask_pair(
            record_id=UUID(int=200 + sequence),
            sequence=sequence,
            accepted_at=origin + timedelta(seconds=sequence * 2),
            question=f"ASK-USER-{sequence}",
            answer=f"ASK-ASSISTANT-{sequence}",
        )
        for sequence in range(1, 5)
    ]
    ask_reader = _FakeAskContextService(asks)
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)
    fake = _FakeGenerationClient()

    service.propose_world_plan_document_edit(
        root=tmp_path,
        request=request,
        generation_client=fake,
        model="test-model",
        action_store=store,
    )

    context = json.loads(fake.requests[0].user_prompt)
    history = context["conversation_history"]
    assert [(item["role"], item["content"]) for item in history] == [
        ("user", "PLAN-USER-2"),
        ("assistant", "PLAN-ASSISTANT-2"),
        ("user", "ASK-USER-2"),
        ("assistant", "ASK-ASSISTANT-2"),
        ("user", "PLAN-USER-3"),
        ("assistant", "PLAN-ASSISTANT-3"),
        ("user", "ASK-USER-3"),
        ("assistant", "ASK-ASSISTANT-3"),
        ("user", "PLAN-USER-4"),
        ("assistant", "PLAN-ASSISTANT-4"),
        ("user", "ASK-USER-4"),
        ("assistant", "ASK-ASSISTANT-4"),
    ]
    assert "CLIENT-POISON" not in fake.requests[0].user_prompt
    assert store.context_calls == [(basis, 6)]
    assert ask_reader.calls == [("world-1", PlanAskContextBasis.model_validate(
        basis.model_dump(mode="python")
    ), 6)]


def test_server_context_merge_uses_deterministic_ties_and_utc_timestamps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    basis = service._validate_world_authority(tmp_path, _request())
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    store = _FakeActionStore()
    store.plan_context = [
        _completed_plan_pair(
            basis,
            action_id=UUID(int=4),
            sequence=1,
            accepted_at=instant,
            instruction="PLAN-UUID-4",
            summary="PLAN-ANSWER-4",
        ),
        _completed_plan_pair(
            basis,
            action_id=UUID(int=3),
            sequence=1,
            accepted_at=instant,
            instruction="PLAN-UUID-3",
            summary="PLAN-ANSWER-3",
        ),
    ]
    ask_reader = _FakeAskContextService(
        [
            _completed_ask_pair(
                record_id=UUID(int=2),
                sequence=1,
                accepted_at=instant.astimezone(timezone(timedelta(hours=5))),
                question="ASK-UUID-2",
                answer="ASK-ANSWER-2",
            ),
            _completed_ask_pair(
                record_id=UUID(int=1),
                sequence=1,
                accepted_at=instant,
                question="ASK-UUID-1",
                answer="ASK-ANSWER-1",
            ),
        ]
    )
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)

    history = service._server_owned_proposal_history(store, basis)

    assert [item.content for item in history] == [
        "ASK-UUID-1",
        "ASK-ANSWER-1",
        "ASK-UUID-2",
        "ASK-ANSWER-2",
        "PLAN-UUID-3",
        "PLAN-ANSWER-3",
        "PLAN-UUID-4",
        "PLAN-ANSWER-4",
    ]


def test_server_context_bounds_each_visible_message_with_unicode_suffix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    basis = service._validate_world_authority(tmp_path, _request())
    store = _FakeActionStore()
    plan_instruction = "界" * 4_100
    plan_summary = "Ω" * 4_100
    store.plan_context = [
        _completed_plan_pair(
            basis,
            action_id=UUID(int=1),
            sequence=1,
            accepted_at=datetime(2026, 1, 1, tzinfo=UTC),
            instruction=plan_instruction,
            summary=plan_summary,
        )
    ]
    ask_question = "é" * 4_100
    ask_answer = "🜁" * 4_100
    ask_reader = _FakeAskContextService(
        [
            _completed_ask_pair(
                record_id=UUID(int=2),
                sequence=1,
                accepted_at=datetime(2026, 1, 2, tzinfo=UTC),
                question=ask_question,
                answer=ask_answer,
            )
        ]
    )
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)

    history = service._server_owned_proposal_history(store, basis)

    assert len(history) == 4
    for item in history:
        assert len(item.content) == 4_000
        assert item.content.endswith(" …[truncated]")
    assert store.plan_context[0].instruction == plan_instruction
    assert ask_reader.pairs[0].question == ask_question


@pytest.mark.parametrize("failure", ["plan_store", "ask_store", "basis_mismatch"])
def test_context_failure_is_persisted_and_never_calls_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    snapshot = _authority(monkeypatch)
    request = _request()
    basis = service._validate_world_authority(tmp_path, request)
    store = _FakeActionStore()
    ask_reader = _FakeAskContextService()
    if failure == "plan_store":
        store.context_error = RuntimeError("projection unavailable")
        expected_code = "proposal_context_unavailable"
    elif failure == "ask_store":
        ask_reader.error = RuntimeError("projection unavailable")
        expected_code = "proposal_context_unavailable"
    else:
        store.plan_context = [
            _completed_plan_pair(
                basis.model_copy(update={"object_revision": snapshot.object_revision + 1}),
                action_id=UUID(int=1),
                sequence=1,
                accepted_at=datetime(2026, 1, 1, tzinfo=UTC),
                instruction="MISMATCH-USER",
                summary="MISMATCH-ASSISTANT",
            )
        ]
        expected_code = "proposal_context_invalid"
    monkeypatch.setattr(service, "AgentConversationService", lambda: ask_reader)
    fake = _FakeGenerationClient()

    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )

    assert caught.value.code == expected_code
    assert caught.value.status_code == 503
    assert fake.requests == []
    assert store.finished[0]["status"] == "failed"
    assert store.finished[0]["failure_code"] == expected_code


def test_completed_action_can_deliver_late_only_for_its_original_basis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    from threading import Event

    from application_state.plan_action_dialogue.types import PlanActionBasis

    original_snapshot = _authority(monkeypatch)
    request = _request()
    original_basis = PlanActionBasis(
        world_id="world-1",
        document_id="plan-1",
        object_revision=original_snapshot.object_revision,
        work_revision_id=UUID(original_snapshot.work_revision_id),
        revision_n=original_snapshot.revision_n,
        content_sha256=original_snapshot.content_sha256,
    )
    completed = Event()
    release_response = Event()

    class _HoldCompletedResponse(PlanActionDialogueService):
        def finish(self, **kwargs):
            result = super().finish(**kwargs)
            if kwargs["status"] == "completed":
                completed.set()
                if not release_response.wait(timeout=5):
                    raise TimeoutError("test did not release completed proposal response")
            return result

    store = _HoldCompletedResponse()
    fake = _FakeGenerationClient("LATE-REPLACEMENT-SENTINEL")
    executor = ThreadPoolExecutor(max_workers=1)
    future = None
    try:
        future = executor.submit(
            service.propose_world_plan_document_edit,
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )
        assert completed.wait(timeout=5)
        recorded = store.get_by_key(request.world_id, request.idempotency_key)
        assert recorded is not None
        assert recorded.status == "completed"
        assert recorded.basis == original_basis
        assert recorded.lease_expires_at is None

        _authority(monkeypatch, revision=3, saved_markdown="A newer committed Plan.")
        current_projection = service.get_world_plan_action_projection(
            root=tmp_path,
            world_id="world-1",
            document_id="plan-1",
            action_store=store,
        )
        assert current_projection.basis.object_revision == 3
        assert current_projection.actions == []

        release_response.set()
        response = future.result(timeout=5)
        assert response.action_id == recorded.action_id
        assert response.idempotency_key == request.idempotency_key
        assert response.base_revision == original_basis.object_revision
        assert response.base_content_sha256 == original_basis.content_sha256
        assert response.replacement_markdown == "LATE-REPLACEMENT-SENTINEL"
        assert len(fake.requests) == 1
    finally:
        release_response.set()
        if future is not None:
            future.result(timeout=5)
        executor.shutdown(wait=True, cancel_futures=True)


def test_persistence_uncertainty_never_returns_uncommitted_proposal_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    _authority(monkeypatch)

    class _CommitThenLoseReceipt(PlanActionDialogueService):
        def finish(self, **kwargs):
            result = super().finish(**kwargs)
            if kwargs["status"] == "completed":
                raise OSError("test simulates a lost persistence acknowledgement")
            return result

    store = _CommitThenLoseReceipt()
    fake = _FakeGenerationClient("UNRETURNED-REPLACEMENT-SENTINEL")
    request = _request()
    with pytest.raises(service.PlanDocumentEditProposalError) as caught:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=fake,
            model="test-model",
            action_store=store,
        )
    assert caught.value.code == "action_persistence_uncertain"
    assert caught.value.status_code == 503
    assert len(fake.requests) == 1

    recorded = store.get_by_key(request.world_id, request.idempotency_key)
    assert recorded is not None
    assert recorded.status == "completed"
    assert recorded.assistant_summary == "Add a tense beat"
    assert recorded.assistant_summary != "UNRETURNED-REPLACEMENT-SENTINEL"
    assert store.completed_context(recorded.basis)[0].assistant_summary == "Add a tense beat"
    retry_fake = _FakeGenerationClient()
    with pytest.raises(service.PlanDocumentEditProposalError) as retry:
        service.propose_world_plan_document_edit(
            root=tmp_path,
            request=request,
            generation_client=retry_fake,
            model="test-model",
            action_store=store,
        )
    assert retry.value.code == "action_already_completed"
    assert retry_fake.requests == []


def test_world_replacement_prompt_allows_only_echoing_existing_protected_tokens(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marker = "<!-- dmb-playable-element:v2 kind=scene id=scene:town-breathes -->"
    link = "[Lysandra Ironveil](dmb-node:node:captain-lysandra-ironveil)"
    section = f"{marker}\n### Mireward After the Attack\n\n{link} is present.\n"
    _authority(monkeypatch)
    fake = _FakeGenerationClient(section)
    action_store = _FakeActionStore()
    result = service.propose_world_plan_document_edit(
        root=tmp_path,
        request=_request(draft_markdown=section, draft_sha256=_sha(section), selected_text=section),
        generation_client=fake,
        model="test-model",
        action_store=action_store,
    )

    assert result.replacement_markdown == section.strip()
    prompt = fake.requests[0].system_prompt
    assert "For this World replace-selection request only" in prompt
    assert "exact original spelling" in prompt
    assert "Never invent, change, remove, reorder, duplicate" in prompt
    assert "graph identities or graph truth" in prompt
    context = json.loads(fake.requests[0].user_prompt)
    assert context["selected_text"] == section
    assert context["current_plan_markdown"] == section


def test_world_caret_prompt_keeps_the_restricted_shared_grammar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _authority(monkeypatch)
    fake = _FakeGenerationClient()
    service.propose_world_plan_document_edit(
        root=tmp_path,
        request=_request(target_kind="insert_at_caret", selected_text=""),
        generation_client=fake,
        model="test-model",
        action_store=_FakeActionStore(),
    )

    assert fake.requests[0].system_prompt == service._SYSTEM_PROMPT
    normalized_prompt = " ".join(fake.requests[0].system_prompt.split())
    assert "Do not produce HTML, graph node IDs, file paths, or unknown component markers." in normalized_prompt


def _client(monkeypatch: pytest.MonkeyPatch, root: Path) -> TestClient:
    monkeypatch.setattr(workspace_documents, "repo_root", lambda: root)
    monkeypatch.setattr(live, "repo_root", lambda: root)
    app = FastAPI()
    app.include_router(workspace_documents.router)
    app.include_router(live.router)
    return TestClient(app)


def _create_saved_world_plan(
    client: TestClient, world_id: str, *, title: str, markdown: str
) -> tuple[str, dict]:
    created = client.post(
        "/api/live/workspace-documents/world-plans",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world_id,
            "title": title,
        },
    )
    assert created.status_code == 200, created.text
    document_id = created.json()["document_id"]
    prepared = client.post(
        "/api/live/tiptap/markdown-write/prepare",
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world_id,
            "document_id": document_id,
            "markdown": markdown,
            "expected_revision": created.json()["revision"],
        },
    )
    assert prepared.status_code == 200, prepared.text
    committed = client.post(
        "/api/live/tiptap/markdown-write/commit",
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world_id,
            "document_id": document_id,
            "markdown": markdown,
            "expected_revision": prepared.json()["registry_revision"],
            "writer_confirm_token": prepared.json()["writer_confirm_token"],
        },
    )
    assert committed.status_code == 200, committed.text
    saved = client.get(f"/api/live/workspace-documents/{document_id}/snapshot")
    assert saved.status_code == 200, saved.text
    return document_id, saved.json()


def _seed_completed_proposal_context(
    application_state_dsn: str, basis: PlanActionBasis
) -> None:
    plan_store = PlanActionDialogueService()
    action, created = plan_store.reserve(
        PlanActionReservation(
            idempotency_key=uuid4(),
            request_fingerprint="a" * 64,
            action_type="revise",
            basis=basis,
            draft_matches_basis=True,
            draft_sha256=basis.content_sha256,
            target_kind="replace_selection",
            selected_text_sha256=_sha("Saved passage"),
            instruction="SERVER-PLAN-USER-SENTINEL",
        )
    )
    assert created
    plan_store.finish(
        action_id=action.action_id,
        token=action.dispatch_token,
        fence=action.fence,
        status="completed",
        summary="SERVER-PLAN-ASSISTANT-SENTINEL",
    )

    ask_basis = PlanAskContextBasis.model_validate(basis.model_dump(mode="python"))
    ask = AgentConversationService()
    conversation = ask.new_conversation(
        ConversationCommand(
            world_id=basis.world_id,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )
    plan_reference = HistoricalReference(
        resolution="resolved",
        kind="plan",
        object_id=ask_basis.document_id,
        content_sha256=ask_basis.content_sha256,
        object_revision=ask_basis.object_revision,
        work_revision_id=ask_basis.work_revision_id,
        revision_n=ask_basis.revision_n,
    )
    provenance = TurnProvenance(
        world_id=basis.world_id,
        surface_resolution="resolved",
        surface_id="plan",
        primary_work=plan_reference,
        selected_object=HistoricalReference(resolution="absent"),
    )
    question = "SERVER-ASK-USER-SENTINEL"
    intent = SubmittedTurnIntentV1(
        world_id=basis.world_id,
        client_thread_id="world-plan-proposal-test",
        message=question,
        surface_id="plan",
        surface_instance_id="world-plan-proposal-test-pane",
        client_work_state="saved_clean",
        primary_work=SubmittedPrimaryWorkIntentV1(
            kind="plan",
            object_id=ask_basis.document_id,
            expected_revision=ask_basis.object_revision,
            expected_revision_n=ask_basis.revision_n,
            expected_content_sha256=ask_basis.content_sha256,
        ),
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    turn = ask.accept_turn(
        TurnSubmission(
            world_id=basis.world_id,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=1,
            user_text=question,
            provenance=provenance,
            submitted_intent_v1=intent,
        )
    )
    claimed = ask.begin_turn(
        basis.world_id,
        conversation.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
    )
    ask.complete_turn(
        TurnResult(
            world_id=basis.world_id,
            conversation_id=conversation.conversation_id,
            turn_id=turn.turn_id,
            expected_revision=claimed.revision,
            assistant_text="SERVER-ASK-ASSISTANT-SENTINEL",
        )
    )

    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET accepted_at = %s WHERE action_id = %s",
            (datetime(2026, 1, 1, tzinfo=UTC), action.action_id),
        )
        conn.execute(
            "UPDATE agent.turn SET accepted_at = %s WHERE turn_id = %s",
            (datetime(2026, 1, 2, tzinfo=UTC), turn.turn_id),
        )


def test_world_plan_route_uses_real_saved_world_plan_and_never_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    world = create_world_container(tmp_path, name="Reviewed Apply route world")
    client = _client(monkeypatch, tmp_path)
    created = client.post(
        "/api/live/workspace-documents/world-plans",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "title": "Reviewed Plan",
        },
    )
    assert created.status_code == 200
    record = created.json()
    document_id = record["document_id"]
    committed_markdown = "# Saved server-only prose\n"
    prepared = client.post(
        "/api/live/tiptap/markdown-write/prepare",
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": record["revision"],
        },
    )
    assert prepared.status_code == 200
    commit_fields = prepared.json()
    committed = client.post(
        "/api/live/tiptap/markdown-write/commit",
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": commit_fields["registry_revision"],
            "writer_confirm_token": commit_fields["writer_confirm_token"],
        },
    )
    assert committed.status_code == 200
    saved_before = client.get(f"/api/live/workspace-documents/{document_id}/snapshot").json()
    draft = "# Explicit unsaved editor draft\n"

    fake = _FakeGenerationClient()
    monkeypatch.setattr(service, "_resolve_model", lambda: "test-model")
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: fake)
    request = {
        "idempotency_key": str(uuid4()),
        "document_id": document_id,
        "world_id": world.world_id,
        "base_revision": saved_before["loaded_revision"],
        "base_content_sha256": saved_before["content_sha256"],
        "draft_markdown": draft,
        "draft_sha256": _sha(draft),
        "target_kind": "insert_at_caret",
        "selected_text": "",
        "instruction": "Add a tense opening.",
        "conversation_history": [
            {"role": "user", "content": "CLIENT-POISON-USER-SENTINEL"},
            {"role": "assistant", "content": "CLIENT-POISON-ASSISTANT-SENTINEL"},
        ],
    }
    typed_request = WorldPlanDocumentEditProposalRequest.model_validate(request)
    resolved_basis = service._validate_world_authority(tmp_path, typed_request)
    _seed_completed_proposal_context(application_state_dsn, resolved_basis)
    response = client.post("/api/live/world-plan-edit/propose", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["schema_version"] == "dmb_world_plan_document_edit_proposal_v1"
    assert response.json()["world_id"] == world.world_id
    assert response.json()["document_id"] == document_id
    assert response.json()["idempotency_key"] == request["idempotency_key"]
    assert "session" not in response.json()
    assert len(fake.requests) == 1
    assert "Explicit unsaved editor draft" in fake.requests[0].user_prompt
    assert "Saved server-only prose" not in fake.requests[0].user_prompt
    prompt_context = json.loads(fake.requests[0].user_prompt)
    assert prompt_context["conversation_history"] == [
        {"role": "user", "content": "SERVER-PLAN-USER-SENTINEL"},
        {"role": "assistant", "content": "SERVER-PLAN-ASSISTANT-SENTINEL"},
        {"role": "user", "content": "SERVER-ASK-USER-SENTINEL"},
        {"role": "assistant", "content": "SERVER-ASK-ASSISTANT-SENTINEL"},
    ]
    assert "CLIENT-POISON" not in fake.requests[0].user_prompt

    retry = client.post("/api/live/world-plan-edit/propose", json=request)
    assert retry.status_code == 409
    assert "replacement_markdown" not in retry.json()
    assert len(fake.requests) == 1
    conflicting_retry = client.post(
        "/api/live/world-plan-edit/propose",
        json={**request, "instruction": "Use the same key for different intent."},
    )
    assert conflicting_retry.status_code == 409
    assert conflicting_retry.json()["detail"]["code"] == "action_idempotency_conflict"
    assert len(fake.requests) == 1
    actions = client.get(
        "/api/live/world-plan-edit/actions",
        params={"world_id": world.world_id, "document_id": document_id},
    )
    assert actions.status_code == 200
    proposal_action = next(
        item
        for item in actions.json()["actions"]
        if item["action_id"] == response.json()["action_id"]
    )
    assert proposal_action["status"] == "completed"
    assert proposal_action["assistant_summary"] == response.json()["summary"]
    assert "draft_sha256" not in json.dumps(actions.json())
    assert "replacement_markdown" not in json.dumps(actions.json())

    rejected = client.post("/api/live/world-plan-edit/propose", json={**request, "session": 1})
    assert rejected.status_code == 422
    assert len(fake.requests) == 1
    saved_after = client.get(f"/api/live/workspace-documents/{document_id}/snapshot").json()
    assert saved_after["loaded_revision"] == saved_before["loaded_revision"]
    assert saved_after["content_sha256"] == saved_before["content_sha256"]
    assert saved_after["markdown"] == committed_markdown


def test_late_provider_result_loses_expired_action_fence_without_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    world = create_world_container(tmp_path, name="Late Plan action world")
    client = _client(monkeypatch, tmp_path)
    created = client.post(
        "/api/live/workspace-documents/world-plans",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "title": "Late Plan",
        },
    )
    assert created.status_code == 200
    document_id = created.json()["document_id"]
    committed_markdown = "# The saved Plan\n"
    prepared = client.post(
        "/api/live/tiptap/markdown-write/prepare",
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": created.json()["revision"],
        },
    )
    assert prepared.status_code == 200
    prepared_body = prepared.json()
    committed = client.post(
        "/api/live/tiptap/markdown-write/commit",
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": committed_markdown,
            "expected_revision": prepared_body["registry_revision"],
            "writer_confirm_token": prepared_body["writer_confirm_token"],
        },
    )
    assert committed.status_code == 200
    saved = client.get(f"/api/live/workspace-documents/{document_id}/snapshot").json()

    entered = Event()
    release = Event()

    class _BlockingGenerationClient:
        def __init__(self) -> None:
            self.calls = 0
            self.reservation_seen = False

        async def generate_structured(self, generation_request):
            self.calls += 1
            with psycopg.connect(application_state_dsn) as conn:
                row = conn.execute(
                    "SELECT status, dispatch_token, lease_expires_at FROM plan_action.action WHERE world_id = %s AND idempotency_key = %s",
                    (request["world_id"], request["idempotency_key"]),
                ).fetchone()
            self.reservation_seen = bool(row and row[0] == "pending" and row[1] and row[2])
            entered.set()
            if not release.wait(timeout=8):
                raise TimeoutError("test did not release blocked generation")
            return SimpleNamespace(
                parsed={
                    "replacement_markdown": "STALE-REPLACEMENT-SENTINEL",
                    "summary": "STALE-SUMMARY-SENTINEL",
                    "assumptions": [],
                    "cannot_complete_reason": None,
                },
                observation=SimpleNamespace(
                    response_model="observed-test-model",
                    resolved_model="test-model",
                    latency_ms=1,
                    input_tokens=1,
                    output_tokens=1,
                ),
            )

    fake = _BlockingGenerationClient()
    monkeypatch.setattr(service, "_resolve_model", lambda: "test-model")
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: fake)
    draft = "# Mounted Plan draft\n"
    request = {
        "idempotency_key": str(uuid4()),
        "document_id": document_id,
        "world_id": world.world_id,
        "base_revision": saved["loaded_revision"],
        "base_content_sha256": saved["content_sha256"],
        "draft_markdown": draft,
        "draft_sha256": _sha(draft),
        "target_kind": "insert_at_caret",
        "selected_text": "",
        "instruction": "Add a distant bell.",
        "conversation_history": [],
    }

    executor = ThreadPoolExecutor(max_workers=1)
    future = None
    try:
        future = executor.submit(client.post, "/api/live/world-plan-edit/propose", json=request)
        assert entered.wait(timeout=5)
        assert fake.calls == 1
        assert fake.reservation_seen

        duplicate = client.post("/api/live/world-plan-edit/propose", json=request)
        assert duplicate.status_code == 409
        assert fake.calls == 1

        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                "UPDATE plan_action.action SET lease_expires_at = clock_timestamp() - interval '1 second' WHERE world_id = %s AND idempotency_key = %s",
                (request["world_id"], request["idempotency_key"]),
            )
        status_page = client.get(
            "/api/live/world-plan-edit/actions",
            params={"world_id": world.world_id, "document_id": document_id},
        )
        assert status_page.status_code == 200
        action = status_page.json()["actions"][0]
        assert action["status"] == "indeterminate"
        assert action["assistant_summary"] is None
        retry = client.post("/api/live/world-plan-edit/propose", json=request)
        assert retry.status_code == 409
        assert fake.calls == 1

        release.set()
        original = future.result(timeout=8)
        assert original.status_code == 409
        original_text = original.text
        assert "STALE-REPLACEMENT-SENTINEL" not in original_text
        assert "STALE-SUMMARY-SENTINEL" not in original_text
        assert "replacement_markdown" not in original_text
        final_page = client.get(
            "/api/live/world-plan-edit/actions",
            params={"world_id": world.world_id, "document_id": document_id},
        )
        assert final_page.json()["actions"][0]["status"] == "indeterminate"
        assert "STALE-SUMMARY-SENTINEL" not in json.dumps(final_page.json())
        with psycopg.connect(application_state_dsn) as conn:
            status, summary, fence = conn.execute(
                "SELECT status, assistant_summary, fence FROM plan_action.action WHERE world_id = %s AND idempotency_key = %s",
                (request["world_id"], request["idempotency_key"]),
            ).fetchone()
        assert status == "indeterminate"
        assert summary is None
        assert fence == 2
        assert fake.calls == 1
    finally:
        release.set()
        if future is not None:
            future.result(timeout=8)
        executor.shutdown(wait=True, cancel_futures=True)


def test_same_key_is_world_scoped_and_foreign_retry_leaves_expired_action_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    world_a = create_world_container(tmp_path, name="Idempotency World A")
    world_b = create_world_container(tmp_path, name="Idempotency World B")
    client = _client(monkeypatch, tmp_path)
    document_a, saved_a = _create_saved_world_plan(
        client, world_a.world_id, title="Plan A", markdown="# Plan A\n"
    )
    document_b, saved_b = _create_saved_world_plan(
        client, world_b.world_id, title="Plan B", markdown="# Plan B\n"
    )

    first_entered = Event()
    release_first = Event()

    class _TwoWorldGenerationClient:
        def __init__(self) -> None:
            self.calls = 0
            self.lock = Lock()

        async def generate_structured(self, _generation_request):
            with self.lock:
                self.calls += 1
                call_number = self.calls
            if call_number == 1:
                first_entered.set()
                if not release_first.wait(timeout=15):
                    raise TimeoutError("test did not release World A generation")
            return SimpleNamespace(
                parsed={
                    "replacement_markdown": f"Proposal {call_number}",
                    "summary": f"World {call_number} proposal summary",
                    "assumptions": [],
                    "cannot_complete_reason": None,
                },
                observation=SimpleNamespace(
                    response_model="observed-test-model",
                    resolved_model="test-model",
                    latency_ms=1,
                    input_tokens=1,
                    output_tokens=1,
                ),
            )

    fake = _TwoWorldGenerationClient()
    monkeypatch.setattr(service, "_resolve_model", lambda: "test-model")
    monkeypatch.setattr(service.GenerationClient, "from_env", lambda: fake)
    key = str(uuid4())

    def request(world_id: str, document_id: str, saved: dict, *, instruction: str, draft: str) -> dict:
        return {
            "idempotency_key": key,
            "document_id": document_id,
            "world_id": world_id,
            "base_revision": saved["loaded_revision"],
            "base_content_sha256": saved["content_sha256"],
            "draft_markdown": draft,
            "draft_sha256": _sha(draft),
            "target_kind": "insert_at_caret",
            "selected_text": "",
            "instruction": instruction,
            "conversation_history": [],
        }

    request_a = request(
        world_a.world_id, document_a, saved_a,
        instruction="Add a signal to Plan A.", draft="# Plan A draft\n",
    )
    request_b = request(
        world_b.world_id, document_b, saved_b,
        instruction="Add a signal to Plan B.", draft="# Plan B draft\n",
    )

    executor = ThreadPoolExecutor(max_workers=1)
    future = None
    try:
        future = executor.submit(
            client.post, "/api/live/world-plan-edit/propose", json=request_a
        )
        assert first_entered.wait(timeout=5)
        assert fake.calls == 1

        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                "UPDATE plan_action.action SET lease_expires_at = clock_timestamp() - interval '1 second' "
                "WHERE world_id = %s AND idempotency_key = %s",
                (world_a.world_id, key),
            )

        response_b = client.post("/api/live/world-plan-edit/propose", json=request_b)
        assert response_b.status_code == 200, response_b.text
        assert response_b.json()["idempotency_key"] == key
        assert fake.calls == 2

        with psycopg.connect(application_state_dsn) as conn:
            rows = conn.execute(
                "SELECT world_id, status, fence, assistant_summary, "
                "lease_expires_at <= clock_timestamp() AS expired "
                "FROM plan_action.action WHERE idempotency_key = %s",
                (key,),
            ).fetchall()
        by_world = {row[0]: row[1:] for row in rows}
        assert set(by_world) == {world_a.world_id, world_b.world_id}
        assert by_world[world_a.world_id][0] == "pending"
        assert by_world[world_a.world_id][1] == 1
        assert by_world[world_a.world_id][3] is True
        assert by_world[world_b.world_id][0] == "completed"
        assert by_world[world_b.world_id][1] == 1
        assert by_world[world_b.world_id][2] == response_b.json()["summary"]

        release_first.set()
        response_a = future.result(timeout=20)
        assert response_a.status_code == 409
        assert "replacement_markdown" not in response_a.text
        assert "Proposal 1" not in response_a.text

        with psycopg.connect(application_state_dsn) as conn:
            rows = conn.execute(
                "SELECT world_id, status, fence, assistant_summary "
                "FROM plan_action.action WHERE idempotency_key = %s",
                (key,),
            ).fetchall()
        by_world = {row[0]: row[1:] for row in rows}
        assert by_world[world_a.world_id] == ("indeterminate", 2, None)
        assert by_world[world_b.world_id] == (
            "completed", 1, response_b.json()["summary"]
        )
    finally:
        release_first.set()
        if future is not None:
            future.result(timeout=20)
        executor.shutdown(wait=True, cancel_futures=True)
