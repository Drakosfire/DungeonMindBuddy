"""One selected dependency lifetime, with fresh native reads and durable guards."""
import asyncio

import pytest
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import Decisions


def selected(adapter):
    dispatch = PlanJevDispatch(adapter, tuple(RetrievalCandidate(
        handle=f"node:{node}", label=node, kind="location") for node in ("pond", "bridge")))
    asyncio.run(dispatch.run(transport=Decisions(), api_key="synthetic-not-secret"))


def test_bundle_binds_once_and_clears_on_error_then_rebinds(plan_adapter, monkeypatch):
    selected(plan_adapter)
    calls = []
    def bind(world):
        assert plan_adapter.authorize({}) is False
        result = object()
        calls.append((world, result))
        return result
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config', bind)
    with pytest.raises(RuntimeError, match="stop"):
        with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
            assert calls == []
            assert plan_adapter._plan_graph_read_services.resolve() is plan_adapter._plan_graph_read_services.resolve()
            assert len(calls) == 1
            with pytest.raises(ValueError, match="current decision"):
                with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
                    pytest.fail("Nested acquisition")
            raise RuntimeError("stop")
    assert plan_adapter._plan_graph_read_services is None
    with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
        assert plan_adapter._plan_graph_read_services.resolve() is calls[1][1]
    assert len(calls) == 2 and calls[0][1] is not calls[1][1]
    assert all(world == plan_adapter.bootstrap.world_scope.world_id for world, _ in calls)


@pytest.mark.parametrize("nodes", [("pond", "foreign"), ("pond", "pond"), ("pond",)])
def test_bundle_refuses_changed_selection_before_native_bind(plan_adapter, monkeypatch, nodes):
    selected(plan_adapter)
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',
        lambda *_: pytest.fail("Unselected native IO"))
    with pytest.raises(ValueError, match="selected targets"):
        with plan_adapter.plan_graph_acquisition(nodes):
            pytest.fail("Invalid acquisition")


def test_unacknowledged_or_failed_bind_never_leaves_active_lifetime(plan_adapter, monkeypatch):
    with pytest.raises(ValueError, match="current decision"):
        with plan_adapter.plan_graph_acquisition(("pond",)):
            pytest.fail("Unacknowledged acquisition")
    selected(plan_adapter)
    def unavailable(world):
        raise RuntimeError("Native binding unavailable")
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config', unavailable)
    with pytest.raises(RuntimeError, match="Native binding unavailable"):
        with plan_adapter.plan_graph_acquisition(("pond", "bridge")):
            plan_adapter._plan_graph_read_services.resolve()
    assert plan_adapter._plan_graph_read_services is None


def test_two_objects_through_real_broker_share_native_context_and_keep_events(plan_adapter, monkeypatch):
    from dataclasses import replace
    from graph_memory.interaction.session import GraphReferent
    from tests.test_world_graph_retrieval_contract import _selected_native_fixture
    services, request, revision = _selected_native_fixture(unrelated=1)
    a = plan_adapter
    scope = replace(a.bootstrap.world_scope, world_id=request.world_id, revision_id=revision)
    a.bootstrap.retrieval_session.snapshot = a.bootstrap.retrieval_session.snapshot.model_copy(update={
        'world_id':request.world_id, 'revision_id':revision})
    a.bootstrap.retrieval_session.referents = [GraphReferent(id=n, label=n) for n in ('obj:tavern','obj:noise:0')]
    a.bootstrap = replace(a.bootstrap, world_scope=scope,
        graph_envelope={**a.bootstrap.graph_envelope, 'world_id':request.world_id,'revision_id':revision})
    candidates = tuple(RetrievalCandidate(handle=f'node:{n}',label=n,kind='location') for n in ('obj:tavern','obj:noise:0'))
    asyncio.run(PlanJevDispatch(a,candidates).run(transport=Decisions(),api_key='synthetic-not-secret'))
    from unittest.mock import Mock
    opened = Mock(wraps=services.projection.open_read_context)
    monkeypatch.setattr(services.projection,'open_read_context',opened)
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',lambda _:services)
    with a.plan_graph_acquisition(('obj:tavern','obj:noise:0')):
        lifetime = a._plan_graph_read_services
        assert opened.call_count == 0 and a.authorize({}) is False
        for node in ('obj:tavern','obj:noise:0'):
            reply = a.broker_graph_operation({'toolName':'expand_graph_retrieval','arguments':{
                'retrievalSessionId':a.bootstrap.retrieval_session.id,'operation':'object',
                'targets':[{'kind':'node','id':node}]}})
            assert a.failure is None, reply
        assert opened.call_count == 1
        retained = lifetime.for_object(request)
    assert a._plan_graph_read_services is None
    with pytest.raises(RuntimeError,match='closed'):
        lifetime.resolve()
    assert retained.object_read_wave._native is None
    events = [e for e in a._broker_execution().events if e.kind=='validated_graph_operation_v3']
    assert len(events)==2 and len({e.operation_id for e in events})==2
    assert all(e.graph_revision==revision and e.returned_source_pins for e in events)
