from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.context_trace import TraceGraphTool
from application_state.agent_conversation.context_trace import TraceContextMaterial
from application_state.agent_conversation.context_trace_store import (
    _validate_graph_tool_observation,
)
from application_state.errors import ApplicationStateValidationError


def _graph_tool_observation(**overrides: object) -> TraceGraphTool:
    event_id = uuid4()
    payload: dict[str, object] = {
        "sequence": 0,
        "elapsed_ms": 12.0,
        "kind": "graph_tool",
        "tool_name": "expand_graph_retrieval",
        "execution_event_id": event_id,
        "request_arguments_sha256": "a" * 64,
        "result_packet_sha256": "b" * 64,
        "scope_mode": "campaign",
        "campaign_id": "campaign-1",
        "revision_pin": "graph-r7",
        "request": {
            "operation": "search",
            "query_text": "the ruined watchtower",
            "seed_node_ids": ["node-1"],
            "max_nodes": 8,
            "max_relationships": 16,
            "max_claims": 24,
            "max_source_anchors": 24,
        },
        "result": {
            "outcome": "enough",
            "graph_revision": "graph-r7",
            "coverage_status": "complete",
            "projection_status": "complete",
            "nodes": [{"node_id": "node-2", "label": "Ruined Watchtower", "kind": "location"}],
            "relationship_ids": ["edge-1"],
            "claim_ids": ["claim-1"],
            "evidence_ref_ids": ["evidence-1"],
            "returned_counts": {"nodes": 1, "relationships": 1, "claims": 1, "evidence_refs": 1},
            "total_counts": {"nodes": 1, "relationships": 1, "claims": 1, "evidence_refs": 1},
            "omission_codes": [],
        },
    }
    payload.update(overrides)
    return TraceGraphTool.model_validate(payload)


def test_graph_tool_observation_is_typed_bounded_and_has_no_freeform_payload() -> None:
    observation = _graph_tool_observation()
    assert observation.request.operation == "search"
    assert observation.request.query_text == "the ruined watchtower"
    assert observation.result.nodes[0].node_id == "node-2"

    with pytest.raises(ValidationError):
        TraceGraphTool.model_validate({
            **observation.model_dump(mode="python"),
            "provider_request": {"api_key": "must not be accepted"},
        })
    with pytest.raises(ValidationError, match="limited projection"):
        TraceGraphTool.model_validate({
            **observation.model_dump(mode="python"),
            "result": {
                **observation.result.model_dump(mode="python"),
                "projection_status": "limited",
            },
        })


def test_graph_tool_projection_is_bound_to_authoritative_event_ids_and_revision() -> None:
    observation = _graph_tool_observation()
    event = {
        "kind": "validated_graph_operation",
        "event_id": str(observation.execution_event_id),
        "operation": "expand_graph_retrieval",
        "request_arguments_sha256": "a" * 64,
        "result_packet_sha256": "b" * 64,
        "graph_revision": "graph-r7",
        "coverage_status": "complete",
        "truncated": False,
        "assertion_ids": ["claim-1"],
        "relationship_ids": ["edge-1"],
        "evidence_ref_ids": ["evidence-1"],
    }
    _validate_graph_tool_observation(observation, {"events": [event]})

    changed = observation.model_copy(update={
        "result": observation.result.model_copy(update={"claim_ids": ["other-claim"]}),
    })
    with pytest.raises(ApplicationStateValidationError, match="authoritative execution receipt"):
        _validate_graph_tool_observation(changed, {"events": [event]})


def test_limited_graph_tool_projection_names_omitted_results() -> None:
    payload = _graph_tool_observation().model_dump(mode="python")
    payload["result"] = {
        **payload["result"],
        "projection_status": "limited",
        "nodes": [{"node_id": f"node-{i}", "label": f"Node {i}", "kind": "location"} for i in range(64)],
        "returned_counts": {"nodes": 64, "relationships": 1, "claims": 1, "evidence_refs": 1},
        "total_counts": {"nodes": 65, "relationships": 1, "claims": 1, "evidence_refs": 1},
        "omission_codes": ["node_projection_limit"],
    }
    observation = TraceGraphTool.model_validate(payload)
    assert observation.result.projection_status == "limited"
    assert observation.result.omission_codes == ["node_projection_limit"]


def test_historical_material_is_exclusive_and_legacy_serialization_is_unchanged() -> None:
    legacy = TraceContextMaterial(item_id="question", state="model_context", role="user", text="Question")
    assert "historical_source_reads" not in legacy.model_dump(mode="json", by_alias=True)
    ref = {"world_id": "world", "conversation_id": uuid4(), "turn_id": uuid4(), "attempt": 1,
           "trace_id": uuid4(), "source_read_event_id": uuid4(), "source_read_id": "read-1", "content_sha256": "a" * 64}
    material = TraceContextMaterial(item_id="history", state="model_context", role="source", historical_source_reads=[ref])
    assert material.model_dump(mode="json")["historical_source_reads"][0]["source_read_id"] == "read-1"
    for overrides in ({"text": "arbitrary source text"},
                      {"source_read_event_id": uuid4(), "source_reads": [{"source_read_id": "current", "content_sha256": "a" * 64}]}):
        with pytest.raises(ValidationError, match="present source material"):
            TraceContextMaterial.model_validate({**material.model_dump(mode="python"), **overrides})


