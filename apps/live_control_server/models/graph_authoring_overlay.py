"""Durable authored graph overlay contracts for human-authored campaign graph memory."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

AUTHORED_GRAPH_OVERLAY_SCHEMA = "dmb.authored_graph_overlay.v1"

GraphVisibility = Literal[
    "gm_private",
    "player_visible",
    "table_known",
    "character_specific",
    "hidden_until_revealed",
]

GraphScope = Literal[
    "recap_graph",
    "worldbuilding_graph",
    "campaign_memory_graph",
    "gm_private_graph",
    "player_visible_graph",
    "evaluation_gold",
]

GraphAuthoringOrigin = Literal[
    "human_authored",
    "human_corrected_extraction",
    "imported_worldbuilding",
    "llm_proposed_human_accepted",
]

GraphAuthoringSurface = Literal["memory_ingest_graph_authoring"]

GraphAuthoringSourceAnchorKind = Literal[
    "text_span",
    "graph_node_reference",
    "block",
    "relationship_context",
]

AuthoredGraphAssertionKind = Literal["object", "link_existing", "relationship"]

AuthoredGraphAssertionStatus = Literal["authored", "superseded", "retracted"]

AuthoredGraphObjectRefKind = Literal[
    "existing_graph_node",
    "local_proposal",
    "manual_ref",
    "authored_node",
]

AuthoredGraphObjectOperation = Literal["create", "update", "alias", "link_existing"]

AuthoredGraphLinkExistingOperation = Literal["alias", "reference", "link_existing"]

AuthoredGraphRelationshipOperation = Literal["create", "update", "link_existing"]

AuthoredGraphRelationshipDirection = Literal["directed", "undirected"]

DEFAULT_GRAPH_SCOPES: tuple[GraphScope, ...] = ("recap_graph", "campaign_memory_graph")

_SAFE_CAMPAIGN_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class GraphAuthoringOverlayError(ValueError):
    """Base error for authored graph overlay validation."""


class UnsafeCampaignIdError(GraphAuthoringOverlayError):
    """Raised when campaign_id would escape authored overlay storage."""


def validate_campaign_id(campaign_id: str) -> str:
    candidate = campaign_id.strip()
    if not candidate or not _SAFE_CAMPAIGN_ID.fullmatch(candidate):
        raise UnsafeCampaignIdError("unsafe campaign_id for graph authoring overlay")
    if ".." in candidate or "/" in candidate or "\\" in candidate:
        raise UnsafeCampaignIdError("unsafe campaign_id for graph authoring overlay")
    if _contains_uri_scheme(candidate):
        raise UnsafeCampaignIdError("unsafe campaign_id for graph authoring overlay")
    return candidate


def _contains_uri_scheme(value: str) -> bool:
    return "://" in value


def normalize_selected_text(text: str) -> str:
    return " ".join(text.split())


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat_z(value: datetime | None = None) -> str:
    stamp = value or _utc_now()
    return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


class GraphAuthoringSourceAnchor(BaseModel):
    anchor_kind: GraphAuthoringSourceAnchorKind
    selected_text: str
    normalized_selected_text: str
    surrounding_text_before: str | None = None
    surrounding_text_after: str | None = None
    paragraph_ordinal: int | None = None
    source_span_ref_id: str | None = None
    tiptap_from: int | None = None
    tiptap_to: int | None = None
    selected_text_sha256: str | None = None
    context_sha256: str | None = None
    existing_graph_node_id: str | None = None

    @model_validator(mode="after")
    def _anchor_has_redundant_evidence(self) -> GraphAuthoringSourceAnchor:
        if not self.selected_text.strip():
            raise ValueError("source anchor selected_text must be non-blank")
        if not self.normalized_selected_text.strip():
            raise ValueError("source anchor normalized_selected_text must be non-blank")
        return self


class GraphAuthoringProvenance(BaseModel):
    origin: GraphAuthoringOrigin
    authoring_surface: GraphAuthoringSurface
    created_at: str
    updated_at: str | None = None
    source_run_id: str | None = None
    source_graph_id: str | None = None
    source_projection_id: str | None = None
    operator_note: str | None = None


class GraphVisibilityPolicy(BaseModel):
    visibility: GraphVisibility = "gm_private"
    visible_to_player_ids: list[str] = Field(default_factory=list)
    visible_to_character_ids: list[str] = Field(default_factory=list)
    reveal_state: Literal["unrevealed", "partial", "revealed"] = "unrevealed"
    visibility_note: str | None = None


class AuthoredGraphObjectRef(BaseModel):
    ref_kind: AuthoredGraphObjectRefKind
    node_id: str | None = None
    local_proposal_id: str | None = None
    authored_node_id: str | None = None
    label: str
    kind: str | None = None
    role: str | None = None

    @field_validator("label")
    @classmethod
    def _label_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("object ref label must be non-blank")
        return trimmed


class AuthoredGraphAssertionBase(BaseModel):
    assertion_id: str
    assertion_kind: AuthoredGraphAssertionKind
    operation: str

    campaign_id: str
    session_id: str | None = None
    source_artifact_path: str | None = None
    source_artifact_sha256: str | None = None

    source_anchor: GraphAuthoringSourceAnchor | None = None
    provenance: GraphAuthoringProvenance
    visibility: GraphVisibilityPolicy = Field(default_factory=GraphVisibilityPolicy)
    graph_scope: list[GraphScope] = Field(default_factory=lambda: list(DEFAULT_GRAPH_SCOPES))

    status: AuthoredGraphAssertionStatus = "authored"
    include_in_gold_eval: bool = False
    gold_eval_notes: str | None = None

    @field_validator("campaign_id")
    @classmethod
    def _validate_campaign_id(cls, value: str) -> str:
        return validate_campaign_id(value)

    @field_validator("graph_scope")
    @classmethod
    def _graph_scope_not_empty(cls, value: list[GraphScope]) -> list[GraphScope]:
        if not value:
            raise ValueError("graph_scope must include at least one scope")
        return value


class AuthoredGraphObjectAssertion(AuthoredGraphAssertionBase):
    assertion_kind: Literal["object"] = "object"
    operation: AuthoredGraphObjectOperation
    object_ref: AuthoredGraphObjectRef
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None


class AuthoredGraphLinkExistingAssertion(AuthoredGraphAssertionBase):
    assertion_kind: Literal["link_existing"] = "link_existing"
    operation: AuthoredGraphLinkExistingOperation
    selected_text: str
    normalized_selected_text: str
    existing_object_ref: AuthoredGraphObjectRef
    alias_text: str | None = None


class AuthoredGraphRelationshipAssertion(AuthoredGraphAssertionBase):
    assertion_kind: Literal["relationship"] = "relationship"
    operation: AuthoredGraphRelationshipOperation = "create"
    source_object_ref: AuthoredGraphObjectRef
    target_object_ref: AuthoredGraphObjectRef
    relationship_type: str
    relationship_label: str | None = None
    direction: AuthoredGraphRelationshipDirection
    summary: str | None = None

    @field_validator("relationship_type")
    @classmethod
    def _relationship_type_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("relationship_type must be non-blank")
        return trimmed


AuthoredGraphAssertion = Annotated[
    AuthoredGraphObjectAssertion
    | AuthoredGraphLinkExistingAssertion
    | AuthoredGraphRelationshipAssertion,
    Field(discriminator="assertion_kind"),
]


class AuthoredGraphOverlay(BaseModel):
    schema_version: Literal["dmb.authored_graph_overlay.v1"] = AUTHORED_GRAPH_OVERLAY_SCHEMA
    campaign_id: str
    overlay_id: str
    created_at: str
    updated_at: str
    assertions: list[
        Annotated[
            AuthoredGraphObjectAssertion
            | AuthoredGraphLinkExistingAssertion
            | AuthoredGraphRelationshipAssertion,
            Field(discriminator="assertion_kind"),
        ]
    ] = Field(default_factory=list)

    @field_validator("campaign_id")
    @classmethod
    def _validate_overlay_campaign_id(cls, value: str) -> str:
        return validate_campaign_id(value)


def default_graph_authoring_provenance(
    *,
    origin: GraphAuthoringOrigin = "human_authored",
    authoring_surface: GraphAuthoringSurface = "memory_ingest_graph_authoring",
    created_at: str | None = None,
    operator_note: str | None = None,
    source_graph_id: str | None = None,
) -> GraphAuthoringProvenance:
    stamp = created_at or isoformat_z()
    return GraphAuthoringProvenance(
        origin=origin,
        authoring_surface=authoring_surface,
        created_at=stamp,
        updated_at=stamp,
        source_graph_id=source_graph_id,
        operator_note=operator_note,
    )


def build_source_anchor_from_payload(payload: Mapping[str, Any]) -> GraphAuthoringSourceAnchor:
    selected_text = str(payload.get("selected_text") or payload.get("selectedText") or "")
    normalized = str(
        payload.get("normalized_selected_text")
        or payload.get("normalizedSelectedText")
        or normalize_selected_text(selected_text)
    )
    before = payload.get("surrounding_text_before") or payload.get("surroundingTextBefore")
    after = payload.get("surrounding_text_after") or payload.get("surroundingTextAfter")
    context_parts = [part for part in (before, selected_text, after) if isinstance(part, str) and part]
    context_sha256 = hash_text("\n".join(context_parts)) if context_parts else None
    anchor = GraphAuthoringSourceAnchor(
        anchor_kind=payload.get("anchor_kind") or payload.get("selectionKind") or "text_span",
        selected_text=selected_text,
        normalized_selected_text=normalized,
        surrounding_text_before=before if isinstance(before, str) else None,
        surrounding_text_after=after if isinstance(after, str) else None,
        paragraph_ordinal=payload.get("paragraph_ordinal") or payload.get("paragraphOrdinal"),
        source_span_ref_id=payload.get("source_span_ref_id") or payload.get("sourceSpanRefId"),
        tiptap_from=payload.get("tiptap_from") or payload.get("tiptapFrom"),
        tiptap_to=payload.get("tiptap_to") or payload.get("tiptapTo"),
        selected_text_sha256=hash_text(normalized) if normalized else None,
        context_sha256=context_sha256,
        existing_graph_node_id=payload.get("existing_graph_node_id")
        or payload.get("existingNodeId"),
    )
    return anchor


def create_empty_authored_graph_overlay(
    campaign_id: str,
    *,
    overlay_id: str | None = None,
    created_at: str | None = None,
) -> AuthoredGraphOverlay:
    safe_campaign_id = validate_campaign_id(campaign_id)
    stamp = created_at or isoformat_z()
    return AuthoredGraphOverlay(
        campaign_id=safe_campaign_id,
        overlay_id=overlay_id or f"overlay-{safe_campaign_id}",
        created_at=stamp,
        updated_at=stamp,
        assertions=[],
    )
