"""Actual held-child service persistence in a uniquely named disposable APP DB."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from application_state.cli import upgrade_to_head
from application_state.config import APPLICATION_STATE_DSN_ENV
from application_state.errors import ApplicationStateConflictError
from application_state.ingest import service as ingest
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequestV9, RecapCandidateCorrectionRequestV10,
)
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import recap_semantic_candidate_correction as correction
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from graph_memory.ingestion.extraction_run import ExtractionRunStatus
from tests.test_recap_semantic_candidate_correction import _append_fixture, _append_request


@pytest.fixture
def disposable_append_app(monkeypatch):
    admin = os.environ.get("DMB_RAKE_PG_ADMIN_DSN")
    if not admin:
        pytest.fail("DMB_RAKE_PG_ADMIN_DSN must designate disposable PostgreSQL administration")
    name = "dungeonbuddy_app_state_test_rake_append_" + uuid4().hex[:12]
    parts = urlsplit(admin)
    dsn = urlunsplit((parts.scheme, parts.netloc, "/" + name, parts.query, parts.fragment))
    try:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.Error as exc:
        pytest.fail("disposable database creation failed: " + type(exc).__name__)
    try:
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
        upgrade_to_head()  # Uses the checked-in Alembic head, including future compatible migrations.
        yield name
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def test_append_durable_child_fresh_read_retry_and_pc_proof(disposable_append_app, monkeypatch, tmp_path):
    original_get = registry.get_extraction_run
    original_create = registry.create_extraction_run
    original_update = registry.update_extraction_run_status
    parent, raw, _, pc_body, _, index = _append_fixture(monkeypatch, tmp_path)
    # Synthetic frozen source registry; the real registry/service validates scope and persists its bytes.
    source = (tmp_path / "source.md").read_text()
    record = {"schema_version": "dmb_source_artifact_v1", "source_artifact_id": parent.source_artifact_id,
              "source_domain": "recap", "campaign_id": "c", "session_id": "session-28",
              "uri": "repo://source.md", "content_sha256": pc_body["source_revision_sha256"],
              "artifact_kind": "recap_markdown", "document_class": "recap", "status": "active"}
    directory = tmp_path / "out/registries"
    directory.mkdir(parents=True)
    (directory / "source_artifacts.json").write_text(json.dumps({"schema_version": "dmb_source_artifact_registry_v1", "records": [record]}))
    from apps.live_control_server.services.source_artifact_registry import source_span_index_path
    span_path = source_span_index_path(tmp_path, parent.source_artifact_id)
    span_path.parent.mkdir(parents=True)
    span_path.write_bytes((tmp_path / "spans.json").read_bytes())
    monkeypatch.setattr(correction, "get_extraction_run", original_get)
    monkeypatch.setattr(correction, "create_extraction_run", original_create)
    monkeypatch.setattr(correction, "update_extraction_run_status", original_update)
    registered = original_create(tmp_path, run_id=parent.run_id, source_artifact_id=parent.source_artifact_id,
        source_domain="recap", campaign_id="c", session_id="session-28", profile_id=parent.profile_id,
        components=parent.components, status=ExtractionRunStatus.DRAFT)
    for state in correction._LIFECYCLE[1:]:
        registered = original_update(tmp_path, parent.run_id, status=state, expected_revision=registered.revision)
    assert registered.revision == pc_body["expected_parent_revision"]
    # Keep only the fixture's source-path resolver seam; all run persistence/read/CAS is real APP-STATE.
    def resolve(run_id, **kwargs):
        from types import SimpleNamespace
        run = original_get(tmp_path, run_id)
        return SimpleNamespace(run_id=run_id, source_domain="recap", extraction_profile=correction.PROFILE,
            campaign_id="c", session_id="session-28", source_artifact_id=parent.source_artifact_id,
            candidate_graph_path=tmp_path / run.components["candidate_graph"].uri,
            normalized_recap_path=tmp_path / "source.md", source_span_index_path=tmp_path / "spans.json",
            source_revision_id=pc_body["source_revision_sha256"])
    monkeypatch.setattr(correction, "resolve_promotable_ingest_run", resolve)
    pc_response = correction.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(pc_body))
    pc_parent = original_get(tmp_path, pc_response.run_id)
    pc_path = tmp_path / pc_parent.components["candidate_graph"].uri
    pc_bytes = pc_path.read_bytes()
    payload = json.loads(pc_bytes)
    body = _append_request(pc_parent, payload, index)
    second = _append_request(pc_parent, payload, index, kind="edge", identifier="edge-bridge", line=3)
    body["evidence_appends"].extend(second["evidence_appends"])
    response = correction.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(body))
    assert correction.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(body)) == response
    child = original_get(tmp_path, response.run_id)
    actual = json.loads((tmp_path / child.components["candidate_graph"].uri).read_bytes())
    for group in ("nodes", "edges"):
        assert actual[group][0]["evidence_refs"][:-1] == payload[group][0]["evidence_refs"]
    assert actual["nodes"][0]["corpus_ref"] == payload["nodes"][0]["corpus_ref"]
    assert pc_path.read_bytes() == pc_bytes and (tmp_path / "parent.json").read_bytes() == raw
    assert (tmp_path / "source.md").read_text() == source
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert len(ingest.list_extraction_runs()) == 3
    fresh_code = """
