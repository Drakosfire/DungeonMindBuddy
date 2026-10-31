"""Publication qualification consumes canonical evidence, not its file mirrors."""
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest

from apps.live_control_server.services import exact_run_evidence_correction as correction
from apps.live_control_server.services import extract_promote as publication
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
from tests.test_database_worldbuilding_correction_parent import _parent

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _case(monkeypatch, root):
    _, request = _parent(monkeypatch, root)
    child = correction.correct_exact_run_evidence(request)
    resolved = resolve_promotable_ingest_run(child.run_id, root=root)
    return resolved, registry.load_reviewable_extraction_data(root, child.run_id)


def test_qualification_uses_exact_custom_spans_without_any_evidence_files(monkeypatch, tmp_path):
    resolved, data = _case(monkeypatch, tmp_path)
    expected = publication._load_worldbuilding_publication_input(resolved)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *_a, **_k: pytest.fail("qualification opened a file"))
        actual = publication._load_worldbuilding_publication_input(resolved)
    assert actual == expected and actual.profile_id == data.run.profile_id
    assert actual.source_prose.encode() == data.source_bytes
    assert actual.span_index == data.span_index
    span_ids = {span.source_span_id for span in data.span_index.spans}
    assert len(span_ids) == 1
    assert {ref.source_span_ref_id for node in actual.preview.nodes for ref in node.evidence_refs} == span_ids
    assert registry.load_reviewable_extraction_data(tmp_path, data.run.run_id) == data


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_canonical_failure_cannot_fall_back_to_valid_files(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    resolved, data = _case(monkeypatch, tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (data.run.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (data.run.source_artifact_id,))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (data.run.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", data.run.run_id, kind))
    with pytest.raises(publication.ExtractPromoteError) as failure:
        publication._load_worldbuilding_publication_input(resolved)
    assert failure.value.status_code == (500 if violation == "corrupt" and kind != "source_artifact" else 422)
    assert registry.get_extraction_run(tmp_path, data.run.run_id) == data.run


@pytest.mark.parametrize("field,value", [
    ("source_revision_id", "sha256:" + "f" * 64), ("source_artifact_id", "foreign"),
    ("world_id", "another-world"), ("campaign_id", "another-campaign"),
])
def test_changed_resolved_binding_cannot_qualify_stored_run(monkeypatch, tmp_path, field, value):
    resolved, _ = _case(monkeypatch, tmp_path)
    with pytest.raises(publication.ExtractPromoteError) as failure:
        publication._load_worldbuilding_publication_input(replace(resolved, **{field: value}))
    assert failure.value.code == "run_scope_mismatch"
