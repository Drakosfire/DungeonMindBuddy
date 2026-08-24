"""Live-server post-commit World Graph resident prewarm coordinator (OPT02)."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import graph_memory.kernel as kernel
from apps.live_control_server.services.world_graph_projection_recipes import (
    warm_projection_recipes_for_ready_revision,
)

logger = logging.getLogger(__name__)

PrewarmStatus = Literal[
    "resident_hit",
    "resident_miss",
    "coalesced",
    "superseded",
    "failed",
    "dropped",
]


def _dungeonmind_authority_active() -> bool:
    """R.3: in ``dungeonmind`` mode reads execute natively in DungeonMind.

    The Buddy resident runtime and projection cache have no consumer on the
    read path, so post-commit prewarming is pure waste. The coordinator
    lifecycle stays intact (start/stop succeed) but no worker runs.
    """
    from apps.live_control_server import config
    from graph_memory.world_supergraph import storage

    return (
        config.world_graph_authority_mode()
        == storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )

_DEFAULT_SHUTDOWN_TIMEOUT_S = 5.0
_POLL_TIMEOUT_S = 0.25


@dataclass(frozen=True)
class PrewarmObservation:
    event: str
    resolved_root: str
    world_id: str
    revision_id: str
    parent_revision_id: str | None
    operation_ids: tuple[str, ...]
    status: PrewarmStatus
    queue_wait_ms: float
    prewarm_ms: float
    graph_payload_reads: int
    revision_manifest_reads: int
    contribution_reads: int
    source_index_reads: int
    head_json_reads: int
    resident_generation: int | None = None
    error_type: str | None = None
    error_message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "resolved_root": self.resolved_root,
            "world_id": self.world_id,
            "revision_id": self.revision_id,
            "parent_revision_id": self.parent_revision_id,
            "operation_ids": list(self.operation_ids),
            "status": self.status,
            "queue_wait_ms": self.queue_wait_ms,
            "prewarm_ms": self.prewarm_ms,
            "graph_payload_reads": self.graph_payload_reads,
            "revision_manifest_reads": self.revision_manifest_reads,
            "contribution_reads": self.contribution_reads,
            "source_index_reads": self.source_index_reads,
            "head_json_reads": self.head_json_reads,
            "resident_generation": self.resident_generation,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


_OBSERVATIONS: list[PrewarmObservation] = []
_OBS_LOCK = threading.Lock()
_COORDINATOR: "WorldGraphPrewarmCoordinator | None" = None
_COORDINATOR_COND = threading.Condition()
# Overlapping app lifecycles share one worker; only the last release stops it.
_LIFECYCLE_REFCOUNT = 0


def get_prewarm_observations() -> list[PrewarmObservation]:
    with _OBS_LOCK:
        return list(_OBSERVATIONS)


def clear_prewarm_observations() -> None:
    with _OBS_LOCK:
        _OBSERVATIONS.clear()


def _emit_observation(observation: PrewarmObservation) -> None:
    with _OBS_LOCK:
        _OBSERVATIONS.append(observation)
        if len(_OBSERVATIONS) > 256:
            del _OBSERVATIONS[:-128]
    logger.info("world_graph_post_commit_prewarm", extra=observation.as_dict())


class WorldGraphPrewarmCoordinator:
    """One bounded worker that admits exact notified revisions via OPT01."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self._lease: kernel.RevisionReadyConsumerLease | None = None
        self._active = False
        self._busy = 0
        self._run_generation = 0
        self._orphaned = False
        self._stopping = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread is not None and thread.is_alive())

    @property
    def is_orphaned(self) -> bool:
        with self._lock:
            return self._orphaned

    @property
    def is_stopping(self) -> bool:
        with self._lock:
            return self._stopping

    def start(self) -> bool:
        with self._lock:
            if self._stopping or self._orphaned:
                logger.error(
                    "world graph prewarm coordinator start refused: "
                    "stopping=%s orphaned=%s",
                    self._stopping,
                    self._orphaned,
                )
                return False
            if self._active and self.is_running:
                return True
            if _dungeonmind_authority_active():
                # R.3: no worker — the direct DungeonMind read path never
                # touches the Buddy resident runtime or projection cache.
                # Lifecycle remains a no-op success so app startup is
                # authority-mode agnostic.
                logger.info(
                    "world graph prewarm coordinator disabled: "
                    "dungeonmind authority mode serves reads natively"
                )
                return True
            mailbox = kernel.get_revision_ready_mailbox()
            lease = mailbox.acquire_consumer()
            if lease is None:
                logger.error("world graph prewarm coordinator consumer lease unavailable")
                return False
            self._lease = lease
            self._stop.clear()
            self._busy = 0
            self._orphaned = False
            self._stopping = False
            self._run_generation += 1
            run_generation = self._run_generation
            self._idle.set()
            self._active = True
            self._thread = threading.Thread(
                target=self._run,
                kwargs={"run_generation": run_generation},
                name="world-graph-prewarm",
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self, *, timeout_s: float = _DEFAULT_SHUTDOWN_TIMEOUT_S) -> bool:
        with self._lock:
            if not self._active and self._thread is None and not self._orphaned:
                self._stopping = False
                return True
            # Mark stopping before any wait so concurrent start() cannot treat
            # this instance as a healthy running coordinator.
            self._stopping = True
            # Invalidate the current worker before closing intake so an orphan
            # cannot admit residents or emit under a later lifecycle.
            self._run_generation += 1
            self._stop.set()
            mailbox = kernel.get_revision_ready_mailbox()
            discarded = mailbox.close()
            lease = self._lease
            thread = self._thread
            stop_generation = self._run_generation
        for notification in discarded:
            _emit_observation(
                PrewarmObservation(
                    event="world_graph_post_commit_prewarm",
                    resolved_root=notification.resolved_root,
                    world_id=notification.world_id,
                    revision_id=notification.revision_id,
                    parent_revision_id=notification.parent_revision_id,
                    operation_ids=notification.operation_ids,
                    status="dropped",
                    queue_wait_ms=0.0,
                    prewarm_ms=0.0,
                    graph_payload_reads=0,
                    revision_manifest_reads=0,
                    contribution_reads=0,
                    source_index_reads=0,
                    head_json_reads=0,
                )
            )
        if thread is not None:
            thread.join(timeout=timeout_s)
        with self._lock:
            alive = thread is not None and thread.is_alive()
            if alive:
                # Keep lease + coordinator identity so a new lifecycle cannot
                # race an orphan worker that still holds the old run.
                self._orphaned = True
                self._active = False
                self._stopping = False
                self._idle.set()
                return False
            if lease is not None:
                lease.release()
            self._lease = None
            self._thread = None
            self._active = False
            self._orphaned = False
            self._stopping = False
            self._idle.set()
            # Re-open mailbox only after the worker has fully stopped.
            if stop_generation == self._run_generation:
                mailbox = kernel.get_revision_ready_mailbox()
                mailbox.reset()
            return True

    def wait_idle(self, *, timeout_s: float = 30.0) -> bool:
        return self._idle.wait(timeout=timeout_s)

    def _still_current(self, run_generation: int) -> bool:
        with self._lock:
            return run_generation == self._run_generation and not self._stop.is_set()

    def _recipe_still_current(
        self,
        run_generation: int,
        notification: kernel.WorldRevisionReadyNotification,
    ) -> bool:
        if not self._still_current(run_generation):
            return False
        try:
            head = kernel.open_world_graph_head(
                Path(notification.resolved_root),
                notification.world_id,
            )
        except Exception:
            return False
        return head.head_revision_id == notification.revision_id

    def _cleanup_orphan_after_exit(self) -> None:
        """Release lease/mailbox when a timed-out worker finally terminates."""
        global _COORDINATOR, _LIFECYCLE_REFCOUNT
        with self._lock:
            if not self._orphaned:
                return
            if self._thread is not threading.current_thread():
                return
            lease = self._lease
            self._lease = None
            self._thread = None
            self._orphaned = False
            self._active = False
            self._stopping = False
        if lease is not None:
            lease.release()
        kernel.get_revision_ready_mailbox().reset()
        with _COORDINATOR_COND:
            if _COORDINATOR is self:
                _COORDINATOR = None
                _LIFECYCLE_REFCOUNT = 0
            _COORDINATOR_COND.notify_all()

    def _run(self, *, run_generation: int) -> None:
        lease = self._lease
        if lease is None:
            return
        mailbox = kernel.get_revision_ready_mailbox()
        try:
            while self._still_current(run_generation):
                try:
                    notification = mailbox.wait_for_notification(
                        lease,
                        timeout=_POLL_TIMEOUT_S,
                    )
                except RuntimeError:
                    break
                if not self._still_current(run_generation):
                    break
                if notification is None:
                    continue
                with self._lock:
                    if run_generation != self._run_generation:
                        break
                    self._busy += 1
                    self._idle.clear()
                try:
                    self._handle(notification, run_generation=run_generation)
                finally:
                    with self._lock:
                        self._busy = max(0, self._busy - 1)
                        if (
                            run_generation == self._run_generation
                            and self._busy == 0
                            and mailbox.pending_count() == 0
                            and not self._stop.is_set()
                        ):
                            self._idle.set()
        finally:
            self._idle.set()
            self._cleanup_orphan_after_exit()

    def _handle(
        self,
        notification: kernel.WorldRevisionReadyNotification,
        *,
        run_generation: int,
    ) -> None:
        if not self._still_current(run_generation):
            return
        queue_wait_ms = kernel.pop_revision_ready_queue_wait_ms(notification)
        started = time.perf_counter()
        counters = kernel.begin_request_io()
        status: PrewarmStatus = "failed"
        generation: int | None = None
        error_type: str | None = None
        error_message: str | None = None
        try:
            if not self._still_current(run_generation):
                return
            try:
                head = kernel.open_world_graph_head(
                    Path(notification.resolved_root),
                    notification.world_id,
                )
            except Exception as exc:
                status = "failed"
                error_type = type(exc).__name__
                error_message = str(exc)
                counters.head_json_reads += 1
                return
            counters.head_json_reads += 1
            if head.world_id != notification.world_id:
                status = "failed"
                error_type = "WorldIdMismatch"
                error_message = (
                    f"head world_id={head.world_id!r} "
                    f"notification world_id={notification.world_id!r}"
                )
                return
            if head.head_revision_id != notification.revision_id:
                status = "superseded"
                return
            if not self._still_current(run_generation):
                return
            try:
                resident = kernel.get_world_read_runtime().get_or_load_resident(
                    Path(notification.resolved_root),
                    notification.world_id,
                    notification.revision_id,
                )
            except Exception as exc:
                status = "failed"
                error_type = type(exc).__name__
                error_message = str(exc)
                return
            if not self._still_current(run_generation):
                return
            generation = resident.generation
            outcome = counters.last_resident_status
            if outcome == "hit":
                status = "resident_hit"
            elif outcome == "coalesced":
                status = "coalesced"
            else:
                status = "resident_miss"
        finally:
            if not self._still_current(run_generation):
                kernel.reset_request_io()
                return
            prewarm_ms = (time.perf_counter() - started) * 1000.0
            _emit_observation(
                PrewarmObservation(
                    event="world_graph_post_commit_prewarm",
                    resolved_root=notification.resolved_root,
                    world_id=notification.world_id,
                    revision_id=notification.revision_id,
                    parent_revision_id=notification.parent_revision_id,
                    operation_ids=notification.operation_ids,
                    status=status,
                    queue_wait_ms=queue_wait_ms,
                    prewarm_ms=prewarm_ms,
                    graph_payload_reads=counters.graph_payload_reads,
                    revision_manifest_reads=counters.revision_manifest_reads,
                    contribution_reads=counters.contribution_reads,
                    source_index_reads=counters.source_index_reads,
                    head_json_reads=counters.head_json_reads,
                    resident_generation=generation,
                    error_type=error_type,
                    error_message=error_message,
                )
            )
            # Drop request-IO before recipe replay so nested project_world_graph
            # begin/reset cannot clear this prewarm request's ContextVar early.
            kernel.reset_request_io()
            if status in {"resident_hit", "resident_miss", "coalesced"}:
                try:
                    warm_projection_recipes_for_ready_revision(
                        root=Path(notification.resolved_root),
                        world_id=notification.world_id,
                        revision_id=notification.revision_id,
                        still_current=lambda: self._recipe_still_current(
                            run_generation,
                            notification,
                        ),
                    )
                except Exception:
                    logger.exception("projection recipe warm failed")


