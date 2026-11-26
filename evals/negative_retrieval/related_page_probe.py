"""Opt-in process-local probe for two actual related-page acquisition owners.

Use only inside an isolated, serial evaluator process. This does not cover Graph,
corpus or every other source owner and is not a complete acquisition journal.
"""
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from unittest.mock import patch
from uuid import UUID

_lock = Lock()


@contextmanager
def observe_related_page_owners():
    """Record entry and completion without changing arguments or return values."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("Related-page observation requires a serial process")
    records = []
    record_lock = Lock()
    try:
        from apps.live_control_server.services import build_related_pages

        def watch(name, function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                row = {"owner": name, "state": "entered"}
                if name == "related_page_materialization" and args:
                    pointer = args[0]
                    identity = pointer.get("document_id") if isinstance(pointer, dict) else getattr(pointer, "document_id", None)
                    if isinstance(identity, (str, UUID)) and str(identity):
                        row["document_id"] = str(identity)
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

        with patch.object(build_related_pages, "discover", watch("related_catalog_discovery", build_related_pages.discover)), \
             patch.object(build_related_pages, "materialize", watch("related_page_materialization", build_related_pages.materialize)):
            yield records
    finally:
        _lock.release()


def acquisition_labels(records, *, label_by_document=None, completed_only=False):
    """Project observed page-materialization attempts as unmapped reads.

    Document identity is host-side evidence, never model input. Materialization may be witnessed again
    in the trace; the case-level violation remains the same. With completed_only,
    only returned calls are included. No absence claim
    follows from this partial probe.
    """
    from .trace_observation import UNKNOWN
    if not isinstance(records, list) or any(
        not isinstance(row, dict)
        or row.get("owner") not in {"related_catalog_discovery", "related_page_materialization"}
        or row.get("state") not in {"entered", "returned", "raised"}
        for row in records
    ):
        raise ValueError("Malformed related-page probe evidence")
    labels = label_by_document or {}
    return [labels.get(row.get("document_id"), UNKNOWN) for row in records
            if row["owner"] == "related_page_materialization"
            and (not completed_only or row["state"] == "returned")]


def catalog_discovery_count(records):
    """Count observed catalog attempts, including empty and failed attempts."""
    acquisition_labels(records)  # Validate the complete record shape first.
    return sum(row["owner"] == "related_catalog_discovery" for row in records)
