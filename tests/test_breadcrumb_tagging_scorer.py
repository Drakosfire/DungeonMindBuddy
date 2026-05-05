from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_scorer import (
    SENTINELS_SCHEMA,
    score_artifact,
    score_cohort,
    score_normalized_records,
)

MANUAL_BASELINE = Path(
    "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md"
)
CORPUS_ROOT = Path("corpus/eldyrwild-markdown")


def _sentinels(positive: list[dict] | None = None, negative: list[dict] | None = None,
               protected: list[dict] | None = None) -> dict:
    return {
        "schema": SENTINELS_SCHEMA,
        "positive_units": positive or [],
        "negative_units": negative or [],
        "protected_units": protected or [],
    }


def test_manual_baseline_exposes_known_gap_and_keeps_protected_routes() -> None:
    sentinels = _sentinels(
        positive=[
            {
                "unit_id": "u-L0019-09",
                "must_contain": ["NPCs/captain_lysandra_ironveil", "Voices Tower"],
            },
            {
                "unit_id": "u-L0019-10",
                "must_contain": ["NPCs/captain_lysandra_ironveil", "Voices Tower"],
            },
        ],
        negative=[
            {"unit_id": "u-L0019-02", "must_not_contain": ["captain_lysandra_ironveil"]},
            {"unit_id": "u-L0007-01", "must_not_contain": ["captain_lysandra_ironveil"]},
        ],
        protected=[
            {"unit_id": "u-L0019-06", "must_contain": ["NPCs/captain_lysandra_ironveil"]},
            {"unit_id": "u-L0019-11", "must_contain": ["NPCs/captain_lysandra_ironveil"]},
            {"unit_id": "u-L0021-07", "must_contain": ["NPCs/captain_lysandra_ironveil"]},
        ],
    )
    out = score_artifact(
        artifact_path=MANUAL_BASELINE.resolve(),
        corpus_root=CORPUS_ROOT.resolve(),
        sentinels=sentinels,
        baseline_artifact_path=None,
    )
    assert out["normalize"]["ok"] is True
    summary = out["sentinels"]["summary"]
    assert summary["positive_total"] == 2
    assert summary["positive_passed"] == 0, "manual baseline must surface the L0019-09/10 gap"
    assert summary["negative_total"] == 2
    assert summary["negative_passed"] == 2, "no over-routing on protected non-Lysandra units"
    assert summary["protected_total"] == 3
    assert summary["protected_passed"] == 3, "manual baseline keeps Lysandra on already-good units"


def test_score_cohort_aggregates_pass_count(tmp_path: Path) -> None:
    sentinels = _sentinels(
        protected=[
            {"unit_id": "u-L0019-06", "must_contain": ["NPCs/captain_lysandra_ironveil"]},
        ]
    )
    report = score_cohort(
        artifact_paths=[MANUAL_BASELINE.resolve()],
        corpus_root=CORPUS_ROOT.resolve(),
        sentinels=sentinels,
        baseline_artifact_path=None,
    )
    assert report["aggregate"]["artifact_count"] == 1
    assert report["aggregate"]["sentinels_all_passed_count"] == 1


def test_normalize_error_does_not_crash_scoring(tmp_path: Path) -> None:
    bad_artifact = tmp_path / "bad.md"
    bad_artifact.write_text(
        """---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
campaign_id: longmont-c2
session:
  number: 20
---
Hello world this body does not match the recap.
""",
        encoding="utf-8",
    )
    out = score_artifact(
        artifact_path=bad_artifact,
        corpus_root=CORPUS_ROOT.resolve(),
        sentinels=_sentinels(),
        baseline_artifact_path=None,
    )
    assert out["normalize"]["ok"] is False
    assert out["normalize"]["error"]
    assert out["sentinels"]["summary"]["all_passed"] is True  # vacuously true: no sentinel checks defined


def test_score_normalized_records_matches_score_artifact() -> None:
    text = MANUAL_BASELINE.read_text(encoding="utf-8")
    records, meta = normalize_breadcrumb_artifact(
        artifact_text=text, corpus_root=CORPUS_ROOT.resolve()
    )
    baseline_path = Path(
        "evals/sentence_routing_retrieval_falsification/manual_labels/artifacts/"
        "Session 20 - Recap.breadcrumbed.indexed.gpt-5_3-codex.md"
    ).resolve()
    direct = score_artifact(
        artifact_path=MANUAL_BASELINE.resolve(),
        corpus_root=CORPUS_ROOT.resolve(),
        sentinels=None,
        baseline_artifact_path=baseline_path,
    )
    via_records = score_normalized_records(
        records=records,
        corpus_root=CORPUS_ROOT.resolve(),
        artifact_path=str(MANUAL_BASELINE.resolve()),
        meta=meta,
        normalize_error=None,
        sentinels=None,
        baseline_artifact_path=baseline_path,
        breadcrumb_full_text=text,
    )
    assert direct["normalize"] == via_records["normalize"]
    assert direct["baseline_comparison"] == via_records["baseline_comparison"]


def test_baseline_comparison_emitted_when_path_provided() -> None:
    out = score_artifact(
        artifact_path=MANUAL_BASELINE.resolve(),
        corpus_root=CORPUS_ROOT.resolve(),
        sentinels=None,
        baseline_artifact_path=Path(
            "evals/sentence_routing_retrieval_falsification/manual_labels/artifacts/Session 20 - Recap.breadcrumbed.indexed.gpt-5_3-codex.md"
        ).resolve(),
    )
    block = out["baseline_comparison"]
    assert block is not None
    assert "precision_vs_baseline" in block
    assert "recall_vs_baseline" in block
