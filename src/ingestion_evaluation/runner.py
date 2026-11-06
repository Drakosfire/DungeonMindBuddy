"""Manifest-pinned evaluation lifecycle, independent of providers and corpus contents."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
from decimal import Decimal
from typing import Any


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tooling_identity() -> str:
    root = Path(__file__).resolve().parents[2]
    files = [*sorted(Path(__file__).parent.glob('*.py')), root / 'scripts' / 'evaluate_ingestion.py']
    return digest(encoded([{'name': p.name, 'sha256': digest(p.read_bytes())} for p in files]))


def encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, default=str) + '\n').encode()


def read_pin(pin: dict) -> bytes:
    data = Path(pin['path']).read_bytes()
    if digest(data) != pin['sha256']:
        raise ValueError(f"Pin mismatch: {pin['path']}")
    return data


def seal(path: Path, value: Any) -> str:
    data = encoded(value)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return digest(data)


def retain_bytes(path: Path, data: bytes) -> str:
    """Idempotent evidence export, never a reason to redispatch a model request."""
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Existing evidence differs: {path}')
    else:
        with path.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    return digest(data)


def verify_manifest(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema') != 'dmb_ingestion_evaluation_v1':
        raise ValueError('Unsupported evaluation manifest')
    if manifest.get('tooling_sha256') != tooling_identity():
        raise ValueError('Evaluation tooling pin mismatch')
    ids = [item['id'] for item in manifest['items']]
    if not ids or len(ids) != len(set(ids)) or any(
        not isinstance(i, str) or not i or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in i)
        for i in ids
    ):
        raise ValueError('Items require unique safe IDs')
    runtime = json.loads(read_pin(manifest['runtime']))
    root = Path(runtime['root']).resolve()
    for row in runtime['files']:
        name = Path(row['path'])
        if name.is_absolute() or '..' in name.parts:
            raise ValueError('Unsafe runtime member')
        member = root / name
        data = os.readlink(member).encode() if member.is_symlink() else member.read_bytes()
        if digest(data) != row['sha256']:
            raise ValueError(f'Runtime drift: {name}')
    for item in manifest['items']:
        read_pin(item['request'])
        read_pin(item['source'])
    for pin in manifest.get('prior_evidence', []):
        read_pin(pin)
    output = Path(manifest['output']).resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest['_runtime_root'] = str(root)
    manifest['_output'] = str(output)
    return manifest, digest(raw)


def conserve(before: dict, after: dict, append_tables: set[str]) -> None:
    if before.keys() != after.keys():
        raise ValueError('Database table set changed')
    for table, rows in before.items():
        newer = after[table]
        if rows == newer:
            continue
        if table not in append_tables:
            raise ValueError(f'Unpermitted table mutation: {table}')
        old_counts, new_counts = dict(rows), dict(newer)
        if any(new_counts.get(key, 0) < count for key, count in old_counts.items()):
            raise ValueError(f'Prior rows changed: {table}')


class Runner:
    def __init__(self, manifest: dict, manifest_sha: str, backend):
        self.manifest, self.manifest_sha, self.backend = manifest, manifest_sha, backend
        self.output = Path(manifest['_output'])

    def qualify(self) -> str:
        with (self.output / 'lifecycle.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if (self.output / 'qualification.json').exists():
                raise ValueError('Qualification already exists; use a new cohort output directory')
            before = self.backend.snapshot()
            items = [self.backend.qualify(item) for item in self.manifest['items']]
            if before != self.backend.snapshot():
                raise ValueError('State changed during qualification')
            return seal(self.output / 'qualification.json', {
                'manifest_sha256': self.manifest_sha, 'snapshot': before, 'items': items,
                'scope': 'Qualification only; no model or publication acceptance',
            })

    def capture(self, qualification_sha: str) -> dict:
        if any(item.get('retained_run_id') for item in self.manifest['items']):
            raise ValueError('Historical evidence manifests are read-only; never dispatch')
        with (self.output / 'lifecycle.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            qbytes = (self.output / 'qualification.json').read_bytes()
            if digest(qbytes) != qualification_sha:
                raise ValueError('Qualification pin mismatch')
            q = json.loads(qbytes)
            if q['manifest_sha256'] != self.manifest_sha:
                raise ValueError('Manifest changed after qualification')
            # A stopped process is not permission to repeat any request.
            if (self.output / 'execution.json').exists():
                raise ValueError('Execution already dispatched; observe/audit it, never replay')
            if q['snapshot'] != self.backend.snapshot():
                raise ValueError('Database drift after qualification')
            for item, qualified in zip(self.manifest['items'], q['items'], strict=True):
                if self.backend.qualify(item) != qualified:
                    raise ValueError('Source, request or prior-run drift')
            seal(self.output / 'execution.json', {'pid': os.getpid(), 'manifest_sha256': self.manifest_sha,
                 'qualification_sha256': qualification_sha, 'state': 'dispatched'})
            stopping = False

            def stop(_signum, _frame):
                nonlocal stopping
                stopping = True

            previous = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
            completed = []
            status = 'completed'
            try:
                for item, qualified in zip(self.manifest['items'], q['items'], strict=True):
                    if stopping or (self.output / 'PAUSE').exists():
                        status = 'paused'
                        break
                    prefix = self.output / item['id']
                    seal(prefix.with_suffix('.dispatch.json'), {'id': item['id'], 'request': item['request']})
                    # Backend retains HTTP response before interpreting it and never retries.
                    result = self.backend.capture(item, qualified, prefix)
                    seal(prefix.with_suffix('.result.json'), result)
                    completed.append(item['id'])
                    if result['state'] != 'reviewable':
                        status = 'stopped_at_capture_boundary'
                        break
                self.backend.check_conservation(q['snapshot'])
                terminal = {'state': status, 'completed_items': completed,
                            'manifest_sha256': self.manifest_sha}
                seal(self.output / 'terminal.json', terminal)
                return terminal
            finally:
                for signum, handler in previous.items():
                    signal.signal(signum, handler)
                # An exception leaves dispatch markers unproven. Do not fake terminal success.

    def observe(self) -> dict:
        return {'manifest_sha256': self.manifest_sha,
                'terminal': self._optional('terminal.json'),
                'items': [{'id': item['id'], 'dispatched': (self.output / (item['id'] + '.dispatch.json')).exists(),
                           'actual': self.backend.observe(item)} for item in self.manifest['items']]}

    def audit(self, *, retained=False) -> dict:
        with (self.output / 'lifecycle.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if retained and not all(item.get('retained_run_id') for item in self.manifest['items']):
                raise ValueError('Retained audit requires exact pinned run IDs for every item')
            if not retained and not (self.output / 'terminal.json').exists():
                raise ValueError('Terminal evidence missing; interrupted outcome requires inspection, not replay')
            q = json.loads((self.output / 'qualification.json').read_bytes())
            self._verify_chain()
            self.backend.check_conservation(q['snapshot'])
            before_audit = self.backend.snapshot()
            results = []
            for item, qualified in zip(self.manifest['items'], q['items'], strict=True):
                if retained or (self.output / (item['id'] + '.dispatch.json')).exists():
                    results.append({'id': item['id'], **self.backend.audit(item, qualified, self.output)})
            if self.backend.snapshot() != before_audit:
                raise ValueError('State changed during audit; mixed-state evidence is unproven')
            record = {'manifest_sha256': self.manifest_sha, 'items': results,
                      'qualification_sha256': digest((self.output / 'qualification.json').read_bytes()),
                      'conservation_scope': 'Since this qualification only; historical capture conservation remains predecessor evidence',
                      'prior_evidence': self.manifest.get('prior_evidence', []),
                      'scope': 'Capture/evidence/accounting; independent semantic and publication assessment required'}
            seal(self.output / 'audit.json', record)
            return record

    def _optional(self, name):
        path = self.output / name
        return json.loads(path.read_bytes()) if path.exists() else None

    def _verify_chain(self):
        for name in ('qualification.json', 'execution.json', 'terminal.json', 'audit.json'):
            record = self._optional(name)
            if record and record.get('manifest_sha256') != self.manifest_sha:
                raise ValueError(f'Manifest differs from retained {name}')
        execution = self._optional('execution.json')
        if execution and execution['qualification_sha256'] != digest((self.output / 'qualification.json').read_bytes()):
            raise ValueError('Retained qualification differs from execution pin')
        audit = self._optional('audit.json')
        if audit and audit['qualification_sha256'] != digest((self.output / 'qualification.json').read_bytes()):
            raise ValueError('Retained qualification differs from audit pin')

    def report(self) -> dict:
        self._verify_chain()
        audit = self._optional('audit.json')
        boundary = 'qualification'
        if self._optional('qualification.json'):
            boundary = 'capture'
        if audit:
            boundary = next((item.get('failed_boundary') for item in audit['items'] if item.get('failed_boundary')), 'independent_semantic_assessment')
            if boundary == 'independent_semantic_assessment' and len(audit['items']) < len(self.manifest['items']):
                boundary = 'capture_remaining_items'
        summaries = [item.get('accounting', {}).get('summary') if item.get('accounting') else None for item in (audit or {}).get('items', [])]
        accounting = {}
        for field in ('input_tokens', 'output_tokens', 'reasoning_tokens', 'provider_attempts', 'cost_usd'):
            values = [summary.get(field) if summary else None for summary in summaries]
            known = sum((Decimal(str(v)) for v in values if v is not None), Decimal(0))
            accounting[field] = {'reported_sum': str(known), 'complete_total': str(known) if values and all(v is not None for v in values) else None,
                                 'missing_run_count': sum(v is None for v in values)}
        return {'manifest_sha256': self.manifest_sha, 'next_unproven_boundary': boundary,
                'terminal': self._optional('terminal.json'), 'audit': audit,
                'accounting': accounting,
                'publication': 'unproven', 'gold': 'independent source-grounded assessment required'}
