"""Observe selected native Graph and authored-source calls, not a complete journal.

This process-local diagnostic records attempts and outcomes, not arguments,
identities, query text or source bodies. Other Graph, corpus, lookup and
previously captured call aliases may bypass these wrappers.
"""
from contextlib import ExitStack, contextmanager
from functools import wraps
import sys
from threading import Lock
from unittest.mock import patch

_lock = Lock()
_OWNERS = {
    "prepare_query": "native_graph_query",
    "pending_build_query": "native_graph_binding",
    "read_selected": "native_graph_selected_read",
    "read_authored_reference": "native_graph_authored_reference_read",
    "reopen_context": "native_graph_context_reopen",
}
_GRAPH_BODY_OWNERS = {"open_admitted_native_text": "native_graph_body_open",
                      "open_admitted_native_text_batch": "native_graph_body_open_batch"}
_PREPARATION_OWNERS = {"prepare": "native_source_preparation"}
_APP_SOURCE_OWNERS = {"get_source_markdown": "app_source_body_read",
                      "get_source_markdown_batch": "app_source_body_read_batch",
                      "get_source_markdown_by_revision_id": "app_source_body_read_revision"}
_CORPUS_OWNERS = {
    "read_authored_source": "native_corpus_authored_source_read",
    "capture_native_sources": "native_corpus_discovery",
    "open_admitted_native_text": "native_corpus_body_open",
    "read_native_corpus_member": "native_corpus_member_read",
    "read_direct_native_source": "native_corpus_direct_read",
}


def summarize_records(records):
    """Count observed attempts without turning absent calls into a coverage claim."""
    if not isinstance(records, list) or any(
        not isinstance(row, dict) or set(row) != {"owner", "state"}
        or not isinstance(row["owner"], str) or not isinstance(row["state"], str)
        or row["owner"] not in (*_OWNERS.values(), *_PREPARATION_OWNERS.values(), *_CORPUS_OWNERS.values(), *_APP_SOURCE_OWNERS.values(), *_GRAPH_BODY_OWNERS.values())
        or row["state"] not in {"entered", "returned", "raised"}
        for row in records
    ):
        raise ValueError("Malformed native Graph probe evidence")
    counts = {owner: {state: sum(row["owner"] == owner and row["state"] == state for row in records)
                      for state in ("entered", "returned", "raised")}
              for owner in (*_OWNERS.values(), *_PREPARATION_OWNERS.values(), *_CORPUS_OWNERS.values(), *_APP_SOURCE_OWNERS.values(), *_GRAPH_BODY_OWNERS.values())}
    # Old v1 artifacts predate these hooks. Without an observed call, their
    # records cannot distinguish an inactive owner from absent instrumentation.
    for owner in ("native_source_preparation", "native_graph_binding", "app_source_body_read",
                  "native_graph_body_open", "native_graph_body_open_batch", "app_source_body_read_batch",
                  "app_source_body_read_revision"):
        if not any(counts[owner].values()):
            counts[owner] = None
    return counts


@contextmanager
def observe_native_graph_owners():
    """Observe direct calls to these owner functions within one serial process."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("Native Graph observation requires a serial process")
    records = []
    record_lock = Lock()
    try:
        from apps.live_control_server.services import native_graph_reads, plan_source_turn
        from apps.live_control_server.integrations.dungeonmind import native_corpus_source
        from application_state.source import repository as app_sources

        def watch(owner, function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                # The Core batch owner does no source lookup for an empty
                # list/tuple. Preserve its behavior without inventing a read.
                if owner == "native_graph_body_open_batch":
                    ids = args[1] if len(args) > 1 else kwargs.get("evidence_ref_ids")
                    if isinstance(ids, (list, tuple)) and not ids:
                        return function(*args, **kwargs)
                if owner == "app_source_body_read_batch":
                    bindings = kwargs.get("bindings")
                    if isinstance(bindings, (list, tuple)) and not bindings:
                        return function(*args, **kwargs)
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
            authored = sys.modules.get("apps.live_control_server.services.native_authored_references")
            authored_reader = getattr(authored, "read_authored_reference", None)
            original_reader = native_graph_reads.read_authored_reference
            authored_source = getattr(authored, "read_authored_source", None)
            original_source = native_corpus_source.read_authored_source
            for name, owner in _OWNERS.items():
                stack.enter_context(patch.object(native_graph_reads, name, watch(owner, getattr(native_graph_reads, name))))
            for name, owner in _GRAPH_BODY_OWNERS.items():
                stack.enter_context(patch.object(native_graph_reads, name, watch(owner, getattr(native_graph_reads, name))))
            for name, owner in _PREPARATION_OWNERS.items():
                stack.enter_context(patch.object(plan_source_turn, name, watch(owner, getattr(plan_source_turn, name))))
            for name, owner in _APP_SOURCE_OWNERS.items():
                stack.enter_context(patch.object(app_sources, name, watch(owner, getattr(app_sources, name))))
            # This module imports the reader at module load; preserve its alias
            # when already loaded and avoid replacing a separately patched owner.
            if authored is not None and authored_reader is original_reader:
                stack.enter_context(patch.object(authored, "read_authored_reference", native_graph_reads.read_authored_reference))
            for name, owner in _CORPUS_OWNERS.items():
                stack.enter_context(patch.object(native_corpus_source, name, watch(owner, getattr(native_corpus_source, name))))
            if authored is not None and authored_source is original_source:
                stack.enter_context(patch.object(authored, "read_authored_source", native_corpus_source.read_authored_source))
            yield records
    finally:
        _lock.release()
