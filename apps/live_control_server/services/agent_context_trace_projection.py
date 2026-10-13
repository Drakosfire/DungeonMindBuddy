"""Allowlisted observations of actual broker requests and validated results.

These projections do not alter the model's retrieval payload or grant evidence
authority. Projection limits describe omissions explicitly; source text belongs
to APP-STATE's separately validated passage snapshots.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from application_state.agent_conversation.types import ValidatedGraphOperationEventV1
from graph_memory.retrieval.models import (
    WorldGraphEvidenceRequest, WorldGraphNeighborhoodRequest, WorldGraphObjectRequest,
    WorldGraphRetrievalResult, WorldGraphSearchRequest,
)


def graph_operation_observation(
    *, request: WorldGraphSearchRequest | WorldGraphObjectRequest
    | WorldGraphNeighborhoodRequest | WorldGraphEvidenceRequest,
    result: WorldGraphRetrievalResult, result_payload: Mapping[str, Any],
    execution_event: ValidatedGraphOperationEventV1, sequence: int,
    elapsed_ms: float, duration_ms: float,
) -> dict[str, Any]:
    """Project observed effective inputs, not child-supplied defaults/scope."""
    encoded = json.dumps(result_payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != execution_event.result_packet_sha256:
        raise ValueError("trace result differs from its validated execution event")
    if any(result_payload.get(key) != value for key, value in result.model_dump(mode="json", by_alias=True).items()):
        raise ValueError("trace typed result differs from its broker payload")
    if (result.snapshot is None or result.snapshot.revision_id != execution_event.graph_revision
            or request.revision_pin != execution_event.graph_revision
            or result.snapshot.world_id != request.world_id):
        raise ValueError("trace request/result revision differs from its execution event")
    assertions = sorted({item.assertion_id for item in result.attributes})
    relationships = sorted({item.edge_id for item in result.relationships})
    evidence = sorted({item.evidence_ref_id for item in result.source_anchors if item.evidence_ref_id})
    if (assertions != sorted(execution_event.assertion_ids)
            or relationships != sorted(execution_event.relationship_ids)
            or evidence != sorted(execution_event.evidence_ref_ids)):
        raise ValueError("trace result identifiers differ from its execution event")
    bounds = request.bounds
    observed: dict[str, Any] = {"max_source_anchors": bounds.max_source_anchors}
    if not isinstance(request, WorldGraphEvidenceRequest):
        observed.update(max_nodes=bounds.max_nodes,
                        max_relationships=bounds.max_relationships,
                        max_claims=bounds.max_attributes)
    if isinstance(request, WorldGraphSearchRequest):
        observed.update(operation="search", query_text=request.query_text,
                        seed_node_ids=list(request.seed_node_ids))
    elif isinstance(request, WorldGraphObjectRequest):
        observed.update(operation="object", target_node_id=request.node_id)
    elif isinstance(request, WorldGraphNeighborhoodRequest):
        observed.update(operation="neighborhood", seed_node_ids=list(request.seed_node_ids),
                        depth=request.max_depth)
    else:
        observed.update(operation="support", target_node_id=request.target.id)
    expected_operation = "evidence" if observed["operation"] == "support" else observed["operation"]
    if result.operation != expected_operation:
        raise ValueError("trace result operation differs from its effective request")
    all_nodes = [{"node_id": item.node_id, "label": item.label, "kind": item.kind}
                 for item in result.nodes]
    projected = {"nodes": all_nodes[:64], "relationships": relationships[:128],
                 "claims": assertions[:128], "evidence_refs": evidence[:128]}
    totals = {"nodes": len(all_nodes), "relationships": len(relationships),
              "claims": len(assertions), "evidence_refs": len(evidence)}
    returned = {key: len(value) for key, value in projected.items()}
    omissions = [f"trace_{key}_limit" for key in totals if totals[key] > returned[key]]
    return {
        "kind": "graph_tool", "sequence": sequence, "elapsed_ms": elapsed_ms,
        "tool_name": "expand_graph_retrieval", "execution_event_id": str(execution_event.event_id),
        "request_arguments_sha256": execution_event.request_arguments_sha256,
        "result_packet_sha256": execution_event.result_packet_sha256,
        "scope_mode": request.scope_mode,
        "campaign_id": request.campaign_id if request.scope_mode == "campaign" else None,
        "revision_pin": execution_event.graph_revision, "request": observed,
        "result": {
            "outcome": result.outcome, "graph_revision": execution_event.graph_revision,
            "coverage_status": execution_event.coverage_status,
            "projection_status": "limited" if omissions else "complete",
            "nodes": projected["nodes"], "relationship_ids": projected["relationships"],
            "claim_ids": projected["claims"], "evidence_ref_ids": projected["evidence_refs"],
            "returned_counts": returned, "total_counts": totals, "omission_codes": omissions,
        },
        "duration_ms": duration_ms,
    }
