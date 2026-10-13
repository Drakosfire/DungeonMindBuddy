from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.context_trace import TraceGraphTool
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
