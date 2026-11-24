"""Observe selected native Graph owner calls, never a complete journal.

This process-local diagnostic records attempts and outcomes, not arguments,
identities, query text or source bodies. Other Graph, corpus, lookup and
previously captured call aliases may bypass these wrappers.
"""
from contextlib import ExitStack, contextmanager
from functools import wraps
from threading import Lock
from unittest.mock import patch

_lock = Lock()
_OWNERS = {
    "prepare_query": "native_graph_query",
    "read_selected": "native_graph_selected_read",
    "read_authored_reference": "native_graph_authored_reference_read",
    "reopen_context": "native_graph_context_reopen",
}


def summarize_records(records):
    """Count observed attempts without turning absent calls into a coverage claim."""
    if not isinstance(records, list) or any(
        not isinstance(row, dict) or set(row) != {"owner", "state"}
        or not isinstance(row["owner"], str) or not isinstance(row["state"], str)
        or row["owner"] not in _OWNERS.values()
        or row["state"] not in {"entered", "returned", "raised"}
        for row in records
    ):
        raise ValueError("Malformed native Graph probe evidence")
    return {owner: {state: sum(row["owner"] == owner and row["state"] == state for row in records)
                    for state in ("entered", "returned", "raised")}
            for owner in _OWNERS.values()}


@contextmanager
def observe_native_graph_owners():
    """Observe direct calls to these owner functions within one serial process."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("Native Graph observation requires a serial process")
    records = []
    record_lock = Lock()
    try:
        from apps.live_control_server.services import native_graph_reads

        def watch(owner, function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                row = {"owner": owner, "state": "entered"}
                with record_lock:
                    records.append(row)
                try:
                    result = function(*args, **kwargs)
                except BaseException:
                    with record_lock:
                        row["state"] = "raised"
                    raise
                with record_lock:
                    row["state"] = "returned"
                return result
            return wrapped

        with ExitStack() as stack:
            for name, owner in _OWNERS.items():
                stack.enter_context(patch.object(native_graph_reads, name, watch(owner, getattr(native_graph_reads, name))))
            yield records
    finally:
        _lock.release()
