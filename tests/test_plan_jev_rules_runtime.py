"""Plan controller → direct Rules reader through current actual APP owners."""
import asyncio
import pytest
from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_events import RulesPlanJevToolAuthorizedV1, RulesQueryObservedV1
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
from apps.live_control_server.services import agent_turn_service as owner
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import Decisions
from tests.test_rules_lookup_broker import args


def test_actual_selected_plan_rules_read_is_one_question_and_one_packet(plan_adapter, monkeypatch):
    from apps.live_control_server.services import rules_lookup_broker as broker
    a = plan_adapter
    a.request = a.request.model_copy(update={'message': args().question})
    a.submitted_intent = owner._submitted_turn_intent(a.request, world_id=a.world_id)
    rules = PlanRulesRuntime(a, rules_capability(graph=True))
    assert rules.native is None and a.rules_runtime is None
    calls = []; original = broker.prepare_plan_lookup
    def reader(execution, call_id, question, **kwargs):
        calls.append(question)
        return original(execution, call_id, question, **kwargs)
    monkeypatch.setattr(broker, 'prepare_plan_lookup', reader)
    driver = PlanJevDriver(a, rules=rules)
    proof = asyncio.run(driver.run(transport=Decisions(), api_key='synthetic-not-secret'))
    assert calls == [a.request.message] and rules.selected
    execution = rules.native.record.execution
    assert len([event for event in execution.events if isinstance(event, RulesPlanJevToolAuthorizedV1)]) == 1
    assert len([event for event in execution.events if isinstance(event, RulesQueryObservedV1)]) == 1
    first = rules.frame(); second = rules.frame()
    assert first == second and len(first.lookups) == 1 and first.lookups[0].status == 'evidence'
    assert proof['graph_packets'] == {} and proof['source_names'] == {}
    with pytest.raises(ValueError, match='repeat'): rules.lookup_selected('changed request')
    assert calls == [a.request.message]


def test_unused_rules_offer_binds_empty_frame_without_corpus_read(plan_adapter, monkeypatch):
    from apps.live_control_server.services import rules_lookup_broker as broker
    from tests.test_plan_jev_dispatch import controller, Wire
    rules = PlanRulesRuntime(plan_adapter, rules_capability(graph=True))
    # The actual controller explicitly finishes without choosing any read.
    asyncio.run(controller(plan_adapter).run(transport=Wire(plan_adapter), api_key='synthetic-not-secret'))
    monkeypatch.setattr(broker, 'prepare_plan_lookup', lambda *_args, **_kwargs: pytest.fail('unused offer read corpus'))
    assert rules.native is None
    assert rules.frame().lookups == () and not rules.selected
    assert rules.native.record.execution.events == ()


def test_plan_rules_offer_needs_plan_surface_and_initialization_needs_claim(plan_adapter):
    rules = PlanRulesRuntime(plan_adapter, rules_capability(graph=True))
    with pytest.raises(ValueError, match='actual Plan claim'): rules.frame()
    assert rules.native is None and plan_adapter.rules_runtime is None
    plan_adapter.request = plan_adapter.request.model_copy(update={'surface':
        plan_adapter.request.surface.model_copy(update={'surface_id': 'play'})})
    with pytest.raises(ValueError, match='exact current Graph capability'):
        PlanRulesRuntime(plan_adapter, rules_capability(graph=True))
