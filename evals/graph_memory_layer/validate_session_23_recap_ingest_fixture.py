from __future__ import annotations
import json
from dataclasses import asdict
from .session_23_recap_ingest_fixture import *

READY = ["manifest","raw recap source","explicit path boundary","existing recap helper import","normalized recap assembly","expected normalized recap fixture","frontmatter/session metadata","paragraph index","source line provenance","source span seed refs","source evidence openability","source evidence highlightability","expected phrase checks","no heading-only evidence refs","no full raw source leakage","no absolute path leakage","no corpus mutation","no graph output","no extraction/LLM output","no adapter/plan/agent/runtime leakage","session 23 recap ingest fixture"]

def _assert_frontmatter(text: str) -> None:
    required = ['title: "Session 23 - Mireward Gate Battle"','document_class: play','canon_layer: campaign','campaign_id: longmont-c2','temporal_scope: session_specific','session: 23','origin_session: 23','last_updated_session: 23','source_class: observed_session_recap','# Session 23 Recap']
    for r in required: assert r in text, r

def validate_all() -> None:
    manifest = load_manifest(); validate_manifest(manifest)
    raw = load_raw_recap(manifest); assert "Session 23 Recap" in raw and raw.strip()
    normalized, report = assemble_session_23_normalized_recap(raw)
    assert report.title_line_stripped and report.paragraph_count_out >= 10 and not report.duplicates_removed
    assert normalized == load_expected_normalized_recap(); _assert_frontmatter(normalized)
    idx = build_paragraph_index(raw); assert idx == load_expected_paragraph_index()
    prev = 0
    for p in idx["paragraphs"]:
        assert p["source_line_start"] <= p["source_line_end"] and p["source_line_start"] > prev
        assert len(p["preview"]) <= 160; prev = p["source_line_end"]
    seed = load_source_span_seed_refs(); assert seed["schema"] == SOURCE_SPAN_SEED_SCHEMA and seed["version"] == "0.1"
    refs = seed["source_span_refs"]; assert len(refs) >= seed["expected"]["total_refs_min"] >= 12
    anchors = [r["source_anchor_id"] for r in refs]; assert len(anchors) == len(set(anchors))
    resolved = resolve_source_span_seed_refs(); assert len(resolved) == len(refs)
    by_anchor = {r["source_anchor_id"]: r for r in refs}
    for ev in resolved:
        assert ev.can_open_source and ev.can_highlight_span and ev.preview_snippet and not ev.warnings
        assert not ev.preview_snippet.strip().startswith("#")
        assert len(ev.preview_snippet) <= 240 and (ev.surrounding_context is None or len(ev.surrounding_context) <= 500)
        assert by_anchor[ev.source_anchor_id]["expected_phrase"] in ev.preview_snippet
    serialized = json.dumps([asdict(r) for r in resolved], ensure_ascii=False)
    assert raw not in serialized and str(repo_root()) not in serialized
    text = json.dumps(seed) + json.dumps(idx) + serialized
    for token in ('"nodes"','"edges"','"proposed_writes"','gold_graph','llm_generated','"approved"','"promoted"','/plan','agent_interaction','runtime_ui','query_execution','corpus_mutation'):
        assert token not in text

def main() -> int:
    validate_all()
    print("Graph Memory Session 23 recap ingest fixture validation")
    for item in READY: print(f"- {item}: ready")
    return 0
if __name__ == "__main__": raise SystemExit(main())
