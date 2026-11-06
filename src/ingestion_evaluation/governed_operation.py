"""Shared one-shot governed-operation lifecycle; owning backends prove effects."""
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import time
import traceback
from .runner import digest, seal

class GovernedOperationRunner:
    mode = 'source_authority_v1'
    prefix = 'source'
    qualification_scope = 'Source authority only; no semantic claims or model execution'
    outcome_scope = 'Source authority only; semantic publication and Gold unproven'
    report_scope = 'Source authority only; no automatic replay or semantic acceptance'

    def __init__(self, manifest, manifest_sha, backend):
        if manifest.get('mode') != self.mode:
            raise ValueError(f'An explicit {self.prefix}-authority manifest is required')
        self.manifest, self.sha, self.backend = (manifest, manifest_sha, backend)
        self.output = Path(manifest['_output'])
        if self.output.stat().st_mode & 63:
            raise ValueError('Source evidence directory must be private')

    @contextmanager
    def locked(self):
        with (self.output / 'lifecycle.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def record(self, name, value):
        path = self.output / name
        result = seal(path, value)
        path.chmod(384)
        return result

    def qualification(self, expected=None):
        raw = (self.output / f'{self.prefix}-qualification.json').read_bytes()
        if expected is not None and digest(raw) != expected:
            raise ValueError('Source qualification pin mismatch')
        value = json.loads(raw)
        if value['manifest_sha256'] != self.sha:
            raise ValueError('Source manifest differs from qualification')
        execution = self.output / f'{self.prefix}-execution.json'
        if execution.exists():
            intent = json.loads(execution.read_bytes())
            if intent.get('manifest_sha256') != self.sha or intent.get('qualification_sha256') != digest(raw):
                raise ValueError('Source execution/qualification pins differ')
        return value

    def qualify(self):
        with self.locked(), self.backend.lease():
            if (self.output / f'{self.prefix}-execution.json').exists():
                raise ValueError('Already dispatched; inspect without replay')
            before = self.backend.snapshot()
            prepared = self.backend.preflight()
            if self.backend.snapshot() != before:
                raise ValueError('State changed during source qualification')
            pin = self.record(f'{self.prefix}-qualification.json', {'manifest_sha256': self.sha, 'snapshot': before, 'prepared': prepared, 'scope': self.qualification_scope})
            return {'qualification_sha256': pin, 'operation': prepared['operation']}

    def execute(self, qualification_sha):
        if not qualification_sha:
            raise ValueError('Source qualification SHA is required')
        with self.locked(), self.backend.lease():
            qualified = self.qualification(qualification_sha)
            if (self.output / f'{self.prefix}-execution.json').exists():
                raise ValueError('Already dispatched; inspect without replay')
            if self.backend.snapshot() != qualified['snapshot'] or self.backend.preflight() != qualified['prepared']:
                raise ValueError('Source qualification drift; no dispatch')
            self.record(f'{self.prefix}-execution.json', {'manifest_sha256': self.sha, 'qualification_sha256': qualification_sha, 'operation': qualified['prepared']['operation']})
            transport_error = False
            try:
                self.record(f'{self.prefix}-http.json', self.backend.dispatch())
            except Exception:
                transport_error = True
                self.record(f'{self.prefix}-dispatch-error.json', {'traceback': self.backend.redact(traceback.format_exc())})
            return self._inspect(qualified, f'{self.prefix}-outcome.json', transport_error)

    def _inspect(self, qualified, filename, transport_error=False):
        details = {}
        try:
            after = self.backend.snapshot()
            details['snapshot_sha256'] = self.record(filename + '.snapshot.json', after)
            proof = self.backend.verify(qualified, after)
            proof_sha = self.record(filename + '.proof.json', proof)
            state = 'verified'
            details['proof_sha256'] = proof_sha
        except Exception:
            details['verification_error'] = self.backend.redact(traceback.format_exc())
            try:
                committed = self.backend.committed(qualified['prepared'])
            except Exception:
                committed = False
            state = 'committed_unverified' if committed else 'outcome_unknown'
        result = {'state': state, 'manifest_sha256': self.sha, 'transport_error': transport_error, **details, 'scope': self.outcome_scope, 'retry': 'Never redispatch this intent; inspect owner evidence read-only'}
        self.record(filename, result)
        return result

    def inspect(self):
        with self.locked(), self.backend.lease():
            qualified = self.qualification()
            return self._inspect(qualified, f'{self.prefix}-inspection-{time.time_ns()}.json')

    def report(self):

        def optional(name):
            path = self.output / name
            value = json.loads(path.read_bytes()) if path.exists() else None
            if value is not None and value.get('manifest_sha256') != self.sha:
                raise ValueError('Retained source record uses another manifest')
            return value
        execution, outcome = (optional(f'{self.prefix}-execution.json'), optional(f'{self.prefix}-outcome.json'))
        if execution is not None:
            self.qualification(execution['qualification_sha256'])
        inspections = [p.name for p in sorted(self.output.glob(f'{self.prefix}-inspection-*.json')) if not p.name.endswith(('.proof.json', '.snapshot.json'))]
        latest = optional(inspections[-1]) if inspections else outcome
        return {'execution': execution, 'outcome': outcome, 'latest_assessment': latest, 'state': latest['state'] if latest else 'outcome_unknown' if execution else 'not_dispatched', 'inspections': inspections, 'scope': self.report_scope}
