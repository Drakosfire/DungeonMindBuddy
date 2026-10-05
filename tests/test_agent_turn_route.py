from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from types import SimpleNamespace

from fastapi import FastAPI
import httpx
import pytest

from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.routes.live import router as live_router
from apps.live_control_server.services.agent_runtime import (
    AgentRuntimeDescriptor,
    AgentRuntimeResult,
)
from application_state.agent_conversation.types import (
    HistoricalReference,
    Turn,
    TurnClaimReceipt,
    TurnFailure,
    TurnProvenance,
    TurnSubmission,
)
from uuid import uuid4


class FakeRuntime:
    descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

    def __init__(self) -> None:
        self.invocations: list[Any] = []

    def run(self, invocation: Any) -> AgentRuntimeResult:
        self.invocations.append(invocation)
        return AgentRuntimeResult(
            status="ok", final_text="A simple answer.", runtime_session_id="runtime-1"
        )


def _payload() -> dict[str, Any]:
    return {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "thread-no-scope",
        "turn_id": "turn-no-scope",
        "surface": {"surface_id": "index", "instance_id": "index-home"},
        "owner_scope": None,
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": "What can you help me with?",
    }


def test_auto_plan_world_request_requires_exact_saved_world_plan_pin() -> None:
    payload = _payload()
    payload.update(
        {
            "surface": {"surface_id": "plan", "instance_id": "plan-main"},
            "owner_scope": {"kind": "world", "world_id": "managed-world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 7,
                "expected_revision_n": 3,
                "expected_content_sha256": "a" * 64,
            },
            "client_work_state": "saved_dirty",
            "plan_context_policy": {
                "schema": "dmb_plan_context_policy_v1",
                "policy": "auto_plan_world",
            },
        }
    )

    parsed = AgentTurnRequest.model_validate(payload)
    assert parsed.plan_context_policy is not None
    assert parsed.plan_context_policy.policy == "auto_plan_world"

    invalid = dict(payload)
    invalid["primary_work"] = {
        "kind": "plan",
        "object_id": "plan-1",
        "expected_revision": 7,
    }
    with pytest.raises(ValueError, match="auto_plan_world"):
        AgentTurnRequest.model_validate(invalid)


def test_auto_plan_world_rejects_generic_graph_reads_and_non_plan_surface() -> None:
    payload = _payload()
    payload.update(
        {
            "surface": {"surface_id": "plan", "instance_id": "plan-main"},
            "owner_scope": {"kind": "world", "world_id": "managed-world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 7,
                "expected_revision_n": 3,
                "expected_content_sha256": "a" * 64,
            },
            "client_work_state": "saved_clean",
            "plan_context_policy": {"policy": "auto_plan_world"},
            "graph_request": {
                "mode": "world",
                "world_id": "native-world-1",
                "campaign_id": None,
                "revision_pin": None,
                "focus": {"kind": "none", "session_id": None, "campaign_id": None},
            },
        }
    )
    with pytest.raises(ValueError, match="auto_plan_world"):
        AgentTurnRequest.model_validate(payload)


def _durable_turn(
    *,
    world_id: str,
    status: str,
    provenance: TurnProvenance | None = None,
    revision: int = 1,
    assistant_text: str | None = None,
) -> Turn:
    now = datetime.now(UTC)
    return Turn(
        turn_id=uuid4(),
        conversation_id=uuid4(),
        world_id=world_id,
        idempotency_key=uuid4(),
        sequence=1,
        revision=revision,
        status=status,
        user_text="What can you help me with?",
        assistant_text=assistant_text,
        failure_code=None,
        provenance=provenance
        or TurnProvenance(
            world_id=world_id,
            surface_resolution="resolved",
            surface_id="index",
            primary_work=HistoricalReference(resolution="absent"),
            selected_object=HistoricalReference(resolution="absent"),
        ),
        submitted_intent_fingerprint_v1=None,
        attempt=1 if status in {"running", "completed"} else 0,
        claim_expires_at=None,
        accepted_at=now,
        completed_at=now if status == "completed" else None,
        updated_at=now,
    )


@pytest.fixture(autouse=True)
def _authorize_route_execution(monkeypatch: Any) -> None:
    """Keep these route behavior tests independent of local auth setup."""
    from apps.live_control_server.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", lambda _request: None)
    monkeypatch.setattr(agent_route, "_conversation_service", lambda _request: None)


def test_no_scope_route_does_not_load_packet_and_registers_exactly_once(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.routes import live as live_route

    runtime = FakeRuntime()
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "session-dir")
    monkeypatch.setattr(agent_route, "_owner_resolver", lambda _body: None)
    monkeypatch.setattr(agent_route, "_work_resolver", lambda _body, _owner: None)

    def forbidden_packet_load(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("generic no-scope route loaded a live session packet")

    monkeypatch.setattr(live_route, "load_session", forbidden_packet_load)
    app = FastAPI()
    app.include_router(live_router)
    app.state.agent_turn_runtime = runtime
    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/live/agent/turn"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(matches) == 1
    legacy_matches = [
        route
        for route in live_router.routes
        if getattr(route, "path", None) == "/api/live/query"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(legacy_matches) == 1
    response = agent_route.post_agent_turn(
        AgentTurnRequest.model_validate(_payload()),
        SimpleNamespace(app=app),
    )
    body = response
    assert body["answer"]["text"] == "A simple answer."
    assert body["answer"]["graph_grounded"] is False
    assert body["graph"]["status"] == "not_requested"
    assert len(runtime.invocations) == 1
    assert runtime.invocations[0].context_packet.world_scope is None
    assert runtime.invocations[0].context_packet.retrieval_session is None
    assert (tmp_path / "session-dir" / "hermes_thread_pointers.json").is_file()


def test_graph_auth_denial_precedes_world_receipt_reconciliation(
    monkeypatch: Any,
) -> None:
    from fastapi import HTTPException

    from apps.live_control_server.routes import agent as agent_route

    class ReceiptSpy:
        called = False

        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Any:
            self.called = True
            raise AssertionError("denied Graph request reached receipt reconciliation")

    receipt_spy = ReceiptSpy()

    def deny(_request: Any) -> Any:
        raise HTTPException(status_code=403, detail="denied")

    monkeypatch.setattr(agent_route, "enforce_native_graph_gm", deny)
    body = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "owner_scope": {"kind": "world", "world_id": "world-auth-test"},
        }
    )
    app = SimpleNamespace(
        state=SimpleNamespace(agent_conversation_service=receipt_spy)
    )

    with pytest.raises(HTTPException) as exc_info:
        agent_route.post_agent_turn(body, SimpleNamespace(app=app))

    assert exc_info.value.status_code == 403
    assert receipt_spy.called is False


