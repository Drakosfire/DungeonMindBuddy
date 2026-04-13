"""Unit tests for exemplar / keyword benchmark helpers (no live embedding)."""

from __future__ import annotations

from evals.planner_slice.planner_answer_benchmark import (
    build_citation_grounding,
    build_quality_summary,
    instrument_planner_answer,
    load_manifest,
    manifest_row,
    score_concept_coverage,
    score_keyword_coverage,
    score_single_phrase_concept,
)


def test_score_keyword_coverage_case_insensitive() -> None:
    r = score_keyword_coverage("The ASPITOME ceremony and stories.", ["aspitome", "missing_phrase", ""])
    assert r["present"] == ["aspitome"]
    assert r["missing"] == ["missing_phrase"]
    assert r["fraction"] == 0.5


def test_score_keyword_coverage_empty_keywords() -> None:
    r = score_keyword_coverage("anything", [])
    assert r["fraction"] == 1.0
    assert r["keyword_count"] == 0


def test_load_manifest_has_benchmark_scenarios() -> None:
    m = load_manifest()
    assert m is not None
    assert m.get("embedding_model_id")
    ids = {str(r.get("scenario_id", "")) for r in (m.get("scenarios") or [])}
    for sid in (
        "live_festival_aspitome_ceremony_detail",
        "live_festival_tindlewix_illusionist_detail",
        "live_mirathorn_main_gate_detail",
        "live_migrating_forest_branchbound_plan",
    ):
        assert sid in ids
        row = manifest_row(m, sid)
        assert row is not None
        assert row.get("exemplar")
        assert isinstance(row.get("critical_keywords"), list)
        assert len(row.get("critical_keywords") or []) > 5


def test_instrument_planner_answer_known_scenario() -> None:
    out = instrument_planner_answer(
        "live_festival_tindlewix_illusionist_detail",
        "Tindlewix illusionist festival prep with gnome energy.",
    )
    assert out is not None
    assert out.get("keyword_coverage")
    assert out["keyword_coverage"]["fraction"] < 1.0
    assert out.get("concept_coverage")
    assert "weighted_score" in out["concept_coverage"]
    assert out["concept_coverage"]["phrase_count"] > 0
    assert out.get("quality_summary")
    assert out["quality_summary"].get("purpose")
    assert "citation_alignment" in out["quality_summary"]


def test_build_quality_summary_citation_misaligned_on_hallucinated_cite() -> None:
    cg = {
        "read_count": 1,
        "citation_count": 2,
        "reads": ["Elderwyld/a.md"],
        "citations_in_final": ["Elderwyld/a.md", "Elderwyld/phantom.md"],
        "citations_not_grounded": ["Elderwyld/phantom.md"],
        "reads_not_mentioned_in_final": [],
    }
    qs = build_quality_summary(cg, None, None, None, exemplar_loaded=False)
    assert qs["citation_alignment"]["aligned"] is False
    assert any("hallucinated citation" in n.lower() for n in qs["notes"])


def test_build_quality_summary_reads_not_echoed_still_aligned() -> None:
    cg = {
        "read_count": 2,
        "citation_count": 1,
        "reads": ["Elderwyld/a.md", "Elderwyld/b.md"],
        "citations_in_final": ["Elderwyld/a.md"],
        "citations_not_grounded": [],
        "reads_not_mentioned_in_final": ["Elderwyld/b.md"],
    }
    qs = build_quality_summary(cg, None, None, None, exemplar_loaded=False)
    assert qs["citation_alignment"]["aligned"] is True
    assert qs["citation_alignment"]["reads_not_echoed_in_prose_count"] == 1
    assert any("not echoed" in n.lower() for n in qs["notes"])


def test_build_quality_summary_substring_vs_concept_note() -> None:
    concept = {"weighted_score": 0.9, "per_phrase": [{"phrase": "x", "score": 0.9}]}
    kw = {"fraction": 0.4, "present": [], "missing": []}
    qs = build_quality_summary(None, concept, kw, None, exemplar_loaded=True)
    assert any("substring" in n.lower() or "concept" in n.lower() for n in qs["notes"])


def test_instrument_planner_answer_includes_citation_grounding_with_trace() -> None:
    final = "Loaded `Elderwyld/Events/Foo/bar.md`."
    trace = [{"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Events/Foo/bar.md"}}]
    out = instrument_planner_answer(
        "live_festival_tindlewix_illusionist_detail",
        final,
        trace,
    )
    assert out is not None
    cg = out.get("citation_grounding")
    assert isinstance(cg, dict)
    assert cg.get("read_count") == 1
    assert cg.get("citation_count") >= 1
    assert cg.get("citations_not_grounded") == []
    assert cg.get("reads_not_mentioned_in_final") == []


def test_build_citation_grounding_dedupes_duplicate_reads_for_missing_list() -> None:
    path = "Elderwyld/Events/Foo/Schedule.md"
    trace = [
        {"tool": "read_corpus_file", "arguments": {"path": path}},
        {"tool": "read_corpus_file", "arguments": {"path": path}},
    ]
    cg = build_citation_grounding("No backticks here.", trace)
    assert cg is not None
    assert cg["read_count"] == 1
    assert cg["reads"] == [path]
    assert len(cg["reads_not_mentioned_in_final"]) == 1


def test_build_citation_grounding_hallucinated_citation() -> None:
    final = "See `Elderwyld/Other/wrong.md` for truth."
    trace = [{"tool": "read_corpus_file", "arguments": {"path": "Elderwyld/Events/Foo/bar.md"}}]
    cg = build_citation_grounding(final, trace)
    assert cg is not None
    assert cg["citations_not_grounded"]


def test_score_single_phrase_arcana_performance_split_lines() -> None:
    text = "Guests may roll **Arcana** or **Performance** to join."
    r = score_single_phrase_concept(text, "Arcana or Performance")
    assert r["bag_fraction"] == 1.0
    assert r["score"] >= 0.75


def test_score_single_phrase_shadow_moving_partial_overlap() -> None:
    r = score_single_phrase_concept("a shadow out of sync with the dancers", "shadow moving out of sync")
    assert 0.4 <= r["bag_fraction"] < 1.0


def test_score_concept_coverage_weighted() -> None:
    text = "Master Tindlewix speaks."
    r = score_concept_coverage(
        text,
        [("Master Tindlewix", 3.0), ("absent-phrase-xyz", 1.0)],
    )
    assert r["weighted_score"] < 1.0
    assert r["phrase_count"] == 2


def test_instrument_planner_answer_unknown_scenario_returns_none() -> None:
    assert instrument_planner_answer("definitely_not_a_benchmark_scenario_12345", "x") is None
