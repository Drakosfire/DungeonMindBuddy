"""Build primary page and a distinct World source through real SDK/APP gates."""

import json
from dataclasses import replace
from types import SimpleNamespace

import httpx2
import pytest

from application_state.agent_conversation import AgentConversationService, types as t
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    WriterWire,
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class WorldDecisions(DecisionWire):
    def __init__(self):
        super().__init__()
        self.opened_world = False

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body, data = json.loads(request.content), response.json()
        for key, answer in data["answers"].items():
            labels = body["questions"][key].get("criteria", {})
            chosen = None
            if key == "next":
                chosen = next((v for v in labels if v.startswith("saved:")), None)
                chosen = chosen or next(
                    (v for v in labels if v.startswith("world-object:")),
                    "world-search" if "world-search" in labels else "none",
                )
                self.opened_world |= chosen.startswith("world-object:")
            elif key.startswith("use_") and any(
                kind in body["questions"][key].get("instructions", "")
                for kind in ("world-object:", "world-search")
            ):
                chosen = "useful"
                self.opened_world |= "world-object:" in body["questions"][key].get(
                    "instructions", ""
                )
            elif key == "sufficiency":
                chosen = "sufficient" if self.opened_world else "more_evidence"
            if chosen is not None:
                answer.update(
                    choice=chosen, probabilities={v: float(v == chosen) for v in labels}
                )
        return httpx2.Response(200, request=request, json=data)


def world_case(build_case, monkeypatch):
    case, reads = ordinary_case(build_case, monkeypatch)
    source, request, bootstrap = case
    from graph_memory.interaction.session import GraphReferent

    bootstrap.retrieval_session.referents = [
        GraphReferent(id="frank", label="River Watch")
    ]
    bootstrap = replace(
        bootstrap,
        navigation_candidates=(("frank", "River Watch"),),
        completed_discovery_query=request.message,
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as native,
    )
    from graph_memory.interaction import expansion_executor

    original_graph = native.get_object_with_reviewed_sources_direct_v3
    artifact = "artifact:synthetic:river-watch"

    def graph(*args, **kwargs):
        value = original_graph(*args, **kwargs)
        return replace(
            value,
            result=value.result.model_copy(
                update={
                    "source_anchors": [
                        anchor.model_copy(update={"source_artifact_id": artifact})
                        for anchor in value.result.source_anchors
                    ]
                }
            ),
            source_pins=tuple(
                SimpleNamespace(**{**vars(pin), "source_artifact_id": artifact})
                for pin in value.source_pins
            ),
            reviewed_source_observations=tuple(
                row.model_copy(update={"source_artifact_id": artifact})
                for row in value.reviewed_source_observations
            ),
        )

    monkeypatch.setattr(native, "get_object_with_reviewed_sources_direct_v3", graph)
    original_read = expansion_executor.execute_read_graph_source

    def read(*args, **kwargs):
        value = original_read(*args, **kwargs)
        for row in value["reads"]:
            row["result"].update(
                sourceArtifactId=artifact, sourceName="River Watch — synthetic source"
            )
            row["receipt"]["source_artifact_id"] = artifact
        return value

    monkeypatch.setattr(expansion_executor, "execute_read_graph_source", read)
    return (source, request, bootstrap), reads


@pytest.fixture(params=[False, True], ids=["retained-world", "named-world"])
def world_completed(build_case, monkeypatch, tmp_path, request):
    case, reads = world_case(build_case, monkeypatch)
    decisions, writer = WorldDecisions(), WriterWire()
    harness = BuildJevHarness(
        world_context=True,
        named_citations=request.param,
        decision_transport=decisions,
        writer_transport=writer,
        accounting=counter(),
    )
    response = execute(case, tmp_path, harness)
    assert response.answer.status == "ok"
    service = AgentConversationService()
    (turn,) = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )
    return turn, writer, decisions, reads, harness.adapter


