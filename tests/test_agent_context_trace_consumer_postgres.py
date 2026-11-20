import hashlib
import json

import pytest
from time import monotonic
from uuid import uuid4

from application_state.agent_conversation.context_trace import MAX_CONTEXT_TRACE_BYTES
from application_state.agent_conversation.types import (
    SubmittedTurnIntentV2, TurnFailure, TurnSubmission,
)
from apps.live_control_server.services.agent_context_compaction_report import compaction_report
from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
from apps.live_control_server.services.agent_conversation_context import compact_conversation_context
from apps.live_control_server.services.agent_turn_service import _ClaimFence
from tests.application_state.test_agent_conversation_historical_trace_postgres import historical_pair as historical_pair


def test_restoration_consumer_persists_exact_historical_before_and_route_only_after(historical_pair):
    service, conversation, original, current, _, ref, passage = historical_pair
    original_trace = service.list_context_trace_attempts(world_id=current.world_id, turn_id=original.turn_id)
    messages = [{"role": "user", "content": "Tell me all about Mirathorn."},
        {"role": "tool", "content": json.dumps({"schema": "dmb_world_graph_source_anchor_read_v1",
            "outcome": passage.outcome, "anchorId": passage.anchor_id, "evidenceRefId": passage.evidence_ref_id,
            "sourceArtifactId": passage.source_artifact_id, "sourceRevisionId": passage.source_revision_id,
            "snapshot": {"worldId": current.world_id, "revisionId": passage.graph_revision}, "content": passage.text})},
        {"role": "assistant", "content": "An established communications fact."}]
    compacted = compact_conversation_context(messages)
    fence = _ClaimFence(service, current)
    capture = ContextTraceCollector.__new__(ContextTraceCollector)
    capture.fence, capture.started = fence, monotonic()
    capture.trace = service.list_context_trace_attempts(world_id=current.world_id, turn_id=current.turn_id)[0]
    try:
        capture.compaction(compaction_report(messages, compacted), graph_world_id=current.world_id)
        capture.provider_context("Who are the operators?", [], body={"input": compacted.messages})
        assert fence.turn.revision == current.revision
        assert fence.turn.graph_context_execution is None
    finally:
        stopped, error = fence.stop()
        assert error is None
    service.fail_turn(TurnFailure(world_id=current.world_id, conversation_id=conversation.conversation_id,
                                 turn_id=current.turn_id, expected_revision=stopped.revision,
                                 failure_code="synthetic_consumer_terminal"))
    saved = service.list_context_trace_attempts(world_id=current.world_id, turn_id=current.turn_id)[0]
    assert saved.capture_status == "complete" and saved.terminal_status == "failed"
    before, after = saved.observations[:2]
    source = next(item for item in before.materials if item.role == "source")
    assert source.historical_source_reads == [ref]
    assert any(item.state == "retrieval_route" and item.route.anchor_id == passage.anchor_id for item in after.materials)
    assert not any(item.role == "source" and item.state == "model_context" for item in after.materials)
    assert passage.text not in saved.model_dump_json()
    assert service.list_context_trace_attempts(world_id=current.world_id, turn_id=original.turn_id) == original_trace


