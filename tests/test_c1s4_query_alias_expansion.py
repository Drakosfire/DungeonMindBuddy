from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.beat_question_answer_harness import load_beat_question_targets, iter_target_questions
from evals.c1s4_preplanning_vertical_slice.query_alias_expansion import (
    FORBIDDEN_QUERY_SUBSTRINGS,
    build_step2c_query_variants,
    query_variant_forbidden_tokens,
)


def _q1_text() -> str:
    targets = load_beat_question_targets()
    return str(next(q for q in iter_target_questions(targets) if q["question_number"] == 1)["question"])


def _q3_text() -> str:
    targets = load_beat_question_targets()
    return str(next(q for q in iter_target_questions(targets) if q["question_number"] == 3)["question"])


def _q5_text() -> str:
    targets = load_beat_question_targets()
    return str(next(q for q in iter_target_questions(targets) if q["question_number"] == 5)["question"])


def test_literal_question_is_always_first_variant() -> None:
    variants = build_step2c_query_variants(question_text=_q1_text(), retrieval_mode="prior_only")
    assert variants[0]["variant_role"] == "literal_question"
    assert variants[0]["query"] == _q1_text()


def test_q5_support_mode_generates_hempholm_tree_support_aliases() -> None:
    variants = build_step2c_query_variants(
        question_text=_q5_text(),
        retrieval_mode="prior_plus_support_content_only",
    )
    roles = {v["variant_role"] for v in variants}
    assert "support_alias" in roles
    queries = " ".join(v["query"] for v in variants).lower()
    assert "hempholm visible threat giant tree" in queries
    assert "support hempholm tree visible threat" in queries


def test_q5_prior_only_does_not_generate_support_only_aliases() -> None:
    variants = build_step2c_query_variants(question_text=_q5_text(), retrieval_mode="prior_only")
    assert all(v["variant_role"] != "support_alias" for v in variants)


def test_q5_support_mode_does_not_generate_npc_aliases_from_metallic_substring() -> None:
    variants = build_step2c_query_variants(
        question_text=_q5_text(),
        retrieval_mode="prior_plus_support_content_only",
    )
    assert all(v["variant_role"] != "npc_target_alias" for v in variants)


def test_q1_broad_npc_question_generates_pr58_target_npc_aliases() -> None:
    variants = build_step2c_query_variants(question_text=_q1_text(), retrieval_mode="prior_only")
    roles = {v["variant_role"] for v in variants}
    assert "npc_target_alias" in roles
    queries = " ".join(v["query"] for v in variants).lower()
    assert "grishna" in queries
    assert "pippa" in queries
    assert "bubbles" in queries


def test_q3_route_distance_question_generates_stone_bridge_mirathorn_aliases() -> None:
    variants = build_step2c_query_variants(question_text=_q3_text(), retrieval_mode="prior_only")
    roles = {v["variant_role"] for v in variants}
    assert "route_distance_alias" in roles
    queries = " ".join(v["query"] for v in variants).lower()
    assert "mirathorn" in queries
    assert "stone bridge" in queries


def test_query_variants_are_deterministic_and_deduped() -> None:
    first = build_step2c_query_variants(question_text=_q1_text(), retrieval_mode="prior_only")
    second = build_step2c_query_variants(question_text=_q1_text(), retrieval_mode="prior_only")
    assert first == second
    queries = [v["query"] for v in first]
    assert len(queries) == len(set(q.lower() for q in queries))


def test_query_variants_do_not_include_forbidden_oracle_tokens() -> None:
    for mode in ("prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"):
        for qn in (1, 3, 5):
            targets = load_beat_question_targets()
            question = str(next(q for q in iter_target_questions(targets) if q["question_number"] == qn)["question"])
            for variant in build_step2c_query_variants(question_text=question, retrieval_mode=mode):
                assert not query_variant_forbidden_tokens(variant["query"]), variant
    for token in FORBIDDEN_QUERY_SUBSTRINGS:
        assert query_variant_forbidden_tokens(f"probe {token} probe")
