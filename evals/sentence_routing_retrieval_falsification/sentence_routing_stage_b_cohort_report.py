"""Multi-run cohort summary for Stage B hub routing (cost + pass rate)."""

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


def build_cohort_payload(
    records: list[StageBRunRecord],
    *,
    model_id: str,
    scenario_id: str,
) -> dict[str, Any]:
    n = len(records)
    costs = [r.scenario_estimated_cost_usd for r in records]
    passed_n = sum(1 for r in records if r.gates_passed)
    when = datetime.now(timezone.utc)
    return {
        "schema": SUMMARY_SCHEMA_VERSION,
        "iso_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_id": scenario_id,
        "model_id": model_id,
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
            }
            for r in records
        ],
    }


def write_stage_b_cohort_summary(
    records: list[StageBRunRecord],
    *,
    model_id: str,
    scenario_id: str,
    runs_root: Path | None = None,
) -> tuple[Path, Path]:
    """Write JSON + Markdown cohort summary under ``runs_root/<YYYY-MM-DD>/``."""
    when = datetime.now(timezone.utc)
    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    n = len(records)
    mod = _sanitize_filename_segment(model_id)
    base = f"sentence_routing_stage_b_cohort_summary--{mod}--N{n}--{iso_compact}"
    root = (runs_root or Path(__file__).resolve().parent / "artifacts" / "runs").resolve()
    day_dir = root / when.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    json_path = day_dir / f"{base}.json"
    md_path = day_dir / f"{base}.md"

    payload = build_cohort_payload(records, model_id=model_id, scenario_id=scenario_id)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    costs = payload["cost_usd"]
    md_lines = [
        f"# Stage B hub routing — cohort summary ({n} runs)",
        "",
        f"- **model:** `{model_id}`",
        f"- **scenario:** `{scenario_id}`",
        f"- **pass rate:** {payload['passed']}/{n}",
        f"- **Cost:** sum ${costs['sum']:.4f} | mean ${costs['mean']:.4f} | min ${costs['min']:.4f} | max ${costs['max']:.4f}",
        "",
        payload["cost_baseline_note"],
        "",
        "## Runs",
        "",
    ]
    for r in records:
        md_lines.append(
            f"- run {r.run_index + 1}: {'PASS' if r.gates_passed else 'FAIL'} "
            f"| ${r.scenario_estimated_cost_usd:.4f} "
            f"| violations={r.stage_b_violation_count} "
            f"| `{r.sidecar_json_path}`"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path
