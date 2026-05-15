from evals.c1s4_preplanning_vertical_slice.step1b_prior_plus_support_context import run_step1b
from src.agent.session_memory_query import query_session_memory_candidate


def test_support_retrieval_does_not_use_usable_for_questions():
    records = [
        {"campaign_id": "longmont-c1", "session_number": 1, "unit_id": "support:fake_bad_card", "lexical_plain": "Completely unrelated pastry inventory. A list of pies jam spoons and bakery gossip.", "routes": []},
        {"campaign_id": "longmont-c1", "session_number": 1, "unit_id": "support:tree", "lexical_plain": "Magical tree threat near rural village with grotesque branches.", "routes": []},
    ]
    out = query_session_memory_candidate(records=records, query="How should the road merchant describe the strange magical tree near the village?", campaign_id="longmont-c1", session_min=1, session_max=3, max_hits=3)
    assert out.hits
    assert out.hits[0]["unit_id"] != "support:fake_bad_card"


def test_support_retrieval_can_find_relevant_card_without_question_id():
    out = run_step1b(mode="content_plus_lexical_hints")
    tree_bundle = next(x["bundle"] for x in out["bundles"] if x["query_id"] == "visible_tree_threat")
    ids = [i["unit_id"] for i in tree_bundle["items"]]
    assert any("hempholm_tree_visible_threat" in i or "hempholm_tree_mechanics_and_clues" in i for i in ids)


def test_prior_plus_support_preserves_oracle_boundary_and_authority():
    out = run_step1b(mode="content_only")
    assert out["oracle_leakage_check"]["forbidden_path_hits"] == []
    assert out["oracle_leakage_check"]["forbidden_session_hits"] == []
    for b in out["bundles"]:
        for item in b["bundle"]["items"]:
            assert "session 4" not in str(item).lower()
            if item.get("source_kind") == "support_knowledge_card":
                for k in ["source_layer", "authority_role", "canon_status", "source_reference"]:
                    assert k in item


def test_content_only_and_lexical_hint_modes_report_separately():
    a = run_step1b(mode="content_only")
    b = run_step1b(mode="content_plus_lexical_hints")
    for out in [a, b]:
        for k in ["retrieval_mode", "record_counts", "support_records_by_source_layer", "bundles"]:
            assert k in out
    assert a["retrieval_mode"] != b["retrieval_mode"]
