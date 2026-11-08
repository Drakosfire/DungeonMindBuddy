"""Plan's real orchestration retains failures without turning them into answers."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.live_control_server.services import plan_jev_harness as module
from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError


@pytest.mark.parametrize('code', ['plan_authoring_destination_unavailable', 'plan_authoring_target_unavailable'])
def test_refusal_is_observed_before_terminal_settlement(monkeypatch, code):
    harness = module.PlanJevHarness()
    error = AgentTurnServiceError('A destination is required.', code=code, status_code=409)
    harness.execute = Mock(side_effect=error)
    events = []
    adapter = SimpleNamespace(context_capture=SimpleNamespace(observe=lambda value: events.append(value)),
        fence=SimpleNamespace(turn=SimpleNamespace(status='running')), service=object())
    def settle(*args, **kwargs):
        assert events == [dict(kind='failure', phase='delivery', code=code)]
        assert kwargs['failure_code_override'] == code
    monkeypatch.setattr('apps.live_control_server.services.agent_turn_service._interrupt_policy_delivery', settle)
    trace = Mock()
    with pytest.raises(AgentTurnServiceError) as failed:
        harness.execute_response(adapter, owner=None, trace=trace)
    assert failed.value is error
    trace.finalize_and_log.assert_called_once()


@pytest.mark.parametrize('capture_fails', [False, True])
def test_unexpected_failure_does_not_export_exception_text_or_disappear(monkeypatch, capture_fails):
    harness = module.PlanJevHarness()
    harness.execute = Mock(side_effect=ValueError('PRIVATE_PROVIDER_OR_STORY_TEXT'))
    observed = []
    def observe(event):
        observed.append(event)
        if capture_fails:
            raise RuntimeError('observation unavailable')
    adapter = SimpleNamespace(context_capture=SimpleNamespace(observe=observe), fence=None)
    trace = Mock()
    with pytest.raises(AgentTurnServiceError) as failed:
        harness.execute_response(adapter, owner=None, trace=trace)
    assert failed.value.code == 'plan_jev_delivery_failure'
    assert observed == [dict(kind='failure', phase='delivery', code='plan_jev_delivery_failure')]
    assert 'PRIVATE_PROVIDER_OR_STORY_TEXT' not in str(observed)
    assert isinstance(failed.value.__cause__, ValueError)
    trace.finalize_and_log.assert_called_once()


def test_cleanup_cannot_replace_the_known_destination_refusal(monkeypatch):
    harness = module.PlanJevHarness()
    semantic = SimpleNamespace(call=None, run=Mock())
    async def select(**kwargs):
        return 'different_destination', None
    semantic.run = select
    monkeypatch.setattr(module.PlanJevDispatch, 'requested_work', lambda *args, **kwargs: semantic)
    monkeypatch.setattr(module, 'PlanRulesRuntime', lambda *args: object())
    adapter = SimpleNamespace(work=SimpleNamespace(plan_markdown='# Session preparation'),
        fence=object(), stop=Mock(side_effect=RuntimeError('claim cleanup failed')))
    with pytest.raises(AgentTurnServiceError) as failed:
        harness.execute(adapter)
    assert failed.value.code == 'plan_authoring_destination_unavailable'
    adapter.stop.assert_called_once()
    assert harness.calls == []
