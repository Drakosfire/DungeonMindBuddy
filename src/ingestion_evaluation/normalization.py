"""Pinned, offline counterfactual normalization of retained actual responses.

This is not an ingestion producer. It never replaces a saved candidate or its
actual inference receipts, and refuses treatment comparison without exact old
candidate reconstruction.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

from ingestion_evaluation.runner import digest, read_pin, seal, tooling_identity

SCHEMA = 'dmb_retained_normalization_v1'


def verify_runtime(pin: dict) -> dict:
    manifest = json.loads(read_pin(pin))
    root = Path(manifest['root'])
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError('Runtime root must be an absolute real directory')
    root = root.resolve()
    seen = set()
    for row in manifest['files']:
        rel = Path(row['path'])
        target = root / rel
        if (rel.is_absolute() or '..' in rel.parts or str(rel) in seen
                or target.is_symlink() or not target.resolve().is_relative_to(root)):
            raise ValueError('Unsafe or duplicate runtime member')
        seen.add(str(rel))
        read_pin({'path': str(target), 'sha256': row['sha256']})
    if not seen:
        raise ValueError('Empty runtime manifest')
    return manifest


def select_responses(raw: dict, run: dict, canonical_bytes) -> dict:
    """Follow explicit accepted-component links, never array order or siblings."""
    binding = raw['execution_evidence']['binding']
    lineage = run['lineage']
    for key, expected in {'run_id': run['run_id'], 'model_id': lineage['model_id'],
                          'profile_id': run['profile_id'], 'source_artifact_id': run['source_artifact_id'],
                          'source_sha256': lineage['source_sha256']}.items():
        if binding.get(key) != expected:
            raise ValueError('Retained execution binding mismatch: ' + key)
    if type(binding.get('prepared_revision')) is not int or not 0 < binding['prepared_revision'] <= run['revision']:
        raise ValueError('Invalid prepared revision binding')
    records = {}
    for row in raw['execution_evidence']['records']:
        if row['kind'] != 'raw_model_response':
            continue
        envelope = row['envelope']
        if digest(canonical_bytes(envelope) + b'\n') != row['sha256']:
            raise ValueError('Retained envelope hash mismatch')
        if row['sha256'] in records:
            raise ValueError('Duplicate retained response component')
        records[row['sha256']] = envelope
    selected, ordinals = {}, set()
    for observation in raw['execution_observations']:
        name, ordinal = observation['pass_name'], observation['ordinal']
        if name in selected or ordinal in ordinals or type(ordinal) is not int:
            raise ValueError('Duplicate accepted pass or ordinal')
        ordinals.add(ordinal)
        link = observation['response_component']
        envelope = records[link['sha256']]
        if (link['kind'] != 'raw_model_response' or observation['external_outcome'] != 'completed'
                or observation.get('worker_cleanup') != 'reaped'
                or envelope['pass_name'] != name or envelope['pass_ordinal'] != ordinal
                or envelope['execution_binding'] != binding or not isinstance(envelope.get('ge_attempt'), dict)
                or envelope['request']['facts']['model'] != binding['model_id']
                or observation['model'] != binding['model_id']
                or envelope['ge_attempt'].get('requested_model') != binding['model_id']
                or observation['requested_provider'] != envelope['request']['facts']['provider']
                or observation['requested_route'] != envelope['request']['facts']['provider_route']
                or observation['reasoning_effort'] != envelope['request']['facts']['reasoning_effort']):
            raise ValueError('Accepted response linkage or outcome mismatch')
        response = envelope['response']
        body = response['text'].encode('utf-8')
        if digest(body) != response['sha256'] or len(body) != response['utf8_bytes']:
            raise ValueError('Response text receipt mismatch')
        selected[name] = {'envelope': envelope, 'observation': observation, 'component': link}
    if ordinals != set(range(1, len(selected) + 1)):
        raise ValueError('Accepted pass ordinals are incomplete')
    return selected


def verify_runtime_imports(manifest: dict):
    """Every loaded source inside a runtime must be a pinned member."""
    root = Path(manifest['root']).resolve()
    members = {row['path']: row['sha256'] for row in manifest['files']}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            relative = str(path.relative_to(root))
            if relative not in members:
                raise ValueError('Imported runtime member is not pinned: ' + relative)
            read_pin({'path': str(path), 'sha256': members[relative]})


def _deny_effects():
    import socket
    import sqlite3

    def denied(*args, **kwargs):
        raise RuntimeError('Offline normalization forbids network, database and child-process effects')

    socket.create_connection = socket.getaddrinfo = denied
    for name in ('connect', 'connect_ex', 'send', 'sendall', 'sendto'):
        setattr(socket.socket, name, denied)
    subprocess.Popen = os.system = denied
    for name in ('posix_spawn', 'posix_spawnp', 'fork'):
        if hasattr(os, name):
            setattr(os, name, denied)
    sqlite3.connect = denied
    try:
        import psycopg
    except ImportError:
        pass
    else:
        psycopg.connect = denied
        psycopg.Connection.connect = denied
        psycopg.AsyncConnection.connect = denied


def prepared_prompts(bounded, facts, pass_name, instructions, user_content, spec, packet):
    """Execute pinned request preparation, stopping at request construction.

    The client remains unbound. No persistence or engine dispatch is reached;
    the existing request-type injection seam captures effective prompt text.
    """
    class Captured(BaseException):
        pass

    captured = []

    def capture(**kwargs):
        captured.append(kwargs)
        raise Captured()

    def forbidden_engine(*args, **kwargs):
        raise RuntimeError('Offline request preparation reached an engine')

    client = bounded.BoundedRecapPassClient(bounded.RecapExecutionLimits(
        provider=facts['provider'], model=facts['model'],
        reasoning_effort=facts['reasoning_effort'],
    ), engine_factory=forbidden_engine)
    client._request_type = capture
    try:
        client.run_pass(pass_name, model_id=facts['model'], instructions=instructions,
                        user_content=user_content, pass_spec=spec, source_evidence_packet=packet)
    except Captured:
        pass
    if len(captured) != 1 or client.execution_binding is not None or client.calls:
        raise ValueError('Pinned request preparation did not stop before execution')
    return captured[0]['system_prompt'], captured[0]['user_prompt']


def _worker(job_path: Path):
    """Internal pure-product worker. Public entry is compare(), not this function."""
    import resource
    job = json.loads(job_path.read_bytes())
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    if job['tooling_sha256'] != tooling_identity():
        raise ValueError('Worker tooling changed')
    environment = json.loads(read_pin(job['environment']))
    for pin in environment['files']:
        read_pin(pin)
    sys.path.extend(environment['import_roots'])
    runtime = verify_runtime(job['runtime'])
    root = Path(runtime['root']).resolve()
    sys.path[:0] = [str(root), str(root / 'src')]
    _deny_effects()
    from src.graph_memory.extraction import category_candidate_graph_extractor as owner
    from src.graph_memory.extraction import bounded_recap_execution as bounded
    from src.graph_memory.extraction.category_candidate_graph_schema import category_pass_text_format_for_spec
    from src.graph_memory.extraction.source_sentence_evidence import materialize_node_evidence, node_wire_schema
    from jsonschema import validate
    verify_runtime_imports(runtime)
    if not Path(owner.__file__).resolve().is_relative_to(root):
        raise ValueError('Product import escaped the pinned runtime')
    case = job['case']
    result = json.loads(read_pin(case['result']))
    run = result['run']
    source = read_pin(case['source']).decode('utf-8')
    request = json.loads(read_pin(case['request']))
    index = json.loads(read_pin(result['components']['source_span_index']))
    raw = json.loads(read_pin(result['components']['raw_model_response']))
    selected = select_responses(raw, run, bounded._canonical_json_bytes)
    profile = owner.resolve_extraction_profile(owner.CategoryGraphExtractionOptions(
        campaign_id=run['campaign_id'], session_id=run['session_id'], session_number=request['session'],
        source_span_index=index,
    ))
    if profile.qualified_id != run['profile_id'] or run.get('status') != 'reviewable':
        raise ValueError('Original profile or run status is not supported')
    expected_passes = [p.pass_id for p in profile.node_passes]
    if profile.beat_pass is not None:
        expected_passes.append(profile.beat_pass.pass_id)
    if profile.enable_encounter_job_pass or profile.edge_review_pass is not None:
        raise ValueError('This offline adapter requires the ordinary source-only profile')
    expected_passes.append(profile.edge_pass.pass_id)
    if set(selected) != set(expected_passes) or [selected[p]['observation']['ordinal'] for p in expected_passes] != list(range(1, len(expected_passes) + 1)):
        raise ValueError('Complete configured pass fixtures are required')
    context = run['lineage']['known_character_bindings']
    context_payload = {k: v for k, v in context.items() if k != 'sha256'}
    if (context['sha256'] != digest(json.dumps(context_payload, sort_keys=True, separators=(',', ':')).encode())
            or context['source_sha256'] != digest(source.encode())
            or run['lineage']['source_sha256'] != digest(source.encode())
            or request['campaign_id'] != run['campaign_id']
            or index['source_artifact_id'] != run['source_artifact_id']):
        raise ValueError('Source or retained character context mismatch')
    requests = {}

    class ActualFixture(owner.FixtureCategoryGraphPassClient):
        supports_node_source_handles = True

        def run_pass(self, pass_name, *, model_id, instructions, user_content, pass_spec=None, source_evidence_packet=None):
            entry = selected[pass_name]
            envelope = entry['envelope']
            actual_request = envelope['request']
            system, user = prepared_prompts(bounded, actual_request['facts'], pass_name,
                                            instructions, user_content, pass_spec, source_evidence_packet)
            hashes = {'system_prompt_sha256': digest(system.encode()),
                      'user_prompt_sha256': digest(user.encode())}
            if model_id != run['lineage']['model_id'] or any(actual_request[k] != v for k, v in hashes.items()):
                raise ValueError('Reconstructed request differs from actual request')
            parsed = owner.parse_json_object(envelope['response']['text'])
            schema = category_pass_text_format_for_spec(pass_spec)['format']['schema']
            if source_evidence_packet is not None:
                expected = envelope['context_sha256']['node_source_packet']
                if source_evidence_packet.packet_id != expected:
                    raise ValueError('Source packet fingerprint mismatch')
                validate(parsed, node_wire_schema(schema, source_evidence_packet))
                parsed = materialize_node_evidence(source_evidence_packet, parsed, expected_packet_id=expected)
            validate(parsed, schema)
            self._pass_outputs[pass_name] = parsed
            requests[pass_name] = hashes
            return super().run_pass(pass_name, model_id=model_id, instructions=instructions,
                                    user_content=user_content, pass_spec=pass_spec)

    product = owner.extract_category_candidate_graph(owner.CategoryGraphExtractionOptions(
        campaign_id=run['campaign_id'], session_id=run['session_id'], session_number=request['session'],
        source_span_index=index, source_text=source, model_id=run['lineage']['model_id'],
        source_artifact_id=run['source_artifact_id'], known_character_context=context,
    ), client=ActualFixture({}))
    verify_runtime(job['runtime'])
    verify_runtime_imports(runtime)
    seal(Path(job['product_output']), {'candidate': product.candidate_graph, 'requests': requests,
                                      'scope': 'Counterfactual normalization only; fixture metrics omitted'})


def compare(manifest_path: Path) -> dict:
    body = manifest_path.read_bytes()
    manifest = json.loads(body)
    if (manifest.get('schema') != SCHEMA or manifest.get('tooling_sha256') != tooling_identity()
            or set(manifest) != {'schema', 'tooling_sha256', 'interpreter', 'environment', 'runtimes', 'cases', 'output', 'worker_timeout_seconds'}):
        raise ValueError('Invalid or unpinned normalization manifest')
    if not Path(manifest['interpreter']['path']).is_absolute() or not Path(manifest['output']).is_absolute():
        raise ValueError('Interpreter and output paths must be absolute')
    if set(manifest['runtimes']) != {'control', 'treatment'}:
        raise ValueError('Exactly control and treatment runtime pins are required')
    read_pin(manifest['interpreter'])
    environment = json.loads(read_pin(manifest['environment']))
    if not environment.get('scope') or not environment.get('files') or not environment.get('import_roots'):
        raise ValueError('Explicit dependency pins and reproducibility scope are required')
    for pin in environment['files']:
        read_pin(pin)
    dependency_roots = []
    for value in environment['import_roots']:
        root = Path(value)
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise ValueError('Dependency import roots must be absolute real directories')
        dependency_roots.append(root.resolve())
    roots = [Path(verify_runtime(manifest['runtimes'][arm])['root']).resolve() for arm in ('control', 'treatment')]
    timeout = manifest['worker_timeout_seconds']
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise ValueError('Offline worker timeout must be 1..60 seconds')
    output = Path(manifest['output']).resolve()
    inputs = [manifest_path.resolve(), Path(manifest['environment']['path']).resolve()]
    ids, run_ids = set(), set()
    for case in manifest['cases']:
        if (not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', case['id']) or case['id'] in ids
                or set(case) != {'id', 'result', 'source', 'request', 'assessment'}):
            raise ValueError('Invalid or duplicate normalization case')
        ids.add(case['id'])
        for key in ('result', 'source', 'request', 'assessment'):
            read_pin(case[key])
            inputs.append(Path(case[key]['path']).resolve())
        result = json.loads(read_pin(case['result']))
        run_id = result['run']['run_id']
        if run_id in run_ids:
            raise ValueError('Original run reused across cases')
        run_ids.add(run_id)
        from ingestion_evaluation.assessment import report as assessment_report
        assessment_report(Path(case['assessment']['path']))
        subject = json.loads(read_pin(case['assessment']))['subject']
        if (subject['result']['artifact']['sha256'] != case['result']['sha256']
                or subject['result']['pointer'] != '/run'
                or subject['candidate']['sha256'] != result['components']['candidate_graph']['sha256']):
            raise ValueError('Raw assessment belongs to another original result')
        for kind in ('candidate_graph', 'raw_model_response', 'source_span_index'):
            pin = result['components'][kind]
            if pin['sha256'] != result['run']['components'][kind]['sha256']:
                raise ValueError('Original component binding mismatch')
            read_pin(pin)
            inputs.append(Path(pin['path']).resolve())
    if not ids or any(output == root or output.is_relative_to(root) or root.is_relative_to(output) for root in roots + dependency_roots):
        raise ValueError('Empty cases or output overlaps runtime')
    if any(path == output or path.is_relative_to(output) for path in inputs):
        raise ValueError('Output overlaps an input')
    receipt = output / 'report.json'
    completion = output / 'completion.json'
    if output.exists():
        if not completion.exists():
            raise ValueError('Existing incomplete or failed normalization output; preserve it')
        finished = json.loads(completion.read_bytes())
        read_pin(finished['report'])
        prior = json.loads(receipt.read_bytes())
        if prior['manifest_sha256'] != digest(body):
            raise ValueError('Output belongs to another manifest')
        for pin in prior['artifacts']:
            read_pin(pin)
        return prior
    output.mkdir(parents=True)
    seal(output / 'manifest.json', manifest)
    report = {'schema': 'dmb_retained_normalization_report_v1', 'manifest_sha256': digest(body),
              'scope': 'Offline counterfactuals, not new inference, raw scores, DB candidates or publication',
              'environment': manifest['environment'], 'cases': [],
              'artifacts': [{'path': str(output / 'manifest.json'),
                             'sha256': digest((output / 'manifest.json').read_bytes())}]}
    def artifact(path):
        pin = {'path': str(path), 'sha256': digest(path.read_bytes())}
        report['artifacts'].append(pin)
        return pin
    try:
        for case in manifest['cases']:
            folder = output / case['id']
            folder.mkdir()
            products = {}
            for arm in ('control', 'treatment'):
                target = folder / (arm + '.json')
                job = folder / (arm + '.job.json')
                seal(job, {'runtime': manifest['runtimes'][arm], 'case': case, 'product_output': str(target),
                           'environment': manifest['environment'], 'tooling_sha256': manifest['tooling_sha256']})
                stderr = folder / (arm + '.stderr')
                runtime_root = roots[('control', 'treatment').index(arm)]
                env = {'PATH': str(Path(manifest['interpreter']['path']).parent),
                       'PYTHONPATH': str(Path(__file__).resolve().parents[1]),
                       'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                       'PYTHONPYCACHEPREFIX': str(folder / (arm + '.empty-cache')), 'LANG': 'C.UTF-8'}
                with stderr.open('xb') as log:
                    proc = subprocess.run([manifest['interpreter']['path'], '-S', str(Path(__file__).resolve()),
                                           '--worker', str(job)], cwd=runtime_root, env=env,
                                          stdout=subprocess.DEVNULL, stderr=log, timeout=timeout)
                artifact(job); artifact(stderr)
                if proc.returncode:
                    raise ValueError(f'Offline {arm} worker failed with exit {proc.returncode}; see retained stderr')
                artifact(target)
                products[arm] = json.loads(target.read_bytes())
                verify_runtime(manifest['runtimes'][arm])
                for pin in environment['files']:
                    read_pin(pin)
                if arm == 'control':
                    original = json.loads(read_pin(json.loads(read_pin(case['result']))['components']['candidate_graph']))
                    if products[arm]['candidate'] != original:
                        raise ValueError('Old candidate reconstruction differs; treatment comparison refused')
            old, new = products['control'], products['treatment']
            keys = set(old['candidate']) | set(new['candidate'])
            report['cases'].append({'id': case['id'], 'old_reconstruction': 'exact_decoded_equality',
                                    'changed_root_fields': sorted(k for k in keys if old['candidate'].get(k) != new['candidate'].get(k)),
                                    'requests_equal': old['requests'] == new['requests'],
                                    'actual_result': case['result'], 'unchanged_raw_assessment': case['assessment']})
        seal(receipt, report)
        seal(completion, {'manifest_sha256': digest(body),
                          'report': {'path': str(receipt), 'sha256': digest(receipt.read_bytes())}})
        return report
    except Exception as exc:
        seal(output / 'failure.json', {'schema': 'dmb_normalization_failure_v1',
                                      'manifest_sha256': digest(body), 'error_type': type(exc).__name__,
                                      'reason': str(exc), 'artifacts': [{'path': str(p), 'sha256': digest(p.read_bytes())}
                                                                       for p in sorted(output.rglob('*')) if p.is_file()],
                                      'scope': 'No successful comparison or inference receipt'})
        raise


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--worker':
        raise SystemExit('Internal worker; use evaluate_ingestion.py normalization-compare --manifest')
    _worker(Path(sys.argv[2]))