def start_world_graph_prewarm_coordinator(
    *,
    wait_s: float = 30.0,
) -> WorldGraphPrewarmCoordinator | None:
    """Acquire one lifecycle ownership of the process-local coordinator.

    Concurrent callers never receive a coordinator that is mid-stop. A second
    active lifecycle increments the refcount and shares the same worker.
    ``wait_s=0`` refuses immediately while a prior lifecycle is stopping or
    orphaned.
    """
    global _COORDINATOR, _LIFECYCLE_REFCOUNT
    deadline = time.monotonic() + max(0.0, wait_s)
    with _COORDINATOR_COND:
        while True:
            coordinator = _COORDINATOR
            if coordinator is not None and (
                coordinator.is_stopping or coordinator.is_orphaned
            ):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.error(
                        "world graph prewarm coordinator start refused while "
                        "prior lifecycle stopping=%s orphaned=%s",
                        coordinator.is_stopping,
                        coordinator.is_orphaned,
                    )
                    return None
                _COORDINATOR_COND.wait(timeout=remaining)
                continue
            if coordinator is not None and coordinator.is_running:
                _LIFECYCLE_REFCOUNT += 1
                return coordinator
            if coordinator is not None and not coordinator.is_running:
                _COORDINATOR = None
                _LIFECYCLE_REFCOUNT = 0
            created = WorldGraphPrewarmCoordinator()
            if not created.start():
                return None
            _COORDINATOR = created
            _LIFECYCLE_REFCOUNT = 1
            _COORDINATOR_COND.notify_all()
            return created


