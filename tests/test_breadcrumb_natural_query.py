from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    build_query_expansion,
    grade_natural_scenario,
    grade_natural_scenario_lanes,
    hits_cover_expected_routes,
    load_gold,
    natural_retrieval_bundle,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_semantic_similarity import (
    cosine_similarity,
    embedding_cost_usd,
)


def test_grade_natural_scenario_passes_on_synthetic_hit_context() -> None:
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "U-test-lysandra-001",
            "lexical_plain": "Captain Lysandra ties the voices tower clue to her sheet after the migrating forest.",
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "subject_class": "npc",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_natural",
        "campaign_id": "longmont-c2",
        "query_spec": {
            "query": "What happened to the captain after the migrating forest pulled back?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        "must_hit_tokens": ["captain", "forest"],
        "stale_tokens": [],
        "expect_route_substrings": ["captain_lysandra_ironveil"],
        "min_context_support_ratio": 0.67,
        "update_signal_tokens": [],
    }
    out = grade_natural_scenario(records=records, scenario=scenario)
    assert out["ok"] is True
    assert out["violations"] == []
    assert out["semantic_verdict"] == "pass_updated"


def test_hits_cover_expected_routes_allows_location_hierarchy_query_time_expansion() -> None:
    hits = [
        {
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                    "subject_class": "location",
                    "proposed": False,
                }
            ]
        }
    ]
    ok = hits_cover_expected_routes(
        hits,
        ["stonebridge"],
        location_hierarchy_equivalences={"stonebridge": ["rivers_edge_pub"]},
    )
    assert ok is True


def test_hits_cover_expected_routes_fails_without_hierarchy_match() -> None:
    hits = [
        {
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
                    "subject_class": "location",
                    "proposed": False,
                }
            ]
        }
    ]
    ok = hits_cover_expected_routes(hits, ["stonebridge"])
    assert ok is False


def test_grade_natural_llm_answer_bypasses_hit_context_semantic() -> None:
    """LLM path must not fail retrieval-context semantic when the answer satisfies rubric."""
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "U-test-lysandra-001",
            "lexical_plain": "Captain Lysandra ties the voices tower clue to her sheet after the migrating forest.",
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "subject_class": "npc",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_natural_llm",
        "campaign_id": "longmont-c2",
        "query_spec": {
            "query": "What happened to the captain after the migrating forest pulled back?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        "must_hit_tokens": ["captain", "forest"],
        "stale_tokens": [],
        "expect_route_substrings": ["captain_lysandra_ironveil"],
        "min_context_support_ratio": 0.67,
        "update_signal_tokens": [],
    }
    bundle = natural_retrieval_bundle(records=records, scenario=scenario)
    out = grade_natural_scenario(
        records=records,
        scenario=scenario,
        llm_answer=(
            "After the migrating forest episode, Captain Lysandra is still in play and the recap ties "
            "her to forest-adjacent beats and tower-related clues."
        ),
        cached_retrieval=bundle,
    )
    assert out["grading_mode"] == "natural_retrieval_context+llm"
    assert out["ok"] is True
    assert out["llm_semantic_verdict"] == "pass_updated"


def test_grade_natural_llm_answer_fails_negated_required_token() -> None:
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "U-test-lysandra-002",
            "lexical_plain": "Captain Lysandra is tied to a tower drawing and a blueprint.",
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "subject_class": "npc",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_negated_required_token",
        "campaign_id": "longmont-c2",
        "query_spec": {
            "query": "Does the recap tie a tower drawing to the captain?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        "must_hit_tokens": ["captain", "tower", "blueprint"],
        "semantic_equivalences": {"blueprint": ["drawing"]},
        "must_not_cooccur": {
            "blueprint": ["no drawing", "no blueprint", "no mention of a drawing"]
        },
        "stale_tokens": [],
        "expect_route_substrings": ["captain_lysandra_ironveil"],
        "min_context_support_ratio": 1.0,
        "update_signal_tokens": [],
    }
    bundle = natural_retrieval_bundle(records=records, scenario=scenario)
    out = grade_natural_scenario(
        records=records,
        scenario=scenario,
        llm_answer="The captain is tied to the tower, but there is no mention of a drawing.",
        cached_retrieval=bundle,
    )
    assert out["ok"] is False
    assert "llm_context_support_below_threshold" in out["violations"]


def test_load_gold_accepts_natural_schema(tmp_path: Path) -> None:
    p = tmp_path / "g.json"
    p.write_text(
        '{"schema": "dmb_breadcrumb_query_natural_gold_v1", "campaign_id": "x", "scenarios": []}',
        encoding="utf-8",
    )
    data = load_gold(p)
    assert data["schema"] == "dmb_breadcrumb_query_natural_gold_v1"


