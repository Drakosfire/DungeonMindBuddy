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
  return (
    <div>
      <h1>Cohort L3 Question Deep Dive</h1>
      <p>question_count: {{payload.question_count}}</p>
      {{payload.scenarios.flatMap((s: any) => s.questions).map((q: any) => (
        <details key={{q.question_id}} open={{q.delta.verdict === 'regressed' || q.delta.verdict === 'improved'}}>
          <summary>{{q.question_id}} — {{q.delta.verdict}}</summary>
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
