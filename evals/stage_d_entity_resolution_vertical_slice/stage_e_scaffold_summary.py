"""Cohort summary writer for Stage E scaffold reports."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SLICE_DIR = Path(__file__).resolve().parent
_DEFAULT_GLOB = str(_SLICE_DIR / "scaffold" / "stage_e_hub_scaffold_*.json")


def _expand(pattern: str) -> list[Path]:
    p = Path(pattern)
    if p.is_absolute():
        base = Path("/")
        pat = str(p).lstrip("/")
    else:
        base = _SLICE_DIR.parents[1]
        pat = str(p)
    return sorted(base.glob(pat))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_stage_e_cohort_payload(reports: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(reports)
    passed = 0
    graded_runs = 0
    gate_ids = ("EE1", "EE2", "EE3")
    gate_pass_counts = {g: 0 for g in gate_ids}
    aggregate_violation_counts = {g: 0 for g in gate_ids}
    status_counts = {
        "preview_ok": 0,
        "preview_error": 0,
        "committed": 0,
        "commit_error": 0,
        "skipped_existing": 0,
    }
    runs: list[dict[str, Any]] = []

    for rep in reports:
        grading = rep.get("grading") or {}
        verdict = grading.get("per_gate_verdict") or {}
        vcounts = grading.get("violation_counts") or {}
        counts = rep.get("counts") or {}
        has_grading = bool(verdict)
        gates_passed = str(grading.get("gates_passed") or ("3/3" if has_grading and all(verdict.get(g) == "PASS" for g in gate_ids) else "ungraded"))
        if has_grading:
            graded_runs += 1
            if gates_passed == "3/3":
                passed += 1
            for g in gate_ids:
                if verdict.get(g) == "PASS":
                    gate_pass_counts[g] += 1
                aggregate_violation_counts[g] += int(vcounts.get(g) or 0)
        for k in status_counts:
            status_counts[k] += int(counts.get(k) or 0)
        runs.append(
            {
                "generated_at": rep.get("generated_at"),
                "campaign_id": rep.get("campaign_id"),
                "gates_passed": gates_passed,
                "per_gate_verdict": verdict,
                "violation_counts": vcounts,
                "counts": counts,
                "promotion_source": rep.get("promotion_source"),
            }
        )

    return {
        "schema": "stage_e_scaffold_cohort_summary_v1",
        "iso_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n": n,
        "graded_runs": graded_runs,
        "passed": passed,
        "per_gate_pass_counts": gate_pass_counts,
        "aggregate_violation_counts": aggregate_violation_counts,
        "aggregate_status_counts": status_counts,
        "runs": runs,
    }


def write_stage_e_cohort_summary(
    *,
    report_paths: list[Path],
    out_dir: Path | None = None,
) -> tuple[Path, Path]:
    reports = [_load(p) for p in report_paths]
    payload = build_stage_e_cohort_payload(reports)
    when = datetime.now(timezone.utc)
    stamp = when.strftime("%Y%m%dT%H%M%S") + "Z"
    base = f"stage_e_scaffold_summary--N{len(report_paths)}--{stamp}"
    root = out_dir or (_SLICE_DIR / "scaffold")
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / f"{base}.json"
    md_path = root / f"{base}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        f"# Stage E scaffold cohort summary ({payload['n']} runs)",
        "",
        f"- **pass rate (graded runs):** {payload['passed']}/{payload['graded_runs']}",
        "",
        "## Per-gate pass counts",
        "",
    ]
    for g in ("EE1", "EE2", "EE3"):
        lines.append(f"- {g}: {payload['per_gate_pass_counts'][g]}/{payload['graded_runs']}")
    lines.extend(["", "## Aggregate status counts", ""])
    for k, v in payload["aggregate_status_counts"].items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Runs", ""])
    for run in payload["runs"]:
        verdict = run.get("per_gate_verdict") or {}
        verdict_s = " ".join(f"{g}={verdict.get(g, '?')}" for g in ("EE1", "EE2", "EE3"))
        lines.append(
            f"- {run.get('generated_at')} | gates={run.get('gates_passed')} | {verdict_s} | {run.get('promotion_source')}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Stage E scaffold cohort summary.")
    parser.add_argument("--reports-glob", default=_DEFAULT_GLOB)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()
    paths = _expand(str(args.reports_glob))
    if not paths:
        raise SystemExit(f"No Stage E report files matched: {args.reports_glob}")
    md, js = write_stage_e_cohort_summary(report_paths=paths, out_dir=args.out_dir)
    print(json.dumps({"md_path": str(md), "json_path": str(js), "n": len(paths)}))


if __name__ == "__main__":
    main()
