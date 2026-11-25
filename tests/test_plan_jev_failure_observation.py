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
        request=SimpleNamespace(surface=SimpleNamespace(surface_id='plan')),
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
    adapter = SimpleNamespace(context_capture=SimpleNamespace(observe=observe), fence=None,
        request=SimpleNamespace(surface=SimpleNamespace(surface_id='plan')))
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
    driver = Mock(calls=[])
    driver.decision_arguments.return_value = {}
    monkeypatch.setattr(module, 'PlanJevDriver', lambda *args, **kwargs: driver)
    monkeypatch.setattr('apps.live_control_server.services.native_authored_references.acquire', lambda *args: None)
    from application_state.agent_conversation.types import PlanContextPolicyV2
    adapter = SimpleNamespace(work=SimpleNamespace(plan_markdown='# Session preparation'),
        request=SimpleNamespace(plan_context_policy=PlanContextPolicyV2(policy='auto_plan_world', graph_source='reviewed_native_graph')),
        claim_native_plan_request=Mock(), fence=object(), stop=Mock(side_effect=RuntimeError('claim cleanup failed')))
    with pytest.raises(AgentTurnServiceError) as failed:
        harness.execute(adapter)
    assert failed.value.code == 'plan_authoring_destination_unavailable'
    adapter.stop.assert_called_once()
    assert harness.calls == []


def test_guest_model_write_selection_never_reserves_action(monkeypatch):
    from application_state.agent_conversation.types import PlanContextPolicyV2
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal

    async def select(**_kwargs):
        return 'write_current_page', None

    semantic = SimpleNamespace(call=None, run=select)
    monkeypatch.setattr(module.PlanJevDispatch, 'requested_work', lambda *args, **kwargs: semantic)
    monkeypatch.setattr(module, 'PlanRulesRuntime', lambda *args: object())
    driver = Mock(calls=[])
    driver.decision_arguments.return_value = {}
    monkeypatch.setattr(module, 'PlanJevDriver', lambda *args, **kwargs: driver)
    monkeypatch.setattr('apps.live_control_server.services.native_authored_references.acquire', lambda *args: None)
    principal = HostedGuestGraphPrincipal(subject='hosted_guest', role='gm', auth_method='hosted_guest',
        managed_world_id='world', session_id='session', request=SimpleNamespace())
    turn = SimpleNamespace(graph_context_receipt=None,
        graph_context_execution=SimpleNamespace(policy=SimpleNamespace(action=object())))
    fence = SimpleNamespace(turn=turn, begin_plan_opening=Mock())
    service = SimpleNamespace(reserve_plan_authoring_action=Mock())
    adapter = SimpleNamespace(work=SimpleNamespace(plan_markdown='# Plan'), turn=turn,
        request=SimpleNamespace(plan_context_policy=PlanContextPolicyV2(policy='auto_plan_world', graph_source='reviewed_native_graph')),
        native_principal=principal, claim_native_plan_request=Mock(), fence=fence, service=service, stop=Mock())
    with pytest.raises(AgentTurnServiceError) as failed:
        module.PlanJevHarness().execute(adapter)
    assert failed.value.code == 'guest_turn_capability_unavailable'
    service.reserve_plan_authoring_action.assert_not_called()
