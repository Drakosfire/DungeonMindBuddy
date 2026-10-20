"""Rules source admission and actual authenticated HTTP boundaries; no provider/DB."""
from copy import deepcopy
from hashlib import sha256
import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from apps.live_control_server.services import rules_lookup as service
from apps.live_control_server.routes.rules_lookup import router

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    service.load_bundle.cache_clear()
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'local')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', 'rules-test-operator-token-0123456789abcdef')
    yield
    service.load_bundle.cache_clear()

def request(path, authenticated=True):
    async def run():
        app = FastAPI(); app.include_router(router)
        headers = {'Authorization': 'Bearer rules-test-operator-token-0123456789abcdef'} if authenticated else {}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 123)), base_url='http://test') as client:
            return await client.get(path, headers=headers)
    return asyncio.run(run())

def install(tmp_path, monkeypatch, mutate=lambda bundle: None):
    raw = json.loads(service.ADMITTED_BUNDLES[0][1].read_bytes())
    mutate(raw)
    path = tmp_path / 'rules.json'; path.write_text(json.dumps(raw, ensure_ascii=False))
    digest = sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(service, 'ADMITTED_BUNDLES', ((digest, path),))
    return digest, path

def test_real_public_bundle_exact_provenance_and_no_graph_claim():
    packet = service.query_rules(service.SEED_DIGEST, 'Can I willingly end my move in a prone ally space?')
    assert packet['status'] == 'evidence' and packet['coverage_status'] == 'limited'
    assert packet['ruleset_id'] == 'dnd_2024_srd_5_2_1'
    hit, = packet['hits']
    assert hit['printed_page'] == 14 and hit['pdf_page_index'] == 13
    assert 'can’t willingly end a move' in hit['excerpt'] and 'unless you are Tiny' in hit['excerpt']
    passage = service.inspect_passage(service.SEED_DIGEST, hit['citation_id'])
    assert passage['text'] == hit['excerpt'] and sha256(passage['text'].encode()).hexdigest() == hit['text_sha256']
    assert 'Creative Commons Attribution 4.0' in passage['attribution']
    assert 'graph' not in packet and 'assertion_id' not in hit

def test_missing_travel_is_not_a_rule_denial():
    packet = service.query_rules(service.SEED_DIGEST, 'What is slow travel speed?')
    assert packet['status'] == 'no_evidence' and packet['hits'] == []
    assert 'only' in packet['coverage']

def test_normalization_stable_identity_and_no_duplicate_hit():
    a = service.query_rules(service.SEED_DIGEST, '  ＰＲＯＮＥ   ally ')
    b = service.query_rules(service.SEED_DIGEST, 'prone ally')
    assert a == b and len(a['hits']) == 1
    assert service.inspect_passage(service.SEED_DIGEST, 'f' * 64) is None

@pytest.mark.parametrize('mutation', [
    lambda d: d.update(extra='not allowed'),
    lambda d: d['units'].append(deepcopy(d['units'][0])),
    lambda d: d['units'][0].update(text='altered text'),
    lambda d: d['units'][0].update(gate_passed=False),
    lambda d: d['units'][0].update(gate_passed=1),
    lambda d: d['units'][0].update(text='x' * 8193),
    lambda d: d['units'][0].update(source_uri='file:///private/source'),
    lambda d: d['units'][0].update(pdf_page_index=-1),
])
def test_artifact_import_rejects_invalid_units(tmp_path, monkeypatch, mutation):
    digest, _ = install(tmp_path, monkeypatch, mutation)
    with pytest.raises(service.RulesCorpusUnavailable): service.admitted_bundle(digest)

def test_pin_failure_missing_file_and_unknown_corpus_do_not_substitute_latest(tmp_path, monkeypatch):
    digest, path = install(tmp_path, monkeypatch)
    path.write_text('{}')
    with pytest.raises(service.RulesCorpusUnavailable): service.admitted_bundle(digest)
    path.unlink()
    with pytest.raises(service.RulesCorpusUnavailable): service.admitted_bundle(digest)
    with pytest.raises(service.RulesCorpusUnavailable): service.admitted_bundle('f' * 64)
    assert service.catalog()['sources'] == [{'corpus': digest, 'available': False}]

