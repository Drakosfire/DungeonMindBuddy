from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.campaign_corpus_materializer import load_campaign_corpus_records_for_c1s4
from evals.c1s4_preplanning_vertical_slice.visibility_provenance import (
    infer_c1s4_visibility,
    is_planner_visible_for_c1s4_preplanning,
)


def test_visibility_rejects_future_observed_play_record() -> None:
    record = {
        "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/hempholm/README.md",
        "title": "Hempholm campaign-canon hub",
        "section_heading": "Authority stance",
        "lexical_plain": "This hub records Sessions 4-5 after the party arrived and fought the tree battle.",
        "session_number": 0,
    }

    visibility = infer_c1s4_visibility(record)

    assert visibility["planner_visible"] is False
    assert visibility["derived_from_artifact_role"] == "post_session_campaign_canon"
    assert not is_planner_visible_for_c1s4_preplanning(record)


def test_c1s4_campaign_materializer_does_not_admit_future_hempholm_canon() -> None:
    records = load_campaign_corpus_records_for_c1s4()
    hempholm_hub_records = [
        r
        for r in records
        if "/Locations/hempholm/README.md" in str(r.get("source_path") or "")
    ]

    assert hempholm_hub_records == []
    assert all(is_planner_visible_for_c1s4_preplanning(r) for r in records)
