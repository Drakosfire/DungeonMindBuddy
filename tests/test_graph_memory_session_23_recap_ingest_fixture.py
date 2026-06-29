from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

from evals.graph_memory_layer.session_23_recap_ingest_fixture import *


def test_manifest_and_raw_boundary():
    manifest = load_manifest(); validate_manifest(manifest)
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["version"] == MANIFEST_VERSION
    assert manifest["fixture_id"] == FIXTURE_ID
    assert manifest["session"] == 23 and manifest["campaign_id"] == "longmont-c2"
    assert manifest["input_mode"] == "explicit_path_only"
    assert manifest["raw_recap_path"] == RAW_RECAP_REL
    assert not Path(RAW_RECAP_REL).is_absolute() and ".." not in Path(RAW_RECAP_REL).parts
    assert raw_recap_path(manifest).is_file()
    assert Path(RAW_RECAP_REL).parts[0] != "corpus"
    for key in DANGEROUS_FLAGS:
        assert manifest["diagnostics"][key] is False


def test_raw_recap_content():
    raw = load_raw_recap()
    assert raw.strip() and "Session 23 Recap" in raw and len(raw.splitlines()) >= 10
    for phrase in ["Lysandra is surprised to see her father", "message from Edge", "Orik Tane", "Brin Holloway", "Hunger of Hadar", "Commanding Shout", "Hunter’s Mark", "lightning bolt"]:
        assert phrase in raw


def test_normalized_recap_and_paragraph_index_match_helper():
    raw = load_raw_recap(); normalized, report = assemble_session_23_normalized_recap(raw)
    assert report.title_line_stripped and report.paragraph_count_out == 13
    assert "Session 23 Recap\n\nSession 23 Recap" not in normalized
    for field in ['title: "Session 23 - Mireward Gate Battle"','document_class: play','canon_layer: campaign','campaign_id: longmont-c2','temporal_scope: session_specific','session: 23','origin_session: 23','last_updated_session: 23','source_class: observed_session_recap','# Session 23 Recap']:
        assert field in normalized
    assert load_expected_normalized_recap() == normalized
    index = load_expected_paragraph_index(); generated = build_paragraph_index(raw)
    assert index == generated
    assert index["schema"] == PARAGRAPH_INDEX_SCHEMA and index["version"] == "0.1"
    ids = [p["paragraph_id"] for p in index["paragraphs"]]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    prev = 0
    for p in index["paragraphs"]:
        assert 0 < p["source_line_start"] <= p["source_line_end"]
        assert p["source_line_start"] > prev; prev = p["source_line_end"]
        assert len(p["preview"]) <= 160
    assert raw not in json.dumps(index, ensure_ascii=False)


def test_source_span_seed_refs_resolve_meaningfully():
    seed = load_source_span_seed_refs()
    assert seed["schema"] == SOURCE_SPAN_SEED_SCHEMA and seed["version"] == "0.1"
    refs = seed["source_span_refs"]; assert len(refs) >= 12
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
    assert load_raw_recap() not in json.dumps(resolved_to_serializable(resolved), ensure_ascii=False)


def test_fixture_json_has_no_graph_or_runtime_payloads():
    fixture = fixture_dir()
    assert not any("candidate" in p.name and "graph" in p.name for p in fixture.iterdir())
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
        text = json.dumps(data)
        walk(data)
        for token in ("/_normalized", "/_breadcrumbed", ".records_meta.jsonl"):
            assert token not in text


def test_validator_and_report_cli():
    validator = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_session_23_recap_ingest_fixture"], text=True, capture_output=True, check=True)
    assert "session 23 recap ingest fixture: ready" in validator.stdout
    report = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_session_23_recap_ingest_fixture"], text=True, capture_output=True, check=True)
    assert "## Source Span Seeds" in report.stdout and "Snippet Preview" in report.stdout
    assert "It does not call an LLM." in report.stdout