def test_unverified_world_is_rejected_before_turn_receipt_reconciliation(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
        execute_agent_turn,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    class ReceiptSpy:
        called = False

        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Any:
            self.called = True
            raise AssertionError("unverified World reached receipt reconciliation")

    receipt_spy = ReceiptSpy()
    body = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "owner_scope": {"kind": "world", "world_id": "submitted-world"},
        }
    )
    with pytest.raises(AgentTurnServiceError) as exc_info:
        execute_agent_turn(
            body,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "sessions"),
            owner_resolver=lambda _body: {"kind": "world", "id": "other-world"},
            work_resolver=lambda *_args: pytest.fail("World denial resolved work"),
            graph_resolver=lambda *_args: pytest.fail("no Graph was requested"),
            runtime_factory=lambda: pytest.fail("World denial loaded runtime"),
            conversation_service=receipt_spy,
        )

    assert exc_info.value.code == "world_owner_unverified"
    assert exc_info.value.status_code == 403
    assert receipt_spy.called is False


def test_legacy_receipt_conflict_does_not_load_runtime_or_resolve_work(
    tmp_path: Path,
) -> None:
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
        execute_agent_turn,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    class LegacyReceipt:
        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Any:
            raise ApplicationStateConflictError(
                "legacy-receipt-unverifiable: stored receipt has no v1 digest"
            )

    body = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "owner_scope": {"kind": "world", "world_id": "world-legacy-test"},
        }
    )
    with pytest.raises(AgentTurnServiceError) as exc_info:
        execute_agent_turn(
            body,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "sessions"),
            owner_resolver=lambda _body: {"kind": "world", "id": "world-legacy-test"},
            work_resolver=lambda *_args: pytest.fail("legacy receipt resolved work"),
            graph_resolver=lambda *_args: pytest.fail("no Graph was requested"),
            runtime_factory=lambda: pytest.fail("legacy receipt loaded runtime"),
            conversation_service=LegacyReceipt(),
        )

    assert exc_info.value.code == "turn_receipt_unverifiable"
    assert exc_info.value.status_code == 409


def test_completed_graph_receipt_replays_frozen_snapshot_projection(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.agent_turn_service import execute_agent_turn
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    world_id = "world-replay-test"
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="index",
        primary_work=HistoricalReference(resolution="absent"),
        supporting_work=[
            HistoricalReference(
                resolution="resolved",
                kind="world_graph_revision",
                object_id=world_id,
                revision="graph-revision-7",
            )
        ],
        selected_object=HistoricalReference(
            resolution="resolved",
            kind="character",
            object_id="node-42",
            revision="graph-revision-7",
        ),
    )
    completed = _durable_turn(
        world_id=world_id,
        status="completed",
        provenance=provenance,
        revision=2,
        assistant_text="The stored answer.",
    )

    class ReceiptService:
        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Turn:
            return completed

    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": world_id},
        "graph_request": {
            "mode": "world",
            "world_id": world_id,
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
        "graph_selection": {"node_id": "node-42"},
    }
    response = execute_agent_turn(
        AgentTurnRequest.model_validate(payload),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "sessions"),
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": world_id,
            "name": "Replay World",
        },
        work_resolver=lambda *_args: pytest.fail("replay resolved current work"),
        graph_resolver=lambda *_args: pytest.fail("replay re-ran Graph retrieval"),
        runtime_factory=lambda: pytest.fail("replay loaded provider runtime"),
        conversation_service=ReceiptService(),
    )

    assert response.answer.text == "The stored answer."
    assert response.primary_work.content_basis is None
    assert response.graph.status == "replayed"
    assert response.graph.world_id == world_id
    assert response.graph.scope_mode == "world"
    assert response.graph.revision_id == "graph-revision-7"
    assert response.graph.selection_found is True
    assert response.graph.head_revision_id is None
    assert response.graph.is_head is None


def test_graph_provenance_persists_actual_snapshot_and_selected_node() -> None:
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.agent_turn_service import (
        _conversation_provenance,
    )

    world_id = "world-graph-provenance-test"
    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": world_id},
        "graph_request": {
            "mode": "world",
            "world_id": world_id,
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
        "graph_selection": {"node_id": "node-42"},
    }
    request = AgentTurnRequest.model_validate(payload)
    provenance = _conversation_provenance(
        request,
        world_id=world_id,
        work=None,
        graph_scope=AgentWorldScope(
            world_id=world_id,
            campaign_id="",
            focus={"kind": "none", "session_id": None, "campaign_id": None},
            admissibility="gm",
            revision_id="snapshot-a",
            scope_mode="world",
        ),
        graph_envelope={
            "revision_id": "snapshot-a",
            "nodes": [{"node_id": "node-42", "kind": "character"}],
        },
    )

    assert provenance.supporting_work[0].kind == "world_graph_revision"
    assert provenance.supporting_work[0].object_id == world_id
    assert provenance.supporting_work[0].revision == "snapshot-a"
    assert provenance.selected_object.kind == "character"
    assert provenance.selected_object.object_id == "node-42"
    assert provenance.selected_object.revision == "snapshot-a"


