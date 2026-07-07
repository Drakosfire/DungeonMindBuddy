"""Export explicitly opted-in authored graph overlay assertions to eval artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphAssertion,
    AuthoredGraphLinkExistingAssertion,
    AuthoredGraphObjectAssertion,
    AuthoredGraphObjectRef,
    AuthoredGraphOverlay,
    AuthoredGraphRelationshipAssertion,
    GraphAuthoringProvenance,
    GraphAuthoringSourceAnchor,
    GraphScope,
    GraphVisibilityPolicy,
    UnsafeCampaignIdError,
    UnsafeCampaignRelError,
    hash_text,
    isoformat_z,
    validate_campaign_id,
    validate_campaign_rel,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
)
from src.live_play.live_store import write_json

AUTHORED_GRAPH_GOLD_EVAL_EXPORT_SCHEMA = "dmb.authored_graph_gold_eval_export.v1"
AUTHORED_GRAPH_GOLD_EVAL_EXPORT_VERSION = "0.1"
EXPORT_FILENAME_PREFIX = "authored_graph_gold_eval_export"
_UNSAFE_CREATED_AT_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

AuthoredGraphGoldKnowledgeScope = Literal[
    "session_local",
    "campaign_retrospective",
    "cross_session_context_required",
]


class AuthoredGraphGoldEvalExportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    campaign_rel: str | None = None
    session_id: str | None = None
    knowledge_scope: AuthoredGraphGoldKnowledgeScope = "session_local"
    overlay_path: str | None = None
    created_at: str | None = None
    operator_note: str | None = None


class AuthoredGraphGoldEvalExportSourceOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overlay_id: str
    overlay_path: str | None = None
    overlay_token: str | None = None
    assertion_count: int
    included_assertion_count: int


class AuthoredGraphGoldEvalExportDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manual_export: bool = True
    source_markdown_mutated: bool = False
    extracted_run_artifacts_mutated: bool = False
    candidate_graph_gold_mutated: bool = False
    overlay_mutated: bool = False
    llm_used: bool = False
    operator_note: str | None = None
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None


class AuthoredGraphGoldEvalExportAssertionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    assertion_kind: Literal["object", "link_existing", "relationship"]
    operation: str
    session_id: str | None = None
    source_anchor: GraphAuthoringSourceAnchor | None = None
    visibility: GraphVisibilityPolicy
    graph_scope: list[GraphScope]
    provenance: GraphAuthoringProvenance
    gold_eval_notes: str | None = None


class AuthoredGraphGoldEvalExportObjectAssertion(AuthoredGraphGoldEvalExportAssertionBase):
    assertion_kind: Literal["object"] = "object"
    object_ref: AuthoredGraphObjectRef
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None
    label: str
    kind: str | None = None


class AuthoredGraphGoldEvalExportLinkExistingAssertion(AuthoredGraphGoldEvalExportAssertionBase):
    assertion_kind: Literal["link_existing"] = "link_existing"
    selected_text: str
    normalized_selected_text: str
    existing_object_ref: AuthoredGraphObjectRef
    alias_text: str | None = None


class AuthoredGraphGoldEvalExportRelationshipAssertion(AuthoredGraphGoldEvalExportAssertionBase):
    assertion_kind: Literal["relationship"] = "relationship"
    source_object_ref: AuthoredGraphObjectRef
    target_object_ref: AuthoredGraphObjectRef
    relationship_type: str
    relationship_label: str | None = None
    direction: Literal["directed", "undirected"]
    summary: str | None = None


AuthoredGraphGoldEvalExportAssertion = Annotated[
    AuthoredGraphGoldEvalExportObjectAssertion
    | AuthoredGraphGoldEvalExportLinkExistingAssertion
    | AuthoredGraphGoldEvalExportRelationshipAssertion,
    Field(discriminator="assertion_kind"),
]


class AuthoredGraphGoldEvalExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb.authored_graph_gold_eval_export.v1"] = (
        AUTHORED_GRAPH_GOLD_EVAL_EXPORT_SCHEMA
    )
    version: Literal["0.1"] = AUTHORED_GRAPH_GOLD_EVAL_EXPORT_VERSION
    export_id: str
    campaign_id: str
    session_id: str | None = None
    created_at: str
    knowledge_scope: AuthoredGraphGoldKnowledgeScope
    source_overlay: AuthoredGraphGoldEvalExportSourceOverlay
    assertions: list[
        Annotated[
            AuthoredGraphGoldEvalExportObjectAssertion
            | AuthoredGraphGoldEvalExportLinkExistingAssertion
            | AuthoredGraphGoldEvalExportRelationshipAssertion,
            Field(discriminator="assertion_kind"),
        ]
    ] = Field(default_factory=list)
    diagnostics: AuthoredGraphGoldEvalExportDiagnostics = Field(
        default_factory=AuthoredGraphGoldEvalExportDiagnostics
    )


class AuthoredGraphGoldEvalExportWriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exported: bool
    export_path: str | None = None
    export: AuthoredGraphGoldEvalExport | None = None
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None


def gold_eval_eligible_assertions(
    overlay: AuthoredGraphOverlay,
) -> list[AuthoredGraphAssertion]:
    """Return active authored assertions explicitly flagged for gold/eval export."""
    return [
        assertion
        for assertion in overlay.assertions
        if assertion.status == "authored" and assertion.include_in_gold_eval
    ]


def _map_object_assertion(
    assertion: AuthoredGraphObjectAssertion,
) -> AuthoredGraphGoldEvalExportObjectAssertion:
    return AuthoredGraphGoldEvalExportObjectAssertion(
        assertion_id=assertion.assertion_id,
        operation=assertion.operation,
        session_id=assertion.session_id,
        source_anchor=assertion.source_anchor,
        visibility=assertion.visibility,
        graph_scope=list(assertion.graph_scope),
        provenance=assertion.provenance,
        gold_eval_notes=assertion.gold_eval_notes,
        object_ref=assertion.object_ref,
        aliases=list(assertion.aliases),
        summary=assertion.summary,
        label=assertion.object_ref.label,
        kind=assertion.object_ref.kind,
    )


def _map_link_existing_assertion(
    assertion: AuthoredGraphLinkExistingAssertion,
) -> AuthoredGraphGoldEvalExportLinkExistingAssertion:
    return AuthoredGraphGoldEvalExportLinkExistingAssertion(
        assertion_id=assertion.assertion_id,
        operation=assertion.operation,
        session_id=assertion.session_id,
        source_anchor=assertion.source_anchor,
        visibility=assertion.visibility,
        graph_scope=list(assertion.graph_scope),
        provenance=assertion.provenance,
        gold_eval_notes=assertion.gold_eval_notes,
        selected_text=assertion.selected_text,
        normalized_selected_text=assertion.normalized_selected_text,
        existing_object_ref=assertion.existing_object_ref,
        alias_text=assertion.alias_text,
    )


def _map_relationship_assertion(
    assertion: AuthoredGraphRelationshipAssertion,
) -> AuthoredGraphGoldEvalExportRelationshipAssertion:
    return AuthoredGraphGoldEvalExportRelationshipAssertion(
        assertion_id=assertion.assertion_id,
        operation=assertion.operation,
        session_id=assertion.session_id,
        source_anchor=assertion.source_anchor,
        visibility=assertion.visibility,
        graph_scope=list(assertion.graph_scope),
        provenance=assertion.provenance,
        gold_eval_notes=assertion.gold_eval_notes,
        source_object_ref=assertion.source_object_ref,
        target_object_ref=assertion.target_object_ref,
        relationship_type=assertion.relationship_type,
        relationship_label=assertion.relationship_label,
        direction=assertion.direction,
        summary=assertion.summary,
    )


def map_assertion_for_gold_eval_export(
    assertion: AuthoredGraphAssertion,
) -> AuthoredGraphGoldEvalExportAssertion:
    if assertion.assertion_kind == "object":
        return _map_object_assertion(assertion)
    if assertion.assertion_kind == "link_existing":
        return _map_link_existing_assertion(assertion)
    return _map_relationship_assertion(assertion)


def _overlay_token(overlay: AuthoredGraphOverlay) -> str:
    payload = overlay.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hash_text(canonical)


def _export_id(
    *,
    campaign_id: str,
    overlay_id: str,
    assertion_ids: list[str],
    created_at: str,
) -> str:
    digest_input = "|".join([campaign_id, overlay_id, *sorted(assertion_ids), created_at])
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:12]
    return f"authored-gold-eval-export-{digest}"


def _validate_export_options(options: AuthoredGraphGoldEvalExportOptions) -> None:
    validate_campaign_id(options.campaign_id)
    if options.campaign_rel is not None:
        validate_campaign_rel(options.campaign_rel)


def build_authored_graph_gold_eval_export(
    overlay: AuthoredGraphOverlay,
    *,
    options: AuthoredGraphGoldEvalExportOptions,
    overlay_path: str | None = None,
    overlay_token: str | None = None,
) -> AuthoredGraphGoldEvalExport | None:
    """Build an export artifact from flagged overlay assertions, or None if none qualify."""
    _validate_export_options(options)
    if overlay.campaign_id != validate_campaign_id(options.campaign_id):
        raise ValueError("overlay campaign_id must match export options campaign_id")

    eligible = gold_eval_eligible_assertions(overlay)
    if not eligible:
        return None

    created_at = options.created_at or isoformat_z()
    mapped_assertions = [map_assertion_for_gold_eval_export(item) for item in eligible]
    export_id = _export_id(
        campaign_id=overlay.campaign_id,
        overlay_id=overlay.overlay_id,
        assertion_ids=[item.assertion_id for item in eligible],
        created_at=created_at,
    )
    resolved_overlay_path = options.overlay_path or overlay_path
    resolved_overlay_token = overlay_token or _overlay_token(overlay)

    return AuthoredGraphGoldEvalExport(
        export_id=export_id,
        campaign_id=overlay.campaign_id,
        session_id=options.session_id,
        created_at=created_at,
        knowledge_scope=options.knowledge_scope,
        source_overlay=AuthoredGraphGoldEvalExportSourceOverlay(
            overlay_id=overlay.overlay_id,
            overlay_path=resolved_overlay_path,
            overlay_token=resolved_overlay_token,
            assertion_count=len(overlay.assertions),
            included_assertion_count=len(eligible),
        ),
        assertions=mapped_assertions,
        diagnostics=AuthoredGraphGoldEvalExportDiagnostics(
            operator_note=options.operator_note,
        ),
    )


def _filename_timestamp_from_created_at(created_at: str) -> str:
    """Derive a safe filename segment from an ISO-style created_at stamp."""
    if "/" in created_at or "\\" in created_at or ".." in created_at:
        raise ValueError("unsafe created_at for export filename")
    compact = created_at.replace(":", "").replace("-", "")
    sanitized = _UNSAFE_CREATED_AT_CHARS.sub("", compact)
    if not sanitized:
        raise ValueError("unsafe created_at for export filename")
    return sanitized


def _export_filename(export: AuthoredGraphGoldEvalExport) -> str:
    stamp = _filename_timestamp_from_created_at(export.created_at)
    digest = export.export_id.removeprefix("authored-gold-eval-export-")
    return f"{EXPORT_FILENAME_PREFIX}.{stamp}.{digest}.json"


def _resolve_exports_dir(
    *,
    campaign_id: str,
    campaign_rel: str | None,
    corpus_root: Path,
) -> Path:
    store = GraphAuthoringOverlayStore(corpus_root)
    return store.exports_dir(campaign_id, campaign_rel=campaign_rel)


def write_authored_graph_gold_eval_export(
    export: AuthoredGraphGoldEvalExport,
    *,
    campaign_id: str,
    campaign_rel: str | None = None,
    corpus_root: Path | None = None,
) -> Path:
    """Write export JSON under campaign `_graph_authoring/exports/`."""
    safe_campaign_id = validate_campaign_id(campaign_id)
    if export.campaign_id != safe_campaign_id:
        raise ValueError("export campaign_id must match write campaign_id")
    if campaign_rel is not None:
        validate_campaign_rel(campaign_rel)
    if corpus_root is None:
        raise ValueError("corpus_root is required to write authored graph gold eval export")

    exports_dir = _resolve_exports_dir(
        campaign_id=safe_campaign_id,
        campaign_rel=campaign_rel,
        corpus_root=corpus_root,
    )
    exports_dir.mkdir(parents=True, exist_ok=True)
    path = exports_dir / _export_filename(export)
    if path.exists():
        raise FileExistsError(f"authored graph gold/eval export already exists: {path}")
    write_json(path, export.model_dump(mode="json"))
    return path


def export_authored_graph_gold_eval(
    *,
    campaign_id: str,
    campaign_rel: str | None = None,
    session_id: str | None = None,
    knowledge_scope: AuthoredGraphGoldKnowledgeScope = "session_local",
    corpus_root: Path | None = None,
    created_at: str | None = None,
    operator_note: str | None = None,
) -> AuthoredGraphGoldEvalExportWriteResult:
    """Load overlay, build export, and write when flagged assertions exist."""
    try:
        _validate_export_options(
            AuthoredGraphGoldEvalExportOptions(
                campaign_id=campaign_id,
                campaign_rel=campaign_rel,
                session_id=session_id,
                knowledge_scope=knowledge_scope,
                created_at=created_at,
                operator_note=operator_note,
            )
        )
    except (UnsafeCampaignIdError, UnsafeCampaignRelError) as exc:
        raise exc

    if corpus_root is None:
        raise ValueError("corpus_root is required to export authored graph gold eval")

    store = GraphAuthoringOverlayStore(corpus_root)
    safe_campaign_id = validate_campaign_id(campaign_id)
    overlay = store.load_overlay(safe_campaign_id, campaign_rel=campaign_rel)
    overlay_path = str(store.overlay_path(safe_campaign_id, campaign_rel=campaign_rel))

    options = AuthoredGraphGoldEvalExportOptions(
        campaign_id=safe_campaign_id,
        campaign_rel=campaign_rel,
        session_id=session_id,
        knowledge_scope=knowledge_scope,
        overlay_path=overlay_path,
        created_at=created_at,
        operator_note=operator_note,
    )
    export = build_authored_graph_gold_eval_export(
        overlay,
        options=options,
        overlay_path=overlay_path,
    )
    if export is None:
        return AuthoredGraphGoldEvalExportWriteResult(
            exported=False,
            diagnostic_code="no_gold_eval_assertions",
            diagnostic_message="No authored assertions with include_in_gold_eval=true",
        )

    path = write_authored_graph_gold_eval_export(
        export,
        campaign_id=safe_campaign_id,
        campaign_rel=campaign_rel,
        corpus_root=corpus_root,
    )
    return AuthoredGraphGoldEvalExportWriteResult(
        exported=True,
        export_path=str(path),
        export=export,
    )
