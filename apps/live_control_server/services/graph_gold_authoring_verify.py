"""Read-only verification of committed graph gold-authoring operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_gold_authoring_commit import GraphGoldAuthoringCommittedOperation
from apps.live_control_server.services.graph_gold_review import GraphGoldReviewError, _session_entry, build_gold_graph_projection

REQUEST_SCHEMA = "dmb_graph_gold_authoring_verify_commit_request_v1"
RESPONSE_SCHEMA = "dmb_graph_gold_authoring_verify_commit_response_v1"


class GraphGoldAuthoringVerifyCommitRequest(BaseModel):
    schema: Literal["dmb_graph_gold_authoring_verify_commit_request_v1"] = REQUEST_SCHEMA
    campaign_id: str
    session_id: str
    commit_id: str
    applied_operations: list[GraphGoldAuthoringCommittedOperation] = Field(default_factory=list)


class GraphGoldAuthoringVerifiedOperation(BaseModel):
    operation_id: str
    operation_type: str
    source_proposal_id: str
    target_id: str | None = None
    verification_status: Literal[
        "found_in_gold_projection",
        "found_in_fixture_only",
        "recorded_event_only",
        "not_expected_in_projection",
        "missing",
    ]
    summary: str


class GraphGoldAuthoringVerifyDiagnostic(BaseModel):
    code: str
    message: str
    operation_id: str | None = None
    severity: Literal["error", "warning", "info"] = "info"


class GraphGoldAuthoringVerifyCommitResponse(BaseModel):
    schema: Literal["dmb_graph_gold_authoring_verify_commit_response_v1"] = RESPONSE_SCHEMA
    campaign_id: str
    session_id: str
    commit_id: str
    verification_status: Literal["verified", "partial", "missing", "blocked"]
    checked_operations: list[GraphGoldAuthoringVerifiedOperation] = Field(default_factory=list)
    diagnostics: list[GraphGoldAuthoringVerifyDiagnostic] = Field(default_factory=list)


def _diag(code: str, message: str, operation_id: str | None = None, severity: Literal["error", "warning", "info"] = "info") -> GraphGoldAuthoringVerifyDiagnostic:
    return GraphGoldAuthoringVerifyDiagnostic(code=code, message=message, operation_id=operation_id, severity=severity)


def _event_contains_commit(event_log: Path, commit_id: str) -> bool:
    if not event_log.exists():
        return False
    for line in event_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            if json.loads(line).get("commit_id") == commit_id:
                return True
        except json.JSONDecodeError:
            continue
    return False


def verify_graph_gold_authoring_commit(request: GraphGoldAuthoringVerifyCommitRequest, *, root: Path | None = None) -> GraphGoldAuthoringVerifyCommitResponse:
    repo = (root or repo_root()).resolve()
    entry = _session_entry(request.session_id)
    if entry["campaign_id"] is not None and entry["campaign_id"] != request.campaign_id:
        raise GraphGoldReviewError(f"session {request.session_id} belongs to {entry['campaign_id']}, not {request.campaign_id}", status_code=422)

    fixture_relpath = str(entry["gold_dir_rel"]) + "/candidate_graph_gold.json"
    fixture_path = repo / fixture_relpath
    try:
        graph: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GraphGoldReviewError(f"path does not exist: {fixture_relpath}", status_code=404) from exc

    node_ids = {str(n.get("node_id")) for n in graph.get("nodes", []) if isinstance(n, dict) and n.get("node_id")}
    edge_ids = {str(e.get("edge_id")) for e in graph.get("edges", []) if isinstance(e, dict) and e.get("edge_id")}
    projection_node_ids: set[str] = set()
    projection_edge_ids: set[str] = set()
    diagnostics: list[GraphGoldAuthoringVerifyDiagnostic] = []
    try:
        projection = build_gold_graph_projection(campaign_id=request.campaign_id, session_id=request.session_id, root=repo)
        projection_node_ids = set(projection.node_views.keys())
        for view in projection.node_views.values():
            projection_edge_ids.update(str(adj.edge_id) for adj in view.adjacency if adj.edge_id)
    except Exception as exc:  # projection errors should not hide fixture verification
        diagnostics.append(_diag("projection_unavailable", f"Gold projection could not be built during verification: {exc}", severity="warning"))

    event_log = fixture_path.parent / "authoring_events.jsonl"
    event_found = _event_contains_commit(event_log, request.commit_id)
    if not event_found:
        diagnostics.append(_diag("commit_event_missing", f"Commit {request.commit_id} was not found in the authoring event log.", severity="warning"))

    checked: list[GraphGoldAuthoringVerifiedOperation] = []
    for op in request.applied_operations:
        status: Literal["found_in_gold_projection", "found_in_fixture_only", "recorded_event_only", "not_expected_in_projection", "missing"]
        target = op.target_id
        if op.operation_type == "add_node" and target:
            if target in projection_node_ids:
                status = "found_in_gold_projection"
                summary = "Committed node found in gold projection."
            elif target in node_ids:
                status = "found_in_fixture_only"
                summary = "Committed node found in gold fixture, but not anchored in projection."
            else:
                status = "missing"
                summary = "Committed node was not found in the gold fixture or projection."
        elif op.operation_type == "add_edge" and target:
            if target in projection_edge_ids:
                status = "found_in_gold_projection"
                summary = "Committed edge found in gold projection adjacency."
            elif target in edge_ids:
                status = "found_in_fixture_only"
                summary = "Committed edge found in gold fixture, but not projected as adjacency."
            else:
                status = "missing"
                summary = "Committed edge was not found in the gold fixture or projection."
        elif op.operation_type in {"assert_node", "link_existing_intent"}:
            status = "recorded_event_only" if event_found else "missing"
            summary = "Recorded in authoring event log only; no identity link was written." if op.operation_type == "link_existing_intent" else "Recorded in authoring event log only."
        else:
            status = "not_expected_in_projection"
            summary = "Operation is not expected to appear in the gold projection."
        if status == "missing":
            diagnostics.append(_diag("operation_missing", summary, op.operation_id, severity="error"))
        checked.append(GraphGoldAuthoringVerifiedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=op.source_proposal_id, target_id=target, verification_status=status, summary=summary))

    if not checked:
        overall: Literal["verified", "partial", "missing", "blocked"] = "blocked"
        diagnostics.append(_diag("no_operations_to_verify", "No applied operations were provided for verification.", severity="warning"))
    elif all(item.verification_status == "missing" for item in checked):
        overall = "missing"
    elif any(item.verification_status == "missing" for item in checked) or any(item.verification_status in {"found_in_fixture_only", "recorded_event_only", "not_expected_in_projection"} for item in checked):
        overall = "partial"
    else:
        overall = "verified"
    return GraphGoldAuthoringVerifyCommitResponse(campaign_id=request.campaign_id, session_id=request.session_id, commit_id=request.commit_id, verification_status=overall, checked_operations=checked, diagnostics=diagnostics)
