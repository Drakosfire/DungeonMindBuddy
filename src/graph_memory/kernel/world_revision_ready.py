"""Process-local revision-ready notifications after successful Kernel publish (OPT02).

Offers are bounded, non-blocking, and never durable authority. The live-server
prewarm coordinator is the sole consumer lease holder.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from graph_memory.world_supergraph.model import WorldGraphPublishResult

logger = logging.getLogger(__name__)

_DEFAULT_MAILBOX_CAPACITY = 64
_MIN_MAILBOX_CAPACITY = 1

OfferStatus = Literal["accepted", "coalesced", "dropped"]
WorldKey = tuple[str, str]
ExactRevisionKey = tuple[str, str, str]


@dataclass(frozen=True)
class WorldRevisionReadyNotification:
    """Exact committed revision signal for process-local prewarm."""

    resolved_root: str
    world_id: str
    revision_id: str
    parent_revision_id: str | None
    operation_ids: tuple[str, ...]
    created_at: str


@dataclass(frozen=True)
class RevisionReadyOfferResult:
    status: OfferStatus
    notification: WorldRevisionReadyNotification
    replaced: WorldRevisionReadyNotification | None = None


@dataclass
class RevisionReadyConsumerLease:
    """Exclusive consumer lease for one live-server coordinator."""

    _mailbox: "RevisionReadyMailbox"
    _token: object
    released: bool = False

    def release(self) -> None:
        if self.released:
            return
        self._mailbox.release_consumer(self._token)
        self.released = True


class RevisionReadyMailbox:
    """Latest-by-world bounded mailbox with one exclusive consumer lease."""

    def __init__(self, *, capacity: int | None = None) -> None:
        self._capacity = capacity if capacity is not None else _default_mailbox_capacity()
        self._capacity = max(_MIN_MAILBOX_CAPACITY, int(self._capacity))
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._pending: OrderedDict[WorldKey, WorldRevisionReadyNotification] = OrderedDict()
        self._closed = False
        self._consumer_token: object | None = None
        self._generation = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def close(self) -> list[WorldRevisionReadyNotification]:
        """Stop intake and return discarded pending notifications."""
        with self._condition:
            self._closed = True
            discarded = list(self._pending.values())
            self._pending.clear()
            self._condition.notify_all()
            return discarded

    def reset(self) -> None:
        """Test/lifecycle helper: clear pending, reopen, release consumer."""
        with self._condition:
            self._pending.clear()
            self._closed = False
            self._consumer_token = None
            self._generation += 1
            self._condition.notify_all()

    def offer(
        self,
        notification: WorldRevisionReadyNotification,
    ) -> RevisionReadyOfferResult:
        with self._condition:
            if self._closed:
                return RevisionReadyOfferResult(
                    status="dropped",
                    notification=notification,
                )
            key = (notification.resolved_root, notification.world_id)
            replaced = self._pending.get(key)
            if replaced is not None:
                self._pending[key] = notification
                self._pending.move_to_end(key)
                self._condition.notify()
                return RevisionReadyOfferResult(
                    status="coalesced",
                    notification=notification,
                    replaced=replaced,
                )
            if len(self._pending) >= self._capacity:
                return RevisionReadyOfferResult(
                    status="dropped",
                    notification=notification,
                )
            self._pending[key] = notification
            self._condition.notify()
            return RevisionReadyOfferResult(
                status="accepted",
                notification=notification,
            )

    def acquire_consumer(self) -> RevisionReadyConsumerLease | None:
        with self._lock:
            if self._consumer_token is not None:
                return None
            token = object()
            self._consumer_token = token
            return RevisionReadyConsumerLease(_mailbox=self, _token=token)

    def release_consumer(self, token: object) -> None:
        with self._lock:
            if self._consumer_token is token:
                self._consumer_token = None

    def wait_for_notification(
        self,
        lease: RevisionReadyConsumerLease,
        *,
        timeout: float | None = None,
    ) -> WorldRevisionReadyNotification | None:
        with self._condition:
            if lease.released or lease._token is not self._consumer_token:
                raise RuntimeError("invalid or released revision-ready consumer lease")
            if not self._pending and not self._closed:
                self._condition.wait(timeout=timeout)
            if lease.released or lease._token is not self._consumer_token:
                return None
            if not self._pending:
                return None
            _key, notification = self._pending.popitem(last=False)
            return notification


_MAILBOX: RevisionReadyMailbox | None = None
_MAILBOX_LOCK = threading.Lock()
_OFFER_OBSERVATIONS: list[dict[str, object]] = []
_OFFER_OBS_LOCK = threading.Lock()
_ENQUEUED_AT: dict[ExactRevisionKey, float] = {}
_ENQUEUED_LOCK = threading.Lock()


def _default_mailbox_capacity() -> int:
    raw = os.environ.get(
        "DMB_WORLD_GRAPH_REVISION_READY_MAILBOX_CAPACITY",
        str(_DEFAULT_MAILBOX_CAPACITY),
    )
    try:
        parsed = int(raw)
    except ValueError:
        parsed = _DEFAULT_MAILBOX_CAPACITY
    return max(_MIN_MAILBOX_CAPACITY, parsed)


def get_revision_ready_mailbox() -> RevisionReadyMailbox:
    global _MAILBOX
    with _MAILBOX_LOCK:
        if _MAILBOX is None:
            _MAILBOX = RevisionReadyMailbox()
        return _MAILBOX


def reset_revision_ready_mailbox() -> None:
    """Clear process mailbox state for tests / deterministic restarts."""
    mailbox = get_revision_ready_mailbox()
    mailbox.reset()
    with _OFFER_OBS_LOCK:
        _OFFER_OBSERVATIONS.clear()
    with _ENQUEUED_LOCK:
        _ENQUEUED_AT.clear()


def mark_revision_ready_enqueued(notification: WorldRevisionReadyNotification) -> None:
    key = (
        notification.resolved_root,
        notification.world_id,
        notification.revision_id,
    )
    with _ENQUEUED_LOCK:
        _ENQUEUED_AT[key] = time.perf_counter()


def pop_revision_ready_queue_wait_ms(
    notification: WorldRevisionReadyNotification,
) -> float:
    key = (
        notification.resolved_root,
        notification.world_id,
        notification.revision_id,
    )
    with _ENQUEUED_LOCK:
        started = _ENQUEUED_AT.pop(key, None)
    if started is None:
        return 0.0
    return max(0.0, (time.perf_counter() - started) * 1000.0)


def get_revision_ready_offer_observations() -> list[dict[str, object]]:
    with _OFFER_OBS_LOCK:
        return list(_OFFER_OBSERVATIONS)


def clear_revision_ready_offer_observations() -> None:
    with _OFFER_OBS_LOCK:
        _OFFER_OBSERVATIONS.clear()


def _record_offer_observation(result: RevisionReadyOfferResult) -> None:
    row = {
        "event": "world_graph_revision_ready_offer",
        "status": result.status,
        "resolved_root": result.notification.resolved_root,
        "world_id": result.notification.world_id,
        "revision_id": result.notification.revision_id,
        "parent_revision_id": result.notification.parent_revision_id,
        "operation_ids": list(result.notification.operation_ids),
        "created_at": result.notification.created_at,
        "replaced_revision_id": (
            result.replaced.revision_id if result.replaced is not None else None
        ),
    }
    with _OFFER_OBS_LOCK:
        _OFFER_OBSERVATIONS.append(row)
        if len(_OFFER_OBSERVATIONS) > 256:
            del _OFFER_OBSERVATIONS[:-128]
    logger.info("world_graph_revision_ready_offer", extra=row)


def notification_from_publish_result(
    root: Path,
    world_id: str,
    result: WorldGraphPublishResult,
) -> WorldRevisionReadyNotification:
    if result.head.world_id != world_id:
        raise ValueError(
            "publish result head.world_id does not match publish world_id: "
            f"head={result.head.world_id!r} world_id={world_id!r}"
        )
    if result.revision.world_id != world_id:
        raise ValueError(
            "publish result revision.world_id does not match publish world_id: "
            f"revision={result.revision.world_id!r} world_id={world_id!r}"
        )
    if result.head.head_revision_id != result.revision.revision_id:
        raise ValueError(
            "publish result head does not name the published revision: "
            f"head={result.head.head_revision_id!r} "
            f"revision={result.revision.revision_id!r}"
        )
    return WorldRevisionReadyNotification(
        resolved_root=str(root.resolve()),
        world_id=world_id,
        revision_id=result.revision.revision_id,
        parent_revision_id=result.revision.parent_revision_id,
        operation_ids=tuple(result.revision.operation_ids),
        created_at=result.revision.created_at,
    )


def offer_revision_ready(
    notification: WorldRevisionReadyNotification,
) -> RevisionReadyOfferResult:
    """Non-blocking offer into the process mailbox. Never raises to callers."""
    try:
        result = get_revision_ready_mailbox().offer(notification)
    except Exception as exc:  # pragma: no cover - defensive containment
        logger.exception("revision-ready offer failed: %s", exc)
        result = RevisionReadyOfferResult(status="dropped", notification=notification)
    if result.status in {"accepted", "coalesced"}:
        mark_revision_ready_enqueued(notification)
    _record_offer_observation(result)
    return result


def offer_revision_ready_from_publish(
    root: Path,
    world_id: str,
    result: WorldGraphPublishResult,
) -> RevisionReadyOfferResult | None:
    """Map a successful publish result and offer it. Contain all failures."""
    try:
        notification = notification_from_publish_result(root, world_id, result)
    except Exception as exc:
        logger.exception("revision-ready mapping failed after publish: %s", exc)
        return None
    return offer_revision_ready(notification)


__all__ = [
    "OfferStatus",
    "RevisionReadyConsumerLease",
    "RevisionReadyMailbox",
    "RevisionReadyOfferResult",
    "WorldRevisionReadyNotification",
    "clear_revision_ready_offer_observations",
    "get_revision_ready_mailbox",
    "get_revision_ready_offer_observations",
    "notification_from_publish_result",
    "offer_revision_ready",
    "offer_revision_ready_from_publish",
    "pop_revision_ready_queue_wait_ms",
    "reset_revision_ready_mailbox",
]
