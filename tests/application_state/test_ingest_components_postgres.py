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


def test_transition_verification_is_revision_fenced_without_binding():
    run = run_with()
    payload = b"staged failed response"
    digest = components.persist_component_payload(run_id=run.run_id, expected_revision=1, kind=Kind.RAW_MODEL_RESPONSE, payload=payload)
    options = dict(run_id=run.run_id, kind=Kind.RAW_MODEL_RESPONSE, content_sha256=digest)
    assert components.verify_transition_component_bytes(expected_revision=1, **options) == payload
    assert service.get_extraction_run(run.run_id) == run
    with pytest.raises(ApplicationStateConflictError, match="run binding"):
        components.get_component_bytes(**options)
    with pytest.raises(ApplicationStateConflictError, match="changed"):
        components.verify_transition_component_bytes(expected_revision=2, **options)


def test_transition_verification_missing_and_corrupt_bytes(application_state_dsn):
    run = run_with()
    payload = b"exact"
    digest = hashlib.sha256(payload).hexdigest()
    options = dict(run_id=run.run_id, expected_revision=1, kind=Kind.CANDIDATE_GRAPH, content_sha256=digest)
    with pytest.raises(ApplicationStateNotFoundError, match="not durable"):
        components.verify_transition_component_bytes(**options)
    components.persist_component_payload(run_id=run.run_id, expected_revision=1, kind=Kind.CANDIDATE_GRAPH, payload=payload)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s", (b"corrupt", run.run_id))
    with pytest.raises(ApplicationStateIntegrityError, match="digest mismatch"):
        components.verify_transition_component_bytes(**options)


def test_transition_verification_frozen_owner_and_source_boundaries(application_state_dsn):
    run = run_with(payload=b"bound", status=Status.REVIEWABLE)
    other = b"unbound"
    digest = hashlib.sha256(other).hexdigest()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("INSERT INTO ingest.component_payload (run_id,kind,content_sha256,payload) VALUES (%s,%s,%s,%s)", (run.run_id, Kind.CANDIDATE_GRAPH.value, digest, other))
    options = dict(run_id=run.run_id, expected_revision=1, kind=Kind.CANDIDATE_GRAPH, content_sha256=digest)
    with pytest.raises(ApplicationStateConflictError, match="frozen"):
        components.verify_transition_component_bytes(**options)
    with pytest.raises(ApplicationStateValidationError, match="source store"):
        components.verify_transition_component_bytes(**{**options, "kind": Kind.SOURCE_ARTIFACT})
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.run SET lineage=%s::jsonb WHERE run_id=%s", ('{"native_recap_source": {}}', run.run_id))
    with pytest.raises(ApplicationStateConflictError, match="source-only"):
        components.verify_transition_component_bytes(**options)


# These tests exercise the same immutable table, run lock and public bound reader.
def prepared_execution(*, model_id="synthetic-model", source_sha256=None):
    run = service.create_extraction_run(ExtractionRun(
        run_id=str(uuid4()), source_artifact_id="source:execution-input",
        source_domain="recap", campaign_id="synthetic", session_id="session-1",
        status=Status.PREPARED, profile_id="recap_fixture@1",
        lineage={"model_id": model_id},
        components={"source_artifact": ExtractionRunComponentRef(
            kind=Kind.SOURCE_ARTIFACT, uri="urn:fixture-source",
            sha256=source_sha256 or hashlib.sha256(b"source").hexdigest(), exists=True,
        )},
    ))
    return run, components.execution_evidence_binding(
        run_id=run.run_id, expected_revision=run.revision,
    )


def execution_event(binding, *, capture_id="attempt:1:event:1", text="private response"):
    import json
    return json.dumps({
        "execution_binding": binding, "capture_id": capture_id,
        "schema": "dmb_private_recap_attempt_response_v1", "response": {"text": text},
    }, sort_keys=True).encode()


