"""Real APP output/source storage owns semantic replay, not package files."""
import json
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from application_state.ingest import service as ingest
from application_state.ingest.components import get_component_bytes, persist_component_payload
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import recap_semantic_candidate_correction as correction
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from graph_memory.ingestion.extraction_run import ExtractionRunStatus as Status
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _stored_correction(root):
    _, result = _run_recap_extraction(root, client=FixtureClient())
    parent = result.run
    data = registry.load_reviewable_extraction_data(root, parent.run_id)
    payload = json.loads(data.candidate_bytes)
    node = payload["nodes"][0]
    manifest = {"schema": correction.MANIFEST_SCHEMA,
        "node_description_replacements": [{"node_id": node["node_id"],
            "original_description": node["description"],
            "replacement_description": "Mirathorn is a river city."}],
        "omitted_edge_ids": []}
    child_bytes = correction._canonical_bytes(correction.replay_candidate(payload, manifest))
    child_id = str(uuid4())
    refs = dict(parent.components)
    refs["candidate_graph"] = refs["candidate_graph"].model_copy(update={
        "uri": "historical:never-open-candidate", "sha256": correction._sha(child_bytes)})
    basis = ingest.RecapSemanticBasisV2(parent_run_id=parent.run_id,
        parent_candidate_sha256=correction._sha(data.candidate_bytes),
        manifest_sha256=correction._sha(correction._canonical_bytes(manifest)),
        child_run_id=child_id, candidate_uri=refs["candidate_graph"].uri,
        candidate_sha256=refs["candidate_graph"].sha256,
        source_artifact_id=parent.source_artifact_id,
        source_uri=refs["source_artifact"].uri,
        source_revision_sha256=refs["source_artifact"].sha256,
        span_index_uri=refs["source_span_index"].uri,
        span_index_sha256=refs["source_span_index"].sha256,
        profile_id=parent.profile_id, profile_version="1.0",
        campaign_id=parent.campaign_id, session_id=parent.session_id)
    child = registry.create_extraction_run(root, run_id=child_id,
        source_artifact_id=parent.source_artifact_id, source_domain=parent.source_domain,
        campaign_id=parent.campaign_id, session_id=parent.session_id,
        profile_id=parent.profile_id, status=Status.VALIDATED, components=refs,
        lineage={**parent.lineage, "derivation": correction.DERIVATION,
            "parent_run_id": parent.run_id, "parent_candidate_sha256": basis.parent_candidate_sha256,
            "manifest_sha256": basis.manifest_sha256, "semantic_candidate_manifest": manifest,
            "semantic_disposition": {"version": 1, "state": "held", "basis_sha256": basis.digest()}})
    for kind, value in (("candidate_graph", child_bytes), ("source_span_index", data.span_bytes)):
        persist_component_payload(run_id=child_id, expected_revision=child.revision, kind=kind, payload=value)
    child = registry.update_extraction_run_status(root, child_id, status=Status.REVIEWABLE, expected_revision=child.revision)
    return parent, child, basis


def test_replay_and_recorded_decision_survive_all_files_removed(monkeypatch, tmp_path):
    parent, child, basis = _stored_correction(tmp_path)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("semantic replay opened a locator file"))
    assert correction.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=basis.source_revision_sha256, root=tmp_path)
    assert assessment.basis_sha256 == basis.digest()
    assert not assessment.accepted
    decided = ingest.record_recap_semantic_disposition(child.run_id,
        expected_revision=child.revision, basis=basis,
        decision=ingest.RecapSemanticDispositionCommandV1(state="accepted",
            reviewer_id="synthetic:test-operator", review_decision_ref="synthetic:reviewed-description"))
    accepted = assess_recap_semantics(decided, parent=parent, source_revision_id=basis.source_revision_sha256, root=tmp_path)
    assert accepted.accepted and accepted.basis_sha256 == assessment.basis_sha256
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize("owner", ["parent", "child"])
@pytest.mark.parametrize("kind", ["candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_files_cannot_rescue_invalid_stored_replay(application_state_dsn, tmp_path, owner, kind, violation):
    parent, child, basis = _stored_correction(tmp_path)
    target = parent if owner == "parent" else child
    with psycopg.connect(application_state_dsn) as conn:
        if violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (target.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", target.run_id, kind))
    assert not correction.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=basis.source_revision_sha256, root=tmp_path)
    assert assessment.marked and not assessment.accepted and assessment.basis is None


def test_source_and_binding_drift_stay_closed(application_state_dsn, tmp_path):
    parent, child, _ = _stored_correction(tmp_path)
    refs = dict(child.components)
    refs["candidate_graph"] = refs["candidate_graph"].model_copy(update={"sha256": "a" * 64})
    assert not correction.verify_child_replay(child.model_copy(update={"components": refs}), parent, tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE source.revision SET markdown=%s WHERE source_artifact_id=%s", ("corrupt source", parent.source_artifact_id))
    assert not correction.verify_child_replay(child, parent, tmp_path)
    # Other stored output rows remain intact; no file repair or reseal occurs.
    ref = child.components["candidate_graph"]
    assert get_component_bytes(run_id=child.run_id, kind=ref.kind, content_sha256=ref.sha256)
