from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.llm_ingestion_slice.run_slice import OUTPUT_DIR, main as run_slice_main
from evals.llm_ingestion_slice.score_gold import (
    GoldEntityExpectation,
    _check_temporal_accuracy,
    _concept_event_confusion,
    _exclude_path_metrics,
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
        [{"display_name": "Mirathorn", "entity_class": "place", "aliases": []}]
    )
    exact_match = _match_gold_entities_to_stage(
        gold_entities=[
            GoldEntityExpectation(
                display_name="Mirathorn",
                entity_class="place",
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
        [{"display_name": "Council", "entity_class": "group", "aliases": ["city council"]}]
    )
    match = _match_gold_entities_to_stage(
        gold_entities=[
            GoldEntityExpectation(
                display_name="Council",
                entity_class="group",
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
        [{"display_name": "Elara Swiftwind", "entity_class": "actor", "aliases": []}]
    )
    match = _match_gold_entities_to_stage(
        gold_entities=[
            GoldEntityExpectation(
                display_name="Mayor Elara Swiftwind",
                entity_class="actor",
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
            {"display_name": "Mirathorn", "entity_class": "place", "aliases": []},
            {"display_name": "the players", "entity_class": "concept", "aliases": []},
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


class TestConceptEventConfusion:
    def test_no_confusion_when_classes_match(self) -> None:
        gold_entities = [
            GoldEntityExpectation(display_name="Festival of Expansion", entity_class="event", importance="core", aliases_suggested=()),
            GoldEntityExpectation(display_name="Shepherd's Rise", entity_class="concept", importance="core", aliases_suggested=()),
        ]
        stage_entities = _parse_stage_entities([
            {"display_name": "Festival of Expansion", "entity_class": "event", "aliases": []},
            {"display_name": "Shepherd's Rise", "entity_class": "concept", "aliases": []},
        ])
        result = _concept_event_confusion(gold_entities, stage_entities)
        assert result["confusion_count"] == 0
        assert result["confusion_pairs"] == []

    def test_detects_event_classified_as_concept(self) -> None:
        gold_entities = [
            GoldEntityExpectation(display_name="Festival of Expansion", entity_class="event", importance="core", aliases_suggested=()),
        ]
        stage_entities = _parse_stage_entities([
            {"display_name": "Festival of Expansion", "entity_class": "concept", "aliases": []},
        ])
        result = _concept_event_confusion(gold_entities, stage_entities)
        assert result["confusion_count"] == 1
        assert result["confusion_pairs"][0]["gold_class"] == "event"
        assert result["confusion_pairs"][0]["stage_class"] == "concept"

    def test_detects_concept_classified_as_event(self) -> None:
        gold_entities = [
            GoldEntityExpectation(display_name="Shepherd's Rise", entity_class="concept", importance="core", aliases_suggested=()),
        ]
        stage_entities = _parse_stage_entities([
            {"display_name": "Shepherd's Rise", "entity_class": "event", "aliases": []},
        ])
        result = _concept_event_confusion(gold_entities, stage_entities)
        assert result["confusion_count"] == 1
        assert result["confusion_pairs"][0]["gold_class"] == "concept"
        assert result["confusion_pairs"][0]["stage_class"] == "event"

    def test_ignores_non_confusable_mismatches(self) -> None:
        gold_entities = [
            GoldEntityExpectation(display_name="Mirathorn", entity_class="place", importance="core", aliases_suggested=()),
        ]
        stage_entities = _parse_stage_entities([
            {"display_name": "Mirathorn", "entity_class": "group", "aliases": []},
        ])
        result = _concept_event_confusion(gold_entities, stage_entities)
        assert result["confusion_count"] == 0


class TestExcludePathMetrics:
    def test_counts_excluded_by_reason(self) -> None:
        excluded = [
            {"display_name": "candlelight", "exclude_reason": "generic_noun", "entity_class": None, "source": "llm_exclude", "evidence_id": "ev1"},
            {"display_name": "Executive DM Summary", "exclude_reason": "document_structure", "entity_class": None, "source": "llm_exclude", "evidence_id": "ev2"},
            {"display_name": "DC 12 save", "exclude_reason": "game_mechanic", "entity_class": None, "source": "llm_exclude", "evidence_id": "ev3"},
        ]
        gold: dict[str, Any] = {"negative_examples": {"must_not_extract_as_entities": []}}
        result = _exclude_path_metrics([], excluded, gold)
        assert result["total_excluded_candidates"] == 3
        assert result["document_structure_excluded"] == 1
        assert result["game_mechanic_excluded"] == 1

    def test_detects_false_positives_from_gold_negatives(self) -> None:
        gold: dict[str, Any] = {"negative_examples": {"must_not_extract_as_entities": ["the players", "candlelight"]}}
        stage_payload = [
            {"display_name": "the players", "entity_class": "concept", "extraction_method": "llm"},
            {"display_name": "Mirathorn", "entity_class": "place", "extraction_method": "llm"},
        ]
        result = _exclude_path_metrics(stage_payload, None, gold)
        assert result["non_entity_false_positive_count"] == 1
        assert "the players" in result["non_entity_false_positives"]

    def test_counts_extraction_methods(self) -> None:
        gold: dict[str, Any] = {"negative_examples": {"must_not_extract_as_entities": []}}
        stage_payload = [
            {"display_name": "A", "extraction_method": "llm"},
            {"display_name": "B", "extraction_method": "heuristic"},
            {"display_name": "C", "extraction_method": "heuristic"},
            {"display_name": "D"},
        ]
        result = _exclude_path_metrics(stage_payload, None, gold)
        assert result["extraction_method_counts"]["llm"] == 2
        assert result["extraction_method_counts"]["heuristic"] == 2

    def test_handles_no_excluded_candidates(self) -> None:
        gold: dict[str, Any] = {"negative_examples": {"must_not_extract_as_entities": []}}
        result = _exclude_path_metrics([], None, gold)
        assert result["total_excluded_candidates"] == 0


class TestExcludedCandidatesPersistence:
    def test_excluded_candidates_written_to_cache(self, tmp_path: Path) -> None:
        from src.ingestion.entity_extractor import run_entity_extraction

        class ExcludeClient:
            def extract_entities(self, **kwargs: Any) -> dict[str, Any]:
                return {
                    "entities": [
                        {
                            "entity_class": "place",
                            "display_name": "Mirathorn",
                            "aliases": [],
                            "is_new": True,
                            "decision": "entity",
                        },
                        {
                            "entity_class": None,
                            "display_name": "candlelight",
                            "aliases": [],
                            "is_new": True,
                            "decision": "exclude",
                            "exclude_reason": "generic_noun",
                        },
                    ]
                }

        evidence = {
            "schema_version": "0.1.0",
            "created_at": "2026-03-27T00:00:00Z",
            "updated_at": "2026-03-27T00:00:00Z",
            "record_status": "active",
            "evidence_id": "evid_1",
            "document_id": "doc_test",
            "document_type": "world_reference",
            "document_title": "Test Doc",
            "source_class": "seed_reference",
            "canon_layer": "world",
            "campaign_id": None,
            "text": "Mirathorn glows by candlelight.",
            "section_path": ["Test"],
            "paragraph_index": 0,
            "source_order_index": 0,
            "line_span": None,
            "char_span": None,
            "inferred_session": None,
            "speaker_or_subject": None,
            "notes": None,
        }
        cache_dir = tmp_path / "cache"
        run_entity_extraction([evidence], cache_dir=cache_dir, openai_client=ExcludeClient())

        excluded_path = cache_dir / "excluded_candidates.json"
        assert excluded_path.exists()
        excluded = json.loads(excluded_path.read_text(encoding="utf-8"))
        assert any(e["display_name"] == "candlelight" for e in excluded)
        assert any(e["source"] == "llm_exclude" for e in excluded)

    def test_extraction_method_set_correctly(self, tmp_path: Path) -> None:
        from src.ingestion.entity_extractor import run_entity_extraction

        entity_out = run_entity_extraction(
            [
                {
                    "schema_version": "0.1.0",
                    "created_at": "2026-03-27T00:00:00Z",
                    "updated_at": "2026-03-27T00:00:00Z",
                    "record_status": "active",
                    "evidence_id": "evid_h",
                    "document_id": "doc_test",
                    "document_type": "world_reference",
                    "document_title": "Test",
                    "source_class": "seed_reference",
                    "canon_layer": "world",
                    "campaign_id": None,
                    "text": "Mirathorn lies near Lake Mirathorn.",
                    "section_path": ["Test"],
                    "paragraph_index": 0,
                    "source_order_index": 0,
                    "line_span": None,
                    "char_span": None,
                    "inferred_session": None,
                    "speaker_or_subject": None,
                    "notes": None,
                }
            ],
            cache_dir=tmp_path / "cache",
        )
        entities = entity_out["entities"]
        assert len(entities) > 0
        for entity in entities:
            assert entity.get("extraction_method") == "heuristic"
