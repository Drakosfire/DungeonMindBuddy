from __future__ import annotations

import pytest

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import load_beat_question_targets, iter_target_questions
from evals.c1s4_preplanning_vertical_slice.campaign_corpus_materializer import load_campaign_corpus_records_for_c1s4
from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import DEFAULT_POLICY_PATH, load_kb_manifest
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import _retrieve, build_summary
from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import load_normalized_support_records
from src.agent.session_memory_query import query_session_memory_candidate


def _combined_records(mode: str) -> list[dict]:
    _, session_records = load_kb_manifest(DEFAULT_POLICY_PATH)
    combined = list(session_records) + load_campaign_corpus_records_for_c1s4()
    if mode == "prior_plus_support_content_only":
        combined.extend(load_normalized_support_records(retrieval_mode="content_only"))
    return combined


def _probe_hits(*, records: list[dict], query: str) -> list[dict]:
    return list(
        query_session_memory_candidate(
            records=records,
            query=query,
            campaign_id="longmont-c1",
            session_min=0,
            session_max=3,
            max_hits=50,
        ).hits
    )


def _refs(hits: list[dict]) -> str:
    return " ".join(str(h.get("source_recap_path") or h.get("unit_id") or "") for h in hits).lower()


def test_step2_combined_universe_includes_campaign_corpus_records() -> None:
    combined = _combined_records("prior_only")
    paths = {str(r.get("source_path") or r.get("source_recap_path") or "") for r in combined}
    assert any("NPCs/pippa/README.md" in p for p in paths)
    assert any("Locations/stone_bridge/README.md" in p for p in paths)


@pytest.mark.parametrize(
    ("needle", "query"),
    [
        ("pippa", "Pippa Goldwhistle"),
        ("bubbles_the_float_goat", "Bubbles Float Goat"),
        ("grishna", "Grishna River's Edge Pub"),
    ],
)
def test_q1_direct_probe_retrieves_each_npc_family(needle: str, query: str) -> None:
    hits = _probe_hits(records=_combined_records("prior_only"), query=query)
    assert needle in _refs(hits)


@pytest.mark.parametrize(
    ("needle", "query"),
    [
        ("session 3 - the stone bridge flood.md", "Mirathorn week on foot"),
        ("stone_bridge", "Stone Bridge Mirathorn"),
    ],
)
def test_q3_direct_probe_retrieves_session_recap_and_stone_bridge(needle: str, query: str) -> None:
    hits = _probe_hits(records=_combined_records("prior_only"), query=query)
    assert needle in _refs(hits)


def test_q5_support_direct_probe_retrieves_hempholm_tree_support_card() -> None:
    hits = _probe_hits(
        records=_combined_records("prior_plus_support_content_only"),
        query="Hempholm visible threat giant tree",
    )
    assert any(str(h.get("unit_id") or "") == "support:hempholm_tree_visible_threat" for h in hits)


def test_q5_actual_question_candidate_context_includes_support_card_in_support_modes() -> None:
    targets = load_beat_question_targets()
    q5 = next(q for q in iter_target_questions(targets) if q["question_number"] == 5)
    for mode in ("prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"):
        items, _leak, _diag = _retrieve(str(q5["question"]), mode, "longmont-c1", max_hits=50)
        unit_ids = {str(i.get("unit_id") or "") for i in items}
        assert "support:hempholm_tree_visible_threat" in unit_ids


def test_q5_actual_question_prior_only_does_not_include_support_card() -> None:
    targets = load_beat_question_targets()
    q5 = next(q for q in iter_target_questions(targets) if q["question_number"] == 5)
    items, _leak, _diag = _retrieve(str(q5["question"]), "prior_only", "longmont-c1", max_hits=50)
    unit_ids = {str(i.get("unit_id") or "") for i in items}
    assert "support:hempholm_tree_visible_threat" not in unit_ids


def test_q1_actual_question_candidate_context_includes_grishna_after_alias_expansion() -> None:
    targets = load_beat_question_targets()
    q1 = next(q for q in iter_target_questions(targets) if q["question_number"] == 1)
    items, _leak, _diag = _retrieve(str(q1["question"]), "prior_only", "longmont-c1", max_hits=50)
    refs = " ".join(str(i.get("source_path") or i.get("source_recap_path") or i.get("unit_id") or "") for i in items).lower()
    assert "grishna" in refs


def test_q1_grishna_actual_packet_still_documents_candidate_pool_gap_after_pr60() -> None:
    targets = load_beat_question_targets()
    q1 = next(q for q in iter_target_questions(targets) if q["question_number"] == 1)

    summary = build_summary(mode="prior_only", question_number=1, max_hits=50)
    packet = summary["packets"][0]
    assert str(packet.get("question_id") or "") == str(q1.get("question_id") or "")

    candidate_context = packet.get("candidate_context") or []
    admitted_context = packet.get("admitted_context") or []

    admittable_grishna_candidates = [
        i
        for i in candidate_context
        if "/npcs/grishna/" in str(i.get("source_path") or "").lower()
        and str(i.get("evidence_role") or "") == "evidence"
    ]

    admitted_grishna = [
        i for i in admitted_context if "/npcs/grishna/" in str(i.get("source_path") or "").lower()
    ]

    assert admittable_grishna_candidates == []
    assert admitted_grishna == []

    diag = packet.get("admission_preservation_diagnostics") or {}
    assert diag.get("schema") == "dmb_admission_preservation_diagnostics_v1"


def test_q3_actual_question_candidate_context_includes_stone_bridge_after_alias_expansion() -> None:
    targets = load_beat_question_targets()
    q3 = next(q for q in iter_target_questions(targets) if q["question_number"] == 3)
    items, _leak, _diag = _retrieve(str(q3["question"]), "prior_only", "longmont-c1", max_hits=50)
    refs = " ".join(str(i.get("source_path") or i.get("source_recap_path") or i.get("unit_id") or "") for i in items).lower()
    assert "stone_bridge" in refs or "stone bridge" in refs


def test_step2_packet_includes_query_variant_diagnostics() -> None:
    summary = build_summary(mode="prior_plus_support_content_only", question_number=5, max_hits=50)
    packet = summary["packets"][0]
    diag = packet.get("query_variant_diagnostics") or {}
    assert diag.get("variant_count", 0) >= 2
    assert isinstance(diag.get("variants"), list)
    assert diag.get("retrieval_merge_policy")
    assert isinstance(diag.get("variant_hit_counts"), list)



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
    q1 = next(q for q in iter_target_questions(targets) if q["question_number"] == 1)
    items, _leak, _diag = _retrieve(str(q1["question"]), "prior_only", "longmont-c1", max_hits=50)
    refs = " ".join(str(i.get("source_path") or i.get("source_recap_path") or i.get("unit_id") or "") for i in items).lower()
    assert "pippa" in refs
