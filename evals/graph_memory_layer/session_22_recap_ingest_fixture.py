"""Session 22 recap source-span fixture helpers (hand-authored; no extraction)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.graph_memory.source_span import (
    ResolvedEvidence,
    SourceArtifactStructured,
    SourceArtifactText,
    SourceSpanRef,
    resolve_many_source_span_refs,
    source_span_ref_from_dict,
)

FIXTURE_ID = "graph-memory:session-22-recap-ingest:v0"
MANIFEST_SCHEMA = "dmb_session_22_recap_ingest_fixture_manifest_v0"
MANIFEST_VERSION = "0.1"
SOURCE_SPAN_SEED_SCHEMA = "dmb_session_22_recap_source_span_seed_refs_v0"
NORMALIZED_RECAP_REL = "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"
FIXTURE_REL = "evals/graph_memory_layer/examples/session_22_recap_ingest"
DANGEROUS_FLAGS = (
    "llm_required",
    "live_planner_required",
    "write_tools_required",
    "corpus_scan_required",
    "corpus_mutation_required",
    "graph_extraction_performed",
    "candidate_graph_output",
    "gold_graph_output",
    "plan_connected",
    "agent_interaction_connected",
    "runtime_behavior_changed",
    "production_behavior_changed",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fixture_dir() -> Path:
    return repo_root() / FIXTURE_REL


def manifest_path() -> Path:
    return fixture_dir() / "session_22_recap_ingest_manifest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe relative path: {value}")
    return path


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or manifest_path())


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("wrong manifest schema")
    if manifest.get("version") != MANIFEST_VERSION:
        raise ValueError("wrong manifest version")
    if manifest.get("fixture_id") != FIXTURE_ID:
        raise ValueError("wrong fixture id")
    if manifest.get("campaign_id") != "longmont-c2" or manifest.get("session") != 22:
        raise ValueError("wrong session metadata")
    if manifest.get("input_mode") != "explicit_normalized_corpus_path":
        raise ValueError("input must be explicit_normalized_corpus_path")
    if manifest.get("normalized_recap_path") != NORMALIZED_RECAP_REL:
        raise ValueError("normalized recap path must be exact")
    normalized = _rel_path(manifest["normalized_recap_path"])
    if not (repo_root() / normalized).is_file():
        raise ValueError("normalized recap path missing or not a file")
    rel = _rel_path(manifest["source_span_seed_refs_path"])
    if not str(rel).startswith(FIXTURE_REL + "/"):
        raise ValueError("source_span_seed_refs_path outside fixture dir")
    diagnostics = manifest.get("diagnostics", {})
    for key in DANGEROUS_FLAGS:
        if diagnostics.get(key) is not False:
            raise ValueError(f"dangerous diagnostic flag not false: {key}")
    if diagnostics.get("manual_source_span_fixture") is not True:
        raise ValueError("manual_source_span_fixture must be true")


def normalized_recap_path(manifest: dict[str, Any] | None = None) -> Path:
    manifest = manifest or load_manifest()
    validate_manifest(manifest)
    return repo_root() / manifest["normalized_recap_path"]


def load_normalized_recap(manifest: dict[str, Any] | None = None) -> str:
    return normalized_recap_path(manifest).read_text(encoding="utf-8")


def load_source_span_seed_refs() -> dict[str, Any]:
    return _load_json(fixture_dir() / "source_span_seed_refs.json")


def build_source_span_artifacts() -> tuple[dict[str, SourceArtifactText], dict[str, SourceArtifactStructured]]:
    data = load_source_span_seed_refs()
    text: dict[str, SourceArtifactText] = {}
    for art in data["source_artifacts"]:
        rel = _rel_path(art["path"])
        text[art["source_artifact_id"]] = SourceArtifactText(
            art["source_artifact_id"],
            art["source_ref_id"],
            art["artifact_kind"],
            art["path"],
            (repo_root() / rel).read_text(encoding="utf-8"),
            art["evidence_role"],
            art["visibility_state"],
        )
    return text, {}


def parse_source_span_seed_refs() -> tuple[SourceSpanRef, ...]:
    data = load_source_span_seed_refs()
    if data.get("schema") != SOURCE_SPAN_SEED_SCHEMA or data.get("version") != "0.1":
        raise ValueError("wrong source span seed schema/version")
    return tuple(source_span_ref_from_dict(ref) for ref in data["source_span_refs"])


def resolve_source_span_seed_refs() -> tuple[ResolvedEvidence, ...]:
    text, structured = build_source_span_artifacts()
    return resolve_many_source_span_refs(
        parse_source_span_seed_refs(),
        text_artifacts=text,
        structured_artifacts=structured,
        snippet_max_chars=240,
        context_lines=0,
    )


def resolved_to_serializable(resolved: tuple[ResolvedEvidence, ...]) -> list[dict[str, Any]]:
    return [asdict(item) for item in resolved]
