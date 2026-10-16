"""Run each frozen synthetic case once through existing GE/TypeSafe Jev only."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from evals.graph_memory_layer.jev_controller_cohort import cases, score_case
from evals.graph_memory_layer.jev_evidence_loop import digest, run_loop


async def run_cohort(evaluate, output: Path):
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    cohort = cases()
    (output/'frozen-cohort.json').write_text(json.dumps(cohort, indent=2))
    rows = []
    for name, case in cohort.items():
        result = await run_loop(case['snapshot'], evaluate, output=output/name)
        score = score_case(result, case['gold'])
        row = {'case': name, **score, 'rounds': len(result['rounds']),
               'elapsed_seconds': result['elapsed_seconds'], 'usage_status': result['usage_status'],
               'input_tokens': result['input_tokens_reported'], 'output_tokens': result['output_tokens_reported']}
        rows.append(row)
        (output/name/'gold-evaluation.json').write_text(json.dumps(score, indent=2))
        # Persist completed cases even if a later independent case is interrupted.
        (output/'progress.json').write_text(json.dumps(rows, indent=2))
    report = {'cohort_sha256': digest(cohort), 'cases': rows, 'passed': sum(r['passed'] for r in rows),
              'total': len(rows), 'luna_calls': 0, 'retained_writes': 0,
              'provider_cost': 'unavailable_not_zero',
              'limits': ['Synthetic constructed holdouts with human requirements and seeds.',
                         'Whole-question variant probes manual decomposition dependence; it does not remove it.',
                         'Independent semantic review required; no answer writer or general accuracy claim.']}
    (output/'report.json').write_text(json.dumps(report, indent=2))
    return report


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credential-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    from dotenv import dotenv_values
    key = dotenv_values(args.credential_file).get('TYPESAFE_JEV_API_KEY')
    if not key:
        raise SystemExit('Jev credential unavailable; no provider calls attempted.')
    os.environ['TYPESAFE_JEV_API_KEY'] = key
    from generationengine import GenerationClient
    from generationengine.types import DecisionRequest
    client = GenerationClient.from_env()
    async def evaluate(request):
        response = await client.decide(DecisionRequest.model_validate(request))
        return response.model_dump(mode='json')
    try:
        report = await run_cohort(evaluate, args.output)
    finally:
        await client.aclose()
    print(json.dumps(report))


if __name__ == '__main__':
    asyncio.run(main())
