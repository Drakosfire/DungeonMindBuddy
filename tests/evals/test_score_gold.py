from __future__ import annotations

import json
from pathlib import Path

from evals.llm_ingestion_slice.run_slice import OUTPUT_DIR, main as run_slice_main
from evals.llm_ingestion_slice.score_gold import (
    GoldEntityExpectation,
    _check_temporal_accuracy,
    _match_gold_entities_to_stage,
    _negative_violations,
    _parse_stage_entities,
    main as score_gold_main,
)

ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = ROOT / "evals" / "llm_ingestion_slice" / "gold" / "manual_entity_extraction_gold.json"


def _load_gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def test_score_gold_on_deterministic_slice() -> None:
    assert run_slice_main() == 0
    assert (
        score_gold_main(
            artifacts_dir=OUTPUT_DIR,
            eval_mode="deterministic_slice",
            min_core_recall=0.10,
            min_temporal_accuracy=1.0,
            min_catalog_recall=1.0,
        )
        == 0
    )

    report = json.loads((OUTPUT_DIR / "gold_score.json").read_text(encoding="utf-8"))
    assert report["eval_mode"] == "deterministic_slice"
    assert report["pass_fail"]["overall_pass"] is True
    assert report["temporal"]["metrics"]["field_accuracy"] >= 1.0
    assert report["catalog_recall"]["metrics"]["recall"] >= 1.0
    assert report["negative_examples"]["violations"] == []


def test_entity_matching_exact() -> None:
    stage_entities = _parse_stage_entities(
        [{"display_name": "Mirathorn", "entity_type": "location", "aliases": []}]
    )
    exact_match = _match_gold_entities_to_stage(
        gold_entities=[
            GoldEntityExpectation(
                display_name="Mirathorn",
                entity_type="location",
                importance="core",
                aliases_suggested=(),
            )
        ],
        stage_entities=stage_entities,
    )
    assert len(exact_match["matched_gold"]) == 1
    assert exact_match["matched_gold"][0]["match_strength"] == 3


def test_entity_matching_alias() -> None:
    stage_entities = _parse_stage_entities(
        [{"display_name": "Council", "entity_type": "faction", "aliases": ["city council"]}]
    )
    match = _match_gold_entities_to_stage(
        gold_entities=[
            GoldEntityExpectation(
                display_name="Council",
                entity_type="faction",
                importance="core",
                aliases_suggested=("city council",),
            )
        ],
        stage_entities=stage_entities,
    )
    assert len(match["matched_gold"]) == 1
    assert match["matched_gold"][0]["match_strength"] >= 2


def test_entity_matching_substring() -> None:
    stage_entities = _parse_stage_entities(
        [{"display_name": "Elara Swiftwind", "entity_type": "npc", "aliases": []}]
    )
    match = _match_gold_entities_to_stage(
        gold_entities=[
            GoldEntityExpectation(
                display_name="Mayor Elara Swiftwind",
                entity_type="npc",
                importance="core",
                aliases_suggested=(),
            )
        ],
        stage_entities=stage_entities,
    )
    assert len(match["matched_gold"]) == 1
    assert match["matched_gold"][0]["match_strength"] == 1


def test_negative_example_detection() -> None:
    gold = _load_gold()
    stage_entities = _parse_stage_entities(
        [
            {"display_name": "Mirathorn", "entity_type": "location", "aliases": []},
            {"display_name": "the players", "entity_type": "other", "aliases": []},
        ]
    )
    violations = _negative_violations(gold=gold, stage_entities=stage_entities)
    assert "the players" in violations


def test_temporal_check_pass() -> None:
    gold = {
        "sources": [
            {
                "key": "campaign_markdown",
                "segments": [
                    {
                        "segment_id": "seg_1",
                        "aligns_with_slice_evidence_id": "evu_campaign_planning_cult",
                        "expected_fact_temporal": {
                            "asserted_in_session": 6,
                            "sequence_index_within_session": 2,
                        },
                    }
                ],
            }
        ]
    }
    stage_chunks = [
        {
            "evidence_id": "evu_campaign_planning_cult",
            "text": "Secure Shipment Shepherds and Maelthor details...",
        }
    ]
    stage_facts = [
        {
            "fact_id": "fact_1",
            "evidence_ids": ["evu_campaign_planning_cult"],
            "asserted_in_session": 6,
            "sequence_index_within_session": 2,
        }
    ]
    result = _check_temporal_accuracy(gold=gold, stage_facts=stage_facts, stage_chunks=stage_chunks)
    assert result["metrics"]["field_accuracy"] == 1.0
    assert result["counts"]["mismatch_count"] == 0


def test_temporal_check_mismatch() -> None:
    gold = {
        "sources": [
            {
                "key": "campaign_markdown",
                "segments": [
                    {
                        "segment_id": "seg_1",
                        "aligns_with_slice_evidence_id": "evu_campaign_planning_cult",
                        "expected_fact_temporal": {
                            "asserted_in_session": 6,
                            "sequence_index_within_session": 2,
                        },
                    }
                ],
            }
        ]
    }
    stage_chunks = [
        {
            "evidence_id": "evu_campaign_planning_cult",
            "text": "Secure Shipment Shepherds and Maelthor details...",
        }
    ]
    stage_facts = [
        {
            "fact_id": "fact_bad",
            "evidence_ids": ["evu_campaign_planning_cult"],
            "asserted_in_session": None,
            "sequence_index_within_session": 999,
        }
    ]
    result = _check_temporal_accuracy(gold=gold, stage_facts=stage_facts, stage_chunks=stage_chunks)
    assert result["counts"]["mismatch_count"] >= 2