def test_historical_plan_retry_loads_exact_work_revision(
    monkeypatch: Any,
) -> None:
    from apps.live_control_server.routes import agent as agent_route

    world_id = "world-historical-plan-test"
    document_id = str(uuid4())
    work_revision_id = uuid4()
    digest = "a" * 64
    payload = {
        **_payload(),
        "surface": {"surface_id": "plan", "instance_id": "plan-main"},
        "owner_scope": {"kind": "world", "world_id": world_id},
        "primary_work": {
            "kind": "plan",
            "object_id": document_id,
            "expected_revision": 7,
            "expected_revision_n": 4,
            "expected_content_sha256": digest,
        },
        "client_work_state": "saved_dirty",
    }
    request = AgentTurnRequest.model_validate(payload)
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="plan",
        primary_work=HistoricalReference(
            resolution="resolved",
            kind="plan",
            object_id=document_id,
            revision="7",
            content_sha256=digest,
            object_revision=7,
            work_revision_id=work_revision_id,
            revision_n=4,
        ),
        selected_object=HistoricalReference(resolution="absent"),
    )
    calls: list[dict[str, Any]] = []

    def exact_revision(actual_id: str, **kwargs: Any) -> Any:
        calls.append({"document_id": actual_id, **kwargs})
        return SimpleNamespace(
            document_id=actual_id,
            work_revision_id=str(work_revision_id),
            revision_n=4,
            content_sha256=digest,
            world_id=world_id,
            target_session=None,
            campaign_id=None,
            markdown="# Historical Plan",
        )

    monkeypatch.setattr(agent_route, "get_committed_playable_revision", exact_revision)
    resolved = agent_route._historical_work_resolver(
        request, {"kind": "world", "id": world_id}, provenance
    )

    assert calls == [
        {
            "document_id": document_id,
            "revision_n": 4,
            "expected_sha256": digest,
            "kind": "plan",
            "expected_world_id": world_id,
        }
    ]
    assert resolved is not None
    assert resolved.revision == 7
    assert resolved.plan_markdown == "# Historical Plan"
    assert resolved.content_basis is None


def test_world_turn_claim_pending_does_not_dispatch_provider(tmp_path: Path) -> None:
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
        execute_agent_turn,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    world_id = "world-pending-test"
    running = _durable_turn(world_id=world_id, status="running", revision=2)

    class ReceiptService:
        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Turn:
            return running

        def claim_turn(self, *_args: Any, **_kwargs: Any) -> TurnClaimReceipt:
            return TurnClaimReceipt(disposition="pending", turn=running)

    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": world_id},
    }
    with pytest.raises(AgentTurnServiceError) as exc_info:
        execute_agent_turn(
            AgentTurnRequest.model_validate(payload),
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "sessions"),
            owner_resolver=lambda _request: {"kind": "world", "id": world_id},
            work_resolver=lambda *_args: None,
            graph_resolver=lambda *_args: pytest.fail("no Graph requested"),
            runtime_factory=lambda: pytest.fail("pending turn loaded runtime"),
            conversation_service=ReceiptService(),
        )

    assert exc_info.value.code == "turn_already_running"
    assert exc_info.value.status_code == 409


def test_retry_graph_resolution_is_pinned_to_stored_snapshot(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.services import agent_turn_service
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    world_id = "world-pinned-retry-test"
    provenance = TurnProvenance(
        world_id=world_id,
        surface_resolution="resolved",
        surface_id="index",
        primary_work=HistoricalReference(resolution="absent"),
        supporting_work=[
            HistoricalReference(
                resolution="resolved",
                kind="world_graph_revision",
                object_id=world_id,
                revision="snapshot-frozen-8",
            )
        ],
        selected_object=HistoricalReference(resolution="absent"),
    )
    accepted = _durable_turn(
        world_id=world_id, status="accepted", provenance=provenance
    )
    resolved_pins: list[str | None] = []

    class ReceiptService:
        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Turn:
            return accepted

        def claim_turn(self, *_args: Any, **_kwargs: Any) -> TurnClaimReceipt:
            return TurnClaimReceipt(
                disposition="pending",
                turn=accepted.model_copy(update={"status": "running"}),
            )

    def resolve_graph(request: AgentTurnRequest, *_args: Any) -> tuple[dict[str, Any], AgentWorldScope]:
        resolved_pins.append(request.graph_request.revision_pin)
        return (
            {"status": "ready", "revision_id": "snapshot-frozen-8", "nodes": []},
            AgentWorldScope(
                world_id=world_id,
                campaign_id="",
                focus={"kind": "none", "session_id": None, "campaign_id": None},
                admissibility="gm",
                revision_id="snapshot-frozen-8",
                scope_mode="world",
            ),
        )

    monkeypatch.setattr(
        agent_turn_service,
        "assemble_agent_graph_context",
        lambda **_kwargs: SimpleNamespace(invocation=object(), trace_summary={}),
    )
    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": world_id},
        "graph_request": {
            "mode": "world",
            "world_id": world_id,
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
    }
    with pytest.raises(agent_turn_service.AgentTurnServiceError) as exc_info:
        agent_turn_service.execute_agent_turn(
            AgentTurnRequest.model_validate(payload),
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "sessions"),
            owner_resolver=lambda _request: {"kind": "world", "id": world_id},
            work_resolver=lambda *_args: None,
            graph_resolver=resolve_graph,
            runtime_factory=lambda: pytest.fail("pending turn loaded runtime"),
            conversation_service=ReceiptService(),
        )

    assert resolved_pins == ["snapshot-frozen-8"]
    assert exc_info.value.code == "turn_already_running"


