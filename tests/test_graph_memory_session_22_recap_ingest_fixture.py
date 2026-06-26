from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.session_22_recap_ingest_fixture import *


def test_manifest_and_source_boundary() -> None:
    manifest = load_manifest()
    validate_manifest(manifest)
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["version"] == MANIFEST_VERSION
    assert manifest["fixture_id"] == FIXTURE_ID
    assert manifest["session"] == 22 and manifest["campaign_id"] == "longmont-c2"
    assert manifest["input_mode"] == "explicit_normalized_corpus_path"
    assert manifest["normalized_recap_path"] == NORMALIZED_RECAP_REL
    assert not Path(NORMALIZED_RECAP_REL).is_absolute()
    assert ".." not in Path(NORMALIZED_RECAP_REL).parts
    assert normalized_recap_path(manifest).is_file()
    for key in DANGEROUS_FLAGS:
        assert manifest["diagnostics"][key] is False


def test_normalized_recap_content() -> None:
    text = load_normalized_recap()
    assert text.strip() and "Session 22 Recap" in text and len(text.splitlines()) >= 40
    for phrase in ["Private Hester", "Commander Vale", "Grobnok took the rockie-talkie", "Dustwalker perform at the festival", "father Lysandro"]:
        assert phrase in text


def test_source_span_seed_refs_resolve_meaningfully() -> None:
    seed = load_source_span_seed_refs()
    assert seed["schema"] == SOURCE_SPAN_SEED_SCHEMA and seed["version"] == "0.1"
    refs = seed["source_span_refs"]
    assert len(refs) >= 18
    anchors = [ref["source_anchor_id"] for ref in refs]
    assert len(anchors) == len(set(anchors))
    resolved = resolve_source_span_seed_refs()
    assert len(resolved) == len(refs)
    by_anchor = {ref["source_anchor_id"]: ref for ref in refs}
    for item in resolved:
        assert item.can_open_source and item.can_highlight_span
        assert by_anchor[item.source_anchor_id]["expected_phrase"] in item.preview_snippet
        assert not item.preview_snippet.strip().startswith("#")
        assert len(item.preview_snippet) <= 240
        assert not item.warnings
    assert load_normalized_recap() not in json.dumps(resolved_to_serializable(resolved), ensure_ascii=False)


def test_fixture_json_has_no_graph_or_runtime_payloads() -> None:
    fixture = fixture_dir()
    forbidden_keys = {"nodes", "edges", "proposed_writes", "gold_graph", "llm_generated", "approved", "promoted", "plan_payload", "agent_interaction_payload", "runtime_ui_payload", "query_execution", "corpus_mutation"}

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


def test_validator_cli_via_candidate_gold_dependency() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_session_22_candidate_graph_gold_fixture"], text=True, capture_output=True, check=True)
    assert "session 22 recap ingest dependency: ready" in result.stdout
