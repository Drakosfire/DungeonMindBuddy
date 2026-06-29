"""Read-only gold-vs-live graph review for Plan toolbar developer tooling."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestRunRegistryError,
    GraphIngestRunSummary,
    discover_graph_ingest_runs,
    resolve_latest_preview_union_graph_ingest_run,
)
from evals.graph_memory_layer.live_vs_gold_compare import (
    compare_parts,
    parts_from_raw_graph,
)
from evals.graph_memory_layer.session_22_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID as S22_GOLD_FIXTURE_ID,
    load_gold_candidate_graph_dict as load_s22_gold_graph_dict,
    load_gold_manifest as load_s22_gold_manifest,
)
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID as S23_GOLD_FIXTURE_ID,
    load_gold_candidate_graph_dict as load_s23_gold_graph_dict,
    load_gold_manifest as load_s23_gold_manifest,
)
from graph_memory import identity_resolution as ir
from graph_memory.ingestion.graph_ingest_run import GraphIngestRunManifest
from src.graph_memory.source_span import ResolvedEvidence, resolve_many_source_span_refs

COMPARISON_SCHEMA = "dmb_graph_gold_review_compare_v1"
COMPARISON_VERSION = "0.1"
SESSIONS_SCHEMA = "dmb_graph_gold_review_sessions_v1"
EVIDENCE_SCHEMA = "dmb_graph_gold_review_evidence_v1"

_OBJECT_KINDS = (
    "nodes",
    "edges",
    "beats",
    "proposed_writes",
    "ignored_items",
    "deferred_items",
)
_KIND_TO_ID_ATTR = {
    "nodes": "node_id",
    "edges": "edge_id",
    "beats": "beat_id",
    "proposed_writes": "write_id",
    "ignored_items": "item_id",
    "deferred_items": "item_id",
}
_KIND_TO_LABEL_ATTR = {
    "nodes": "label",
    "edges": "label",
    "beats": "title",
    "proposed_writes": "label",
    "ignored_items": "label",
    "deferred_items": "label",
}
_SCORE_CONFIG: dict[str, tuple[float, str | None]] = {
    "nodes": (0.6, "node"),
    "edges": (0.6, "edge"),
    "beats": (0.45, "beat"),
    "proposed_writes": (0.5, "write"),
    "ignored_items": (0.5, "label"),
    "deferred_items": (0.5, "label"),
}

_GOLD_SESSIONS: tuple[dict[str, Any], ...] = (
    {
        "session_id": "session-22",
        "session_number": 22,
        "campaign_id": "longmont-c2",
        "gold_fixture_id": S22_GOLD_FIXTURE_ID,
        "load_gold_manifest": load_s22_gold_manifest,
        "load_gold_graph_dict": load_s22_gold_graph_dict,
    },
    {
        "session_id": "session-23",
        "session_number": 23,
        "campaign_id": "longmont-c2",
        "gold_fixture_id": S23_GOLD_FIXTURE_ID,
        "load_gold_manifest": load_s23_gold_manifest,
        "load_gold_graph_dict": load_s23_gold_graph_dict,
    },
)


class GraphGoldReviewError(ValueError):
    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class GoldReviewSessionSummary(BaseModel):
    session_id: str
    session_number: int
    campaign_id: str
    gold_fixture_id: str
    gold_manifest_path: str
    gold_graph_path: str
    gold_counts: dict[str, int] = Field(default_factory=dict)
    available_runs: list[GraphIngestRunSummary] = Field(default_factory=list)


class GoldReviewSessionsResponse(BaseModel):
    schema_version: Literal["dmb_graph_gold_review_sessions_v1"] = SESSIONS_SCHEMA
    version: str = COMPARISON_VERSION
    sessions: list[GoldReviewSessionSummary] = Field(default_factory=list)


class GoldReviewCompareResponse(BaseModel):
    schema_version: Literal["dmb_graph_gold_review_compare_v1"] = COMPARISON_SCHEMA
    version: str = COMPARISON_VERSION
    session_id: str
    campaign_id: str
    gold_fixture_id: str
    gold_manifest_path: str
    gold_graph_path: str
    live_run: GraphIngestRunSummary | None = None
    comparison: dict[str, Any] = Field(default_factory=dict)
    object_index: dict[str, dict[str, Any]] = Field(default_factory=dict)
    match_pairs: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class GoldReviewEvidenceResolvedRef(BaseModel):
    source_anchor_id: str | None = None
    source_span_ref_id: str | None = None
    label: str | None = None
    preview_snippet: str | None = None
    paragraph_text: str | None = None
    line_start: int | None = None
    line_end: int | None = None


class GoldReviewEvidenceSide(BaseModel):
    object_id: str
    object_kind: str
    label: str | None = None
    summary: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[GoldReviewEvidenceResolvedRef] = Field(default_factory=list)


class GoldReviewEvidenceDiffResponse(BaseModel):
    schema_version: Literal["dmb_graph_gold_review_evidence_v1"] = EVIDENCE_SCHEMA
    version: str = COMPARISON_VERSION
    session_id: str
    campaign_id: str
    object_kind: str
    object_id: str
    matched: bool = False
    match_score: float | None = None
    gold: GoldReviewEvidenceSide
    live: GoldReviewEvidenceSide | None = None


def discover_gold_review_sessions(root: Path | None = None) -> list[GoldReviewSessionSummary]:
    repo = (root or repo_root()).resolve()
    summaries: list[GoldReviewSessionSummary] = []
    for entry in _GOLD_SESSIONS:
        manifest = entry["load_gold_manifest"]()
        gold_graph_path = str(manifest["candidate_graph_gold_path"])
        gold_manifest_path = _gold_manifest_rel_path(entry["session_number"])
        gold_parts = parts_from_raw_graph(entry["load_gold_graph_dict"]())
        runs = discover_graph_ingest_runs(
            repo,
            campaign_id=entry["campaign_id"],
            session_id=entry["session_id"],
            require_preview_union_store=True,
        )
        summaries.append(
            GoldReviewSessionSummary(
                session_id=entry["session_id"],
                session_number=entry["session_number"],
                campaign_id=entry["campaign_id"],
                gold_fixture_id=entry["gold_fixture_id"],
                gold_manifest_path=gold_manifest_path,
                gold_graph_path=gold_graph_path,
                gold_counts={kind: len(gold_parts.get(kind, [])) for kind in _OBJECT_KINDS},
                available_runs=runs,
            )
        )
    return summaries


def compare_gold_review(
    *,
    campaign_id: str,
    session_id: str,
    manifest_path: str | None = None,
    root: Path | None = None,
) -> GoldReviewCompareResponse:
    repo = (root or repo_root()).resolve()
    entry = _session_entry(session_id)
    if entry["campaign_id"] != campaign_id:
        raise GraphGoldReviewError(
            f"session {session_id} belongs to {entry['campaign_id']}, not {campaign_id}",
            status_code=422,
        )

    gold_manifest = entry["load_gold_manifest"]()
    gold_graph = entry["load_gold_graph_dict"]()
    gold_parts = parts_from_raw_graph(gold_graph)

    live_run: GraphIngestRunSummary | None = None
    live_parts: dict[str, list[Any]] = {kind: [] for kind in _OBJECT_KINDS}
    if manifest_path:
        live_run = _resolve_run_summary(repo, manifest_path)
        live_graph = load_live_candidate_graph_dict(repo, manifest_path)
        live_parts = parts_from_raw_graph(live_graph)
    else:
        try:
            live_run = resolve_latest_preview_union_graph_ingest_run(
                repo,
                campaign_id=campaign_id,
                session_id=session_id,
            )
            live_graph = load_live_candidate_graph_dict(repo, live_run.manifest_path)
            live_parts = parts_from_raw_graph(live_graph)
        except GraphIngestRunRegistryError:
            live_run = None

    comparison = compare_parts(
        live_parts,
        gold_parts,
        gold_fixture_id=entry["gold_fixture_id"],
        report_id=f"graph-memory:live-vs-gold-comparison:{session_id}:v0",
    )
    match_pairs = _build_match_pairs(gold_parts, live_parts)
    object_index = _build_object_index(gold_parts, live_parts)

    return GoldReviewCompareResponse(
        session_id=session_id,
        campaign_id=campaign_id,
        gold_fixture_id=entry["gold_fixture_id"],
        gold_manifest_path=_gold_manifest_rel_path(entry["session_number"]),
        gold_graph_path=str(gold_manifest["candidate_graph_gold_path"]),
        live_run=live_run,
        comparison=comparison,
        object_index=object_index,
        match_pairs=match_pairs,
    )


def build_gold_review_evidence_diff(
    *,
    campaign_id: str,
    session_id: str,
    object_kind: str,
    object_id: str,
    manifest_path: str | None = None,
    root: Path | None = None,
) -> GoldReviewEvidenceDiffResponse:
    if object_kind not in _OBJECT_KINDS:
        raise GraphGoldReviewError(f"unsupported object_kind: {object_kind}", status_code=422)

    repo = (root or repo_root()).resolve()
    entry = _session_entry(session_id)
    if entry["campaign_id"] != campaign_id:
        raise GraphGoldReviewError(
            f"session {session_id} belongs to {entry['campaign_id']}, not {campaign_id}",
            status_code=422,
        )

    gold_parts = parts_from_raw_graph(entry["load_gold_graph_dict"]())
    gold_obj = _find_object_in_parts(gold_parts, object_kind, object_id)
    if gold_obj is None:
        raise GraphGoldReviewError(f"unknown gold object: {object_id}", status_code=404)

    live_parts = {kind: [] for kind in _OBJECT_KINDS}
    if manifest_path:
        live_graph = load_live_candidate_graph_dict(repo, manifest_path)
        live_parts = parts_from_raw_graph(live_graph)
    else:
        try:
            live_run = resolve_latest_preview_union_graph_ingest_run(
                repo,
                campaign_id=campaign_id,
                session_id=session_id,
            )
            live_graph = load_live_candidate_graph_dict(repo, live_run.manifest_path)
            live_parts = parts_from_raw_graph(live_graph)
        except GraphIngestRunRegistryError:
            live_parts = {kind: [] for kind in _OBJECT_KINDS}

    match_pairs = _build_match_pairs(gold_parts, live_parts)
    live_obj: dict[str, Any] | None = None
    matched = False
    match_score: float | None = None
    for pair in match_pairs.get(object_kind, []):
        if pair["gold_id"] == object_id:
            matched = True
            match_score = pair.get("score")
            live_obj = _find_object_in_parts(live_parts, object_kind, pair["live_id"])
            break

    if live_obj is None:
        live_obj, match_score = _best_live_match(gold_parts, live_parts, object_kind, gold_obj)

    gold_side = _evidence_side(entry["session_number"], object_kind, object_id, gold_obj)
    live_side = None
    if live_obj is not None:
        live_id = str(live_obj.get(_KIND_TO_ID_ATTR[object_kind], ""))
        live_side = _evidence_side(entry["session_number"], object_kind, live_id, live_obj)

    return GoldReviewEvidenceDiffResponse(
        session_id=session_id,
        campaign_id=campaign_id,
        object_kind=object_kind,
        object_id=object_id,
        matched=matched,
        match_score=match_score,
        gold=gold_side,
        live=live_side,
    )


def load_live_candidate_graph_dict(repo: Path, manifest_path: str) -> dict[str, Any]:
    safe_manifest = _resolve_repo_path(repo, manifest_path)
    payload = json.loads(safe_manifest.read_text(encoding="utf-8"))
    GraphIngestRunManifest.model_validate(payload)
    run_dir = safe_manifest.parent

    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    candidate_ref = artifacts.get("candidate_graph")
    if isinstance(candidate_ref, dict) and candidate_ref.get("uri"):
        raw = json.loads(_resolve_repo_path(repo, candidate_ref["uri"]).read_text(encoding="utf-8"))
        return dict(raw.get("candidate_graph") or raw)

    validation_path = run_dir / "candidate_validation_report.json"
    if validation_path.is_file():
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        reconciled = validation.get("reconciled_candidate_graph")
        if isinstance(reconciled, dict):
            return dict(reconciled)

    import_path = run_dir / "candidate_graph_import_input.json"
    if import_path.is_file():
        return json.loads(import_path.read_text(encoding="utf-8"))

    raise GraphGoldReviewError(
        f"no candidate graph artifact for manifest: {manifest_path}",
        status_code=404,
    )


def _session_entry(session_id: str) -> dict[str, Any]:
    for entry in _GOLD_SESSIONS:
        if entry["session_id"] == session_id:
            return entry
    raise GraphGoldReviewError(f"no gold fixture for session: {session_id}", status_code=404)


def _gold_manifest_rel_path(session_number: int) -> str:
    return (
        f"evals/graph_memory_layer/examples/session_{session_number}_candidate_graph_gold/"
        f"session_{session_number}_candidate_graph_gold_manifest.json"
    )


def _resolve_run_summary(repo: Path, manifest_path: str) -> GraphIngestRunSummary:
    runs = discover_graph_ingest_runs(repo, require_preview_union_store=True)
    for run in runs:
        if run.manifest_path == manifest_path:
            return run
    raise GraphGoldReviewError(f"unknown graph-ingest manifest: {manifest_path}", status_code=404)


def _resolve_repo_path(repo: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise GraphGoldReviewError(f"unsafe path: {value}", status_code=422) from exc
    if not resolved.exists():
        raise GraphGoldReviewError(f"path does not exist: {value}", status_code=404)
    return resolved


def _build_object_index(
    gold_parts: dict[str, list[Any]],
    live_parts: dict[str, list[Any]],
) -> dict[str, dict[str, Any]]:
    return {
        "gold": _index_parts(gold_parts),
        "live": _index_parts(live_parts),
    }


def _index_parts(parts: dict[str, list[Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for kind in _OBJECT_KINDS:
        id_attr = _KIND_TO_ID_ATTR[kind]
        for obj in parts.get(kind, []):
            if isinstance(obj, dict):
                obj_id = str(obj.get(id_attr) or "")
                if obj_id:
                    index[f"{kind}:{obj_id}"] = {
                        "object_kind": kind,
                        "object_id": obj_id,
                        "label": _object_label(kind, obj),
                        "payload": obj,
                    }
    return index


def _object_label(kind: str, obj: dict[str, Any]) -> str:
    label_attr = _KIND_TO_LABEL_ATTR[kind]
    base = str(obj.get(label_attr) or obj.get("label") or obj.get("title") or "")
    if kind == "edges":
        rel = str(obj.get("relationship_type") or obj.get("predicate") or "")
        from_id = str(obj.get("from_node_id") or obj.get("source_node_id") or "")
        to_id = str(obj.get("to_node_id") or obj.get("target_node_id") or "")
        if rel or from_id or to_id:
            return f"{from_id} → {rel or '?'} → {to_id}" if base == "" else base
    return base


def _find_object(
    index: dict[str, dict[str, Any]],
    object_kind: str,
    object_id: str,
) -> dict[str, Any] | None:
    hit = index.get(f"{object_kind}:{object_id}")
    if hit is None:
        return None
    return dict(hit.get("payload") or {})


def _build_match_pairs(
    gold_parts: dict[str, list[Any]],
    live_parts: dict[str, list[Any]],
) -> dict[str, list[dict[str, Any]]]:
    gold_nidx = ir.node_index(list(gold_parts.get("nodes", [])))
    cand_nidx = ir.node_index(list(live_parts.get("nodes", [])))
    out: dict[str, list[dict[str, Any]]] = {}

    for kind in _OBJECT_KINDS:
        id_attr = _KIND_TO_ID_ATTR[kind]
        label_attr = _KIND_TO_LABEL_ATTR[kind]
        threshold, score_kind = _SCORE_CONFIG[kind]
        gold_objs = list(gold_parts.get(kind, []))
        live_objs = list(live_parts.get(kind, []))
        if score_kind == "node":
            score_fn = ir.node_match_score
        elif score_kind == "edge":
            score_fn = lambda g, c: ir.edge_match_score(g, c, gold_nidx, cand_nidx)
        elif score_kind == "beat":
            score_fn = lambda g, c: ir.beat_match_score(g, c, gold_nidx, cand_nidx)
        elif score_kind == "write":

            def write_score(g: Any, c: Any) -> float:
                lab = ir.label_similarity(
                    str(ir._get(g, "label", "")),
                    str(ir._get(c, "label", "")),
                )
                type_ok = str(ir._get(g, "write_type", "")) == str(
                    ir._get(c, "write_type", "")
                )
                return round(0.7 * lab + (0.3 if type_ok else 0.0), 4)

            score_fn = write_score
        elif score_kind == "label":

            def label_score(g: Any, c: Any) -> float:
                return ir.label_similarity(
                    str(ir._get(g, label_attr, "")),
                    str(ir._get(c, label_attr, "")),
                )

            score_fn = label_score
        else:
            continue

        pairs = ir.best_match_assignment(
            gold_objs, live_objs, score_fn, threshold=threshold
        )
        out[kind] = [
            {
                "gold_id": str(ir._get(gold_objs[gi], id_attr, "")),
                "live_id": str(ir._get(live_objs[ci], id_attr, "")),
                "score": score,
            }
            for gi, ci, score in pairs
        ]
    return out


def _find_object_in_parts(
    parts: dict[str, list[Any]],
    object_kind: str,
    object_id: str,
) -> dict[str, Any] | None:
    id_attr = _KIND_TO_ID_ATTR[object_kind]
    for obj in parts.get(object_kind, []):
        if isinstance(obj, dict) and str(obj.get(id_attr) or "") == object_id:
            return dict(obj)
    return None


def _best_live_match(
    gold_parts: dict[str, list[Any]],
    live_parts: dict[str, list[Any]],
    object_kind: str,
    gold_obj: dict[str, Any],
) -> tuple[dict[str, Any] | None, float | None]:
    threshold, score_kind = _SCORE_CONFIG[object_kind]
    gold_nidx = ir.node_index(list(gold_parts.get("nodes", [])))
    cand_nidx = ir.node_index(list(live_parts.get("nodes", [])))
    live_objs = list(live_parts.get(object_kind, []))
    if not live_objs:
        return None, None

    label_attr = _KIND_TO_LABEL_ATTR[object_kind]
    if score_kind == "node":
        score_fn = ir.node_match_score
    elif score_kind == "edge":
        score_fn = lambda g, c: ir.edge_match_score(g, c, gold_nidx, cand_nidx)
    elif score_kind == "beat":
        score_fn = lambda g, c: ir.beat_match_score(g, c, gold_nidx, cand_nidx)
    elif score_kind == "write":

        def write_score(g: Any, c: Any) -> float:
            lab = ir.label_similarity(str(ir._get(g, "label", "")), str(ir._get(c, "label", "")))
            type_ok = str(ir._get(g, "write_type", "")) == str(ir._get(c, "write_type", ""))
            return round(0.7 * lab + (0.3 if type_ok else 0.0), 4)

        score_fn = write_score
    elif score_kind == "label":

        def label_score(g: Any, c: Any) -> float:
            return ir.label_similarity(
                str(ir._get(g, label_attr, "")),
                str(ir._get(c, label_attr, "")),
            )

        score_fn = label_score
    else:
        return None, None

    best_score: float | None = None
    best_obj: dict[str, Any] | None = None
    for candidate in live_objs:
        if not isinstance(candidate, dict):
            continue
        score = score_fn(gold_obj, candidate)
        if score >= threshold and (best_score is None or score > best_score):
            best_score = score
            best_obj = dict(candidate)
    return best_obj, best_score


def _evidence_side(
    session_number: int,
    object_kind: str,
    object_id: str,
    payload: dict[str, Any],
) -> GoldReviewEvidenceSide:
    refs = payload.get("evidence_refs") or []
    resolved = _resolve_evidence_refs(session_number, refs)
    summary = None
    if object_kind == "beats":
        summary = str(payload.get("summary") or "")
    return GoldReviewEvidenceSide(
        object_id=object_id,
        object_kind=object_kind,
        label=_object_label(object_kind, payload),
        summary=summary,
        payload=payload,
        evidence=resolved,
    )


def _resolve_evidence_refs(
    session_number: int,
    refs: list[Any],
) -> list[GoldReviewEvidenceResolvedRef]:
    anchor_lookup = _resolved_anchor_lookup(session_number)
    out: list[GoldReviewEvidenceResolvedRef] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        anchor_id = ref.get("source_anchor_id")
        span_ref_id = ref.get("source_span_ref_id")
        resolved = anchor_lookup.get(str(anchor_id or ""))
        out.append(
            GoldReviewEvidenceResolvedRef(
                source_anchor_id=str(anchor_id) if anchor_id else None,
                source_span_ref_id=str(span_ref_id) if span_ref_id else None,
                label=str(ref.get("label") or resolved.get("label") if resolved else "") or None,
                preview_snippet=resolved.get("preview_snippet") if resolved else None,
                paragraph_text=resolved.get("paragraph_text") if resolved else None,
                line_start=resolved.get("line_start") if resolved else None,
                line_end=resolved.get("line_end") if resolved else None,
            )
        )
    return out


def _resolved_anchor_lookup(session_number: int) -> dict[str, dict[str, Any]]:
    resolved_items = _resolve_session_seed_refs(session_number)
    lookup: dict[str, dict[str, Any]] = {}
    for item in resolved_items:
        lookup[item["source_anchor_id"]] = item
    return lookup


def _resolve_session_seed_refs(session_number: int) -> list[dict[str, Any]]:
    if session_number == 22:
        from evals.graph_memory_layer.session_22_recap_ingest_fixture import (
            build_source_span_artifacts as build_s22_artifacts,
            parse_source_span_seed_refs as parse_s22_seed_refs,
        )

        text, structured = build_s22_artifacts()
        refs = parse_s22_seed_refs()
    elif session_number == 23:
        from evals.graph_memory_layer.session_23_recap_ingest_fixture import (
            build_source_span_artifacts as build_s23_artifacts,
            parse_source_span_seed_refs as parse_s23_seed_refs,
        )

        text, structured = build_s23_artifacts()
        refs = parse_s23_seed_refs()
    else:
        return []

    resolved: tuple[ResolvedEvidence, ...] = resolve_many_source_span_refs(
        refs,
        text_artifacts=text,
        structured_artifacts=structured,
        snippet_max_chars=480,
        context_lines=0,
    )
    items: list[dict[str, Any]] = []
    for item in resolved:
        row = asdict(item)
        row["paragraph_text"] = row.get("paragraph_text") or row.get("preview_snippet")
        items.append(row)
    return items
