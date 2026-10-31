from __future__ import annotations

import json

import pytest
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

from application_state.agent_conversation.types import (
    GraphExecutionPolicyV3, WorldPointer,
    graph_execution_policy_digest_v3,
)
from application_state.plan_action_dialogue.types import PlanActionBasis
from apps.live_control_server.services.agent_runtime import AgentWorldScope
from apps.live_control_server.services.agent_turn_service import AgentPlanWorldGraphBootstrap
from apps.live_control_server.services.plan_action_consultation import _freeze_action_inputs
from graph_memory.interaction.session import (
    CoverageState, GraphRetrievalSession, SessionSnapshot,
)


def test_saved_plan_consultation_freezes_v3_policy_with_empty_initial_source_scope():
    world_id = "managed-world:one"
    native_world_id = "native-world:one"
    revision = "graph-revision:one"
    action = SimpleNamespace(
        action_id=uuid4(), request_fingerprint="b" * 64,
        basis=PlanActionBasis(
            world_id=world_id, document_id="plan:one", object_revision=4,
            work_revision_id=uuid4(), revision_n=2, content_sha256="a" * 64,
        ),
        draft_matches_basis=True, draft_sha256="a" * 64,
        target_kind="replace_selection", selected_text_sha256="c" * 64,
        instruction="Check this Plan against the published World.",
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=native_world_id, campaign_id="", focus={"kind": "none"},
            admissibility="gm", revision_id=revision, scope_mode="world",
        ),
        question=action.instruction, coverage=CoverageState(state="ready"),
    )
    bootstrap = AgentPlanWorldGraphBootstrap(
        graph_envelope={},
        world_scope=AgentWorldScope(
            world_id=native_world_id, campaign_id="", focus={"kind": "none"},
            admissibility="gm", revision_id=revision, scope_mode="world",
        ),
        retrieval_session=session, binding_version=1,
        candidate_assertion_ids=(),
        candidate_relationship_ids=(), candidate_evidence_ref_ids=(),
        evidence_by_anchor_id={}, source_scope_anchors=(),
    )
    body = {"input": [], "tools": []}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    view = {
        "model": "gpt-6-luna", "payloadJson": payload,
        "payloadSha256": sha256(payload.encode()).hexdigest(),
        "payloadUtf8Bytes": len(payload.encode()),
    }
    budget = {
        "estimator": "utf8_json_bytes_plus_64_per_node_v1",
        "contextLimitTokens": 1_050_000, "outputReserveTokens": 2048,
        "maxProviderAttempts": 4, "maxGraphOperations": 8,
    }
    initial_packet = {
        "candidates": [], "claimLedger": [], "intentHint": None,
        "availableExpansions": [],
    }

    receipt, policy = _freeze_action_inputs(
        action, bootstrap, view, budget, "plan-surface",
        initial_packet, ([], [], []), None, None, (),
        WorldPointer(
            world_id=world_id, active_conversation_id=uuid4(), revision=1,
        ),
    )

    assert isinstance(policy, GraphExecutionPolicyV3)
    assert policy.source_read_scope.admitted_anchors == []
    assert policy.max_source_read_chars == 96_000
    assert policy.max_chars_per_source_read == 12_000
    assert not hasattr(policy, "max_source_read_calls")
    assert receipt.graph_authority.native_world_id == native_world_id
    assert graph_execution_policy_digest_v3(
        receipt.consultation_receipt_sha256, policy,
    )


def _action_adapter_without_ask_request():
    from apps.live_control_server.services.plan_action_consultation import (
        ActionPolicyExecutionAdapter,
    )

    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="native-world",
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_id="revision",
            scope_mode="world",
        ),
        question="Action instruction",
        coverage=CoverageState(state="ready"),
    )
    bootstrap = AgentPlanWorldGraphBootstrap(
        graph_envelope={},
        world_scope=AgentWorldScope(
            world_id="native-world",
            campaign_id="",
            focus={"kind": "none"},
            admissibility="gm",
            revision_id="revision",
            scope_mode="world",
        ),
        retrieval_session=session,
        binding_version=1,
        candidate_assertion_ids=(),
        candidate_relationship_ids=(),
        candidate_evidence_ref_ids=(),
        evidence_by_anchor_id={},
    )
    return ActionPolicyExecutionAdapter(
        store=object(),
        action=SimpleNamespace(basis=SimpleNamespace(world_id="managed-world")),
        bootstrap=bootstrap,
        budget={},
        surface_instance_id="plan",
    )


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("case", ["valid", "invalid", "late"])
def test_action_compaction_observation_never_requires_ask_or_build_authority(
    monkeypatch, capture, case
):
    monkeypatch.delenv("DMB_CONTEXT_TRACE_CAPTURE", raising=False)
    monkeypatch.setenv("DMB_AGENT_PROMPT_CAPTURE", "1" if capture else "0")
    adapter = _action_adapter_without_ask_request()
    assert not hasattr(adapter, "request") and not adapter._is_build_turn()
    payload = {
        "before_visible": [],
        "after_visible": [],
        "prior_sources": [],
        "routes": {},
        "decisions": [],
        "before_chars": 0,
        "after_chars": 0,
    }
    if case == "invalid":
        payload["before_chars"] = -1
    if case == "late":
        adapter.fence = object()
    response = adapter.broker_graph_operation(
        {"toolName": "observe_context_compaction", "arguments": payload}
    )
    assert (
        json.loads(response["resultJson"])["schema"] == "dmb_context_compaction_ack_v1"
    )
    assert (adapter.context_compaction_report is not None) == (
        capture and case == "valid"
    )
    assert adapter.context_compaction_unavailable == (capture and case != "valid")
    assert adapter.context_capture is None and not hasattr(adapter, "request")


def test_action_cannot_acquire_build_driver_or_writer_capabilities():
    adapter = _action_adapter_without_ask_request()
    with pytest.raises(ValueError, match="actual Build turn"):
        adapter.create_build_jev_driver()
    with pytest.raises(ValueError, match="actual Build turn"):
        adapter.stage_build_controller_exposure()
    assert adapter.authorize_prepared_build_writer(object()) is False
    assert adapter.authorize_prepared_build_decision(object()) is False
    with pytest.raises(ValueError, match="No acknowledged writer"):
        adapter.complete_build_writer(object())
    assert not hasattr(adapter, "request")