def test_accept_race_never_dispatches_context_different_from_winner_receipt(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.services import agent_turn_service
    from apps.live_control_server.services.agent_runtime import (
        AgentContextPacket,
        AgentRunOptions,
        AgentRuntimeInvocation,
        AgentWorldScope,
        WORLD_GRAPH_READ_POLICY,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )
    from application_state.agent_conversation.types import TurnResult

    world_id = "world-accept-race-test"
    request_payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": world_id},
        "graph_request": {
            "mode": "world",
            "world_id": world_id,
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
    }
    request = AgentTurnRequest.model_validate(request_payload)

    def graph_provenance(revision: str) -> TurnProvenance:
        return TurnProvenance(
            world_id=world_id,
            surface_resolution="resolved",
            surface_id="index",
            primary_work=HistoricalReference(resolution="absent"),
            supporting_work=[
                HistoricalReference(
                    resolution="resolved",
                    kind="world_graph_revision",
                    object_id=world_id,
                    revision=revision,
                )
            ],
            selected_object=HistoricalReference(resolution="absent"),
        )

    winning_provenance = graph_provenance("snapshot-r1")
    winning_receipt = _durable_turn(
        world_id=world_id,
        status="accepted",
        provenance=winning_provenance,
        revision=1,
    )

    class ConcurrentReceiptService:
        reconciliations = 0
        submissions: list[TurnSubmission] = []
        claims = 0
        completions: list[TurnResult] = []

        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Turn | None:
            self.reconciliations += 1
            # Model two callers that both miss before either can observe the
            # winning R1 receipt. The third lookup is the matching retry.
            return None if self.reconciliations <= 2 else winning_receipt

        def get_active_conversation(self, _world_id: str) -> Any:
            return SimpleNamespace(
                conversation_id=winning_receipt.conversation_id,
                revision=1,
            )

        def accept_turn(self, submission: TurnSubmission) -> Turn:
            assert (
                submission.provenance.supporting_work[0].revision == "snapshot-r2"
            )
            self.submissions.append(submission)
            return winning_receipt

        def claim_turn(self, *_args: Any, **_kwargs: Any) -> TurnClaimReceipt:
            self.claims += 1
            running = winning_receipt.model_copy(
                update={"status": "running", "revision": winning_receipt.revision + 1}
            )
            return TurnClaimReceipt(disposition="claimed", turn=running)

        def complete_turn(self, result: TurnResult) -> Turn:
            self.completions.append(result)
            return winning_receipt.model_copy(
                update={
                    "status": "completed",
                    "revision": result.expected_revision + 1,
                    "assistant_text": result.assistant_text,
                    "completed_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            )

    service = ConcurrentReceiptService()
    runtime = FakeRuntime()
    graph_pins: list[str | None] = []
    assembled_revisions: list[str] = []
    segment_bases: list[TurnProvenance] = []
    original_segment_id = agent_turn_service._provider_segment_thread_id

    def resolve_graph(
        graph_request: AgentTurnRequest, *_args: Any
    ) -> tuple[dict[str, Any], AgentWorldScope]:
        pin = graph_request.graph_request.revision_pin
        graph_pins.append(pin)
        revision = pin or "snapshot-r2"
        return (
            {"status": "ready", "revision_id": revision, "nodes": []},
            AgentWorldScope(
                world_id=world_id,
                campaign_id="",
                focus={"kind": "none", "session_id": None, "campaign_id": None},
                admissibility="gm",
                revision_id=revision,
                scope_mode="world",
            ),
        )

    def assemble_graph(**kwargs: Any) -> Any:
        revision = str(kwargs["graph_envelope"]["revision_id"])
        assembled_revisions.append(revision)
        scope = AgentWorldScope(
            world_id=world_id,
            campaign_id="",
            focus={"kind": "none", "session_id": None, "campaign_id": None},
            admissibility="gm",
            revision_id=revision,
            scope_mode="world",
        )
        return SimpleNamespace(
            invocation=AgentRuntimeInvocation(
                thread_id=kwargs["thread_id"],
                turn_id=kwargs["turn_id"],
                message=kwargs["question"],
                conversation_history=None,
                context_packet=AgentContextPacket(
                    world_scope=scope,
                    retrieval_session=None,
                    surface_context=kwargs["surface_context"],
                ),
                capability_policy=WORLD_GRAPH_READ_POLICY,
                run_options=AgentRunOptions(),
            ),
            trace_summary={},
        )

    monkeypatch.setattr(
        agent_turn_service,
        "assemble_agent_graph_context",
        assemble_graph,
    )
    monkeypatch.setattr(
        agent_turn_service,
        "_provider_segment_thread_id",
        lambda provenance, *, conversation_id: (
            segment_bases.append(provenance)
            or original_segment_id(provenance, conversation_id=conversation_id)
        ),
    )
    pointer_store = HermesSessionPointerStore(tmp_path / "sessions")
    assert service.reconcile_turn() is None  # competing caller's early miss

    with pytest.raises(agent_turn_service.AgentTurnServiceError) as exc_info:
        agent_turn_service.execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: {
                "kind": "world",
                "id": world_id,
                "name": "Race World",
            },
            work_resolver=lambda *_args: None,
            graph_resolver=resolve_graph,
            runtime=runtime,
            conversation_service=service,
        )

    assert exc_info.value.code == "turn_basis_changed"
    assert service.submissions[0].provenance.supporting_work[0].revision == "snapshot-r2"
    assert winning_receipt.provenance.supporting_work[0].revision == "snapshot-r1"
    assert runtime.invocations == []
    assert service.claims == 0
    assert graph_pins == [None]
    assert assembled_revisions == []
    assert segment_bases == []

    # The matching retry must rebuild context and provider continuity from the
    # winning immutable receipt, never the loser's newly observed Graph head.
    response = agent_turn_service.execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": world_id,
            "name": "Race World",
        },
        work_resolver=lambda *_args: None,
        graph_resolver=resolve_graph,
        runtime=runtime,
        conversation_service=service,
    )

    assert response.graph.revision_id == "snapshot-r1"
    assert graph_pins == [None, "snapshot-r1"]
    assert service.reconciliations == 3
    assert assembled_revisions == ["snapshot-r1"]
    assert segment_bases == [winning_provenance]
    assert len(runtime.invocations) == 1
    assert service.claims == 1
    assert len(service.completions) == 1


def test_provider_output_is_retried_without_redispatch(tmp_path: Path) -> None:
    from application_state.agent_conversation.types import TurnResult
    from application_state.errors import ApplicationStateUnavailableError
    from apps.live_control_server.services.agent_turn_service import execute_agent_turn
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    world_id = "world-completion-retry-test"
    accepted = _durable_turn(world_id=world_id, status="accepted")
    runtime = FakeRuntime()

    class ReceiptService:
        attempts = 0
        completions: list[TurnResult] = []

        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Turn:
            return accepted

        def claim_turn(self, *_args: Any, **_kwargs: Any) -> TurnClaimReceipt:
            running = accepted.model_copy(
                update={"status": "running", "revision": accepted.revision + 1}
            )
            return TurnClaimReceipt(disposition="claimed", turn=running)

        def complete_turn(self, result: TurnResult) -> Turn:
            self.completions.append(result)
            self.attempts += 1
            if self.attempts == 1:
                raise ApplicationStateUnavailableError("temporary write failure")
            return accepted.model_copy(
                update={
                    "status": "completed",
                    "revision": result.expected_revision + 1,
                    "assistant_text": result.assistant_text,
                    "completed_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            )

    service = ReceiptService()
    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": world_id},
    }
    response = execute_agent_turn(
        AgentTurnRequest.model_validate(payload),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "sessions"),
        owner_resolver=lambda _request: {"kind": "world", "id": world_id},
        work_resolver=lambda *_args: None,
        graph_resolver=lambda *_args: pytest.fail("no Graph requested"),
        runtime=runtime,
        conversation_service=service,
    )

    assert response.answer.text == "A simple answer."
    assert len(runtime.invocations) == 1
    assert [item.assistant_text for item in service.completions] == [
        "A simple answer.",
        "A simple answer.",
    ]
    assert {item.expected_revision for item in service.completions} == {2}


