import json
from pathlib import Path

from extraction_lab.campaign_memory_baseline_qualification import qualify_baseline


ROOT = Path(__file__).resolve().parents[2]


def test_qualification_exposes_instability_and_unscored_witness(tmp_path: Path) -> None:
    repetitions = []
    for index, passed in enumerate((True, False, True), 1):
        store = tmp_path / f"store-{index}"
        lab = tmp_path / f"lab-{index}"
        store.mkdir()
        lab.mkdir()
        (store / "entities.json").write_text(
            json.dumps([{"entity_id": "e1", "display_name": "Brin"}])
        )
        (store / "facts.json").write_text(
            json.dumps(
                [{"fact_id": "f1", "subject_entity_id": "e1", "attribute": "role"}]
            )
        )
        (lab / "entity_results.json").write_text(
            json.dumps(
                [
                    {
                        "anchor_id": "brin_holloway_session23",
                        "passed": passed,
                        "fail_bucket": None if passed else "name_not_found",
                        "resolved_entity_id": "e1" if passed else None,
                    }
                ]
            )
        )
        (lab / "fact_results.json").write_text(
            json.dumps(
                [
                    {
                        "anchor_id": "brin_role",
                        "passed": passed,
                        "fail_bucket": None if passed else "subject_unresolved",
                        "matched_fact_id": "f1" if passed else None,
                    }
                ]
            )
        )
        (lab / "aggregate_metrics.json").write_text(
            json.dumps(
                {
                    "entity_anchor_recall": float(passed),
                    "fact_anchor_recall": float(passed),
                    "total_entity_count": 1,
                    "total_fact_count": 1,
                }
            )
        )
        repetitions.append(
            {
                "index": index,
                "store_path": str(store),
                "lab_run_path": str(lab),
                "observed_models": {"entity": "m", "fact": "m"},
                "telemetry": {
                    key: 1
                    for key in (
                        "runtime_seconds",
                        "api_calls",
                        "input_tokens",
                        "output_tokens",
                        "total_tokens",
                        "cost_usd",
                    )
                },
            }
        )
    qualification, witness = qualify_baseline(
        repetitions=repetitions,
        benchmark_path=ROOT / "evals/campaign_memory_development/benchmark.json",
        temporal_path=ROOT
        / "evals/campaign_memory_development/temporal_expectations.json",
    )
    assert qualification["entity_anchors"][0]["stability"] == "unstable"
    assert witness["scoring"] == "none"
    assert len(witness["repetitions"][0]["temporal_expectations"]) == 7