def _authored_trace_fixture():
    from datetime import datetime, UTC
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferencesV1
    from application_state.agent_conversation.context_trace import TraceAuthoredGraphReferenceV1, TurnContextTraceV1
    captured = t.BuildAuthoredReferencesCapturedV1(kind='build_authored_references_captured_v1', event_id=uuid4(), sequence=0,
        references=AuthoredGraphReferencesV1(references=()), read_graph_revision='revision', turn_id=uuid4(), conversation_id=uuid4(), attempt=1, submitted_intent_fingerprint='a'*64)
    trace = TurnContextTraceV1(trace_id=uuid4(), world_id='world', conversation_id=captured.conversation_id,
        turn_id=captured.turn_id, attempt=1, started_at=datetime.now(UTC), execution_start_sequence=4, observations=[])
    observation = TraceAuthoredGraphReferenceV1(sequence=0, elapsed_ms=1, execution_event=captured)
    return captured, trace, observation


def test_authored_trace_accepts_only_its_closed_event_subset_and_exact_ledger_membership():
    from application_state.agent_conversation.context_trace import TraceAuthoredGraphReferenceV1
    from application_state.agent_conversation.context_trace_store import validate_authored_reference_observation
    captured, trace, observation = _authored_trace_fixture()
    ledger = {'events': [captured.model_dump(mode='json', by_alias=True)]}
    # The capture can precede this physical trace's execution start.
    validate_authored_reference_observation(observation, ledger, trace)
    validate_authored_reference_observation(observation, ledger, trace.model_copy(update={'observations':[observation]}))
    with pytest.raises(ApplicationStateValidationError, match='already has an observation'):
        validate_authored_reference_observation(observation.model_copy(update={'sequence':1}), ledger, trace.model_copy(update={'observations':[observation]}))
    for changed in ({'sequence':9}, {'event_id':uuid4()}, {'read_graph_revision':'different'}, {'submitted_intent_fingerprint':'b'*64}):
        invalid=observation.model_copy(update={'execution_event':captured.model_copy(update=changed)})
        with pytest.raises(ApplicationStateValidationError, match='exact turn ledger'):
            validate_authored_reference_observation(invalid, ledger, trace)
    with pytest.raises(ApplicationStateValidationError, match='exact turn ledger'):
        validate_authored_reference_observation(observation, {'events':[{**ledger['events'][0], 'sequence':0.0}]}, trace)
    with pytest.raises(ApplicationStateValidationError, match='another trace owner'):
        validate_authored_reference_observation(observation, ledger, trace.model_copy(update={'turn_id':uuid4()}))
    with pytest.raises(ValidationError):
        TraceAuthoredGraphReferenceV1.model_validate({'kind':'authored_graph_reference_v1','sequence':0,'elapsed_ms':0,'execution_event':{'kind':'build_draft_provider_inclusion_v1'}})
    with pytest.raises(ValidationError):
        TraceAuthoredGraphReferenceV1.model_validate({**observation.model_dump(mode='json'),'source_body':'unrelated prose'})


@pytest.mark.parametrize('kind', ['authorized', 'read', 'inclusion'])
def test_authored_trace_rejects_prior_physical_work_but_accepts_start_boundary(kind):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.context_trace import TraceAuthoredGraphReferenceV1
    from application_state.agent_conversation.context_trace_store import validate_authored_reference_observation
    captured, trace, _ = _authored_trace_fixture()
    common = dict(event_id=uuid4(), sequence=trace.execution_start_sequence, capture_event_id=captured.event_id)
    if kind == 'authorized':
        event = t.BuildAuthoredReferenceAuthorizedV1(**common, kind='build_authored_reference_authorized_v1', node_id='node', arguments_sha256='a'*64)
    elif kind == 'read':
        event = t.BuildAuthoredReferenceReadV1(**common, kind='build_authored_reference_read_v1', node_id='node', authorization_event_id=uuid4(), operation_event_ids=[], source_read_event_ids=[], returned_node_ids=['node'], outcome='read')
    else:
        event = t.BuildAuthoredProviderInclusionV1(**common, kind='build_authored_provider_inclusion_v1', references_sha256='a'*64, source_read_event_ids=[], provider_attempt_id=uuid4(), envelope_sha256='b'*64, material_sha256='c'*64)
    observation = TraceAuthoredGraphReferenceV1(sequence=0, elapsed_ms=1, execution_event=event)
    validate_authored_reference_observation(observation, {'events':[event.model_dump(mode='json', by_alias=True)]}, trace)
    old = event.model_copy(update={'sequence':trace.execution_start_sequence-1})
    with pytest.raises(ApplicationStateValidationError, match='predates this physical attempt'):
        validate_authored_reference_observation(observation.model_copy(update={'execution_event':old}), {'events':[old.model_dump(mode='json', by_alias=True)]}, trace)
