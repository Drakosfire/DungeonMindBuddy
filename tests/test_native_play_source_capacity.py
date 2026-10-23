"""Empty initial source scope must retain capacity for later exact discovery."""

from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from application_state.agent_conversation import types as t
from application_state.errors import ApplicationStateValidationError
from application_state.agent_conversation.play_graph_input import NativePlayInputV4, pack_play_frame
from application_state.agent_conversation.rules_authority_types import canonical_bytes
from application_state.agent_conversation.surface_evidence_answer import NATIVE_INSTRUCTIONS
from apps.live_control_server.services import native_play_graph_owner as owner
from tests.application_state.test_native_play_graph_postgres import make_submission
from tests.application_state.test_native_play_input_postgres import append
from tests.test_play_graph_authority import native_provider
from tests.test_settled_source_read_accounting import (
    receipt as settled_read,
)


def prepare_empty_owner(application_state_dsn, monkeypatch):
    service, sub, frame = make_submission()
    body = {
        "model": "synthetic",
        "messages": [
            {
                "role": "user",
                "content": canonical_bytes(
                    NativePlayInputV4(
                        submission_id=sub.idempotency_key,
                        message=sub.user_text,
                        source_frame=pack_play_frame(frame),
                        answer_instructions=NATIVE_INSTRUCTIONS,
                    )
                ).decode(),
            }
        ],
        "tools": [],
    }
    raw = json.dumps(body)
    view = {
        "payloadJson": raw,
        "payloadSha256": sha256(raw.encode()).hexdigest(),
        "payloadUtf8Bytes": len(raw.encode()),
        "model": "synthetic",
    }
    # Source owner projection and initial Graph claims are independently covered;
    # this calls the actual production freeze and persists its empty-scope policy.
    monkeypatch.setattr(owner, "prepare_play_sources", lambda *_: (frame, ""))
    monkeypatch.setattr(owner, "_initial_claim_packet", lambda *_: {"claims": []})
    monkeypatch.setattr(owner, "_initial_membership", lambda *_: ([], [], []))
    authority = sub.graph_context_receipt.graph_authority
    bootstrap = SimpleNamespace(
        retrieval_session=SimpleNamespace(
            id="empty-discovery", coverage=SimpleNamespace(state="ready")
        ),
        source_index_commitment=None,
        source_scope_anchors=(),
        candidate_assertion_ids=(),
        candidate_relationship_ids=(),
        candidate_evidence_ref_ids=(),
        assembler_version="native-play-v1",
        binding_version=authority.binding_version,
        world_scope=SimpleNamespace(
            world_id=authority.native_world_id, revision_id=authority.graph_revision
        ),
    )
    budget = {
        "contextLimitTokens": 100000,
        "outputReserveTokens": 1000,
        "estimator": "utf8_json_bytes_plus_64_per_node_v1",
    }
    receipt, execution, _ = owner.freeze_play_receipt(
        None,
        SimpleNamespace(play_context_receipt=sub.play_context_receipt),
        bootstrap,
        view,
        budget,
    )
    assert execution.policy.source_read_scope.admitted_anchors == []
    assert execution.policy.max_source_read_chars == 96000
    sub = sub.model_copy(
        update={"graph_context_receipt": receipt, "graph_context_execution": execution}
    )
    turn = service.accept_turn(sub)
    turn = service.claim_turn(
        sub.world_id, sub.conversation_id, turn.turn_id, expected_revision=turn.revision
    ).turn
    provider = native_provider(1).model_copy(
        update={
            "envelope_sha256": view["payloadSha256"],
            "api_mode": "chat_completions",
            "input_tokens": receipt.assembled_input.provider_envelope_input_tokens,
            "input_estimator": budget["estimator"],
            "output_token_reserve": budget["outputReserveTokens"],
            "input_accounting_kind": "conservative_upper_bound",
        }
    )
    turn, _ = append(service, sub, turn, provider, raw)
    for value in ("sdk_entered", "response_received"):
        turn, _ = service.record_provider_outcome(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(
                kind="provider_outcome",
                event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events),
                provider_attempt_id=provider.provider_attempt_id,
                outcome=value,
            ),
        )
    return SimpleNamespace(
        service=service,
        sub=sub,
        turn=turn,
        provider=provider,
        raw=raw,
        receipt=receipt,
        execution=execution,
        authority=authority,
    )


def test_actual_empty_discovery_owner_freeze_allows_only_later_exact_pins(
    application_state_dsn, monkeypatch
):
    case = prepare_empty_owner(application_state_dsn, monkeypatch)
    service, turn, receipt, execution, authority = (
        case.service,
        case.turn,
        case.receipt,
        case.execution,
        case.authority,
    )
    pin = t.GraphSourceScopeAnchorV2(
        anchor_id="new-anchor",
        evidence_ref_id="new-evidence",
        source_artifact_id="new-source",
        source_revision_id="new-revision",
    )
    auth = t.SourceReadAuthorizationEventV2(
        kind="source_read_authorized_v2",
        event_id=uuid4(),
        sequence=len(turn.graph_context_execution.events),
        read_call_id=uuid4(),
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        retrieval_session_id=receipt.retrieval_session_id,
        world_id=turn.world_id,
        campaign_id=None,
        graph_revision=authority.graph_revision,
        anchors=[pin],
        max_chars=4000,
    )
    with pytest.raises(ApplicationStateValidationError, match="scope|admitted"):
        service.authorize_source_read(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            authorization=auth,
        )
    op = t.ValidatedGraphOperationEventV3(
        kind="validated_graph_operation_v3",
        event_id=uuid4(),
        sequence=len(turn.graph_context_execution.events),
        operation_id=uuid4(),
        operation="expand_graph_retrieval",
        request_arguments_sha256="a" * 64,
        graph_revision=authority.graph_revision,
        result_packet_sha256="b" * 64,
        assertion_ids=[],
        relationship_ids=[],
        evidence_ref_ids=[pin.evidence_ref_id],
        evidence_sufficiency_status="insufficient",
        coverage_status="complete",
        truncated=False,
        source_opened=False,
        returned_source_pins=[pin],
    )
    turn, _ = service.append_validated_graph_operation(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        operation_event=op,
    )
    ext = t.SourceScopeExtensionEventV3(
        kind="source_scope_extension_v3",
        event_id=uuid4(),
        sequence=len(turn.graph_context_execution.events),
        origin_graph_event_id=op.event_id,
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        world_id=turn.world_id,
        native_world_id=authority.native_world_id,
        binding_version=authority.binding_version,
        campaign_id=None,
        graph_revision=authority.graph_revision,
        retrieval_session_id=receipt.retrieval_session_id,
        pins=[pin],
    )
    turn, _ = service.extend_source_scope(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        extension=ext,
    )
    auth = auth.model_copy(
        update={"sequence": len(turn.graph_context_execution.events)}
    )
    turn, _ = service.authorize_source_read(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        authorization=auth,
    )
    done = settled_read(auth, len(turn.graph_context_execution.events), counts=[38])
    turn, _ = service.record_validated_source_read(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        receipt=done,
    )
    reopened = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert reopened.graph_context_execution.events[-1] == done
    assert (
        t.source_read_character_usage(
            execution.policy, reopened.graph_context_execution.events
        )
        == 38
    )
