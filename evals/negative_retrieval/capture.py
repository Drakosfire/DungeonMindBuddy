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

from evals.buddy_benchmark.artifacts import immutable_save
from evals.buddy_benchmark import workflow

from .fixture_binding import verify_preflight_history, verify_preflight_snapshot
from .fixture_sources import inspect_related_pages
from .related_page_probe import observe_related_page_owners
from .native_graph_probe import observe_native_graph_owners

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
        original = workflow.capture_case

        def observed_case(client, world, template, case, directory, **kwargs):
            fixture = None if fixtures is None else fixtures[case["id"]]
            before = None
            checked_client = client
            if fixture is not None:
                work = template["primary_work"]
                preflight_request = SimpleNamespace(owner_scope=SimpleNamespace(world_id=world),
                                                     primary_work=SimpleNamespace(object_id=work["object_id"]))
                try:
                    verify_preflight_snapshot(fixture, template, world, kwargs.get("build_editor_snapshot"))
                    conversation = kwargs.get("expected_conversation_id")
                    if conversation is not None or fixture["history"]:
                        response = client.get("/api/live/agent/worlds/" + world + "/conversation")
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
            dispatch_started = False
            post_entered = False

            class ObservedTurnClient:
                """Instrument the actual turn POST, not history or setup calls."""
                def __init__(self, wrapped):
                    self.wrapped = wrapped

                def __getattr__(self, name):
                    return getattr(self.wrapped, name)

                def post(self, route, *args, **options):
                    nonlocal records, native_records, dispatch_started, post_entered
                    if route != "/api/live/agent/turn":
                        return self.wrapped.post(route, *args, **options)
                    if dispatch_started:
                        raise ValueError("A capture may dispatch only one turn")
                    dispatch_started = True
                    with observe_related_page_owners() as records:
                        with observe_native_graph_owners() as native_records:
                            post_entered = True
                            return self.wrapped.post(route, *args, **options)

            try:
                return original(ObservedTurnClient(checked_client), world, template, case, directory, **kwargs)
            finally:
                failure = sys.exc_info()[1]
                try:
                    immutable_save(Path(directory), "related-page-probe", {
                        "schema": "dmb_negative_retrieval_related_page_probe_v1",
                        "coverage": "partial", "case_id": case["id"],
                        "status": "observed" if post_entered else "not_started", "records": records,
                    })
                    immutable_save(Path(directory), "native-graph-probe", {
                        "schema": "dmb_negative_retrieval_native_graph_probe_v1",
                        "coverage": "partial", "case_id": case["id"],
                        "status": "observed" if post_entered else "not_started",
                        "records": native_records if native_records is not None else [],
                    })
                    if fixture is not None:
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

        with patch.object(workflow, "capture_case", observed_case):
            return workflow.capture(manifest, output, clone_app=False,
                                    cohort_manifest_sha256=expected_manifest_sha256)
    finally:
        _lock.release()
