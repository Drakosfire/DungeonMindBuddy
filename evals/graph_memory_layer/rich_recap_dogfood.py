from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.graph_memory.recap_ingestion_materialize import INPUT_MODE, SOURCE_FAMILY, RecapIngestionMaterializerInput
from src.graph_memory.recap_ingestion_materializer_report import KNOWN_ARTIFACT_FAMILIES
from src.graph_memory.source_span import SourceArtifactStructured, SourceArtifactText, source_span_ref_from_dict

MANIFEST_SCHEMA = "dmb_rich_recap_dogfood_manifest_v0"
MANIFEST_VERSION = "0.1"
REQUIREMENTS_SCHEMA = "dmb_rich_recap_dogfood_requirements_v0"
SOURCE_SPAN_REFS_SCHEMA = "dmb_rich_recap_source_span_refs_v0"
FIXTURE_ID = "dogfood:rich-recap:redacted-lantern-archive:v0"
ARTIFACT_IDS = {
    "normalized_recap_markdown": "source-artifact:rich-normalized-recap",
    "breadcrumbed_recap_markdown": "source-artifact:rich-breadcrumbed-recap",
    "frontmatter_seed_markdown": "source-artifact:rich-frontmatter-seed",
    "session_memory_jsonl_meta": "source-artifact:rich-session-memory-meta",
    "corpus_impact_proof": "source-artifact:rich-corpus-impact-proof",
}
SOURCE_REF_IDS = {
    "normalized_recap_markdown": "source-ref:rich-normalized-recap",
    "breadcrumbed_recap_markdown": "source-ref:rich-breadcrumbed-recap",
    "frontmatter_seed_markdown": "source-ref:rich-frontmatter-seed",
    "session_memory_jsonl_meta": "source-ref:rich-session-memory-meta",
    "corpus_impact_proof": "source-ref:rich-corpus-impact-proof",
}
ARTIFACT_KINDS = {
    "normalized_recap_markdown": "normalized_recap",
    "breadcrumbed_recap_markdown": "breadcrumbed_recap",
    "frontmatter_seed_markdown": "frontmatter_seed",
    "session_memory_jsonl_meta": "session_memory_meta",
    "corpus_impact_proof": "corpus_impact_proof",
}
EVIDENCE_ROLES = {
    "normalized_recap_markdown": "source_evidence",
    "breadcrumbed_recap_markdown": "navigation_hint",
    "frontmatter_seed_markdown": "not_evidence",
    "session_memory_jsonl_meta": "diagnostic_only",
    "corpus_impact_proof": "diagnostic_only",
}
VISIBILITY = {
    "normalized_recap_markdown": "gm_private",
    "breadcrumbed_recap_markdown": "gm_private",
    "frontmatter_seed_markdown": "internal_diagnostic",
    "session_memory_jsonl_meta": "internal_diagnostic",
    "corpus_impact_proof": "internal_diagnostic",
}


def rich_recap_fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "examples" / "rich_recap_dogfood"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(data, dict), f"{path.name} must be a JSON object")
    return data


def load_rich_recap_manifest(path: Path | None = None) -> dict[str, object]:
    return _load_json(path or rich_recap_fixture_dir() / "rich_recap_manifest.json")


def _safe_relative_path(value: object) -> Path:
    _require(isinstance(value, str) and value, "artifact input relative_path must be a non-empty string")
    rel = Path(value)
    _require(not rel.is_absolute(), f"absolute rich recap input paths are forbidden: {value}")
    _require(".." not in rel.parts, f"parent traversal is forbidden in rich recap input path: {value}")
    _require(len(rel.parts) == 1, f"rich recap input path must be an explicit fixture-local filename: {value}")
    return rel


def validate_rich_recap_manifest(manifest: dict[str, object]) -> None:
    _require(manifest.get("schema") == MANIFEST_SCHEMA, "bad rich recap manifest schema")
    _require(manifest.get("version") == MANIFEST_VERSION, "bad rich recap manifest version")
    _require(manifest.get("fixture_id") == FIXTURE_ID, "bad rich recap fixture_id")
    _require(manifest.get("source_family") == SOURCE_FAMILY, "bad rich recap source_family")
    _require(manifest.get("input_mode") == INPUT_MODE, "rich recap input_mode must be explicit_paths_only")
    artifact_inputs = manifest.get("artifact_inputs")
    _require(isinstance(artifact_inputs, list), "artifact_inputs must be a list")
    seen: set[str] = set()
    for item in artifact_inputs:
        _require(isinstance(item, dict), "artifact input must be an object")
        admitted_id = item.get("admitted_artifact_id")
        _require(isinstance(admitted_id, str) and admitted_id, "admitted_artifact_id must be a non-empty string")
        _require(admitted_id in KNOWN_ARTIFACT_FAMILIES, f"unknown admitted artifact id: {admitted_id}")
        _require(admitted_id not in seen, f"duplicate admitted artifact id: {admitted_id}")
        seen.add(admitted_id)
        _safe_relative_path(item.get("relative_path"))
    _require(seen == KNOWN_ARTIFACT_FAMILIES, "rich recap manifest must include all five admitted artifact families")


def build_rich_recap_materializer_inputs(path: Path | None = None) -> list[RecapIngestionMaterializerInput]:
    manifest_path = path or rich_recap_fixture_dir() / "rich_recap_manifest.json"
    manifest = load_rich_recap_manifest(manifest_path)
    validate_rich_recap_manifest(manifest)
    inputs: list[RecapIngestionMaterializerInput] = []
    for item in manifest["artifact_inputs"]:  # type: ignore[index]
        admitted_id = str(item["admitted_artifact_id"])
        rel = _safe_relative_path(item["relative_path"])
        resolved = manifest_path.parent / rel
        _require(resolved.exists(), f"rich recap input is missing: {rel}")
        _require(resolved.is_file(), f"rich recap input must be a file: {rel}")
        _require(not resolved.is_dir(), f"rich recap input directories are forbidden: {rel}")
        inputs.append(RecapIngestionMaterializerInput(admitted_id, resolved))
    return inputs


def load_rich_recap_requirements(path: Path | None = None) -> dict[str, object]:
    return _load_json(path or rich_recap_fixture_dir() / "dogfood_requirements.json")


def load_rich_recap_source_span_refs(path: Path | None = None) -> dict[str, object]:
    return _load_json(path or rich_recap_fixture_dir() / "source_span_refs.json")


def build_rich_recap_source_span_registries(path: Path | None = None):
    inputs = build_rich_recap_materializer_inputs(path)
    text_artifacts = {}
    structured_artifacts = {}
    for item in inputs:
        common = dict(
            source_artifact_id=ARTIFACT_IDS[item.admitted_artifact_id],
            source_ref_id=SOURCE_REF_IDS[item.admitted_artifact_id],
            artifact_kind=ARTIFACT_KINDS[item.admitted_artifact_id],
            label=item.path.name,
            evidence_role=EVIDENCE_ROLES[item.admitted_artifact_id],
            visibility_state=VISIBILITY[item.admitted_artifact_id],
        )
        if item.path.suffix.lower() == ".json":
            structured_artifacts[common["source_artifact_id"]] = SourceArtifactStructured(data=json.loads(item.path.read_text(encoding="utf-8")), **common)
        else:
            text_artifacts[common["source_artifact_id"]] = SourceArtifactText(text=item.path.read_text(encoding="utf-8"), **common)
    refs_doc = load_rich_recap_source_span_refs()
    refs = tuple(source_span_ref_from_dict(ref) for ref in refs_doc["source_span_refs"])  # type: ignore[index]
    return text_artifacts, structured_artifacts, refs
