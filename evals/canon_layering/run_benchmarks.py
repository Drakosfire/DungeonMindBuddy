from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
try:
    from src.contracts.schema_validation import validate_many
    from src.reducer.canon_projection import project_entity_state
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.contracts.schema_validation import validate_many
    from src.reducer.canon_projection import project_entity_state

EVAL_DIR = ROOT / "evals" / "canon_layering"
SCENARIOS_DIR = EVAL_DIR / "scenarios"
OUT_DIR = ROOT / "out" / "evals" / "canon_layering"
THRESHOLDS_PATH = EVAL_DIR / "thresholds.json"
MANIFEST_PATH = EVAL_DIR / "scenario_manifest.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_projection_for_compare(projection: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "campaign_id": projection.get("campaign_id"),
        "entities": {},
        "conflicts": projection.get("conflicts", []),
        "metrics": projection.get("metrics", {}),
    }
    for entity_id, entity_payload in projection.get("entities", {}).items():
        attrs: dict[str, Any] = {}
        for attr_name, attr_payload in entity_payload.get("attributes", {}).items():
            cleaned = dict(attr_payload)
            cleaned.pop("source_class", None)
            cleaned.pop("source_truth_state", None)
            cleaned.pop("all_value_labels", None)
            attrs[attr_name] = cleaned
        payload["entities"][entity_id] = {"attributes": attrs}
    return payload


def _run_scenario(scenario_id: str, campaign_id: str) -> dict[str, Any]:
    scenario_dir = SCENARIOS_DIR / scenario_id
    evidence_units = _load_json(scenario_dir / "input" / "evidence_units.json")
    facts = _load_json(scenario_dir / "input" / "facts.json")
    conflicts = _load_json(scenario_dir / "input" / "conflicts.json")
    canon_decisions = _load_json(scenario_dir / "input" / "canon_decisions.json")

    validate_many(evidence_units, "evidence_unit.schema.json")
    validate_many(facts, "fact.schema.json")
    validate_many(conflicts, "conflict.schema.json")
    validate_many(canon_decisions, "canon_decision.schema.json")

    started = time.perf_counter()
    world_projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=conflicts,
        canon_decisions=canon_decisions,
        campaign_id=None,
    )
    campaign_projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=conflicts,
        canon_decisions=canon_decisions,
        campaign_id=campaign_id,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    expected_world = _load_json(scenario_dir / "expected" / "world_projection.json")
    expected_campaign = _load_json(
        scenario_dir / "expected" / f"campaign_{campaign_id}_projection.json"
    )

    world_match = _normalize_projection_for_compare(world_projection) == expected_world
    campaign_match = _normalize_projection_for_compare(campaign_projection) == expected_campaign

    return {
        "scenario_id": scenario_id,
        "campaign_id": campaign_id,
        "elapsed_ms": round(elapsed_ms, 4),
        "world_match": world_match,
        "campaign_match": campaign_match,
        "pass": world_match and campaign_match,
        "world_projection": world_projection,
        "campaign_projection": campaign_projection,
        "expected_world": expected_world,
        "expected_campaign": expected_campaign,
    }


def _metric_layer_isolation(results: list[dict[str, Any]]) -> float:
    total = 0
    passed = 0
    for result in results:
        entities = result["world_projection"]["entities"]
        for entity_data in entities.values():
            for attr_data in entity_data["attributes"].values():
                total += 1
                if attr_data["source_layer"] == "world":
                    passed += 1
    return 1.0 if total == 0 else passed / total


def _metric_provenance_completeness(results: list[dict[str, Any]]) -> float:
    total = 0
    passed = 0
    for result in results:
        for projection_key in ["world_projection", "campaign_projection"]:
            entities = result[projection_key]["entities"]
            for entity_data in entities.values():
                for attr_data in entity_data["attributes"].values():
                    total += 1
                    if attr_data.get("provenance_evidence_ids"):
                        passed += 1
    return 1.0 if total == 0 else passed / total


def _metric_conflict_detection_seeded(results: list[dict[str, Any]]) -> float:
    expected_nonzero = 0
    passed = 0
    for result in results:
        expected_conflicts = len(result["expected_campaign"]["conflicts"])
        if expected_conflicts > 0:
            expected_nonzero += 1
            actual_conflicts = len(result["campaign_projection"]["conflicts"])
            if actual_conflicts == expected_conflicts:
                passed += 1
    return 1.0 if expected_nonzero == 0 else passed / expected_nonzero