def test_query_expansion_uses_first_pass_not_expected_gates() -> None:
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "u-comm-1",
            "lexical_plain": "The communication beat: Caelynn uses the rockie talkie and Sara relays the message.",
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
                    "subject_class": "npc",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_expansion",
        "campaign_id": "longmont-c2",
        "question": "What communication happened?",
        "query_spec": {
            "query": "What communication happened?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        # This is intentionally absent from the question and records. The
        # expansion stage must not read expected gates as oracle terms.
        "expect_route_substrings": ["secret_oracle_route"],
        "must_hit_tokens": ["secret_oracle_token"],
    }
    lanes = grade_natural_scenario_lanes(records=records, scenario=scenario)
    expanded_terms = lanes["expansion"]["expanded_terms"]
    assert "relay" in expanded_terms
    assert "operator" in expanded_terms
    assert "secret_oracle_route" not in expanded_terms
    assert "secret_oracle_token" not in expanded_terms
    assert lanes["expanded_retrieval"]["raw_question"] == "What communication happened?"
    assert lanes["expanded_retrieval"]["expansion_source"] == "first_pass"


def test_build_query_expansion_records_trace_shape() -> None:
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "u-place-1",
            "lexical_plain": "Nearby locations include a wagon camp outside town.",
            "routes": [
                {
                    "normalized_route": "Elderwyld/Cities and Towns/Mossford/",
                    "subject_class": "location",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_manifestish",
        "campaign_id": "longmont-c2",
        "query_spec": {
            "query": "What locations are nearby?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        "must_hit_tokens": ["town"],
        "stale_tokens": [],
    }
    result, _ = natural_retrieval_bundle(records=records, scenario=scenario)
    expansion = build_query_expansion(
        question="What locations are nearby?",
        records=records,
        first_pass_result=result,
    )
    assert expansion["raw_question"] == "What locations are nearby?"
    assert expansion["expansion_source"] == "first_pass"
    assert "town" in expansion["expanded_terms"]


def test_breadcrumb_normalize_emits_frontmatter_location_metadata_records() -> None:
    artifact = Path(
        "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md"
    ).read_text(encoding="utf-8")
    records, meta = normalize_breadcrumb_artifact(
        artifact_text=artifact,
        corpus_root=Path("corpus/eldyrwild-markdown").resolve(),
    )
    by_unit = {record.unit_id: record for record in records}

    assert meta["metadata_record_count"] == 2
    locations = by_unit["meta-session-0020-locations"]
    assert "locations" in locations.lexical_plain
    assert "mossford" in locations.lexical_plain
    assert "mirathorn" in locations.lexical_plain
    assert "voices tower" in locations.lexical_plain
    assert any("Mossford" in route.normalized_route for route in locations.routes)
    assert any("Voices Tower" in route.normalized_route for route in locations.routes)
    assert all(route.tag_kind == "frontmatter" for route in locations.routes)

    open_loops = by_unit["meta-session-0020-open-loops"]
    assert "open loops" in open_loops.lexical_plain
    assert "actionable" in open_loops.lexical_plain
    assert any("Stormspire Academy" in route.normalized_route for route in open_loops.routes)
    assert any("Voices Tower" in route.normalized_route for route in open_loops.routes)


def test_pronoun_route_handle_enrichment_makes_resolved_routes_searchable() -> None:
    artifact = Path(
        "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md"
    ).read_text(encoding="utf-8")
    records, meta = normalize_breadcrumb_artifact(
        artifact_text=artifact,
        corpus_root=Path("corpus/eldyrwild-markdown").resolve(),
        enrich_pronoun_route_handles=True,
    )
    by_unit = {record.unit_id: record for record in records}
    target = by_unit["u-L0017-04"]

    assert meta["pronoun_route_handle_enrichment_enabled"] is True
    assert meta["enriched_pronoun_record_count"] > 0
    assert target.lexical_plain.startswith("She tells Caelynn")
    assert "resolved pronoun handles" in target.lexical_plain
    assert "captain lysandra ironveil" in target.lexical_plain
    assert "sara mirathorn operator" in target.lexical_plain
    assert "longmont campaign" not in target.lexical_plain
    assert "elderwyld" not in target.lexical_plain


def test_embedding_similarity_helpers_are_deterministic() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([], [1.0]) == 0.0
    assert embedding_cost_usd(model="text-embedding-3-large", total_tokens=1_000_000) == 0.13
