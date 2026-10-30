"""Owning PostgreSQL boundary for immutable run output bytes, not Graph authority."""
from uuid import uuid4
import hashlib

import psycopg
import pytest

from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError, ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.ingest import components, service
from graph_memory.ingestion.extraction_run import ExtractionRun, ExtractionRunComponentRef, ExtractionRunComponentKind as Kind, ExtractionRunStatus as Status

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def run_with(*, payload=None, status=Status.DRAFT):
    refs = {}
    if payload is not None:
        digest = hashlib.sha256(payload).hexdigest()
        for kind in (Kind.SOURCE_ARTIFACT, Kind.SOURCE_SPAN_INDEX, Kind.CANDIDATE_GRAPH):
            refs[kind.value] = ExtractionRunComponentRef(kind=kind, uri="historical:never-open", sha256=digest, exists=True)
    return service.create_extraction_run(ExtractionRun(run_id=str(uuid4()), source_artifact_id="source:input", source_domain="worldbuilding", status=status, components=refs))


def test_staged_bytes_confer_no_run_binding_or_review_authority():
    run = run_with()
    payload = b'{"nodes": []}\n'
    digest = components.persist_component_payload(run_id=run.run_id, expected_revision=run.revision, kind=Kind.CANDIDATE_GRAPH, payload=payload)
    assert service.get_extraction_run(run.run_id) == run
    with pytest.raises(ApplicationStateConflictError, match="run binding"):
        components.get_component_bytes(run_id=run.run_id, kind=Kind.CANDIDATE_GRAPH, content_sha256=digest)


def test_frozen_exact_restoration_replay_and_conflict(application_state_dsn):
    payload = b'{"nodes": []}\n'
    run = run_with(payload=payload, status=Status.REVIEWABLE)
    options = dict(run_id=run.run_id, expected_revision=run.revision, kind=Kind.CANDIDATE_GRAPH)
    first = components.persist_component_payload(**options, payload=payload)
    assert components.persist_component_payload(**options, payload=payload) == first
    assert components.get_component_bytes(run_id=run.run_id, kind=Kind.CANDIDATE_GRAPH, content_sha256=first) == payload
    with pytest.raises(ApplicationStateConflictError, match="frozen"):
        components.persist_component_payload(**options, payload=b"different")
    assert service.get_extraction_run(run.run_id) == run
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ingest.component_payload").fetchone()[0] == 1


def test_missing_payload_never_uses_locator(tmp_path):
    payload = b"valid file payload"
    (tmp_path / "candidate.json").write_bytes(payload)
    run = run_with(payload=payload)
    with pytest.raises(ApplicationStateNotFoundError, match="not durable"):
        components.get_component_bytes(run_id=run.run_id, kind=Kind.CANDIDATE_GRAPH, content_sha256=hashlib.sha256(payload).hexdigest())


def test_corruption_fails_closed(application_state_dsn):
    payload = b"exact"
    run = run_with(payload=payload)
    digest = components.persist_component_payload(run_id=run.run_id, expected_revision=1, kind=Kind.CANDIDATE_GRAPH, payload=payload)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s", (b"corrupt", run.run_id))
    with pytest.raises(ApplicationStateIntegrityError, match="digest mismatch"):
        components.get_component_bytes(run_id=run.run_id, kind=Kind.CANDIDATE_GRAPH, content_sha256=digest)
    with pytest.raises(ApplicationStateIntegrityError, match="differs"):
        components.persist_component_payload(run_id=run.run_id, expected_revision=1, kind=Kind.CANDIDATE_GRAPH, payload=payload)


def test_run_revision_and_owner_boundaries():
    run = run_with()
    with pytest.raises(ApplicationStateConflictError, match="run changed"):
        components.persist_component_payload(run_id=run.run_id, expected_revision=2, kind=Kind.CANDIDATE_GRAPH, payload=b"x")
    with pytest.raises(ApplicationStateValidationError, match="source store"):
        components.persist_component_payload(run_id=run.run_id, expected_revision=1, kind=Kind.SOURCE_ARTIFACT, payload=b"x")
    with pytest.raises(ApplicationStateNotFoundError, match="run not found"):
        components.persist_component_payload(run_id="missing", expected_revision=1, kind=Kind.CANDIDATE_GRAPH, payload=b"x")


def test_native_source_only_run_cannot_use_generic_output_store(application_state_dsn):
    run = run_with()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.run SET lineage=%s::jsonb WHERE run_id=%s", ('{"native_recap_source": {}}', run.run_id))
    with pytest.raises(ApplicationStateConflictError, match="source-only"):
        components.persist_component_payload(run_id=run.run_id, expected_revision=1, kind=Kind.CANDIDATE_GRAPH, payload=b"x")
    with pytest.raises(ApplicationStateConflictError, match="source-only"):
        components.get_component_bytes(run_id=run.run_id, kind=Kind.CANDIDATE_GRAPH, content_sha256=hashlib.sha256(b"x").hexdigest())
