"""Prepare authored graph overlay writes from staged local proposals."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.live_control_server.models.graph_authoring_overlay import (
    AUTHORED_GRAPH_OVERLAY_SCHEMA,
    AuthoredGraphAssertion,
    AuthoredGraphLinkExistingAssertion,
    AuthoredGraphObjectAssertion,
    AuthoredGraphObjectRef,
    AuthoredGraphRelationshipAssertion,
    GraphAuthoringProvenance,
    GraphAuthoringSourceAnchor,
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
]

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
    proposal_kind: Literal["object", "link_existing", "relationship"] = Field(alias="proposalKind")
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
    visibility: GraphObjectAuthoringVisibilityPayload
    graph_scopes: list[GraphScope] = Field(default_factory=lambda: ["recap_graph", "campaign_memory_graph"], alias="graphScopes")
    provenance_preview: GraphObjectAuthoringProvenancePayload = Field(alias="provenancePreview")


class GraphObjectAuthoringPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    campaign_id: str = Field(alias="campaignId")
    campaign_rel: str | None = Field(default=None, alias="campaignRel")
    session_id: str | None = Field(default=None, alias="sessionId")
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
    source_run_id: str | None = Field(default=None, alias="sourceRunId")
    source_graph_id: str | None = Field(default=None, alias="sourceGraphId")
    source_projection_id: str | None = Field(default=None, alias="sourceProjectionId")
    proposals: list[GraphObjectAuthoringProposalPayload]
    confirm_token: str = Field(alias="confirmToken")
    current_overlay_token: str = Field(alias="currentOverlayToken")
    operator_note: str | None = Field(default=None, alias="operatorNote")


def authoring_prepare_request_from_write(
    request: GraphObjectAuthoringPrepareRequest | GraphObjectAuthoringCommitRequest,
) -> GraphObjectAuthoringPrepareRequest:
    if isinstance(request, GraphObjectAuthoringPrepareRequest):
        return request
    return GraphObjectAuthoringPrepareRequest(
        campaign_id=request.campaign_id,
        campaign_rel=request.campaign_rel,
        session_id=request.session_id,
        source_run_id=request.source_run_id,
        source_graph_id=request.source_graph_id,
        source_projection_id=request.source_projection_id,
        proposals=request.proposals,
        operator_note=request.operator_note,
    )


class AuthoredGraphAssertionPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    assertion_kind: Literal["object", "link_existing", "relationship"]
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


class GraphObjectAuthoringCommitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    committed: bool
    campaign_id: str
    overlay_path: str
    event_log_path: str
    backup_path: str | None = None
    assertion_count: int
    event_count: int
    new_overlay_token: str
    diagnostics: list[GraphAuthoringDiagnostic]
    no_mutation_guarantees: list[str]


def stable_json_digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def _build_object_ref(payload: dict[str, Any]) -> AuthoredGraphObjectRef:
    parsed = GraphObjectAuthoringObjectRefPayload.model_validate(payload)
    return AuthoredGraphObjectRef(
        ref_kind=parsed.ref_kind,
        node_id=parsed.node_id,
        local_proposal_id=parsed.local_proposal_id,
        label=parsed.label,
        kind=parsed.kind,
        role=parsed.role,
    )


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
            else:
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
    proposed_count = len(assertions)
    return GraphAuthoringOverlaySummary(
        existing_assertion_count=existing_count,
        proposed_assertion_count=proposed_count,
        total_assertion_count=existing_count + proposed_count,
        object_count=object_count,
        link_existing_count=link_count,
        relationship_count=relationship_count,
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


def prepare_graph_object_authoring_write(
    request: GraphObjectAuthoringPrepareRequest,
    *,
    corpus_root: Path | None = None,
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

    assertions, diagnostics = build_assertions_from_proposals(request)
    if diagnostics:
        raise GraphObjectAuthoringError(
            diagnostics[0].message,
            code=diagnostics[0].code,
        )
    if not assertions:
        raise GraphObjectAuthoringError("No valid assertions could be built.", code="empty_proposals")

    overlap_warnings = detect_prepare_overlap_warnings(
        request,
        existing_overlay=existing_overlay,
    )

    confirm_token = build_confirm_token(
        campaign_id=request.campaign_id,
        overlay_path=str(overlay_path),
        current_overlay_token=current_token,
        assertions=assertions,
    )
    assertions_digest = proposed_assertions_digest(assertions)
    preview = build_assertions_preview(assertions, request.proposals)
    summary = build_overlay_summary(len(existing_overlay.assertions), assertions)
    # One batch event plus one per assertion at commit time.
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
        diagnostics=overlap_warnings,
        no_mutation_guarantees=list(NO_MUTATION_GUARANTEES_PREPARE),
    )
