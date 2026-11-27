"""Opt-in related-page observation around the existing ordinary capture.

Run only in a dedicated serial process against the benchmark's pinned isolated
fixture. All runtime, provider, source and database preflight remains with the
existing capture owner; this wrapper never modifies its request or response.
"""
from pathlib import Path
from hashlib import sha256
from threading import Lock
from types import SimpleNamespace
from unittest.mock import patch
import json
import sys
import inspect

from evals.buddy_benchmark.artifacts import immutable_save
from evals.buddy_benchmark import workflow

from .fixture_binding import verify_preflight_history, verify_preflight_snapshot
from .fixture_sources import inspect_related_pages
from .related_page_probe import observe_related_page_owners
from .native_graph_probe import observe_native_graph_owners
from .source_window import observe_source_window
from .owned_db_fixture import checked_owned_dsn
from .primary_page_stability import inspect_primary_page, expected_primary_page
from .primary_resolution_probe import observe_primary_resolution

_lock = Lock()


def _fixture_bytes(fixtures):
    if not isinstance(fixtures, dict):
        raise ValueError("Fixture set must be an object")
    try:
        return json.dumps(fixtures, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Fixture set must be canonical JSON") from exc


def fixture_sha256(fixtures):
    """Hash a canonical evaluator-only fixture set, never a model input."""
    return sha256(_fixture_bytes(fixtures)).hexdigest()


def capture(manifest, output, *, expected_manifest_sha256=None, expected_fixture_sha256=None,
            clone_app=False, fixtures=None):
    """Delegate ordinary capture with partial per-turn observation.

    Optional fixtures are evaluator-side only and never enter a product request.
    Their exact related-page inventory is read before and after each turn.
    """
    if clone_app:
        raise ValueError("Use the already owned workstream App clone; per-capture cloning is disabled")
    if (not isinstance(expected_manifest_sha256, str) or len(expected_manifest_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_manifest_sha256)):
        raise ValueError("A frozen manifest SHA-256 is required")
    if fixtures is not None:
        frozen_fixtures = _fixture_bytes(fixtures)
        if (not isinstance(expected_fixture_sha256, str) or len(expected_fixture_sha256) != 64
                or any(c not in "0123456789abcdef" for c in expected_fixture_sha256)
                or sha256(frozen_fixtures).hexdigest() != expected_fixture_sha256):
            raise ValueError("Fixture set differs from its frozen SHA-256")
        # A caller cannot mutate nested fixture data after it has been pinned.
        fixtures = json.loads(frozen_fixtures)
    elif expected_fixture_sha256 is not None:
        raise ValueError("Fixture pin requires a fixture set")
    if not _lock.acquire(blocking=False):
        raise RuntimeError("Negative-retrieval capture must be serial")
    try:
        if sha256(Path(manifest).read_bytes()).hexdigest() != expected_manifest_sha256:
            raise ValueError("Manifest differs from the frozen SHA-256")
        spec, _ = workflow.load_manifest(manifest, expected_sha256=expected_manifest_sha256)
        if spec.get("conversation_mode") != "build_sequence":
            raise ValueError("Negative-retrieval probe requires ordinary Build sequence capture")
        if fixtures is not None:
            if not isinstance(fixtures, dict) or set(fixtures) != {case["id"] for case in spec["cases"]}:
                raise ValueError("Fixture cases must match the ordinary capture manifest")
            for case in spec["cases"]:
                if fixtures[case["id"]]["request"] != case["question"]:
                    raise ValueError("Fixture request differs from ordinary capture")
        # The ordinary runner checks its manifest pins and Core login, but its
        # cohort path does not establish that this caller owns the App clone.
        # Require the live workstream owner and exact database identity before
        # any fixture access, output creation or provider dispatch.
        checked_owned_dsn()
        original = workflow.capture_case

        def observed_case(client, world, template, case, directory, **kwargs):
            fixture = None if fixtures is None else fixtures[case["id"]]
            before = None
            primary_before = None
            checked_client = client
            if fixture is not None:
                work = template["primary_work"]
                preflight_request = SimpleNamespace(owner_scope=SimpleNamespace(world_id=world),
                                                     primary_work=SimpleNamespace(object_id=work["object_id"]))
                try:
                    verify_preflight_snapshot(fixture, template, world, kwargs.get("build_editor_snapshot"))
                    primary_before = inspect_primary_page(world, work)
                    if primary_before != expected_primary_page(fixture, world, work):
                        raise ValueError("Actual primary page differs from the frozen fixture")
                    conversation = kwargs.get("expected_conversation_id")
                    if conversation is not None or fixture["history"]:
                        response = client.get("/api/live/agent/worlds/" + world + "/conversation",
                                              params={"limit": 100})
                        if response.status_code != 200:
                            raise ValueError("Preflight history read failed")
                        history = response.json()
                        if conversation is None:
                            conversation = history.get("active_conversation_id")
                            if not isinstance(conversation, str) or not conversation:
                                raise ValueError("A seeded fixture requires an active conversation")
                            kwargs["expected_conversation_id"] = conversation
                        verify_preflight_history(fixture, history, world, conversation)
                        # Recheck the runner's own history read, not just this
                        # earlier preflight. The conversation ID can remain
                        # unchanged while another turn alters its prefix.
                        class CheckedHistoryClient:
                            def __init__(self, wrapped):
                                self.wrapped = wrapped
                                self.pending = True

                            def __getattr__(self, name):
                                return getattr(self.wrapped, name)

                            def get(self, route, *args, **options):
                                history_route = "/api/live/agent/worlds/" + world + "/conversation"
                                if route == history_route:
                                    params = options.get("params", {})
                                    if (not isinstance(params, dict) or "before_sequence" in params
                                            or params.get("limit", 100) != 100):
                                        raise ValueError("Runner history query cannot prove a complete prefix")
                                    options["params"] = {**params, "limit": 100}
                                response = self.wrapped.get(route, *args, **options)
                                if self.pending:
                                    if (route != "/api/live/agent/worlds/" + world + "/conversation"
                                            or response.status_code != 200):
                                        raise ValueError("Runner history read could not be verified")
                                    verify_preflight_history(fixture, response.json(), world, conversation)
                                    self.pending = False
                                return response

                        checked_client = CheckedHistoryClient(client)
                    before = inspect_related_pages(preflight_request, fixture)
                except Exception as exc:
                    immutable_save(Path(directory), "fixture-sources", {
                        "schema": "dmb_negative_retrieval_fixture_sources_v1", "case_id": case["id"],
                        "status": "preflight_failed", "error_type": type(exc).__name__,
                    })
                    raise
            records = []
            native_records = None
            source_window_state = None
            primary_resolution_state = None
            source_window_setup_failed = False
            dispatch_started = False
            post_entered = False
            dispatch_uncertain = False

            class ObservedTurnClient:
                """Instrument the actual turn POST, not history or setup calls."""
                def __init__(self, wrapped):
                    self.wrapped = wrapped

                def __getattr__(self, name):
                    return getattr(self.wrapped, name)

                def post(self, route, *args, **options):
                    nonlocal records, native_records, source_window_state, primary_resolution_state, source_window_setup_failed, dispatch_started, post_entered, dispatch_uncertain
                    if route != "/api/live/agent/turn":
                        return self.wrapped.post(route, *args, **options)
                    if dispatch_started:
                        raise ValueError("A capture may dispatch only one turn")
                    dispatch_started = True
                    if inspect.iscoroutinefunction(self.wrapped.post):
                        raise TypeError("Async clients are unsupported for serial capture")
                    with observe_primary_resolution() as primary_resolution_state, observe_related_page_owners() as records:
                        with observe_native_graph_owners() as native_records:
                            try:
                                with observe_source_window() as source_window_state:
                                    post_entered = True
                                    try:
                                        response = self.wrapped.post(route, *args, **options)
                                        if inspect.isawaitable(response):
                                            dispatch_uncertain = True
                                            if inspect.iscoroutine(response):
                                                response.close()
                                            raise TypeError("Awaitable response is unsupported for serial capture")
                                        return response
                                    finally:
                                        # Detach existing owner rows before their hooks exit.
                                        records = [dict(row) for row in records]
                                        native_records = [dict(row) for row in native_records]
                            except BaseException:
                                if not post_entered:
                                    source_window_setup_failed = True
                                raise
                            finally:
                                if source_window_state is not None:
                                    source_window_state = {
                                        key: dict(value) if isinstance(value, dict) else value
                                        for key, value in source_window_state.items() if key != "pending"
                                    }

            try:
                return original(ObservedTurnClient(checked_client), world, template, case, directory, **kwargs)
            finally:
                failure = sys.exc_info()[1]
                try:
                    primary_row = dict(primary_resolution_state) if primary_resolution_state is not None else {
                        "status": "unavailable" if dispatch_started else "not_started",
                        "started": 0, "returned": 0, "raised": 0, "pending_at_close": 0,
                    }
                    if not post_entered and primary_resolution_state is not None:
                        primary_row["status"] = "uncertain" if primary_row["started"] else "not_started"
                    elif dispatch_uncertain and primary_row["status"] == "observed":
                        primary_row["status"] = "uncertain"
                    immutable_save(Path(directory), "primary-resolution-probe", {
                        "schema": "dmb_negative_retrieval_primary_resolution_v1", "case_id": case["id"],
                        "window": "turn_post_v1", "coverage": "partial", **primary_row,
                    })
                    immutable_save(Path(directory), "related-page-probe", {
                        "schema": "dmb_negative_retrieval_related_page_probe_v1",
                        "coverage": "partial", "window": "turn_post_v1", "case_id": case["id"],
                        "status": "dispatch_uncertain" if dispatch_uncertain else "observed" if post_entered else "not_started", "records": records,
                    })
                    immutable_save(Path(directory), "native-graph-probe", {
                        "schema": "dmb_negative_retrieval_native_graph_probe_v1",
                        "coverage": "partial", "window": "turn_post_v1", "case_id": case["id"],
                        "status": "dispatch_uncertain" if dispatch_uncertain else "observed" if post_entered else "not_started",
                        "records": native_records if native_records is not None else [],
                    })
                    immutable_save(Path(directory), "source-window-probe", {
                        "schema": "dmb_negative_retrieval_source_window_v7", "case_id": case["id"],
                        "window": "turn_post_v1", "dispatch_uncertain": dispatch_uncertain,
                        **(source_window_state if source_window_state is not None else {
                            "coverage": "partial", "status": "setup_failed" if source_window_setup_failed else "not_started",
                            "scoped": {"metadata": 0, "text": 0, "text_batch": 0},
                            "unscoped": {"metadata": 0, "text": 0, "text_batch": 0},
                            "pending_at_close": 0, "late": 0,
                            "monitor_error": source_window_setup_failed, "owner_provenance": None,
                            "batch_read": {"scoped": 0, "unscoped": 0, "code_sha256": None},
                            "app_source": {"scoped": {"app_single": 0, "app_revision": 0},
                                           "unscoped": {"app_single": 0, "app_revision": 0}, "owner_provenance": None},
                            "app_batch_read": {"scoped": 0, "unscoped": 0, "scoped_starts": 0,
                                               "unscoped_starts": 0, "code_sha256": None},
                            "pdf_source": {"scoped": 0, "unscoped": 0, "owner_provenance": None},
                            "pdf_discovery": {"scoped": 0, "unscoped": 0, "scoped_starts": 0,
                                              "unscoped_starts": 0, "owner_provenance": None},
                        }),
                    })
                    if fixture is not None:
                        primary_after = None
                        primary_error = None
                        primary_status = "not_started"
                        if post_entered:
                            try:
                                primary_after = inspect_primary_page(world, work)
                                primary_status = "stable" if primary_before == primary_after else "changed"
                            except Exception as exc:
                                primary_status = "unavailable"
                                primary_error = type(exc).__name__
                        immutable_save(Path(directory), "primary-page-stability", {
                            "schema": "dmb_negative_retrieval_primary_page_v1", "case_id": case["id"],
                            "status": primary_status, "before": primary_before, "after": primary_after,
                            "error_type": primary_error,
                        })
                        immutable_save(Path(directory), "fixture-pin", {
                            "schema": "dmb_negative_retrieval_fixture_pin_v1", "case_id": case["id"],
                            "fixture_set_sha256": expected_fixture_sha256,
                            "case_sha256": fixture_sha256({case["id"]: fixture}),
                        })
                        try:
                            after = inspect_related_pages(preflight_request, fixture)
                        except Exception as exc:
                            immutable_save(Path(directory), "fixture-sources", {
                                "schema": "dmb_negative_retrieval_fixture_sources_v1", "case_id": case["id"],
                                "status": "postflight_failed", "before": before, "error_type": type(exc).__name__,
                            })
                            raise
                        immutable_save(Path(directory), "fixture-sources", {
                            "schema": "dmb_negative_retrieval_fixture_sources_v1", "case_id": case["id"],
                            "status": "stable" if before == after else "changed", "before": before, "after": after,
                        })
                        if before != after:
                            raise ValueError("Related-page fixture changed during capture")
                except Exception as exc:
                    if failure is None:
                        raise
                    failure.add_note(f"Probe or fixture retention failed: {type(exc).__name__}")

        # The deployed serving lineage's capture predates the optional clone
        # keyword; it already runs against the caller-owned App database. Both
        # supported signatures must accept the pinned cohort path, which owns
        # the read-only Core guard and avoids the standalone inventory scan.
        parameters = inspect.signature(workflow.capture).parameters
        cohort = parameters.get("cohort_manifest_sha256")
        if cohort is None or cohort.kind not in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            raise ValueError("Ordinary capture does not explicitly support the pinned cohort path")
        options = {"cohort_manifest_sha256": expected_manifest_sha256}
        if "clone_app" in parameters:
            if parameters["clone_app"].kind not in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                raise ValueError("Ordinary capture clone option is not explicitly controllable")
            options["clone_app"] = False
        with patch.object(workflow, "capture_case", observed_case):
            return workflow.capture(manifest, output, **options)
    finally:
        _lock.release()
