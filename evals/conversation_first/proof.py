"""Real-provider isolated proof. Not a runtime workflow or a tool execution test."""
from __future__ import annotations

import argparse
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path
import time

import jsonschema

from .cases import cases
from .scaffold import REPLY_SCHEMA, WRITER, decision_request, frame


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return sha256(canonical(value).encode()).hexdigest()


def choose(result):
    answer = result['answers']['next_step']
    scores = answer['probabilities']
    options = {'converse', 'research', 'write', 'image'}
    if set(scores) != options or answer['selected'] not in options:
        raise ValueError('Invalid next-step domain')
    import math
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values()):
        raise ValueError('Invalid next-step probabilities')
    if abs(sum(scores.values()) - 1) > .02:
        raise ValueError('Invalid probability mass')
    best = max(scores.values())
    if scores[answer['selected']] != best or sum(v == best for v in scores.values()) != 1:
        raise ValueError('No unique selected next step')
    return answer['selected']


async def one(case, repeat, decide, write):
    row = {'case_id': case['id'], 'repeat': repeat, 'calls': [], 'passed': False}
    started = time.perf_counter()
    try:
        request = decision_request(case)
        decision = {'role': 'controller', 'request': request, 'response': None}
        row['calls'].append(decision)
        decision['response'] = await decide(request, decision)
        selected = choose(decision['response'])
        row.update(selected=selected, expected_step=case['expected_step'])
        row['passed'] = selected == case['expected_step']
        # Never substitute the gold route to force a conversational output.
        if selected == 'converse':
            reply = {'role': 'writer', 'input': frame(case), 'response': None}
            row['calls'].append(reply)
            reply['response'] = await write(reply['input'], reply)
            jsonschema.validate(reply['response']['output'], REPLY_SCHEMA)
            count = case['expected_questions']
            row['question_count_passed'] = count is None or len(reply['response']['output']['questions']) == count
            row['passed'] &= row['question_count_passed']
            # Ablate only workflow discovery on the two chain-shaped cases. Same writer instructions.
            if case['id'] in {'ask_first_chain', 'correct_wrong_surface'}:
                ablation = {'role': 'writer_without_catalog', 'input': frame(case, include_workflow=False), 'response': None}
                row['calls'].append(ablation)
                ablation['response'] = await write(ablation['input'], ablation)
                jsonschema.validate(ablation['response']['output'], REPLY_SCHEMA)
    except Exception as exc:
        row.update(passed=False, error=type(exc).__name__, error_message=str(exc)[:500])
    row['elapsed_ms'] = round((time.perf_counter() - started) * 1000)
    return row


async def run(output, decide, write, repeats=2):
    frozen_cases = cases()
    if len({c['id'] for c in frozen_cases}) != len(frozen_cases):
        raise ValueError('Duplicate case ID')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    files = {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
             for name in ('scaffold.py', 'cases.py', 'proof.py')}
    manifest = {'cases': frozen_cases, 'repeats': repeats, 'files': files,
                'limits': ['Synthetic compact contexts, not exact captured product payloads.',
                           'Proof-only schemas; production has no conversation-only branch yet.',
                           'No graph reads, page writes, publication or retained turn executed.',
                           'No-tool writer cannot prove a tool-enabled agent stops; dispatch policy needs product proof.',
                           'Question relevance, tone and execution claims require qualitative review.']}
    (output / 'frozen.json').write_text(canonical(manifest))
    rows = []
    for repeat in range(repeats):
        for case in frozen_cases:
            row = await one(case, repeat, decide, write)
            (output / f'{case["id"]}-{repeat}.json').write_text(canonical(row))
            rows.append(row)
            print(canonical({k: row[k] for k in ('case_id', 'repeat', 'passed', 'elapsed_ms')}), flush=True)
    report = {'manifest_sha256': fingerprint(manifest), 'runs': len(rows),
              'passed': sum(r['passed'] for r in rows), 'errors': sum('error' in r for r in rows),
              'limits': manifest['limits'], 'rows': rows}
    (output / 'report.json').write_text(canonical(report))
    return report


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--credential-file', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    from dotenv import dotenv_values
    from generationengine import GenerationClient, TextRequest
    from generationengine.types import DecisionRequest
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    from generationengine.providers.openai_text import OpenAITextProvider
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.text_dispatch import TextDispatchGate
    credentials = dotenv_values(args.credential_file)
    decision_key = credentials.get('TYPESAFE_JEV_API_KEY')
    writer_key = credentials.get('DUNGEONBUDDY_OPENAI') or credentials.get('OPENAI_API_KEY')
    if not decision_key or not writer_key:
        raise RuntimeError('Configured proof credentials unavailable')

    def gates(entry):
        entry['wire'] = []
        entry['lifecycle'] = []

        async def authorize(prepared):
            if prepared.provider == 'typesafe':
                assert prepared.url == 'https://ai-gateway.vercel.sh/typesafe/v1/systemone'
            else:
                assert prepared.provider == 'openai' and prepared.url == 'https://api.openai.com/v1/responses'
            body = json.loads(prepared.body)
            assert sha256(prepared.body).hexdigest() == prepared.body_sha256
            entry['wire'].append({'body': body, 'sha256': prepared.body_sha256})
            return True

        async def record(event):
            entry['lifecycle'].append(event.outcome)
            return True
        return authorize, record

    async def decide(request, entry):
        provider = TypeSafeDecisionProvider(api_key=decision_key, dispatch_gate=DecisionDispatchGate(*gates(entry)))
        client = GenerationClient(decision_providers={'typesafe': provider})
        try:
            return (await client.decide(DecisionRequest.model_validate(request))).model_dump(mode='json')
        finally:
            await client.aclose()

    async def write(value, entry):
        provider = OpenAITextProvider(api_key=writer_key, dispatch_gate=TextDispatchGate(*gates(entry)))
        client = GenerationClient(text_providers={'openai': provider})
        try:
            response = await client.generate_structured(TextRequest(provider='openai', model='gpt-6-luna',
                user_prompt=canonical(value), system_prompt=WRITER, max_output_tokens=1800,
                temperature=None, reasoning_effort='low', json_schema=REPLY_SCHEMA,
                schema_name='conversation_first_proof_v1', max_conformance_retries=0, max_transport_retries=0))
            return {'output': json.loads(response.text), 'observation': response.observation.model_dump(mode='json')}
        finally:
            await client.aclose()

    report = await run(args.output, decide, write)
    print(canonical({k: report[k] for k in ('manifest_sha256', 'runs', 'passed', 'errors')}))


if __name__ == '__main__':
    asyncio.run(main())
