"""The public offline CLI preserves bytes, unknowns, and historical runner pins."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ingestion_evaluation.baseline import CATEGORIES, freeze, verify


@pytest.fixture
def evidence(tmp_path):
    source = tmp_path / 'source'
    source.write_bytes(b'exact source\r\n')
    pin = {'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    categories = {k: {'status': 'unknown', 'reason': 'Not measured in historical run'} for k in CATEGORIES}
    categories['original_inputs'] = {'status': 'retained', 'artifacts': [pin], 'limitations': []}
    spec = {'schema': 'dmb_ingestion_baseline_v1', 'baseline_id': 'baseline-one', 'categories': categories}
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(spec))
    return source, manifest, tmp_path / 'frozen'


def test_public_cli_offline_roundtrip_and_independence(evidence):
    source, manifest, output = evidence
    cli = Path(__file__).resolve().parents[1] / 'scripts/evaluate_ingestion.py'
    def call(*args):
        return subprocess.run([sys.executable, str(cli), *args], capture_output=True, text=True, check=True)
    result = json.loads(call('baseline-freeze', '--manifest', str(manifest), '--baseline-output', str(output)).stdout)
    assert result['members_verified'] == 1
    assert 'scores' in result['unknown_categories']
    source.unlink()
    manifest.unlink()
    assert json.loads(call('baseline-verify', '--baseline-output', str(output)).stdout) == result


def test_no_replay_or_overwrite(evidence):
    _, manifest, output = evidence
    freeze(manifest, output)
    before = (output / 'complete.json').read_bytes()
    with pytest.raises(FileExistsError):
        freeze(manifest, output)
    assert (output / 'complete.json').read_bytes() == before


def test_bad_input_does_not_claim_output(evidence):
    source, manifest, output = evidence
    source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='Pin mismatch'):
        freeze(manifest, output)
    assert not output.exists()


@pytest.mark.parametrize('member', ['data', 'manifest.json', 'baseline.json'])
def test_retained_mutation_is_detected(evidence, member):
    source, manifest, output = evidence
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    freeze(manifest, output)
    (output / (sha if member == 'data' else member)).write_bytes(b'{}')
    with pytest.raises((ValueError, KeyError)):
        verify(output)


def test_missing_category_and_unexplained_unknown_rejected(evidence):
    _, manifest, output = evidence
    spec = json.loads(manifest.read_text())
    spec['categories']['scores']['reason'] = ''
    manifest.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='reason'):
        freeze(manifest, output)
    del spec['categories']['scores']
    manifest.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='Every required'):
        freeze(manifest, output)


def test_mid_copy_failure_cannot_complete_or_replay(evidence, monkeypatch):
    import ingestion_evaluation.baseline as baseline
    _, manifest, output = evidence
    original = baseline.read_pin
    calls = 0
    def interrupted_copy(pin):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('Injected retention failure after preflight')
        return original(pin)
    monkeypatch.setattr(baseline, 'read_pin', interrupted_copy)
    with pytest.raises(OSError, match='Injected retention failure'):
        freeze(manifest, output)
    assert output.exists() and not (output / 'complete.json').exists()
    with pytest.raises(FileNotFoundError):
        verify(output)
    with pytest.raises(FileExistsError):
        freeze(manifest, output)
