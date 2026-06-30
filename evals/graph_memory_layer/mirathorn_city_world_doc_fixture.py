"""Mirathorn city world doc fixture helpers (deterministic; no IO writes)."""
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

FIXTURE_ID = "graph-memory:mirathorn-city-world-doc:v0"
MANIFEST_SCHEMA = "dmb_mirathorn_city_world_doc_fixture_manifest_v0"
MANIFEST_VERSION = "0.1"
SOURCE_SPAN_SEED_SCHEMA = "dmb_mirathorn_city_world_doc_source_span_seed_refs_v0"
FIXTURE_REL = "evals/graph_memory_layer/examples/mirathorn_city_world_doc"
SOURCE_DOC_REL = "evals/graph_memory_layer/examples/mirathorn_city_world_doc/mirathorn_city_source.md"
SOURCE_ARTIFACT_ID = "source-artifact:mirathorn-city-world-doc"
SOURCE_REF_ID = "source-ref:mirathorn-city-world-doc"
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
    return fixture_dir() / "mirathorn_city_world_doc_manifest.json"


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
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("wrong manifest schema")
    if manifest.get("version") != MANIFEST_VERSION:
        raise ValueError("wrong manifest version")
    if manifest.get("fixture_id") != FIXTURE_ID:
        raise ValueError("wrong fixture id")
    if manifest.get("campaign_id") is not None or manifest.get("session") is not None:
        raise ValueError("world doc fixture must not carry session metadata")
    if manifest.get("input_mode") != "explicit_path_only":
        raise ValueError("input must be explicit_path_only")
    if manifest.get("source_doc_path") != SOURCE_DOC_REL:
        raise ValueError("source doc path must be exact")
    source = _rel_path(manifest["source_doc_path"])
    if not str(source).startswith(FIXTURE_REL + "/"):
        raise ValueError("source doc must live inside fixture dir")
    source_abs = repo_root() / source
    if not source_abs.exists() or not source_abs.is_file():
        raise ValueError("source doc path missing or not a file")
    seed_rel = _rel_path(manifest["source_span_seed_refs_path"])
    if not str(seed_rel).startswith(FIXTURE_REL + "/"):
        raise ValueError("source_span_seed_refs_path outside fixture dir")
    diagnostics = manifest.get("diagnostics", {})
    for key in DANGEROUS_FLAGS:
        if diagnostics.get(key) is not False:
            raise ValueError(f"dangerous diagnostic flag not false: {key}")


def source_doc_path(manifest: dict[str, Any] | None = None) -> Path:
    manifest = manifest or load_manifest()
    validate_manifest(manifest)
    return repo_root() / manifest["source_doc_path"]


def load_source_doc(manifest: dict[str, Any] | None = None) -> str:
    return source_doc_path(manifest).read_text(encoding="utf-8")


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
    return [asdict(r) for r in resolved]
