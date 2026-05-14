from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import default_cursor_canvas_path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json"
DEFAULT_OUTPUT = default_cursor_canvas_path("cohort-l3-ab-question-deep-dive.canvas.tsx")
BLOCK_BEGIN = "// BEGIN GENERATED COHORT_L3_QUESTION_DEEP_DIVE"
BLOCK_END = "// END GENERATED COHORT_L3_QUESTION_DEEP_DIVE"

TEMPLATE = '''import React from "react";

{block}

export default function CohortL3QuestionDeepDiveCanvas() {{
  const payload = cohortL3QuestionDeepDiveGenerated;
  const cohortId = String(payload?.cohort_manifest || "").split("/").pop()?.replace(/\\.json$/i, "") || "unknown";
  const summary = payload?.summary || {{}};
  const scenario = Array.isArray(payload?.scenarios) && payload.scenarios.length > 0 ? payload.scenarios[0] : {{}};
  const failureSummary = payload?.failure_diagnostic_summary || {{}};

  const renderMustHitComparison = (q: any) => {{
    const required = Array.isArray(q?.must_hit_tokens) ? q.must_hit_tokens : [];
    const baselineMatched = Array.isArray(q?.baseline?.context_must_hits) ? q.baseline.context_must_hits : [];
    const baselineMissing = Array.isArray(q?.baseline?.context_must_hits_missing)
      ? q.baseline.context_must_hits_missing
      : required.filter((tok: string) => !baselineMatched.includes(tok));
    const defaultMatched = Array.isArray(q?.with_equivalence?.context_must_hits) ? q.with_equivalence.context_must_hits : [];
    const defaultMissing = Array.isArray(q?.with_equivalence?.context_must_hits_missing)
      ? q.with_equivalence.context_must_hits_missing
      : required.filter((tok: string) => !defaultMatched.includes(tok));

    return (
      <div style={{{{ border: "1px solid #e5e7eb", borderRadius: 6, padding: 8, marginBottom: 8 }}}}>
        <div><strong>Required must-hit tokens:</strong> {{required.length ? required.join(", ") : "none"}}</div>
        <div style={{{{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 6 }}}}>
          <div>
            <strong>Baseline</strong>
            <div>Matched: {{baselineMatched.length ? baselineMatched.join(", ") : "none"}}</div>
            <div>Missing: {{baselineMissing.length ? baselineMissing.join(", ") : "none"}}</div>
          </div>
          <div>
            <strong>Default</strong>
            <div>Matched: {{defaultMatched.length ? defaultMatched.join(", ") : "none"}}</div>
            <div>Missing: {{defaultMissing.length ? defaultMissing.join(", ") : "none"}}</div>
          </div>
        </div>
      </div>
    );
  }};

  const renderUnitDiff = (q: any) => {{
    const topMissed = Array.isArray(q?.delta?.topk_units_swapped_out) ? q.delta.topk_units_swapped_out : [];
    const fullMissed = Array.isArray(q?.delta?.full_units_swapped_out) ? q.delta.full_units_swapped_out : [];
    const topAdded = Array.isArray(q?.delta?.topk_units_swapped_in) ? q.delta.topk_units_swapped_in : [];
    const fullAdded = Array.isArray(q?.delta?.full_units_swapped_in) ? q.delta.full_units_swapped_in : [];
    return (
      <div style={{{{ border: "1px solid #f59e0b", borderRadius: 6, padding: 8, marginBottom: 8 }}}}>
        <div><strong>Swapped out vs legacy-only reference:</strong> {{fullMissed.length ? fullMissed.join(", ") : "none"}}</div>
        <div><strong>Top-5 swapped out:</strong> {{topMissed.length ? topMissed.join(", ") : "none"}}</div>
        <div><strong>Swapped in under default (equivalence) ranking:</strong> {{fullAdded.length ? fullAdded.join(", ") : "none"}}</div>
        <div><strong>Top-5 swapped in:</strong> {{topAdded.length ? topAdded.join(", ") : "none"}}</div>
      </div>
    );
  }};

  return (
    <div>
      <h1>Cohort L3 Question Deep Dive — {{cohortId}}</h1>
      <div>
        <p>question_count: {{payload.question_count}}</p>
        <p>summary.regressed: {{summary.regressed ?? 0}}</p>
        <p>summary.improved: {{summary.improved ?? 0}}</p>
        <p>summary.unchanged_pass: {{summary.unchanged_pass ?? 0}}</p>
        <p>summary.unchanged_fail: {{summary.unchanged_fail ?? 0}}</p>
        <p>scenario baseline_pass_count: {{scenario.baseline_pass_count ?? 0}}</p>
        <p>scenario with_equivalence_pass_count: {{scenario.with_equivalence_pass_count ?? 0}}</p>
      </div>
      <h2>failure_diagnostic_summary</h2>
      <ul>
        {{Object.entries(failureSummary).map(([k, v]) => (
          <li key={{k}}>{{k}}: {{String(v)}}</li>
        ))}}
      </ul>
      {{payload.scenarios.flatMap((s: any) => s.questions).map((q: any) => (
        <details key={{q.question_id}} open={{["regressed", "improved", "unchanged_fail"].includes(q.delta.verdict)}}>
          <summary>{{q.question_id}} — {{q.delta.verdict}}</summary>
          <div><strong>failure_diagnostic.bucket:</strong> {{q?.failure_diagnostic?.bucket || "n/a"}}</div>
          <div><strong>failure_diagnostic.reasons:</strong> {{Array.isArray(q?.failure_diagnostic?.reasons) && q.failure_diagnostic.reasons.length ? q.failure_diagnostic.reasons.join(", ") : "none"}}</div>
          <div><strong>support_ratio_delta:</strong> {{q?.delta?.support_ratio_delta ?? "n/a"}}</div>
          {{renderUnitDiff(q)}}
          {{(q.delta.verdict === "regressed" || q.delta.verdict === "unchanged_fail") && renderMustHitComparison(q)}}
          <h3>Default (equivalence-augmented ranking)</h3>
          <pre>{{JSON.stringify((() => {{ const {{ baseline, ...rest }} = q; return rest; }})(), null, 2)}}</pre>
        </details>
      ))}}
    </div>
  );
}}
'''


def emit(*, input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> int:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    block = f"{BLOCK_BEGIN}\nconst cohortL3QuestionDeepDiveGenerated = {json.dumps(data, indent=2)} as const;\n{BLOCK_END}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(TEMPLATE.format(block=block), encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit cohort L3 question deep dive canvas")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    return emit(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
