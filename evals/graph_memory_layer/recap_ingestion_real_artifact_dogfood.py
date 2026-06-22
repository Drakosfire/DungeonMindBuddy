from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.graph_memory.recap_ingestion_materialize import INPUT_MODE, SOURCE_FAMILY, RecapIngestionMaterializerInput
from src.graph_memory.recap_ingestion_materializer_report import KNOWN_ARTIFACT_FAMILIES

MANIFEST_SCHEMA = "dmb_recap_ingestion_explicit_real_artifact_dogfood_manifest_v0"
MANIFEST_VERSION = "0.1"
FIXTURE_ID = "dogfood:recap-ingestion-explicit-real-artifact:v0"


def dogfood_fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "examples" / "recap_ingestion_real_artifact_dogfood"


def load_dogfood_manifest(path: Path | None = None) -> dict[str, object]:
    manifest_path = path or dogfood_fixture_dir() / "dogfood_manifest.json"
    with manifest_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("dogfood manifest must be a JSON object")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _safe_relative_path(value: object) -> Path:
    _require(isinstance(value, str) and value, "artifact input relative_path must be a non-empty string")
    rel = Path(value)
    _require(not rel.is_absolute(), f"absolute dogfood input paths are forbidden: {value}")
    _require(".." not in rel.parts, f"parent traversal is forbidden in dogfood input path: {value}")
    _require(len(rel.parts) == 1, f"dogfood input path must be an explicit fixture-local filename: {value}")
    return rel


def validate_dogfood_manifest(manifest: dict[str, object]) -> None:
    _require(manifest.get("schema") == MANIFEST_SCHEMA, "bad dogfood manifest schema")
    _require(manifest.get("version") == MANIFEST_VERSION, "bad dogfood manifest version")
    _require(manifest.get("fixture_id") == FIXTURE_ID, "bad dogfood fixture_id")
    _require(manifest.get("source_family") == SOURCE_FAMILY, "bad dogfood source_family")
    _require(manifest.get("input_mode") == INPUT_MODE, "dogfood input_mode must be explicit_paths_only")
    artifact_inputs = manifest.get("artifact_inputs")
    _require(isinstance(artifact_inputs, list), "dogfood artifact_inputs must be a list")
    seen: set[str] = set()
    for item in artifact_inputs:
        _require(isinstance(item, dict), "dogfood artifact input must be an object")
        admitted_id = item.get("admitted_artifact_id")
        _require(isinstance(admitted_id, str) and admitted_id, "admitted_artifact_id must be a non-empty string")
        _require(admitted_id in KNOWN_ARTIFACT_FAMILIES, f"unknown admitted artifact id: {admitted_id}")
        _require(admitted_id not in seen, f"duplicate admitted artifact id: {admitted_id}")
        seen.add(admitted_id)
        _safe_relative_path(item.get("relative_path"))
    _require(seen == KNOWN_ARTIFACT_FAMILIES, "dogfood manifest must include all five admitted artifact families")


def build_dogfood_materializer_inputs(path: Path | None = None) -> list[RecapIngestionMaterializerInput]:
    manifest_path = path or dogfood_fixture_dir() / "dogfood_manifest.json"
    manifest = load_dogfood_manifest(manifest_path)
    validate_dogfood_manifest(manifest)
    base_dir = manifest_path.parent
    inputs: list[RecapIngestionMaterializerInput] = []
    for item in manifest["artifact_inputs"]:  # type: ignore[index]
        assert isinstance(item, dict)
        admitted_id = str(item["admitted_artifact_id"])
        rel = _safe_relative_path(item["relative_path"])
        resolved = base_dir / rel
        _require(resolved.exists(), f"dogfood input is missing: {rel}")
        _require(resolved.is_file(), f"dogfood input must be a file: {rel}")
        _require(not resolved.is_dir(), f"dogfood input directories are forbidden: {rel}")
        inputs.append(RecapIngestionMaterializerInput(admitted_id, resolved))
    return inputs