def test_interrupted_runtime_persistence_outage_is_reported_indeterminate(
    tmp_path: Path,
) -> None:
    import psycopg

    from apps.live_control_server.services.agent_runtime import AgentRuntimeDescriptor
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
        execute_agent_turn,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    world_id = "world-interruption-outage-test"
    accepted = _durable_turn(world_id=world_id, status="accepted")

    class InterruptedRuntime:
        descriptor = AgentRuntimeDescriptor("fake", "fake", "test", "conversation")

        def __init__(self) -> None:
            self.calls = 0

        def run(self, _invocation: Any) -> Any:
            self.calls += 1
            raise RuntimeError("provider transport disconnected")

    class ReceiptService:
        failures: list[tuple[TurnFailure, bool]] = []

        def reconcile_turn(self, *_args: Any, **_kwargs: Any) -> Turn:
            return accepted

        def claim_turn(self, *_args: Any, **_kwargs: Any) -> TurnClaimReceipt:
            running = accepted.model_copy(
                update={"status": "running", "revision": accepted.revision + 1}
            )
            return TurnClaimReceipt(disposition="claimed", turn=running)

        def fail_turn(self, failure: TurnFailure, *, interrupted: bool = False) -> Any:
            self.failures.append((failure, interrupted))
            raise psycopg.OperationalError("database connection lost")

    runtime = InterruptedRuntime()
    service = ReceiptService()
    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": world_id},
    }

    with pytest.raises(AgentTurnServiceError) as exc_info:
        execute_agent_turn(
            AgentTurnRequest.model_validate(payload),
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "sessions"),
            owner_resolver=lambda _request: {"kind": "world", "id": world_id},
            work_resolver=lambda *_args: None,
            graph_resolver=lambda *_args: pytest.fail("no Graph requested"),
            runtime=runtime,
            conversation_service=service,
        )

    assert exc_info.value.code == "turn_persistence_indeterminate"
    assert exc_info.value.status_code == 503
    assert runtime.calls == 1
    assert len(service.failures) == 1
    assert service.failures[0][1] is True


def test_claim_renewer_serializes_latest_revision_fence() -> None:
    from threading import Event

    from apps.live_control_server.services.agent_turn_service import _TurnClaimRenewer

    initial = _durable_turn(
        world_id="world-renew-worker-test", status="running", revision=5
    )

    class ClaimService:
        revisions: list[int] = []

        def renew_turn_claim(
            self,
            _world_id: str,
            _conversation_id: Any,
            _turn_id: Any,
            *,
            expected_revision: int,
            lease_seconds: int,
        ) -> Turn:
            assert lease_seconds == 7
            self.revisions.append(expected_revision)
            return initial.model_copy(
                update={"revision": expected_revision + 1}
            )

    service = ClaimService()
    renewer = _TurnClaimRenewer(
        service, initial, lease_seconds=7, renewal_interval_seconds=0.01
    )
    Event().wait(0.04)
    final_turn, error = renewer.stop_and_join()

    assert error is None
    assert len(service.revisions) >= 2
    assert service.revisions[0] == initial.revision
    assert service.revisions == sorted(service.revisions)
    assert service.revisions[-1] == final_turn.revision - 1


def test_request_validation_rejects_unknown_or_contradictory_fields() -> None:
    from apps.live_control_server.models.agent_turn import AgentTurnRequest

    payload = _payload()
    saved_work = {
        **payload,
        "primary_work": {
            "kind": "plan",
            "document_id": "plan-1",
            "expected_revision": 1,
        },
        "client_work_state": "saved_clean",
    }
    for invalid in (
        {**payload, "untrusted_resolved_scope": "world:fake"},
        {**payload, "graph_selection": {"node_id": "node:stacy"}},
        {**payload, "message": " " * 8_001},
        {**payload, "message": " \t\n "},
        {
            **saved_work,
            "primary_work": {**saved_work["primary_work"], "expected_revision": 0},
        },
        {
            **saved_work,
            "primary_work": {**saved_work["primary_work"], "expected_revision": "1"},
        },
        {**payload, "client_work_state": "saved_clean"},
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 1,
            },
            "client_work_state": "saved_clean",
        },
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan", "object_id": "plan-1", "expected_revision": 1,
                "expected_revision_n": 2, "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_clean",
            "playable_target": {
                "schema": "dmb_plan_playable_target_v1", "kind": "scene", "id": "scene:arrival",
                "marker_grammar_version": "v1",
            },
        },
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan", "object_id": "plan-1", "expected_revision": 1,
                "expected_revision_n": 2, "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_clean",
            "playable_target": {
                "schema": "dmb_plan_playable_target_v1", "kind": "scene", "id": "choice:arrival"
            },
        },
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 1,
                "expected_revision_n": 2,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_clean",
            "graph_request": {
                "mode": "world",
                "world_id": "world-1",
                "campaign_id": None,
                "revision_pin": None,
                "focus": {"kind": "none", "session_id": None, "campaign_id": None},
            },
        },
        {
            **payload,
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 1,
                "expected_revision_n": 2,
                "expected_content_sha256": "b" * 63,
            },
            "client_work_state": "saved_clean",
        },
    ):
        try:
            AgentTurnRequest.model_validate(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid turn request was accepted")

    accepted_target = AgentTurnRequest.model_validate({
        **payload,
        "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
        "owner_scope": {"kind": "world", "world_id": "world-1"},
        "primary_work": {
            "kind": "plan", "object_id": "plan-1", "expected_revision": 1,
            "expected_revision_n": 2, "expected_content_sha256": "b" * 64,
        },
        "client_work_state": "saved_clean",
        "playable_target": {
            "schema": "dmb_plan_playable_target_v1", "kind": "beat", "id": "beat:a"
        },
    })
    assert accepted_target.playable_target is not None
    assert accepted_target.playable_target.id == "beat:a"


def test_plan_resolver_reads_exact_committed_world_revision_and_returns_basis(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.routes import agent as agent_route

    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    basis = {
        "world_id": "world-1",
        "document_id": "plan-1",
        "object_revision": 4,
        "work_revision_id": "work-revision-8",
        "revision_n": 8,
        "markdown": "# Saved plan\n\nThe sealed phrase is amber lantern.\n",
        "content_sha256": "b" * 64,
        "committed_status": "committed",
        "has_divergent_working_copy": True,
    }
    observed: dict[str, Any] = {}

    def read_exact(document_id: str, **kwargs: Any) -> Any:
        observed["document_id"] = document_id
        observed.update(kwargs)
        return SimpleNamespace(**basis)

    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", read_exact)
    monkeypatch.setattr(
        agent_route,
        "get_workspace_document",
        lambda *_args: pytest.fail(
            "pinned Plan turns must use the atomic Content read"
        ),
    )
    monkeypatch.setattr(
        agent_route,
        "get_committed_playable_revision",
        lambda *_args, **_kwargs: pytest.fail(
            "pinned Plan turns must not mix revision reads"
        ),
    )
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 4,
                "expected_revision_n": 8,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_dirty",
        }
    )
    work = agent_route._work_resolver(request, {"kind": "world", "id": "world-1"})
    assert work is not None
    assert work.revision == 4
    assert work.changed_since_expected is False
    assert work.surface_context.current_work.object_revision == 4
    assert work.plan_markdown == basis["markdown"]
    assert work.content_basis.model_dump() == {
        key: value for key, value in basis.items() if key != "markdown"
    }
    assert observed == {
        "document_id": "plan-1",
        "expected_world_id": "world-1",
        "expected_revision": 4,
        "expected_revision_n": 8,
        "expected_content_sha256": "b" * 64,
    }


