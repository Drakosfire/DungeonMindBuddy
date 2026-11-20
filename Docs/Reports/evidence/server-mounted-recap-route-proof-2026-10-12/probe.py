"""Mounted retained-native source-route witness; metadata-only output, no writes."""
import asyncio
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import subprocess
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from dotenv import dotenv_values

CODE = Path('/tmp/buddy-agent-source-targets')
DATA = Path('/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy')
PROFILE = Path('/home/drakosfire/.local/state/dungeonmind/recovery/native-live-20261011/dogfood-runtime.env')
REVISION = 'rev:62820bcd7eca116af9d889e128fabf4e'
EXPECTED = {
    'corpus:eldyrwild:session-22-recap': '06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083',
    'corpus:eldyrwild:session-23-recap': '77ba5030b5c89e8888e8a3d900fe3fc07b94313af81a7ad5f888eb663d4c7782',
}
TOKEN = 'synthetic-mounted-route-proof-local-operator-20261012'
logging.disable(logging.CRITICAL)
profile = dotenv_values(PROFILE, interpolate=False)
parts = urlsplit(profile['DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL'])
assert (parts.hostname, parts.port, parts.path.lstrip('/')) == (
    '127.0.0.1', 54330, 'dungeonmind_cutover_live_restore_20261011'
)
query = [(k, v) for k, v in parse_qsl(parts.query) if k != 'options']
query.append(('options', '-c default_transaction_read_only=on'))
dsn = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, quote_via=quote), parts.fragment))
os.environ['DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL'] = dsn
os.environ['PGOPTIONS'] = '-c default_transaction_read_only=on'
os.environ['DMB_ARTIFACT_DATA_ROOT'] = str(DATA)
os.environ['DMB_MANAGED_WORLD_DATA_ROOT'] = str(DATA)
os.environ['DMB_AGENT_GRAPH_AUTH_MODE'] = 'local_operator'
os.environ['DMB_AGENT_GRAPH_AUTH_ENVIRONMENT'] = 'development'
os.environ['DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN'] = TOKEN

import httpx
import psycopg
from fastapi import FastAPI
from apps.live_control_server.routes.world_graph_retrieval import router
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import direct_services_from_config

app = FastAPI()
app.include_router(router)
PREFIX = '/api/live/world-graph/retrieval/recap-context'
common = {
    'worldId': 'eldyrwild', 'campaignId': '', 'scopeMode': 'world',
    'admissibility': 'gm', 'revisionPin': REVISION,
    'focus': {'kind': 'none', 'sessionId': None, 'campaignId': None},
}
with psycopg.connect(dsn) as conn:
    default_ro = conn.execute('SHOW default_transaction_read_only').fetchone()[0]
    active_ro = conn.execute('SHOW transaction_read_only').fetchone()[0]
assert default_ro == active_ro == 'on'
core_url = json.loads(importlib.metadata.distribution('dungeonmind').read_text('direct_url.json'))
core_sha = core_url['vcs_info']['commit_id']
assert core_sha == '13143455b304d748c249bd7bd628134c421bf6d9'
services = direct_services_from_config('eldyrwild')
before = services.bundle.world_graph.get_head('eldyrwild').head_revision_id
assert before == REVISION


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