import json,sys
from pathlib import Path
from application_state.ingest.service import get_extraction_run
from apps.live_control_server.services.recap_semantic_candidate_correction import inherited_pc_reference_proof,verify_child_replay
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
root=Path(sys.argv[1]);child=get_extraction_run(sys.argv[2]);parent=get_extraction_run(sys.argv[3])
assert verify_child_replay(child,parent,root)
proof=inherited_pc_reference_proof(child,root)
assert proof==child.lineage['inherited_pc_proof'] and proof['rows'][0]['origin_run_id']==parent.run_id
assessment=assess_recap_semantics(child,parent=parent,source_revision_id=sys.argv[4],root=root)
assert assessment.marked and not assessment.accepted and assessment.basis['schema']=='dmb_recap_semantic_basis_v11'
print(json.dumps({'revision':child.revision,'state':child.lineage['semantic_disposition']['state'],'proof_origin':proof['rows'][0]['origin_run_id']}))
"""
    output = subprocess.check_output([sys.executable, "-c", fresh_code, str(tmp_path), child.run_id,
                                      pc_parent.run_id, body["source_revision_sha256"]], text=True)
    assert json.loads(output)["state"] == "held"
    assessment = assess_recap_semantics(child, parent=pc_parent, source_revision_id=body["source_revision_sha256"], root=tmp_path)
    basis = ingest.RecapSemanticBasisV11.model_validate(assessment.basis)
    # The actual APP CAS must reject a forged inherited proof, leaving the held child untouched.
    forged = basis.model_copy(update={"inherited_pc_proof_sha256": "0" * 64})
    with pytest.raises(ApplicationStateConflictError):
        ingest.record_recap_semantic_disposition(child.run_id, expected_revision=child.revision, basis=forged,
            decision=ingest.RecapSemanticDispositionCommandV1(state="accepted", reviewer_id="synthetic-reviewer", review_decision_ref="synthetic:reject-forged-proof"))
    for fault in ("parent", "source", "quote", "unknown", "existing", "preimage"):
        bad = copy.deepcopy(body)
        if fault == "parent":
            bad["expected_parent_revision"] += 1
        elif fault == "source":
            bad["source_revision_sha256"] = "0" * 64
        elif fault == "quote":
            bad["evidence_appends"][0]["anchor_quotes"] = ["forged quote"]
        elif fault == "unknown":
            bad["evidence_appends"][0]["record_id"] = "unknown"
        elif fault == "existing":
            bad["evidence_appends"][0].update(source_span_ref_id=index["spans"][0]["source_span_id"], anchor_quotes=["Mira found the key under the bridge."])
        else:
            bad["evidence_appends"][0]["expected_evidence_refs_sha256"] = "0" * 64
        with pytest.raises(correction.ExtractPromoteError):
            correction.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(bad))
        assert len(ingest.list_extraction_runs()) == 3
    assert original_get(tmp_path, child.run_id).revision == child.revision
    assert original_get(tmp_path, child.run_id).lineage["semantic_disposition"]["state"] == "held"