def test_plan_resolver_fails_stale_pin_before_agent_dispatch(monkeypatch: Any) -> None:
    from apps.live_control_server.routes import agent as agent_route

    def stale_read(*_args: Any, **_kwargs: Any) -> Any:
        raise agent_route.WorkspaceDocumentRegistryError(
            "World Plan current revision does not match the requested pin",
            status_code=409,
        )

    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", stale_read)
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": "world-1"},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 4,
                "expected_revision_n": 8,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_dirty",
        }
    )

    with pytest.raises(agent_route.AgentTurnServiceError) as exc_info:
        agent_route._work_resolver(request, {"kind": "world", "id": "world-1"})

    assert exc_info.value.code == "plan_revision_changed"
    assert exc_info.value.status_code == 409


def test_plan_agent_route_dispatches_only_atomic_committed_content(
    tmp_path: Path, monkeypatch: Any, application_state_dsn: str
) -> None:
    import json

    assert application_state_dsn
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    managed_world = create_world_container(tmp_path, name="Plan Ask World")
    markdown = "# Saved Plan\n\nThe keeper waits below the black arch.\n"
    basis = {
        "world_id": managed_world.world_id,
        "document_id": "plan-1",
        "object_revision": 7,
        "work_revision_id": "f9077838-81ae-4b7c-bfa6-37ade6f0d488",
        "revision_n": 4,
        "markdown": markdown,
        "content_sha256": "b" * 64,
        "committed_status": "committed",
        "has_divergent_working_copy": True,
    }
    observed: dict[str, Any] = {}

    def read_atomic(document_id: str, **kwargs: Any) -> Any:
        observed["document_id"] = document_id
        observed.update(kwargs)
        return SimpleNamespace(**basis)

    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", read_atomic)
    monkeypatch.setattr(
        agent_route,
        "get_workspace_document",
        lambda *_args: pytest.fail(
            "Plan Ask must not perform a separate metadata read"
        ),
    )
    monkeypatch.setattr(
        agent_route,
        "get_committed_playable_revision",
        lambda *_args, **_kwargs: pytest.fail(
            "Plan Ask must use the atomic current Content read"
        ),
    )
    runtime = FakeRuntime()
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 7,
                "expected_revision_n": 4,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_dirty",
            "message": "What is beneath the black arch?",
        }
    )
    app = SimpleNamespace(state=SimpleNamespace(agent_turn_runtime=runtime))

    response = agent_route.post_agent_turn(request, SimpleNamespace(app=app))

    assert observed == {
        "document_id": "plan-1",
        "expected_world_id": managed_world.world_id,
        "expected_revision": 7,
        "expected_revision_n": 4,
        "expected_content_sha256": "b" * 64,
    }
    assert len(runtime.invocations) == 1
    _prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert json.loads(payload) == {
        "committed_plan_markdown": markdown,
        "user_question": "What is beneath the black arch?",
    }
    assert response["graph"]["status"] == "not_requested"
    assert response["primary_work"]["content_basis"] == {
        key: value for key, value in basis.items() if key != "markdown"
    }
    assert markdown not in json.dumps(response)


def test_plan_agent_route_rejects_stale_pin_before_runtime_dispatch(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from fastapi import HTTPException

    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    managed_world = create_world_container(tmp_path, name="Stale Plan Ask World")

    def stale_read(*_args: Any, **_kwargs: Any) -> Any:
        raise agent_route.WorkspaceDocumentRegistryError(
            "World Plan current revision does not match the requested pin",
            status_code=409,
        )

    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "get_current_world_plan_revision", stale_read)
    runtime = FakeRuntime()
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
            "primary_work": {
                "kind": "plan",
                "object_id": "plan-1",
                "expected_revision": 7,
                "expected_revision_n": 4,
                "expected_content_sha256": "b" * 64,
            },
            "client_work_state": "saved_clean",
        }
    )
    app = SimpleNamespace(state=SimpleNamespace(agent_turn_runtime=runtime))

    with pytest.raises(HTTPException) as exc_info:
        agent_route.post_agent_turn(request, SimpleNamespace(app=app))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "plan_revision_changed"
    assert runtime.invocations == []
    assert not (tmp_path / "sessions" / "hermes_thread_pointers.json").exists()


