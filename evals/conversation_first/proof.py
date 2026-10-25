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
from .scaffold import PREPARED_ITEMS, REPLY_SCHEMA, WRITER, decision_request, frame, preparation_request


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return sha256(canonical(value).encode()).hexdigest()


def choose(result, name="next_step", options=None):
    answer = result["answers"][name]
    scores = answer["probabilities"]
    options = set(options) if options is not None else {"converse", "research", "prepare"}
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


def validate_reply(reply, value):
    jsonschema.validate(reply['output'], REPLY_SCHEMA)
    allowed = {item['id'] for item in value['workflow_catalog']}
    if reply['output']['workflow_suggestion'] is not None and reply['output']['workflow_suggestion'] not in allowed:
        raise ValueError('Writer invented an unavailable workflow')


def retain_attempt(entry, event):
    entry.setdefault('attempts', []).append(event.model_dump(mode='json'))


async def one(case, repeat, decide, write):
    row = {'case_id': case['id'], 'repeat': repeat, 'calls': [], 'passed': False}
    started = time.perf_counter()
    try:
        request = decision_request(case)
        decision = {'role': 'controller', 'request': request, 'response': None}
        row['calls'].append(decision)
        decision['response'] = await decide(request, decision)
        selected = choose(decision['response'])
        row.update(selected=selected, expected_step=case['expected_step'], cohort=case['cohort'])
        row['passed'] = selected == case['expected_step']
        # Never substitute the gold route to force a conversational output.
        if selected == 'prepare':
            item_call = {'role': 'prepared_item_controller', 'request': preparation_request(case), 'response': None}
            row['calls'].append(item_call)
            item_call['response'] = await decide(item_call['request'], item_call)
            item = choose(item_call['response'], 'prepared_item', PREPARED_ITEMS)
            row.update(prepared_item=item, expected_item=case['expected_item'])
            row['passed'] &= item == case['expected_item']
        if selected == 'converse':
            reply = {'role': 'writer', 'input': frame(case), 'response': None}
            row['calls'].append(reply)
            reply['response'] = await write(reply['input'], reply)
            validate_reply(reply['response'], reply['input'])
            count = case['expected_questions']
            row['question_count_passed'] = count is None or len(reply['response']['output']['questions']) == count
            row['passed'] &= row['question_count_passed']
            # Ablate only workflow discovery on the two chain-shaped cases. Same writer instructions.
            if case['id'] in {'ask_first_chain', 'correct_wrong_surface'}:
                ablation = {'role': 'writer_without_catalog', 'input': frame(case, include_workflow=False), 'response': None}
                row['calls'].append(ablation)
                ablation['response'] = await write(ablation['input'], ablation)
                validate_reply(ablation['response'], ablation['input'])
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
                           'Prepare-item classification confers no executable capability; unavailable Build actions stay unavailable.',
                           'Previously tuned and fresh taxonomy cohorts must be reported separately.',
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
        from uuid import uuid4
        entry['call_id'] = str(uuid4())
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

    def journal(entry, event):
        with (args.output / 'attempts.jsonl').open('a') as sink:
            sink.write(canonical({'call_id': entry['call_id'], 'event': event}) + '\n')

    async def decide(request, entry):
        provider = TypeSafeDecisionProvider(api_key=decision_key, dispatch_gate=DecisionDispatchGate(*gates(entry)))
        client = GenerationClient(decision_providers={'typesafe': provider})
        try:
            return (await client.decide(DecisionRequest.model_validate(request))).model_dump(mode='json')
        except Exception as exc:
            observation = getattr(exc, 'observation', None)
            if observation is not None:
                entry['failure_observation'] = observation.model_dump(mode='json')
                journal(entry, {'failure_observation': entry['failure_observation']})
            raise
        finally:
            await client.aclose()

    async def write(value, entry):
        provider = OpenAITextProvider(api_key=writer_key, dispatch_gate=TextDispatchGate(*gates(entry)))
        client = GenerationClient(text_providers={'openai': provider})
        async def completed(event):
            retain_attempt(entry, event)
            journal(entry, entry['attempts'][-1])
        try:
            response = await client.generate_structured(TextRequest(provider='openai', model='gpt-6-luna',
                user_prompt=canonical(value), system_prompt=WRITER, max_output_tokens=1800,
                temperature=None, reasoning_effort='low', json_schema=REPLY_SCHEMA,
                schema_name='conversation_first_proof_v1', max_conformance_retries=0, max_transport_retries=0),
                on_attempt_completed=completed)
            return {'output': json.loads(response.text), 'observation': response.observation.model_dump(mode='json')}
        except Exception as exc:
            observation = getattr(exc, 'observation', None)
            if observation is not None:
                entry['failure_observation'] = observation.model_dump(mode='json')
                journal(entry, {'failure_observation': entry['failure_observation']})
            raise
        finally:
            await client.aclose()

    report = await run(args.output, decide, write)
    print(canonical({k: report[k] for k in ('manifest_sha256', 'runs', 'passed', 'errors')}))


if __name__ == '__main__':
    asyncio.run(main())
