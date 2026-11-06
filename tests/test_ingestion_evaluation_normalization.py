"""Generic offline worker/binding tests; no campaign-specific fixtures."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ingestion_evaluation.normalization import compare, prepared_prompts, select_responses, verify_runtime
from ingestion_evaluation.runner import digest, tooling_identity
from tests.test_ingestion_evaluation_assessment import assessment


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


@pytest.fixture
def normalization(assessment, tmp_path):
    original, _, put = assessment
    source = 'A lantern stands by the gate.'
    source_file = tmp_path / 'source.txt'
    source_file.write_text(source)
    source_pin = {'path': str(source_file), 'sha256': digest(source_file.read_bytes())}
    candidate = {'nodes': [{'description': 'Actual output'}], 'beats': [], 'diagnostics': {'preview': True}}
    def runtime(name, changed=False):
        root = tmp_path / name
        files = {
            'src/__init__.py': '', 'src/graph_memory/__init__.py': '',
            'src/graph_memory/extraction/__init__.py': '',
            'src/graph_memory/extraction/bounded_recap_execution.py':
                '''import json
def _canonical_json_bytes(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
class RecapExecutionLimits:
    def __init__(self, **kwargs): self.__dict__.update(kwargs)
class BoundedRecapPassClient:
    def __init__(self, limits, **kwargs): self.execution_binding=None; self.calls=[]
    def run_pass(self, name, *, instructions, user_content, **kwargs):
        self._request_type(system_prompt=instructions, user_prompt=user_content)
''',
            'src/graph_memory/extraction/source_sentence_evidence.py':
                'def materialize_node_evidence(*a, **kw): raise AssertionError("unexpected node packet")\ndef node_wire_schema(*a): raise AssertionError("unexpected node schema")\n',
            'src/graph_memory/extraction/category_candidate_graph_schema.py':
                'def category_pass_text_format_for_spec(spec): return {"format":{"schema":{"type":"object"}}}\n',
            'src/graph_memory/extraction/recap_quote_integrity.py':
                'def validate_and_defer_nonliteral_recap_items(candidate, **kwargs): return candidate, {"verified":True}\n',
            'src/graph_memory/extraction/category_candidate_graph_extractor.py': '''
import json
from types import SimpleNamespace
class CategoryGraphExtractionOptions:
    def __init__(self, **kw): self.__dict__.update(kw)
def parse_json_object(text): return json.loads(text)
def resolve_extraction_profile(options):
    return SimpleNamespace(qualified_id='recap_category_v2@2.0', node_passes=[], beat_pass=None,
                           edge_pass=SimpleNamespace(pass_id='edge_pass'), enable_encounter_job_pass=False, edge_review_pass=None)
class FixtureCategoryGraphPassClient:
    def __init__(self, data): self._pass_outputs=data
    def run_pass(self, name, **kw): return {'parsed':self._pass_outputs[name], 'cost_usd':0.0}
def extract_category_candidate_graph(options, client):
    profile=resolve_extraction_profile(options)
    parsed=client.run_pass('edge_pass',model_id='model:test',instructions='inert',user_content='retained input',pass_spec=profile.edge_pass)['parsed']
    candidate=parsed['candidate']
    CHANGE
    return SimpleNamespace(candidate_graph=candidate)
'''.replace('CHANGE', "candidate['beats']=[{'summary':'retained authored candidate'}]" if changed else 'pass'),
        }
        for rel, text in files.items():
            path = root / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
        manifest = {'root': str(root), 'files': [{'path': rel, 'sha256': digest((root / rel).read_bytes())} for rel in files]}
        return put(name + '.runtime.json', manifest), root
    control, control_root = runtime('control')
    treatment, treatment_root = runtime('treatment', True)
    def case(name):
        cp = put(name + '.candidate.json', candidate)
        context = {'schema': 'test-context', 'source_sha256': source_pin['sha256'], 'native_pin': {'revision': 'r'}, 'entities': [], 'mentions': [], 'ambiguous_surfaces': []}
        context['sha256'] = digest(json.dumps(context, sort_keys=True, separators=(',', ':')).encode())
        run = {'run_id': name, 'revision': 5, 'profile_id': 'recap_category_v2@2.0', 'status': 'reviewable',
               'source_artifact_id': 'artifact:generic', 'campaign_id': 'generic', 'session_id': 'session-1',
               'lineage': {'model_id': 'model:test', 'source_sha256': source_pin['sha256'], 'known_character_bindings': context}}
        binding = {k: (run['lineage'][k] if k in ('model_id', 'source_sha256') else run[k])
                   for k in ('run_id', 'model_id', 'profile_id', 'source_artifact_id', 'source_sha256')}
        binding['prepared_revision'] = 2
        text = json.dumps({'candidate': candidate})
        envelope = {'pass_name': 'edge_pass', 'pass_ordinal': 1, 'execution_binding': binding,
                    'ge_attempt': {'requested_model': 'model:test'},
                    'request': {'facts': {'model': 'model:test', 'provider': 'synthetic', 'provider_route': {}, 'reasoning_effort': 'low'},
                                'system_prompt_sha256': digest(b'inert'), 'user_prompt_sha256': digest(b'retained input')},
                    'response': {'text': text, 'sha256': digest(text.encode()), 'utf8_bytes': len(text.encode())}}
        sha = digest(canonical(envelope) + b'\n')
        raw = {'execution_evidence': {'binding': binding, 'records': [{'kind': 'raw_model_response', 'sha256': sha, 'envelope': envelope}]},
               'execution_observations': [{'pass_name': 'edge_pass', 'ordinal': 1, 'external_outcome': 'completed', 'worker_cleanup': 'reaped',
                   'model': 'model:test', 'requested_provider': 'synthetic', 'requested_route': {}, 'reasoning_effort': 'low',
                   'response_component': {'kind': 'raw_model_response', 'sha256': sha}}]}
        components = {'candidate_graph': cp, 'raw_model_response': put(name + '.raw.json', raw),
                      'source_span_index': put(name + '.index.json', {'source_artifact_id': 'artifact:generic'})}
        run['components'] = {k: {'sha256': v['sha256']} for k, v in components.items()}
        result = put(name + '.result.json', {'run': run, 'components': components})
        a = copy.deepcopy(original)
        a['subject'] = {'candidate': cp, 'result': {'artifact': result, 'pointer': '/run'}}
        review = put(name + '.review.json', {'run_id': name, 'revision': 5, 'candidate_sha256': cp['sha256'], 'checks': [{'criterion_id': 'F1'}]})
        phase = a['phases']['raw_extraction']; phase['phase_evidence'] = [review]
        phase['judgments'][0]['review'] = {'artifact': review, 'pointer': '/checks/0'}
        phase['judgments'][0]['evidence'] = [{'artifact': cp, 'pointer': '/nodes/0/description'}]
        return {'id': name, 'result': result, 'source': source_pin,
                'request': put(name + '.request.json', {'session': 1, 'campaign_id': 'generic'}),
                'assessment': put(name + '.assessment.json', a)}
    dependency = put('environment-marker.json', {'synthetic': True})
    environment = put('environment.json', {'scope': 'Synthetic test environment; transitive libraries not attested', 'files': [dependency], 'import_roots': [str(Path(pytest.__file__).resolve().parents[1])]})
    python = Path(sys.executable)
    spec = {'schema': 'dmb_retained_normalization_v1', 'tooling_sha256': tooling_identity(),
            'interpreter': {'path': str(python), 'sha256': digest(python.read_bytes())}, 'environment': environment,
            'runtimes': {'control': control, 'treatment': treatment}, 'cases': [case('one'), case('two')],
            'output': str(tmp_path / 'output'), 'worker_timeout_seconds': 10}
    path = tmp_path / 'normalization.json'
    def save(): path.write_text(json.dumps(spec)); return path
    def replace_pin(pin, value):
        target = Path(pin['path']); target.write_text(json.dumps(value)); pin['sha256'] = digest(target.read_bytes())
    return spec, save, replace_pin, control_root, treatment_root


def test_shared_cli_and_real_workers_reconstruct_generic_cases(normalization):
    spec, save, _, _, _ = normalization
    path = save()
    report = compare(path)
    assert [c['id'] for c in report['cases']] == ['one', 'two']
    assert all(c['old_reconstruction'] == 'exact_decoded_equality' for c in report['cases'])
    assert all(c['changed_root_fields'] == ['beats'] and c['requests_equal'] for c in report['cases'])
    assert 'cost_usd' not in json.dumps(report)
    assert compare(path) == report
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    result = subprocess.run([sys.executable, str(cli), 'normalization-compare', '--manifest', str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == report


def test_successful_report_tamper_is_not_reused(normalization):
    spec, save, _, _, _ = normalization
    path = save()
    compare(path)
    report = Path(spec['output']) / 'report.json'
    report.write_text('{}')
    with pytest.raises(ValueError, match='Pin mismatch'):
        compare(path)


def test_actual_deepseek_owner_prepares_prompts_without_execution(monkeypatch):
    from src.graph_memory.extraction import bounded_recap_execution as bounded
    from src.graph_memory.extraction.source_sentence_evidence import compile_source_sentence_packet

    def forbidden(*args, **kwargs):
        pytest.fail('Request preparation reached execution or persistence')

    monkeypatch.setattr(bounded, '_execute_in_owned_process', forbidden)
    monkeypatch.setattr(bounded.BoundedRecapPassClient, '_persist_capture', forbidden)
    source = 'A lantern stands by the gate.'
    packet = compile_source_sentence_packet(source, [{'source_span_ref_id': 'span:1', 'line_start': 1, 'text': source}])
    spec = bounded.RECAP_EXTRACTION_PROFILE.node_passes[0]
    system, user = prepared_prompts(bounded, {
        'provider': 'openrouter', 'model': bounded.DEEPSEEK_MODEL, 'reasoning_effort': 'low',
    }, spec.pass_id, 'Generic extraction instruction', 'Generic source input', spec, packet)
    assert system.startswith('Generic extraction instruction\n\n')
    assert 'complete JSON object' in system
    assert user == 'Generic source input'


def test_unlisted_imported_owner_is_rejected(normalization):
    spec, save, replace_pin, _, _ = normalization
    pin = spec['runtimes']['control']
    runtime = json.loads(Path(pin['path']).read_text())
    runtime['files'] = [row for row in runtime['files'] if not row['path'].endswith('category_candidate_graph_extractor.py')]
    replace_pin(pin, runtime)
    with pytest.raises(ValueError, match='worker failed'):
        compare(save())
    error = (Path(spec['output']) / 'one/control.stderr').read_text()
    assert 'Imported runtime member is not pinned' in error


def test_saved_candidate_reconstruction_includes_ordinary_quote_owner(normalization):
    spec, save, replace_pin, control, treatment = normalization
    for arm, root in [('control', control), ('treatment', treatment)]:
        owner = root / 'src/graph_memory/extraction/category_candidate_graph_extractor.py'
        owner.write_text(owner.read_text().replace('    return SimpleNamespace(candidate_graph=candidate)',
                                                  "    candidate['diagnostics']['preview']=False\n    return SimpleNamespace(candidate_graph=candidate)"))
        quote_owner = root / 'src/graph_memory/extraction/recap_quote_integrity.py'
        quote_owner.write_text('def validate_and_defer_nonliteral_recap_items(candidate, **kwargs):\n    candidate["diagnostics"]["preview"]=True\n    return candidate, {"verified":True}\n')
        pin = spec['runtimes'][arm]
        runtime = json.loads(Path(pin['path']).read_text())
        for row in runtime['files']:
            row['sha256'] = digest((root / row['path']).read_bytes())
        replace_pin(pin, runtime)
    report = compare(save())
    assert all(c['old_reconstruction'] == 'exact_decoded_equality' for c in report['cases'])
    product = json.loads((Path(spec['output']) / 'one/control.json').read_text())
    assert product['quote_integrity'] == {'verified': True}


@pytest.mark.parametrize('packet_matches', [True, False])
def test_real_worker_materializes_node_packets_before_fixture_use(normalization, packet_matches):
    spec, save, replace_pin, control, treatment = normalization
    for arm, root in [('control', control), ('treatment', treatment)]:
        owner = root / 'src/graph_memory/extraction/category_candidate_graph_extractor.py'
        text = owner.read_text().replace("node_passes=[]", "node_passes=[SimpleNamespace(pass_id='node_pass')]")
        text = text.replace("    parsed=client.run_pass('edge_pass'", "    node=client.run_pass('node_pass',model_id='model:test',instructions='inert',user_content='retained input',pass_spec=profile.node_passes[0],source_evidence_packet=SimpleNamespace(packet_id='packet'))['parsed']\n    assert node['materialized'] is True\n    parsed=client.run_pass('edge_pass'")
        owner.write_text(text)
        evidence = root / 'src/graph_memory/extraction/source_sentence_evidence.py'
        evidence.write_text('def node_wire_schema(schema, packet): return schema\ndef materialize_node_evidence(packet, parsed, expected_packet_id):\n    assert expected_packet_id == packet.packet_id\n    return {**parsed, "materialized":True}\n')
        runtime = json.loads(Path(spec['runtimes'][arm]['path']).read_text())
        for row in runtime['files']:
            row['sha256'] = digest((root / row['path']).read_bytes())
        replace_pin(spec['runtimes'][arm], runtime)
    for case in spec['cases']:
        result = json.loads(Path(case['result']['path']).read_text())
        pin = result['components']['raw_model_response']
        raw = json.loads(Path(pin['path']).read_text())
        edge = raw['execution_evidence']['records'][0]
        edge['envelope']['pass_ordinal'] = 2
        edge['sha256'] = digest(canonical(edge['envelope']) + b'\n')
        observation = raw['execution_observations'][0]
        observation['ordinal'] = 2
        observation['response_component']['sha256'] = edge['sha256']
        node = copy.deepcopy(edge)
        node['envelope']['pass_name'] = 'node_pass'
        node['envelope']['pass_ordinal'] = 1
        node['envelope']['context_sha256'] = {'node_source_packet': 'packet' if packet_matches else 'foreign'}
        node['sha256'] = digest(canonical(node['envelope']) + b'\n')
        raw['execution_evidence']['records'].append(node)
        node_observation = copy.deepcopy(observation)
        node_observation.update(pass_name='node_pass', ordinal=1)
        node_observation['response_component']['sha256'] = node['sha256']
        raw['execution_observations'].append(node_observation)
        replace_pin(pin, raw)
        result['run']['components']['raw_model_response']['sha256'] = pin['sha256']
        replace_pin(case['result'], result)
        assessment_value = json.loads(Path(case['assessment']['path']).read_text())
        assessment_value['subject']['result']['artifact'] = case['result']
        replace_pin(case['assessment'], assessment_value)
    if packet_matches:
        assert all(c['requests_equal'] for c in compare(save())['cases'])
    else:
        with pytest.raises(ValueError, match='worker failed'):
            compare(save())


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'binding', 'text_hash', 'record_hash', 'host_sibling', 'wrong_model', 'outcome'])
def test_actual_response_links_fail_closed(normalization, fault):
    spec, _, _, _, _ = normalization
    result = json.loads(Path(spec['cases'][0]['result']['path']).read_text())
    raw = json.loads(Path(result['components']['raw_model_response']['path']).read_text())
    row = raw['execution_evidence']['records'][0]
    obs = raw['execution_observations'][0]
    if fault == 'missing': obs['response_component']['sha256'] = 'f' * 64
    elif fault == 'duplicate': raw['execution_observations'].append(copy.deepcopy(obs))
    elif fault == 'binding': row['envelope']['execution_binding']['run_id'] = 'foreign'
    elif fault == 'text_hash': row['envelope']['response']['sha256'] = '0' * 64
    elif fault == 'record_hash': row['sha256'] = '0' * 64
    elif fault == 'host_sibling': row['envelope'].pop('ge_attempt')
    elif fault == 'wrong_model': obs['model'] = 'foreign'
    else: obs['external_outcome'] = 'unknown'
    if fault not in ('missing', 'duplicate', 'record_hash'):
        row['sha256'] = digest(canonical(row['envelope']) + b'\n')
        obs['response_component']['sha256'] = row['sha256']
    with pytest.raises((ValueError, KeyError)):
        select_responses(raw, result['run'], canonical)


@pytest.mark.parametrize('fault', ['runtime_escape', 'runtime_tamper', 'overlap', 'same_run', 'assessment', 'tooling'])
def test_manifest_and_input_boundaries(normalization, fault):
    spec, save, replace_pin, root, _ = normalization
    if fault == 'runtime_escape':
        m = json.loads(Path(spec['runtimes']['control']['path']).read_text()); m['files'][0]['path'] = '../escape'; replace_pin(spec['runtimes']['control'], m)
    elif fault == 'runtime_tamper': (root / 'src/__init__.py').write_text('changed')
    elif fault == 'overlap': spec['output'] = str(root / 'out')
    elif fault == 'same_run': spec['cases'][1] = {**spec['cases'][0], 'id': 'other'}
    elif fault == 'assessment': spec['cases'][1]['assessment'] = spec['cases'][0]['assessment']
    else: spec['tooling_sha256'] = '0' * 64
    with pytest.raises(ValueError): compare(save())
    assert not (Path(spec['output']) / 'report.json').exists()


@pytest.mark.parametrize('fault', ['old_candidate', 'context', 'request', 'missing_pass', 'provider', 'database', 'timeout'])
def test_workers_retain_failures_without_success_or_fallback(normalization, fault):
    spec, save, replace_pin, root, _ = normalization
    source = root / 'src/graph_memory/extraction/category_candidate_graph_extractor.py'
    if fault in ('provider', 'database', 'timeout', 'old_candidate'):
        prefix = {'provider': "import socket; socket.create_connection(('127.0.0.1', 9))\n",
                  'database': "import psycopg; psycopg.connect('dbname=forbidden')\n",
                  'timeout': 'import time; time.sleep(5)\n',
                  'old_candidate': ''}[fault]
        text = prefix + source.read_text()
        if fault == 'old_candidate': text = text.replace('    pass\n', "    candidate['diagnostics']['changed']=True\n")
        source.write_text(text)
        m = json.loads(Path(spec['runtimes']['control']['path']).read_text())
        for row in m['files']:
            if row['path'].endswith('category_candidate_graph_extractor.py'): row['sha256'] = digest(source.read_bytes())
        replace_pin(spec['runtimes']['control'], m)
        if fault == 'timeout': spec['worker_timeout_seconds'] = 1
    else:
        case = spec['cases'][0]; result = json.loads(Path(case['result']['path']).read_text())
        if fault == 'context': result['run']['lineage']['known_character_bindings']['sha256'] = '0' * 64
        else:
            raw_pin = result['components']['raw_model_response']; raw = json.loads(Path(raw_pin['path']).read_text())
            if fault == 'missing_pass': raw['execution_observations'] = []
            else:
                row = raw['execution_evidence']['records'][0]; row['envelope']['request']['user_prompt_sha256'] = '0' * 64
                row['sha256'] = digest(canonical(row['envelope']) + b'\n'); raw['execution_observations'][0]['response_component']['sha256'] = row['sha256']
            replace_pin(raw_pin, raw); result['run']['components']['raw_model_response']['sha256'] = raw_pin['sha256']
        replace_pin(case['result'], result)
        a = json.loads(Path(case['assessment']['path']).read_text()); a['subject']['result']['artifact'] = case['result']; replace_pin(case['assessment'], a)
    with pytest.raises((ValueError, subprocess.TimeoutExpired)): compare(save())
    output = Path(spec['output'])
    assert (output / 'failure.json').exists()
    assert not (output / 'report.json').exists()
    assert json.loads((output / 'failure.json').read_text())['artifacts']
    with pytest.raises(ValueError, match='incomplete or failed'): compare(save())