def test_primary_and_distinct_world_passage_reach_named_writer(world_completed):
    turn, writer, decisions, reads, adapter = world_completed
    service = AgentConversationService()
    execution = turn.graph_context_execution
    assert isinstance(execution.policy, t.BuildWorldContextPolicyV1)
    selections = [
        e for e in execution.events if isinstance(e, t.BuildWorldReadSelectionV1)
    ]
    assert len(selections) == 1, json.dumps(
        [
            {
                k: q.get("criteria")
                for k, q in json.loads(call.content)["questions"].items()
            }
            for call in decisions.calls
        ]
    )
    assert selections[0].actions[0].action_id == "world-object:frank"
    assert reads == {"graph": 1, "source": 1}
    assert len(writer.calls) == 1
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["artifact_under_edit"]["sections"]
    assert packet["exposure"]["saved_sections"] == []
    assert (
        packet["opened_passages"][0]["source_artifact_id"]
        == "artifact:synthetic:river-watch"
    )
    assert (
        packet["opened_passages"][0]["source_name"] == "River Watch — synthetic source"
    )
    assert turn.completion.source_citations
    named = getattr(execution.policy, "source_citation_names_policy", None) is not None
    assert isinstance(turn.completion, t.BuildNamedGraphCompletionV3) == named
    if named:
        assert {c.source_name for c in turn.completion.source_citations} == {
            "River Watch — synthetic source"
        }
    assert service.inspect_turn(world_id="elderwyld", turn_id=turn.turn_id) == turn


@pytest.mark.parametrize("tamper", ["body", "artifact", "range", "name"])
def test_world_passage_or_name_tampering_is_refused(world_completed, tamper):
    from copy import deepcopy
    from application_state.agent_conversation.build_world_context import (
        opened_world_passages,
        verify_named_input,
    )

    turn, writer, decisions, reads, adapter = world_completed
    execution = turn.graph_context_execution
    operations = [
        str(e.event_id)
        for e in execution.events
        if isinstance(e, t.ValidatedGraphOperationEventV3)
    ]
    events = [
        e for e in execution.events if isinstance(e, t.ValidatedSourceReadEventV2)
    ]
    payloads = deepcopy(adapter.source_payloads)
    raw = json.loads(payloads[events[0].event_id])
    if tamper == "name":
        packet = json.loads(json.loads(writer.calls[0].content)["input"])
        packet["opened_passages"][0]["source_name"] = "Invented display name"
        trace = (
            AgentConversationService()
            .list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[
                -1
            ]
            .model_dump(mode="json")
        )
        with pytest.raises(ValueError, match="source name"):
            verify_named_input(packet, turn, trace)
        return
    row = raw.get("reads", [raw])[0]
    row[
        {"body": "content", "artifact": "sourceArtifactId", "range": "lineEnd"}[tamper]
    ] = {"body": "Unopened replacement", "artifact": "foreign-artifact", "range": 999}[
        tamper
    ]
    payloads[events[0].event_id] = json.dumps(raw)
    with pytest.raises(ValueError, match="differs"):
        opened_world_passages(
            execution,
            operations,
            [str(e.event_id) for e in events],
            adapter.operation_payloads,
            payloads,
        )


def test_world_operation_requires_its_prior_controller_selection(world_completed):
    from application_state.agent_conversation.build_world_context import (
        opened_world_passages,
    )

    turn, _, _, _, adapter = world_completed
    execution = turn.graph_context_execution
    operations = [
        str(e.event_id)
        for e in execution.events
        if isinstance(e, t.ValidatedGraphOperationEventV3)
    ]
    reads = [
        str(e.event_id)
        for e in execution.events
        if isinstance(e, t.ValidatedSourceReadEventV2)
    ]
    changed = execution.model_copy(
        update={
            "events": [
                e
                for e in execution.events
                if not isinstance(e, t.BuildWorldReadSelectionV1)
            ]
        }
    )
    with pytest.raises(ValueError, match="selected current object operation"):
        opened_world_passages(
            changed,
            operations,
            reads,
            adapter.operation_payloads,
            adapter.source_payloads,
        )


