"""OPT02 revision-ready mailbox and publish-side offer proofs."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.services.world_graph_prewarm import (
    stop_world_graph_prewarm_coordinator,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

WORLD_ID = "eldyrwild"


@pytest.fixture(autouse=True)
def _isolated_revision_ready_state() -> None:
    kernel.reset_revision_ready_mailbox()
    kernel.clear_revision_ready_offer_observations()
    kernel.clear_world_read_runtime()
    stop_world_graph_prewarm_coordinator()
    yield
    stop_world_graph_prewarm_coordinator()
    kernel.reset_revision_ready_mailbox()
    kernel.clear_revision_ready_offer_observations()
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


def _notification(
    root: Path,
    *,
    world_id: str = WORLD_ID,
    revision_id: str,
    parent_revision_id: str | None = None,
    operation_ids: tuple[str, ...] = ("op:test",),
    created_at: str = "2026-01-01T00:00:00Z",
    commit_seq: int = 0,
) -> kernel.WorldRevisionReadyNotification:
    return kernel.WorldRevisionReadyNotification(
        resolved_root=str(root.resolve()),
        world_id=world_id,
        revision_id=revision_id,
        parent_revision_id=parent_revision_id,
        operation_ids=operation_ids,
        created_at=created_at,
        commit_seq=commit_seq,
    )


def test_successful_publish_offers_exact_mapped_notification(tmp_path: Path) -> None:
    published = _publish(tmp_path, ["op:rev-ready-success"])

    observations = kernel.get_revision_ready_offer_observations()
    assert len(observations) == 1
    row = observations[0]
    assert isinstance(row["commit_seq"], int)
    assert int(row["commit_seq"]) >= 1
    expected = kernel.notification_from_publish_result(
        tmp_path,
        WORLD_ID,
        published,
        commit_seq=int(row["commit_seq"]),
    )
    assert row["status"] == "accepted"
    assert row["resolved_root"] == expected.resolved_root
    assert row["world_id"] == expected.world_id
    assert row["revision_id"] == expected.revision_id
    assert row["parent_revision_id"] == expected.parent_revision_id
    assert row["operation_ids"] == list(expected.operation_ids)
    assert row["created_at"] == expected.created_at
    assert row["commit_seq"] == expected.commit_seq

    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head.head_revision_id == expected.revision_id


def test_second_offer_same_world_coalesces_before_consumer_drain(
    tmp_path: Path,
) -> None:
    first = _notification(
        tmp_path,
        revision_id="rev:first",
        created_at="2026-01-01T00:00:00Z",
        commit_seq=1,
    )
    second = _notification(
        tmp_path,
        revision_id="rev:second",
        parent_revision_id="rev:first",
        created_at="2026-01-02T00:00:00Z",
        commit_seq=2,
    )

    first_result = kernel.offer_revision_ready(first)
    second_result = kernel.offer_revision_ready(second)

    assert first_result.status == "accepted"
    assert second_result.status == "coalesced"
    assert second_result.replaced is not None
    assert second_result.replaced.revision_id == "rev:first"

    observations = kernel.get_revision_ready_offer_observations()
    assert [row["status"] for row in observations] == ["accepted", "coalesced"]
    assert observations[1]["replaced_revision_id"] == "rev:first"
    mailbox = kernel.get_revision_ready_mailbox()
    assert mailbox.pending_count() == 1
    assert mailbox.enqueued_timing_count() == 1


def test_late_older_offer_does_not_displace_newer_pending_revision(
    tmp_path: Path,
) -> None:
    newer = _notification(
        tmp_path,
        revision_id="rev:b",
        created_at="2026-01-02T00:00:00Z",
        commit_seq=2,
    )
    older = _notification(
        tmp_path,
        revision_id="rev:a",
        created_at="2026-01-01T00:00:00Z",
        commit_seq=1,
    )

    assert kernel.offer_revision_ready(newer).status == "accepted"
    late = kernel.offer_revision_ready(older)
    assert late.status == "dropped"

    mailbox = kernel.get_revision_ready_mailbox()
    lease = mailbox.acquire_consumer()
    assert lease is not None
    pending = mailbox.wait_for_notification(lease, timeout=0.1)
    lease.release()
    assert pending is not None
    assert pending.revision_id == "rev:b"
    assert mailbox.enqueued_timing_count() <= 1


def test_equal_created_at_lower_commit_seq_does_not_win_via_revision_id_lexicographic_order(
    tmp_path: Path,
) -> None:
    """Storage drops microseconds; SHA revision ids must not decide commit order."""
    same_ts = "2026-01-01T00:00:00Z"
    # Pending B sorts first lexicographically; late stale A sorts later.
    newer_b = _notification(
        tmp_path,
        revision_id="rev:aaa",
        created_at=same_ts,
        commit_seq=2,
    )
    stale_a = _notification(
        tmp_path,
        revision_id="rev:zzz",
        created_at=same_ts,
        commit_seq=1,
    )
    assert stale_a.revision_id > newer_b.revision_id
    assert stale_a.created_at == newer_b.created_at
    assert stale_a.commit_seq < newer_b.commit_seq

    assert kernel.offer_revision_ready(newer_b).status == "accepted"
    late = kernel.offer_revision_ready(stale_a)
    assert late.status == "dropped"

    mailbox = kernel.get_revision_ready_mailbox()
    lease = mailbox.acquire_consumer()
    assert lease is not None
    pending = mailbox.wait_for_notification(lease, timeout=0.1)
    lease.release()
    assert pending is not None
    assert pending.revision_id == "rev:aaa"
    assert pending.commit_seq == 2


def test_mailbox_full_drops_distinct_world_keys_without_raising(
    tmp_path: Path,
) -> None:
    mailbox = kernel.get_revision_ready_mailbox()
    mailbox._capacity = 2

    first = kernel.offer_revision_ready(
        _notification(tmp_path, world_id="world-a", revision_id="rev:a")
    )
    second = kernel.offer_revision_ready(
        _notification(tmp_path, world_id="world-b", revision_id="rev:b")
    )
    third = kernel.offer_revision_ready(
        _notification(tmp_path, world_id="world-c", revision_id="rev:c")
    )

    assert first.status == "accepted"
    assert second.status == "accepted"
    assert third.status == "dropped"
    assert mailbox.pending_count() == 2
    assert mailbox.enqueued_timing_count() == 2


def test_failed_and_noop_publishes_emit_no_offer_observations(tmp_path: Path) -> None:
    published = _publish(tmp_path, ["op:rev-ready-success"])
    kernel.clear_revision_ready_offer_observations()
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)

    with pytest.raises(kernel.WorldGraphStaleParentError):
        kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store,
            operation_ids=["op:rev-ready-stale-parent"],
            expected_parent_revision_id="rev:definitely-not-current",
        )
    assert kernel.get_revision_ready_offer_observations() == []

    with pytest.raises(kernel.WorldGraphValidationError):
        kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store.model_copy(update={"schema": ""}),
            operation_ids=["op:rev-ready-invalid"],
            expected_parent_revision_id=published.revision.revision_id,
        )
    assert kernel.get_revision_ready_offer_observations() == []

    # Force revision-exists by pre-creating the content-addressed revision dir.
    from graph_memory.union_supergraph.load import dump_union_supergraph_store
    from graph_memory.world_supergraph.storage import (
        canonicalize_graph_payload,
        compute_revision_id,
    )

    payload = dump_union_supergraph_store(store)
    canonical = canonicalize_graph_payload(payload)
    collision_ops = ["op:rev-ready-exists"]
    collision_id = compute_revision_id(
        world_id=WORLD_ID,
        parent_revision_id=published.revision.revision_id,
        operation_ids=collision_ops,
        canonical_graph_json=canonical,
    )
    (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / collision_id
    ).mkdir(parents=True, exist_ok=False)
    with pytest.raises(kernel.WorldGraphRevisionExistsError):
        kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store,
            operation_ids=collision_ops,
            expected_parent_revision_id=published.revision.revision_id,
        )
    assert kernel.get_revision_ready_offer_observations() == []

    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head.head_revision_id == published.revision.revision_id


def test_offer_bookkeeping_failure_does_not_raise_or_break_publish(
    tmp_path: Path,
) -> None:
    notification = _notification(tmp_path, revision_id="rev:offer-failure")
    mailbox = kernel.get_revision_ready_mailbox()

    with patch.object(mailbox, "offer", side_effect=RuntimeError("injected offer failure")):
        result = kernel.offer_revision_ready(notification)
    assert result.status == "dropped"

    # Observation/logging failures after a successful mailbox insert must not raise.
    with patch(
        "graph_memory.kernel.world_revision_ready._record_offer_observation",
        side_effect=RuntimeError("injected observation failure"),
    ):
        result = kernel.offer_revision_ready(
            _notification(tmp_path, revision_id="rev:obs-failure")
        )
    assert result.status == "accepted"

    # Facade final containment: post-publish bookkeeping exception must not
    # escape publish_world_graph_revision.
    with patch(
        "graph_memory.kernel.world_revision_ready.offer_revision_ready_from_publish",
        side_effect=RuntimeError("injected facade failure"),
    ):
        published = _publish(tmp_path, ["op:rev-ready-facade-containment"])
    assert published.revision.revision_id
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head.head_revision_id == published.revision.revision_id


def test_publish_completes_durable_work_before_blocked_offer_returns(
    tmp_path: Path,
) -> None:
    offer_entered = threading.Event()
    release_offer = threading.Event()
    mailbox = kernel.get_revision_ready_mailbox()
    original_offer = mailbox.offer

    def _blocking_offer(notification: kernel.WorldRevisionReadyNotification):
        offer_entered.set()
        assert release_offer.wait(timeout=5.0)
        return original_offer(notification)

    publish_error: list[BaseException] = []
    published_result: list[kernel.WorldGraphPublishResult] = []

    def _publish_in_thread() -> None:
        try:
            published_result.append(_publish(tmp_path, ["op:rev-ready-nonblocking"]))
        except BaseException as exc:
            publish_error.append(exc)

    with patch.object(mailbox, "offer", side_effect=_blocking_offer):
        thread = threading.Thread(target=_publish_in_thread)
        thread.start()
        assert offer_entered.wait(timeout=5.0)

        head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
        assert head.head_revision_id is not None
        assert thread.is_alive()

        release_offer.set()
        thread.join(timeout=5.0)

    assert not publish_error
    assert published_result
    assert not thread.is_alive()
    assert kernel.get_revision_ready_offer_observations()[-1]["status"] == "accepted"
