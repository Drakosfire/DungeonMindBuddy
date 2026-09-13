from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from extraction_lab.campaign_memory_benchmark import CampaignMemoryBenchmark
from extraction_lab.campaign_memory_temporal_intent import TemporalIntentOverlay


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _stats(values: list[float]) -> dict[str, Any]:
    return {
        "values": values,
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
        "population_standard_deviation": statistics.pstdev(values),
    }


def _anchors(repetitions: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    rows_by_run = [
        _read(Path(row["lab_run_path"]) / f"{kind}_results.json") for row in repetitions
    ]
    ids = [row["anchor_id"] for row in rows_by_run[0]]
    if any([row["anchor_id"] for row in rows] != ids for rows in rows_by_run[1:]):
        raise ValueError(f"{kind} anchor result identity drift")
    output = []
    for anchor_id in ids:
        observed = [
            next(row for row in rows if row["anchor_id"] == anchor_id)
            for rows in rows_by_run
        ]
        passed = sum(bool(row["passed"]) for row in observed)
        output.append(
            {
                "anchor_id": anchor_id,
                "pass_count": passed,
                "pass_rate": passed / len(observed),
                "stability": "stable_pass"
                if passed == len(observed)
                else "stable_fail"
                if passed == 0
                else "unstable",
                "fail_buckets": dict(
                    sorted(
                        Counter(
                            str(row.get("fail_bucket"))
                            for row in observed
                            if not row["passed"]
                        ).items()
                    )
                ),
                "repetitions": observed,
            }
        )
    return output


def qualify_baseline(
    *, repetitions: list[dict[str, Any]], benchmark_path: Path, temporal_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(repetitions) != 3:
        raise ValueError("exactly three repetitions required")
    metrics = [
        _read(Path(row["lab_run_path"]) / "aggregate_metrics.json")
        for row in repetitions
    ]
    metric_names = (
        "entity_anchor_recall",
        "fact_anchor_recall",
        "total_entity_count",
        "total_fact_count",
    )
    qualification = {
        "schema": "dmb_campaign_memory_baseline_qualification_v1",
        "repetitions": 3,
        "metrics": {
            name: _stats([float(row[name]) for row in metrics]) for name in metric_names
        },
        "entity_anchors": _anchors(repetitions, "entity"),
        "fact_anchors": _anchors(repetitions, "fact"),
        "operations": {
            name: _stats([float(row["telemetry"][name]) for row in repetitions])
            for name in (
                "runtime_seconds",
                "api_calls",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cost_usd",
            )
        },
        "models": sorted(
            {model for row in repetitions for model in row["observed_models"].values()}
        ),
    }
    benchmark = CampaignMemoryBenchmark.model_validate_json(benchmark_path.read_bytes())
    temporal = TemporalIntentOverlay.model_validate_json(temporal_path.read_bytes())
    witness_runs = []
    for repetition in repetitions:
        store = Path(repetition["store_path"])
        entities = _read(store / "entities.json")
        facts = _read(store / "facts.json")
        entity_results = {
            r["anchor_id"]: r
            for r in _read(Path(repetition["lab_run_path"]) / "entity_results.json")
        }
        fact_results = {
            r["anchor_id"]: r
            for r in _read(Path(repetition["lab_run_path"]) / "fact_results.json")
        }
        identities = []
        for intent in benchmark.identity_expectations:
            identities.append(
                {
                    "expectation_id": intent.expectation_id,
                    "intent": intent.intent,
                    "anchors": [
                        {
                            "anchor_id": anchor,
                            "resolution": entity_results.get(anchor),
                            "entity": next(
                                (
                                    e
                                    for e in entities
                                    if e.get("entity_id")
                                    == (entity_results.get(anchor) or {}).get(
                                        "resolved_entity_id"
                                    )
                                ),
                                None,
                            ),
                        }
                        for anchor in intent.anchor_ids
                    ],
                }
            )
        temporal_rows = []
        for intent in temporal.expectations:
            subject = entity_results.get(intent.subject_anchor)
            subject_id = (subject or {}).get("resolved_entity_id")
            temporal_rows.append(
                {
                    "expectation_id": intent.expectation_id,
                    "intent": intent.intent,
                    "truth_window": intent.truth_window.model_dump(),
                    "subject_resolution": subject,
                    "linked_fact_resolution": fact_results.get(intent.fact_anchor)
                    if intent.fact_anchor
                    else None,
                    "subject_facts": [
                        fact
                        for fact in facts
                        if fact.get("subject_entity_id") == subject_id
                    ],
                }
            )
        witness_runs.append(
            {
                "repetition": repetition["index"],
                "identity_expectations": identities,
                "temporal_expectations": temporal_rows,
            }
        )
    witness = {
        "schema": "dmb_campaign_memory_baseline_witness_v1",
        "scoring": "none",
        "repetitions": witness_runs,
    }
    return qualification, witness


def render_report(q: dict[str, Any]) -> str:
    lines = ["# Campaign-memory baseline characterization", "", "## Scored", ""]
    for name, row in q["metrics"].items():
        lines.append(f"- {name}: `{row['values']}` (mean `{row['mean']:.4f}`)")
    lines += ["", "## Operations", ""]
    for name, row in q["operations"].items():
        lines.append(f"- {name}: `{row['values']}` (total `{sum(row['values']):.4f}`)")
    lines += [
        "",
        "Identity and temporal requirements are emitted in `witness_index.json` for inspection and are not scored.",
        "",
    ]
    return "\n".join(lines)
