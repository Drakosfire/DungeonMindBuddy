"""OPT02 FastAPI lifespan ownership for the world graph prewarm coordinator."""

from __future__ import annotations

import time

import graph_memory.kernel as kernel
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_graph_prewarm import (
    get_world_graph_prewarm_coordinator,
    start_world_graph_prewarm_coordinator,
    stop_world_graph_prewarm_coordinator,
)


def _reset_process_state() -> None:
    stop_world_graph_prewarm_coordinator(timeout_s=5.0)
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        coordinator = get_world_graph_prewarm_coordinator()
        if coordinator is None:
            break
        time.sleep(0.01)
    kernel.reset_revision_ready_mailbox()
    kernel.clear_revision_ready_offer_observations()
    kernel.clear_world_read_runtime()


def test_lifespan_starts_prewarm_coordinator_on_client_enter() -> None:
    _reset_process_state()
    with TestClient(create_app()) as _client:
        coordinator = get_world_graph_prewarm_coordinator()
        assert coordinator is not None
        assert coordinator.is_running


def test_lifespan_exit_stops_coordinator_and_releases_consumer_lease() -> None:
    _reset_process_state()
    with TestClient(create_app()):
        assert get_world_graph_prewarm_coordinator() is not None

    coordinator = get_world_graph_prewarm_coordinator()
    assert coordinator is None or not coordinator.is_running

    restarted = start_world_graph_prewarm_coordinator()
    assert restarted is not None
    assert restarted.is_running
    stop_world_graph_prewarm_coordinator()


def test_sequential_lifecycles_do_not_leak_revision_ready_consumer() -> None:
    _reset_process_state()

    with TestClient(create_app()):
        pass
    stop_world_graph_prewarm_coordinator()

    with TestClient(create_app()):
        pass
    stop_world_graph_prewarm_coordinator()

    first = kernel.get_revision_ready_mailbox().acquire_consumer()
    assert first is not None
    first.release()

    second = kernel.get_revision_ready_mailbox().acquire_consumer()
    assert second is not None
    second.release()
