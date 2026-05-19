from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import load_beat_question_targets
from evals.c1s4_preplanning_vertical_slice.campaign_corpus_materializer import load_campaign_corpus_records_for_c1s4
from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import DEFAULT_POLICY_PATH, load_kb_manifest
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import _retrieve
from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import load_normalized_support_records
from src.agent.session_memory_query import query_session_memory_candidate


def _combined_records(mode: str) -> list[dict]:
    _, session_records = load_kb_manifest(DEFAULT_POLICY_PATH)
    combined = list(session_records) + load_campaign_corpus_records_for_c1s4()
    if mode == "prior_plus_support_content_only":
        combined.extend(load_normalized_support_records(retrieval_mode="content_only"))
    return combined


def test_step2_combined_universe_includes_campaign_corpus_records() -> None:
    combined = _combined_records("prior_only")
    paths = {str(r.get("source_path") or r.get("source_recap_path") or "") for r in combined}
    assert any("NPCs/pippa/README.md" in p for p in paths)
    assert any("Locations/stone_bridge/README.md" in p for p in paths)


def test_q1_direct_query_retrieves_npc_materialized_records() -> None:
    records = _combined_records("prior_only")
    targets = load_beat_question_targets()
    q1 = next(q for q in targets["beats"][0]["questions"] if q["question_number"] == 1)
    hits = query_session_memory_candidate(
        records=records,
        query=str(q1["question"]),
        campaign_id="longmont-c1",
        session_min=0,
        session_max=3,
        max_hits=50,
    ).hits
    refs = " ".join(str(h.get("source_recap_path") or h.get("unit_id") or "") for h in hits).lower()
    assert "pippa" in refs or "bubbles" in refs or "grishna" in refs


def test_q3_direct_query_retrieves_session_and_location_records() -> None:
    records = _combined_records("prior_only")
    targets = load_beat_question_targets()
    q3 = next(q for q in targets["beats"][0]["questions"] if q["question_number"] == 3)
    hits = query_session_memory_candidate(
        records=records,
        query=str(q3["question"]),
        campaign_id="longmont-c1",
        session_min=0,
        session_max=3,
        max_hits=50,
    ).hits
    refs = " ".join(str(h.get("source_recap_path") or h.get("unit_id") or "") for h in hits).lower()
    assert "session 3" in refs or "stone_bridge" in refs or "mirathorn" in refs


def test_q5_support_path_retrieves_hempholm_tree_support_card() -> None:
    records = _combined_records("prior_plus_support_content_only")
    hits = query_session_memory_candidate(
        records=records,
        query="Hempholm visible threat giant tree",
        campaign_id="longmont-c1",
        session_min=0,
        session_max=3,
        max_hits=50,
    ).hits
    assert any(str(h.get("unit_id") or "") == "support:hempholm_tree_visible_threat" for h in hits)


def test_support_bundle_preserves_support_card_hits() -> None:
    support_record = next(
        r for r in load_normalized_support_records(retrieval_mode="content_only") if r["unit_id"] == "support:hempholm_tree_visible_threat"
    )
    unit_id = str(support_record["unit_id"])
    bundle = build_preplanning_context_bundle(
        kb_id="test",
        campaign_id="longmont-c1",
        allowed_sessions=[1, 2, 3],
        heldout_sessions=[4],
        query="gigantic tree growing in hemp",
        retrieval_result={"hits": [{"unit_id": unit_id, "routes": [], "why_matched": ["lexical_token:hempholm"]}]},
        forbidden_oracle_relpaths=[],
        records_by_unit_id={unit_id: support_record},
        max_items=50,
    )
    unit_ids = {str(i.get("unit_id") or "") for i in bundle["items"]}
    assert unit_id in unit_ids


def test_step2_retrieve_includes_materialized_pippa_for_q1() -> None:
    targets = load_beat_question_targets()
    q1 = next(q for q in targets["beats"][0]["questions"] if q["question_number"] == 1)
    items, _leak = _retrieve(str(q1["question"]), "prior_only", "longmont-c1", max_hits=50)
    refs = " ".join(str(i.get("source_path") or i.get("source_recap_path") or i.get("unit_id") or "") for i in items).lower()
    assert "pippa" in refs
