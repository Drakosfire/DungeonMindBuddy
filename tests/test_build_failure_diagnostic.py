from hashlib import sha256
import json
import stat
from uuid import uuid4

import pytest

from apps.live_control_server.services.build_failure_diagnostic import store_failure
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from application_state.agent_conversation.context_trace import TraceFailure
from types import SimpleNamespace


def test_private_diagnostic_retains_cause_without_exposing_messages_in_trace(tmp_path, monkeypatch):
    monkeypatch.setattr('apps.live_control_server.services.build_failure_diagnostic.artifact_data_root', lambda: tmp_path)
    try:
        try:
            raise ValueError('private source excerpt and secret-like string')
        except ValueError as exc:
            raise RuntimeError('outer private message') from exc
    except RuntimeError as exc:
        result = store_failure(exc, stage='controller_prepare', turn_id=uuid4(), attempt=1)
    path = tmp_path / 'out' / 'agent_failure_evidence' / (str(result['diagnostic_id']) + '.json')
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert sha256(path.read_bytes()).hexdigest() == result['diagnostic_sha256']
    value = json.loads(path.read_bytes())
    assert value['exception_types'] == ['RuntimeError', 'ValueError']
    assert 'private source excerpt' in value['traceback']
    projection = TraceFailure(kind='failure', code='build_execution_exception', phase='delivery',
        sequence=0, elapsed_ms=1, **result)
    assert 'private source excerpt' not in projection.model_dump_json()
    assert 'outer private message' not in projection.model_dump_json()


def test_diagnostic_directory_symlink_refused(tmp_path, monkeypatch):
    monkeypatch.setattr('apps.live_control_server.services.build_failure_diagnostic.artifact_data_root', lambda: tmp_path)
    (tmp_path / 'out').mkdir()
    (tmp_path / 'target').mkdir()
    (tmp_path / 'out' / 'agent_failure_evidence').symlink_to(tmp_path / 'target')
    with pytest.raises(OSError):
        store_failure(ValueError('private'), stage='controller_prepare', turn_id=uuid4(), attempt=1)
    assert not list((tmp_path / 'target').iterdir())


def test_telemetry_failure_does_not_replace_original_error(monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise OSError('private storage failure')
    monkeypatch.setattr('apps.live_control_server.services.build_failure_diagnostic.store_failure', fail)
    harness = BuildJevHarness()
    harness.failure_stage = 'controller_prepare'
    adapter = SimpleNamespace(turn=SimpleNamespace(turn_id=uuid4(), attempt=1), context_capture=None)
    harness._capture_failure(adapter, ValueError('original fault'))
    assert 'original exception preserved' in caplog.text


def test_incomplete_diagnostic_reference_is_refused():
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match='complete reference'):
        TraceFailure(kind='failure', code='build_execution_exception', phase='delivery',
            sequence=0, elapsed_ms=1, diagnostic_id=uuid4())


def test_large_traceback_is_bounded_and_marked(tmp_path, monkeypatch):
    monkeypatch.setattr('apps.live_control_server.services.build_failure_diagnostic.artifact_data_root', lambda: tmp_path)
    result = store_failure(ValueError('x'*100000), stage='controller_prepare', turn_id=uuid4(), attempt=1)
    path = tmp_path/'out'/'agent_failure_evidence'/(str(result['diagnostic_id'])+'.json')
    value = json.loads(path.read_text())
    assert value['truncated'] and len(value['traceback']) == 64000


def test_only_exact_known_host_reason_is_public():
    from apps.live_control_server.services.build_failure_diagnostic import failure_code
    assert failure_code(ValueError('World passage lacks its host-provided source name')) == 'build_source_name_missing'
    assert failure_code(ValueError('private source text')) == 'build_execution_exception'


def test_unavailable_private_store_records_an_honest_marker(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('private storage failure')
    monkeypatch.setattr('apps.live_control_server.services.build_failure_diagnostic.store_failure', fail)
    observations = []
    adapter = SimpleNamespace(turn=SimpleNamespace(turn_id=uuid4(), attempt=1),
        context_capture=SimpleNamespace(observe=observations.append))
    harness = BuildJevHarness()
    harness.failure_stage = 'controller_prepare'
    harness._capture_failure(adapter, ValueError('private original fault'))
    assert observations == [{'kind': 'failure', 'phase': 'delivery', 'code': 'build_failure_diagnostic_unavailable'}]
