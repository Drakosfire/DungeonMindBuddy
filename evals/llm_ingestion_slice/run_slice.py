from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

validate_many = importlib.import_module("src.contracts.schema_validation").validate_many
campaign_temporal_tick_violations = importlib.import_module(
    "src.contracts.temporal_tick_gate"
).campaign_temporal_tick_violations
campaign_temporal_consistency_violations = importlib.import_module(
    "src.contracts.temporal_tick_gate"
).campaign_temporal_consistency_violations
campaign_temporal_quality_summary = importlib.import_module(
    "src.contracts.temporal_tick_gate"
).campaign_temporal_quality_summary
build_mirathorn_event_slice = importlib.import_module(
    "src.ingestion.event_sourced_slice"
).build_mirathorn_event_slice

EVAL_DIR = ROOT / "evals" / "llm_ingestion_slice"
GOLD_DIR = EVAL_DIR / "gold"
OUTPUT_DIR = EVAL_DIR / "output" / "current"
MANIFEST_PATH = EVAL_DIR / "slice_manifest.json"
VIABILITY_THRESHOLDS_PATH = EVAL_DIR / "viability_thresholds.json"
GOLD_SCORE_THRESHOLDS = {
    "min_core_recall": 0.10,
    "min_temporal_accuracy": 1.0,
    "min_catalog_recall": 1.0,
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_viability_thresholds() -> dict[str, Any]:
    payload = _load_json(VIABILITY_THRESHOLDS_PATH)
    required_keys = (
        "min_entity_density",
        "max_duplicate_fact_ratio",
        "min_conflicts",
        "max_conflicts",
    )
    missing = [key for key in required_keys if key not in payload]
    if missing:
        missing_csv = ", ".join(sorted(missing))
        raise ValueError(f"viability threshold config missing keys: {missing_csv}")
    return payload


def _load_sources(manifest: dict[str, Any]) -> tuple[str, str]:
    world_rel = manifest["sources"]["world_markdown"]["path"]
    campaign_rel = manifest["sources"]["campaign_markdown"]["path"]
    world_path = ROOT / world_rel
    campaign_path = ROOT / campaign_rel
    return world_path.read_text(encoding="utf-8"), campaign_path.read_text(encoding="utf-8")


def _gate_a_source_layer_integrity(
    *,
    manifest: dict[str, Any],
    evidence_units: list[dict[str, Any]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    source_errors: list[str] = []

    for source_key in ("world_markdown", "campaign_markdown"):
        source_def = manifest["sources"][source_key]
        source_path = ROOT / source_def["path"]
        exists = source_path.exists()
        digest = _sha256(source_path) if exists else None
        expected = source_def["sha256"]
        match = exists and digest == expected
        checks.append(
            {
                "source_key": source_key,
                "path": source_def["path"],
                "exists": exists,
                "sha256": digest,
                "expected_sha256": expected,
                "match": match,
            }
        )
        if not match:
            source_errors.append(f"{source_key} fingerprint mismatch")

    layer_errors: list[str] = []
    for row in evidence_units:
        layer = row["canon_layer"]
        campaign_id = row.get("campaign_id")
        if layer == "world" and campaign_id is not None:
            layer_errors.append(f"{row['evidence_id']} world evidence has campaign_id")
        if layer == "campaign" and not campaign_id:
            layer_errors.append(f"{row['evidence_id']} campaign evidence missing campaign_id")

    passed = not source_errors and not layer_errors
    return {
        "name": "Gate A - source and layer integrity",
        "pass": passed,
        "source_checks": checks,
        "source_errors": source_errors,
        "layer_errors": layer_errors,
    }


def _gate_b_event_contract_integrity(events: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_many(events, "event.schema.json")
    except Exception as exc:  # pragma: no cover - surfaced by test failures if triggered.
        errors.append(f"event schema validation failed: {exc}")

    for event in events:
        if not event.get("participants"):
            errors.append(f"{event['event_id']} missing participants")
        if not event.get("source_evidence_ids"):
            errors.append(f"{event['event_id']} missing source_evidence_ids")

    expected_order = sorted(
        events,
        key=lambda item: (
            int(item["sequence_index_within_session"]),
            str(item["event_id"]),
        ),
    )
    deterministic_order = [item["event_id"] for item in events] == [
        item["event_id"] for item in expected_order
    ]
    if not deterministic_order:
        errors.append("event ordering is not deterministic")

    return {
        "name": "Gate B - event contract integrity",
        "pass": not errors,
        "errors": errors,
        "event_count": len(events),
    }


def _fact_value_key(value: Any) -> str:
    if isinstance(value, dict):
        normalized = value.get("normalized")
        if normalized is not None:
            return str(normalized)
        label = value.get("label")
        if label is not None:
            return str(label)
        return json.dumps(value, sort_keys=True)
    return str(value)


def _gate_extraction_viability(
    *,
    evidence_units: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    evidence_count = len(evidence_units)
    unique_entity_ids = {
        entity.get("entity_id")
        for entity in entities
        if isinstance(entity.get("entity_id"), str) and entity.get("entity_id")
    }
    unique_entity_count = len(unique_entity_ids)
    entity_density = (
        float(unique_entity_count) / float(evidence_count) if evidence_count > 0 else 0.0
    )

    total_facts = len(facts)
    fact_keys: set[tuple[str, str, str]] = set()
    for fact in facts:
        subject_entity_id = str(fact.get("subject_entity_id") or "")
        attribute = str(fact.get("attribute") or "")
        normalized_or_label = _fact_value_key(fact.get("value"))
        fact_keys.add((subject_entity_id, attribute, normalized_or_label))
    unique_fact_keys = len(fact_keys)
    duplicate_fact_ratio = (
        float(total_facts - unique_fact_keys) / float(total_facts) if total_facts > 0 else 0.0
    )

    conflict_count = len(conflicts)

    min_entity_density = float(thresholds["min_entity_density"])
    max_duplicate_fact_ratio = float(thresholds["max_duplicate_fact_ratio"])
    min_conflicts = int(thresholds["min_conflicts"])
    max_conflicts = int(thresholds["max_conflicts"])

    if evidence_count == 0:
        errors.append("evidence_units count is 0")
    if unique_entity_count == 0:
        errors.append("unique entity_id count is 0")
    if entity_density < min_entity_density:
        errors.append(
            f"entity_density {entity_density:.6f} below minimum {min_entity_density:.6f}"
        )

    if total_facts == 0:
        errors.append("facts count is 0")
    if duplicate_fact_ratio > max_duplicate_fact_ratio:
        errors.append(
            "duplicate_fact_ratio "
            f"{duplicate_fact_ratio:.6f} above maximum {max_duplicate_fact_ratio:.6f}"
        )

    if conflict_count < min_conflicts:
        errors.append(f"conflict_count {conflict_count} below minimum {min_conflicts}")
    if conflict_count > max_conflicts:
        errors.append(f"conflict_count {conflict_count} above maximum {max_conflicts}")

    return {
        "name": "Gate V - extraction viability",
        "pass": not errors,
        "errors": errors,
        "metrics": {
            "entity_density": entity_density,
            "duplicate_fact_ratio": duplicate_fact_ratio,
            "conflict_volume_band": conflict_count,
            "counts": {
                "evidence_units": evidence_count,
                "unique_entity_ids": unique_entity_count,
                "facts": total_facts,
                "unique_fact_keys": unique_fact_keys,
                "conflicts": conflict_count,
            },
        },
        "thresholds": {
            "min_entity_density": min_entity_density,
            "max_duplicate_fact_ratio": max_duplicate_fact_ratio,
            "min_conflicts": min_conflicts,
            "max_conflicts": max_conflicts,
        },
    }


def _gate_c_hybrid_correctness(
    *,
    run_payload: dict[str, Any],
    gold_payload: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    run_fact_ids = sorted(entry["fact_id"] for entry in run_payload["facts"])
    gold_fact_ids = sorted(entry["fact_id"] for entry in gold_payload["facts"])
    if run_fact_ids != gold_fact_ids:
        errors.append("fact id set mismatch versus gold")

    run_conflict_ids = sorted(entry["conflict_id"] for entry in run_payload["conflicts"])
    gold_conflict_ids = sorted(entry["conflict_id"] for entry in gold_payload["conflicts"])
    if run_conflict_ids != gold_conflict_ids:
        errors.append("conflict set mismatch versus gold")

    live_attr = (
        run_payload["projection_live_state"]
        .get("entities", {})
        .get("ent_mirathorn", {})
        .get("attributes", {})
        .get("atmosphere", {})
    )
    if live_attr.get("value_normalized") != "gate_protest_pressure":
        errors.append("live projection missing campaign atmosphere override")

    inst_governance = (
        run_payload["projection_instantiation"]
        .get("entities", {})
        .get("ent_mirathorn", {})
        .get("attributes", {})
        .get("governance", {})
        .get("value_normalized")
    )
    live_governance = (
        run_payload["projection_live_state"]
        .get("entities", {})
        .get("ent_mirathorn", {})
        .get("attributes", {})
        .get("governance", {})
        .get("value_normalized")
    )
    if not inst_governance or inst_governance != live_governance:
        errors.append("world baseline governance mutated across stages")

    return {
        "name": "Gate C - hybrid correctness",
        "pass": not errors,
        "errors": errors,
    }


def _gate_d_workflow_state_progression(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for key in (
        "projection_instantiation",
        "projection_zero_tick",
        "projection_live_state",
    ):
        if not payload.get(key):
            errors.append(f"missing {key}")

    deltas = payload.get("projection_deltas", {})
    first = deltas.get("instantiation_to_zero_tick", [])
    second = deltas.get("zero_tick_to_live_state", [])
    if not first:
        errors.append("missing auditable delta instantiation->zero_tick")
    if not second:
        errors.append("missing auditable delta zero_tick->live_state")

    return {
        "name": "Gate D - workflow state progression",
        "pass": not errors,
        "errors": errors,
        "delta_counts": {
            "instantiation_to_zero_tick": len(first),
            "zero_tick_to_live_state": len(second),
        },
    }


def _gate_temporal_narrative_tick(
    *,
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    errors = campaign_temporal_tick_violations(evidence_units, facts)
    return {
        "name": "Gate T - narrative temporal tick",
        "pass": not errors,
        "errors": errors,
        "fact_count": len(facts),
    }


def _gate_temporal_consistency(
    *,
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    errors = campaign_temporal_consistency_violations(evidence_units, facts)
    return {
        "name": "Gate TC - campaign temporal consistency",
        "pass": not errors,
        "errors": errors,
        "fact_count": len(facts),
    }


def _gate_temporal_quality_warning(
    *,
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    quality = campaign_temporal_quality_summary(evidence_units, facts)
    return {
        "name": "Gate TW - sequence-only temporal warning",
        "pass": True,
        "warnings": quality["warnings"],
        "metrics": quality["metrics"],
        "fact_count": len(facts),
    }


def _gate_g_gold_scoring(
    *,
    stage_entities: list[dict[str, Any]],
    stage_facts: list[dict[str, Any]],
    stage_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_module = __import__("evals.llm_ingestion_slice.score_gold", fromlist=["GOLD_PATH", "_load_json", "score"])
    gold = gold_module._load_json(gold_module.GOLD_PATH)
    score_report = gold_module.score(
        gold=gold,
        stage_entities_payload=stage_entities,
        stage_facts=stage_facts,
        stage_chunks=stage_chunks,
        eval_mode="deterministic_slice",
        min_core_recall=float(GOLD_SCORE_THRESHOLDS["min_core_recall"]),
        min_temporal_accuracy=float(GOLD_SCORE_THRESHOLDS["min_temporal_accuracy"]),
        min_catalog_recall=float(GOLD_SCORE_THRESHOLDS["min_catalog_recall"]),
    )
    failed_subgates = [
        gate["name"] for gate in score_report["pass_fail"]["gates"] if not bool(gate.get("pass"))
    ]
    errors = [f"failed gold sub-gates: {', '.join(failed_subgates)}"] if failed_subgates else []
    return {
        "name": "Gate G - gold scoring",
        "pass": bool(score_report["pass_fail"]["overall_pass"]),
        "errors": errors,
        "metrics": {
            "core_recall": score_report["entity_metrics"]["core"]["metrics"]["recall"],
            "temporal_field_accuracy": score_report["temporal"]["metrics"]["field_accuracy"],
            "catalog_recall": score_report["catalog_recall"]["metrics"]["recall"],
            "negative_violations": len(score_report["negative_examples"]["violations"]),
        },
        "thresholds": GOLD_SCORE_THRESHOLDS,
        "subgates": score_report["pass_fail"]["gates"],
        "score_report": score_report,
    }


def _render_report(gates: list[dict[str, Any]]) -> str:
    lines = ["# Mirathorn LLM Ingestion Slice Report", ""]
    overall = all(gate["pass"] for gate in gates)
    lines.append(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    lines.append("")
    for gate in gates:
        lines.append(f"## {gate['name']}")
        lines.append(f"- status: {'PASS' if gate['pass'] else 'FAIL'}")
        errors = gate.get("errors", [])
        if errors:
            for error in errors:
                lines.append(f"- error: {error}")
        warnings = gate.get("warnings", [])
        if warnings:
            for warning in warnings:
                lines.append(f"- warning: {warning}")
        if gate.get("metrics"):
            lines.append(f"- metrics: {json.dumps(gate['metrics'], sort_keys=True)}")
        if gate.get("thresholds"):
            lines.append(f"- thresholds: {json.dumps(gate['thresholds'], sort_keys=True)}")
        if gate.get("delta_counts"):
            lines.append(f"- deltas: {json.dumps(gate['delta_counts'], sort_keys=True)}")
        lines.append("")
    return "\n".join(lines)


def run_slice() -> dict[str, Any]:
    manifest = _load_json(MANIFEST_PATH)
    world_text, campaign_text = _load_sources(manifest)
    campaign_id = manifest["campaign_id"]
    payload = build_mirathorn_event_slice(
        world_text=world_text,
        campaign_text=campaign_text,
        campaign_id=campaign_id,
    )

    validate_many(payload["evidence_units"], "evidence_unit.schema.json")
    validate_many(payload["entities"], "entity.schema.json")
    validate_many(payload["events"], "event.schema.json")
    validate_many(payload["facts"], "fact.schema.json")
    validate_many(payload["conflicts"], "conflict.schema.json")
    validate_many(payload["canon_decisions"], "canon_decision.schema.json")

    return payload


def main() -> int:
    run_payload = run_slice()
    manifest = _load_json(MANIFEST_PATH)
    viability_thresholds = _load_viability_thresholds()
    gold_payload = {
        "evidence_units": _load_json(GOLD_DIR / "evidence_units.json"),
        "events": _load_json(GOLD_DIR / "events.json"),
        "facts": _load_json(GOLD_DIR / "facts.json"),
        "conflicts": _load_json(GOLD_DIR / "conflicts.json"),
        "canon_decisions": _load_json(GOLD_DIR / "canon_decisions.json"),
    }

    gate_a = _gate_a_source_layer_integrity(
        manifest=manifest,
        evidence_units=run_payload["evidence_units"],
    )
    gate_v = _gate_extraction_viability(
        evidence_units=run_payload["evidence_units"],
        entities=run_payload["entities"],
        facts=run_payload["facts"],
        conflicts=run_payload["conflicts"],
        thresholds=viability_thresholds,
    )
    gate_t = _gate_temporal_narrative_tick(
        evidence_units=run_payload["evidence_units"],
        facts=run_payload["facts"],
    )
    gate_tc = _gate_temporal_consistency(
        evidence_units=run_payload["evidence_units"],
        facts=run_payload["facts"],
    )
    gate_tw = _gate_temporal_quality_warning(
        evidence_units=run_payload["evidence_units"],
        facts=run_payload["facts"],
    )
    gates = [gate_a, gate_v, gate_t, gate_tc, gate_tw]

    if gate_a["pass"] and gate_v["pass"] and gate_t["pass"] and gate_tc["pass"]:
        gate_b = _gate_b_event_contract_integrity(run_payload["events"])
        gate_c = _gate_c_hybrid_correctness(run_payload=run_payload, gold_payload=gold_payload)
        gate_d = _gate_d_workflow_state_progression(run_payload)
        gate_g = _gate_g_gold_scoring(
            stage_entities=run_payload["stage_artifacts"]["entities"],
            stage_facts=run_payload["stage_artifacts"]["facts"],
            stage_chunks=run_payload["stage_artifacts"]["chunks"],
        )
        gates.extend([gate_b, gate_c, gate_d, gate_g])

    overall_pass = all(gate["pass"] for gate in gates)

    _write_json(OUTPUT_DIR / "run_payload.json", run_payload)
    _write_json(OUTPUT_DIR / "gate_report.json", {"overall_pass": overall_pass, "gates": gates})
    _write_json(OUTPUT_DIR / "stage_chunks.json", run_payload["stage_artifacts"]["chunks"])
    _write_json(OUTPUT_DIR / "stage_entities.json", run_payload["stage_artifacts"]["entities"])
    _write_json(OUTPUT_DIR / "stage_facts.json", run_payload["stage_artifacts"]["facts"])
    _write_json(OUTPUT_DIR / "stage_events.json", run_payload["stage_artifacts"]["events"])
    _write_json(
        OUTPUT_DIR / "projection_deltas.json",
        run_payload["projection_deltas"],
    )
    gate_g_payload = next((gate for gate in gates if gate["name"] == "Gate G - gold scoring"), None)
    if gate_g_payload is not None:
        _write_json(OUTPUT_DIR / "gold_score.json", gate_g_payload["score_report"])
    (OUTPUT_DIR / "report.md").write_text(_render_report(gates), encoding="utf-8")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
