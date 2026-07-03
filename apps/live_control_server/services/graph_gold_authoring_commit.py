"""Commit prepared graph gold-authoring previews to fixture JSON."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_gold_authoring_prepare import (
    GraphGoldAuthoringLocalProposal,
    GraphGoldAuthoringPrepareDiagnostic,
    GraphGoldAuthoringPrepareRequest,
    GraphGoldAuthoringPreviewOperation,
    prepare_graph_gold_authoring_preview,
)
from apps.live_control_server.services.graph_gold_review import GraphGoldReviewError, _session_entry

REQUEST_SCHEMA = "dmb_graph_gold_authoring_commit_request_v1"
RESPONSE_SCHEMA = "dmb_graph_gold_authoring_commit_response_v1"
EVENT_SCHEMA = "dmb_graph_gold_authoring_event_v1"


class GraphGoldAuthoringCommitRequest(BaseModel):
    schema: Literal["dmb_graph_gold_authoring_commit_request_v1"] = REQUEST_SCHEMA
    campaign_id: str
    session_id: str
    fixture_version: str | None = None
    proposals: list[GraphGoldAuthoringLocalProposal] = Field(default_factory=list)
    expected_prepare_fingerprint: str | None = None
    commit_message: str | None = None
    operator_note: str | None = None


class GraphGoldAuthoringCommitChangedCounts(BaseModel):
    nodes_added: int = 0
    nodes_asserted: int = 0
    edges_added: int = 0
    link_intents_recorded: int = 0
    operations_skipped: int = 0


class GraphGoldAuthoringCommittedOperation(BaseModel):
    operation_id: str
    operation_type: str
    source_proposal_id: str
    status: Literal["applied", "recorded_assertion", "recorded_intent"]
    target_id: str | None = None
    summary: str


class GraphGoldAuthoringSkippedOperation(BaseModel):
    operation_id: str
    operation_type: str
    source_proposal_id: str
    reason: str
    diagnostics: list[GraphGoldAuthoringPrepareDiagnostic] = Field(default_factory=list)


class GraphGoldAuthoringCommitDiagnostic(BaseModel):
    code: str
    message: str
    source_proposal_id: str | None = None
    severity: Literal["error", "warning", "info"] = "warning"


class GraphGoldAuthoringCommitResponse(BaseModel):
    schema: Literal["dmb_graph_gold_authoring_commit_response_v1"] = RESPONSE_SCHEMA
    campaign_id: str
    session_id: str
    fixture_relpath: str
    backup_relpath: str | None = None
    event_log_relpath: str | None = None
    commit_id: str
    committed_at_iso: str
    commit_status: Literal["committed", "blocked", "partial"]
    prepare_fingerprint: str
    applied_operations: list[GraphGoldAuthoringCommittedOperation] = Field(default_factory=list)
    skipped_operations: list[GraphGoldAuthoringSkippedOperation] = Field(default_factory=list)
    diagnostics: list[GraphGoldAuthoringCommitDiagnostic] = Field(default_factory=list)
    changed_counts: GraphGoldAuthoringCommitChangedCounts = Field(default_factory=GraphGoldAuthoringCommitChangedCounts)


def prepare_fingerprint(request: GraphGoldAuthoringCommitRequest, operations: list[GraphGoldAuthoringPreviewOperation], validation_status: str) -> str:
    payload = {
        "campaign_id": request.campaign_id,
        "session_id": request.session_id,
        "proposals": [p.model_dump(mode="json") for p in request.proposals],
        "proposed_operations": [o.model_dump(mode="json") for o in operations],
        "validation_status": validation_status,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _rel(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _diag(code: str, message: str, proposal_id: str | None = None, severity: Literal["error", "warning", "info"] = "warning") -> GraphGoldAuthoringCommitDiagnostic:
    return GraphGoldAuthoringCommitDiagnostic(code=code, message=message, source_proposal_id=proposal_id, severity=severity)


def _find_proposal(request: GraphGoldAuthoringCommitRequest, proposal_id: str) -> GraphGoldAuthoringLocalProposal | None:
    return next((p for p in request.proposals if p.proposal_id == proposal_id), None)


def _semantic_state() -> dict[str, str]:
    return {"canon_state": "played_canon", "lifecycle_state": "candidate", "evidence_role": "authoring_evidence", "authority_state": "human_authored", "visibility_state": "gm_private"}


def _commit_blocked_response(request: GraphGoldAuthoringCommitRequest, fixture_relpath: str, commit_id: str, now: str, fingerprint: str, diagnostics: list[GraphGoldAuthoringCommitDiagnostic], skipped: list[GraphGoldAuthoringSkippedOperation] | None = None) -> GraphGoldAuthoringCommitResponse:
    return GraphGoldAuthoringCommitResponse(campaign_id=request.campaign_id, session_id=request.session_id, fixture_relpath=fixture_relpath, commit_id=commit_id, committed_at_iso=now, commit_status="blocked", prepare_fingerprint=fingerprint, skipped_operations=skipped or [], diagnostics=diagnostics)


def commit_graph_gold_authoring_preview(request: GraphGoldAuthoringCommitRequest, *, root: Path | None = None) -> GraphGoldAuthoringCommitResponse:
    repo = (root or repo_root()).resolve()
    if request.fixture_version is not None:
        raise GraphGoldReviewError("fixture_version selection is not supported yet; omit fixture_version", status_code=422)
    entry = _session_entry(request.session_id)
    if entry["campaign_id"] is not None and entry["campaign_id"] != request.campaign_id:
        raise GraphGoldReviewError(f"session {request.session_id} belongs to {entry['campaign_id']}, not {request.campaign_id}", status_code=422)

    fixture_relpath = str(entry["gold_dir_rel"]) + "/candidate_graph_gold.json"
    commit_id = "graph-gold-authoring-" + uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    prepare_request = GraphGoldAuthoringPrepareRequest(campaign_id=request.campaign_id, session_id=request.session_id, fixture_version=request.fixture_version, proposals=request.proposals)
    prepare = prepare_graph_gold_authoring_preview(prepare_request, root=repo)
    fingerprint = prepare_fingerprint(request, prepare.proposed_operations, prepare.validation_status)
    if request.expected_prepare_fingerprint and request.expected_prepare_fingerprint != fingerprint:
        return _commit_blocked_response(request, fixture_relpath, commit_id, now, fingerprint, [_diag("prepare_fingerprint_mismatch", "Prepared preview fingerprint changed; no files were changed.", severity="error")])
    skipped = [GraphGoldAuthoringSkippedOperation(operation_id=o.operation_id, operation_type=o.operation_type, source_proposal_id=o.source_proposal_id, reason="prepare blocked or ignored this operation", diagnostics=o.diagnostics) for o in prepare.proposed_operations if o.operation_type in {"blocked", "ignored"}]
    if prepare.validation_status == "blocked":
        return _commit_blocked_response(request, fixture_relpath, commit_id, now, fingerprint, [_diag(e.code, e.message, e.source_proposal_id, e.severity) for e in prepare.blocking_errors] or [_diag("prepare_blocked", "Commit blocked. No files were changed.", severity="error")], skipped)

    fixture_path = repo / fixture_relpath
    try:
        original = fixture_path.read_bytes()
        graph = json.loads(original.decode("utf-8"))
    except FileNotFoundError as exc:
        raise GraphGoldReviewError(f"path does not exist: {fixture_relpath}", status_code=404) from exc
    if not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        raise GraphGoldReviewError("gold fixture must contain nodes and edges arrays", status_code=422)

    applied: list[GraphGoldAuthoringCommittedOperation] = []
    diagnostics: list[GraphGoldAuthoringCommitDiagnostic] = []
    counts = GraphGoldAuthoringCommitChangedCounts(operations_skipped=len(skipped))
    node_ids = {str(n.get("node_id")) for n in graph["nodes"] if isinstance(n, dict) and n.get("node_id")}
    node_labels = {str(n.get("label")) for n in graph["nodes"] if isinstance(n, dict) and n.get("label")}
    edge_ids = {str(e.get("edge_id")) for e in graph["edges"] if isinstance(e, dict) and e.get("edge_id")}

    for op in prepare.proposed_operations:
        if op.operation_type in {"blocked", "ignored"}:
            continue
        proposal = _find_proposal(request, op.source_proposal_id)
        if proposal is None:
            skipped.append(GraphGoldAuthoringSkippedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=op.source_proposal_id, reason="source proposal missing at commit time")); counts.operations_skipped += 1; continue
        if op.operation_type == "add_node" and hasattr(proposal, "suggested_label"):
            node_id = f"authored:node:{proposal.proposal_id}"
            if node_id in node_ids:
                skipped.append(GraphGoldAuthoringSkippedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=proposal.proposal_id, reason="authored node id already exists")); counts.operations_skipped += 1; continue
            node = {"node_id": node_id, "label": proposal.suggested_label, "node_type": proposal.suggested_kind or "authored_note", "description": proposal.source_text, "importance": "medium", "semantic_state": _semantic_state(), "evidence_refs": [], "proposed_action": "create", "confidence": "human", "warnings": ["human-authored via Graph Review Workbench"], "authoring": {"proposal_id": proposal.proposal_id, "source_text": proposal.source_text, "source_anchor": proposal.source_offsets, "lane_role": proposal.lane_role, "review_state": "authored_commit", "committed_at_iso": now, "commit_id": commit_id}}
            graph["nodes"].append(node); node_ids.add(node_id); node_labels.add(str(proposal.suggested_label)); counts.nodes_added += 1
            applied.append(GraphGoldAuthoringCommittedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=proposal.proposal_id, status="applied", target_id=node_id, summary=f"Added authored node {proposal.suggested_label}."))
        elif op.operation_type == "assert_node":
            counts.nodes_asserted += 1
            applied.append(GraphGoldAuthoringCommittedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=proposal.proposal_id, status="recorded_assertion", target_id=getattr(proposal, "node_id", None), summary="Recorded node assertion in authoring event log; fixture node was not created."))
        elif op.operation_type == "add_edge" and hasattr(proposal, "source_node"):
            edge_id = f"authored:edge:{proposal.proposal_id}"
            if edge_id in edge_ids:
                skipped.append(GraphGoldAuthoringSkippedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=proposal.proposal_id, reason="authored edge id already exists")); counts.operations_skipped += 1; continue
            source_id = proposal.source_node.node_id if proposal.source_node.node_id in node_ids else None
            target_id = proposal.target_node.node_id if proposal.target_node.node_id in node_ids else None
            if source_id is None and proposal.source_node.label in node_labels: source_id = proposal.source_node.node_id
            if target_id is None and proposal.target_node.label in node_labels: target_id = proposal.target_node.node_id
            edge = {"edge_id": edge_id, "from_node_id": source_id or proposal.source_node.node_id, "to_node_id": target_id or proposal.target_node.node_id, "label": f"{proposal.source_node.label} {proposal.predicate} {proposal.target_node.label}", "relationship_type": proposal.predicate, "semantic_state": _semantic_state(), "evidence_refs": [], "proposed_action": "create", "confidence": "human", "warnings": ["human-authored via Graph Review Workbench; endpoint refs may require later resolver review"], "authoring": {"proposal_id": proposal.proposal_id, "source_label": proposal.source_node.label, "target_label": proposal.target_node.label, "lane_role": proposal.lane_role, "review_state": "authored_commit", "committed_at_iso": now, "commit_id": commit_id}}
            graph["edges"].append(edge); edge_ids.add(edge_id); counts.edges_added += 1
            applied.append(GraphGoldAuthoringCommittedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=proposal.proposal_id, status="applied", target_id=edge_id, summary="Added authored edge assertion."))
        elif op.operation_type == "link_existing_intent":
            counts.link_intents_recorded += 1
            applied.append(GraphGoldAuthoringCommittedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=proposal.proposal_id, status="recorded_intent", target_id=None, summary="Recorded link intent in authoring event log; no identity link was written."))
        else:
            skipped.append(GraphGoldAuthoringSkippedOperation(operation_id=op.operation_id, operation_type=op.operation_type, source_proposal_id=op.source_proposal_id, reason="operation type is not supported by commit v1")); counts.operations_skipped += 1

    if not applied and counts.operations_skipped:
        return _commit_blocked_response(request, fixture_relpath, commit_id, now, fingerprint, [_diag("no_supported_operations", "No supported operations could be committed; no files were changed.", severity="error")], skipped)

    backup_dir = fixture_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"candidate_graph_gold.{now.replace(':','').replace('-','').replace('.','')}.{commit_id}.json"
    shutil.copyfile(fixture_path, backup_path)
    tmp_path = fixture_path.with_name(fixture_path.name + ".tmp")
    encoded = (json.dumps(graph, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    json.loads(encoded.decode("utf-8"))
    tmp_path.write_bytes(encoded)
    os.replace(tmp_path, fixture_path)

    event_log_path = fixture_path.parent / "authoring_events.jsonl"
    event = {"schema": EVENT_SCHEMA, "event_type": "commit_prepared_preview", "commit_id": commit_id, "committed_at_iso": now, "campaign_id": request.campaign_id, "session_id": request.session_id, "fixture_relpath": fixture_relpath, "backup_relpath": _rel(repo, backup_path), "prepare_fingerprint": fingerprint, "applied_operations": [a.model_dump(mode="json") for a in applied], "skipped_operations": [s.model_dump(mode="json") for s in skipped], "diagnostics": [d.model_dump(mode="json") for d in diagnostics], "commit_message": request.commit_message, "operator_note": request.operator_note}
    with event_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")

    status: Literal["committed", "partial"] = "partial" if skipped or counts.operations_skipped else "committed"
    return GraphGoldAuthoringCommitResponse(campaign_id=request.campaign_id, session_id=request.session_id, fixture_relpath=fixture_relpath, backup_relpath=_rel(repo, backup_path), event_log_relpath=_rel(repo, event_log_path), commit_id=commit_id, committed_at_iso=now, commit_status=status, prepare_fingerprint=fingerprint, applied_operations=applied, skipped_operations=skipped, diagnostics=diagnostics, changed_counts=counts)
