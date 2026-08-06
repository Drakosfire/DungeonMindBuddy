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
    get_world_graph_prewarm_coordinator,
    start_world_graph_prewarm_coordinator,
    stop_world_graph_prewarm_coordinator,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

WORLD_ID = "eldyrwild"


def _drain_coordinator(*, timeout_s: float = 10.0) -> None:
    """Stop coordinator and wait out any orphaned worker from a prior timeout."""
    stop_world_graph_prewarm_coordinator(timeout_s=timeout_s)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        coordinator = get_world_graph_prewarm_coordinator()
        if coordinator is None:
            return
        if not coordinator.is_orphaned and not coordinator.is_running:
            stop_world_graph_prewarm_coordinator(timeout_s=timeout_s)
            return
        time.sleep(0.01)


@pytest.fixture(autouse=True)
def _isolated_prewarm_state() -> None:
    _drain_coordinator()
    kernel.reset_revision_ready_mailbox()
    kernel.clear_revision_ready_offer_observations()
    clear_prewarm_observations()
    kernel.clear_world_read_runtime()
    yield
    _drain_coordinator()
    kernel.reset_revision_ready_mailbox()
    kernel.clear_revision_ready_offer_observations()
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
    _wait_for_prewarm_observations(
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

    matching = [
        obs for obs in get_prewarm_observations() if obs.revision_id == revision_id
    ]
    assert len(matching) == 1
    assert matching[0].status == "resident_miss"


def test_publish_returns_while_worker_cold_load_remains_blocked(
    tmp_path: Path,
) -> None:
    runtime = kernel.get_world_read_runtime()
    load_started = threading.Event()
    release_load = threading.Event()
    original_cold = runtime._cold_load

    def _gated_cold_load(*args, **kwargs):
        load_started.set()
        assert release_load.wait(timeout=30.0)
        return original_cold(*args, **kwargs)

    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    with patch.object(runtime, "_cold_load", side_effect=_gated_cold_load):
        published = _publish(tmp_path, ["op:prewarm-publish-before-load"])
        assert published.revision.revision_id
        head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
        assert head.head_revision_id == published.revision.revision_id
        assert load_started.wait(timeout=30.0)
        release_load.set()
        _wait_for_prewarm_observations(
            coordinator,
            revision_id=published.revision.revision_id,
            expected_count=1,
        )


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

    notification = kernel.notification_from_publish_result(
        tmp_path,
        WORLD_ID,
        published,
        commit_seq=kernel.allocate_revision_ready_commit_seq(),
    )
    kernel.offer_revision_ready(notification)
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


def test_late_offer_of_stale_a_after_b_keeps_b_for_prewarm(
    tmp_path: Path,
) -> None:
    """Publish A stalls before offer; B commits/offers first; late A must not win."""
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    a_offer_gate = threading.Event()
    a_entered = threading.Event()
    mailbox = kernel.get_revision_ready_mailbox()
    original_offer = mailbox.offer
    offer_count = {"n": 0}

    def _gated_offer(notification):
        offer_count["n"] += 1
        if offer_count["n"] == 1:
            a_entered.set()
            assert a_offer_gate.wait(timeout=30.0)
        return original_offer(notification)

    publish_a_result: list[kernel.WorldGraphPublishResult] = []

    def _publish_a() -> None:
        publish_a_result.append(
            kernel.publish_world_revision(
                tmp_path,
                WORLD_ID,
                store,
                operation_ids=["op:prewarm-late-a"],
            )
        )

    with patch.object(mailbox, "offer", side_effect=_gated_offer):
        thread_a = threading.Thread(target=_publish_a)
        thread_a.start()
        assert a_entered.wait(timeout=30.0)

        # A has committed (head advanced) but not offered yet.
        head_after_a = kernel.open_world_graph_head(tmp_path, WORLD_ID)
        assert head_after_a.head_revision_id is not None
        pub_b = kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store,
            operation_ids=["op:prewarm-late-b"],
            expected_parent_revision_id=head_after_a.head_revision_id,
        )
        a_offer_gate.set()
        thread_a.join(timeout=30.0)

    assert publish_a_result
    pub_a = publish_a_result[0]
    offer_rows = kernel.get_revision_ready_offer_observations()
    seq_by_revision = {
        str(row["revision_id"]): int(row["commit_seq"]) for row in offer_rows
    }
    assert seq_by_revision[pub_a.revision.revision_id] < seq_by_revision[
        pub_b.revision.revision_id
    ]
    # Same-second publish is common because storage strips microseconds.
    assert pub_a.revision.created_at == pub_b.revision.created_at or (
        pub_a.revision.created_at <= pub_b.revision.created_at
    )

    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    _wait_for_prewarm_observations(
        coordinator,
        revision_id=pub_b.revision.revision_id,
        expected_count=1,
    )
    by_revision = {obs.revision_id: obs for obs in get_prewarm_observations()}
    assert pub_b.revision.revision_id in by_revision
    assert by_revision[pub_b.revision.revision_id].status in {
        "resident_miss",
        "resident_hit",
        "coalesced",
    }
    # Stale A must not be the only/final head-following warm authority.
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head.head_revision_id == pub_b.revision.revision_id
    resident_b = kernel.get_world_read_runtime().get_or_load_resident(
        tmp_path,
        WORLD_ID,
        pub_b.revision.revision_id,
    )
    assert resident_b.key.revision_id == pub_b.revision.revision_id