def test_search_discovers_then_opens_a_new_world_candidate(
    build_case, monkeypatch, tmp_path
):
    case, reads = world_case(build_case, monkeypatch)
    source, request, bootstrap = case
    bootstrap.retrieval_session.referents = []
    bootstrap = replace(
        bootstrap, navigation_candidates=(), completed_discovery_query=None
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as native,
    )
    from graph_memory.retrieval.models import WorldGraphRetrievalNode

    original = native.get_object_with_reviewed_sources_direct_v3

    def search(*args, **kwargs):
        base = original(*args, **kwargs).result
        result = base.model_copy(
            update={
                "operation": "search",
                "requested_node_id": None,
                "source_anchors": [],
                "reviewed_source_observations": [],
                "nodes": [
                    WorldGraphRetrievalNode(
                        node_id="frank",
                        label="River Watch",
                        kind="location",
                        role="match",
                    )
                ],
            }
        )
        return native.ResolvedWorldGraphOperationV3(result=result, source_pins=())

    monkeypatch.setattr(native, "search_world_graph_direct_v3", search)
    decisions, writer = WorldDecisions(), WriterWire()
    harness = BuildJevHarness(
        world_context=True,
        decision_transport=decisions,
        writer_transport=writer,
        accounting=counter(),
    )
    execute((source, request, bootstrap), tmp_path, harness)
    execution = harness.adapter._broker_execution()
    selections = [
        e for e in execution.events if isinstance(e, t.BuildWorldReadSelectionV1)
    ]
    assert [a.operation for e in selections for a in e.actions] == ["search", "object"]
    assert len(writer.calls) == 1
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert len(packet["opened_passages"]) == 1
    assert (
        packet["opened_passages"][0]["source_name"] == "River Watch — synthetic source"
    )


def test_partial_world_read_cannot_become_writer_evidence(
    build_case, monkeypatch, tmp_path
):
    from tests.test_build_writer_selection import SavedWriter
    from graph_memory.interaction import expansion_executor

    case, reads = world_case(build_case, monkeypatch)
    original = expansion_executor.execute_read_graph_source

    def partial(*args, **kwargs):
        value = original(*args, **kwargs)
        for row in value["reads"]:
            row["result"].update(outcome="partial")
            row["receipt"].update(outcome="partial")
        return value

    monkeypatch.setattr(expansion_executor, "execute_read_graph_source", partial)
    decisions, writer = WorldDecisions(), SavedWriter()
    harness = BuildJevHarness(
        world_context=True,
        decision_transport=decisions,
        writer_transport=writer,
        accounting=counter(),
    )
    execute(case, tmp_path, harness)
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["opened_passages"] == []
    assert packet["artifact_under_edit"]["sections"]
    execution = harness.adapter._broker_execution()
    assert any(
        r.outcome == "partial"
        for e in execution.events
        if isinstance(e, t.ValidatedSourceReadEventV2)
        for r in e.receipts
    )
    assert reads == {"graph": 1, "source": 1}


