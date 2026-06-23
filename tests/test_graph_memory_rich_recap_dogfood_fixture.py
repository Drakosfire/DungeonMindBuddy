from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.rich_recap_dogfood import (
    FIXTURE_ID,
    build_rich_recap_materializer_inputs,
    build_rich_recap_source_span_registries,
    load_rich_recap_manifest,
    load_rich_recap_requirements,
    load_rich_recap_source_span_refs,
    rich_recap_fixture_dir,
    validate_rich_recap_manifest,
)
from src.graph_memory.recap_ingestion_materialize import materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import KNOWN_ARTIFACT_FAMILIES, analyze_recap_ingestion_materializer_output
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness
from src.graph_memory.source_span import DEFAULT_CONTEXT_MAX_CHARS, DEFAULT_SNIPPET_MAX_CHARS, resolve_many_source_span_refs


def test_rich_recap_cli_commands_exit_zero() -> None:
    for module in (
        "evals.graph_memory_layer.validate_rich_recap_dogfood_fixture",
        "evals.graph_memory_layer.report_rich_recap_dogfood_fixture",
    ):
        result = subprocess.run([sys.executable, "-m", module], check=False, text=True, capture_output=True)
        assert result.returncode == 0, result.stderr


def test_fixture_manifest_explicit_inputs() -> None:
    fixture_dir = rich_recap_fixture_dir()
    assert fixture_dir.is_dir()
    manifest_path = fixture_dir / "rich_recap_manifest.json"
    assert manifest_path.is_file()
    manifest = load_rich_recap_manifest()
    validate_rich_recap_manifest(manifest)
    assert manifest["schema"] == "dmb_rich_recap_dogfood_manifest_v0"
    assert manifest["version"] == "0.1"
    assert manifest["source_family"] == "recap_ingestion_source_artifacts"
    assert manifest["input_mode"] == "explicit_paths_only"
    artifact_inputs = manifest["artifact_inputs"]
    assert {item["admitted_artifact_id"] for item in artifact_inputs} == KNOWN_ARTIFACT_FAMILIES
    for item in artifact_inputs:
        rel = Path(item["relative_path"])
        assert not rel.is_absolute()
        assert ".." not in rel.parts
        assert (fixture_dir / rel).is_file()


def test_declared_richness_meets_minimums() -> None:
    req_path = rich_recap_fixture_dir() / "dogfood_requirements.json"
    assert req_path.is_file()
    req = load_rich_recap_requirements()
    assert req["schema"] == "dmb_rich_recap_dogfood_requirements_v0"
    assert req["version"] == "0.1"
    mins = req["minimum_requirements"]
    declared = req["declared_contents"]
    for key, minimum in mins.items():
        declared_key = "unnamed_important_concepts" if key == "unnamed_important_relationship_opportunities" else key
        values = declared[declared_key]
        assert len(values) >= minimum, key


def test_materializer_report_and_readiness_are_ready() -> None:
    inputs = build_rich_recap_materializer_inputs()
    assert len(inputs) == 5
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    assert len(materialization.artifacts) == 5
    assert len(materialization.units) == 5
    report = analyze_recap_ingestion_materializer_output(materialization)
    assert report.total_source_refs == 5
    readiness = assess_recap_ingestion_projection_readiness(materialization, report)
    assert readiness.readiness_status == "ready"
    for unit in materialization.units:
        assert all(p["source_ref_id"] == unit.source_ref["source_ref_id"] for p in unit.provenance)


def test_source_span_refs_resolve_and_cover_required_categories() -> None:
    refs_path = rich_recap_fixture_dir() / "source_span_refs.json"
    assert refs_path.is_file()
    refs_doc = load_rich_recap_source_span_refs()
    assert refs_doc["schema"] == "dmb_rich_recap_source_span_refs_v0"
    assert refs_doc["version"] == "0.1"
    refs_raw = refs_doc["source_span_refs"]
    assert len(refs_raw) >= 12
    assert sum(1 for r in refs_raw if r.get("start_line") is not None) >= 8
    assert sum(1 for r in refs_raw if r.get("structured_path")) >= 2
    text_artifacts, structured_artifacts, refs = build_rich_recap_source_span_registries()
    resolved = resolve_many_source_span_refs(refs, text_artifacts=text_artifacts, structured_artifacts=structured_artifacts)
    assert all(r.can_open_source for r in resolved)
    assert all(r.can_highlight_span for r in resolved)
    assert all(len(r.preview_snippet) <= DEFAULT_SNIPPET_MAX_CHARS for r in resolved)
    assert all(r.surrounding_context is None or len(r.surrounding_context) <= DEFAULT_CONTEXT_MAX_CHARS for r in resolved)
    labels = "\n".join(r["label"].lower() for r in refs_raw)
    assert "open unresolved" in labels
    assert "ignored table noise" in labels
    assert "archive search clue" in labels
    assert "gm-private" in labels


def test_structured_fixture_json_has_no_graph_or_promotion_outputs() -> None:
    forbidden = {"nodes", "edges", "proposed_writes", "candidate_graph_preview", "gold_graph", "llm_generated", "approved", "promoted"}
    for path in rich_recap_fixture_dir().glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        keys: list[str] = []
        def walk(value):
            if isinstance(value, dict):
                keys.extend(value.keys())
                for nested in value.values(): walk(nested)
            elif isinstance(value, list):
                for nested in value: walk(nested)
        walk(data)
        assert not (set(keys) & forbidden), path