@pytest.mark.parametrize("prior_gap", [None, "historical_source_unavailable"])
def test_real_source_capture_cap_commits_one_receipt_without_uncaptured_passage(historical_pair, prior_gap):
    service, conversation, original, current, _, _, _ = historical_pair
    original = next(turn for turn in service.list_turns(current.world_id, conversation.conversation_id)
                    if turn.turn_id == original.turn_id)
    service.fail_turn(TurnFailure(world_id=current.world_id, conversation_id=conversation.conversation_id,
                                 turn_id=current.turn_id, expected_revision=current.revision,
                                 failure_code="synthetic_setup_terminal"))
    primary = original.provenance.primary_work
    intent = SubmittedTurnIntentV2(world_id=current.world_id, client_thread_id="source-cap-consumer",
        message="Capture a new source.", surface_id="plan", surface_instance_id="plan-pane-source-read",
        client_work_state="saved_clean", primary_work={"kind": "plan", "object_id": primary.object_id,
            "expected_revision": primary.object_revision, "expected_revision_n": primary.revision_n,
            "expected_content_sha256": primary.content_sha256},
        plan_context_policy={"policy": "auto_plan_world"},
        playable_target={"schema": "dmb_plan_playable_target_v1", "kind": "beat", "id": "beat:a"},
        graph_request={"mode": "none"}, graph_selection=None)
    accepted = service.accept_turn(TurnSubmission(world_id=current.world_id, conversation_id=conversation.conversation_id,
        expected_conversation_revision=service.get_conversation(current.world_id, conversation.conversation_id).revision,
        idempotency_key=uuid4(), user_text=intent.message, submitted_intent_v2=intent,
        provenance=original.provenance, graph_context_receipt=original.graph_context_receipt,
        graph_context_execution=original.graph_context_execution.model_copy(update={"events": []})))
    claimed = service.claim_turn(current.world_id, conversation.conversation_id, accepted.turn_id,
                                  expected_revision=accepted.revision, lease_seconds=60).turn
    fence = _ClaimFence(service, claimed)
    capture = ContextTraceCollector(fence)
    try:
        if prior_gap:
            capture.mark_incomplete(prior_gap)
        capture.observe({"kind": "context_snapshot", "stage": "before", "materials": [
            {"item_id": "capacity-witness", "state": "model_context", "role": "assistant",
             "text": "x" * (MAX_CONTEXT_TRACE_BYTES - 6000)}]})
        assert capture.trace.capture_status == ("incomplete" if prior_gap else "recording")
        read_call = uuid4()
        authorization = original.graph_context_execution.events[0].model_copy(update={
            "event_id": uuid4(), "sequence": 0, "read_call_id": read_call})
        fence.append("authorize_source_read", "authorization", authorization)
        text = "p" * 12000
        prior_result = original.graph_context_execution.events[1]
        receipt = prior_result.receipts[0].model_copy(update={"source_read_id": "source-read:capacity",
            "returned_chars": len(text), "content_sha256": hashlib.sha256(text.encode()).hexdigest()})
        event = prior_result.model_copy(update={"event_id": uuid4(), "sequence": 1,
                                                "read_call_id": read_call, "receipts": [receipt]})
        updated, fresh, may_release = capture.persist_source_receipt(event, [{"content": text}],
            world_id=current.world_id, graph_revision=authorization.graph_revision)
        assert fresh and not may_release
        assert len(updated.graph_context_execution.events) == 2
        assert updated.graph_context_execution.events[-1].event_id == event.event_id
        assert capture.trace.capture_failure_code == (prior_gap or "trace_size_limit")
        assert capture._capture_exhausted()
        assert not any(item.kind == "source_passage" for item in capture.trace.observations)
    finally:
        stopped, error = fence.stop()
        assert error is None
    service.fail_turn(TurnFailure(world_id=current.world_id, conversation_id=conversation.conversation_id,
                                 turn_id=stopped.turn_id, expected_revision=stopped.revision,
                                 failure_code="synthetic_capacity_terminal"))
    saved = service.list_context_trace_attempts(world_id=current.world_id, turn_id=stopped.turn_id)[0]
    assert saved.capture_status == "incomplete" and saved.terminal_status == "failed"


def test_real_combined_partial_gaps_preserve_first_marker(historical_pair):
    service, _, _, current, _, _, _ = historical_pair
    fence = _ClaimFence(service, current)
    capture = ContextTraceCollector.__new__(ContextTraceCollector)
    capture.fence, capture.started = fence, monotonic()
    capture.trace = service.list_context_trace_attempts(world_id=current.world_id, turn_id=current.turn_id)[0]
    try:
        capture.mark_incomplete("historical_source_unavailable")
        capture.mark_incomplete("recap_context_capture_unavailable")
        capture.observe({"kind": "failure", "phase": "graph_retrieval", "code": "synthetic_later_observation"})
        assert capture.trace.capture_failure_code == "historical_source_unavailable"
        assert not capture._capture_exhausted()
        assert any(item.kind == "failure" and item.code == "recap_context_capture_unavailable"
                   for item in capture.trace.observations)
        assert capture.trace.observations[-1].code == "synthetic_later_observation"
        assert fence.turn.revision == current.revision
    finally:
        _, error = fence.stop()
        assert error is None
