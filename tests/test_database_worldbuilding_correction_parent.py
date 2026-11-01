"""Worldbuilding correction and span catalog use exact stored run evidence."""
import json

import psycopg
import pytest

from application_state.ingest import service as ingest
from apps.live_control_server.models.extract_promote import (
    WorldbuildingEvidenceCorrectionRequest, WorldbuildingEvidenceRefCorrection,
    WorldbuildingEvidencePart, WorldbuildingEvidenceQuoteAssignment,
)
from apps.live_control_server.services import exact_run_evidence_correction as correction
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services.world_container_registry import create_world_container
from tests._cutover_d3a_blocker_safe_fixtures import _reseal_extraction_component_digest
from tests.test_worldbuilding_profile_pipeline import (
    _load_fixture, _pass_outputs_for_span, _run_with_pass_outputs,
)

from tests.test_database_literal_correction_parent import _deny_artifact_io, _check_child_storage_recovery
from tests.test_graph_preview_runner import _admit_worldbuilding, _first_paragraph_span_id
from graph_memory.source_span import build_stable_source_span_id

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _parent(monkeypatch, root):
    fixture = _load_fixture()
    world = create_world_container(root, name="Eldyrwild")
    source = _admit_worldbuilding(root, fixture["source_text"] + "\nAn unrelated second paragraph.\n")
    span_id = _first_paragraph_span_id(source)
    result = _run_with_pass_outputs(root, source=source,
        pass_outputs=_pass_outputs_for_span(fixture, span_id))
    assert result.failure_kind is None
    data = registry.load_reviewable_extraction_data(root, result.run.run_id)
    payload = json.loads(data.candidate_bytes)
    row = payload["nodes"][0]
    ref = row["evidence_refs"][0]
    replacement = ref["anchor_quotes"][0]
    ref["anchor_quotes"][0] = "A nonexistent sentence in this synthetic source."
    line_count = len(data.source_bytes.decode().splitlines())
    custom_span_id = build_stable_source_span_id(source_artifact_id=data.run.source_artifact_id,
        content_sha256=source.source_sha256, start_line=1, end_line=line_count)
    assert custom_span_id != span_id
    for node in [*payload["nodes"], *payload["edges"]]:
        for evidence in node["evidence_refs"]:
            assert evidence["source_span_ref_id"] == span_id
            evidence["source_span_ref_id"] = custom_span_id
    candidate = correction._canonical_bytes(payload)
    # Explicit test fixture: persist one inspectable false quote, not a fact.
    _reseal_extraction_component_digest(result.run.run_id, kind="candidate_graph",
        digest=correction._sha(candidate), payload=candidate)
    index = json.loads(data.span_bytes)
    index["spans"] = [span for span in index["spans"] if span["source_span_id"] == span_id]
    index["spans"][0]["source_span_id"] = custom_span_id
    index["spans"][0]["end_line"] = line_count
    spans = correction._canonical_bytes(index)
    assert spans != data.span_bytes
    _reseal_extraction_component_digest(result.run.run_id, kind="source_span_index",
        digest=correction._sha(spans), payload=spans)
    parent = registry.get_extraction_run(root, result.run.run_id)
    for kind, raw in (("candidate_graph", candidate), ("source_span_index", spans)):
        (root / parent.components[kind].uri.removeprefix("repo://")).write_bytes(raw)
    monkeypatch.setattr(correction, "repo_root", lambda: root)
    request = WorldbuildingEvidenceCorrectionRequest(
        parent_run_id=parent.run_id, expected_parent_revision=parent.revision,
        world_id=world.world_id, source_artifact_id=parent.source_artifact_id,
        source_sha256=correction._sha(data.source_bytes),
        span_index_sha256=correction._sha(spans), parent_candidate_sha256=correction._sha(candidate),
        corrections=[WorldbuildingEvidenceRefCorrection(assertion_id=row["node_id"], evidence_index=0,
            expected_ref_sha256=correction._sha(correction._canonical_bytes(ref)),
            parts=[WorldbuildingEvidencePart(source_span_ref_id=custom_span_id,
                quote_assignments=[WorldbuildingEvidenceQuoteAssignment(
                    original_quote_index=i, replacement_quote=replacement if i == 0 else quote)
                    for i, quote in enumerate(ref["anchor_quotes"])])])])
    return parent, request


def test_catalog_and_correction_without_parent_evidence_files(monkeypatch, tmp_path):
    parent, request = _parent(monkeypatch, tmp_path)
    expected = registry.load_reviewable_extraction_data(tmp_path, parent.run_id)
    # World and source ownership are database-backed; remove evidence mirrors.
    paths = {tmp_path / ref.uri.removeprefix("repo://") for ref in parent.components.values()}
    for path in paths:
        if path.is_file():
            path.unlink()
    _deny_artifact_io(monkeypatch, tmp_path)
    catalog = correction.get_worldbuilding_frozen_spans(parent.run_id)
    assert catalog.parent_candidate_sha256 == request.parent_candidate_sha256
    assert catalog.source_sha256 == request.source_sha256
    assert catalog.span_index_sha256 == request.span_index_sha256
    assert len(catalog.spans) == 1
    response = correction.correct_exact_run_evidence(request)
    child = registry.load_reviewable_extraction_data(tmp_path, response.run_id)
    assert child.run.status.value == "reviewable"
    assert child.span_bytes == expected.span_bytes
    assert child.source_bytes == expected.source_bytes
    assert child.run.components["source_span_index"] == parent.components["source_span_index"]
    assert correction.correct_exact_run_evidence(request) == response
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_valid_mirrors_cannot_rescue_bad_stored_evidence(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    parent, request = _parent(monkeypatch, tmp_path)
    before = ingest.list_extraction_runs()
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (parent.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (parent.source_artifact_id,))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (parent.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", parent.run_id, kind))
    for operation in (lambda: correction.get_worldbuilding_frozen_spans(parent.run_id),
                      lambda: correction.correct_exact_run_evidence(request)):
        with pytest.raises(correction.ExtractPromoteError) as error:
            operation()
        assert error.value.status_code == (500 if violation == "corrupt" and kind != "source_artifact" else 422)
    assert ingest.list_extraction_runs() == before


def test_managed_world_admission_still_required(monkeypatch, tmp_path):
    parent, request = _parent(monkeypatch, tmp_path)
    def reject(*_):
        raise ValueError("World not admitted")
    monkeypatch.setattr(correction, "admit_managed_world", reject)
    with pytest.raises(correction.ExtractPromoteError, match="managed World"):
        correction.correct_exact_run_evidence(request)
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize("kind", ["candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_worldbuilding_child_payload_recovery_uses_only_database_owner(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    parent, request = _parent(monkeypatch, tmp_path)
    _check_child_storage_recovery(monkeypatch, tmp_path, application_state_dsn, parent, request,
        correction.correct_exact_run_evidence, kind, violation)
