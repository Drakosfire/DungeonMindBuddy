from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.mirathorn_city_world_doc_fixture import *


def test_manifest_and_source_boundary():
    manifest = load_manifest()
    validate_manifest(manifest)
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["version"] == MANIFEST_VERSION
    assert manifest["fixture_id"] == FIXTURE_ID
    assert manifest["campaign_id"] is None and manifest["session"] is None
    assert manifest["input_mode"] == "explicit_path_only"
    assert manifest["source_doc_path"] == SOURCE_DOC_REL
    assert not Path(SOURCE_DOC_REL).is_absolute() and ".." not in Path(SOURCE_DOC_REL).parts
    assert source_doc_path(manifest).is_file()
    for key in DANGEROUS_FLAGS:
        assert manifest["diagnostics"][key] is False


def test_source_doc_content():
    source = load_source_doc()
    assert source.strip() and "Mirathorn" in source and len(source.splitlines()) >= 100
    for phrase in [
        "The Elderwyld",
        "Lundayell Empire",
        "Stormspire Academy",
        "Shepherd's Flock",
        "Wizard's Tower Brewing Co",
        "Mayor Elara Swiftwind",
        "Headmaster Tinkerbright",
        "Nameless Goddess",
    ]:
        assert phrase in source


def test_source_span_seed_refs_resolve_meaningfully():
    seed = load_source_span_seed_refs()
    assert seed["schema"] == SOURCE_SPAN_SEED_SCHEMA and seed["version"] == "0.1"
    refs = seed["source_span_refs"]
    assert len(refs) >= 22
    anchors = [r["source_anchor_id"] for r in refs]
    assert len(anchors) == len(set(anchors))
    resolved = resolve_source_span_seed_refs()
    assert len(resolved) == len(refs)
    by_anchor = {r["source_anchor_id"]: r for r in refs}
    for ev in resolved:
        assert ev.can_open_source and ev.can_highlight_span
        assert by_anchor[ev.source_anchor_id]["expected_phrase"] in ev.preview_snippet
        assert not ev.preview_snippet.strip().startswith("#")
        assert len(ev.preview_snippet) <= 240
    assert load_source_doc() not in json.dumps(resolved_to_serializable(resolved), ensure_ascii=False)


def test_fixture_json_has_no_graph_or_runtime_payloads():
    fixture = fixture_dir()
    assert not any("candidate" in p.name and "graph" in p.name for p in fixture.iterdir())
    forbidden_keys = {
        "nodes",
        "edges",
        "proposed_writes",
        "gold_graph",
        "llm_generated",
        "approved",
        "promoted",
        "plan_payload",
        "agent_interaction_payload",
        "runtime_ui_payload",
        "query_execution",
        "corpus_mutation",
    }

    def walk(value):
        if isinstance(value, dict):
            assert not (forbidden_keys & set(value))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for path in fixture.glob("*.json"):
        data = json.loads(path.read_text())
        walk(data)


def test_validator_and_report_cli():
    validator = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_mirathorn_city_world_doc_fixture"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "mirathorn city world doc fixture: ready" in validator.stdout
    report = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.report_mirathorn_city_world_doc_fixture"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "## Source Span Seeds" in report.stdout and "Snippet Preview" in report.stdout
    assert "It does not call an LLM." in report.stdout
