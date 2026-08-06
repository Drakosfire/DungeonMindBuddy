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
from graph_memory.kernel.world_revision_ready import (
    WorldRevisionReadyNotification,
    clear_revision_ready_offer_observations,
    get_revision_ready_mailbox,
    get_revision_ready_offer_observations,
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
def _isolated_revision_ready_state() -> None:
    reset_revision_ready_mailbox()
    clear_revision_ready_offer_observations()
    kernel.clear_world_read_runtime()
    stop_world_graph_prewarm_coordinator()
    yield
    stop_world_graph_prewarm_coordinator()
    reset_revision_ready_mailbox()
    clear_revision_ready_offer_observations()
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
) -> WorldRevisionReadyNotification:
    return WorldRevisionReadyNotification(
        resolved_root=str(root.resolve()),
        world_id=world_id,
        revision_id=revision_id,
        parent_revision_id=parent_revision_id,
        operation_ids=operation_ids,
        created_at=created_at,
    )


def test_successful_publish_offers_exact_mapped_notification(tmp_path: Path) -> None:
    published = _publish(tmp_path, ["op:rev-ready-success"])

    expected = notification_from_publish_result(tmp_path, WORLD_ID, published)
    observations = get_revision_ready_offer_observations()
    assert len(observations) == 1
    row = observations[0]
    assert row["status"] == "accepted"
    assert row["resolved_root"] == expected.resolved_root
    assert row["world_id"] == expected.world_id
    assert row["revision_id"] == expected.revision_id
    assert row["parent_revision_id"] == expected.parent_revision_id
    assert row["operation_ids"] == list(expected.operation_ids)
    assert row["created_at"] == expected.created_at

    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head.head_revision_id == expected.revision_id


def test_second_offer_same_world_coalesces_before_consumer_drain(
    tmp_path: Path,
) -> None:
    first = _notification(tmp_path, revision_id="rev:first")
    second = _notification(tmp_path, revision_id="rev:second", parent_revision_id="rev:first")

    first_result = offer_revision_ready(first)
    second_result = offer_revision_ready(second)

    assert first_result.status == "accepted"
    assert second_result.status == "coalesced"
    assert second_result.replaced is not None
    assert second_result.replaced.revision_id == "rev:first"

    observations = get_revision_ready_offer_observations()
    assert [row["status"] for row in observations] == ["accepted", "coalesced"]
    assert observations[1]["replaced_revision_id"] == "rev:first"
    assert get_revision_ready_mailbox().pending_count() == 1


def test_mailbox_full_drops_distinct_world_keys_without_raising(
    tmp_path: Path,
) -> None:
    mailbox = get_revision_ready_mailbox()
    mailbox._capacity = 2

    first = offer_revision_ready(_notification(tmp_path, world_id="world-a", revision_id="rev:a"))
    second = offer_revision_ready(_notification(tmp_path, world_id="world-b", revision_id="rev:b"))
    third = offer_revision_ready(_notification(tmp_path, world_id="world-c", revision_id="rev:c"))

    assert first.status == "accepted"
    assert second.status == "accepted"
    assert third.status == "dropped"
    assert mailbox.pending_count() == 2


def test_failed_publish_emits_no_offer_observations(tmp_path: Path) -> None:
    published = _publish(tmp_path, ["op:rev-ready-success"])
    clear_revision_ready_offer_observations()

    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    with pytest.raises(kernel.WorldGraphStaleParentError):
        kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store,
            operation_ids=["op:rev-ready-stale-parent"],
            expected_parent_revision_id="rev:definitely-not-current",
        )

    assert get_revision_ready_offer_observations() == []
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    assert head.head_revision_id == published.revision.revision_id


def test_offer_internal_failure_returns_dropped_without_raising(
    tmp_path: Path,
) -> None:
    notification = _notification(tmp_path, revision_id="rev:offer-failure")
    mailbox = get_revision_ready_mailbox()

    with patch.object(mailbox, "offer", side_effect=RuntimeError("injected offer failure")):
        result = offer_revision_ready(notification)

    assert result.status == "dropped"
    assert result.notification.revision_id == "rev:offer-failure"
    assert get_revision_ready_mailbox().pending_count() == 0


def test_publish_completes_durable_work_before_blocked_offer_returns(
    tmp_path: Path,
) -> None:
    offer_entered = threading.Event()
    release_offer = threading.Event()
    mailbox = get_revision_ready_mailbox()
    original_offer = mailbox.offer

    def _blocking_offer(notification: WorldRevisionReadyNotification):
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
    assert get_revision_ready_offer_observations()[-1]["status"] == "accepted"
