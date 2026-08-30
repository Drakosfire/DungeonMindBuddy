"""Prepare authored graph overlay writes from staged local proposals."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.live_control_server.models.graph_authoring_overlay import (
    AUTHORED_GRAPH_OVERLAY_SCHEMA,
    AuthoredGraphAssertion,
    AuthoredGraphLinkExistingAssertion,
    AuthoredGraphMergeObjectsAssertion,
    AuthoredGraphObjectAssertion,
    AuthoredGraphObjectRef,
    AuthoredGraphRelationshipAssertion,
    GraphAuthoringProvenance,
    GraphAuthoringSourceAnchor,
    GraphObjectCandidateScope,
    GraphScope,
    GraphVisibility,
    GraphVisibilityPolicy,
    UnsafeCampaignIdError,
    UnsafeCampaignRelError,
    build_source_anchor_from_payload,
    default_graph_authoring_provenance,
    validate_campaign_id,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
)
from apps.live_control_server.services.graph_authoring_ids import (
    authored_object_node_id,
)
from apps.live_control_server.services.graph_object_authoring_merge_guard import (
    detect_merge_assertion_conflicts,
)
from apps.live_control_server.services.graph_object_authoring_overlap import (
    detect_prepare_overlap_warnings,
)

STABLE_ASSERTION_TIMESTAMP = "1970-01-01T00:00:00Z"
CONFIRM_TOKEN_KIND = "graph_authoring_commit_confirmation_v1"

NO_MUTATION_GUARANTEES_PREPARE = [
    "Prepare wrote nothing.",
    "Source markdown was not mutated.",
    "Extracted live run artifacts were not mutated.",
    "Candidate graph gold was not mutated.",
    "DungeonMind graph head was not advanced.",
    "Authored overlay and UnionSupergraph were not mutated.",
]

GRAPH_REVIEW_PREPARE_BINDING_SCHEMA = "dmb_graph_review_prepare_binding_v1"
GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV = "DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY"
PREPARE_TTL = timedelta(hours=1)
EXPRESSIBLE_KINDS = frozenset({"object", "link_existing", "relationship"})

NO_MUTATION_GUARANTEES_COMMIT_SHARED = [
    "Source markdown was not mutated.",
    "Extracted live run artifacts were not mutated.",
    "Candidate graph gold was not mutated.",
]

NO_MUTATION_GUARANTEES_COMMIT = [
    "Committed authored graph memory.",
    "Wrote authored graph overlay.",
    "Appended authoring event log.",
    *NO_MUTATION_GUARANTEES_COMMIT_SHARED,
]


def commit_no_mutation_guarantees(
    *,
    overlay_written: bool,
    event_log_written: bool,
    union_store_materialized: bool = False,
) -> list[str]:
    guarantees: list[str] = []
    if overlay_written and event_log_written:
        guarantees.append("Committed authored graph memory.")
    elif overlay_written:
        guarantees.append("Partial commit: authored graph overlay was written.")
    if overlay_written:
        guarantees.append("Wrote authored graph overlay.")
    if event_log_written:
        guarantees.append("Appended authoring event log.")
    elif overlay_written:
        guarantees.append("Authoring event log was not appended.")
    if union_store_materialized:
        guarantees.append("Updated preview union graph store for committed identity merges.")
    guarantees.extend(NO_MUTATION_GUARANTEES_COMMIT_SHARED)
    return guarantees


def validate_authoring_campaign_scope(
    campaign_id: str,
    campaign_rel: str | None,
) -> None:
    try:
        validate_campaign_id(campaign_id)
    except UnsafeCampaignIdError as exc:
        raise GraphObjectAuthoringError(str(exc), code="unsafe_campaign_id") from exc

    if campaign_rel is not None:
        from apps.live_control_server.models.graph_authoring_overlay import validate_campaign_rel

        try:
            validate_campaign_rel(campaign_rel)
        except UnsafeCampaignRelError as exc:
            raise GraphObjectAuthoringError(str(exc), code="unsafe_campaign_rel") from exc


class GraphObjectAuthoringError(ValueError):
    status_code = 422

    def __init__(self, message: str, *, code: str = "invalid_request", status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class GraphAuthoringDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    local_proposal_id: str | None = None
    severity: Literal["error", "warning", "info"] = "error"


class GraphObjectAuthoringNewObjectPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    label: str
    kind: str | None = None
    role: str | None = None
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None


class GraphObjectAuthoringObjectRefPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ref_kind: Literal["existing_graph_node", "local_proposal", "manual_ref"] = Field(
        alias="refKind",
    )
    node_id: str | None = Field(default=None, alias="nodeId")
    local_proposal_id: str | None = Field(default=None, alias="localProposalId")
    label: str
    kind: str | None = None
    role: str | None = None
    graph_scope: str | None = Field(default=None, alias="graphScope")
    source_label: str | None = Field(default=None, alias="sourceLabel")
    source_graph_id: str | None = Field(default=None, alias="sourceGraphId")
    source_path: str | None = Field(default=None, alias="sourcePath")
    visibility: str | None = None


class GraphObjectAuthoringVisibilityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    visibility: GraphVisibility
    reveal_state: Literal["unrevealed", "partial", "revealed"] = Field(
        default="unrevealed",
        alias="revealState",
    )
    visibility_note: str | None = Field(default=None, alias="visibilityNote")


class GraphObjectAuthoringProvenancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    origin: Literal["human_authored"] = "human_authored"
    authoring_surface: Literal["memory_ingest_graph_authoring"] = Field(
        default="memory_ingest_graph_authoring",
        alias="authoringSurface",
    )
    source_graph_id: str | None = Field(default=None, alias="sourceGraphId")
    source_artifact_path: str | None = Field(default=None, alias="sourceArtifactPath")
    operator_note: str | None = Field(default=None, alias="operatorNote")


class GraphObjectAuthoringProposalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    local_proposal_id: str = Field(alias="localProposalId")
    proposal_kind: Literal["object", "link_existing", "relationship", "merge_objects"] = Field(
        alias="proposalKind",
    )
    status: Literal["staged_local"] = "staged_local"
    selection: dict[str, Any] | None = None
    object_ref: dict[str, Any] | None = Field(default=None, alias="objectRef")
    selected_text: str | None = Field(default=None, alias="selectedText")
    normalized_selected_text: str | None = Field(default=None, alias="normalizedSelectedText")
    existing_object_ref: dict[str, Any] | None = Field(default=None, alias="existingObjectRef")
    operation: str | None = None
    alias_text: str | None = Field(default=None, alias="aliasText")
    source_object_ref: dict[str, Any] | None = Field(default=None, alias="sourceObjectRef")
    target_object_ref: dict[str, Any] | None = Field(default=None, alias="targetObjectRef")
    relationship_type: str | None = Field(default=None, alias="relationshipType")
    relationship_label: str | None = Field(default=None, alias="relationshipLabel")
    direction: Literal["directed", "undirected"] | None = None
    summary: str | None = None
    survivor_object_ref: dict[str, Any] | None = Field(default=None, alias="survivorObjectRef")
    merged_object_refs: list[dict[str, Any]] | None = Field(
        default=None,
        alias="mergedObjectRefs",
    )
    merge_reason: str | None = Field(default=None, alias="mergeReason")
    matched_features: list[str] = Field(default_factory=list, alias="matchedFeatures")
    alias_policy: Literal["preserve_all_aliases", "manual"] | None = Field(
        default=None,
        alias="aliasPolicy",
    )
    relationship_policy: Literal[
        "preserve_all_relationships",
        "manual_review_required",
    ] | None = Field(default=None, alias="relationshipPolicy")
    evidence_policy: Literal["preserve_all_evidence"] | None = Field(
        default=None,
        alias="evidencePolicy",
    )
    visibility: GraphObjectAuthoringVisibilityPayload
    graph_scopes: list[GraphScope] = Field(default_factory=lambda: ["recap_graph", "campaign_memory_graph"], alias="graphScopes")
    provenance_preview: GraphObjectAuthoringProvenancePayload = Field(alias="provenancePreview")


class GraphObjectAuthoringPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    campaign_id: str = Field(alias="campaignId")
    campaign_rel: str | None = Field(default=None, alias="campaignRel")
    session_id: str | None = Field(default=None, alias="sessionId")
    world_id: str | None = Field(default=None, alias="worldId")
    source_run_id: str | None = Field(default=None, alias="sourceRunId")
    source_graph_id: str | None = Field(default=None, alias="sourceGraphId")
    source_projection_id: str | None = Field(default=None, alias="sourceProjectionId")
    proposals: list[GraphObjectAuthoringProposalPayload]
    operator_note: str | None = Field(default=None, alias="operatorNote")


class GraphObjectAuthoringCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    campaign_id: str = Field(alias="campaignId")
    campaign_rel: str | None = Field(default=None, alias="campaignRel")
    session_id: str | None = Field(default=None, alias="sessionId")
    world_id: str | None = Field(default=None, alias="worldId")
    source_run_id: str | None = Field(default=None, alias="sourceRunId")
    source_graph_id: str | None = Field(default=None, alias="sourceGraphId")
    source_projection_id: str | None = Field(default=None, alias="sourceProjectionId")
    proposals: list[GraphObjectAuthoringProposalPayload]
    confirm_token: str = Field(alias="confirmToken")
    current_overlay_token: str | None = Field(default=None, alias="currentOverlayToken")
    operator_note: str | None = Field(default=None, alias="operatorNote")
    preview_union_store_path: str | None = Field(default=None, alias="previewUnionStorePath")
    merge_into_union: bool | None = Field(default=None, alias="mergeIntoUnion")


def authoring_prepare_request_from_write(
    request: GraphObjectAuthoringPrepareRequest | GraphObjectAuthoringCommitRequest,
) -> GraphObjectAuthoringPrepareRequest:
    if isinstance(request, GraphObjectAuthoringPrepareRequest):
        return request
    return GraphObjectAuthoringPrepareRequest(
        campaign_id=request.campaign_id,
        campaign_rel=request.campaign_rel,
        session_id=request.session_id,
        world_id=request.world_id,
        source_run_id=request.source_run_id,
        source_graph_id=request.source_graph_id,
        source_projection_id=request.source_projection_id,
        proposals=request.proposals,
        operator_note=request.operator_note,
    )


class AuthoredGraphAssertionPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    assertion_kind: Literal["object", "link_existing", "relationship", "merge_objects"]
    operation: str
    local_proposal_id: str
    summary: str


class GraphAuthoringOverlaySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existing_assertion_count: int
    proposed_assertion_count: int
    total_assertion_count: int
    object_count: int
    link_existing_count: int
    relationship_count: int
    merge_objects_count: int


class GraphObjectAuthoringPrepareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prepared: bool = True
    campaign_id: str
    overlay_path: str
    event_log_path: str
    current_overlay_token: str
    proposed_assertions_digest: str
    confirm_token: str
    assertion_count: int
    event_count: int
    assertions_preview: list[AuthoredGraphAssertionPreview]
    overlay_summary: GraphAuthoringOverlaySummary
    diagnostics: list[GraphAuthoringDiagnostic]
    no_mutation_guarantees: list[str]
    world_id: str | None = None
    expected_parent_revision_id: str | None = None
    source_artifact_id: str | None = None
    source_revision_id: str | None = None
    authority_operation_id: str | None = None
    contribution_digest: str | None = None
    expressibility: Literal["EXPRESSIBLE", "INEXPRESSIBLE"] = "EXPRESSIBLE"
    expires_at: str | None = None
    actor: str | None = None


UnionStoreMaterializationReason = Literal[
    "no_preview_union_store_selected",
    "no_actionable_merge_assertions",
    "materialized",
    "materialization_failed",
    "event_log_failed",
]


class GraphObjectAuthoringUnionStoreMaterializationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempted: bool
    applied: bool
    reason: UnionStoreMaterializationReason
    union_store_path: str | None = None
    backup_path: str | None = None
    applied_assertion_ids: list[str] = Field(default_factory=list)
    redirects_added: int = 0
    edges_rewired: int = 0
    survivor_nodes_updated: int = 0
    diagnostics: list[GraphAuthoringDiagnostic] = Field(default_factory=list)


class GraphObjectAuthoringCommitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    committed: bool
    campaign_id: str
    overlay_path: str | None = None
    event_log_path: str | None = None
    backup_path: str | None = None
    assertion_count: int = 0
    event_count: int = 0
    new_overlay_token: str | None = None
    diagnostics: list[GraphAuthoringDiagnostic] = Field(default_factory=list)
    no_mutation_guarantees: list[str] = Field(default_factory=list)
    union_store_materialization: GraphObjectAuthoringUnionStoreMaterializationSummary | None = None
    created_node_ids: dict[str, str] = Field(default_factory=dict)
    world_id: str | None = None
    parent_revision_id: str | None = None
    published_revision_id: str | None = None
    operation_id: str | None = None
    result: str | None = None
    idempotency_status: str | None = None
    audit_status: Literal["recorded", "degraded", "skipped"] | None = None


def stable_json_digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def contribution_binding_digest(contribution: Any) -> str:
    payload = contribution.model_dump(mode="json")
    payload.pop("produced_at", None)
    return stable_json_digest(payload)


def overlay_file_token(path: Path, *, campaign_id: str) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return stable_json_digest({"missing_overlay": campaign_id})


def _diag(
    code: str,
    message: str,
    *,
    local_proposal_id: str | None = None,
    severity: Literal["error", "warning", "info"] = "error",
) -> GraphAuthoringDiagnostic:
    return GraphAuthoringDiagnostic(
        code=code,
        message=message,
        local_proposal_id=local_proposal_id,
        severity=severity,
    )


def _blocking_assertion_diagnostics(
    diagnostics: list[GraphAuthoringDiagnostic],
) -> list[GraphAuthoringDiagnostic]:
    return [item for item in diagnostics if item.severity == "error"]


def _non_blocking_assertion_diagnostics(
    diagnostics: list[GraphAuthoringDiagnostic],
) -> list[GraphAuthoringDiagnostic]:
    return [item for item in diagnostics if item.severity != "error"]


def _validate_merge_object_ref(
    payload: dict[str, Any],
    *,
    local_proposal_id: str,
    context: str,
) -> AuthoredGraphObjectRef:
    parsed = GraphObjectAuthoringObjectRefPayload.model_validate(payload)
    if parsed.ref_kind == "manual_ref":
        raise GraphObjectAuthoringError(
            f"{context}: manual_ref is not supported for merge MVP",
            code="unsupported_merge_ref",
        )
    if parsed.ref_kind not in ("existing_graph_node", "local_proposal"):
        raise GraphObjectAuthoringError(
            f"{context}: ref kind {parsed.ref_kind!r} is not supported for merge MVP",
            code="unsupported_merge_ref",
        )
    if parsed.ref_kind == "existing_graph_node" and not (parsed.node_id or "").strip():
        raise GraphObjectAuthoringError(
            f"{context}: existing_graph_node ref requires nodeId",
            code="invalid_merge_ref",
        )
    if parsed.ref_kind == "local_proposal" and not (parsed.local_proposal_id or "").strip():
        raise GraphObjectAuthoringError(
            f"{context}: local_proposal ref requires localProposalId",
            code="invalid_merge_ref",
        )
    if not parsed.label.strip():
        raise GraphObjectAuthoringError(
            f"{context}: object ref label must be non-blank",
            code="invalid_merge_ref",
        )
    return _build_object_ref(payload)


_CANDIDATE_GRAPH_SCOPE_VALUES: frozenset[str] = frozenset(
    {
        "current_recap_projection",
        "authored_overlay",
        "campaign_memory",
        "worldbuilding",
        "party_pc",
        "gm_private",
    }
)

_CANDIDATE_GRAPH_SCOPE_ALIASES: dict[str, GraphObjectCandidateScope] = {
    "recap": "current_recap_projection",
    "live_projection": "current_recap_projection",
    "gold_fixture": "current_recap_projection",
}


def _normalize_candidate_graph_scope(
    value: str | None,
) -> GraphObjectCandidateScope | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if trimmed in _CANDIDATE_GRAPH_SCOPE_VALUES:
        return trimmed  # type: ignore[return-value]
    return _CANDIDATE_GRAPH_SCOPE_ALIASES.get(trimmed)


def _build_object_ref(payload: dict[str, Any]) -> AuthoredGraphObjectRef:
    parsed = GraphObjectAuthoringObjectRefPayload.model_validate(payload)
    return AuthoredGraphObjectRef(
        ref_kind=parsed.ref_kind,
        node_id=parsed.node_id,
        local_proposal_id=parsed.local_proposal_id,
        label=parsed.label,
        kind=parsed.kind,
        role=parsed.role,
        candidate_graph_scope=_normalize_candidate_graph_scope(parsed.graph_scope),
        source_label=parsed.source_label,
        source_graph_id=parsed.source_graph_id,
        source_path=parsed.source_path,
        source_visibility=parsed.visibility,
    )


def _merge_kind_conflict_warning(
    survivor: AuthoredGraphObjectRef,
    merged_refs: list[AuthoredGraphObjectRef],
    *,
    local_proposal_id: str,
) -> GraphAuthoringDiagnostic | None:
    survivor_kind = (survivor.kind or "").strip().lower()
    if not survivor_kind or survivor_kind == "unknown":
        return None
    for ref in merged_refs:
        merged_kind = (ref.kind or "").strip().lower()
        if merged_kind and merged_kind != "unknown" and merged_kind != survivor_kind:
            return _diag(
                "merge_kind_role_conflict",
                (
                    f"Kind mismatch: survivor {survivor.label!r} ({survivor.kind}) vs "
                    f"merged-away {ref.label!r} ({ref.kind}). Review before commit."
                ),
                local_proposal_id=local_proposal_id,
                severity="warning",
            )
    return None


def _build_visibility(payload: GraphObjectAuthoringVisibilityPayload) -> GraphVisibilityPolicy:
    return GraphVisibilityPolicy(
        visibility=payload.visibility,
        reveal_state=payload.reveal_state,
        visibility_note=payload.visibility_note,
    )


def _build_provenance(
    *,
    request_source_run_id: str | None,
    request_source_graph_id: str | None,
    request_source_projection_id: str | None,
    request_operator_note: str | None,
    preview: GraphObjectAuthoringProvenancePayload,
) -> GraphAuthoringProvenance:
    return default_graph_authoring_provenance(
        created_at=STABLE_ASSERTION_TIMESTAMP,
        operator_note=request_operator_note or preview.operator_note,
        source_graph_id=request_source_graph_id or preview.source_graph_id,
    ).model_copy(
        update={
            "updated_at": STABLE_ASSERTION_TIMESTAMP,
            "source_run_id": request_source_run_id,
            "source_projection_id": request_source_projection_id,
        }
    )


def _assertion_id(
    campaign_id: str,
    proposal: GraphObjectAuthoringProposalPayload,
    *,
    normalized_payload: dict[str, Any],
) -> str:
    digest = stable_json_digest(
        {
            "campaign_id": campaign_id,
            "proposal_kind": proposal.proposal_kind,
            "local_proposal_id": proposal.local_proposal_id,
            "payload": normalized_payload,
        }
    )
    return f"assert-{digest[:16]}"


def _normalized_proposal_payload(proposal: GraphObjectAuthoringProposalPayload) -> dict[str, Any]:
    return proposal.model_dump(mode="json", by_alias=False)


def _optional_source_anchor(selection: dict[str, Any] | None) -> GraphAuthoringSourceAnchor | None:
    if not selection:
        return None
    return build_source_anchor_from_payload(selection)


def build_assertions_from_proposals(
    request: GraphObjectAuthoringPrepareRequest | GraphObjectAuthoringCommitRequest,
) -> tuple[list[AuthoredGraphAssertion], list[GraphAuthoringDiagnostic]]:
    campaign_id = validate_campaign_id(request.campaign_id)
    assertions: list[AuthoredGraphAssertion] = []
    diagnostics: list[GraphAuthoringDiagnostic] = []

    source_run_id = getattr(request, "source_run_id", None)
    source_graph_id = getattr(request, "source_graph_id", None)
    source_projection_id = getattr(request, "source_projection_id", None)

    for proposal in request.proposals:
        normalized_payload = _normalized_proposal_payload(proposal)
        assertion_id = _assertion_id(campaign_id, proposal, normalized_payload=normalized_payload)
        provenance = _build_provenance(
            request_source_run_id=source_run_id,
            request_source_graph_id=source_graph_id,
            request_source_projection_id=source_projection_id,
            request_operator_note=request.operator_note,
            preview=proposal.provenance_preview,
        )
        visibility = _build_visibility(proposal.visibility)
        base_kwargs = {
            "assertion_id": assertion_id,
            "campaign_id": campaign_id,
            "session_id": request.session_id,
            "source_anchor": _optional_source_anchor(proposal.selection),
            "provenance": provenance,
            "visibility": visibility,
            "graph_scope": proposal.graph_scopes,
        }

        try:
            if proposal.proposal_kind == "object":
                if not proposal.object_ref:
                    raise GraphObjectAuthoringError(
                        "object proposal requires objectRef",
                        code="invalid_proposal",
                    )
                new_object = GraphObjectAuthoringNewObjectPayload.model_validate(proposal.object_ref)
                object_ref = AuthoredGraphObjectRef(
                    ref_kind="local_proposal",
                    local_proposal_id=proposal.local_proposal_id,
                    label=new_object.label,
                    kind=new_object.kind,
                    role=new_object.role,
                )
                assertion = AuthoredGraphObjectAssertion(
                    **base_kwargs,
                    assertion_kind="object",
                    operation="create",
                    object_ref=object_ref,
                    aliases=list(new_object.aliases),
                    summary=new_object.summary,
                )
            elif proposal.proposal_kind == "link_existing":
                if not proposal.existing_object_ref:
                    raise GraphObjectAuthoringError(
                        "link_existing proposal requires existingObjectRef",
                        code="invalid_proposal",
                    )
                selected_text = (proposal.selected_text or "").strip()
                normalized = (proposal.normalized_selected_text or selected_text).strip()
                if not selected_text or not normalized:
                    raise GraphObjectAuthoringError(
                        "link_existing proposal requires selected text",
                        code="invalid_proposal",
                    )
                assertion = AuthoredGraphLinkExistingAssertion(
                    **base_kwargs,
                    assertion_kind="link_existing",
                    operation=proposal.operation or "alias",
                    selected_text=selected_text,
                    normalized_selected_text=normalized,
                    existing_object_ref=_build_object_ref(proposal.existing_object_ref),
                    alias_text=proposal.alias_text,
                )
            elif proposal.proposal_kind == "relationship":
                if not proposal.source_object_ref or not proposal.target_object_ref:
                    raise GraphObjectAuthoringError(
                        "relationship proposal requires source and target object refs",
                        code="invalid_proposal",
                    )
                relationship_type = (proposal.relationship_type or "").strip()
                if not relationship_type:
                    raise GraphObjectAuthoringError(
                        "relationship proposal requires relationshipType",
                        code="invalid_relationship_type",
                    )
                assertion = AuthoredGraphRelationshipAssertion(
                    **base_kwargs,
                    assertion_kind="relationship",
                    operation="create",
                    source_object_ref=_build_object_ref(proposal.source_object_ref),
                    target_object_ref=_build_object_ref(proposal.target_object_ref),
                    relationship_type=relationship_type,
                    relationship_label=proposal.relationship_label,
                    direction=proposal.direction or "directed",
                    summary=proposal.summary,
                )
            elif proposal.proposal_kind == "merge_objects":
                if not proposal.survivor_object_ref:
                    raise GraphObjectAuthoringError(
                        "merge_objects proposal requires survivorObjectRef",
                        code="invalid_proposal",
                    )
                if not proposal.merged_object_refs:
                    raise GraphObjectAuthoringError(
                        "merge_objects proposal requires at least one mergedObjectRef",
                        code="invalid_proposal",
                    )
                survivor_ref = _validate_merge_object_ref(
                    proposal.survivor_object_ref,
                    local_proposal_id=proposal.local_proposal_id,
                    context="survivorObjectRef",
                )
                merged_refs = [
                    _validate_merge_object_ref(
                        ref_payload,
                        local_proposal_id=proposal.local_proposal_id,
                        context="mergedObjectRef",
                    )
                    for ref_payload in proposal.merged_object_refs
                ]
                assertion = AuthoredGraphMergeObjectsAssertion(
                    **base_kwargs,
                    assertion_kind="merge_objects",
                    operation="merge",
                    survivor_object_ref=survivor_ref,
                    merged_object_refs=merged_refs,
                    merge_reason=proposal.merge_reason,
                    matched_features=list(proposal.matched_features),
                    alias_policy=proposal.alias_policy or "preserve_all_aliases",
                    relationship_policy=proposal.relationship_policy or "preserve_all_relationships",
                    evidence_policy=proposal.evidence_policy or "preserve_all_evidence",
                )
                kind_warning = _merge_kind_conflict_warning(
                    survivor_ref,
                    merged_refs,
                    local_proposal_id=proposal.local_proposal_id,
                )
                if kind_warning:
                    diagnostics.append(kind_warning)
            else:
                raise GraphObjectAuthoringError(
                    f"Unsupported proposal kind: {proposal.proposal_kind}",
                    code="invalid_proposal",
                )
            assertions.append(assertion)
        except (GraphObjectAuthoringError, ValidationError) as exc:
            message = str(exc)
            code = getattr(exc, "code", "invalid_proposal")
            diagnostics.append(
                _diag(code, message, local_proposal_id=proposal.local_proposal_id),
            )

    return assertions, diagnostics


def build_assertions_preview(
    assertions: list[AuthoredGraphAssertion],
    proposals: list[GraphObjectAuthoringProposalPayload],
) -> list[AuthoredGraphAssertionPreview]:
    proposal_ids = [proposal.local_proposal_id for proposal in proposals]
    previews: list[AuthoredGraphAssertionPreview] = []
    for assertion, local_proposal_id in zip(assertions, proposal_ids, strict=False):
        if assertion.assertion_kind == "object":
            summary = f"Object: {assertion.object_ref.label}"
        elif assertion.assertion_kind == "link_existing":
            summary = (
                f"Link existing: {assertion.selected_text} → "
                f"{assertion.existing_object_ref.label}"
            )
        elif assertion.assertion_kind == "merge_objects":
            merged_labels = ", ".join(ref.label for ref in assertion.merged_object_refs)
            summary = (
                f"Merge: {assertion.survivor_object_ref.label} ← {merged_labels}"
            )
        else:
            summary = (
                f"Relationship: {assertion.source_object_ref.label} "
                f"{assertion.relationship_type} {assertion.target_object_ref.label}"
            )
        previews.append(
            AuthoredGraphAssertionPreview(
                assertion_id=assertion.assertion_id,
                assertion_kind=assertion.assertion_kind,
                operation=assertion.operation,
                local_proposal_id=local_proposal_id,
                summary=summary,
            )
        )
    return previews


def build_overlay_summary(
    existing_count: int,
    assertions: list[AuthoredGraphAssertion],
) -> GraphAuthoringOverlaySummary:
    object_count = sum(1 for item in assertions if item.assertion_kind == "object")
    link_count = sum(1 for item in assertions if item.assertion_kind == "link_existing")
    relationship_count = sum(1 for item in assertions if item.assertion_kind == "relationship")
    merge_count = sum(1 for item in assertions if item.assertion_kind == "merge_objects")
    proposed_count = len(assertions)
    return GraphAuthoringOverlaySummary(
        existing_assertion_count=existing_count,
        proposed_assertion_count=proposed_count,
        total_assertion_count=existing_count + proposed_count,
        object_count=object_count,
        link_existing_count=link_count,
        relationship_count=relationship_count,
        merge_objects_count=merge_count,
    )


def proposed_assertions_digest(assertions: list[AuthoredGraphAssertion]) -> str:
    payload = [assertion.model_dump(mode="json") for assertion in assertions]
    return stable_json_digest(payload)


def build_confirm_token(
    *,
    campaign_id: str,
    overlay_path: str,
    current_overlay_token: str,
    assertions: list[AuthoredGraphAssertion],
) -> str:
    return stable_json_digest(
        {
            "kind": CONFIRM_TOKEN_KIND,
            "campaign_id": campaign_id,
            "overlay_path": overlay_path,
            "current_overlay_token": current_overlay_token,
            "proposed_assertions_digest": proposed_assertions_digest(assertions),
            "schema_version": AUTHORED_GRAPH_OVERLAY_SCHEMA,
        }
    )


def _resolve_store(corpus_root: Path | None) -> GraphAuthoringOverlayStore:
    if corpus_root is None:
        from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

        return GraphAuthoringOverlayStore(default_corpus_root())
    return GraphAuthoringOverlayStore(corpus_root)


def classify_graph_review_expressibility(
    proposals: list[GraphObjectAuthoringProposalPayload],
) -> Literal["EXPRESSIBLE", "INEXPRESSIBLE"]:
    if not proposals:
        return "INEXPRESSIBLE"
    for proposal in proposals:
        if proposal.proposal_kind not in EXPRESSIBLE_KINDS:
            return "INEXPRESSIBLE"
        if proposal.proposal_kind == "link_existing":
            node_id = ""
            if isinstance(proposal.existing_object_ref, dict):
                node_id = str(proposal.existing_object_ref.get("nodeId") or proposal.existing_object_ref.get("node_id") or "")
            if not node_id.strip():
                return "INEXPRESSIBLE"
        if proposal.proposal_kind == "relationship":
            source_id = ""
            target_id = ""
            if isinstance(proposal.source_object_ref, dict):
                source_id = str(proposal.source_object_ref.get("nodeId") or proposal.source_object_ref.get("node_id") or "")
            if isinstance(proposal.target_object_ref, dict):
                target_id = str(proposal.target_object_ref.get("nodeId") or proposal.target_object_ref.get("node_id") or "")
            if not source_id.strip() or not target_id.strip():
                return "INEXPRESSIBLE"
    return "EXPRESSIBLE"


def authored_world_id(request: GraphObjectAuthoringPrepareRequest | GraphObjectAuthoringCommitRequest) -> str:
    explicit = (request.world_id or "").strip()
    if explicit:
        return explicit
    return request.campaign_id


def graph_review_actor(campaign_id: str) -> str:
    return f"graph-review:{campaign_id}"


def _prepare_binding_key() -> bytes:
    explicit = os.environ.get(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "").strip()
    if not explicit:
        raise GraphObjectAuthoringError(
            "Graph Review confirm binding key is not configured "
            f"({GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV}).",
            code="authority_unavailable",
            status_code=503,
        )
    return hashlib.sha256(
        f"{GRAPH_REVIEW_PREPARE_BINDING_SCHEMA}:{explicit}".encode("utf-8")
    ).digest()


def publication_intent_payload(
    *,
    world_id: str,
    campaign_id: str,
    campaign_rel: str | None,
    source_run_id: str | None,
    source_artifact_id: str | None,
    source_revision_id: str | None,
    expected_parent_revision_id: str | None,
    authority_operation_id: str | None,
    expressibility: str,
    actor: str,
    assertions_digest: str,
    expires_at: str,
    contribution_digest: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": GRAPH_REVIEW_PREPARE_BINDING_SCHEMA,
        "world_id": world_id,
        "campaign_id": campaign_id,
        "campaign_rel": campaign_rel,
        "source_run_id": source_run_id,
        "source_artifact_id": source_artifact_id,
        "source_revision_id": source_revision_id,
        "expected_parent_revision_id": expected_parent_revision_id,
        "authority_operation_id": authority_operation_id,
        "expressibility": expressibility,
        "actor": actor,
        "assertions_digest": assertions_digest,
        "contribution_digest": contribution_digest,
        "expires_at": expires_at,
    }


def sign_publication_intent(payload: dict[str, Any]) -> str:
    import base64

    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    digest = hmac.new(_prepare_binding_key(), raw, hashlib.sha256).hexdigest()
    return f"v1.{body}.{digest}"


def decode_publication_intent(token: str) -> dict[str, Any]:
    import base64

    raw_token = (token or "").strip()
    parts = raw_token.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    body = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(body.encode("ascii"))
    except Exception as exc:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        ) from exc
    expected = hmac.new(_prepare_binding_key(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(parts[2], expected):
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        ) from exc
    if not isinstance(payload, dict):
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )
    expires_at = str(payload.get("expires_at") or "")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at)
        except ValueError as exc:
            raise GraphObjectAuthoringError(
                "Prepared confirmation has an invalid expiry.",
                code="confirmation_invalid",
                status_code=409,
            ) from exc
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if datetime.now(UTC) > expiry:
            raise GraphObjectAuthoringError(
                "Prepared confirmation has expired. Prepare again.",
                code="confirmation_expired",
                status_code=409,
            )
    return payload


def verify_publication_intent(token: str, payload: dict[str, Any]) -> None:
    decoded = decode_publication_intent(token)
    expected = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    actual = json.dumps(decoded, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if not hmac.compare_digest(expected, actual):
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared publication intent.",
            code="confirmation_invalid",
            status_code=409,
        )


def graph_review_source_evidence_ref_id(source_artifact_id: str) -> str:
    """One contribution evidence handle for the sealed Graph Review source pair."""
    return f"grauth-ev:{source_artifact_id}"


def translate_assertions_to_contribution(
    *,
    world_id: str,
    campaign_id: str,
    actor: str,
    source_artifact_id: str,
    source_revision_id: str,
    assertions: list[AuthoredGraphAssertion],
):
    from apps.live_control_server.models.world_graph_contributions import (
        build_assertion,
        create_graph_contribution,
    )

    evidence_ref_ids = [graph_review_source_evidence_ref_id(source_artifact_id)]
    node_id_by_local_proposal_id = {
        str(assertion.object_ref.local_proposal_id): authored_object_node_id(
            assertion.assertion_id
        )
        for assertion in assertions
        if assertion.assertion_kind == "object"
        and assertion.object_ref.local_proposal_id
    }

    def exact_node_id(ref: AuthoredGraphObjectRef) -> str:
        return (
            (ref.node_id or "").strip()
            or node_id_by_local_proposal_id.get(str(ref.local_proposal_id or ""), "")
        )

    accepted = []
    for assertion in assertions:
        if assertion.assertion_kind == "object":
            node_id = authored_object_node_id(assertion.assertion_id)
            accepted.append(
                build_assertion(
                    assertion_kind="node",
                    acceptance_state="accepted",
                    subject_node_id=node_id,
                    label=assertion.object_ref.label,
                    value={
                        "kind": assertion.object_ref.kind or "unknown",
                        "role": assertion.object_ref.role or assertion.object_ref.kind or "unknown",
                        "source_domains": ["worldbuilding"],
                        "aliases": list(assertion.aliases or [assertion.object_ref.label]),
                        "summary": assertion.summary,
                    },
                    evidence_ref_ids=evidence_ref_ids,
                    source_artifact_id=source_artifact_id,
                    source_revision_id=source_revision_id,
                    campaign_scope=campaign_id,
                    epistemic_kind="fact",
                    visibility="gm",
                    identity_resolution_outcome="created_new",
                )
            )
        elif assertion.assertion_kind == "link_existing":
            node_id = (assertion.existing_object_ref.node_id or "").strip()
            if not node_id:
                raise GraphObjectAuthoringError(
                    "link_existing requires an exact existing graph node id",
                    code="governed_write_inexpressible",
                )
            alias_text = (assertion.alias_text or assertion.selected_text or "").strip()
            accepted.append(
                build_assertion(
                    assertion_kind="alias",
                    acceptance_state="accepted",
                    subject_node_id=node_id,
                    label=alias_text or assertion.existing_object_ref.label,
                    value={
                        "alias": alias_text or assertion.existing_object_ref.label,
                        "source_domains": ["worldbuilding"],
                    },
                    evidence_ref_ids=evidence_ref_ids,
                    source_artifact_id=source_artifact_id,
                    source_revision_id=source_revision_id,
                    campaign_scope=campaign_id,
                    epistemic_kind="fact",
                    visibility="gm",
                    identity_resolution_outcome="resolved_existing",
                )
            )
        elif assertion.assertion_kind == "relationship":
            source_id = exact_node_id(assertion.source_object_ref)
            target_id = exact_node_id(assertion.target_object_ref)
            if not source_id or not target_id:
                raise GraphObjectAuthoringError(
                    "relationship requires exact source and target node ids",
                    code="governed_write_inexpressible",
                )
            accepted.append(
                build_assertion(
                    assertion_kind="edge",
                    acceptance_state="accepted",
                    subject_node_id=source_id,
                    target_node_id=target_id,
                    predicate=assertion.relationship_type,
                    label=assertion.relationship_label,
                    value={"source_domains": ["worldbuilding"], "direction": assertion.direction},
                    evidence_ref_ids=evidence_ref_ids,
                    source_artifact_id=source_artifact_id,
                    source_revision_id=source_revision_id,
                    campaign_scope=campaign_id,
                    epistemic_kind="fact",
                    visibility="gm",
                    identity_resolution_outcome="created_new",
                )
            )
        else:
            raise GraphObjectAuthoringError(
                f"{assertion.assertion_kind} is not a DungeonMind-publishable Graph Review operation",
                code="governed_write_inexpressible",
            )
    return create_graph_contribution(
        world_id=world_id,
        source_kind="graph_review_authored_assertion",
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_id,
        authored_by=actor,
        proposal_digest=stable_json_digest(
            [assertion.model_dump(mode="json") for assertion in accepted]
        ),
        accepted_assertions=accepted,
        produced_at=STABLE_ASSERTION_TIMESTAMP,
    )


def resolve_graph_review_source(
    request: GraphObjectAuthoringPrepareRequest | GraphObjectAuthoringCommitRequest,
    *,
    authored_world: str,
    resolved_source: Any | None = None,
):
    if resolved_source is not None:
        run_campaign = (getattr(resolved_source, "campaign_id", "") or "").strip()
        if run_campaign and run_campaign != request.campaign_id:
            raise GraphObjectAuthoringError(
                "resolved source belongs to a different campaign",
                code="source_inadmissible",
            )
        run_world = (getattr(resolved_source, "world_id", "") or "").strip()
        if run_world and run_world != authored_world:
            raise GraphObjectAuthoringError(
                "resolved source belongs to a different world",
                code="source_inadmissible",
            )
        return resolved_source
    run_id = (request.source_run_id or "").strip()
    if not run_id:
        raise GraphObjectAuthoringError(
            "Graph Review confirmation requires an exact sourceRunId.",
            code="source_unresolved",
        )
    from apps.live_control_server.services.promotable_ingest_run import (
        PromotableIngestRunError,
        resolve_promotable_ingest_run,
    )

    try:
        resolved = resolve_promotable_ingest_run(run_id)
    except PromotableIngestRunError as exc:
        code = "source_artifact_not_found" if exc.code in {"run_not_found", "not_found"} else "source_unresolved"
        raise GraphObjectAuthoringError(str(exc), code=code, status_code=exc.status_code) from exc
    run_campaign = (resolved.campaign_id or "").strip()
    if run_campaign != request.campaign_id:
        raise GraphObjectAuthoringError(
            "sourceRunId belongs to a different campaign",
            code="source_inadmissible",
        )
    run_world = (resolved.world_id or "").strip()
    if run_world and run_world != authored_world:
        raise GraphObjectAuthoringError(
            "sourceRunId belongs to a different world",
            code="source_inadmissible",
        )
    return resolved


def _buddy_source_artifact(resolved: Any):
    attached = getattr(resolved, "source_artifact", None)
    if attached is not None:
        return attached
    from apps.live_control_server.config import repo_root
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        get_source_artifact,
    )

    try:
        return get_source_artifact(repo_root(), str(resolved.source_artifact_id))
    except SourceArtifactRegistryError as exc:
        raise GraphObjectAuthoringError(
            str(exc),
            code="source_artifact_not_found",
            status_code=getattr(exc, "status_code", 404),
        ) from exc


def _scope_check_buddy_artifact(
    artifact: Any,
    *,
    authored_world: str,
    authored_campaign: str,
) -> None:
    art_campaign = (getattr(artifact, "campaign_id", "") or "").strip()
    if art_campaign and art_campaign != authored_campaign:
        raise GraphObjectAuthoringError(
            "source artifact belongs to a different campaign",
            code="source_inadmissible",
        )
    art_world = (getattr(artifact, "world_id", "") or "").strip()
    if art_world and art_world != authored_world:
        raise GraphObjectAuthoringError(
            "source artifact belongs to a different world",
            code="source_inadmissible",
        )


def _raise_source_admission(exc: Exception) -> None:
    from apps.live_control_server.ports.world_graph_source_admission import (
        WorldGraphSourceAdmissionError,
    )

    if not isinstance(exc, WorldGraphSourceAdmissionError):
        raise GraphObjectAuthoringError(
            str(exc),
            code="authority_unavailable",
            status_code=503,
        ) from exc
    mapped = {
        "source_not_admitted": "source_artifact_not_found",
        "source_identity_conflict": "source_identity_conflict",
        "source_identity_missing": "source_unresolved",
        "authority_unavailable": "authority_unavailable",
        "inexpressible": "source_inadmissible",
    }.get(exc.code, "source_inadmissible")
    status = 503 if mapped == "authority_unavailable" else 409
    if mapped in {"source_artifact_not_found", "source_unresolved"}:
        status = 422
    raise GraphObjectAuthoringError(str(exc), code=mapped, status_code=status) from exc


def prove_or_admit_graph_review_source(
    *,
    world_id: str,
    campaign_id: str,
    resolved_source: Any,
    source_admission: Any | None = None,
) -> tuple[str, str]:
    from apps.live_control_server.ports.world_graph_source_admission import (
        WorldGraphSourceAdmissionError,
        WorldGraphSourceAdmissionRequest,
    )
    from apps.live_control_server.ports.world_graph_source_admission_access import (
        get_world_graph_source_admission_authority,
    )

    artifact = _buddy_source_artifact(resolved_source)
    _scope_check_buddy_artifact(
        artifact,
        authored_world=world_id,
        authored_campaign=campaign_id,
    )
    admission = source_admission or get_world_graph_source_admission_authority()
    request = WorldGraphSourceAdmissionRequest(
        world_id=world_id,
        campaign_id=campaign_id,
        source_artifact=artifact,
        source_revision_token=str(getattr(resolved_source, "source_revision_id")),
        source_uri=getattr(resolved_source, "sealed_source_uri", None)
        or getattr(artifact, "uri", None),
    )
    try:
        admitted = admission.prove_or_admit(request)
    except WorldGraphSourceAdmissionError as exc:
        _raise_source_admission(exc)
        raise
    return admitted.source_artifact_id, admitted.source_revision_id


def prove_graph_review_source(
    *,
    world_id: str,
    source_artifact_id: str,
    source_revision_id: str,
    source_revision_token: str,
    source_admission: Any | None = None,
) -> tuple[str, str]:
    from apps.live_control_server.ports.world_graph_source_admission import (
        WorldGraphSourceAdmissionError,
    )
    from apps.live_control_server.ports.world_graph_source_admission_access import (
        get_world_graph_source_admission_authority,
    )

    admission = source_admission or get_world_graph_source_admission_authority()
    try:
        admitted = admission.prove(
            world_id=world_id,
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            source_revision_token=source_revision_token,
        )
    except WorldGraphSourceAdmissionError as exc:
        _raise_source_admission(exc)
        raise
    return admitted.source_artifact_id, admitted.source_revision_id


def prepare_graph_object_authoring_write(
    request: GraphObjectAuthoringPrepareRequest,
    *,
    corpus_root: Path | None = None,
    authority: Any | None = None,
    resolved_source: Any | None = None,
    source_admission: Any | None = None,
) -> GraphObjectAuthoringPrepareResponse:
    validate_authoring_campaign_scope(request.campaign_id, request.campaign_rel)

    if not request.proposals:
        raise GraphObjectAuthoringError(
            "At least one staged proposal is required to prepare a write preview.",
            code="empty_proposals",
        )

    store = _resolve_store(corpus_root)
    overlay_path = store.overlay_path(request.campaign_id, campaign_rel=request.campaign_rel)
    events_path = store.events_path(request.campaign_id, campaign_rel=request.campaign_rel)
    current_token = overlay_file_token(overlay_path, campaign_id=request.campaign_id)
    existing_overlay = store.load_overlay(request.campaign_id, campaign_rel=request.campaign_rel)

    assertions, assertion_diagnostics = build_assertions_from_proposals(request)
    local_proposal_ids = {
        _assertion_id(
            request.campaign_id,
            proposal,
            normalized_payload=_normalized_proposal_payload(proposal),
        ): proposal.local_proposal_id
        for proposal in request.proposals
    }
    merge_conflicts = detect_merge_assertion_conflicts(
        assertions,
        existing_assertions=existing_overlay.assertions,
        local_proposal_id_by_assertion_id=local_proposal_ids,
    )
    blocking = _blocking_assertion_diagnostics([*assertion_diagnostics, *merge_conflicts])
    if blocking:
        raise GraphObjectAuthoringError(
            blocking[0].message,
            code=blocking[0].code,
        )
    if not assertions:
        raise GraphObjectAuthoringError("No valid assertions could be built.", code="empty_proposals")

    overlap_warnings = detect_prepare_overlap_warnings(
        request,
        existing_overlay=existing_overlay,
    )
    prepare_warnings = _non_blocking_assertion_diagnostics(assertion_diagnostics)
    expressibility = classify_graph_review_expressibility(request.proposals)
    world_id = authored_world_id(request)
    actor = graph_review_actor(request.campaign_id)
    expires_at = (datetime.now(UTC) + PREPARE_TTL).isoformat()
    assertions_digest = proposed_assertions_digest(assertions)
    preview = build_assertions_preview(assertions, request.proposals)
    summary = build_overlay_summary(len(existing_overlay.assertions), assertions)
    diagnostics = [*prepare_warnings, *overlap_warnings]

    source_artifact_id = None
    source_revision_id = None
    expected_parent = None
    operation_id = None
    contribution_digest = None
    if expressibility == "INEXPRESSIBLE":
        diagnostics.append(
            _diag(
                "governed_write_inexpressible",
                "merge_objects and unknown Graph Review operations are not publishable through DungeonMind.",
                severity="error",
            )
        )
    else:
        resolved = resolve_graph_review_source(
            request,
            authored_world=world_id,
            resolved_source=resolved_source,
        )
        buddy_artifact_id = str(getattr(resolved, "source_artifact_id"))
        buddy_revision_id = str(getattr(resolved, "source_revision_id"))
        from apps.live_control_server.ports.world_graph_authority_access import (
            get_world_graph_authority,
        )
        from apps.live_control_server.ports.world_graph_authority import (
            WorldGraphAuthorityError,
        )

        mounted = authority or get_world_graph_authority()
        try:
            expected_parent = mounted.current_head(world_id).revision_id
        except WorldGraphAuthorityError as exc:
            code = "authority_unavailable" if exc.code == "authority_unavailable" else "authority_unavailable"
            raise GraphObjectAuthoringError(str(exc), code=code, status_code=503) from exc
        source_artifact_id, source_revision_id = prove_or_admit_graph_review_source(
            world_id=world_id,
            campaign_id=request.campaign_id,
            resolved_source=resolved,
            source_admission=source_admission,
        )
        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            graph_review_authority_operation_id,
        )

        operation_id = graph_review_authority_operation_id(
            world_id=world_id,
            campaign_id=request.campaign_id,
            campaign_rel=request.campaign_rel,
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            sealed_proposal_digest=assertions_digest,
            expected_parent_revision_id=expected_parent,
        )
        contribution = translate_assertions_to_contribution(
            world_id=world_id,
            campaign_id=request.campaign_id,
            actor=actor,
            source_artifact_id=buddy_artifact_id,
            source_revision_id=buddy_revision_id,
            assertions=assertions,
        )
        contribution_digest = contribution_binding_digest(contribution)

    intent = publication_intent_payload(
        world_id=world_id,
        campaign_id=request.campaign_id,
        campaign_rel=request.campaign_rel,
        source_run_id=request.source_run_id,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        expected_parent_revision_id=expected_parent,
        authority_operation_id=operation_id,
        expressibility=expressibility,
        actor=actor,
        assertions_digest=assertions_digest,
        contribution_digest=contribution_digest,
        expires_at=expires_at,
    )
    confirm_token = sign_publication_intent(intent)
    event_count = 1 + len(assertions)

    return GraphObjectAuthoringPrepareResponse(
        campaign_id=request.campaign_id,
        overlay_path=str(overlay_path),
        event_log_path=str(events_path),
        current_overlay_token=current_token,
        proposed_assertions_digest=assertions_digest,
        confirm_token=confirm_token,
        assertion_count=len(assertions),
        event_count=event_count,
        assertions_preview=preview,
        overlay_summary=summary,
        diagnostics=diagnostics,
        no_mutation_guarantees=list(NO_MUTATION_GUARANTEES_PREPARE),
        world_id=world_id,
        expected_parent_revision_id=expected_parent,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        authority_operation_id=operation_id,
        contribution_digest=contribution_digest,
        expressibility=expressibility,
        expires_at=expires_at,
        actor=actor,
    )
