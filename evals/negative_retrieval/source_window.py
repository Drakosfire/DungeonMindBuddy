"""Partial, turn-scoped diagnostics for selected Core source-view entries.

An entry is an attempted call, not evidence that a source was returned. This
never establishes complete coverage or stores arguments, identities or bodies.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from unittest.mock import patch
from pathlib import Path
import hashlib
import inspect
import marshal
import sys
import types

_scope = ContextVar("negative_retrieval_source_window", default=None)
_serial = Lock()
_poisoned = False
_KINDS = ("metadata", "text", "text_batch")
_APP_KINDS = ("app_single", "app_revision")
KNOWN_APP_OWNERS = {
    "normalizer": "marshal-code-v1", "implementation": "cpython", "version": [3, 13, 12],
    "cache_tag": "cpython-313", "optimize": 0,
    "source_sha256": "56aa3d06bf1bebb0e2cbdb275aba63db892d68d7b6e8c4ddb35ffe4b2e2dfa6a",
    "app_single": "acc1bb8109a702543c8d86c45ffc9358cc010aa0b5f61c181d8ed15086bf4a9c",
    "app_revision": "442b09b419311e67fa059ba59d1334209384eb26e7c1409b348e590c1ef152da",
}
KNOWN_APP_BATCH_CODE = "0006033ffc1ea9f4669d26925cfc8df0cf522b3588f6cc99853cfac178905e06"
KNOWN_APP_BATCH_LINE = 145
# Exact pinned Core 6beb506 and CPython 3.13.12 source/code pair. Unknown
# implementations remain diagnostic; this is not process attestation.
KNOWN_TEXT_OWNERS = {
    "normalizer": "marshal-code-v1", "implementation": "cpython", "version": [3, 13, 12],
    "cache_tag": "cpython-313", "optimize": 0,
    "native": {"source_sha256": "1c1016f0d32d43cf4326906383f1ecd2c09b58961623e035914d875d381cb777",
               "code_sha256": "1cc30f75a24b57da0f63f01c684ab49bd1f0cce7d3dea5f452e6d9ade4b8ffd5"},
    "operator": {"source_sha256": "4a961f9cf54f8109350515a11f295f69ec26724a9c5d0ad77967689d2a71a1ef",
                 "code_sha256": "fc07987dd704feca63f54d0eb592bf8eb3c981e81c3f7e84d97eb536e0715e07"},
}


# The exact pinned code reaches this line once while constructing the
# nonempty batch SQL. Earlier failures remain unobserved and therefore unknown.
KNOWN_BATCH_CODE = "3e0f4f1602289759aa4cea23303e55f180bad8a8427400dec83248c1abb28a6e"
KNOWN_BATCH_LINE = 1360


def known_scoped_text_attempt(value):
    """Recognize one lower-bound attempt, never a completed source read."""
    if (value is None or value.get("schema") not in {"dmb_negative_retrieval_source_window_v2", "dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}
            or value.get("owner_provenance") != KNOWN_TEXT_OWNERS
            or value.get("status") != "observed" or value.get("dispatch_uncertain") is not False):
        return False
    single = value["scoped"]["text"] > 0
    batch = (value["schema"] in {"dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}
             and value["batch_read"]["code_sha256"] == KNOWN_BATCH_CODE
             and value["batch_read"]["scoped"] > 0)
    return single or batch


def known_scoped_app_attempt(value):
    """Recognize pinned App reader entries, never source identity or completed reads."""
    return bool(value and value.get("schema") in {"dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}
        and value.get("status") == "observed" and value.get("dispatch_uncertain") is False
        and value["app_source"]["owner_provenance"] == KNOWN_APP_OWNERS
        and (any(value["app_source"]["scoped"].values())
             or (value["schema"] == "dmb_negative_retrieval_source_window_v5"
                 and value["app_batch_read"]["code_sha256"] == KNOWN_APP_BATCH_CODE
                 and value["app_batch_read"]["scoped"] > 0)))


class SourceWindowCleanupError(RuntimeError):
    """The diagnostic could not prove its process-wide hooks were removed."""


def validate_artifact(value, case_id):
    """Validate a partial diagnostic without converting attempts into grades."""
    expected = {"schema", "case_id", "window", "dispatch_uncertain", "coverage", "status",
                "scoped", "unscoped", "pending_at_close", "late", "monitor_error"}
    if isinstance(value, dict) and value.get("schema") in {"dmb_negative_retrieval_source_window_v2", "dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}:
        expected.add("owner_provenance")
    if isinstance(value, dict) and value.get("schema") in {"dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}:
        expected.add("batch_read")
    if isinstance(value, dict) and value.get("schema") in {"dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}:
        expected.add("app_source")
    if isinstance(value, dict) and value.get("schema") == "dmb_negative_retrieval_source_window_v5":
        expected.add("app_batch_read")
    if (not isinstance(value, dict) or set(value) != expected
            or value["schema"] not in {"dmb_negative_retrieval_source_window_v1", "dmb_negative_retrieval_source_window_v2", "dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}
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
    if value["schema"] in {"dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}:
        batch = value["batch_read"]
        if (not isinstance(batch, dict) or set(batch) != {"scoped", "unscoped", "code_sha256"}
                or any(type(batch[k]) is not int or batch[k] < 0 for k in ("scoped", "unscoped"))
                or any(batch[k] > value[k]["text_batch"] for k in ("scoped", "unscoped"))
                or (batch["code_sha256"] is not None and (not isinstance(batch["code_sha256"], str)
                    or len(batch["code_sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in batch["code_sha256"])))
                or (batch["code_sha256"] is None and (batch["scoped"] or batch["unscoped"]))):
            raise ValueError("Invalid source window batch read")
    if value["schema"] in {"dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}:
        app = value["app_source"]
        if not isinstance(app, dict) or set(app) != {"scoped", "unscoped", "owner_provenance"}:
            raise ValueError("Invalid App source window")
        for group in ("scoped", "unscoped"):
            if (not isinstance(app[group], dict) or set(app[group]) != set(_APP_KINDS)
                    or any(type(n) is not int or n < 0 for n in app[group].values())):
                raise ValueError("Invalid App source window counts")
        proof = app["owner_provenance"]
        if proof is not None:
            expected_app = {"normalizer", "implementation", "version", "cache_tag", "optimize", "source_sha256", *_APP_KINDS}
            if (not isinstance(proof, dict) or set(proof) != expected_app
                    or proof["normalizer"] != "marshal-code-v1"
                    or not isinstance(proof["implementation"], str) or not isinstance(proof["cache_tag"], str)
                    or not isinstance(proof["version"], list) or len(proof["version"]) != 3
                    or any(type(n) is not int or n < 0 for n in proof["version"])
                    or type(proof["optimize"]) is not int or proof["optimize"] < 0
                    or any(not isinstance(proof[k], str) or len(proof[k]) != 64
                           or any(c not in "0123456789abcdef" for c in proof[k])
                           for k in ("source_sha256", *_APP_KINDS))):
                raise ValueError("Invalid App source provenance")
    if value["schema"] == "dmb_negative_retrieval_source_window_v5":
        batch = value["app_batch_read"]
        if (not isinstance(batch, dict) or set(batch) != {"scoped", "unscoped", "scoped_starts", "unscoped_starts", "code_sha256"}
                or any(type(batch[k]) is not int or batch[k] < 0 for k in ("scoped", "unscoped", "scoped_starts", "unscoped_starts"))
                or batch["scoped"] > batch["scoped_starts"] or batch["unscoped"] > batch["unscoped_starts"]
                or (batch["code_sha256"] is not None and (not isinstance(batch["code_sha256"], str)
                    or len(batch["code_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in batch["code_sha256"])))
                or (batch["code_sha256"] is None and (batch["scoped"] or batch["unscoped"]))):
            raise ValueError("Invalid App batch window")
    troubled = (value["pending_at_close"] or value["late"] or value["monitor_error"]
                 or any(value["unscoped"].values())
                 or (value["schema"] in {"dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"} and value["batch_read"]["unscoped"])
                 or (value["schema"] in {"dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"} and any(value["app_source"]["unscoped"].values()))
                 or (value["schema"] == "dmb_negative_retrieval_source_window_v5" and value["app_batch_read"]["unscoped_starts"]))
    if value["status"] == "observed" and troubled:
        raise ValueError("Observed source window has unresolved work")
    if value["status"] in {"not_started", "unavailable", "setup_failed"} and (
            any(value["scoped"].values()) or any(value["unscoped"].values())
            or value["pending_at_close"] or value["late"]
            or (value["schema"] in {"dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}
                and any(value["app_source"][group][kind] for group in ("scoped", "unscoped") for kind in _APP_KINDS))
            or (value["schema"] == "dmb_negative_retrieval_source_window_v5" and
                (value["app_batch_read"]["scoped_starts"] or value["app_batch_read"]["unscoped_starts"]))):
        raise ValueError("Unstarted source window has activity")
    if value["status"] == "setup_failed" and not value["monitor_error"]:
        raise ValueError("Source window setup failure is missing its error flag")
    if value["schema"] in {"dmb_negative_retrieval_source_window_v2", "dmb_negative_retrieval_source_window_v3", "dmb_negative_retrieval_source_window_v4", "dmb_negative_retrieval_source_window_v5"}:
        provenance = value["owner_provenance"]
        if provenance is not None:
            if (not isinstance(provenance, dict)
                    or set(provenance) != {"normalizer", "implementation", "version", "cache_tag", "optimize", "native", "operator"}
                    or provenance["normalizer"] != "marshal-code-v1"
                    or not isinstance(provenance["implementation"], str)
                    or not isinstance(provenance["cache_tag"], str)
                    or not isinstance(provenance["version"], list) or len(provenance["version"]) != 3
                    or any(type(n) is not int or n < 0 for n in provenance["version"])
                    or type(provenance["optimize"]) is not int or provenance["optimize"] < 0):
                raise ValueError("Invalid source window owner provenance")
            for name in ("native", "operator"):
                row = provenance[name]
                if (not isinstance(row, dict) or set(row) != {"source_sha256", "code_sha256"}
                        or any(not isinstance(v, str) or len(v) != 64
                               or any(c not in "0123456789abcdef" for c in v) for v in row.values())):
                    raise ValueError("Invalid source window owner provenance")
    return value


def _normalize_code(code):
    """Remove host paths recursively while retaining all other code fields."""
    return code.replace(co_filename="<owner>", co_consts=tuple(
        _normalize_code(item) if isinstance(item, types.CodeType) else item for item in code.co_consts))


def _owner_provenance(native_module, operator_module, package_root, native_code, operator_code):
    """Fingerprint registered code and its expected package files, host-side only."""
    try:
        result = {"normalizer": "marshal-code-v1", "implementation": sys.implementation.name,
                  "version": list(sys.version_info[:3]), "cache_tag": sys.implementation.cache_tag,
                  "optimize": sys.flags.optimize}
        root = Path(package_root).resolve(strict=True)
        for label, module, code, filename in (
            ("native", native_module, native_code, "vnext_sources.py"),
            ("operator", operator_module, operator_code, "vnext_operator_sources.py"),
        ):
            expected = (root / "infrastructure" / "postgres" / filename).resolve(strict=True)
            origin = Path(module.__spec__.origin).resolve(strict=True)
            actual = Path(code.co_filename).resolve(strict=True)
            if origin != expected or actual != expected or Path(module.__file__).resolve(strict=True) != expected:
                return None
            result[label] = {"source_sha256": hashlib.sha256(expected.read_bytes()).hexdigest(),
                             "code_sha256": hashlib.sha256(marshal.dumps(_normalize_code(code))).hexdigest()}
        return result
    except (OSError, AttributeError, TypeError, ValueError):
        # Provenance is optional; inability to bind it cannot imply a read.
        return None


def _default_owners():
    import dungeonmind
    from dungeonmind.infrastructure.postgres import vnext_sources, vnext_operator_sources
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
    try:
        provenance = _owner_provenance(vnext_sources, vnext_operator_sources,
            Path(dungeonmind.__file__).resolve(strict=True).parent,
            _PostgresNativeTextSourceView.get_native_text_source.__code__,
            _PostgresOperatorSourceView.get_native_text_source.__code__)
    except (OSError, AttributeError, TypeError, ValueError):
        provenance = None
    return owners, _BUILD_GRAPH_PREPARATION, provenance


def _app_source_owners():
    """Observe original function code even beneath the outer owner wrappers."""
    from application_state.source import repository
    names = {"get_source_markdown": "app_single", "get_source_markdown_by_revision_id": "app_revision"}
    if hasattr(repository, "get_source_markdown_batch"):
        names["get_source_markdown_batch"] = "app_batch"
    functions = {kind: inspect.unwrap(getattr(repository, name)) for name, kind in names.items()}
    owners = {function.__code__: kind for kind, function in functions.items()}
    try:
        path = Path(repository.__file__).resolve(strict=True)
        if (path != Path(repository.__spec__.origin).resolve(strict=True)
                or any(Path(function.__code__.co_filename).resolve(strict=True) != path for function in functions.values())):
            return owners, None
        proof = {"normalizer": "marshal-code-v1", "implementation": sys.implementation.name,
                 "version": list(sys.version_info[:3]), "cache_tag": sys.implementation.cache_tag,
                 "optimize": sys.flags.optimize, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        proof.update({kind: hashlib.sha256(marshal.dumps(_normalize_code(function.__code__))).hexdigest()
                      for kind, function in functions.items() if kind in _APP_KINDS})
        return owners, proof
    except (OSError, AttributeError, TypeError, ValueError):
        return owners, None


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
             "pending_at_close": 0, "late": 0, "monitor_error": False,
             "owner_provenance": None,
             "batch_read": {"scoped": 0, "unscoped": 0, "code_sha256": None},
             "app_source": {"scoped": {key: 0 for key in _APP_KINDS},
                            "unscoped": {key: 0 for key in _APP_KINDS}, "owner_provenance": None},
             "app_batch_read": {"scoped": 0, "unscoped": 0, "scoped_starts": 0,
                                "unscoped_starts": 0, "code_sha256": None}}
    guard = Lock()
    token = object()
    claimed = None
    line_event = None
    armed = []
    old_submit = None
    reset = None
    active = True
    try:
        if owners is None:
            try:
                defaults = _default_owners()
                owners, executor = defaults[:2]
                if len(defaults) == 3:
                    state["owner_provenance"] = defaults[2]
                try:
                    app_owners, app_provenance = _app_source_owners()
                except (ImportError, AttributeError, TypeError, ValueError):
                    # Older or instrumented source lineages need not offer these
                    # functions. Their App coverage remains unknown.
                    app_owners, app_provenance = {}, None
                if set(owners) & set(app_owners):
                    raise ValueError("App source owners overlap Core owners")
                owners = {**owners, **app_owners}
                state["app_source"]["owner_provenance"] = app_provenance
            except (ImportError, AttributeError):
                state["status"] = "unavailable"
                yield state
                return
        if not isinstance(owners, dict) or not owners or any(v not in (*_KINDS, *_APP_KINDS, "app_batch") for v in owners.values()):
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
                        if kind == "app_batch":
                            state["app_batch_read"][group + "_starts"] += 1
                        elif kind in _APP_KINDS:
                            state["app_source"][group][kind] += 1
                        else:
                            state[group][kind] += 1
                    else:
                        state["late"] += 1
            except BaseException:
                # A diagnostic must never interrupt the source owner.
                state["monitor_error"] = True

        monitoring.register_callback(slot, event, on_start)
        batch_code = None
        app_batch_code = None
        candidates = [code for code, kind in owners.items() if kind == "text_batch"]
        if state["owner_provenance"] == KNOWN_TEXT_OWNERS and len(candidates) == 1:
            candidate = candidates[0]
            digest = hashlib.sha256(marshal.dumps(_normalize_code(candidate))).hexdigest()
            if digest == KNOWN_BATCH_CODE:
                batch_code = candidate
                state["batch_read"]["code_sha256"] = digest
        app_candidates = [code for code, kind in owners.items() if kind == "app_batch"]
        if state["app_source"]["owner_provenance"] == KNOWN_APP_OWNERS and len(app_candidates) == 1:
            candidate = app_candidates[0]
            digest = hashlib.sha256(marshal.dumps(_normalize_code(candidate))).hexdigest()
            if digest == KNOWN_APP_BATCH_CODE:
                app_batch_code = candidate
                state["app_batch_read"]["code_sha256"] = digest
        if batch_code is not None or app_batch_code is not None:
            line_event = monitoring.events.LINE
            def on_line(code, line):
                target = ("batch_read" if code is batch_code and line == KNOWN_BATCH_LINE else
                          "app_batch_read" if code is app_batch_code and line == KNOWN_APP_BATCH_LINE else None)
                if target is None:
                    return
                try:
                    group = "scoped" if _scope.get() is token else "unscoped"
                    with guard:
                        if active:
                            state[target][group] += 1
                        else:
                            state["late"] += 1
                except BaseException:
                    state["monitor_error"] = True
            monitoring.register_callback(slot, line_event, on_line)
        for code in owners:
            armed.append(code)
            monitoring.set_local_events(slot, code, event | (line_event if code is batch_code or code is app_batch_code else 0))

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
                if line_event is not None:
                    try:
                        monitoring.register_callback(claimed, line_event, None)
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
                        or state["monitor_error"] or any(state["unscoped"].values())
                        or state["batch_read"]["unscoped"] or any(state["app_source"]["unscoped"].values())
                        or state["app_batch_read"]["unscoped_starts"]):
                    state["status"] = "uncertain"
            _serial.release()
        if failures:
            if primary_error is not None:
                primary_error.add_note("Source-window cleanup also failed; capture is uncertain")
            else:
                raise SourceWindowCleanupError("Source-window cleanup failed") from failures[0]
