"""Lifecycle source binding belongs to stored bytes, not mirror layout."""
from pathlib import Path

import psycopg
import pytest

from apps.live_control_server.services import graph_run_registry as registry
from application_state.ingest.components import get_component_bytes, persist_component_payload
from graph_memory.ingestion.extraction_run import ExtractionRunStatus as Status
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _child(tmp_path):
    _, result = _run_recap_extraction(tmp_path, client=FixtureClient())
    parent = result.run
    refs = dict(parent.components)
    # Presentation-only locator deliberately bears no relation to the span file.
    refs["source_artifact"] = refs["source_artifact"].model_copy(update={"uri": "historical:do-not-open"})
    child = registry.create_extraction_run(tmp_path,
        source_artifact_id=parent.source_artifact_id, source_domain=parent.source_domain,
        campaign_id=parent.campaign_id, session_id=parent.session_id,
        profile_id=parent.profile_id, components=refs, status=Status.VALIDATED,
        lineage=parent.lineage)
    for key in ("candidate_graph", "source_span_index"):
        ref = refs[key]
        payload = get_component_bytes(run_id=parent.run_id, kind=key, content_sha256=ref.sha256)
        persist_component_payload(run_id=child.run_id, expected_revision=child.revision, kind=key, payload=payload)
    return parent, child


@pytest.mark.parametrize("mirror", ["deleted", "tampered"])
def test_child_lifecycle_ignores_source_mirrors(monkeypatch, tmp_path, mirror):
    parent, child = _child(tmp_path)
    for path in tmp_path.rglob("*.md"):
        if mirror == "deleted":
            path.unlink()
        else:
            path.write_text("not the registered input")
    original = Path.open
    def reject_source_open(path, *args, **kwargs):
        if path.suffix == ".md":
            pytest.fail("source mirrors must not control lifecycle")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", reject_source_open)
    sealed = registry.update_extraction_run_status(tmp_path, child.run_id,
        status=Status.REVIEWABLE, expected_revision=child.revision)
    assert registry.get_reviewable_extraction_run(tmp_path, child.run_id) == sealed
    assert registry.load_reviewable_extraction_data(tmp_path, child.run_id).source_bytes == b"Mirathorn is a river city.\n\nGuards watch the gate.\n"
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize("violation", ["missing_body", "corrupt_body", "component_digest", "campaign"])
def test_lifecycle_rejects_invalid_database_binding(application_state_dsn, tmp_path, violation):
    from tests._cutover_d3a_blocker_safe_fixtures import _patch_extraction_run, _reseal_extraction_component_digest

    _, child = _child(tmp_path)
    if violation in {"missing_body", "corrupt_body"}:
        with psycopg.connect(application_state_dsn) as conn:
            if violation == "missing_body":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (child.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown=%s WHERE source_artifact_id=%s", ("corrupt", child.source_artifact_id))
    elif violation == "component_digest":
        _reseal_extraction_component_digest(child.run_id, kind="source_artifact", digest="a" * 64)
    else:
        _patch_extraction_run(child.run_id, campaign_id="foreign-campaign")
    before = registry.get_extraction_run(tmp_path, child.run_id)
    with pytest.raises(registry.GraphRunRegistryError) as error:
        registry.update_extraction_run_status(tmp_path, child.run_id,
            status=Status.REVIEWABLE, expected_revision=before.revision)
    assert error.value.status_code == 422
    assert registry.get_extraction_run(tmp_path, child.run_id) == before
