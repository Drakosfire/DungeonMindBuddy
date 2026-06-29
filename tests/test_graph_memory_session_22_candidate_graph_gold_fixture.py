from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.session_22_candidate_graph_gold_fixture import *
from evals.graph_memory_layer.session_22_recap_ingest_fixture import load_manifest, load_normalized_recap, validate_manifest
from src.graph_memory.candidate_graph_preview import COMMITTED_ACTIONS


def test_source_manifest_and_gold_manifest() -> None:
    source_manifest = load_manifest()
    validate_manifest(source_manifest)
    assert source_manifest["session"] == 22
    assert source_manifest["input_mode"] == "explicit_normalized_corpus_path"
    manifest = load_gold_manifest()
    validate_gold_manifest(manifest)
    assert manifest["schema"] == GOLD_MANIFEST_SCHEMA
    assert manifest["version"] == GOLD_MANIFEST_VERSION
    assert manifest["fixture_id"] == GOLD_FIXTURE_ID
    assert manifest["campaign_id"] == "longmont-c2" and manifest["session"] == 22
    assert manifest["source_fixture_id"] == "graph-memory:session-22-recap-ingest:v0"
    for key in ("source_manifest_path", "source_span_seed_refs_path", "candidate_graph_gold_path"):
        assert not Path(manifest[key]).is_absolute()
        assert ".." not in Path(manifest[key]).parts
    assert manifest["candidate_graph_gold_path"] == GOLD_GRAPH_PATH
    assert all(value is False for key, value in manifest["diagnostics"].items() if key != "manual_gold_fixture")


def test_parse_schema_shape_and_named_content() -> None:
    assert gold_graph_path().exists()
    preview = parse_gold_candidate_graph()
    report = validate_gold_candidate_graph()
    assert not report.issues
    assert preview.schema == "dmb_candidate_graph_preview_v0" and preview.version == "0.1" and preview.status == "preview"
    assert preview.campaign_id == "longmont-c2" and preview.session_id == "session-22"
    assert len(preview.nodes) >= 25 and len(preview.edges) >= 16 and len(preview.beats) >= 9
    assert len(preview.proposed_writes) >= 10 and len(preview.ignored_items) >= 3 and len(preview.deferred_items) >= 5
    text = json.dumps(load_gold_candidate_graph_dict(), ensure_ascii=False).lower()
    for term in [
        "private hester",
        "commander vale",
        "grobnok",
        "professor tealeaf",
        "frank",
        "sara",
        "meat heads",
        "the shepherd",
        "dustwalker",
        "lysandro",
        "delayed puddle reflections",
        "conjuration planar bleed",
        "northern rhythm / shared song",
        "abandoned meat-on-a-stick restaurant",
        "unseen knocking door",
    ]:
        assert term in text
    for forbidden in ["second wave", "approved_memory", "graph_write_result", "runtime_payload", "plan_payload", "agent_interaction_payload", '"approved"', '"promoted"']:
        assert forbidden not in text


def test_integrity_evidence_and_boundaries() -> None:
    preview = parse_gold_candidate_graph()
    node_ids = {node.node_id for node in preview.nodes}
    assert len(node_ids) == len(preview.nodes)
    assert len({edge.edge_id for edge in preview.edges}) == len(preview.edges)
    assert len({beat.beat_id for beat in preview.beats}) == len(preview.beats)
    assert len({write.write_id for write in preview.proposed_writes}) == len(preview.proposed_writes)
    assert len({item.item_id for item in preview.ignored_items} | {item.item_id for item in preview.deferred_items}) == len(preview.ignored_items) + len(preview.deferred_items)
    assert all(edge.from_node_id in node_ids and edge.to_node_id in node_ids for edge in preview.edges)
    assert all(node_id in node_ids for beat in preview.beats for node_id in beat.involved_node_ids + beat.unresolved_thread_node_ids)
    targets = node_ids | {edge.edge_id for edge in preview.edges} | {beat.beat_id for beat in preview.beats} | {item.item_id for item in preview.ignored_items} | {item.item_id for item in preview.deferred_items}
    assert all(write.target_id in targets for write in preview.proposed_writes)
    orders = [beat.order for beat in preview.beats]
    assert orders == sorted(orders) and len(set(orders)) == len(orders)
    refs = collect_gold_evidence_refs(preview)
    anchors = valid_source_anchor_ids()
    assert refs and all(ref.source_artifact_id == SOURCE_ARTIFACT_ID and ref.source_ref_id == SOURCE_REF_ID and ref.source_anchor_id in anchors for ref in refs)
    resolved = resolve_gold_evidence_refs()
    assert len(resolved) == len(refs)
    assert all(not item.warnings for item in resolved)
    assert all(item.can_open_source and item.can_highlight_span for item in resolved)
    assert all(item.preview_snippet.strip() and not item.preview_snippet.strip().startswith("#") for item in resolved)
    validate_high_risk_evidence_audit(preview)
    assert load_normalized_recap() not in json.dumps(load_gold_candidate_graph_dict(), ensure_ascii=False)


def test_semantic_boundaries_and_deferred_decisions() -> None:
    preview = parse_gold_candidate_graph()
    assert all(node.semantic_state.lifecycle_state != "promoted" for node in preview.nodes)
    assert all(edge.semantic_state.lifecycle_state != "promoted" for edge in preview.edges)
    assert all(write.status == "pending" for write in preview.proposed_writes)
    assert all(getattr(obj, "proposed_action", "create") not in COMMITTED_ACTIONS for obj in list(preview.nodes) + list(preview.edges) + list(preview.beats))
    diagnostics = preview.diagnostics
    assert diagnostics.preview_only
    assert not any([diagnostics.extraction_performed, diagnostics.llm_used, diagnostics.runtime_connected, diagnostics.plan_connected, diagnostics.agent_interaction_connected, diagnostics.corpus_scanned, diagnostics.corpus_mutated, diagnostics.facts_promoted, diagnostics.canon_promoted])
    deferred_labels = " ".join(item.label.lower() for item in preview.deferred_items)
    for term in ["commander vale", "swamp music", "planar bleed", "shimmering", "knocking", "lysandra trust"]:
        assert term in deferred_labels
    ignored_labels = " ".join(item.label.lower() for item in preview.ignored_items)
    for term in ["good berry", "puddle", "fox"]:
        assert term in ignored_labels


def test_cli_report_and_validator() -> None:
    validator = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_session_22_candidate_graph_gold_fixture"], text=True, capture_output=True, check=True)
    assert "session 22 candidate graph gold fixture: ready" in validator.stdout
    report = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_session_22_candidate_graph_gold_fixture"], text=True, capture_output=True, check=True)
    assert "## Session Outline" in report.stdout and "## Evidence Preview" in report.stdout
    assert "This is a hand-authored Session 22 Candidate Graph Preview gold fixture." in report.stdout
