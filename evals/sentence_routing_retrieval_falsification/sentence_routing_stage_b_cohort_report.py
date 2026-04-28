"""Multi-run cohort summary for ``route_sentence_units_to_hubs`` (legacy: Stage B hub routing; cost + pass rate)."""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUMMARY_SCHEMA_VERSION = "sentence_routing_stage_b_cohort_summary_v1"


def _sanitize_filename_segment(raw: str, *, max_len: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", (raw or "").strip())
    s = s.strip("._-") or "model"
    return s[:max_len]


@dataclass
class StageBRunRecord:
    run_index: int
    gates_passed: bool
    scenario_estimated_cost_usd: float
    sidecar_json_path: str
    stage_b_violation_count: int
    routing_prompt_base_id: str | None = None
    routing_prompt_id: str | None = None
    stage_b_unit_breakdown: dict[str, Any] | None = None


def _common_nonempty(values: list[str | None]) -> str | None:
    cleaned = [str(v).strip() for v in values if str(v or "").strip()]
    if not cleaned:
        return None
    first = cleaned[0]
    return first if all(v == first for v in cleaned) else None


def build_cohort_payload(
    records: list[StageBRunRecord],
    *,
    model_id: str,
    scenario_id: str,
    prompt_variant: str | None = None,
) -> dict[str, Any]:
    n = len(records)
    costs = [r.scenario_estimated_cost_usd for r in records]
    passed_n = sum(1 for r in records if r.gates_passed)
    when = datetime.now(timezone.utc)
    common_prompt_base_id = _common_nonempty([r.routing_prompt_base_id for r in records])
    common_prompt_id = _common_nonempty([r.routing_prompt_id for r in records])
    payload: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA_VERSION,
        "iso_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_id": scenario_id,
        "model_id": model_id,
        "prompt_variant": prompt_variant,
        "routing_prompt_base_id": common_prompt_base_id,
        "routing_prompt_id": common_prompt_id,
        "n": n,
        "passed": passed_n,
        "pass_rate": round(passed_n / n, 6) if n else 0.0,
        "cost_usd": {
            "min": round(min(costs), 6) if costs else 0.0,
            "max": round(max(costs), 6) if costs else 0.0,
            "mean": round(statistics.mean(costs), 6) if costs else 0.0,
            "sum": round(sum(costs), 6),
        },
        "cost_baseline_note": (
            "First cohort establishes baseline; flag regression if cohort sum or any run "
            "exceeds 1.5x prior (see cost-as-signal.mdc)."
        ),
        "runs": [
            {
                "run_index": r.run_index,
                "gates_passed": r.gates_passed,
                "cost_usd": r.scenario_estimated_cost_usd,
                "sidecar_json": r.sidecar_json_path,
                "stage_b_violation_count": r.stage_b_violation_count,
                "routing_prompt_base_id": r.routing_prompt_base_id,
                "routing_prompt_id": r.routing_prompt_id,
                **(
                    {"stage_b_unit_breakdown": r.stage_b_unit_breakdown}
                    if r.stage_b_unit_breakdown is not None
                    else {}
                ),
            }
            for r in records
        ],
    }
    return payload


def write_stage_b_cohort_summary(
    records: list[StageBRunRecord],
    *,
    model_id: str,
    scenario_id: str,
    runs_root: Path | None = None,
    prompt_variant: str | None = None,
) -> tuple[Path, Path]:
    """Write JSON + Markdown cohort summary under ``runs_root/<YYYY-MM-DD>/``."""
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    n = len(records)
    mod = _sanitize_filename_segment(model_id)
    pv_seg = f"--pv-{_sanitize_filename_segment(prompt_variant)}" if prompt_variant else ""
    base = f"sentence_routing_stage_b_cohort_summary--{mod}{pv_seg}--N{n}--{iso_compact}"
    root = (runs_root or Path(__file__).resolve().parent / "artifacts" / "runs").resolve()
    day_dir = root / when.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    json_path = day_dir / f"{base}.json"
    md_path = day_dir / f"{base}.md"

    payload = build_cohort_payload(
        records,
        model_id=model_id,
        scenario_id=scenario_id,
        prompt_variant=prompt_variant,
    )
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    costs = payload["cost_usd"]
    md_lines = [
        f"# route_sentence_units_to_hubs — cohort summary (legacy: Stage B; {n} runs)",
        "",
        f"- **model:** `{model_id}`",
        f"- **scenario:** `{scenario_id}`",
        f"- **prompt_variant:** `{prompt_variant}`",
        f"- **routing_prompt_base_id:** `{payload.get('routing_prompt_base_id')}`",
        f"- **routing_prompt_id:** `{payload.get('routing_prompt_id')}`",
    ]
    md_lines.extend(
        [
            f"- **pass rate:** {payload['passed']}/{n}",
            f"- **Cost:** sum ${costs['sum']:.4f} | mean ${costs['mean']:.4f} | min ${costs['min']:.4f} | max ${costs['max']:.4f}",
            "",
            str(payload["cost_baseline_note"]),
            "",
            "## Runs",
            "",
        ]
    )
    for r in records:
        md_lines.append(
            f"- run {r.run_index + 1}: {'PASS' if r.gates_passed else 'FAIL'} "
            f"| ${r.scenario_estimated_cost_usd:.4f} "
            f"| violations={r.stage_b_violation_count} "
            f"| `{r.sidecar_json_path}`"
        )
        ub = r.stage_b_unit_breakdown
        if isinstance(ub, dict):
            mr = ub.get("must_route") or {}
            ma = ub.get("must_abstain") or {}
            bk = ub.get("violation_failure_buckets") or {}
            md_lines.append(
                "  - **units:** "
                f"{ub.get('sentence_unit_count', '?')} sentence_units total; "
                f"{ub.get('gold_pinned_distinct_unit_count', '?')} distinct gold-pinned; "
                f"{ub.get('unpinned_sentence_unit_count', '?')} unpinned (no must_route/must_abstain row)."
            )
            md_lines.append(
                "  - **gold checks:** "
                f"must_route {mr.get('pass', '?')}/{mr.get('gold_checks', '?')} pass; "
                f"must_abstain {ma.get('pass', '?')}/{ma.get('gold_checks', '?')} pass; "
                f"all gates {ub.get('gold_gate_checks_pass', '?')}/"
                f"{ub.get('gold_gate_checks_total', '?')} pass."
            )
            md_lines.append(
                "  - **violation buckets (line counts):** "
                f"b0={bk.get('b0_schema_row_integrity', 0)}, "
                f"b0_bad_diag={bk.get('b0_invalid_diagnostic_with_assigned_hubs', 0)}, "
                f"b0_diag_null={bk.get('b0_diagnostic_null_when_assigned', 0)}, "
                f"b1_missing={bk.get('b1_missing_expected_hub', 0)}, "
                f"b1_over={bk.get('b1_over_route', 0)}, "
                f"b2_assign={bk.get('b2_over_assigned', 0)}, "
                f"b2_candidate={bk.get('b2_needs_new_hub_candidate', 0)}, "
                f"bd_diag={bk.get('bd_diagnostic_bucket', 0)}, "
                f"other={bk.get('non_gate', 0)}."
            )
            dbexp = ub.get("diagnostic_bucket_expectations") or {}
            if isinstance(dbexp, dict) and dbexp.get("defined"):
                md_lines.append(
                    "  - **diagnostic buckets (gold expectations):** "
                    f"{dbexp.get('pass', '?')}/{dbexp.get('defined', '?')} pass "
                    f"(enforce={dbexp.get('enforce', '?')})."
                )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path
