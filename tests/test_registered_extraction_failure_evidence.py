import hashlib
import json
import os
import stat
import subprocess
import sys

import pytest

from tests.test_worldbuilding_profile_pipeline import (
    _admit_fixture_source,
    _load_fixture,
    _pass_outputs_for_span,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    FixtureCategoryGraphPassClient,
    CategoryGraphExtractionError,
)
from src.graph_memory.extraction import graph_preview_runner as runner
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
)


def run_failure(root, raw):
    source, span = _admit_fixture_source(root)
    fixture = FixtureCategoryGraphPassClient(
        _pass_outputs_for_span(_load_fixture(), span)
    )
    completed = []

    class Client:
        def run_pass(self, name, **kwargs):
            if name == "edge_pass":
                raise CategoryGraphExtractionError(
                    "synthetic edge JSON failure",
                    pass_name=name,
                    raw_model_response=raw,
                )
            result = fixture.run_pass(name, **kwargs)
            completed.append(name)
            return result

    result = runner.run_production_extraction(
        runner.ProductionExtractionRequest(
            repo_root=root,
            source=source,
            profile_id=WORLDBUILDING_PROFILE_ID,
            profile_version=WORLDBUILDING_PROFILE_VERSION,
            allow_llm=True,
            category_client=Client(),
            output_dir=root / "out/runs/failure",
        )
    )
    assert completed and result.run.status.value == "failed"
    assert result.candidate_graph is None
    assert "candidate_graph" not in result.run.components
    source_ref = result.run.components["source_artifact"]
    assert (
        root / source_ref.uri.removeprefix("repo://")
    ).read_text() == source.source_text
    return result


@pytest.mark.parametrize("raw", ["private returned source — 测试\n{bad json}", ""])
def test_registered_failure_retains_exact_private_response_and_fresh_read(
    tmp_path,
    application_state_dsn,
    raw,
):
    result = run_failure(tmp_path, raw)
    component = result.run.components["raw_model_response"]
    path = tmp_path / component.uri.removeprefix("repo://")
    assert path.read_bytes() == raw.encode()
    assert component.sha256 == hashlib.sha256(raw.encode()).hexdigest()
    assert component.exists and stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(path.parent.glob(".raw-response-*"))
    if raw:
        assert raw not in json.dumps(result.diagnostics)
    script = """
import hashlib,sys
from pathlib import Path
from apps.live_control_server.services.graph_run_registry import get_extraction_run
root=Path(sys.argv[1]); run=get_extraction_run(root,sys.argv[2])
assert run.status.value=='failed'
ref=run.components['raw_model_response']; path=root/ref.uri.removeprefix('repo://')
assert hashlib.sha256(path.read_bytes()).hexdigest()==ref.sha256==sys.argv[3]
print('private-failure-evidence-reopened')
"""
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            result.run.run_id,
            component.sha256,
        ],
        env=dict(os.environ),
        text=True,
        capture_output=True,
    )
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == "private-failure-evidence-reopened"


def test_no_raw_response_does_not_invent_evidence(tmp_path, application_state_dsn):
    result = run_failure(tmp_path, None)
    assert "raw_model_response" not in result.run.components
    assert not list((tmp_path / "out/runs/failure").rglob("raw_model_response.txt"))


def test_storage_failure_cannot_report_retention_or_return_candidate(
    tmp_path,
    application_state_dsn,
    monkeypatch,
):
    calls = []

    def unavailable(*args):
        calls.append(args)
        raise RuntimeError("Could not persist private extraction failure evidence")

    monkeypatch.setattr(runner, "_retain_raw_failure_response", unavailable)
    with pytest.raises(RuntimeError, match="persist private"):
        run_failure(tmp_path, "private body")
    assert len(calls) == 1
    assert not list((tmp_path / "out/runs/failure").rglob("candidate_graph.json"))


def test_writer_failure_is_controlled_and_never_echoes_body(tmp_path, monkeypatch):
    def unavailable(**kwargs):
        raise OSError("disk full synthetic")

    monkeypatch.setattr(runner.tempfile, "mkstemp", unavailable)
    with pytest.raises(RuntimeError, match="Could not persist private") as exc:
        runner._retain_raw_failure_response(tmp_path, tmp_path, "PRIVATE_BODY")
    assert "PRIVATE_BODY" not in str(exc.value)
