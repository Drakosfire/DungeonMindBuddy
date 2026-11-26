"""Partial, turn-scoped diagnostics for selected Core source-view entries.

An entry is an attempted call, not evidence that a source was returned. This
never establishes complete coverage or stores arguments, identities or bodies.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from unittest.mock import patch
import sys

_scope = ContextVar("negative_retrieval_source_window", default=None)
_serial = Lock()
_poisoned = False
_KINDS = ("metadata", "text", "text_batch")


class SourceWindowCleanupError(RuntimeError):
    """The diagnostic could not prove its process-wide hooks were removed."""


def validate_artifact(value, case_id):
    """Validate a partial diagnostic without converting attempts into grades."""
    expected = {"schema", "case_id", "window", "dispatch_uncertain", "coverage", "status",
                "scoped", "unscoped", "pending_at_close", "late", "monitor_error"}
    if (not isinstance(value, dict) or set(value) != expected
            or value["schema"] != "dmb_negative_retrieval_source_window_v1"
            or value["case_id"] != case_id or value["window"] != "turn_post_v1"
            or value["coverage"] != "partial"
            or value["status"] not in {"observed", "uncertain", "not_started", "unavailable", "setup_failed"}
            or type(value["dispatch_uncertain"]) is not bool or type(value["monitor_error"]) is not bool
            or any(type(value[key]) is not int or value[key] < 0 for key in ("pending_at_close", "late"))):
        raise ValueError("Invalid source window artifact")
    for group in ("scoped", "unscoped"):
        row = value[group]
        if (not isinstance(row, dict) or set(row) != set(_KINDS)
                or any(type(n) is not int or n < 0 for n in row.values())):
            raise ValueError("Invalid source window counts")
    troubled = (value["pending_at_close"] or value["late"] or value["monitor_error"]
                 or any(value["unscoped"].values()))
    if value["status"] == "observed" and troubled:
        raise ValueError("Observed source window has unresolved work")
    if value["status"] in {"not_started", "unavailable", "setup_failed"} and (
            any(value["scoped"].values()) or any(value["unscoped"].values())
            or value["pending_at_close"] or value["late"]):
        raise ValueError("Unstarted source window has activity")
    if value["status"] == "setup_failed" and not value["monitor_error"]:
        raise ValueError("Source window setup failure is missing its error flag")
    return value


def _default_owners():
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView
    from dungeonmind.infrastructure.postgres.vnext_operator_sources import _PostgresOperatorSourceView
    from apps.live_control_server.services.build_jev_harness import _BUILD_GRAPH_PREPARATION
    owners = {
        _PostgresNativeTextSourceView.get_native_metadata_snapshot.__code__: "metadata",
        _PostgresNativeTextSourceView.get_native_text_source.__code__: "text",
        _PostgresNativeTextSourceView.get_native_text_sources.__code__: "text_batch",
        _PostgresOperatorSourceView.get_native_metadata_snapshot.__code__: "metadata",
        _PostgresOperatorSourceView.get_native_text_source.__code__: "text",
    }
    return owners, _BUILD_GRAPH_PREPARATION


@contextmanager
def observe_source_window(*, owners=None, executor=None):
    """Record scoped entries during one synchronous test-client turn.

    A unique token follows TestClient/asyncio context. For the one known Build
    executor, only this token is set in its existing worker; product context is
    not copied. Unscoped calls or outstanding submitted work make the window
    uncertain. Other threads, subprocesses, owners and late work remain outside
    the coverage claim, so the artifact is always partial.
    """
    global _poisoned
    if not _serial.acquire(blocking=False):
        raise RuntimeError("Source observation requires a serial process")
    if _poisoned:
        _serial.release()
        raise SourceWindowCleanupError("Source observation requires a fresh process after cleanup failure")
    state = {"coverage": "partial", "status": "not_started",
             "scoped": {key: 0 for key in _KINDS},
             "unscoped": {key: 0 for key in _KINDS}, "pending": 0,
             "pending_at_close": 0, "late": 0, "monitor_error": False}
    guard = Lock()
    token = object()
    claimed = None
    armed = []
    old_submit = None
    reset = None
    active = True
    try:
        if owners is None:
            try:
                owners, executor = _default_owners()
            except (ImportError, AttributeError):
                state["status"] = "unavailable"
                yield state
                return
        if not isinstance(owners, dict) or not owners or any(v not in _KINDS for v in owners.values()):
            raise ValueError("Invalid monitored owner map")
        if executor is None:
            raise ValueError("A known executor is required")
        monitoring = getattr(sys, "monitoring", None)
        if monitoring is None:
            state["status"] = "unavailable"
            yield state
            return
        slot = next((i for i in range(6) if monitoring.get_tool(i) is None), None)
        if slot is None:
            state["status"] = "unavailable"
            yield state
            return
        monitoring.use_tool_id(slot, "buddy-negative-source-window")
        claimed = slot
        event = monitoring.events.PY_START

        def on_start(code, offset):
            try:
                kind = owners[code]
                group = "scoped" if _scope.get() is token else "unscoped"
                with guard:
                    if active:
                        state[group][kind] += 1
                    else:
                        state["late"] += 1
            except BaseException:
                # A diagnostic must never interrupt the source owner.
                state["monitor_error"] = True

        monitoring.register_callback(slot, event, on_start)
        for code in owners:
            armed.append(code)
            monitoring.set_local_events(slot, code, event)

        old_submit = executor.submit

        def submit(function, *args, **kwargs):
            if _scope.get() is not token:
                return old_submit(function, *args, **kwargs)
            with guard:
                state["pending"] += 1

            def tagged(*inner_args, **inner_kwargs):
                marker = _scope.set(token)
                try:
                    return function(*inner_args, **inner_kwargs)
                finally:
                    _scope.reset(marker)
                    with guard:
                        state["pending"] -= 1

            try:
                future = old_submit(tagged, *args, **kwargs)
            except BaseException:
                with guard:
                    state["pending"] -= 1
                raise

            # A future cancelled before execution never enters tagged(), so it
            # remains conservatively outstanding. Do not attach callbacks to a
            # foreign Future and risk changing the caller's result path.
            return future

        with patch.object(executor, "submit", submit):
            reset = _scope.set(token)
            state["status"] = "observed"
            try:
                yield state
            finally:
                with guard:
                    active = False
                    state["pending_at_close"] = state["pending"]
                _scope.reset(reset)
                reset = None
    finally:
        primary_error = sys.exc_info()[1]
        failures = []
        try:
            if claimed is not None:
                for code in armed:
                    try:
                        monitoring.set_local_events(claimed, code, 0)
                    except BaseException as error:
                        failures.append(error)
                try:
                    monitoring.register_callback(claimed, event, None)
                except BaseException as error:
                    failures.append(error)
                try:
                    monitoring.free_tool_id(claimed)
                except BaseException as error:
                    failures.append(error)
        finally:
            with guard:
                if failures:
                    state["monitor_error"] = True
                    _poisoned = True
                if state["status"] == "observed" and (state["pending_at_close"] or state["late"]
                        or state["monitor_error"] or any(state["unscoped"].values())):
                    state["status"] = "uncertain"
            _serial.release()
        if failures:
            if primary_error is not None:
                primary_error.add_note("Source-window cleanup also failed; capture is uncertain")
            else:
                raise SourceWindowCleanupError("Source-window cleanup failed") from failures[0]