def test_execution_capture_is_committed_idempotent_and_not_publicly_bound():
    run, binding = prepared_execution()
    raw = execution_event(binding)
    options = dict(binding=binding, kind=Kind.RAW_MODEL_RESPONSE, payload=raw)
    digest = components.persist_execution_event(**options)
    assert components.persist_execution_event(**options) == digest
    rows = components.list_private_execution_events(binding=binding, expected_revision=run.revision)
    assert [(r["sha256"], r["payload"]) for r in rows] == [(digest, raw)]
    assert service.get_extraction_run(run.run_id) == run
    with pytest.raises(ApplicationStateConflictError, match="run binding"):
        components.get_component_bytes(run_id=run.run_id, kind=Kind.RAW_MODEL_RESPONSE, content_sha256=digest)
    with pytest.raises(ApplicationStateConflictError, match="contradictory"):
        components.persist_execution_event(**{**options, "payload": execution_event(binding, text="different")})


def test_concurrent_execution_identity_replay_has_one_committed_value():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    run, binding = prepared_execution()
    barrier = Barrier(2)

    def capture(text):
        barrier.wait(timeout=10)
        try:
            return components.persist_execution_event(
                binding=binding, kind=Kind.RAW_MODEL_RESPONSE,
                payload=execution_event(binding, text=text),
            )
        except ApplicationStateConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(capture, ["first", "second"]))
    assert results.count("conflict") == 1
    assert len(components.list_private_execution_events(binding=binding, expected_revision=run.revision)) == 1


@pytest.mark.parametrize("field,value", [
    ("prepared_revision", 99), ("source_artifact_id", "source:foreign"),
    ("source_sha256", "f" * 64), ("profile_id", "foreign@1"),
    ("model_id", "foreign-model"), ("run_id", "missing"),
])
def test_execution_binding_substitution_refuses_before_capture(field, value):
    run, binding = prepared_execution()
    changed = {**binding, field: value}
    with pytest.raises((ApplicationStateConflictError, ApplicationStateNotFoundError)):
        components.persist_execution_event(
            binding=changed, kind=Kind.RAW_MODEL_RESPONSE, payload=execution_event(changed),
        )
    assert components.list_private_execution_events(binding=binding, expected_revision=run.revision) == []


def test_incomplete_private_recovery_fences_writes_and_current_revision():
    run, binding = prepared_execution()
    raw = execution_event(binding)
    components.persist_execution_event(binding=binding, kind=Kind.RAW_MODEL_RESPONSE, payload=raw)
    incomplete = service.update_extraction_run(run.run_id, expected_revision=run.revision, status=Status.INCOMPLETE)
    assert components.list_private_execution_events(binding=binding, expected_revision=incomplete.revision)[0]["payload"] == raw
    with pytest.raises(ApplicationStateConflictError, match="revision changed"):
        components.list_private_execution_events(binding=binding, expected_revision=run.revision)
    with pytest.raises(ApplicationStateConflictError):
        components.persist_execution_event(binding=binding, kind=Kind.RAW_MODEL_RESPONSE, payload=raw)


def test_frozen_execution_requires_final_public_binding():
    run, binding = prepared_execution()
    raw = execution_event(binding)
    digest = components.persist_execution_event(binding=binding, kind=Kind.RAW_MODEL_RESPONSE, payload=raw)
    frozen = service.update_extraction_run(
        run.run_id, expected_revision=run.revision, status=Status.FAILED,
        components={**run.components, "raw_model_response": ExtractionRunComponentRef(
            kind=Kind.RAW_MODEL_RESPONSE, uri="urn:fixture-private-output", sha256=digest, exists=True,
        )},
    )
    with pytest.raises(ApplicationStateConflictError, match="frozen"):
        components.list_private_execution_events(binding=binding, expected_revision=frozen.revision)
    assert components.get_component_bytes(run_id=run.run_id, kind=Kind.RAW_MODEL_RESPONSE, content_sha256=digest) == raw


def test_native_source_only_execution_binding_and_capture_refused(application_state_dsn):
    from psycopg.types.json import Jsonb
    run, binding = prepared_execution()
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.run SET lineage=%s WHERE run_id=%s", (Jsonb({**run.lineage, "native_recap_source": {}}), run.run_id))
    with pytest.raises(ApplicationStateConflictError, match="source-only"):
        components.execution_evidence_binding(run_id=run.run_id, expected_revision=run.revision)
    with pytest.raises(ApplicationStateConflictError, match="source-only"):
        components.persist_execution_event(binding=binding, kind=Kind.RAW_MODEL_RESPONSE, payload=execution_event(binding))