def stop_world_graph_prewarm_coordinator(
    *,
    timeout_s: float = _DEFAULT_SHUTDOWN_TIMEOUT_S,
) -> bool:
    """Release one lifecycle ownership; stop the worker only at refcount zero."""
    global _COORDINATOR, _LIFECYCLE_REFCOUNT
    with _COORDINATOR_COND:
        coordinator = _COORDINATOR
        if coordinator is None:
            _LIFECYCLE_REFCOUNT = 0
            return True
        if _LIFECYCLE_REFCOUNT > 1:
            _LIFECYCLE_REFCOUNT -= 1
            _COORDINATOR_COND.notify_all()
            return True
        # Last owner (or refcount already zero during cleanup): real stop.
        _LIFECYCLE_REFCOUNT = 0
        # Flip stopping under the global condition before join so concurrent
        # start() waits instead of returning this shutting-down instance.
        with coordinator._lock:
            coordinator._stopping = True
        _COORDINATOR_COND.notify_all()
    stopped = coordinator.stop(timeout_s=timeout_s)
    with _COORDINATOR_COND:
        if stopped:
            if _COORDINATOR is coordinator:
                _COORDINATOR = None
            _LIFECYCLE_REFCOUNT = 0
        # Orphaned coordinator remains registered until self-cleanup.
        _COORDINATOR_COND.notify_all()
    return stopped


def get_world_graph_prewarm_coordinator() -> WorldGraphPrewarmCoordinator | None:
    with _COORDINATOR_COND:
        return _COORDINATOR


def get_world_graph_prewarm_lifecycle_refcount() -> int:
    """Test helper: active overlapping lifecycle owners."""
    with _COORDINATOR_COND:
        return _LIFECYCLE_REFCOUNT