def _metric_decision_scope(results: list[dict[str, Any]]) -> float:
    checks = 0
    passed = 0
    by_id = {result["scenario_id"]: result for result in results}
    for scenario_id in ["05_campaign_scoped_decision", "06_global_decision"]:
        if scenario_id not in by_id:
            continue
        checks += 1
        result = by_id[scenario_id]
        if result["world_match"] and result["campaign_match"]:
            passed += 1
    return 1.0 if checks == 0 else passed / checks


def _determinism_hashes(manifest: dict[str, Any], runs: int) -> list[str]:
    hashes: list[str] = []
    for _ in range(runs):
        payload: dict[str, Any] = {}
        for scenario in manifest["scenarios"]:
            result = _run_scenario(
                scenario_id=scenario["id"],
                campaign_id=scenario["campaign_id"],
            )
            payload[scenario["id"]] = {
                "world_projection": result["world_projection"],
                "campaign_projection": result["campaign_projection"],
            }
        hashes.append(_canonical_hash(payload))
    return hashes


def _render_report(results: list[dict[str, Any]], metrics: dict[str, float], thresholds: dict[str, float], determinism_hashes: list[str]) -> str:
    lines = ["# Canon Layer Benchmark Report", ""]
    lines.append("## Scenario Results")
    for result in results:
        status = "PASS" if result["pass"] else "FAIL"
        lines.append(
            f"- {result['scenario_id']}: {status} | world_match={result['world_match']} | campaign_match={result['campaign_match']} | elapsed_ms={result['elapsed_ms']}"
        )
    lines.append("")
    lines.append("## Metrics")
    for key, value in metrics.items():
        lines.append(f"- {key}: {value:.4f} (threshold {thresholds[key]:.4f})")
    lines.append("")
    lines.append("## Determinism")
    lines.append(f"- hashes: {', '.join(determinism_hashes)}")
    lines.append(
        f"- stable: {all(hash_value == determinism_hashes[0] for hash_value in determinism_hashes)}"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    manifest = _load_json(MANIFEST_PATH)
    thresholds = _load_json(THRESHOLDS_PATH)

    results: list[dict[str, Any]] = []
    for scenario in manifest["scenarios"]:
        results.append(
            _run_scenario(
                scenario_id=scenario["id"],
                campaign_id=scenario["campaign_id"],
            )
        )

    metrics = {
        "layer_isolation_accuracy": _metric_layer_isolation(results),
        "decision_scope_correctness": _metric_decision_scope(results),
        "provenance_completeness": _metric_provenance_completeness(results),
        "conflict_detection_seeded": _metric_conflict_detection_seeded(results),
    }
    determinism_hashes = _determinism_hashes(
        manifest=manifest,
        runs=int(thresholds["determinism_runs"]),
    )
    deterministic = all(
        hash_value == determinism_hashes[0] for hash_value in determinism_hashes
    )
    metrics["determinism_hash_match_rate"] = 1.0 if deterministic else 0.0

    phase_pass = all(result["pass"] for result in results) and all(
        metrics[key] >= thresholds[key] for key in metrics
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUT_DIR / "results.json"
    report_path = OUT_DIR / "report.md"
    determinism_path = OUT_DIR / "determinism_hash_report.json"
    results_payload = {
        "phase_pass": phase_pass,
        "results": [
            {
                key: value
                for key, value in result.items()
                if key
                in {
                    "scenario_id",
                    "campaign_id",
                    "elapsed_ms",
                    "world_match",
                    "campaign_match",
                    "pass",
                }
            }
            for result in results
        ],
        "metrics": metrics,
        "thresholds": thresholds,
    }
    results_path.write_text(
        json.dumps(results_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report_path.write_text(
        _render_report(
            results=results,
            metrics=metrics,
            thresholds=thresholds,
            determinism_hashes=determinism_hashes,
        ),
        encoding="utf-8",
    )
    determinism_path.write_text(
        json.dumps(
            {
                "runs": int(thresholds["determinism_runs"]),
                "hashes": determinism_hashes,
                "stable": deterministic,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    if not phase_pass:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