async def prove():
    receipt = {'code_head': subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip(),
               'core_head': core_sha, 'default_transaction_read_only': default_ro,
               'transaction_read_only': active_ro, 'native_head_before': before,
               'opened': []}
    transport = httpx.ASGITransport(app=app, client=('127.0.0.1', 42123))
    async with httpx.AsyncClient(transport=transport, base_url='http://isolated.local') as client:
        index_request = {'schema': 'dmb_recap_context_index_request_v1', **common}
        read_request = {'schema': 'dmb_recap_context_read_request_v1', **common,
                        'contextAnchorId': 'dm-context-anchor:v1:unauthenticated'}
        for name, request in [('index', index_request), ('read', read_request)]:
            denied = await client.post(PREFIX + '/' + name, json=request)
            assert denied.status_code == 401
            assert denied.json()['detail']['code'] == 'graph_auth_required'
        invalid_auth = await client.post(PREFIX + '/index', json=index_request,
                                        headers={'Authorization': 'Bearer invalid-synthetic-token'})
        assert invalid_auth.status_code == 401
        receipt['unauthenticated_index_status'] = receipt['unauthenticated_read_status'] = 401
        receipt['invalid_token_status'] = 401
        headers = {'Authorization': 'Bearer ' + TOKEN}
        response = await client.post(PREFIX + '/index', json=index_request, headers=headers)
        assert response.status_code == 200
        index = response.json()
        assert index['status'] == 'complete' and index['eligibleCount'] == len(index['entries'])
        assert index['snapshot']['revisionId'] == REVISION
        assert index['snapshot']['scopeMode'] == 'world'
        assert index['snapshot']['campaignId'] == ''
        receipt['authorized_index_status'] = 200
        receipt['descriptor_count'] = index['eligibleCount']
        selected = {row['sourceArtifactId']: row for row in index['entries']
                    if row['sourceArtifactId'] in EXPECTED}
        assert set(selected) == set(EXPECTED)
        for artifact_id in sorted(selected):
            descriptor = selected[artifact_id]
            assert descriptor['contentSha256'] == EXPECTED[artifact_id]
            request = {'schema': 'dmb_recap_context_read_request_v1', **common,
                       'contextAnchorId': descriptor['contextAnchorId'], 'maxChars': 12000}
            response = await client.post(PREFIX + '/read', json=request, headers=headers)
            assert response.status_code == 200
            full = response.json()
            assert full['outcome'] == 'enough' and not full['truncated']
            assert full['context'] == descriptor
            assert (full['headingLine'], full['lineStart'], full['lineEnd']) == (12, 13, 38)
            assert digest(full['content']) == full['sectionSha256']
            pages = []
            joined = ''
            continuation = None
            while True:
                page_request = {**request, 'maxChars': 1000, 'continuation': continuation}
                response = await client.post(PREFIX + '/read', json=page_request, headers=headers)
                assert response.status_code == 200
                page = response.json()
                assert page['context'] == descriptor
                assert page['sectionSha256'] == full['sectionSha256']
                assert (page['headingLine'], page['lineStart'], page['lineEnd']) == (12, 13, 38)
                assert page['offsetChars'] == len(joined) and len(page['content']) <= 1000
                joined += page['content']
                pages.append({'offset_chars': page['offsetChars'], 'returned_chars': len(page['content']),
                              'page_sha256': digest(page['content']), 'truncated': page['truncated']})
                if not page['truncated']:
                    assert page['nextContinuation'] is None
                    break
                assert page['nextContinuation'] and len(pages) < 12
                continuation = page['nextContinuation']
            assert len(pages) > 1 and joined == full['content'] and digest(joined) == full['sectionSha256']
            bad = await client.post(PREFIX + '/read', json={**request, 'continuation': 'invalid-cursor'}, headers=headers)
            assert bad.status_code == 409 and 'content' not in bad.json()
            receipt['opened'].append({'source_artifact_id': artifact_id,
                'context_anchor_id': descriptor['contextAnchorId'],
                'source_revision_id': descriptor['sourceRevisionId'],
                'source_campaign_id': descriptor['campaignId'],
                'content_sha256': descriptor['contentSha256'], 'section_sha256': full['sectionSha256'],
                'heading_line': 12, 'line_start': 13, 'line_end': 38, 'pages': pages,
                'authorized_read_status': 200, 'invalid_continuation_status': 409})
    after = services.bundle.world_graph.get_head('eldyrwild').head_revision_id
    assert before == after
    receipt['native_head_after'] = after
    receipt['head_unchanged'] = True
    output = Path('/tmp/server-mounted-recap-proof-20261012/receipt.json')
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))


asyncio.run(prove())
