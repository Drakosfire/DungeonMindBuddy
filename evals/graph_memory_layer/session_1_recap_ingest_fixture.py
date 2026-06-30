"""Session 1 raw recap ingest fixture helpers (deterministic; no IO writes)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agent.recap_ingest_helpers import IngestReport, assemble_recap, numbered_lines_for_recap, split_paragraphs_robust
from src.graph_memory.source_span import SourceArtifactStructured, SourceArtifactText, SourceSpanRef, ResolvedEvidence, resolve_many_source_span_refs, source_span_ref_from_dict

FIXTURE_ID = "graph-memory:session-1-recap-ingest:v0"
MANIFEST_SCHEMA = "dmb_session_1_recap_ingest_fixture_manifest_v0"
MANIFEST_VERSION = "0.1"
PARAGRAPH_INDEX_SCHEMA = "dmb_session_1_recap_paragraph_index_v0"
SOURCE_SPAN_SEED_SCHEMA = "dmb_session_1_recap_source_span_seed_refs_v0"
RAW_RECAP_REL = "evals/c1_live_prep/live/session_1/session_1_raw_recap.md"
FIXTURE_REL = "evals/graph_memory_layer/examples/session_1_recap_ingest"
DANGEROUS_FLAGS = ("llm_required","live_planner_required","write_tools_required","corpus_scan_required","corpus_mutation_required","graph_extraction_performed","candidate_graph_output","gold_graph_output","plan_connected","agent_interaction_connected","runtime_behavior_changed","production_behavior_changed")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def fixture_dir() -> Path:
    return repo_root() / FIXTURE_REL

def manifest_path() -> Path:
    return fixture_dir() / "session_1_recap_ingest_manifest.json"

def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _rel_path(value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe relative path: {value}")
    return p

def load_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or manifest_path())

def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA: raise ValueError("wrong manifest schema")
    if manifest.get("version") != MANIFEST_VERSION: raise ValueError("wrong manifest version")
    if manifest.get("fixture_id") != FIXTURE_ID: raise ValueError("wrong fixture id")
    if manifest.get("campaign_id") != "longmont-c1" or manifest.get("session") != 1: raise ValueError("wrong session metadata")
    if manifest.get("input_mode") != "explicit_path_only": raise ValueError("input must be explicit_path_only")
    if manifest.get("raw_recap_path") != RAW_RECAP_REL: raise ValueError("raw recap path must be exact")
    raw = _rel_path(manifest["raw_recap_path"])
    if raw.parts and raw.parts[0] == "corpus": raise ValueError("raw recap may not be under corpus")
    raw_abs = repo_root() / raw
    if not raw_abs.exists() or not raw_abs.is_file(): raise ValueError("raw recap path missing or not a file")
    for key in ("expected_normalized_recap_path","expected_paragraph_index_path","source_span_seed_refs_path"):
        rel = _rel_path(manifest[key])
        if not str(rel).startswith(FIXTURE_REL + "/"): raise ValueError(f"{key} outside fixture dir")
    diagnostics = manifest.get("diagnostics", {})
    for key in DANGEROUS_FLAGS:
        if diagnostics.get(key) is not False: raise ValueError(f"dangerous diagnostic flag not false: {key}")

def raw_recap_path(manifest: dict[str, Any] | None = None) -> Path:
    manifest = manifest or load_manifest(); validate_manifest(manifest)
    return repo_root() / manifest["raw_recap_path"]

def load_raw_recap(manifest: dict[str, Any] | None = None) -> str:
    return raw_recap_path(manifest).read_text(encoding="utf-8")

def assemble_session_1_normalized_recap(raw_text: str) -> tuple[str, IngestReport]:
    return assemble_recap(raw_notes=raw_text, session=1, campaign_id="longmont-c1", title="Session 1 - Stonebridge and Glowkindle Rats", remove_duplicates=True)

def build_paragraph_index(raw_text: str) -> dict[str, Any]:
    numbered, stripped = numbered_lines_for_recap(raw_text, 1)
    paragraphs = split_paragraphs_robust(numbered)
    _, report = assemble_session_1_normalized_recap(raw_text)
    return {"schema": PARAGRAPH_INDEX_SCHEMA, "version": "0.1", "fixture_id": FIXTURE_ID, "source_path": RAW_RECAP_REL, "session": 1, "title_line_stripped": stripped, "paragraph_count_in": report.paragraph_count_in, "paragraph_count_out": report.paragraph_count_out, "duplicates_detected": len(report.duplicates_detected), "duplicates_removed": len(report.duplicates_removed), "paragraphs": [{"paragraph_id": f"s1-p{i:03d}", "source_line_start": p.source_line_start, "source_line_end": p.source_line_end, "normalized_index": i, "preview": (p.text[:157].rstrip() + "...") if len(p.text) > 160 else p.text} for i,p in enumerate(paragraphs, 1)]}

def load_expected_normalized_recap() -> str:
    return (fixture_dir() / "expected_normalized_recap.md").read_text(encoding="utf-8")

def load_expected_paragraph_index() -> dict[str, Any]:
    return _load_json(fixture_dir() / "expected_paragraph_index.json")

def load_source_span_seed_refs() -> dict[str, Any]:
    return _load_json(fixture_dir() / "source_span_seed_refs.json")

def build_source_span_artifacts() -> tuple[dict[str, SourceArtifactText], dict[str, SourceArtifactStructured]]:
    data = load_source_span_seed_refs(); text = {}
    for art in data["source_artifacts"]:
        rel = _rel_path(art["path"])
        text[art["source_artifact_id"]] = SourceArtifactText(art["source_artifact_id"], art["source_ref_id"], art["artifact_kind"], art["path"], (repo_root()/rel).read_text(encoding="utf-8"), art["evidence_role"], art["visibility_state"])
    return text, {}

def parse_source_span_seed_refs() -> tuple[SourceSpanRef, ...]:
    data = load_source_span_seed_refs()
    if data.get("schema") != SOURCE_SPAN_SEED_SCHEMA or data.get("version") != "0.1": raise ValueError("wrong source span seed schema/version")
    return tuple(source_span_ref_from_dict(ref) for ref in data["source_span_refs"])

def resolve_source_span_seed_refs() -> tuple[ResolvedEvidence, ...]:
    text, structured = build_source_span_artifacts()
    return resolve_many_source_span_refs(parse_source_span_seed_refs(), text_artifacts=text, structured_artifacts=structured, snippet_max_chars=240, context_lines=0)

def resolved_to_serializable(resolved: tuple[ResolvedEvidence, ...]) -> list[dict[str, Any]]:
    return [asdict(r) for r in resolved]
