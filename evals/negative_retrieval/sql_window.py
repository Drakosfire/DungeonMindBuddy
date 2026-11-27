"""Partial, content-free inventory of psycopg cursor API attempts in a turn.

This cannot establish a complete acquisition journal. It observes selected
Python cursor implementations only, including pre-bound methods, not other
processes, native/custom drivers, uninstrumented methods or remote services.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from threading import Lock
import inspect
import marshal
import os
import sys

from .source_window import _normalize_code, _scope as _turn_scope
from .core_connection_probe import _witness_sql

_lock = Lock()
_poisoned = False
_MAX_CALLERS = 512
_MAX_PENDING = 1024


def runtime_identity():
    """Identify the code-object normalizer without exposing host paths."""
    return {"normalizer": "marshal-code-v1", "implementation": sys.implementation.name,
            "version": list(sys.version_info[:3]), "cache_tag": sys.implementation.cache_tag,
            "optimize": sys.flags.optimize}


class SqlWindowCleanupError(RuntimeError):
    """Monitoring cleanup could not be verified; use a fresh process."""


def _driver_owners():
    import psycopg
    result = {}
    missing = 0
    for name in ("Cursor", "ClientCursor", "ServerCursor", "RawCursor", "AsyncCursor",
                 "AsyncClientCursor", "AsyncServerCursor", "AsyncRawCursor"):
        cls = getattr(psycopg, name, None)
        if cls is None:
            missing += 1
            continue
        for method in ("execute", "executemany", "copy"):
            function = inspect.unwrap(getattr(cls, method, None))
            code = getattr(function, "__code__", None)
            if code is None:
                missing += 1
            elif code in result and result[code] != method:
                raise ValueError("Cursor APIs share an ambiguous code object")
            else:
                result[code] = method
    return result, missing


def _endpoints():
    """Read identities in memory; never return them in an artifact."""
    from psycopg.conninfo import conninfo_to_dict
    result = {}
    for label, name in (("app", "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"),
                        ("core", "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL")):
        raw = os.environ.get(name)
        if not raw:
            continue
        try:
            value = conninfo_to_dict(raw)
            if value.get("hostaddr") or value.get("service"):
                continue
            host, port, database = value.get("host"), value.get("port"), value.get("dbname")
            if host and port and database:
                result[label] = (host, str(port), database)
        except Exception:
            continue
    if len(result) == 2 and result.get("app") == result.get("core"):
        return {}
    return result


def _scope(cursor, endpoints):
    try:
        info = cursor.connection.info
        actual = (info.host, str(info.port), info.dbname)
        labels = [label for label, target in endpoints.items() if target == actual]
        return labels[0] if len(labels) == 1 else "unknown"
    except Exception:
        return "unknown"


def _caller(frame, roots, driver_root, cache):
    """Return only static caller hashes and a line; no locals are read."""
    frame = frame.f_back
    while frame is not None:
        code = frame.f_code
        filename = code.co_filename
        if not isinstance(filename, str) or filename.startswith("<"):
            return None, None, None
        try:
            path = Path(filename).resolve(strict=True)
        except (OSError, ValueError):
            return None, None, None
        if path.is_relative_to(driver_root):
            frame = frame.f_back
            continue
        if path.suffix != ".py" or not any(path.is_relative_to(root) for root in roots):
            return None, None, None
        identity = cache.get(code)
        if identity is None:
            identity = (sha256(path.read_bytes()).hexdigest(),
                        sha256(marshal.dumps(_normalize_code(code))).hexdigest())
            if len(cache) < _MAX_CALLERS:
                cache[code] = identity
        return identity[0], identity[1], frame.f_lineno
    return None, None, None


@contextmanager
def observe_sql_window(*, owners=None, roots=None, endpoints=None, scope_ref=None):
    """Count selected cursor entries, returns and failures without changing calls."""
    global _poisoned
    if not _lock.acquire(blocking=False):
        raise RuntimeError("SQL observation requires a serial process")
    if _poisoned:
        _lock.release()
        raise SqlWindowCleanupError("SQL observation requires a fresh process")
    state = {"coverage": "partial", "status": "not_started", "started": 0,
             "returned": 0, "raised": 0, "pending_at_close": 0,
             "resumed_unknown": 0, "overflow": 0, "dropped_starts": 0, "monitor_error": False,
             "unsupported_apis": 0, "calls": [], "runtime": runtime_identity()}
    guard = Lock()
    claimed = None
    armed = []
    global_enabled = False
    active = True
    pending = set()
    counts = {}
    cache = {}
    try:
        import psycopg
        if owners is None:
            owners, state["unsupported_apis"] = _driver_owners()
        if not isinstance(owners, dict) or not owners or any(v not in {"execute", "executemany", "copy"} for v in owners.values()):
            raise ValueError("Invalid SQL observation owners")
        if roots is None:
            from apps.live_control_server.routes import agent
            roots = [Path(agent.__file__).resolve(strict=True).parents[3]]
        roots = [Path(root).resolve(strict=True) for root in roots]
        driver_root = Path(psycopg.__file__).resolve(strict=True).parent
        if endpoints is None:
            endpoints = _endpoints()
        monitoring = sys.monitoring
        event_start, event_return = monitoring.events.PY_START, monitoring.events.PY_RETURN
        event_unwind, event_resume = monitoring.events.PY_UNWIND, monitoring.events.PY_RESUME
        mask = event_start | event_return | event_resume
        slot = next((slot for slot in range(6) if monitoring.get_tool(slot) is None), None)
        if slot is None:
            state["status"] = "unavailable"
            yield state
            return
        monitoring.use_tool_id(slot, "buddy-negative-sql-window")
        claimed = slot

        def on_start(code, offset):
            try:
                if _witness_sql.get():
                    return
                frame = sys._getframe(1)
                with guard:
                    if not active:
                        return
                    if len(pending) >= _MAX_PENDING:
                        state["dropped_starts"] += 1
                        state["monitor_error"] = True
                        return
                    cursor = frame.f_locals.get("self")
                    scope = _scope(cursor, endpoints)
                    source, caller, line = _caller(frame, roots, driver_root, cache)
                    turn = ("scoped" if scope_ref is not None and scope_ref[0] is not None
                            and _turn_scope.get() is scope_ref[0] else "unscoped")
                    key = (scope, owners[code], source, caller, line, turn)
                    pending.add(id(frame))
                    state["started"] += 1
                    if key in counts or len(counts) < _MAX_CALLERS:
                        counts[key] = counts.get(key, 0) + 1
                    else:
                        state["overflow"] += 1
            except BaseException:
                with guard:
                    state["monitor_error"] = True

        def on_finish(code, offset, value, *, failed):
            try:
                frame = sys._getframe(2)
                with guard:
                    ident = id(frame)
                    if ident in pending:
                        pending.remove(ident)
                        if active:
                            state["raised" if failed else "returned"] += 1
            except BaseException:
                with guard:
                    state["monitor_error"] = True

        def on_return(code, offset, value):
            on_finish(code, offset, value, failed=False)

        def on_unwind(code, offset, exc):
            if code in owners:
                on_finish(code, offset, exc, failed=True)

        def on_resume(code, offset):
            try:
                if _witness_sql.get():
                    return
                frame = sys._getframe(1)
                with guard:
                    if active and id(frame) not in pending:
                        state["resumed_unknown"] += 1
            except BaseException:
                with guard:
                    state["monitor_error"] = True

        for event, callback in ((event_start, on_start), (event_return, on_return),
                                (event_unwind, on_unwind), (event_resume, on_resume)):
            monitoring.register_callback(claimed, event, callback)
        global_enabled = True
        monitoring.set_events(claimed, event_unwind)
        for code in owners:
            armed.append(code)
            monitoring.set_local_events(claimed, code, mask)
        state["status"] = "observed"
        try:
            yield state
        finally:
            with guard:
                active = False
                state["pending_at_close"] = len(pending)
    finally:
        error = sys.exc_info()[1]
        failures = []
        if claimed is not None:
            if global_enabled:
                try:
                    monitoring.set_events(claimed, 0)
                except BaseException as exc:
                    failures.append(exc)
            for code in armed:
                try:
                    monitoring.set_local_events(claimed, code, 0)
                except BaseException as exc:
                    failures.append(exc)
            for event in (event_start, event_return, event_unwind, event_resume):
                try:
                    monitoring.register_callback(claimed, event, None)
                except BaseException as exc:
                    failures.append(exc)
            try:
                monitoring.free_tool_id(claimed)
            except BaseException as exc:
                failures.append(exc)
        with guard:
            state["calls"] = [dict(scope=k[0], api=k[1], source_sha256=k[2], code_sha256=k[3],
                                   line=k[4], count=v, **({"turn": k[5]} if scope_ref is not None else {}))
                              for k, v in sorted(counts.items(), key=lambda row: repr(row[0]))]
            if failures:
                state["monitor_error"] = True
                _poisoned = True
            if state["status"] == "observed" and (state["pending_at_close"] or state["resumed_unknown"]
                    or state["overflow"] or state["dropped_starts"] or state["monitor_error"] or state["unsupported_apis"]):
                state["status"] = "uncertain"
        _lock.release()
        if failures:
            if error is not None:
                error.add_note("SQL-window cleanup also failed; capture is uncertain")
            else:
                raise SqlWindowCleanupError("SQL-window cleanup failed") from failures[0]


def validate_sql_window(value, case_id):
    """Reject malformed partial inventories; this never certifies completeness."""
    keys = {"schema", "case_id", "window", "coverage", "status", "started", "returned", "raised",
            "pending_at_close", "resumed_unknown", "overflow", "dropped_starts", "monitor_error", "unsupported_apis", "calls"}
    numeric = ("started", "returned", "raised", "pending_at_close", "resumed_unknown", "overflow", "dropped_starts", "unsupported_apis")
    if isinstance(value, dict) and value.get("schema") in {"dmb_negative_retrieval_sql_window_v2", "dmb_negative_retrieval_sql_window_v3"}:
        keys.add("runtime")
    if (not isinstance(value, dict) or set(value) != keys
            or value["schema"] not in {"dmb_negative_retrieval_sql_window_v1", "dmb_negative_retrieval_sql_window_v2", "dmb_negative_retrieval_sql_window_v3"} or value["case_id"] != case_id
            or value["window"] != "turn_post_v1" or value["coverage"] != "partial"
            or value["status"] not in {"observed", "uncertain", "not_started", "unavailable"}
            or any(type(value[k]) is not int or value[k] < 0 for k in numeric)
            or type(value["monitor_error"]) is not bool or not isinstance(value["calls"], list)
            or len(value["calls"]) > _MAX_CALLERS):
        raise ValueError("Invalid SQL window")
    if value["schema"] in {"dmb_negative_retrieval_sql_window_v2", "dmb_negative_retrieval_sql_window_v3"}:
        runtime = value["runtime"]
        if (not isinstance(runtime, dict) or set(runtime) != {"normalizer", "implementation", "version", "cache_tag", "optimize"}
                or runtime["normalizer"] != "marshal-code-v1"
                or not isinstance(runtime["implementation"], str) or not runtime["implementation"]
                or not isinstance(runtime["cache_tag"], str) or not runtime["cache_tag"]
                or not isinstance(runtime["version"], list) or len(runtime["version"]) != 3
                or any(type(n) is not int or n < 0 for n in runtime["version"])
                or type(runtime["optimize"]) is not int or runtime["optimize"] < 0):
            raise ValueError("Invalid SQL window runtime")
    seen = set()
    total = 0
    for row in value["calls"]:
        row_keys = {"scope", "api", "source_sha256", "code_sha256", "line", "count"}
        if value["schema"] == "dmb_negative_retrieval_sql_window_v3":
            row_keys.add("turn")
        if (not isinstance(row, dict) or set(row) != row_keys
                or (value["schema"] == "dmb_negative_retrieval_sql_window_v3" and row["turn"] not in {"scoped", "unscoped"})
                or row["scope"] not in {"app", "core", "unknown"} or row["api"] not in {"execute", "executemany", "copy"}
                or type(row["count"]) is not int or row["count"] < 1):
            raise ValueError("Invalid SQL call inventory")
        hashes = (row["source_sha256"], row["code_sha256"])
        if not ((hashes == (None, None) and row["line"] is None)
                or (all(isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h) for h in hashes)
                    and type(row["line"]) is int and row["line"] > 0)):
            raise ValueError("Invalid SQL caller identity")
        key = (row["scope"], row["api"], *hashes, row["line"], row.get("turn"))
        if key in seen:
            raise ValueError("Duplicate SQL call inventory")
        seen.add(key); total += row["count"]
    if (total + value["overflow"] != value["started"]
            or value["returned"] + value["raised"] + value["pending_at_close"] != value["started"]
            or (value["status"] == "observed" and (value["pending_at_close"] or value["resumed_unknown"]
                or value["overflow"] or value["dropped_starts"] or value["monitor_error"] or value["unsupported_apis"]))
            or (value["status"] in {"not_started", "unavailable"} and
                (value["started"] or value["resumed_unknown"] or value["overflow"] or value["dropped_starts"]))):
        raise ValueError("Inconsistent SQL window")
    return value