def test_inflight_a_then_b_keeps_b_as_head_following_authority(
    tmp_path: Path,
) -> None:
    runtime = kernel.get_world_read_runtime()
    load_started = threading.Event()
    release_load = threading.Event()
    original_cold = runtime._cold_load
    cold_targets: list[str] = []

    def _gated_cold_load(*args, **kwargs):
        revision_id = args[2] if len(args) >= 3 else kwargs.get("revision_id")
        cold_targets.append(str(revision_id))
        if len(cold_targets) == 1:
            load_started.set()
            assert release_load.wait(timeout=30.0)
        return original_cold(*args, **kwargs)

    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    with patch.object(runtime, "_cold_load", side_effect=_gated_cold_load):
        pub_a = _publish(tmp_path, ["op:prewarm-inflight-a"])
        assert load_started.wait(timeout=30.0)
        _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
        pub_b = kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store,
            operation_ids=["op:prewarm-inflight-b"],
            expected_parent_revision_id=pub_a.revision.revision_id,
        )
        release_load.set()
        _wait_for_prewarm_observations(
            coordinator,
            revision_id=pub_b.revision.revision_id,
            expected_count=1,
        )

    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head.head_revision_id == pub_b.revision.revision_id
    resident_b = runtime.get_or_load_resident(
        tmp_path,
        WORLD_ID,
        pub_b.revision.revision_id,
    )
    assert resident_b.key.revision_id == pub_b.revision.revision_id


def test_head_world_id_mismatch_reports_failed_not_superseded(
    tmp_path: Path,
) -> None:
    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    published = _publish(tmp_path, ["op:prewarm-world-mismatch"])
    _wait_for_prewarm_observations(
        coordinator,
        revision_id=published.revision.revision_id,
        expected_count=1,
    )
    clear_prewarm_observations()

    notification = kernel.notification_from_publish_result(
        tmp_path,
        WORLD_ID,
        published,
        commit_seq=kernel.allocate_revision_ready_commit_seq(),
    )
    mismatched = kernel.WorldGraphHead(
        world_id="other-world",
        head_revision_id=notification.revision_id,
        updated_at=published.head.updated_at,
    )
    with patch(
        "apps.live_control_server.services.world_graph_prewarm.kernel.open_world_graph_head",
        return_value=mismatched,
    ):
        kernel.offer_revision_ready(notification)
        observations = _wait_for_prewarm_observations(
            coordinator,
            revision_id=notification.revision_id,
            expected_count=1,
        )
    assert observations[0].status == "failed"
    assert observations[0].error_type == "WorldIdMismatch"


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


