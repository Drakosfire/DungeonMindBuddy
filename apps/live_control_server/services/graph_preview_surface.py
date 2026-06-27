"""Read-only graph preview surface adapter for /plan toolbox projection."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from src.graph_memory.anchor_quotes import (
    anchor_quote_matches_to_dicts,
    coerce_anchor_quotes,
    find_anchor_quote_matches,
    quote_found_in_paragraph,
)

GRAPH_PREVIEW_SURFACE_SCHEMA = "dmb_graph_preview_surface_v1"
GRAPH_PREVIEW_SURFACE_VERSION = "0.1"

GRAPH_PREVIEW_ARTIFACTS_ENV = "DUNGEONMIND_GRAPH_PREVIEW_ARTIFACTS_ROOT"
DEFAULT_ARTIFACTS_REL = "evals/graph_memory_layer/artifacts/category_graph_model_study"
LAST_COHORT_MIRROR_REL = "evals/artifacts/category_graph_model_study/last_cohort_summary.json"

CandidateSection = Literal["nodes", "edges", "beats", "ignored_items", "deferred_items"]

SECTION_ID_KEYS: dict[str, tuple[str, ...]] = {
    "nodes": ("node_id",),
    "edges": ("edge_id",),
    "beats": ("beat_id",),
    "ignored_items": ("item_id",),
    "deferred_items": ("item_id",),
}


class GraphPreviewSurfaceError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class AnchorQuoteMatchRow(BaseModel):
    quote: str
    char_start: int
    char_end: int
    match_text: str


class GraphPreviewEvidenceRef(BaseModel):
    source_ref_id: str | None = None
    source_artifact_id: str | None = None
    source_span_ref_id: str | None = None
    source_anchor_id: str | None = None
    label: str | None = None
    evidence_role: str | None = None
    can_open_source: bool = False
    can_highlight_span: bool = False
    anchor_quotes: list[str] = Field(default_factory=list)
    anchor_quote_matches: list[AnchorQuoteMatchRow] = Field(default_factory=list)
    paragraph_text: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    recap_source_path: str | None = None


class GraphPreviewCandidateRow(BaseModel):
    section: CandidateSection
    object_id: str
    label: str
    kind: str
    description: str | None = None
    importance: str | None = None
    evidence_count: int = 0
    evidence_refs: list[GraphPreviewEvidenceRef] = Field(default_factory=list)


class GraphPreviewHealth(BaseModel):
    canonical_ir_valid: bool = False
    reconcile_error: str | None = None
    node_count: int = 0
    edge_count: int = 0
    beat_count: int = 0
    ignored_count: int = 0
    deferred_count: int = 0
    evidence_ref_count: int = 0
    resolvable_evidence_ref_count: int = 0
    model_id: str | None = None
    scenario_estimated_cost_usd: float | None = None
    node_recall: float | None = None


class GraphPreviewRunSummary(BaseModel):
    run_dir: str
    model_id: str | None = None
    run_index: int | None = None
    canonical_ir_valid: bool | None = None
    scenario_estimated_cost_usd: float | None = None


class GraphPreviewSurfaceResponse(BaseModel):
    schema_version: Literal["dmb_graph_preview_surface_v1"] = GRAPH_PREVIEW_SURFACE_SCHEMA
    version: str = GRAPH_PREVIEW_SURFACE_VERSION
    run_dir: str
    run_bundle_dir: str | None = None
    recap_source_path: str | None = None
    health: GraphPreviewHealth
    candidates: list[GraphPreviewCandidateRow] = Field(default_factory=list)


class GraphPreviewRunsResponse(BaseModel):
    schema_version: Literal["dmb_graph_preview_surface_v1"] = GRAPH_PREVIEW_SURFACE_SCHEMA
    version: str = GRAPH_PREVIEW_SURFACE_VERSION
    runs: list[GraphPreviewRunSummary] = Field(default_factory=list)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def artifacts_root(root: Path) -> Path:
    override = os.environ.get(GRAPH_PREVIEW_ARTIFACTS_ENV, "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate
    return root / DEFAULT_ARTIFACTS_REL


def _paragraph_text_for_span(recap_text: str, span: Mapping[str, Any]) -> str:
    lines = recap_text.splitlines()
    start = int(span["line_start"])
    end = int(span["line_end"])
    return "\n".join(lines[start - 1 : end])


def _recap_text_for_run_bundle(root: Path, run_bundle: Path) -> tuple[str, str]:
    base = run_bundle if run_bundle.is_absolute() else root / run_bundle
    manifest = _load_json(base / "run_manifest.json")
    input_rel = str(manifest["source"]["input_path_record"])
    recap_path = Path(input_rel)
    if not recap_path.is_absolute():
        recap_path = root / recap_path
    return recap_path.read_text(encoding="utf-8"), input_rel.replace("\\", "/")


def _default_run_bundle_dir(root: Path) -> Path:
    return root / "evals/graph_memory_layer/runs/live_recap_ingest/session_22_category_study"


def _resolve_run_dir(root: Path, run_dir: str) -> Path:
    raw = run_dir.strip().replace("\\", "/")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise GraphPreviewSurfaceError("run_dir escapes repository", status_code=422)
    if not resolved.is_dir():
        raise GraphPreviewSurfaceError(f"run_dir not found: {run_dir}", status_code=404)
    return resolved


def _collect_runs_from_cohort(cohort: Mapping[str, Any]) -> list[GraphPreviewRunSummary]:
    rows: list[GraphPreviewRunSummary] = []
    for entry in cohort.get("runs") or []:
        if not isinstance(entry, Mapping):
            continue
        run_dir = str(entry.get("run_dir") or "").strip()
        if not run_dir:
            continue
        rows.append(
            GraphPreviewRunSummary(
                run_dir=run_dir.replace("\\", "/"),
                model_id=str(entry.get("model_id") or "") or None,
                run_index=int(entry["run_index"]) if entry.get("run_index") is not None else None,
                canonical_ir_valid=bool(entry.get("canonical_ir_valid")) if entry.get("canonical_ir_valid") is not None else None,
                scenario_estimated_cost_usd=float(entry["scenario_estimated_cost_usd"])
                if entry.get("scenario_estimated_cost_usd") is not None
                else None,
            )
        )
    return rows


def discover_graph_preview_runs(root: Path | None = None) -> list[GraphPreviewRunSummary]:
    base = root or repo_root()
    seen: set[str] = set()
    runs: list[GraphPreviewRunSummary] = []

    mirror = base / LAST_COHORT_MIRROR_REL
    if mirror.is_file():
        runs.extend(_collect_runs_from_cohort(_load_json(mirror)))

    artifacts = artifacts_root(base)
    if artifacts.is_dir():
        for cohort_path in sorted(artifacts.rglob("cohort_summary.json")):
            runs.extend(_collect_runs_from_cohort(_load_json(cohort_path)))

    deduped: list[GraphPreviewRunSummary] = []
    for row in runs:
        if row.run_dir in seen:
            continue
        seen.add(row.run_dir)
        deduped.append(row)
    return deduped


def _graph_from_run_dir(root: Path, run_dir: str) -> dict[str, Any] | None:
    try:
        resolved = _resolve_run_dir(root, run_dir)
    except GraphPreviewSurfaceError:
        return None
    validation_path = resolved / "validation_report.json"
    candidate_path = resolved / "candidate_output.json"
    if validation_path.is_file():
        validation = _load_json(validation_path)
        if validation.get("reconciled_candidate_graph"):
            return dict(validation["reconciled_candidate_graph"])
    if candidate_path.is_file():
        envelope = _load_json(candidate_path)
        return dict(envelope.get("candidate_graph") or envelope)
    return None


def _run_has_resolvable_evidence(root: Path, run_dir: str) -> bool:
    """Cheap probe: does any evidence ref carry a source_span_ref_id we can locate?"""
    graph = _graph_from_run_dir(root, run_dir)
    if graph is None:
        return False
    for section in ("nodes", "edges", "beats", "ignored_items", "deferred_items"):
        for obj in graph.get(section) or []:
            if not isinstance(obj, Mapping):
                continue
            for ref in obj.get("evidence_refs") or []:
                if isinstance(ref, Mapping) and ref.get("source_span_ref_id"):
                    return True
    return False


def _pick_latest_run(root: Path, runs: list[GraphPreviewRunSummary]) -> GraphPreviewRunSummary | None:
    if not runs:
        return None
    # Prefer runs whose evidence can actually be located in the source (spref-backed),
    # so the source-highlight panel has something to render. Among resolvable runs,
    # prefer canonical-IR-valid; otherwise fall back to IR-valid, then most recent.
    resolvable = [r for r in runs if _run_has_resolvable_evidence(root, r.run_dir)]
    if resolvable:
        valid_resolvable = [r for r in resolvable if r.canonical_ir_valid]
        return (valid_resolvable or resolvable)[-1]
    valid = [r for r in runs if r.canonical_ir_valid]
    return (valid or runs)[-1]


def _object_id(section: str, obj: Mapping[str, Any]) -> str:
    for key in SECTION_ID_KEYS.get(section, ("id",)):
        if obj.get(key):
            return str(obj[key])
    return "<unknown>"


def _object_kind(section: str, obj: Mapping[str, Any]) -> str:
    if section == "nodes":
        return str(obj.get("node_type") or "node")
    if section == "edges":
        return str(obj.get("relationship_type") or obj.get("label") or "edge")
    if section == "beats":
        return "beat"
    return str(obj.get("item_type") or section.replace("_items", ""))


def _enrich_evidence_ref(
    ref: Mapping[str, Any],
    *,
    span_lookup: Mapping[str, Mapping[str, Any]],
    recap_text: str,
    recap_path: str,
    entity_label: str | None,
) -> GraphPreviewEvidenceRef:
    spref = str(ref.get("source_span_ref_id") or "") or None
    anchor = str(ref.get("source_anchor_id") or "") or None
    paragraph = ""
    line_start: int | None = None
    line_end: int | None = None
    if spref and spref in span_lookup:
        span = span_lookup[spref]
        line_start = int(span["line_start"])
        line_end = int(span["line_end"])
        paragraph = _paragraph_text_for_span(recap_text, span)

    anchor_quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
    raw_matches = list(ref.get("anchor_quote_matches") or [])
    matches: list[dict[str, Any]] = []
    if raw_matches:
        matches = [dict(m) for m in raw_matches if isinstance(m, Mapping)]
    elif paragraph:
        if anchor_quotes:
            matches = anchor_quote_matches_to_dicts(find_anchor_quote_matches(paragraph, anchor_quotes))
        elif entity_label and quote_found_in_paragraph(paragraph, entity_label):
            matches = anchor_quote_matches_to_dicts(find_anchor_quote_matches(paragraph, [entity_label]))

    return GraphPreviewEvidenceRef(
        source_ref_id=str(ref.get("source_ref_id") or "") or None,
        source_artifact_id=str(ref.get("source_artifact_id") or "") or None,
        source_span_ref_id=spref,
        source_anchor_id=anchor,
        label=str(ref.get("label") or "") or None,
        evidence_role=str(ref.get("evidence_role") or "") or None,
        can_open_source=bool(ref.get("can_open_source")),
        can_highlight_span=bool(ref.get("can_highlight_span")),
        anchor_quotes=anchor_quotes,
        anchor_quote_matches=[AnchorQuoteMatchRow.model_validate(m) for m in matches],
        paragraph_text=paragraph or None,
        line_start=line_start,
        line_end=line_end,
        recap_source_path=recap_path if paragraph else None,
    )


def _build_candidates(
    graph: Mapping[str, Any],
    *,
    span_lookup: Mapping[str, Mapping[str, Any]],
    recap_text: str,
    recap_path: str,
) -> list[GraphPreviewCandidateRow]:
    rows: list[GraphPreviewCandidateRow] = []
    for section in ("nodes", "edges", "beats", "ignored_items", "deferred_items"):
        for obj in graph.get(section) or []:
            if not isinstance(obj, Mapping):
                continue
            label = str(obj.get("label") or obj.get("title") or _object_id(section, obj))
            enriched = [
                _enrich_evidence_ref(
                    ref,
                    span_lookup=span_lookup,
                    recap_text=recap_text,
                    recap_path=recap_path,
                    entity_label=label,
                )
                for ref in obj.get("evidence_refs") or []
                if isinstance(ref, Mapping)
            ]
            rows.append(
                GraphPreviewCandidateRow(
                    section=section,
                    object_id=_object_id(section, obj),
                    label=label,
                    kind=_object_kind(section, obj),
                    description=str(obj.get("description") or obj.get("summary") or "") or None,
                    importance=str(obj.get("importance") or "") or None,
                    evidence_count=len(enriched),
                    evidence_refs=enriched,
                )
            )
    return rows


def build_graph_preview_surface(
    root: Path,
    run_dir: str,
    *,
    run_bundle_dir: Path | None = None,
) -> GraphPreviewSurfaceResponse:
    resolved_run = _resolve_run_dir(root, run_dir)
    rel_run_dir = resolved_run.relative_to(root.resolve()).as_posix()

    validation_path = resolved_run / "validation_report.json"
    run_summary_path = resolved_run / "run_summary.json"
    candidate_path = resolved_run / "candidate_output.json"

    validation = _load_json(validation_path) if validation_path.is_file() else {}
    run_summary = _load_json(run_summary_path) if run_summary_path.is_file() else {}

    graph: dict[str, Any] | None = None
    if validation.get("reconciled_candidate_graph"):
        graph = dict(validation["reconciled_candidate_graph"])
    elif candidate_path.is_file():
        envelope = _load_json(candidate_path)
        graph = dict(envelope.get("candidate_graph") or envelope)

    if graph is None:
        raise GraphPreviewSurfaceError(f"no graph artifact in run_dir: {rel_run_dir}")

    bundle = run_bundle_dir or _default_run_bundle_dir(root)
    if not bundle.is_dir():
        raise GraphPreviewSurfaceError(f"run bundle not found: {bundle}", status_code=404)

    span_index = _load_json(bundle / "source_span_index.json")
    span_lookup = {sp["source_span_ref_id"]: sp for sp in span_index.get("spans", [])}
    recap_text, recap_path = _recap_text_for_run_bundle(root, bundle)

    candidates = _build_candidates(
        graph,
        span_lookup=span_lookup,
        recap_text=recap_text,
        recap_path=recap_path,
    )

    evidence_ref_count = sum(len(c.evidence_refs) for c in candidates)
    resolvable = sum(
        1
        for c in candidates
        for ref in c.evidence_refs
        if ref.paragraph_text or ref.source_anchor_id
    )

    health = GraphPreviewHealth(
        canonical_ir_valid=bool(validation.get("canonical_ir_valid")),
        reconcile_error=str(validation.get("reconcile_error") or "") or None,
        node_count=len(graph.get("nodes") or []),
        edge_count=len(graph.get("edges") or []),
        beat_count=len(graph.get("beats") or []),
        ignored_count=len(graph.get("ignored_items") or []),
        deferred_count=len(graph.get("deferred_items") or []),
        evidence_ref_count=evidence_ref_count,
        resolvable_evidence_ref_count=resolvable,
        model_id=str(run_summary.get("model_id") or "") or None,
        scenario_estimated_cost_usd=float(run_summary["scenario_estimated_cost_usd"])
        if run_summary.get("scenario_estimated_cost_usd") is not None
        else None,
        node_recall=float((run_summary.get("scores") or {}).get("node_recall"))
        if (run_summary.get("scores") or {}).get("node_recall") is not None
        else None,
    )

    bundle_rel = bundle.relative_to(root.resolve()).as_posix() if bundle.is_relative_to(root.resolve()) else str(bundle)

    return GraphPreviewSurfaceResponse(
        run_dir=rel_run_dir,
        run_bundle_dir=bundle_rel,
        recap_source_path=recap_path,
        health=health,
        candidates=candidates,
    )


def build_latest_graph_preview_surface(root: Path | None = None) -> GraphPreviewSurfaceResponse:
    base = root or repo_root()
    runs = discover_graph_preview_runs(base)
    picked = _pick_latest_run(base, runs)
    if picked is None:
        raise GraphPreviewSurfaceError("no graph preview runs discovered", status_code=404)
    return build_graph_preview_surface(base, picked.run_dir)
