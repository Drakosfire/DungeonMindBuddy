from __future__ import annotations

from evals.mirathorn_vertical_slice.claim_verifier import (
    aggregate_accuracy,
    build_projection_fact_index,
    evaluate_answer_accuracy,
    extract_claims_heuristic,
    verify_claims_against_projection,
)


def _sample_projection() -> dict:
    return {
        "entities": {
            "ent_the_wolf": {
                "attributes": {
                    "status": {
                        "value_label": "Dead after decapitated killing blow",
                        "source_truth_state": "OBSERVED",
                    },
                    "corruption_state": {
                        "value_label": "Oily sheen fades after death",
                        "source_truth_state": "OBSERVED",
                    },
                }
            },
            "ent_commander_thalia": {
                "attributes": {
                    "condition": {
                        "value_label": "ensorcelled, not fully corrupted",
                        "source_truth_state": "OBSERVED",
                    }
                }
            },
        }
    }


def _sample_entities() -> list[dict]:
    return [
        {"entity_id": "ent_the_wolf", "display_name": "The Wolf"},
        {
            "entity_id": "ent_commander_thalia",
            "display_name": "Commander Thalia",
            "aliases": ["Thalia"],
        },
    ]


def test_extract_claims_heuristic_filters_headers() -> None:
    answer = (
        "TL;DR: The Wolf is dead.\n"
        "The Wolf is dead after a killing blow.\n"
        "Key Attributes:\n"
        "- status: dead"
    )
    claims = extract_claims_heuristic(answer)
    assert claims
    assert all(not c["text"].lower().startswith("tl;dr") for c in claims)
    assert all("key attributes" not in c["text"].lower() for c in claims)


def test_build_projection_fact_index_includes_truth_state() -> None:
    facts = build_projection_fact_index(_sample_projection(), _sample_entities())
    assert facts
    assert any(f["truth_state"] == "OBSERVED" for f in facts)
    assert any("the wolf" in f["search_text"] for f in facts)


def test_verify_claims_detects_grounded_and_unsupported() -> None:
    claims = [
        {"text": "The Wolf is dead after a killing blow.", "type": "factual"},
        {"text": "The Wolf escaped alive through the sewers.", "type": "factual"},
    ]
    out = verify_claims_against_projection(claims, _sample_projection(), _sample_entities())
    assert out["total_factual_claims"] == 2
    assert out["status_counts"]["grounded"] >= 1
    assert out["status_counts"]["unsupported"] + out["status_counts"]["contradicted"] >= 1


def test_evaluate_answer_accuracy_uses_heuristic_extractor() -> None:
    answer = (
        "TL;DR: The Wolf is dead.\n"
        "The Wolf is dead after a killing blow and the oily sheen fades.\n"
        "Commander Thalia is ensorcelled, not fully corrupted."
    )
    out = evaluate_answer_accuracy(
        answer=answer,
        projection=_sample_projection(),
        entities=_sample_entities(),
        use_llm_extractor=False,
    )
    assert out["extractor"] == "heuristic"
    assert out["total_factual_claims"] >= 2
    assert 0.0 <= out["completeness"] <= 1.0
    assert "claims" in out


def test_aggregate_accuracy_rolls_up_counts() -> None:
    combined = aggregate_accuracy(
        [
            {
                "total_factual_claims": 2,
                "status_counts": {
                    "grounded": 1,
                    "unsupported": 1,
                    "contradicted": 0,
                    "provenance_mismatch": 0,
                },
                "claims_with_provenance": 0,
                "provenance_accuracy": 1.0,
            },
            {
                "total_factual_claims": 1,
                "status_counts": {
                    "grounded": 1,
                    "unsupported": 0,
                    "contradicted": 0,
                    "provenance_mismatch": 0,
                },
                "claims_with_provenance": 0,
                "provenance_accuracy": 1.0,
            },
        ]
    )
    assert combined["enabled"] is True
    assert combined["total_factual_claims"] == 3
    assert combined["status_counts"]["grounded"] == 2
    assert combined["hallucination_rate"] == 0.3333
