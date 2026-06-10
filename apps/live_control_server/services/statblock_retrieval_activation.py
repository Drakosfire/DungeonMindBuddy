from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.services.statblock_draft_store import (
    StoredStatblockDraftRecord,
    read_statblock_draft,
    update_statblock_draft_record,
)
from apps.live_control_server.services.statblock_workbench import StatblockWorkbenchAction
from src.live_play.live_query_context import resolve_manifest_path
from src.live_play.live_store import load_json, write_json
from src.live_play.manifest_context_query import QueryConfig, QueryRequest, build_context_packet, load_manifest

OVERLAY_SCHEMA = "dmb_generated_statblock_manifest_overlay_v1"
OVERLAY_REL_PATH = "statblock_retrieval/generated_statblocks_manifest.json"
CORPUS_ROUTE_PREFIX = "corpus/eldyrwild-markdown"
DEFAULT_PLANNING_MANIFEST = "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"


class StatblockRetrievalActivationError(ValueError):
    status_code = 409


class RetrievalNotActivatedError(StatblockRetrievalActivationError):
    pass


class GeneratedStatblockManifestOverlay(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_: Literal["dmb_generated_statblock_manifest_overlay_v1"] = Field(
        default=OVERLAY_SCHEMA, alias="schema"
    )
    campaign_id: str
    session: int
    generated_at: str
    entries: list[dict[str, Any]] = Field(default_factory=list)


class StatblockRetrievalActivationResponse(BaseModel):
    schema_version: Literal["dmb_statblock_retrieval_activation_v1"] = "dmb_statblock_retrieval_activation_v1"
    artifact_id: str
    draft_id: str
    title: str
    corpus_relpath: str
    corpus_display_path: str
    manifest_overlay_path: str
    manifest_entry: dict[str, Any]
    stored_record: StoredStatblockDraftRecord
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)


class StatblockRetrievalVerifyRequest(BaseModel):
    query: str | None = None


class StatblockRetrievalVerifyResponse(BaseModel):
    schema_version: Literal["dmb_statblock_retrieval_verify_v1"] = "dmb_statblock_retrieval_verify_v1"
    artifact_id: str
    draft_id: str
    title: str
    query: str
    status: Literal["verified", "retrieved_not_admitted", "not_found"]
    corpus_relpath: str
    manifest_overlay_path: str
    admitted_evidence: list[dict[str, Any]] = Field(default_factory=list)
    rejected_evidence: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_trace: dict[str, Any] = Field(default_factory=dict)
    stored_record: StoredStatblockDraftRecord | None = None
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _overlay_path(base: Path) -> Path:
    return base / OVERLAY_REL_PATH


def _corpus_file(root: Path, corpus_relpath: str) -> Path:
    return root / CORPUS_ROUTE_PREFIX / corpus_relpath


def _route_for(corpus_relpath: str) -> str:
    return f"{CORPUS_ROUTE_PREFIX}/{corpus_relpath}"


def _actions(*, activated: bool, verified: bool = False) -> list[StatblockWorkbenchAction]:
    return [
        StatblockWorkbenchAction(
            action_id="activate_retrieval",
            label="Activate retrieval",
            enabled=not activated,
            disabled_reason=None if not activated else "Generated statblock manifest overlay is already activated.",
        ),
        StatblockWorkbenchAction(
            action_id="verify_retrieval",
            label="Verify retrieval",
            enabled=activated,
            disabled_reason=None if activated else "Activate retrieval before verification.",
        ),
        StatblockWorkbenchAction(
            action_id="open_statblock_view",
            label="Open in Statblock View",
            enabled=False,
            disabled_reason="Disabled until a future corpus-backed Statblock View PR.",
        ),
        StatblockWorkbenchAction(
            action_id="add_to_combat",
            label="Add to combat",
            enabled=False,
            disabled_reason="Disabled until corpus-backed combat integration exists.",
        ),
    ]


def _require_confirmed_record(record: StoredStatblockDraftRecord, *, root: Path) -> tuple[str, str]:
    if record.artifact.corpus_status != "promotion_confirmed":
        raise StatblockRetrievalActivationError("statblock draft corpus write is not confirmed")
    if not record.corpus_relpath or not record.corpus_display_path:
        raise StatblockRetrievalActivationError("statblock draft corpus path metadata is missing")
    if not _corpus_file(root, record.corpus_relpath).is_file():
        raise StatblockRetrievalActivationError("statblock draft corpus file is missing")
    return record.corpus_relpath, record.corpus_display_path


def _add_term(terms: list[str], seen: set[str], value: Any) -> None:
    text = str(value or "").strip()
    if not text:
        return
    key = text.casefold()
    if key in seen:
        return
    seen.add(key)
    terms.append(text)


