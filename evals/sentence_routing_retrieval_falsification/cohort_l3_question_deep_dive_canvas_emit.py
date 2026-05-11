from __future__ import annotations
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT = _REPO_ROOT / 'evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json'
OUTPUT = _REPO_ROOT / 'canvases/cohort-l3-ab-question-deep-dive.canvas.tsx'
BLOCK_BEGIN = '// BEGIN GENERATED COHORT_L3_QUESTION_DEEP_DIVE'
BLOCK_END = '// END GENERATED COHORT_L3_QUESTION_DEEP_DIVE'

TEMPLATE = '''import React from "react";

{block}

export default function CohortL3QuestionDeepDiveCanvas() {{
  const payload = cohortL3QuestionDeepDiveGenerated;
  const renderUnitDiff = (q: any) => {{
    const topMissed = Array.isArray(q?.delta?.topk_units_swapped_out) ? q.delta.topk_units_swapped_out : [];
    const fullMissed = Array.isArray(q?.delta?.full_units_swapped_out) ? q.delta.full_units_swapped_out : [];
    const topAdded = Array.isArray(q?.delta?.topk_units_swapped_in) ? q.delta.topk_units_swapped_in : [];
    const fullAdded = Array.isArray(q?.delta?.full_units_swapped_in) ? q.delta.full_units_swapped_in : [];
    return (
      <div style={{{{ border: "1px solid #f59e0b", borderRadius: 6, padding: 8, marginBottom: 8 }}}}>
        <div><strong>Missed units (baseline only):</strong> {{fullMissed.length ? fullMissed.join(", ") : "none"}}</div>
        <div><strong>Top-5 missed units:</strong> {{topMissed.length ? topMissed.join(", ") : "none"}}</div>
        <div><strong>Units added (equivalence only):</strong> {{fullAdded.length ? fullAdded.join(", ") : "none"}}</div>
        <div><strong>Top-5 added units:</strong> {{topAdded.length ? topAdded.join(", ") : "none"}}</div>
      </div>
    );
  }};
  const renderMustHitComparison = (q: any, mode: "baseline" | "with_equivalence") => {{
    const required = Array.isArray(q.must_hit_tokens) ? q.must_hit_tokens : [];
    const matched = Array.isArray(q[mode]?.context_must_hits) ? q[mode].context_must_hits : [];
    const missing = Array.isArray(q[mode]?.context_must_hits_missing)
      ? q[mode].context_must_hits_missing
      : required.filter((tok: string) => !matched.includes(tok));
    return (
      <div>
        <div><strong>Required must-hit tokens:</strong> {{required.length ? required.join(", ") : "none"}}</div>
        <div><strong>Matched must-hit tokens:</strong> {{matched.length ? matched.join(", ") : "none"}}</div>
        <div><strong>Missing must-hit tokens:</strong> {{missing.length ? missing.join(", ") : "none"}}</div>
      </div>
    );
  }};
  return (
    <div>
      <h1>Cohort L3 Question Deep Dive</h1>
      <p>question_count: {{payload.question_count}}</p>
      {{payload.scenarios.flatMap((s: any) => s.questions).map((q: any) => (
        <details key={{q.question_id}} open={{q.delta.verdict === 'regressed' || q.delta.verdict === 'improved'}}>
          <summary>{{q.question_id}} — {{q.delta.verdict}}</summary>
          {{renderUnitDiff(q)}}
          <h3>Baseline</h3>
          {{renderMustHitComparison(q, "baseline")}}
          <h3>With Equivalence</h3>
          {{renderMustHitComparison(q, "with_equivalence")}}
          <pre>{{JSON.stringify(q, null, 2)}}</pre>
        </details>
      ))}}
    </div>
  );
}}
'''

def emit() -> int:
    data = json.loads(INPUT.read_text(encoding='utf-8'))
    block = f"{BLOCK_BEGIN}\nconst cohortL3QuestionDeepDiveGenerated = {json.dumps(data, indent=2)} as const;\n{BLOCK_END}"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(TEMPLATE.format(block=block), encoding='utf-8')
    return 0

if __name__ == '__main__':
    raise SystemExit(emit())
