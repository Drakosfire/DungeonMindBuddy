"""The Recap execution boundary consumes exact registered DB input, not files or pages."""
from dataclasses import replace

import pytest

from apps.live_control_server.services import graph_preview_runner as runner
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError, create_recap_source_artifact,
)
from tests.test_bounded_recap_execution import _fixture_ingest_context
from tests.test_graph_preview_runner import FixtureClient, _first_paragraph_span_id
from tests.test_recap_managed_standing_context import seed_binding

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.fixture
def registered(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    seed_binding(tmp_path, "managed-fixture-world", "world:synthetic")
    original = tmp_path / "import.md"
    original.write_text("A keeper guards a gate.\n")
    artifact = create_recap_source_artifact(tmp_path, world_id="world:synthetic",
        campaign_id="synthetic", session_id="session-1", recap_path=original)
    original.unlink()
    return artifact


def test_registered_corpus_reaches_extraction_without_build_or_import_file(tmp_path, registered):
    source = runner._normalized_from_registered(tmp_path, registered.source_artifact_id)
    result = runner.run_recap_production_extraction(repo_root=tmp_path,
        source_artifact_id=registered.source_artifact_id, campaign_id="synthetic",
        session_id="session-1", ingest_context=_fixture_ingest_context("synthetic"),
        profile="category_baseline", category_client=FixtureClient(span_ref=_first_paragraph_span_id(source)))
    assert result.failure_kind is None, result.diagnostics
    assert result.run.status.value == "reviewable"
    assert result.run.source_artifact_id == registered.source_artifact_id
    assert "build_document_ingest" not in result.run.lineage
    assert not (tmp_path / "import.md").exists()
    assert not registered.workspace_document_id


@pytest.mark.parametrize("mismatch", ["world", "campaign", "session"])
def test_wrong_selected_scope_stops_before_output_or_dispatch(tmp_path, registered, monkeypatch, mismatch):
    context = _fixture_ingest_context("synthetic")
    campaign, session = "synthetic", "session-1"
    if mismatch == "world":
        context = replace(context, native_world_id="other-world")
    elif mismatch == "campaign":
        campaign = "other-campaign"
        context = replace(context, campaign_id=campaign)
    else:
        session = "session-2"
    monkeypatch.setattr(runner, "run_production_extraction", lambda *a, **k: pytest.fail("must not dispatch"))
    monkeypatch.setattr(runner, "_standing_corpus_root", lambda *a: pytest.fail("source mismatch must precede directory context"))
    with pytest.raises(SourceArtifactRegistryError, match="does not match"):
        runner.run_recap_production_extraction(repo_root=tmp_path,
            source_artifact_id=registered.source_artifact_id, campaign_id=campaign,
            session_id=session, ingest_context=context, output_dir=tmp_path / "new-run")
    assert not (tmp_path / "new-run").exists()


def test_missing_database_source_has_no_file_fallback(tmp_path, registered, monkeypatch):
    (tmp_path / "import.md").write_text("A keeper guards a gate.\n")
    monkeypatch.setattr(runner, "run_production_extraction", lambda *a, **k: pytest.fail("must not dispatch"))
    with pytest.raises(SourceArtifactRegistryError, match="not registered in database"):
        runner.run_recap_production_extraction(repo_root=tmp_path, source_artifact_id="absent",
            campaign_id="synthetic", session_id="session-1", ingest_context=_fixture_ingest_context("synthetic"))


def test_explicit_import_hands_registered_identity_to_same_runner(tmp_path, registered, monkeypatch):
    from apps.live_control_server.services import recap_graph_preview_ingest as intake
    source_file = tmp_path / "explicit-import.md"
    source_file.write_text("A keeper guards a gate.\n")
    actual = runner.run_recap_production_extraction
    def execute(**kwargs):
        assert "recap_path" not in kwargs and "build_source_artifact_id" not in kwargs
        source = runner._normalized_from_registered(tmp_path, kwargs["source_artifact_id"])
        source_file.unlink()
        kwargs["category_client"] = FixtureClient(span_ref=_first_paragraph_span_id(source))
        return actual(**kwargs)
    monkeypatch.setattr(intake, "run_recap_production_extraction", execute)
    result = intake.extract_recap(repo_root=tmp_path, campaign_id="synthetic", session=1,
        normalized_recap_path=str(source_file), force_graph_run=True,
        ingest_context=_fixture_ingest_context("synthetic"))
    assert result["status"] == "candidate_validation_ready"
    assert result["source_artifact_id"] == registered.source_artifact_id
    assert not source_file.exists()


def test_import_change_between_selection_and_registration_stops_dispatch(tmp_path, registered, monkeypatch):
    from apps.live_control_server.services import recap_graph_preview_ingest as intake
    source_file = tmp_path / "changing-import.md"
    source_file.write_text("A keeper guards a gate.\n")
    actual = intake.create_recap_source_artifact
    def changed(*args, **kwargs):
        source_file.write_text("Different source bytes.\n")
        return actual(*args, **kwargs)
    monkeypatch.setattr(intake, "create_recap_source_artifact", changed)
    monkeypatch.setattr(intake, "run_recap_production_extraction", lambda **k: pytest.fail("must not dispatch"))
    with pytest.raises(SourceArtifactRegistryError, match="does not match recap source bytes"):
        intake.extract_recap(repo_root=tmp_path, campaign_id="synthetic", session=1,
            normalized_recap_path=str(source_file), force_graph_run=True,
            ingest_context=_fixture_ingest_context("synthetic"))
