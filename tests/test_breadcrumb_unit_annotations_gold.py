from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_gold import (
    GoldBeatEntry,
    compare_unit_annotations_to_gold,
    load_gold_beat_index,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import (
    BeatIndexEntry,
    RecapUnitAnnotationsV1,
    UnitAnnotation,
)


def test_load_gold_beat_index_c1s13() -> None:
    path = Path(
        "evals/sentence_routing_retrieval_falsification/manual_labels/"
        "Session 13 - The Meaty and the Dead.gold.beats.breadcrumbed.md"
    )
    beats = load_gold_beat_index(path)
    assert len(beats) == 12
    assert beats[0].beat_id == "c1s13-b001-plan-academy-departure"
    assert beats[0].unit_ids == ["u-L0003-01", "u-L0003-02", "u-L0003-03", "u-L0003-04"]
    assert beats[0].location_routes == [
        "Longmont Campaign/Campaign 1/Locations/council_chambers/"
    ]
    assert len(beats[0].population_evidence) >= 1
    assert beats[0].population_evidence[0].entity_route is not None
    assert beats[2].beat_id == "c1s13-b003-stormspire-arrival-desk"
    assert beats[7].beat_id == "c1s13-b008-basement-morgue-speak-with-dead"


def test_compare_reports_unit_span_match_when_beat_id_differs() -> None:
    payload = RecapUnitAnnotationsV1(
        schema_discriminator="dmb_recap_unit_annotations_v1",
        source_recap_path="a.md",
        campaign_id="longmont-c1",
        session_number=13,
        beat_index=[
            BeatIndexEntry(beat_id="c1s13-b001-model-slug", summary="Model slug."),
        ],
        unit_annotations=[
            UnitAnnotation(unit_id="u-L0001-01", beat_id="c1s13-b001-model-slug"),
            UnitAnnotation(unit_id="u-L0001-02", beat_id="c1s13-b001-model-slug"),
        ],
    )
    compare = compare_unit_annotations_to_gold(
        payload,
        [
            GoldBeatEntry(
                beat_id="c1s13-b001-gold-slug",
                summary="Gold slug.",
                unit_ids=["u-L0001-01", "u-L0001-02"],
            )
        ],
    )

    assert compare["dimension_pass_rates"]["beat_unit_membership"] == 0.0
    assert compare["unit_span_alignment"]["exact_unit_span_matches"] == 1
    assert compare["per_beat"][0]["best_model_unit_span_match"]["beat_id"] == "c1s13-b001-model-slug"
