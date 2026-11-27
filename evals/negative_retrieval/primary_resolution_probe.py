"""Observe the Build route's primary-work snapshot reader, not all page reads."""
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from unittest.mock import patch

_lock = Lock()


@contextmanager
def observe_primary_resolution():
    """Observe route-bound reads during one isolated turn without retaining data."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("Primary-work observation requires a serial process")
    state = {"status": "observed", "started": 0, "returned": 0, "raised": 0,
             "pending_at_close": 0}
    guard = Lock()
    active = True
    pending = 0
    try:
        from apps.live_control_server.routes import agent
        original = agent.get_committed_page_snapshot

        @wraps(original)
        def watched(*args, **kwargs):
            nonlocal pending
            with guard:
                tracked = active
                if tracked:
                    pending += 1
                    state["started"] += 1
            try:
                value = original(*args, **kwargs)
            except BaseException:
                with guard:
                    if tracked and active:
                        state["raised"] += 1
                    if tracked:
                        pending -= 1
                raise
            with guard:
                if tracked and active:
                    state["returned"] += 1
                if tracked:
                    pending -= 1
            return value

        with patch.object(agent, "get_committed_page_snapshot", watched):
            yield state
    finally:
        with guard:
            active = False
            state["pending_at_close"] = pending
            if pending:
                state["status"] = "uncertain"
        _lock.release()


def validate_primary_resolution(value, case_id):
    """Validate a partial attempt record; no empty record proves absence."""
    keys = {"schema", "case_id", "window", "coverage", "status", "started", "returned", "raised", "pending_at_close"}
    if (not isinstance(value, dict) or set(value) != keys
            or value["schema"] != "dmb_negative_retrieval_primary_resolution_v1"
            or value["case_id"] != case_id or value["window"] != "turn_post_v1"
            or value["coverage"] != "partial"
            or value["status"] not in {"observed", "uncertain", "not_started", "unavailable"}
            or any(type(value[k]) is not int or value[k] < 0 for k in ("started", "returned", "raised", "pending_at_close"))
            or value["started"] != value["returned"] + value["raised"] + value["pending_at_close"]
            or (value["status"] == "observed" and value["pending_at_close"] != 0)
            or (value["status"] in {"not_started", "unavailable"} and value["started"] != 0)):
        raise ValueError("Invalid primary-work resolution observation")
    return value