def _lexical_terms(record: StoredStatblockDraftRecord) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    artifact = record.artifact
    structured = dict(artifact.structured_statblock or {})
    defaults = artifact.combat_defaults
    for value in (
        artifact.title,
        artifact.draft_id,
        artifact.artifact_id,
        structured.get("name"),
        structured.get("type"),
        structured.get("creature_type"),
        structured.get("challenge_rating"),
        structured.get("challenge"),
        defaults.armor_class,
        defaults.hit_points,
        defaults.passive_perception,
    ):
        _add_term(terms, seen, value)
    for value in getattr(defaults, "primary_actions", None) or []:
        _add_term(terms, seen, value)
    for value in getattr(defaults, "suggested_tactics", None) or []:
        _add_term(terms, seen, value)
    for ref in artifact.source_refs:
        data = ref.model_dump(mode="json") if hasattr(ref, "model_dump") else dict(ref)
        _add_term(terms, seen, data.get("label") or data.get("source") or data.get("reason"))
    for value in (
        "statblock",
        "generated statblock",
        "armor class",
        "AC",
        "hit points",
        "HP",
        "challenge rating",
        "CR",
        "primary actions",
        "suggested tactics",
        "passive perception",
    ):
        _add_term(terms, seen, value)
    return terms


def _build_manifest_entry(record: StoredStatblockDraftRecord, *, root: Path) -> dict[str, Any]:
    corpus_relpath, _ = _require_confirmed_record(record, root=root)
    return {
        "source_id": f"generated_statblock-{record.artifact_id}",
        "source_role": "world_evidence",
        "authority": "canon_play",
        "session_scope": [record.session],
        "route": _route_for(corpus_relpath),
        "route_exists": True,
        "admissible": True,
        "allowed_uses": ["planning_context", "statblock_lookup", "mechanical_reference"],
        "forbidden_uses": ["play_facts"],
        "lexical_terms": _lexical_terms(record),
        "notes": ["Generated statblock promoted through DungeonBuddy Workbench and confirmed into corpus."],
    }


def _load_overlay(path: Path, *, campaign_id: str, session: int) -> GeneratedStatblockManifestOverlay:
    if not path.is_file():
        return GeneratedStatblockManifestOverlay(campaign_id=campaign_id, session=session, generated_at=_utc_now())
    return GeneratedStatblockManifestOverlay.model_validate(load_json(path))


