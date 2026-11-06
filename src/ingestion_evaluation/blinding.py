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
        }),
    }
    public = {name: _pin(output / name, body) for name, body in outputs.items()}
    receipt = encoded({'schema': 'dmb_blinded_review_projection_v1', 'review_id': review_id,
        'result': result_pin, 'components': {k: components[k] for k in ('candidate_graph', 'raw_model_response')},
        'public': public, 'response_mapping': mapping,
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
