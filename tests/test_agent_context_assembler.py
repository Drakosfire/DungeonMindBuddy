"""Owning tests for A5 ContextAssembler v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.live_control_server.services.agent_context_assembler import (
    CONTEXT_SUMMARY_KEYS,
    CONTEXT_SUMMARY_SCHEMA,
    AgentContextAssemblyError,
    assemble_agent_graph_context,
)
from apps.live_control_server.services.agent_runtime import WORLD_GRAPH_READ_POLICY
from apps.live_control_server.services.hermes_graph_query import (
    HermesGraphQueryRequestError,
    build_hermes_graph_turn_request,
)
from graph_memory.interaction.initial_resolve import create_session_from_preflight

SECRET_QUESTION = "SECRET-QUESTION-BODY-a5-privacy-9f3c"
SECRET_HISTORY = "SECRET-HISTORY-CONTENT-a5-privacy-7b2e"
SECRET_EXCERPT = "SECRET-ADMITTED-RECAP-EXCERPT-a5-privacy-4d1a"

READY_ENVELOPE: dict[str, Any] = {
    "schema": "dmb_agent_world_graph_query_context_v1",
    "status": "ready",
    "world_id": "world:eldyrwild",
    "campaign_id": "campaign:c1",
    "revision_id": "revision:resolved-server",
    "head_revision_id": "revision:resolved-server",
    "is_head": True,
    "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
    "admissibility": "gm",
    "query_text": SECRET_QUESTION,
    "matched_node_ids": ["threat:tripod-null-calf"],
    "nodes": [],
    "relationships": [],
    "attributes": [],
    "projection_truncated": False,
    "diagnostics": [],
    "warning_codes": [],
    "trust_boundary": {
        "graph_role": "structured_campaign_memory_and_navigation",
        "citation_authority": "corpus_source_evidence",
        "graph_citations_permitted": False,
    },
}


def _assert_summary_privacy(summary: dict[str, Any], *secrets: str) -> None:
    blob = json.dumps(summary, sort_keys=True, default=str)
    for secret in secrets:
        assert secret not in blob
    assert set(summary) == CONTEXT_SUMMARY_KEYS
    assert summary["context_schema"] == CONTEXT_SUMMARY_SCHEMA
    for value in summary.values():
        assert value is None or isinstance(value, (str, int, bool))


def test_world_scope_and_invocation_parity(tmp_path: Path) -> None:
    assembly = assemble_agent_graph_context(
        question=SECRET_QUESTION,
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
        conversation_history=[
            {"role": "user", "content": SECRET_HISTORY},
            {"role": "assistant", "content": "prior answer"},
        ],
        runtime_session_id="continuity-session-1",
        thread_id="thread-1",
        turn_id="turn-1",
    )
    inv = assembly.invocation
    scope = inv.context_packet.world_scope
    assert scope.world_id == "world:eldyrwild"
    assert scope.campaign_id == "campaign:c1"
    assert scope.revision_id == "revision:resolved-server"
    assert scope.admissibility == "gm"
    assert scope.focus == {
        "kind": "session",
        "session_id": "session-21",
        "campaign_id": None,
    }
    assert inv.message == SECRET_QUESTION
    assert inv.thread_id == "thread-1"
    assert inv.turn_id == "turn-1"
    assert inv.conversation_history == [
        {"role": "user", "content": SECRET_HISTORY},
        {"role": "assistant", "content": "prior answer"},
    ]
    assert inv.capability_policy.policy_id == WORLD_GRAPH_READ_POLICY.policy_id
    assert inv.run_options.runtime_session_id == "continuity-session-1"
    assert inv.run_options.execution_root == tmp_path.resolve()
    assert inv.context_packet.retrieval_session is not None
    assert inv.context_packet.retrieval_session.session_id
    assert inv.context_packet.retrieval_session.packet["retrieval_session_id"] == (
        inv.context_packet.retrieval_session.session_id
    )
    summary = dict(assembly.trace_summary)
    assert summary["history_message_count"] == 2
    assert summary["history_char_count"] == len(SECRET_HISTORY) + len("prior answer")
    assert summary["runtime_continuity_present"] is True
    assert summary["retrieval_candidate_count"] == 1
    _assert_summary_privacy(summary, SECRET_QUESTION, SECRET_HISTORY)


def test_retrieval_session_reuse_preserves_id(tmp_path: Path) -> None:
    session = create_session_from_preflight(READY_ENVELOPE, question="seed")
    session_id = session.id
    assembly = assemble_agent_graph_context(
        question="follow-up",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
        retrieval_session=session,
    )
    retrieval = assembly.invocation.context_packet.retrieval_session
    assert retrieval is not None
    assert retrieval.session_id == session_id
    assert assembly.trace_summary["retrieval_session_id"] == session_id


def test_latest_recap_paths(tmp_path: Path) -> None:
    # no latest_recap_change
    bare = assemble_agent_graph_context(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
    )
    assert bare.trace_summary["latest_recap_change_present"] is False
    assert bare.trace_summary["admitted_recap_excerpt_char_count"] == 0

    recap_path = tmp_path / "Session 24 - Recap.md"
    recap_path.write_text(SECRET_EXCERPT, encoding="utf-8")
    lag_envelope = {
        **READY_ENVELOPE,
        "latest_recap_change": {
            "schema": "dmb_latest_recap_change_context_v1",
            "outcome": "memory_lag",
            "memory_lag": True,
            "latest_recap": {
                "source_recap_path": "Session 24 - Recap.md",
            },
        },
    }
    with_excerpt = assemble_agent_graph_context(
        question="q",
        graph_envelope=lag_envelope,
        root=tmp_path,
        corpus_root=tmp_path,
    )
    packet = with_excerpt.invocation.context_packet.retrieval_session.packet
    assert packet["latest_recap_change"]["admitted_recap_excerpt"] == SECRET_EXCERPT
    assert with_excerpt.trace_summary["latest_recap_change_present"] is True
    assert with_excerpt.trace_summary["admitted_recap_excerpt_char_count"] == len(
        SECRET_EXCERPT
    )
    _assert_summary_privacy(dict(with_excerpt.trace_summary), SECRET_EXCERPT)

    # existing excerpt → no duplicate read
    reader = MagicMock(return_value="SHOULD-NOT-READ")
    session = create_session_from_preflight(lag_envelope, question="q")
    session.latest_recap_change = {
        **dict(lag_envelope["latest_recap_change"]),
        "admitted_recap_excerpt": "already-present-excerpt",
    }
    with patch(
        "graph_memory.interaction.latest_recap.read_admitted_recap_excerpt",
        reader,
    ):
        reused = assemble_agent_graph_context(
            question="q",
            graph_envelope=lag_envelope,
            root=tmp_path,
            corpus_root=tmp_path,
            retrieval_session=session,
        )
    reader.assert_not_called()
    assert (
        reused.invocation.context_packet.retrieval_session.packet[
            "latest_recap_change"
        ]["admitted_recap_excerpt"]
        == "already-present-excerpt"
    )


def test_missing_revision_raises_neutral_error(tmp_path: Path) -> None:
    envelope = {**READY_ENVELOPE, "revision_id": ""}
    with pytest.raises(AgentContextAssemblyError) as excinfo:
        assemble_agent_graph_context(
            question="q",
            graph_envelope=envelope,
            root=tmp_path,
        )
    assert excinfo.value.code == "world_graph_context_invalid"


def test_compatibility_wrapper_translates_errors(tmp_path: Path) -> None:
    with pytest.raises(HermesGraphQueryRequestError) as excinfo:
        build_hermes_graph_turn_request(
            question="q",
            graph_envelope={**READY_ENVELOPE, "world_id": ""},
            root=tmp_path,
        )
    assert excinfo.value.code == "world_graph_context_invalid"

    inv, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
    )
    assert inv.context_packet.world_scope.revision_id == scope.revision_id
    assert scope.world_id == "world:eldyrwild"
    assert inv.context_packet.surface_context is None


def test_assembler_carries_resolved_surface_context(tmp_path: Path) -> None:
    from apps.live_control_server.services.agent_runtime import (
        AgentCurrentWorkContext,
        AgentSurfaceContext,
    )

    surface = AgentSurfaceContext(
        surface_id="plan",
        current_work=AgentCurrentWorkContext(
            kind="plan",
            work_object_id="doc-1",
            title="SECRET-TITLE-a6",
            object_revision=2,
            target_session=27,
        ),
    )
    assembly = assemble_agent_graph_context(
        question="What does Lysandra know about the swarm?",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
        surface_context=surface,
    )
    assert assembly.invocation.context_packet.surface_context is surface
    assert assembly.invocation.message == "What does Lysandra know about the swarm?"
    # A5 summary unchanged — no surface keys leaked into context_assembly telemetry
    assert set(assembly.trace_summary) == CONTEXT_SUMMARY_KEYS
    _assert_summary_privacy(dict(assembly.trace_summary), "SECRET-TITLE-a6")

    inv, _scope = build_hermes_graph_turn_request(
        question="What does Lysandra know about the swarm?",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
        surface_context=surface,
    )
    assert inv.context_packet.surface_context is surface
    assert inv.message == "What does Lysandra know about the swarm?"
    world_only = build_hermes_graph_turn_request(
        question="What does Lysandra know about the swarm?",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
    )[0]
    assert world_only.context_packet.world_scope == inv.context_packet.world_scope
    assert world_only.context_packet.surface_context is None