def _upsert(entries: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    source_id = str(entry.get("source_id") or "")
    route = str(entry.get("route") or "")
    retained = [e for e in entries if str(e.get("source_id") or "") != source_id and str(e.get("route") or "") != route]
    retained.append(entry)
    retained.sort(key=lambda e: (str(e.get("route") or ""), str(e.get("source_id") or "")))
    return retained


def merge_generated_statblock_overlay(base_manifest: dict[str, Any], overlay: GeneratedStatblockManifestOverlay) -> dict[str, Any]:
    merged = copy.deepcopy(base_manifest)
    entries = [e for e in list(merged.get("entries") or []) if isinstance(e, dict)]
    for overlay_entry in overlay.entries:
        entries = _upsert(entries, dict(overlay_entry))
    merged["entries"] = entries
    merged["generated_statblock_overlay"] = {"path": OVERLAY_REL_PATH, "entry_count": len(overlay.entries)}
    return merged


def activate_statblock_retrieval(*, base: Path, root: Path, packet: dict[str, Any], artifact_id: str) -> StatblockRetrievalActivationResponse:
    record = read_statblock_draft(base=base, artifact_id=artifact_id)
    corpus_relpath, corpus_display_path = _require_confirmed_record(record, root=root)
    entry = _build_manifest_entry(record, root=root)
    path = _overlay_path(base)
    overlay = _load_overlay(path, campaign_id=str(packet.get("campaign_id") or record.campaign_id), session=int(packet.get("session") or record.session))
    overlay.generated_at = _utc_now()
    overlay.entries = _upsert(overlay.entries, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, overlay.model_dump(mode="json", by_alias=True))

    timestamp = _utc_now()
    updated = record.model_copy(update={
        "updated_at": timestamp,
        "retrieval_status": "manifest_activated",
        "retrieval_manifest_path": OVERLAY_REL_PATH,
        "retrieval_activated_at": timestamp,
    })
    update_statblock_draft_record(base=base, record=updated)
    return StatblockRetrievalActivationResponse(
        artifact_id=record.artifact_id,
        draft_id=record.artifact.draft_id,
        title=record.title,
        corpus_relpath=corpus_relpath,
        corpus_display_path=corpus_display_path,
        manifest_overlay_path=OVERLAY_REL_PATH,
        manifest_entry=entry,
        stored_record=updated,
        diagnostics=["generated-statblock manifest overlay updated", "no corpus, base manifest, event, job, or combat mutation occurred"],
        available_actions=_actions(activated=True),
    )


def _load_base_manifest(*, packet: dict[str, Any], root: Path, diagnostics: list[str]) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(request_manifest_path=None, packet=packet, root=root)
    if manifest_path is None:
        fallback = root / DEFAULT_PLANNING_MANIFEST
        manifest_path = fallback if fallback.is_file() else None
    if manifest_path is None:
        diagnostics.append("no active planning manifest found; verifying generated overlay against an empty manifest")
        return {"schema": "dmb_empty_manifest_for_generated_statblock_verification_v1", "entries": []}
    diagnostics.append(f"merged generated statblock overlay with {manifest_path.relative_to(root).as_posix()}")
    return load_manifest(manifest_path)


def _matches_route(evidence: dict[str, Any], route: str, corpus_relpath: str) -> bool:
    values = [str(evidence.get("path") or "")]
    values.extend(str(v) for v in list(evidence.get("routes") or []))
    return any(v == route or v.endswith(corpus_relpath) or corpus_relpath in v for v in values)


def _default_query(record: StoredStatblockDraftRecord) -> str:
    return f'What are the statblock details for "{record.title}"? Include armor class, hit points, challenge rating, and primary actions.'


def verify_statblock_retrieval(*, base: Path, root: Path, packet: dict[str, Any], artifact_id: str, query: str | None = None) -> StatblockRetrievalVerifyResponse:
    record = read_statblock_draft(base=base, artifact_id=artifact_id)
    corpus_relpath, _ = _require_confirmed_record(record, root=root)
    overlay_path = _overlay_path(base)
    if not overlay_path.is_file():
        raise RetrievalNotActivatedError("statblock retrieval is not activated")
    overlay = GeneratedStatblockManifestOverlay.model_validate(load_json(overlay_path))
    route = _route_for(corpus_relpath)
    if not any(str(e.get("route") or "") == route for e in overlay.entries):
        raise RetrievalNotActivatedError("statblock retrieval overlay entry is missing")

    diagnostics: list[str] = []
    base_manifest = _load_base_manifest(packet=packet, root=root, diagnostics=diagnostics)
    merged_manifest = merge_generated_statblock_overlay(base_manifest, overlay)
    question = (query or "").strip() or _default_query(record)
    packet_out = build_context_packet(
        QueryRequest(question_id=f"statblock-retrieval-{artifact_id}", question=question),
        merged_manifest,
        root=root,
        config=QueryConfig(max_retrieved_evidence=30, max_admitted_evidence=12, max_rejected_evidence=12),
    )
    admitted = [e for e in list(packet_out.get("admitted_evidence") or []) if isinstance(e, dict)]
    rejected = [e for e in list(packet_out.get("rejected_evidence") or []) if isinstance(e, dict)]
    retrieved = [e for e in list(packet_out.get("retrieved_evidence") or []) if isinstance(e, dict)]
    matched = next((e for e in admitted if _matches_route(e, route, corpus_relpath)), None)
    status: Literal["verified", "retrieved_not_admitted", "not_found"] = "verified" if matched else "not_found"
    if matched is None and any(_matches_route(e, route, corpus_relpath) for e in retrieved):
        status = "retrieved_not_admitted"

    timestamp = _utc_now()
    updated_record: StoredStatblockDraftRecord | None = None
    if status == "verified":
        updated_record = record.model_copy(update={
            "updated_at": timestamp,
            "retrieval_status": "retrieval_verified",
            "retrieval_verified_at": timestamp,
            "retrieval_query": question,
            "retrieval_evidence_path": str(matched.get("path") or route),
            "retrieval_evidence_score": float(matched.get("evidence_score") or 0.0),
        })
        update_statblock_draft_record(base=base, record=updated_record)
    else:
        updated_record = record.model_copy(update={"updated_at": timestamp, "retrieval_status": "verification_failed", "retrieval_query": question})
        update_statblock_draft_record(base=base, record=updated_record)

    return StatblockRetrievalVerifyResponse(
        artifact_id=record.artifact_id,
        draft_id=record.artifact.draft_id,
        title=record.title,
        query=question,
        status=status,
        corpus_relpath=corpus_relpath,
        manifest_overlay_path=OVERLAY_REL_PATH,
        admitted_evidence=admitted,
        rejected_evidence=rejected,
        retrieval_trace=dict(packet_out.get("retrieval_trace") or {}),
        stored_record=updated_record,
        diagnostics=diagnostics + [f"retrieval verification status: {status}"],
        available_actions=_actions(activated=True, verified=status == "verified"),
    )