def test_shutdown_timeout_orphans_worker_and_blocks_second_lifecycle(
    tmp_path: Path,
) -> None:
    runtime = kernel.get_world_read_runtime()
    load_started = threading.Event()
    release_load = threading.Event()
    original_cold = runtime._cold_load

    def _gated_cold_load(*args, **kwargs):
        load_started.set()
        assert release_load.wait(timeout=30.0)
        return original_cold(*args, **kwargs)

    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    with patch.object(runtime, "_cold_load", side_effect=_gated_cold_load):
        published = _publish(tmp_path, ["op:prewarm-orphan"])
        assert load_started.wait(timeout=30.0)
        stopped = stop_world_graph_prewarm_coordinator(timeout_s=0.05)
        assert stopped is False
        orphan = get_world_graph_prewarm_coordinator()
        assert orphan is not None
        assert orphan.is_orphaned
        assert orphan.is_running
        assert start_world_graph_prewarm_coordinator(wait_s=0) is None

        before = list(get_prewarm_observations())
        start_after_orphan: list = []

        def _start_waiting() -> None:
            start_after_orphan.append(
                start_world_graph_prewarm_coordinator(wait_s=10.0)
            )

        waiter = threading.Thread(target=_start_waiting)
        waiter.start()
        time.sleep(0.05)
        assert start_after_orphan == []
        release_load.set()
        waiter.join(timeout=10.0)
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            current = get_world_graph_prewarm_coordinator()
            if current is not None and current.is_running and not current.is_orphaned:
                break
            time.sleep(0.01)
        else:
            pytest.fail("waiting start did not obtain a healthy coordinator")
        assert start_after_orphan and start_after_orphan[0] is not None
        assert start_after_orphan[0].is_running
        assert not start_after_orphan[0].is_orphaned
        # Orphan must not emit under the invalidated generation.
        after = [
            obs
            for obs in get_prewarm_observations()
            if obs.revision_id == published.revision.revision_id
            and obs not in before
        ]
        assert after == []

    assert stop_world_graph_prewarm_coordinator(timeout_s=5.0) is True


def test_start_during_stop_waits_and_returns_fresh_coordinator(tmp_path: Path) -> None:
    runtime = kernel.get_world_read_runtime()
    load_started = threading.Event()
    release_load = threading.Event()
    original_cold = runtime._cold_load

    def _gated_cold_load(*args, **kwargs):
        load_started.set()
        assert release_load.wait(timeout=30.0)
        return original_cold(*args, **kwargs)

    coordinator = start_world_graph_prewarm_coordinator()
    assert coordinator is not None
    with patch.object(runtime, "_cold_load", side_effect=_gated_cold_load):
        _publish(tmp_path, ["op:prewarm-stop-race"])
        assert load_started.wait(timeout=30.0)

        stop_result: list[bool] = []

        def _stop() -> None:
            stop_result.append(stop_world_graph_prewarm_coordinator(timeout_s=5.0))

        stopper = threading.Thread(target=_stop)
        stopper.start()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            current = get_world_graph_prewarm_coordinator()
            if current is not None and current.is_stopping:
                break
            time.sleep(0.01)
        else:
            release_load.set()
            stopper.join(timeout=5.0)
            pytest.fail("stop did not mark coordinator stopping")

        started: list = []

        def _start() -> None:
            started.append(start_world_graph_prewarm_coordinator(wait_s=10.0))

        starter = threading.Thread(target=_start)
        starter.start()
        time.sleep(0.05)
        assert started == []
        release_load.set()
        stopper.join(timeout=10.0)
        starter.join(timeout=10.0)

    assert stop_result == [True]
    assert started and started[0] is not None
    assert started[0].is_running
    assert not started[0].is_stopping
    assert started[0] is not coordinator
    assert stop_world_graph_prewarm_coordinator(timeout_s=5.0) is True