def test_plan_agent_route_reads_actual_committed_content_and_excludes_divergent_draft(
    tmp_path: Path,
    monkeypatch: Any,
    application_state_dsn: str,
) -> None:
    import json

    from application_state.content.service import (
        autosave_plan,
        commit_plan,
        create_world_plan,
        read_current_world_plan_revision,
    )
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    assert application_state_dsn
    managed_world = create_world_container(tmp_path, name="Atomic Plan Ask World")
    created = create_world_plan(
        title="Atomic Plan Ask",
        world_id=managed_world.world_id,
    )
    markdown = "# Atomic Plan\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\nThe keeper waits below the black arch.\n"
    draft_markdown = "# Local draft\n\nThe draft says the arch is empty.\n"
    _committed_object, committed = commit_plan(
        str(created.work_object_id),
        markdown,
        expected_world_id=managed_world.world_id,
    )
    draft = autosave_plan(
        str(created.work_object_id),
        draft_markdown,
        expected_world_id=managed_world.world_id,
    )
    current = read_current_world_plan_revision(
        str(created.work_object_id),
        expected_world_id=managed_world.world_id,
        expected_revision=draft.object_revision,
        expected_revision_n=committed.revision_n,
        expected_content_sha256=committed.content_sha256,
    )
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    runtime = FakeRuntime()
    request = AgentTurnRequest.model_validate(
        {
            **_payload(),
            "surface": {"surface_id": "plan", "instance_id": "plan-pane"},
            "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
            "primary_work": {
                "kind": "plan",
                "object_id": str(created.work_object_id),
                "expected_revision": current.object_revision,
                "expected_revision_n": current.revision_n,
                "expected_content_sha256": current.content_sha256,
            },
            "client_work_state": "saved_dirty",
            "playable_target": {
                "schema": "dmb_plan_playable_target_v1",
                "kind": "scene",
                "id": "scene:arrival",
            },
            "message": "What is beneath the black arch?",
        }
    )
    app = SimpleNamespace(state=SimpleNamespace(agent_turn_runtime=runtime))

    response = agent_route.post_agent_turn(request, SimpleNamespace(app=app))

    assert len(runtime.invocations) == 1
    _prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert json.loads(payload) == {
        "committed_plan_markdown": markdown,
        "user_question": "What is beneath the black arch?",
        "focus_metadata": {
            "playable_target": {
                "kind": "scene",
                "id": "scene:arrival",
                "marker_grammar_version": "v1",
            },
            "work_revision": {
                "work_revision_id": str(committed.work_revision_id),
                "revision_n": committed.revision_n,
                "content_sha256": committed.content_sha256,
                "object_revision": current.object_revision,
            },
        },
    }
    assert draft_markdown not in runtime.invocations[0].message
    assert response["primary_work"]["content_basis"] == {
        "world_id": managed_world.world_id,
        "document_id": str(created.work_object_id),
        "object_revision": current.object_revision,
        "work_revision_id": str(committed.work_revision_id),
        "revision_n": committed.revision_n,
        "content_sha256": committed.content_sha256,
        "committed_status": "committed",
        "has_divergent_working_copy": True,
    }
    assert markdown not in json.dumps(response)
    after = read_current_world_plan_revision(
        str(created.work_object_id),
        expected_world_id=managed_world.world_id,
        expected_revision=current.object_revision,
        expected_revision_n=current.revision_n,
        expected_content_sha256=current.content_sha256,
    )
    assert after.markdown == markdown
    assert after.has_divergent_working_copy is True


def test_campaign_id_equal_to_world_id_is_not_world_plan_ownership(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
        execute_agent_turn,
    )
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    managed_world = create_world_container(tmp_path, name="World Alias Test")
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        agent_route,
        "get_workspace_document",
        lambda _root, _document_id: SimpleNamespace(
            kind="plan",
            status="active",
            world_id=None,
            campaign_id=managed_world.world_id,
            target_session=None,
            document_id="plan-campaign-only",
            title="Campaign-only Plan",
        ),
    )
    monkeypatch.setattr(
        agent_route,
        "get_committed_playable_revision",
        lambda _document_id, **_kwargs: SimpleNamespace(
            status="active",
            document_id="plan-campaign-only",
            title="Campaign-only Plan",
            object_revision=1,
        ),
    )
    payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
        "primary_work": {
            "kind": "plan",
            "object_id": "plan-campaign-only",
            "expected_revision": 1,
        },
        "client_work_state": "saved_clean",
    }
    request = AgentTurnRequest.model_validate(payload)
    runtime = FakeRuntime()
    pointer_store = HermesSessionPointerStore(tmp_path / "pointer-store")

    with pytest.raises(AgentTurnServiceError) as exc_info:
        execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=agent_route._owner_resolver,
            work_resolver=agent_route._work_resolver,
            graph_resolver=lambda *_args: pytest.fail("no-graph turn resolved a graph"),
            runtime=runtime,
        )

    assert exc_info.value.code == "work_foreign"
    assert runtime.invocations == []
    assert not (tmp_path / "pointer-store" / "hermes_thread_pointers.json").exists()


def test_graph_focus_must_match_session_id_derived_from_saved_plan(
    monkeypatch: Any,
) -> None:
    from types import SimpleNamespace

    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    monkeypatch.setattr(agent_route, "repo_root", lambda: Path("/tmp"))
    monkeypatch.setattr(agent_route, "get_world_container", lambda *_args: object())
    monkeypatch.setattr(
        agent_route,
        "build_existing_graph_context",
        lambda *_args, **_kwargs: (
            {"status": "empty"},
            AgentWorldScope(
                world_id="world-1",
                campaign_id="campaign-1",
                focus={
                    "kind": "session",
                    "session_id": "session-23",
                    "campaign_id": "campaign-1",
                },
                admissibility="gm",
                revision_id="rev-1",
                scope_mode="world",
            ),
        ),
    )
    work = SimpleNamespace(
        owner_id="world-1",
        world_id="world-1",
        campaign_id="campaign-1",
        target_session=23,
        session_id="session-23",
    )
    request_payload = {
        **_payload(),
        "owner_scope": {"kind": "world", "world_id": "world-1"},
        "primary_work": {
            "kind": "plan",
            "object_id": "plan-1",
            "expected_revision": 1,
        },
        "client_work_state": "saved_clean",
        "graph_request": {
            "mode": "world",
            "world_id": "world-1",
            "campaign_id": "campaign-1",
            "revision_pin": None,
            "focus": {
                "kind": "session",
                "session_id": "session-23",
                "campaign_id": "campaign-1",
            },
        },
    }
    request = AgentTurnRequest.model_validate(request_payload)
    _envelope, scope = agent_route._graph_resolver(
        request, {"kind": "world", "id": "world-1"}, work
    )
    assert scope.focus["session_id"] == "session-23"

    request_payload["graph_request"]["focus"]["session_id"] = "session-24"
    mismatched = AgentTurnRequest.model_validate(request_payload)
    try:
        agent_route._graph_resolver(
            mismatched, {"kind": "world", "id": "world-1"}, work
        )
    except AgentTurnServiceError as exc:
        assert exc.code == "graph_focus_rejected"
    else:
        raise AssertionError("mismatched session focus was accepted")


