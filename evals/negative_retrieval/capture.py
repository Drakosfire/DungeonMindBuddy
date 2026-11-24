"""Opt-in related-page observation around the existing ordinary capture.

Run only in a dedicated serial process against the benchmark's pinned isolated
fixture. All runtime, provider, source and database preflight remains with the
existing capture owner; this wrapper never modifies its request or response.
"""
from pathlib import Path
from threading import Lock
from unittest.mock import patch

from evals.buddy_benchmark.artifacts import immutable_save
from evals.buddy_benchmark import workflow

from .related_page_probe import observe_related_page_owners

_lock = Lock()


def capture(manifest, output, *, clone_app=False):
    """Delegate ordinary capture with a partial, per-turn related-page probe."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("Negative-retrieval capture must be serial")
    try:
        spec, _ = workflow.load_manifest(manifest)
        if spec.get("conversation_mode") != "build_sequence":
            raise ValueError("Negative-retrieval probe requires ordinary Build sequence capture")
        original = workflow.capture_case

        def observed_case(client, world, template, case, directory, **kwargs):
            failure = None
            with observe_related_page_owners() as records:
                try:
                    return original(client, world, template, case, directory, **kwargs)
                except BaseException as exc:
                    failure = exc
                    raise
                finally:
                    try:
                        immutable_save(Path(directory), "related-page-probe", {
                            "schema": "dmb_negative_retrieval_related_page_probe_v1",
                            "coverage": "partial", "case_id": case["id"], "records": records,
                        })
                    except Exception as exc:
                        if failure is None:
                            raise
                        failure.add_note(f"Related-page probe retention failed: {type(exc).__name__}")

        with patch.object(workflow, "capture_case", observed_case):
            return workflow.capture(manifest, output, clone_app=clone_app)
    finally:
        _lock.release()
