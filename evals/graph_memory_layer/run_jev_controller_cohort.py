"""Run each frozen synthetic case once through existing GE/TypeSafe Jev only."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from evals.graph_memory_layer.jev_controller_cohort import cases, challenge_cases, coverage_cases, score_case
from evals.graph_memory_layer.jev_evidence_loop import digest, run_loop


async def run_cohort(evaluate, output: Path, *, question_only=False, challenge_before_stop=False, coverage_before_stop=False):
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    cohort = cases()
    if challenge_before_stop or coverage_before_stop:
        cohort.update(challenge_cases())
    if coverage_before_stop:
        cohort.update(coverage_cases())
    (output/'frozen-cohort.json').write_text(json.dumps(cohort, indent=2))
    rows, inputs_seen = [], set()
    for name, case in cohort.items():
        if question_only:
            identity = digest({k: v for k, v in case['snapshot'].items()
                               if k not in {'requirements', 'initial_actions'}})
            if identity in inputs_seen:
                continue
            inputs_seen.add(identity)
        result = await run_loop(case['snapshot'], evaluate, output=output/name, question_only=question_only, challenge_before_stop=challenge_before_stop, coverage_before_stop=coverage_before_stop)
        score = score_case(result, case['gold'])
        row = {'case': name, **score, 'rounds': len(result['rounds']), 'decision_calls_reported': len(result['observations']),
               'elapsed_seconds': result['elapsed_seconds'], 'usage_status': result['usage_status'],
               'input_tokens': result['input_tokens_reported'], 'output_tokens': result['output_tokens_reported']}
        rows.append(row)
        (output/name/'gold-evaluation.json').write_text(json.dumps(score, indent=2))
        # Persist completed cases even if a later independent case is interrupted.
        (output/'progress.json').write_text(json.dumps(rows, indent=2))
    report = {'cohort_sha256': digest(cohort), 'cases': rows, 'passed': sum(r['passed'] for r in rows),
              'total': len(rows), 'luna_calls': 0, 'retained_writes': 0, 'question_only': question_only, 'challenge_before_stop': challenge_before_stop, 'coverage_before_stop': coverage_before_stop,
              'provider_cost': 'unavailable_not_zero',
              'limits': ['Synthetic constructed holdouts; question-only mode replaces manual requirements and seeds.' if question_only else 'Synthetic constructed holdouts with human requirements and seeds.',
                         'Whole-question variant probes manual decomposition dependence; it does not remove it.',
                         'Independent semantic review required; no answer writer or general accuracy claim.']}
    (output/'report.json').write_text(json.dumps(report, indent=2))
    return report


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credential-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--question-only', action='store_true')
    stopping = parser.add_mutually_exclusive_group()
    stopping.add_argument('--challenge-before-stop', action='store_true')
    stopping.add_argument('--coverage-before-stop', action='store_true')
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
        report = await run_cohort(evaluate, args.output, question_only=args.question_only, challenge_before_stop=args.challenge_before_stop, coverage_before_stop=args.coverage_before_stop)
    finally:
        await client.aclose()
    print(json.dumps(report))


if __name__ == '__main__':
    asyncio.run(main())
