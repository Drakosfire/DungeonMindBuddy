"""Lifecycle transitions verify actual stored outputs, never file mirrors."""
from pathlib import Path

import psycopg
import pytest

from apps.live_control_server.services import graph_run_registry as registry
from application_state.ingest.components import get_component_bytes
from graph_memory.ingestion.extraction_run import ExtractionRunStatus as Status
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction
from tests.test_database_run_source_evidence import _child

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.mark.parametrize("mode,expected", [("ok", Status.REVIEWABLE), ("schema", Status.FAILED)])
def test_controller_transitions_after_all_artifact_files_removed(monkeypatch, tmp_path, mode, expected):
    from src.graph_memory.extraction import graph_preview_runner as runner

    real = runner._advance_run
    removed = []
    def advance(root, run, *, status, **kwargs):
        if status == expected:
            for path in tmp_path.rglob("*"):
                if path.is_file():
                    path.unlink()
            removed.append(status)
            with monkeypatch.context() as context:
                context.setattr(Path, "open", lambda *a, **k: pytest.fail("transition opened a file mirror"))
                return real(root, run, status=status, **kwargs)
        return real(root, run, status=status, **kwargs)
    monkeypatch.setattr(runner, "_advance_run", advance)
    class Client(FixtureClient):
        def run_pass(self, pass_name, **kwargs):
            if mode == "schema":
                from src.graph_memory.extraction.category_candidate_graph_extractor import CategoryGraphExtractionError
                raise CategoryGraphExtractionError("schema failure", pass_name=pass_name,
                    raw_model_response="actual captured invalid JSON — 测试")
            return super().run_pass(pass_name, **kwargs)
    _, result = _run_recap_extraction(tmp_path, client=Client(mode=mode))
    assert removed == [expected]
    assert result.run.status == expected
    for key, ref in result.run.components.items():
        if key != "source_artifact":
            assert get_component_bytes(run_id=result.run.run_id, kind=key, content_sha256=ref.sha256)
    if mode == "schema":
        ref = result.run.components["raw_model_response"]
        assert get_component_bytes(run_id=result.run.run_id, kind=ref.kind, content_sha256=ref.sha256) == "actual captured invalid JSON — 测试".encode()
        assert result.failure_kind == "schema"
        assert any("schema failure" in message for message in result.run.diagnostics.errors)
    else:
        assert registry.load_reviewable_extraction_data(tmp_path, result.run.run_id).candidate_bytes


@pytest.mark.parametrize("kind", ["candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_valid_files_cannot_rescue_bad_database_output(application_state_dsn, tmp_path, kind, violation):
    _, child = _child(tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        if violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (child.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", child.run_id, kind))
    with pytest.raises(registry.GraphRunRegistryError) as error:
        registry.update_extraction_run_status(tmp_path, child.run_id, status=Status.REVIEWABLE, expected_revision=child.revision)
    assert error.value.status_code == (422 if violation == "missing" else 500)
    assert registry.get_extraction_run(tmp_path, child.run_id) == child


def test_direct_reviewable_construction_and_successor_are_rejected(tmp_path):
    parent, child = _child(tmp_path)
    with pytest.raises(registry.GraphRunRegistryError, match="staged run"):
        registry.create_extraction_run(tmp_path, source_artifact_id=parent.source_artifact_id, source_domain=parent.source_domain, status=Status.REVIEWABLE, components=parent.components)
    with pytest.raises(registry.GraphRunRegistryError, match="staged successor"):
        registry.supersede_extraction_run(tmp_path, child.run_id, expected_revision=child.revision, status=Status.REVIEWABLE, components=child.components)
    assert registry.get_extraction_run(tmp_path, child.run_id) == child