def test_full_application_http_route_and_legacy_route_cardinality(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.routes import live as live_route

    runtime = FakeRuntime()
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "_owner_resolver", lambda _body: None)
    monkeypatch.setattr(agent_route, "_work_resolver", lambda _body, _owner: None)

    def forbidden_packet_load(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("no-graph HTTP turn loaded a legacy session packet")

    monkeypatch.setattr(live_route, "load_session", forbidden_packet_load)
    app = create_app()
    app.state.agent_turn_runtime = runtime
    agent_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/live/agent/turn"
        and "POST" in getattr(route, "methods", set())
    ]
    legacy_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/live/query"
        and "POST" in getattr(route, "methods", set())
    ]
    history_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None)
        == "/api/live/agent/worlds/{world_id}/conversation"
        and "GET" in getattr(route, "methods", set())
    ]
    new_conversation_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None)
        == "/api/live/agent/worlds/{world_id}/conversation/new"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(agent_routes) == 1
    assert len(legacy_routes) == 1
    assert len(history_routes) == 1
    assert len(new_conversation_routes) == 1

    async def post_turn() -> httpx.Response:
        # ASGITransport exercises the full HTTP app without starting its
        # provider-worker lifespan; this test injects a deterministic runtime.
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post("/api/live/agent/turn", json=_payload())

    response = asyncio.run(post_turn())

    assert response.status_code == 200
    body = response.json()
    assert body["surface"]["surface_id"] == "index"
    assert body["graph"]["status"] == "not_requested"
    assert body["answer"]["graph_grounded"] is False
    assert runtime.invocations[0].context_packet.surface_context.surface_id == "index"
    assert runtime.invocations[0].context_packet.world_scope is None
    assert runtime.invocations[0].context_packet.retrieval_session is None


def test_verified_world_projection_reaches_runtime_through_full_http_route(
    tmp_path: Path, monkeypatch: Any, application_state_dsn: str
) -> None:
    assert application_state_dsn
    from apps.live_control_server.config import (
        WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
        WORLD_GRAPH_AUTHORITY_ENV,
        WORLD_GRAPH_ROOT_ENV,
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as agent_route
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import (
        InMemorySourceRepository,
        InMemoryWorldGraphRepository,
    )
    from tests._cutover_direct_dungeonmind_read_helpers import (
        WORLD_ID as FIXTURE_WORLD_ID,
        NOW,
        _FakeBundle,
        _payload as direct_payload,
        _receipt,
        _seed_sources,
    )

    managed_world = create_world_container(tmp_path, name="Agent Projection Test World")
    world_root = tmp_path / "isolated-world-root"
    auth_token = "test-local-operator-token-with-adequate-length"
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", auth_token)
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv(WORLD_GRAPH_ROOT_ENV, str(world_root))
    monkeypatch.setattr(agent_route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent_route, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(agent_route, "world_graph_root", lambda: world_root)

    def remap_fixture_ids(value: Any) -> Any:
        if value == FIXTURE_WORLD_ID:
            return managed_world.world_id
        if isinstance(value, dict):
            return {key: remap_fixture_ids(item) for key, item in value.items()}
        if isinstance(value, list):
            return [remap_fixture_ids(item) for item in value]
        return value

    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=managed_world.world_id,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:agent-real-projection"],
            graph_schema="dm_union_graph_v6",
            graph_payload=remap_fixture_ids(direct_payload()),
            created_at=NOW,
        )
    )
    seeded_sources = _seed_sources()
    sources = InMemorySourceRepository()
    for artifact_id in (
        "src:world-lore",
        "src:one-notes",
        "src:one-recap",
        "src:player-sign",
    ):
        artifact = seeded_sources.get_artifact(artifact_id)
        assert artifact is not None
        sources.put_artifact(
            artifact.model_copy(update={"world_id": managed_world.world_id})
        )
        revision = seeded_sources.get_revision(artifact.current_revision_id)
        assert revision is not None
        sources.put_revision(revision)
    services = direct.direct_services_from_bundle(
        _FakeBundle(
            world_graph,
            sources,
            _receipt(managed_world.world_id, published.revision_id),
        ),
        managed_world.world_id,
    )

    def direct_services_for_world(world_id: str) -> Any:
        assert world_id == managed_world.world_id
        return services

    monkeypatch.setattr(
        direct, "direct_services_from_config", direct_services_for_world
    )
    runtime = FakeRuntime()
    app = create_app()
    app.state.agent_turn_runtime = runtime
    payload = {
        **_payload(),
        "surface": {"surface_id": "plan", "instance_id": "world-plan-main"},
        "owner_scope": {"kind": "world", "world_id": managed_world.world_id},
        "graph_request": {
            "mode": "world",
            "world_id": managed_world.world_id,
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
        "message": "Where is the tavern?",
    }

    async def post_turn() -> httpx.Response:
        # Keep the real application/router/HTTP path, but leave the external
        # agent-worker lifecycle outside this deterministic integration test.
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/api/live/agent/turn",
                json=payload,
                headers={"Authorization": f"Bearer {auth_token}"},
            )

    response = asyncio.run(post_turn())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["owner_scope"]["owner_id"] == managed_world.world_id
    assert body["graph"]["status"] == "ready"
    assert body["graph"]["revision_id"] == published.revision_id
    assert body["graph"]["head_revision_id"] == published.revision_id
    invocation = runtime.invocations[0]
    assert invocation.context_packet.world_scope is not None
    assert invocation.context_packet.world_scope.world_id == managed_world.world_id
    assert invocation.context_packet.world_scope.revision_id == published.revision_id
    assert invocation.context_packet.retrieval_session is not None
    packet_text = str(invocation.context_packet.retrieval_session.packet)
    assert "The Prancing Tavern" in packet_text
