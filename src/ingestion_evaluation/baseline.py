"""Offline, write-once retention of explicitly inventoried study evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .runner import digest, read_pin, seal


CATEGORIES = frozenset({
    'code', 'prompts', 'model_settings', 'original_inputs', 'effective_inputs',
    'name_review', 'graph_context', 'outputs', 'failures_retries', 'usage_cost_time',
    'gold', 'assessment_rules', 'scores',
})


def _validate(spec):
    if set(spec) != {'schema', 'baseline_id', 'categories'} or spec['schema'] != 'dmb_ingestion_baseline_v1':
        raise ValueError('Unsupported baseline inventory')
    if not isinstance(spec['baseline_id'], str) or not spec['baseline_id'].strip():
        raise ValueError('Baseline requires an ID')
    if set(spec['categories']) != CATEGORIES:
        raise ValueError('Every required baseline category must be represented')
    for category, entry in spec['categories'].items():
        if entry.get('status') == 'unknown':
            if set(entry) != {'status', 'reason'} or not isinstance(entry['reason'], str) or not entry['reason'].strip():
                raise ValueError(f'Unknown category requires a reason: {category}')
        elif entry.get('status') == 'retained':
            if set(entry) != {'status', 'artifacts', 'limitations'} or not entry['artifacts']:
                raise ValueError(f'Retained category requires artifacts and limitations: {category}')
            if not isinstance(entry['limitations'], list) or any(not isinstance(x, str) for x in entry['limitations']):
                raise ValueError('Limitations must be explicit text entries')
            for pin in entry['artifacts']:
                if set(pin) != {'path', 'sha256'}:
                    raise ValueError('Artifacts require exact path/hash pins')
        else:
            raise ValueError(f'Unsupported category status: {category}')


def freeze(manifest: Path, output: Path):
    """No backend imports, inference, semantic adjudication, or publication."""
    raw = manifest.read_bytes()
    spec = json.loads(raw)
    _validate(spec)
    # Validate the full input inventory before claiming the output directory.
    for entry in spec['categories'].values():
        for pin in entry.get('artifacts', []):
            read_pin(pin)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    with (output / 'manifest.json').open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    members = {}
    for entry in spec['categories'].values():
        for pin in entry.get('artifacts', []):
            sha = pin['sha256']
            if sha in members:
                continue
            data = read_pin(pin)  # Reject drift between preflight and retention.
            target = output / sha
            with target.open('xb') as stream:
                os.chmod(target, 0o600)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            members[sha] = len(data)
    inventory = {'schema': 'dmb_ingestion_baseline_receipt_v1',
                 'manifest_sha256': digest(raw), 'specification': spec,
                 'members': members, 'scope': 'Evidence retained; quality is not inferred'}
    receipt_sha = seal(output / 'baseline.json', inventory)
    seal(output / 'complete.json', {'receipt_sha256': receipt_sha})
    return verify(output)


def verify(output: Path):
    receipt_bytes = (output / 'baseline.json').read_bytes()
    completion = json.loads((output / 'complete.json').read_bytes())
    if completion != {'receipt_sha256': digest(receipt_bytes)}:
        raise ValueError('Baseline receipt changed')
    receipt = json.loads(receipt_bytes)
    if receipt['schema'] != 'dmb_ingestion_baseline_receipt_v1':
        raise ValueError('Unsupported baseline receipt')
    _validate(receipt['specification'])
    manifest_bytes = (output / 'manifest.json').read_bytes()
    if (digest(manifest_bytes) != receipt['manifest_sha256']
            or json.loads(manifest_bytes) != receipt['specification']):
        raise ValueError('Baseline manifest changed')
    expected = {pin['sha256'] for entry in receipt['specification']['categories'].values()
                for pin in entry.get('artifacts', [])}
    if set(receipt['members']) != expected:
        raise ValueError('Baseline member inventory differs')
    for sha, size in receipt['members'].items():
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Invalid member digest')
        member = output / sha
        if member.is_symlink():
            raise ValueError('Retained members cannot be symlinks')
        data = member.read_bytes()
        if digest(data) != sha or len(data) != size:
            raise ValueError(f'Baseline member changed: {sha}')
    return {'baseline_id': receipt['specification']['baseline_id'],
            'receipt_sha256': digest(receipt_bytes), 'members_verified': len(expected),
            'unknown_categories': sorted(k for k, v in receipt['specification']['categories'].items()
                                         if v['status'] == 'unknown'),
            'scope': receipt['scope']}
