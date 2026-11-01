"""Literal correction reads the exact stored parent, never its file mirrors."""
import json
from pathlib import Path

import psycopg
import pytest

from application_state.ingest import service as ingest
from apps.live_control_server.models.extract_promote import ExactRunEvidenceCorrectionRequest, ExactRunEvidenceQuoteCorrection
from apps.live_control_server.services import exact_run_evidence_correction as correction
from apps.live_control_server.services import extract_promote
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from tests._cutover_d3a_blocker_safe_fixtures import _reseal_extraction_component_digest
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _deny_artifact_io(monkeypatch, root):
    """The public correction operation may use DB owners, never artifact files."""
    import tempfile
    original_open, original_mkdir = Path.open, Path.mkdir
    def checked_open(path, *args, **kwargs):
        assert not path.is_relative_to(root), f"artifact file opened: {path}"
        return original_open(path, *args, **kwargs)
    def checked_mkdir(path, *args, **kwargs):
        assert not path.is_relative_to(root), f"artifact directory created: {path}"
        return original_mkdir(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(Path, "mkdir", checked_mkdir)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", lambda *a, **k: pytest.fail("artifact temporary file written"))


def _false_quote_parent(monkeypatch, root):
    _, result = _run_recap_extraction(root, client=FixtureClient())
    data = registry.load_reviewable_extraction_data(root, result.run.run_id)
    payload = json.loads(data.candidate_bytes)
    node = payload["nodes"][0]
    evidence = node["evidence_refs"][0]
    original = "Mirathorn was described in a nonexistent passage"
    evidence["anchor_quotes"][0] = original
    candidate = correction._canonical_bytes(payload)
    # Explicit synthetic fixture: reviewable bytes with a false literal quote
    # are inspectable inputs to the correction capability, never published facts.
    _reseal_extraction_component_digest(result.run.run_id, kind="candidate_graph",
        digest=correction._sha(candidate), payload=candidate)
    # Preserve a custom run-pinned index rather than recomputing the canonical
    # full-source index. Every fixture node cites this selected paragraph.
    index = json.loads(data.span_bytes)
    index["spans"] = [row for row in index["spans"] if row["source_span_id"] == evidence["source_span_ref_id"]]
    assert len(index["spans"]) == 1
    custom_spans = correction._canonical_bytes(index)
    assert custom_spans != data.span_bytes
    _reseal_extraction_component_digest(result.run.run_id, kind="source_span_index",
        digest=correction._sha(custom_spans), payload=custom_spans)
    parent = registry.get_extraction_run(root, result.run.run_id)
    (root / parent.components["candidate_graph"].uri.removeprefix("repo://")).write_bytes(candidate)
    (root / parent.components["source_span_index"].uri.removeprefix("repo://")).write_bytes(custom_spans)
    monkeypatch.setattr(correction, "repo_root", lambda: root)
    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: root)
    request = ExactRunEvidenceCorrectionRequest(parent_run_id=parent.run_id,
        parent_candidate_sha256=correction._sha(candidate), corrections=[ExactRunEvidenceQuoteCorrection(
            assertion_id=node["node_id"], evidence_index=0,
            source_span_ref_id=evidence["source_span_ref_id"], quote_index=0,
            original_quote=original, replacement_quote="Mirathorn")])
    return parent, request


def test_literal_correction_with_parent_files_removed(monkeypatch, tmp_path):
    parent, request = _false_quote_parent(monkeypatch, tmp_path)
    before_source = registry.load_reviewable_extraction_data(tmp_path, parent.run_id)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    _deny_artifact_io(monkeypatch, tmp_path)
    response = correction.correct_recap_run_evidence(request)
    assert response.semantic_state == "held"
    child = registry.load_reviewable_extraction_data(tmp_path, response.run_id)
    assert child.source_bytes == before_source.source_bytes
    assert child.span_bytes == before_source.span_bytes
    assert child.run.components["source_span_index"] == parent.components["source_span_index"]
    assert correction.correct_recap_run_evidence(request) == response
    assessment = assess_recap_semantics(child.run, parent=parent,
        source_revision_id=parent.components["source_artifact"].sha256)
    assert assessment.marked and not assessment.accepted
    assert assessment.basis_sha256 == response.semantic_basis_sha256
    review = extract_promote.get_exact_run_review_package(child.run.run_id)
    assert review.inspection_status == "ready" and not review.promotable
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_literal_correction_cannot_use_valid_files_to_rescue_bad_database(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    parent, request = _false_quote_parent(monkeypatch, tmp_path)
    before_rows = ingest.list_extraction_runs()
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (parent.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown=%s WHERE source_artifact_id=%s", ("corrupt", parent.source_artifact_id))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (parent.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", parent.run_id, kind))
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        correction.correct_recap_run_evidence(request)
    assert error.value.status_code == (500 if violation == "corrupt" and kind != "source_artifact" else 422)
    assert ingest.list_extraction_runs() == before_rows


def _check_child_storage_recovery(monkeypatch, root, dsn, parent, request, correct, kind, violation):
    from application_state.errors import ApplicationStateIntegrityError
    first = correct(request)
    child = registry.load_reviewable_extraction_data(root, first.run_id)
    payload = child.candidate_bytes if kind == "candidate_graph" else child.span_bytes
    ref = child.run.components[kind]
    # A valid old file is deliberately present; it grants no recovery authority.
    mirror = root / ref.uri.removeprefix("repo://")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_bytes(payload)
    before = ingest.list_extraction_runs()
    with psycopg.connect(dsn) as conn:
        if violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (first.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", first.run_id, kind))
    _deny_artifact_io(monkeypatch, root)
    if violation == "missing":
        # Existing owner permits exact referenced-byte restoration on explicit replay.
        assert correct(request) == first
        restored = registry.load_reviewable_extraction_data(root, first.run_id)
        assert restored.candidate_bytes == child.candidate_bytes
        assert restored.span_bytes == child.span_bytes
    else:
        with pytest.raises(ApplicationStateIntegrityError, match="stored extraction output differs"):
            correct(request)
    assert ingest.list_extraction_runs() == before
    assert registry.get_extraction_run(root, parent.run_id) == parent


@pytest.mark.parametrize("kind", ["candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_recap_child_payload_recovery_uses_only_database_owner(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    parent, request = _false_quote_parent(monkeypatch, tmp_path)
    _check_child_storage_recovery(monkeypatch, tmp_path, application_state_dsn, parent, request,
        correction.correct_recap_run_evidence, kind, violation)
