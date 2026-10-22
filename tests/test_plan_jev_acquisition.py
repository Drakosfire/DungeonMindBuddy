"""Real acknowledged APP choices, independent native IO, sequential admission."""
import asyncio
from threading import Barrier, Event

import pytest
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from apps.live_control_server.services import plan_jev_acquisition as acquisition
from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import Decisions


def selected(adapter, nodes=("pond", "bridge")):
    dispatch = PlanJevDispatch(adapter, tuple(RetrievalCandidate(
        handle=f"node:{node}", label=node, kind="location") for node in nodes))
    asyncio.run(dispatch.run(transport=Decisions(), api_key="synthetic-not-secret"))
    return dispatch


def test_native_reads_overlap_but_are_consumed_in_order_once(plan_adapter, monkeypatch):
    selected(plan_adapter)
    barrier = Barrier(2)
    reads = []
    def read(request):
        reads.append(request)
        barrier.wait(timeout=5)  # Serial IO would fail, independent of machine speed.
        return request.node_id, object()
    monkeypatch.setattr(acquisition, "_read", read)
    with plan_adapter.plan_object_acquisition(("pond", "bridge")):
        wave = plan_adapter._plan_object_acquisition
        assert plan_adapter.authorize({}) is False
        pond = acquisition.object_request(plan_adapter, "pond")
        bridge = acquisition.object_request(plan_adapter, "bridge")
        with pytest.raises(ValueError, match="differs"):
            wave.consume(pond.model_copy(update={"revision_pin": "foreign"}))
        assert wave.consume(pond)[0] == "pond"
        with pytest.raises(ValueError, match="differs"):
            wave.consume(pond)
        assert wave.consume(bridge)[0] == "bridge"
        assert not wave.futures
    assert plan_adapter._plan_object_acquisition is None
    assert {r.node_id for r in reads} == {"pond", "bridge"}
    assert all(r.revision_pin == plan_adapter.bootstrap.world_scope.revision_id for r in reads)


@pytest.mark.parametrize("nodes", [("pond", "foreign"), ("pond", "pond"), ("pond",)])
def test_wave_refuses_changed_selection_before_io(plan_adapter, monkeypatch, nodes):
    selected(plan_adapter)
    monkeypatch.setattr(acquisition, "_read", lambda *_: pytest.fail("Unselected native IO"))
    with pytest.raises(ValueError, match="selected targets"):
        with plan_adapter.plan_object_acquisition(nodes):
            pytest.fail("Invalid wave entered")


def test_wave_joins_other_reads_and_clears_on_failure_without_retry(plan_adapter, monkeypatch):
    selected(plan_adapter)
    barrier = Barrier(2)
    completed = Event()
    calls = []
    def read(request):
        calls.append(request.node_id)
        barrier.wait(timeout=5)
        if request.node_id == "pond":
            raise RuntimeError("Native read failed")
        completed.set()
        return object(), object()
    monkeypatch.setattr(acquisition, "_read", read)
    with pytest.raises(RuntimeError, match="Native read failed"):
        with plan_adapter.plan_object_acquisition(("pond", "bridge")):
            plan_adapter._plan_object_acquisition.consume(acquisition.object_request(plan_adapter, "pond"))
    assert completed.is_set() and sorted(calls) == ["bridge", "pond"]
    assert plan_adapter._plan_object_acquisition is None


def test_wave_rejects_nested_lifetime(plan_adapter, monkeypatch):
    selected(plan_adapter, ("pond",))
    calls = []
    monkeypatch.setattr(acquisition, "_read", lambda request: calls.append(request.node_id))
    with plan_adapter.plan_object_acquisition(("pond",)):
        with pytest.raises(ValueError, match="current decision"):
            with plan_adapter.plan_object_acquisition(("pond",)):
                pytest.fail("Nested wave entered")
    assert calls == ["pond"] and plan_adapter._plan_object_acquisition is None


def test_wave_requires_acknowledged_decision_before_native_io(plan_adapter, monkeypatch):
    monkeypatch.setattr(acquisition, "_read", lambda *_: pytest.fail("Native IO before decision"))
    with pytest.raises(ValueError, match="current decision"):
        with plan_adapter.plan_object_acquisition(("pond",)):
            pytest.fail("Unacknowledged wave entered")
