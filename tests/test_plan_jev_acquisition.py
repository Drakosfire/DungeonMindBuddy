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