@pytest.mark.parametrize(
    "mode", ["unselected", "stale", "unknown", "changed", "repeated", "native_failure"]
)
def test_world_broker_refuses_invalid_selection_before_native_io(
    world_completed, monkeypatch, mode
):
    from application_state.agent_conversation.build_world_context import (
        request_arguments,
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as native,
    )

    turn, _, _, _, adapter = world_completed
    execution = turn.graph_context_execution
    selection = next(
        e for e in execution.events if isinstance(e, t.BuildWorldReadSelectionV1)
    )
    args = request_arguments(turn, selection.actions[0])
    events = list(execution.events)
    if mode != "stale":
        stop = selection.sequence + 1
        if mode == "repeated":
            operation = next(
                e
                for e in events
                if isinstance(e, t.ValidatedGraphOperationEventV3)
                and e.request_arguments_sha256
                == selection.actions[0].request_arguments_sha256
            )
            stop = operation.sequence + 1
        events = events[:stop]
        if mode == "unselected":
            events = [
                e for e in events if not isinstance(e, t.BuildWorldReadSelectionV1)
            ]
        elif mode == "unknown":
            events = [
                e.model_copy(update={"outcome": "unknown"})
                if isinstance(e, t.ProviderOutcomeEventV1)
                and e.provider_attempt_id == selection.controller_attempt_id
                else e
                for e in events
            ]
        elif mode == "changed":
            args = {**args, "targets": [{"kind": "node", "id": "another-node"}]}
    snapshot = turn.model_copy(
        update={
            "status": "running",
            "graph_context_execution": execution.model_copy(update={"events": events}),
        }
    )
    monkeypatch.setattr(adapter, "fence", SimpleNamespace(turn=snapshot))
    monkeypatch.setattr(
        adapter,
        "last_provider_attempt_id",
        adapter.last_provider_attempt_id
        if mode == "stale"
        else selection.controller_attempt_id,
    )
    monkeypatch.setattr(
        adapter,
        "_denied_tool_result",
        lambda tool, code, status, *a, **kw: {"code": code, "status": status},
    )
    calls = []

    def forbidden(*a, **kw):
        calls.append(True)
        if mode == "native_failure":
            raise RuntimeError("synthetic indeterminate native read")
        raise AssertionError("unselected native I/O")

    monkeypatch.setattr(native, "get_object_with_reviewed_sources_direct_v3", forbidden)
    result = adapter.broker_graph_operation(
        {"toolName": "expand_graph_retrieval", "arguments": args}
    )
    if mode == "native_failure":
        assert result == {"code": "graph_operation_unavailable", "status": 503}
        assert adapter.failure is not None
        result = adapter.broker_graph_operation(
            {"toolName": "expand_graph_retrieval", "arguments": args}
        )
        assert calls == [True]
    else:
        assert not calls
    assert result == {"code": "build_world_acquisition_not_current", "status": 409}


def test_named_completion_rejects_forged_citation_and_preserves_migration(
    world_completed, application_state_dsn
):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from application_state.agent_conversation.source_writer_output import (
        reconstruct,
        validate_completion_proof,
    )

    turn, writer, _, _, _ = world_completed
    if not isinstance(turn.completion, t.BuildNamedGraphCompletionV3):
        return  # The retained contract is independently reconstructed above.
    trace = (
        AgentConversationService()
        .list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[-1]
        .model_dump(mode="json")
    )
    citation = turn.completion.source_citations[0]
    auth = next(
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV3)
        and e.provider_attempt_id == citation.provider_attempt_id
    )
    raw = next(
        m["text"]
        for o in trace["observations"]
        if o["kind"] == "context_snapshot"
        for m in o.get("materials", [])
        if m["item_id"].startswith("unvalidated-provider-answer:")
    )
    request_json = writer.calls[0].content.decode()
    packet = json.loads(json.loads(request_json)["input"])
    expected, bindings = reconstruct(raw, packet, turn, auth)
    result = t.CitedSourceTurnResult(
        world_id=turn.world_id,
        conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,
        expected_revision=turn.revision,
        assistant_text=turn.assistant_text,
        completion=expected,
        producing_provider_attempt_id=auth.provider_attempt_id,
        claim_graph_event_ids={},
        build_section_bindings=bindings,
        writer_request_json=request_json,
        raw_provider_output_json=raw,
    )
    validate_completion_proof(result, turn, trace)
    forged = expected.model_copy(
        update={
            "source_citations": [
                c.model_copy(update={"source_name": "Invented title"})
                for c in expected.source_citations
            ]
        }
    )
    with pytest.raises(ValueError, match="differs"):
        validate_completion_proof(
            result.model_copy(update={"completion": forged}), turn, trace
        )
    migration = import_module(
        "application_state.migrations.versions.20261023_0058_build_named_source_citations"
    )
    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="retained named Build"):
                    migration.downgrade()
    finally:
        engine.dispose()