def test_actual_read_bound(tmp_path, monkeypatch):
    digest, path = install(tmp_path, monkeypatch)
    monkeypatch.setattr(service, 'MAX_BUNDLE_BYTES', 20)
    with pytest.raises(service.RulesCorpusUnavailable): service.admitted_bundle(digest)

def test_excerpt_bound_and_deterministic_ties(tmp_path, monkeypatch):
    def expand(d):
        original = deepcopy(d['units'][0]); d['units'] = []
        for n in reversed(range(9)):
            unit = deepcopy(original); unit.update(unit_id=f'{n:064x}', text='Prone ' * 1000)
            unit['text_sha256'] = sha256(unit['text'].encode()).hexdigest(); d['units'].append(unit)
    digest, _ = install(tmp_path, monkeypatch, expand)
    packet = service.query_rules(digest, 'prone', 8)
    assert len(packet['hits']) == 8 and packet['additional_matches']
    assert [h['unit_id'] for h in packet['hits']] == sorted(h['unit_id'] for h in packet['hits'])
    assert all(len(h['excerpt']) <= 1400 and not h['excerpt_complete'] for h in packet['hits'])
    assert sum(len(h['excerpt'].encode()) for h in packet['hits']) <= service.MAX_EXCERPT_BYTES

def test_same_unit_in_another_edition_has_distinct_citation(tmp_path, monkeypatch):
    old = service.query_rules(service.SEED_DIGEST, 'prone')['hits'][0]
    digest, _ = install(tmp_path, monkeypatch, lambda d: d.update(ruleset_id='test_other_edition'))
    new = service.query_rules(digest, 'prone')['hits'][0]
    assert old['citation_id'] != new['citation_id'] and old['corpus'] != new['corpus']
    assert service.inspect_passage(digest, old['citation_id']) is None

@pytest.mark.parametrize('path', ['/catalog', '/query?corpus=' + service.SEED_DIGEST + '&question=prone', '/passages/' + 'a' * 64 + '?corpus=' + service.SEED_DIGEST])
def test_all_routes_require_actual_operator_auth(path):
    assert request('/api/live/rules' + path, authenticated=False).status_code == 401

def test_actual_authenticated_lookup_inspect_and_no_store():
    assert request('/api/live/rules/catalog').json()['sources'][0]['unit_count'] == 1
    result = request('/api/live/rules/query?corpus=' + service.SEED_DIGEST + '&question=prone')
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    hit = result.json()['hits'][0]
    exact = request('/api/live/rules/passages/' + hit['citation_id'] + '?corpus=' + service.SEED_DIGEST)
    assert exact.status_code == 200 and exact.json()['text_sha256'] == hit['text_sha256']
    assert request('/api/live/rules/passages/' + 'f' * 64 + '?corpus=' + service.SEED_DIGEST).status_code == 404
    unavailable = request('/api/live/rules/query?corpus=' + 'f' * 64 + '&question=prone')
    assert unavailable.status_code == 503 and unavailable.headers['cache-control'] == 'no-store'
    assert 'path' not in unavailable.text

@pytest.mark.parametrize('query', ['corpus=bad&question=prone', 'corpus=' + service.SEED_DIGEST + '&question=', 'corpus=' + service.SEED_DIGEST + '&question=%20', 'corpus=' + service.SEED_DIGEST + '&question=prone&limit=9', 'corpus=' + service.SEED_DIGEST + '&question=' + 'x' * 801])
def test_actual_query_bounds(query):
    assert request('/api/live/rules/query?' + query).status_code == 422

def test_production_app_mounts_the_authenticated_rules_router():
    from apps.live_control_server.main import create_app
    app = create_app()
    routes = {route.path for route in app.routes}
    assert {'/api/live/rules/catalog', '/api/live/rules/query', '/api/live/rules/passages/{citation_id}'} <= routes
