from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import load_normalized_support_records


def test_support_loader_normalizes_cards():
    rows = load_normalized_support_records(retrieval_mode="content_only")
    assert any("hempholm" in r["unit_id"] for r in rows)
    assert any("elderwyld" in r["unit_id"] or "mirathorn" in r["unit_id"] for r in rows)
    row = rows[0]
    for k in ["unit_id", "source_kind", "source_layer", "authority_role", "canon_status", "lexical_plain"]:
        assert k in row
    assert row["source_kind"] == "support_knowledge_card"


def test_support_loader_separates_eval_metadata():
    row = load_normalized_support_records(retrieval_mode="content_only")[0]
    assert "usable_for_questions" in row["eval_metadata"]
    assert "usable_for_questions" not in row["lexical_plain"]
    assert "must_not_claim" not in row["lexical_plain"]
    assert "must_not_include_unless_sourced" not in row["lexical_plain"]


def test_content_only_index_excludes_retrieval_terms():
    rows = load_normalized_support_records(retrieval_mode="content_only")
    row = next(r for r in rows if r["retrieval_terms"])
    assert row["title"] in row["lexical_plain"]
    for term in row["retrieval_terms"]:
        if term.lower() not in (row["title"] + " " + row["lexical_plain"]).lower():
            assert term not in row["lexical_plain"]


def test_content_plus_lexical_hints_includes_retrieval_terms():
    rows = load_normalized_support_records(retrieval_mode="content_plus_lexical_hints")
    row = next(r for r in rows if r["retrieval_terms"])
    assert "Keywords:" in row["lexical_plain"]
    assert row["retrieval_terms"][0] in row["lexical_plain"]
