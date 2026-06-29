"""Session 22 candidate graph gold fixture helpers (hand-authored; no extraction)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.graph_memory_layer.session_22_recap_ingest_fixture import (
    FIXTURE_ID as SOURCE_FIXTURE_ID,
    build_source_span_artifacts,
    load_normalized_recap,
    load_source_span_seed_refs,
    repo_root,
    resolve_source_span_seed_refs,
)
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

GOLD_FIXTURE_ID = "graph-memory:session-22-candidate-graph-gold:v0"
GOLD_MANIFEST_SCHEMA = "dmb_session_22_candidate_graph_gold_manifest_v0"
GOLD_MANIFEST_VERSION = "0.1"
GOLD_FIXTURE_REL = "evals/graph_memory_layer/examples/session_22_candidate_graph_gold"
GOLD_GRAPH_PATH = "evals/graph_memory_layer/examples/session_22_candidate_graph_gold/candidate_graph_gold.json"
GOLD_MANIFEST_PATH = "evals/graph_memory_layer/examples/session_22_candidate_graph_gold/session_22_candidate_graph_gold_manifest.json"
SOURCE_ARTIFACT_ID = "source-artifact:session-22-normalized-recap"
SOURCE_REF_ID = "source-ref:session-22-normalized-recap"

HIGH_RISK_EVIDENCE_AUDIT: tuple[dict[str, str], ...] = (
    {"object_id": "node:private-hester", "source_anchor_id": "anchor:s22-private-hester-report", "expected_phrase": "Private Hester"},
    {"object_id": "edge:hester-reports-swamp-music", "source_anchor_id": "anchor:s22-hester-swamp-music", "expected_phrase": "mysterious music"},
    {"object_id": "node:grobnok", "source_anchor_id": "anchor:s22-grobnok-frank-sara", "expected_phrase": "rockie-talkie"},
    {"object_id": "edge:grobnok-works-with-tealeaf", "source_anchor_id": "anchor:s22-grobnok-tealeaf-control", "expected_phrase": "Tealeaf"},
    {"object_id": "node:northern-song", "source_anchor_id": "anchor:s22-shared-song-dustwalker", "expected_phrase": "Dustwalker"},
    {"object_id": "edge:lysandro-parent-of-lysandra", "source_anchor_id": "anchor:s22-arrival-lysandro", "expected_phrase": "father Lysandro"},
)


def gold_fixture_dir() -> Path:
    return repo_root() / GOLD_FIXTURE_REL


def gold_manifest_path() -> Path:
    return repo_root() / GOLD_MANIFEST_PATH


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe relative path: {value}")
    return path


def load_gold_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or gold_manifest_path())


def validate_gold_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != GOLD_MANIFEST_SCHEMA:
        raise ValueError("wrong gold manifest schema")
    if manifest.get("version") != GOLD_MANIFEST_VERSION:
        raise ValueError("wrong gold manifest version")
    if manifest.get("fixture_id") != GOLD_FIXTURE_ID:
        raise ValueError("wrong gold fixture id")
    if manifest.get("campaign_id") != "longmont-c2" or manifest.get("session") != 22:
        raise ValueError("wrong gold session metadata")
    if manifest.get("input_mode") != "explicit_fixture_dependency":
        raise ValueError("gold input mode must be explicit_fixture_dependency")
    if manifest.get("source_fixture_id") != SOURCE_FIXTURE_ID:
        raise ValueError("wrong source fixture dependency")
    expected = {
        "source_manifest_path": "evals/graph_memory_layer/examples/session_22_recap_ingest/session_22_recap_ingest_manifest.json",
        "source_span_seed_refs_path": "evals/graph_memory_layer/examples/session_22_recap_ingest/source_span_seed_refs.json",
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


def valid_source_anchor_ids() -> set[str]:
    return {ref["source_anchor_id"] for ref in load_source_span_seed_refs()["source_span_refs"]}


def collect_gold_evidence_refs(preview: CandidateGraphPreview) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = []
    for seq in (preview.nodes, preview.edges, preview.beats, preview.proposed_writes, preview.ignored_items, preview.deferred_items):
        for obj in seq:
            refs.extend(obj.evidence_refs)
    return tuple(refs)


def _to_source_span_ref(ref: EvidenceRef) -> SourceSpanRef:
    seed = next(item for item in load_source_span_seed_refs()["source_span_refs"] if item["source_anchor_id"] == ref.source_anchor_id)
    allowed = set(SourceSpanRef.__dataclass_fields__)
    data = {key: value for key, value in seed.items() if key in allowed}
    data.update({"label": ref.label or seed.get("label"), "evidence_role": ref.evidence_role})
    return SourceSpanRef(**data)


def resolve_gold_evidence_refs() -> tuple[ResolvedEvidence, ...]:
    refs = tuple(_to_source_span_ref(ref) for ref in collect_gold_evidence_refs(parse_gold_candidate_graph()))
    text, structured = build_source_span_artifacts()
    return resolve_many_source_span_refs(refs, text_artifacts=text, structured_artifacts=structured, snippet_max_chars=240, context_lines=0)


def gold_graph_to_serializable() -> dict[str, Any]:
    return candidate_graph_preview_to_dict(parse_gold_candidate_graph())


def resolved_to_serializable(resolved: tuple[ResolvedEvidence, ...]) -> list[dict[str, Any]]:
    return [asdict(item) for item in resolved]


def _object_evidence_refs(preview: CandidateGraphPreview, object_id: str) -> tuple[EvidenceRef, ...]:
    for seq in (preview.nodes, preview.edges, preview.beats, preview.proposed_writes, preview.ignored_items, preview.deferred_items):
        for obj in seq:
            current_id = getattr(obj, "node_id", getattr(obj, "edge_id", getattr(obj, "beat_id", getattr(obj, "write_id", getattr(obj, "item_id", None)))))
            if current_id == object_id:
                return obj.evidence_refs
    raise ValueError(f"unknown gold object for evidence audit: {object_id}")


def validate_high_risk_evidence_audit(preview: CandidateGraphPreview | None = None) -> None:
    preview = preview or parse_gold_candidate_graph()
    resolved_by_anchor = {item.source_anchor_id: item.preview_snippet for item in resolve_source_span_seed_refs()}
    for row in HIGH_RISK_EVIDENCE_AUDIT:
        refs = _object_evidence_refs(preview, row["object_id"])
        if not any(ref.source_anchor_id == row["source_anchor_id"] for ref in refs):
            raise ValueError(f"{row['object_id']} missing audited anchor {row['source_anchor_id']}")
        snippet = resolved_by_anchor.get(row["source_anchor_id"], "")
        if row["expected_phrase"].lower() not in snippet.lower():
            raise ValueError(f"audited phrase not found for {row['object_id']}: {row['expected_phrase']}")


def load_source_text() -> str:
    return load_normalized_recap()
