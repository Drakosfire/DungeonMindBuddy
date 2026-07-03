"""Read-only preparation of local graph gold-authoring draft proposals."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_gold_review import (
    GraphGoldReviewError,
    _session_entry,
)

REQUEST_SCHEMA = "dmb_graph_gold_authoring_prepare_request_v1"
RESPONSE_SCHEMA = "dmb_graph_gold_authoring_prepare_response_v1"
GRAPH_REVIEW_RELATIONSHIP_PREDICATES = {
    "relates_to",
    "threatens",
    "located_at",
    "member_of",
    "ally_of",
    "opposes",
    "caused_by",
    "protects",
}

ProposalStatus = Literal["staged", "accepted_local", "rejected_local"]
LaneRole = Literal["gold", "live"]
RelationshipLaneRole = Literal["gold", "live", "mixed"]


class GraphGoldAuthoringPrepareDiagnostic(BaseModel):
    code: str
    message: str
    source_proposal_id: str | None = None
    severity: Literal["error", "warning", "info"] = "warning"


class GraphGoldAuthoringLocalProposalBase(BaseModel):
    proposal_id: str
    proposal_type: str
    created_at_iso: str
    status: ProposalStatus


class GraphGoldAuthoringRelationshipNodeRef(BaseModel):
    lane_role: LaneRole
    node_id: str
    label: str


class NodeFromSpanProposal(GraphGoldAuthoringLocalProposalBase):
    proposal_type: Literal["node_from_span"]
    lane_role: LaneRole
    source_text: str
    source_offsets: dict[str, int] | None = None
    suggested_label: str
    suggested_kind: str | None = None


class NodeAssertionProposal(GraphGoldAuthoringLocalProposalBase):
    proposal_type: Literal["node_assertion"]
    lane_role: LaneRole
    node_id: str
    label: str
    kind: str | None = None
    role: str | None = None


class RelationshipAssertionProposal(GraphGoldAuthoringLocalProposalBase):
    proposal_type: Literal["relationship_assertion"]
    lane_role: RelationshipLaneRole
    source_node: GraphGoldAuthoringRelationshipNodeRef
    target_node: GraphGoldAuthoringRelationshipNodeRef
    predicate: str


class ExistingObjectCandidate(BaseModel):
    candidate_id: str
    label: str
    source: str
    confidence: str
    score: float | None = None


class ExistingObjectLinkIntentProposal(GraphGoldAuthoringLocalProposalBase):
    proposal_type: Literal["existing_object_link_intent"]
    selected_node: GraphGoldAuthoringRelationshipNodeRef
    candidate: ExistingObjectCandidate


GraphGoldAuthoringLocalProposal = Union[
    NodeFromSpanProposal,
    NodeAssertionProposal,
    RelationshipAssertionProposal,
    ExistingObjectLinkIntentProposal,
]


class GraphGoldAuthoringPrepareRequest(BaseModel):
    schema: Literal["dmb_graph_gold_authoring_prepare_request_v1"] = REQUEST_SCHEMA
    campaign_id: str
    session_id: str
    fixture_version: str | None = None
    proposals: list[GraphGoldAuthoringLocalProposal] = Field(default_factory=list)
    include_rejected: bool = False


class GraphGoldAuthoringProposalCounts(BaseModel):
    total: int = 0
    accepted_local: int = 0
    staged: int = 0
    rejected_local: int = 0
    candidate_operations: int = 0
    ignored: int = 0
    blocked: int = 0


class GraphGoldAuthoringNormalizedProposal(BaseModel):
    proposal_id: str
    proposal_type: str
    status: ProposalStatus
    eligible_for_operation: bool
    summary: str
    diagnostics: list[GraphGoldAuthoringPrepareDiagnostic] = Field(default_factory=list)


class GraphGoldAuthoringPreviewOperation(BaseModel):
    operation_id: str
    operation_type: Literal[
        "add_node",
        "assert_node",
        "add_edge",
        "link_existing_intent",
        "ignored",
        "blocked",
    ]
    source_proposal_id: str
    label: str
    summary: str
    gold_shape_preview: dict[str, Any] | None = None
    requires_manual_review: bool = False
    diagnostics: list[GraphGoldAuthoringPrepareDiagnostic] = Field(default_factory=list)


class GraphGoldAuthoringPrepareResponse(BaseModel):
    schema: Literal["dmb_graph_gold_authoring_prepare_response_v1"] = RESPONSE_SCHEMA
    campaign_id: str
    session_id: str
    fixture_relpath: str | None = None
    validation_status: Literal["ready", "ready_with_warnings", "blocked"]
    proposal_counts: GraphGoldAuthoringProposalCounts
    normalized_proposals: list[GraphGoldAuthoringNormalizedProposal]
    proposed_operations: list[GraphGoldAuthoringPreviewOperation]
    blocking_errors: list[GraphGoldAuthoringPrepareDiagnostic] = Field(default_factory=list)
    warnings: list[GraphGoldAuthoringPrepareDiagnostic] = Field(default_factory=list)
    preview_summary: str
    prepare_fingerprint: str
    fixture_state_fingerprint: str
    write_performed: Literal[False] = False


def graph_gold_authoring_fixture_state_fingerprint(fixture_path: Path) -> str:
    return hashlib.sha256(fixture_path.read_bytes()).hexdigest()


def graph_gold_authoring_prepare_fingerprint(
    *,
    campaign_id: str,
    session_id: str,
    proposals: list[GraphGoldAuthoringLocalProposal],
    proposed_operations: list[GraphGoldAuthoringPreviewOperation],
    validation_status: str,
) -> str:
    payload = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "proposals": [p.model_dump(mode="json") for p in proposals],
        "proposed_operations": [o.model_dump(mode="json") for o in proposed_operations],
        "validation_status": validation_status,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _diag(code: str, message: str, proposal_id: str | None, severity: Literal["error", "warning", "info"] = "warning") -> GraphGoldAuthoringPrepareDiagnostic:
    return GraphGoldAuthoringPrepareDiagnostic(code=code, message=message, source_proposal_id=proposal_id, severity=severity)


def _blank(value: str | None) -> bool:
    return not (value or "").strip()


def _blocked_operation(proposal: GraphGoldAuthoringLocalProposal, label: str, diagnostics: list[GraphGoldAuthoringPrepareDiagnostic]) -> GraphGoldAuthoringPreviewOperation:
    return GraphGoldAuthoringPreviewOperation(operation_id=f"blocked:{proposal.proposal_id}", operation_type="blocked", source_proposal_id=proposal.proposal_id, label=label, summary="Proposal is blocked until diagnostics are resolved.", requires_manual_review=True, diagnostics=diagnostics)


def prepare_graph_gold_authoring_preview(request: GraphGoldAuthoringPrepareRequest, *, root: Path | None = None) -> GraphGoldAuthoringPrepareResponse:
    _repo = (root or repo_root()).resolve()
    if request.fixture_version is not None:
        raise GraphGoldReviewError("fixture_version selection is not supported yet; omit fixture_version", status_code=422)
    entry = _session_entry(request.session_id)
    if entry["campaign_id"] is not None and entry["campaign_id"] != request.campaign_id:
        raise GraphGoldReviewError(f"session {request.session_id} belongs to {entry['campaign_id']}, not {request.campaign_id}", status_code=422)
    fixture_relpath = str(entry["gold_dir_rel"]) + "/candidate_graph_gold.json"
    fixture_path = _repo / fixture_relpath
    fixture_state_fingerprint = graph_gold_authoring_fixture_state_fingerprint(fixture_path)
    # Read fixture context without writing it; future slices may use contents for richer diffs.
    entry["load_gold_graph_dict"]()

    counts = GraphGoldAuthoringProposalCounts(total=len(request.proposals))
    normalized: list[GraphGoldAuthoringNormalizedProposal] = []
    operations: list[GraphGoldAuthoringPreviewOperation] = []
    warnings: list[GraphGoldAuthoringPrepareDiagnostic] = []
    errors: list[GraphGoldAuthoringPrepareDiagnostic] = []

    if not request.proposals:
        errors.append(_diag("empty_proposals", "No local proposals were provided. Accept local proposals before preparing a write preview.", None, "error"))

    for proposal in request.proposals:
        setattr(counts, proposal.status, getattr(counts, proposal.status) + 1)
        if proposal.status == "staged":
            d = _diag("proposal_staged", f"Proposal {proposal.proposal_id} is still staged. Accept locally before preparing it for write preview.", proposal.proposal_id)
            warnings.append(d); counts.ignored += 1
            operations.append(GraphGoldAuthoringPreviewOperation(operation_id=f"ignored:{proposal.proposal_id}", operation_type="ignored", source_proposal_id=proposal.proposal_id, label=proposal.proposal_type, summary="Staged proposal ignored for read-only prepare.", diagnostics=[d]))
            normalized.append(GraphGoldAuthoringNormalizedProposal(proposal_id=proposal.proposal_id, proposal_type=proposal.proposal_type, status=proposal.status, eligible_for_operation=False, summary="Ignored because it is not accepted locally.", diagnostics=[d]))
            continue
        if proposal.status == "rejected_local":
            counts.ignored += 1
            if request.include_rejected:
                operations.append(GraphGoldAuthoringPreviewOperation(operation_id=f"ignored:{proposal.proposal_id}", operation_type="ignored", source_proposal_id=proposal.proposal_id, label=proposal.proposal_type, summary="Rejected proposal ignored for read-only prepare."))
            normalized.append(GraphGoldAuthoringNormalizedProposal(proposal_id=proposal.proposal_id, proposal_type=proposal.proposal_type, status=proposal.status, eligible_for_operation=False, summary="Ignored because it is rejected locally."))
            continue

        diagnostics: list[GraphGoldAuthoringPrepareDiagnostic] = []
        op: GraphGoldAuthoringPreviewOperation | None = None
        if isinstance(proposal, NodeFromSpanProposal):
            if _blank(proposal.source_text): diagnostics.append(_diag("missing_source_text", "Node-from-span proposal requires non-empty source text.", proposal.proposal_id, "error"))
            if _blank(proposal.suggested_label): diagnostics.append(_diag("missing_label", "Node-from-span proposal requires a suggested label.", proposal.proposal_id, "error"))
            if proposal.source_offsets is None:
                diagnostics.append(_diag("unanchored_source", "Source offsets are absent; preview is approximate/unanchored.", proposal.proposal_id))
            if any(d.severity == "error" for d in diagnostics):
                op = _blocked_operation(proposal, proposal.suggested_label or "Node from span", diagnostics)
            else:
                op = GraphGoldAuthoringPreviewOperation(operation_id=f"preview:node:{proposal.proposal_id}", operation_type="add_node", source_proposal_id=proposal.proposal_id, label=proposal.suggested_label, summary="Would add a new gold-shaped draft node from selected prose span.", gold_shape_preview={"node": {"preview_id": f"preview:node:{proposal.proposal_id}", "label": proposal.suggested_label, "kind": proposal.suggested_kind, "source_text": proposal.source_text, "source_anchor": proposal.source_offsets, "lane_role": proposal.lane_role, "review_state": "draft_preview"}}, diagnostics=diagnostics)
        elif isinstance(proposal, NodeAssertionProposal):
            if _blank(proposal.node_id): diagnostics.append(_diag("missing_node_id", "Node assertion requires a node id.", proposal.proposal_id, "error"))
            if _blank(proposal.label): diagnostics.append(_diag("missing_label", "Node assertion requires a label.", proposal.proposal_id, "error"))
            manual = proposal.lane_role == "live"
            if manual: diagnostics.append(_diag("live_lane_manual_review", "Live-lane node assertion requires manual review before future gold write.", proposal.proposal_id))
            op = _blocked_operation(proposal, proposal.label or "Node assertion", diagnostics) if any(d.severity == "error" for d in diagnostics) else GraphGoldAuthoringPreviewOperation(operation_id=f"preview:assert-node:{proposal.proposal_id}", operation_type="assert_node", source_proposal_id=proposal.proposal_id, label=proposal.label, summary="Would assert this projected node exists in gold.", requires_manual_review=manual, diagnostics=diagnostics, gold_shape_preview={"node_assertion": proposal.model_dump(mode="json")})
        elif isinstance(proposal, RelationshipAssertionProposal):
            if _blank(proposal.source_node.node_id) or _blank(proposal.target_node.node_id): diagnostics.append(_diag("missing_relationship_endpoint", "Relationship assertion requires source and target node refs.", proposal.proposal_id, "error"))
            if proposal.source_node.node_id == proposal.target_node.node_id: diagnostics.append(_diag("self_relationship", "Relationship source and target must differ.", proposal.proposal_id, "error"))
            if proposal.predicate not in GRAPH_REVIEW_RELATIONSHIP_PREDICATES: diagnostics.append(_diag("unknown_predicate", f"Predicate {proposal.predicate!r} is not supported for graph review authoring preview.", proposal.proposal_id, "error"))
            manual = proposal.lane_role == "mixed"
            if manual: diagnostics.append(_diag("mixed_lane_manual_review", "Mixed-lane relationship preview requires manual review before future gold write.", proposal.proposal_id))
            label = f"{proposal.source_node.label} {proposal.predicate} {proposal.target_node.label}"
            op = _blocked_operation(proposal, label, diagnostics) if any(d.severity == "error" for d in diagnostics) else GraphGoldAuthoringPreviewOperation(operation_id=f"preview:edge:{proposal.proposal_id}", operation_type="add_edge", source_proposal_id=proposal.proposal_id, label=label, summary="Would add a relationship assertion.", requires_manual_review=manual, diagnostics=diagnostics, gold_shape_preview={"edge": {"source_label": proposal.source_node.label, "predicate": proposal.predicate, "target_label": proposal.target_node.label, "review_state": "draft_preview"}})
        elif isinstance(proposal, ExistingObjectLinkIntentProposal):
            if _blank(proposal.selected_node.node_id) or _blank(proposal.selected_node.label): diagnostics.append(_diag("missing_selected_node", "Existing-object link intent requires a selected node.", proposal.proposal_id, "error"))
            if _blank(proposal.candidate.candidate_id) or _blank(proposal.candidate.label) or _blank(proposal.candidate.source) or _blank(proposal.candidate.confidence): diagnostics.append(_diag("missing_candidate", "Existing-object link intent requires candidate id, label, source, and confidence.", proposal.proposal_id, "error"))
            diagnostics.append(_diag("future_identity_resolution", "Future write must resolve identity/link target before committing.", proposal.proposal_id))
            label = f"{proposal.selected_node.label} → {proposal.candidate.label}"
            op = _blocked_operation(proposal, label, diagnostics) if any(d.severity == "error" for d in diagnostics) else GraphGoldAuthoringPreviewOperation(operation_id=f"preview:link-intent:{proposal.proposal_id}", operation_type="link_existing_intent", source_proposal_id=proposal.proposal_id, label=label, summary="Would carry forward a link intent for future resolver/link write.", requires_manual_review=True, diagnostics=diagnostics, gold_shape_preview={"link_intent": {"selected_node": proposal.selected_node.model_dump(mode="json"), "candidate": proposal.candidate.model_dump(mode="json"), "review_state": "draft_preview"}})
        if op:
            operations.append(op)
            counts.candidate_operations += 1 if op.operation_type not in {"blocked", "ignored"} else 0
            if op.operation_type == "blocked": counts.blocked += 1; errors.extend([d for d in op.diagnostics if d.severity == "error"])
            warnings.extend([d for d in op.diagnostics if d.severity != "error"])
            normalized.append(GraphGoldAuthoringNormalizedProposal(proposal_id=proposal.proposal_id, proposal_type=proposal.proposal_type, status=proposal.status, eligible_for_operation=op.operation_type not in {"blocked", "ignored"}, summary=op.summary, diagnostics=op.diagnostics))

    status: Literal["ready", "ready_with_warnings", "blocked"] = "blocked" if errors or counts.candidate_operations == 0 else ("ready_with_warnings" if warnings else "ready")
    summary = "Preview blocked. Resolve diagnostics before a future write step." if status == "blocked" else f"Preview prepared with {counts.candidate_operations} proposed operation(s). No files were changed."
    fingerprint = graph_gold_authoring_prepare_fingerprint(campaign_id=request.campaign_id, session_id=request.session_id, proposals=request.proposals, proposed_operations=operations, validation_status=status)
    return GraphGoldAuthoringPrepareResponse(campaign_id=request.campaign_id, session_id=request.session_id, fixture_relpath=fixture_relpath, validation_status=status, proposal_counts=counts, normalized_proposals=normalized, proposed_operations=operations, blocking_errors=errors, warnings=warnings, preview_summary=summary, prepare_fingerprint=fingerprint, fixture_state_fingerprint=fixture_state_fingerprint, write_performed=False)
