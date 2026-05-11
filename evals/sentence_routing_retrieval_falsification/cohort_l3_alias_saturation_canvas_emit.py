from __future__ import annotations

import argparse
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = _REPO_ROOT / "canvases/cohort-l3-alias-saturation.canvas.tsx"
BLOCK_BEGIN = "// BEGIN GENERATED COHORT_L3_ALIAS_SATURATION"
BLOCK_END = "// END GENERATED COHORT_L3_ALIAS_SATURATION"
VERDICTS = ("regressed", "improved", "unchanged_pass", "unchanged_fail")

TEMPLATE = '''import React from "react";

{block}

export default function CohortL3AliasSaturationCanvas() {{
  const payload = cohortL3AliasSaturationGenerated;
  const highlighted = payload.rows.filter((r: any) => r.verdict === "regressed" || r.verdict === "unchanged_fail");
  return (
    <div>
      <h1>Cohort L3 Alias Saturation</h1>
      <h2>Verdict counts</h2>
      <pre>{{JSON.stringify(payload.verdict_counts, null, 2)}}</pre>
      <h2>Promotion gate candidate</h2>
      <pre>{{JSON.stringify(payload.promotion_gate_candidate, null, 2)}}</pre>
      <h2>Regressed + unchanged_fail rows</h2>
      {{highlighted.map((r: any) => (
        <details key={{`${{r.scenario_id}}::${{r.question_id}}`}} open>
          <summary>{{r.scenario_id}} / {{r.question_id}} — {{r.verdict}} (alias_count={{r.alias_count}})</summary>
          <div><strong>alias_tokens_added:</strong> {{r.alias_tokens_added.length ? r.alias_tokens_added.join(", ") : "none"}}</div>
          <div><strong>contested_slot_unit_in:</strong> {{r.contested_slot_unit_in ?? "none"}}</div>
          <div><strong>contested_slot_unit_out:</strong> {{r.contested_slot_unit_out ?? "none"}}</div>
          <pre>{{JSON.stringify(r, null, 2)}}</pre>
        </details>
      ))}}
    </div>
  );
}}
'''


def _zero_counts() -> dict[str, int]:
    return {k: 0 for k in VERDICTS}


def build_payload(input_paths: list[Path]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    verdict_counts = _zero_counts()

    for input_path in input_paths:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        for scenario in data.get("scenarios", []):
            scenario_id = scenario.get("scenario_id")
            for question in scenario.get("questions", []):
                delta = question.get("delta", {})
                verdict = delta.get("verdict")
                if verdict in verdict_counts:
                    verdict_counts[verdict] += 1
                alias_tokens_added = delta.get("tokens_added_by_equivalences") or []
                topk_swapped_in = delta.get("topk_units_swapped_in") or []
                topk_swapped_out = delta.get("topk_units_swapped_out") or []
                rows.append(
                    {
                        "scenario_id": scenario_id,
                        "question_id": question.get("question_id"),
                        "verdict": verdict,
                        "alias_tokens_added": alias_tokens_added,
                        "alias_count": len(alias_tokens_added),
                        "topk_swapped_in": topk_swapped_in,
                        "topk_swapped_out": topk_swapped_out,
                        "contested_slot_unit_in": topk_swapped_in[0] if topk_swapped_in else None,
                        "contested_slot_unit_out": topk_swapped_out[0] if topk_swapped_out else None,
                        "support_ratio_delta": delta.get("support_ratio_delta", 0.0),
                    }
                )

    max_alias_count = max((row["alias_count"] for row in rows), default=0)
    threshold_scan: list[dict[str, object]] = []
    promotion_threshold: int | None = None

    for threshold in range(max_alias_count + 1):
        at_or_below = _zero_counts()
        above = _zero_counts()
        for row in rows:
            target = at_or_below if row["alias_count"] <= threshold else above
            verdict = row["verdict"]
            if verdict in target:
                target[verdict] += 1
        threshold_scan.append(
            {
                "threshold_alias_count": threshold,
                "at_or_below": at_or_below,
                "above": above,
            }
        )
        net_nonnegative_below = at_or_below["improved"] >= at_or_below["regressed"]
        no_regressed_above = above["regressed"] == 0
        if promotion_threshold is None and net_nonnegative_below and no_regressed_above:
            promotion_threshold = threshold

    status = "candidate_found" if promotion_threshold is not None else "none_found"
    return {
        "schema_id": "dmb_cohort_l3_alias_saturation_v1",
        "inputs": [str(p.relative_to(_REPO_ROOT)) if p.is_absolute() else str(p) for p in input_paths],
        "question_count": len(rows),
        "verdict_counts": verdict_counts,
        "rows": rows,
        "threshold_scan": threshold_scan,
        "promotion_gate_candidate": {
            "threshold_alias_count": promotion_threshold,
            "rule": "no_regressed_above_threshold_and_net_nonnegative_below",
            "status": status,
        },
    }


def emit(*, input_paths: list[Path], output_path: Path = DEFAULT_OUTPUT) -> int:
    payload = build_payload(input_paths)
    block = f"{BLOCK_BEGIN}\nconst cohortL3AliasSaturationGenerated = {json.dumps(payload, indent=2)} as const;\n{BLOCK_END}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(TEMPLATE.format(block=block), encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit cohort L3 alias saturation canvas")
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    return emit(input_paths=args.input, output_path=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
