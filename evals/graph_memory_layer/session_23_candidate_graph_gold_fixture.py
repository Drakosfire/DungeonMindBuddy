"""Session 23 candidate graph gold fixture helpers (hand-authored; no extraction)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    CandidateGraphPreview,
    CandidateGraphPreviewValidationReport,
    EvidenceRef,
    candidate_graph_preview_from_dict,
    candidate_graph_preview_to_dict,
    validate_candidate_graph_preview,
)
from src.graph_memory.source_span import ResolvedEvidence, SourceSpanRef, resolve_many_source_span_refs
from evals.graph_memory_layer.session_23_recap_ingest_fixture import (
    FIXTURE_ID as SOURCE_FIXTURE_ID,
    build_source_span_artifacts,
    load_source_span_seed_refs,
    repo_root,
    resolve_source_span_seed_refs,
)

GOLD_FIXTURE_ID = "graph-memory:session-23-candidate-graph-gold:v0"
GOLD_MANIFEST_SCHEMA = "dmb_session_23_candidate_graph_gold_manifest_v0"
GOLD_MANIFEST_VERSION = "0.1"
GOLD_FIXTURE_REL = "evals/graph_memory_layer/examples/session_23_candidate_graph_gold"
GOLD_GRAPH_PATH = "evals/graph_memory_layer/examples/session_23_candidate_graph_gold/candidate_graph_gold.json"
GOLD_MANIFEST_PATH = "evals/graph_memory_layer/examples/session_23_candidate_graph_gold/session_23_candidate_graph_gold_manifest.json"
SOURCE_ARTIFACT_ID = "source-artifact:session-23-normalized-recap"
SOURCE_REF_ID = "source-ref:session-23-normalized-recap"


def gold_fixture_dir() -> Path:
    return repo_root() / GOLD_FIXTURE_REL


def gold_manifest_path() -> Path:
    return repo_root() / GOLD_MANIFEST_PATH


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe relative path: {value}")
    return p


def load_gold_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or gold_manifest_path())


def validate_gold_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != GOLD_MANIFEST_SCHEMA:
        raise ValueError("wrong gold manifest schema")
    if manifest.get("version") != GOLD_MANIFEST_VERSION:
        raise ValueError("wrong gold manifest version")
    if manifest.get("fixture_id") != GOLD_FIXTURE_ID:
        raise ValueError("wrong gold fixture id")
    if manifest.get("campaign_id") != "longmont-c2" or manifest.get("session") != 23:
        raise ValueError("wrong gold session metadata")
    if manifest.get("input_mode") != "explicit_fixture_dependency":
        raise ValueError("gold input mode must be explicit_fixture_dependency")
    if manifest.get("source_fixture_id") != SOURCE_FIXTURE_ID:
        raise ValueError("wrong source fixture dependency")
    expected = {
        "source_manifest_path": "evals/graph_memory_layer/examples/session_23_recap_ingest/session_23_recap_ingest_manifest.json",
        "source_span_seed_refs_path": "evals/graph_memory_layer/examples/session_23_recap_ingest/source_span_seed_refs.json",
        "candidate_graph_gold_path": GOLD_GRAPH_PATH,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"wrong {key}")
        _rel(manifest[key])
    diagnostics = manifest.get("diagnostics", {})
    for key, value in diagnostics.items():
        if key != "manual_gold_fixture" and value is not False:
            raise ValueError(f"dangerous diagnostic flag not false: {key}")
    if diagnostics.get("manual_gold_fixture") is not True:
        raise ValueError("manual_gold_fixture must be true")


def gold_graph_path(manifest: dict[str, Any] | None = None) -> Path:
    manifest = manifest or load_gold_manifest()
    validate_gold_manifest(manifest)
    return repo_root() / manifest["candidate_graph_gold_path"]


def load_gold_candidate_graph_dict() -> dict[str, Any]:
    return _load_json(gold_graph_path())


def parse_gold_candidate_graph() -> CandidateGraphPreview:
    return candidate_graph_preview_from_dict(load_gold_candidate_graph_dict())


def validate_gold_candidate_graph() -> CandidateGraphPreviewValidationReport:
    return validate_candidate_graph_preview(parse_gold_candidate_graph())


def load_session_23_source_span_seed_refs() -> dict[str, Any]:
    return load_source_span_seed_refs()


def valid_source_anchor_ids() -> set[str]:
    return {r["source_anchor_id"] for r in load_source_span_seed_refs()["source_span_refs"]}


def collect_gold_evidence_refs(preview: CandidateGraphPreview) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = []
    for seq in (preview.nodes, preview.edges, preview.beats, preview.proposed_writes, preview.ignored_items, preview.deferred_items):
        for obj in seq:
            refs.extend(obj.evidence_refs)
    return tuple(refs)


def _to_source_span_ref(ref: EvidenceRef) -> SourceSpanRef:
    seed = next(r for r in load_source_span_seed_refs()["source_span_refs"] if r["source_anchor_id"] == ref.source_anchor_id)
    allowed = set(SourceSpanRef.__dataclass_fields__)
    data = {k: v for k, v in seed.items() if k in allowed}
    data.update({"label": ref.label or seed.get("label"), "evidence_role": ref.evidence_role})
    return SourceSpanRef(**data)


def resolve_gold_evidence_refs() -> tuple[ResolvedEvidence, ...]:
    refs = tuple(_to_source_span_ref(r) for r in collect_gold_evidence_refs(parse_gold_candidate_graph()))
    text, structured = build_source_span_artifacts()
    return resolve_many_source_span_refs(refs, text_artifacts=text, structured_artifacts=structured, snippet_max_chars=240, context_lines=0)


def gold_graph_to_serializable() -> dict[str, Any]:
    return candidate_graph_preview_to_dict(parse_gold_candidate_graph())


def resolved_to_serializable(resolved: tuple[ResolvedEvidence, ...]) -> list[dict[str, Any]]:
    return [asdict(r) for r in resolved]
