"""Offline, lossless knowledge projection; operational provenance stays private."""
from __future__ import annotations

import json
from pathlib import Path
import re

from .runner import digest, encoded, read_pin, retain_bytes

_CANDIDATE_KEYS = frozenset({
    'schema', 'version', 'preview_id', 'campaign_id', 'session_id', 'status',
    'source_artifact_ids', 'nodes', 'edges', 'beats', 'source_observations',
    'ignored_items', 'deferred_items', 'diagnostics', 'proposed_writes',
})
_OPERATIONAL_KEYS = frozenset({
    'reasoning_effort', 'usage', 'token_usage', 'cost_usd', 'billed_cost_usd',
    'elapsed_ms', 'pass_telemetry', 'request', 'execution_binding',
})


def _pin(path: Path, body: bytes) -> dict:
    return {'path': str(path.resolve()), 'sha256': digest(body)}


def _reject_operational_fields(value):
    if isinstance(value, dict):
        if _OPERATIONAL_KEYS.intersection(value):
            raise ValueError('Candidate contains unexpected operational fields; investigate, do not redact')
        for child in value.values():
            _reject_operational_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_operational_fields(child)


def _captured_source_context(raw: dict, run: dict, components: dict):
    """Project only the owner's retained dictionary, never regenerate handles."""
    evidence = raw['execution_evidence']
    matches = [(i, row) for i, row in enumerate(evidence['records'])
               if row['kind'] == 'pass_telemetry'
               and (row['envelope'].get('schema') == 'dmb_private_compact_evidence_context_v1'
                    or row['envelope'].get('capture_id') == 'context:compact-evidence-v1')]
    if not matches:
        return None, None
    if len(matches) != 1:
        raise ValueError('Duplicate captured source context')
    ordinal, row = matches[0]
    envelope = row['envelope']
    if (envelope.get('schema') != 'dmb_private_compact_evidence_context_v1'
            or envelope.get('capture_id') != 'context:compact-evidence-v1'
            or envelope.get('node_evidence_status') != 'available'):
        raise ValueError('Invalid captured source context identity')
    # Independent artifact integrity check at the projection boundary. The
    # capture owner hashes canonical UTF-8 JSON plus one trailing newline.
    body = (json.dumps(envelope, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if digest(body) != row['sha256']:
        raise ValueError('Captured source context envelope hash mismatch')
    binding = evidence['binding']
    expected = {'run_id': run['run_id'], 'model_id': run['lineage']['model_id'],
                'profile_id': run['profile_id'], 'source_artifact_id': run['source_artifact_id'],
                'source_sha256': run['lineage']['source_sha256']}
    if (envelope['execution_binding'] != binding
            or any(binding.get(k) != v for k, v in expected.items())
            or type(binding.get('prepared_revision')) is not int
            or not 0 < binding['prepared_revision'] <= run['revision']):
        raise ValueError('Captured source context execution binding mismatch')
    context = envelope['context']
    if (not isinstance(context, dict) or set(context) != {'schema', 'source_sha256', 'entries'}
            or context['schema'] != 'dmb_compact_recap_evidence_context_v1'
            or context['source_sha256'] != binding['source_sha256']
            or not isinstance(context['entries'], list) or not context['entries']):
        raise ValueError('Invalid captured source context shape or source')
    index_pin = components['source_span_index']
    if run['components']['source_span_index']['sha256'] != index_pin['sha256']:
        raise ValueError('Source index component binding mismatch')
    index = json.loads(read_pin(index_pin))
    if (index['source_artifact_id'] != binding['source_artifact_id']
            or index['content_sha256'] != binding['source_sha256']):
        raise ValueError('Captured source context index identity mismatch')
    spans = {span['source_span_id']: span for span in index['spans']}
    if len(spans) != len(index['spans']):
        raise ValueError('Duplicate source index span')
    seen = set()
    for number, entry in enumerate(context['entries'], 1):
        if (not isinstance(entry, dict) or set(entry) != {
                'handle', 'source_span_ref_id', 'text', 'text_sha256', 'line_start', 'line_end'}
                or entry['handle'] != f'E{number}'
                or not isinstance(entry['source_span_ref_id'], str)
                or entry['source_span_ref_id'] in seen
                or entry['source_span_ref_id'] not in spans
                or not isinstance(entry['text'], str) or not entry['text']
                or digest(entry['text'].encode('utf-8')) != entry['text_sha256']
                or type(entry['line_start']) is not int or type(entry['line_end']) is not int
                or entry['line_start'] < 1 or entry['line_end'] < entry['line_start']):
            raise ValueError('Invalid captured source context entry')
        span = spans[entry['source_span_ref_id']]
        if (entry['line_start'], entry['line_end']) != (span['start_line'], span['end_line']):
            raise ValueError('Captured source context line bounds differ from index')
        seen.add(entry['source_span_ref_id'])
    return context, {'original_pointer': f'/execution_evidence/records/{ordinal}/envelope/context',
                     'envelope_sha256': row['sha256'], 'source_span_index': index_pin}


def prepare(result_path: Path, output: Path, private_receipt: Path, review_id: str) -> dict:
    """Keep public evidence directly citeable; bind it privately to the original result."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', review_id):
        raise ValueError('Review ID must be an opaque simple identifier')
    output, private_receipt = output.resolve(), private_receipt.resolve()
    if private_receipt == output or output in private_receipt.parents:
        raise ValueError('Private receipt must be outside the public packet')
    result_body = result_path.read_bytes()
    result_pin = _pin(result_path, result_body)
    result = json.loads(result_body)
    run = result['run']
    components = result['components']
    for kind in ('candidate_graph', 'raw_model_response'):
        if run['components'][kind]['sha256'] != components[kind]['sha256']:
            raise ValueError('Result component binding mismatch')
    candidate_body = read_pin(components['candidate_graph'])
    candidate = json.loads(candidate_body)
    if not isinstance(candidate, dict) or set(candidate) - _CANDIDATE_KEYS:
        raise ValueError('Unexpected candidate shape; investigate before exposure')
    _reject_operational_fields(candidate)
    raw_body = read_pin(components['raw_model_response'])
    raw = json.loads(raw_body)
    source_context, context_mapping = _captured_source_context(raw, run, components)
    responses, mapping = [], []
    for index, record in enumerate(raw['execution_evidence']['records']):
        if record['kind'] == 'pass_telemetry':
            continue
        if record['kind'] != 'raw_model_response':
            raise ValueError('Unexpected execution record kind; cannot silently omit it')
        response = record['envelope']['response']
        text = response['text']
        if not isinstance(text, str):
            raise ValueError('Response text unavailable; cannot silently omit an attempt')
        body = text.encode('utf-8')
        if digest(body) != response['sha256'] or len(body) != response['utf8_bytes']:
            raise ValueError('Response text receipt mismatch')
        ordinal = len(responses)
        envelope = record['envelope']
        # The owner also retains exact host-materialized wrappers under this
        # component kind. They are not additional provider attempts or claims.
        pass_name = envelope.get('pass_name')
        origin = ('host_materialization' if isinstance(pass_name, str)
                  and pass_name.endswith('-normalized') and envelope.get('ge_attempt') is None
                  else 'provider_response' if isinstance(envelope.get('ge_attempt'), dict)
                  else 'unclassified')
        responses.append({'response_id': f'response-{ordinal + 1:04d}',
                          'origin': origin,
                          'text': text, 'text_sha256': digest(body), 'utf8_bytes': len(body)})
        mapping.append({'public_pointer': f'/responses/{ordinal}/text',
                        'original_pointer': f'/execution_evidence/records/{index}/envelope/response/text'})
    if not responses:
        raise ValueError('No recorded model responses to assess')
    binding = {'run_id': run['run_id'], 'revision': run['revision'],
               'candidate_sha256': components['candidate_graph']['sha256'], 'review_id': review_id}
    outputs = {
        'candidate.json': candidate_body,
        'responses.json': encoded({'responses': responses}),
        'binding.json': encoded(binding),
        'scope.json': encoded({
            'scope': 'Semantic inputs only. Source, Gold and neutral owner contracts must be separately pinned.',
            'provenance': 'Response text is the exact retained response record, not necessarily pure authored '
                          'prose. Host source_units wrappers and normalized/excerpt fields are not model '
                          'knowledge credit. Use pinned owner contracts to distinguish origins; model rank '
                          'can survive host title/summary replacement.',
            'limits': 'Operational envelopes excluded; response count, length and authored self-disclosure '
                      'remain visible. No semantic redaction. This directory is not an access-control sandbox.',
            'response_origins': 'host_materialization is an owner-normalized wrapper, not another provider '
                                'attempt. provider_response has retained attempt metadata. unclassified '
                                'requires provenance review; never infer model authorship from its text shape.',
            'evidence_context': ('Captured request-local source dictionary is in evidence-context.json; '
                                 'it is host input evidence, not model-authored knowledge.' if source_context is not None
                                 else 'Unavailable: no captured source dictionary. No aliases were regenerated.'),
        }),
    }
    if source_context is not None:
        outputs['evidence-context.json'] = encoded(source_context)
    public = {name: _pin(output / name, body) for name, body in outputs.items()}
    receipt = encoded({'schema': 'dmb_blinded_review_projection_v1', 'review_id': review_id,
        'result': result_pin, 'components': {k: components[k] for k in ('candidate_graph', 'raw_model_response')},
        'public': public, 'response_mapping': mapping, 'source_context_mapping': context_mapping,
        'sealing': 'Review cites public artifacts unchanged. After sealing, use original result with existing '
                   'assessment assembler; preserve this private mapping and the original sealed review.'})
    # Refuse collisions before any retention, including accidental original-source exposure.
    if output.exists() and set(p.name for p in output.iterdir()) - set(outputs):
        raise ValueError('Public output contains unexpected files')
    targets = {output / name: body for name, body in outputs.items()}
    targets[private_receipt] = receipt
    for target, body in targets.items():
        if target.exists() and target.read_bytes() != body:
            raise ValueError(f'Existing evidence differs: {target}')
    output.mkdir(parents=True, exist_ok=True)
    private_receipt.parent.mkdir(parents=True, exist_ok=True)
    for target, body in targets.items():
        retain_bytes(target, body)
    return {'public': public, 'private_receipt': _pin(private_receipt, receipt)}
