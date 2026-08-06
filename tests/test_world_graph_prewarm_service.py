"""OPT02 live-server post-commit world graph prewarm coordinator proofs."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.services.world_graph_prewarm import (
    clear_prewarm_observations,
    get_prewarm_observations,
    start_world_graph_prewarm_coordinator,
    stop_world_graph_prewarm_coordinator,
)
from graph_memory.kernel.world_revision_ready import (
    clear_revision_ready_offer_observations,
    notification_from_publish_result,
    offer_revision_ready,
    reset_revision_ready_mailbox,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

WORLD_ID = "eldyrwild"


@pytest.fixture(autouse=True)
def _isolated_prewarm_state() -> None:
    reset_revision_ready_mailbox()
    clear_revision_ready_offer_observations()
    clear_prewarm_observations()
    kernel.clear_world_read_runtime()
    stop_world_graph_prewarm_coordinator()
    yield
    stop_world_graph_prewarm_coordinator()
    reset_revision_ready_mailbox()
    clear_revision_ready_offer_observations()
    clear_prewarm_observations()
    kernel.clear_world_read_runtime()


def _publish(
    root: Path,
    operation_ids: list[str],
    *,
    expected_parent_revision_id: str | None = None,
) -> kernel.WorldGraphPublishResult:
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    return kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=operation_ids,
        expected_parent_revision_id=expected_parent_revision_id,
    )


def _revision_graph_path(root: Path, revision_id: str) -> Path:
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "graph.json"
    )


def _wait_for_prewarm_observations(
    coordinator,
    *,
    revision_id: str | None = None,
    expected_count: int | None = None,
    timeout_s: float = 30.0,
) -> list:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        observations = get_prewarm_observations()
        if revision_id is not None:
            observations = [
                observation
                for observation in observations
                if observation.revision_id == revision_id
            ]
        if expected_count is None and observations:
            assert coordinator.wait_idle(timeout_s=timeout_s)
            return get_prewarm_observations()
        if expected_count is not None and len(observations) >= expected_count:
            assert coordinator.wait_idle(timeout_s=timeout_s)
            if revision_id is None:
                return get_prewarm_observations()
            return [
                observation
                for observation in get_prewarm_observations()
                if observation.revision_id == revision_id
            ]
        time.sleep(0.01)
    pytest.fail("timed out waiting for prewarm observations")


def test_publish_with_coordinator_prewarms_resident_and_second_load_is_hit(
    tmp_path: Path,
) -> None:
    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None

    published = _publish(tmp_path, ["op:prewarm-success"])
    revision_id = published.revision.revision_id
    observations = _wait_for_prewarm_observations(
        coordinator,
        revision_id=revision_id,
        expected_count=1,
    )

    runtime = kernel.get_world_read_runtime()
    prewarmed = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    assert prewarmed.key.revision_id == revision_id

    kernel.begin_request_io()
    warm = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    counters = kernel.get_request_io()
    assert counters is not None
    assert warm.generation == prewarmed.generation
    assert counters.graph_payload_reads == 0
    assert counters.revision_manifest_reads == 0
    assert counters.contribution_reads == 0
    assert counters.source_index_reads == 0

    observations = get_prewarm_observations()
    matching = [obs for obs in observations if obs.revision_id == revision_id]
    assert len(matching) == 1
    assert matching[0].status == "resident_miss"


def test_reader_and_prewarm_worker_share_one_cold_load(
    tmp_path: Path,
) -> None:
    published = _publish(tmp_path, ["op:prewarm-coalesce"])
    revision_id = published.revision.revision_id
    runtime = kernel.get_world_read_runtime()

    release_load = threading.Event()
    load_started = threading.Event()
    cold_load_count = {"n": 0}
    original_cold_load = runtime._cold_load

    def _gated_cold_load(*args, **kwargs):
        cold_load_count["n"] += 1
        load_started.set()
        assert release_load.wait(timeout=30.0)
        return original_cold_load(*args, **kwargs)

    reader_errors: list[BaseException] = []

    def _reader() -> None:
        try:
            runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
        except BaseException as exc:
            reader_errors.append(exc)

    with patch.object(runtime, "_cold_load", side_effect=_gated_cold_load):
        coordinator = start_world_graph_prewarm_coordinator()
        assert coordinator is not None
        reader = threading.Thread(target=_reader)
        reader.start()
        assert load_started.wait(timeout=30.0)
        release_load.set()
        _wait_for_prewarm_observations(coordinator, revision_id=revision_id)
        reader.join(timeout=30.0)

    assert not reader_errors
    assert cold_load_count["n"] == 1


def test_duplicate_exact_notification_reports_resident_hit_with_zero_reads(
    tmp_path: Path,
) -> None:
    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None

    published = _publish(tmp_path, ["op:prewarm-duplicate"])
    _wait_for_prewarm_observations(
        coordinator,
        revision_id=published.revision.revision_id,
        expected_count=1,
    )
    clear_prewarm_observations()

    notification = notification_from_publish_result(tmp_path, WORLD_ID, published)
    offer_revision_ready(notification)
    observations = _wait_for_prewarm_observations(
        coordinator,
        revision_id=published.revision.revision_id,
        expected_count=1,
    )
    assert len(observations) == 1
    assert observations[0].status == "resident_hit"
    assert observations[0].graph_payload_reads == 0
    assert observations[0].revision_manifest_reads == 0
    assert observations[0].contribution_reads == 0
    assert observations[0].source_index_reads == 0


def test_mailbox_latest_by_world_prewarms_only_head_revision_b(
    tmp_path: Path,
) -> None:
    pub_a = _publish(tmp_path, ["op:prewarm-a"])
    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    pub_b = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:prewarm-b"],
        expected_parent_revision_id=pub_a.revision.revision_id,
    )

    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    observations = _wait_for_prewarm_observations(
        coordinator,
        revision_id=pub_b.revision.revision_id,
        expected_count=1,
    )
    by_revision = {obs.revision_id: obs for obs in observations}
    assert pub_b.revision.revision_id in by_revision
    assert by_revision[pub_b.revision.revision_id].status == "resident_miss"

    if pub_a.revision.revision_id in by_revision:
        assert by_revision[pub_a.revision.revision_id].status == "superseded"

    runtime = kernel.get_world_read_runtime()
    resident_b = runtime.get_or_load_resident(
        tmp_path,
        WORLD_ID,
        pub_b.revision.revision_id,
    )
    assert resident_b.key.revision_id == pub_b.revision.revision_id


def test_prewarm_failure_leaves_head_unchanged_and_no_resident(
    tmp_path: Path,
) -> None:
    published = _publish(tmp_path, ["op:prewarm-failure"])
    revision_id = published.revision.revision_id
    head_before = kernel.open_world_graph_head(tmp_path, WORLD_ID)

    graph_path = _revision_graph_path(tmp_path, revision_id)
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    observations = _wait_for_prewarm_observations(
        coordinator,
        revision_id=revision_id,
        expected_count=1,
    )
    assert len(observations) == 1
    assert observations[0].status == "failed"
    head_after = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head_after.head_revision_id == head_before.head_revision_id
    assert kernel.get_world_read_runtime().resident_count() == 0


def test_clear_during_blocked_prewarm_does_not_pin_stale_generation(
    tmp_path: Path,
) -> None:
    published = _publish(tmp_path, ["op:prewarm-clear"])
    revision_id = published.revision.revision_id
    runtime = kernel.get_world_read_runtime()

    load_started = threading.Event()
    release_load = threading.Event()
    original_cold_load = runtime._cold_load

    def _gated_cold_load(*args, **kwargs):
        load_started.set()
        assert release_load.wait(timeout=30.0)
        return original_cold_load(*args, **kwargs)

    with patch.object(runtime, "_cold_load", side_effect=_gated_cold_load):
        coordinator = start_world_graph_prewarm_coordinator()
        assert coordinator is not None
        assert load_started.wait(timeout=30.0)
        kernel.clear_world_read_runtime()
        release_load.set()
        _wait_for_prewarm_observations(
            coordinator,
            revision_id=revision_id,
        )

    first = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    second = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    assert second.generation == first.generation
