"""Run a non-serving live Jev acquisition then one tool-free Luna answer.

Explicit private case/config paths required. No writes to World or conversation.
Gold is opened only after retrieval/writing, never included in provider inputs.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from evals.graph_memory_layer.jev_evidence_loop import run_loop
from evals.graph_memory_layer.jev_live_evidence import LiveSourceReader, discover_live, write_once
from evals.graph_memory_layer.run_jev_evidence_loop import score_gold


def readonly_environment(path):
    from dotenv import dotenv_values
    for key, value in dotenv_values(path).items():
        if value is None:
            continue
        if value.startswith(("postgresql://", "postgres://")):
            uri = urlsplit(value)
            if uri.hostname not in {"127.0.0.1", "localhost"}:
                raise ValueError("Experiment database must be loopback")
            query = [(k, v) for k, v in parse_qsl(uri.query) if k != "options"]
            query.append(("options", "-c default_transaction_read_only=on"))
            value = urlunsplit(uri._replace(query=urlencode(query, quote_via=quote)))
        os.environ[key] = value


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    start = time.perf_counter()
    readonly_environment(args.credential_file)
    os.environ['DMB_ARTIFACT_DATA_ROOT'] = str(args.root)
    os.environ['DMB_MANAGED_WORLD_DATA_ROOT'] = str(args.root)
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import direct_services_from_bundle
    from apps.live_control_server.routes.agent import _build_work_resolver
    from types import SimpleNamespace
    spec = json.loads(args.case.read_text())
    database = PostgresDatabase(os.environ['DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL'])
    with database.connect() as connection:
        if connection.execute('SHOW transaction_read_only').fetchone()['transaction_read_only'] != 'on':
            raise ValueError('Database is not read-only')
    bundle = PostgresRepositoryBundle(database)
    head = bundle.world_graph.get_head(spec['world_id'])
    if head is None or head.head_revision_id != spec['graph_revision']:
        raise ValueError('Live Graph head changed from explicit case pin')
    locator = SimpleNamespace(kind='build', object_id=spec['build_document_id'],
        expected_revision=spec['build_revision'], expected_content_sha256=spec['source_sha256'])
    body = SimpleNamespace(primary_work=locator, surface=SimpleNamespace(surface_id='build'))
    work = _build_work_resolver(body, {'kind': 'world', 'id': spec['managed_world_id']})
    basis = work.build_source
    services = direct_services_from_bundle(bundle, spec['world_id'])
    discovery = discover_live(services, {'document_id': basis.document_id, 'revision': basis.revision,
        'content_sha256': basis.content_sha256}, world_id=spec['world_id'], graph_revision=spec['graph_revision'])
    reader = LiveSourceReader(services, args.root, spec, basis.markdown, discovery)
    catalog = reader.catalog()
    for name, value in [('case.json', spec), ('discovery.json', discovery), ('catalog.json', catalog)]:
        (args.output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2))
    preparation_seconds = time.perf_counter() - start
    if args.prepare_only:
        for aid in catalog['initial_actions']:
            await reader.retrieve(catalog['actions'][aid])
        (args.output/'live-read-trace.json').write_text(json.dumps(reader.trace, ensure_ascii=False, indent=2))
        print(json.dumps({'status': 'prepared_no_inference', 'actions': len(catalog['actions']),
                          'source_observations': discovery['eligible_count'], 'seconds': preparation_seconds}))
        return
    from generationengine import GenerationClient
    from generationengine.types import DecisionRequest
    from openai import AsyncOpenAI
    from apps.live_control_server.services.agent_graph_policy import resolve_agent_graph_openai_inference
    from apps.live_control_server.services.agent_turn_trace import estimate_model_call_cost
    if os.getenv('DUNGEONBUDDY_OPENAI'):
        os.environ['OPENAI_API_KEY'] = os.environ['DUNGEONBUDDY_OPENAI']
    provider, model, url = resolve_agent_graph_openai_inference(require_api_key=True)
    if (provider, model, url) != ('openai-api', 'gpt-6-luna', 'https://api.openai.com/v1'):
        raise ValueError('Writer route differs from approved existing Buddy Luna route')
    jev = GenerationClient.from_env()
    async def decide(request):
        return (await jev.decide(DecisionRequest.model_validate(request))).model_dump(mode='json')
    try:
        result = await run_loop(catalog, decide, output=args.output/'retrieval', retrieve=reader.retrieve)
    finally:
        await jev.aclose()
        (args.output/'live-read-trace.json').write_text(json.dumps(reader.trace, ensure_ascii=False, indent=2))
    writer = None
    if result['status'] == 'provisionally_supported':
        async with AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=url,
                               max_retries=0, timeout=120) as client:
            async def invoke(request):
                response = await client.responses.create(**request)
                return {'answer': response.output_text, 'data': response.model_dump(mode='json')}
            writer = await write_once(result, spec['question'], invoke, args.output)
    # Evaluation files never enter either provider request.
    gold_bytes = args.gold.read_bytes()
    score = score_gold(result, json.loads(gold_bytes))
    score['answer_accuracy'] = 'requires_independent_review' if writer else 'not_measured_no_writer'
    score['gold_sha256'] = hashlib.sha256(gold_bytes).hexdigest()
    usage = writer.get('response', {}).get('data', {}).get('usage') if writer else None
    cost_usage = None
    if usage:
        cost_usage = {'input_tokens': usage['input_tokens'], 'output_tokens': usage['output_tokens'],
            'cached_input_tokens': (usage.get('input_tokens_details') or {}).get('cached_tokens'),
            'reasoning_tokens': (usage.get('output_tokens_details') or {}).get('reasoning_tokens')}
    report = {'status': result['status'], 'preparation_seconds': preparation_seconds,
        'retrieval_seconds': result['elapsed_seconds'], 'writer_seconds': writer['elapsed_seconds'] if writer else None,
        'total_seconds': time.perf_counter()-start, 'jev_calls': len(result['observations']),
        'jev_input_tokens': result['input_tokens_reported'], 'jev_output_tokens': result['output_tokens_reported'],
        'writer_calls': 1 if writer else 0, 'writer_status': writer['status'] if writer else 'not_called',
        'writer_usage': usage, 'writer_cost_estimate': estimate_model_call_cost(model=model, usage=cost_usage) if cost_usage else None,
        'unique_anchor_reads': len(reader.anchor_cache), 'source_coverage': score,
        'database_read_only': True, 'ordinary_runtime_adoption': False,
        'limits': ['Exact source-scoped pilot with human requirements and seeds.',
                   'Old ordinary-loop comparison has different history, prompt and cache state.',
                   'Gold quote coverage is not answer accuracy; independent semantic review required.']}
    (args.output/'comparison.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    asyncio.run(main())
