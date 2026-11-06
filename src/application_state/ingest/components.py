"""Immutable extraction output storage. Source bodies remain with source owner."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from contextlib import contextmanager

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError, ApplicationStateIntegrityError,
    ApplicationStateNotFoundError, ApplicationStateValidationError,
)
from application_state.ingest import repository
from application_state.unit_of_work import unit_of_work
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind, ExtractionRunStatus, FROZEN_COMPONENT_STATUSES, normalize_content_digest,
)


def _output_kind(kind: ExtractionRunComponentKind | str) -> ExtractionRunComponentKind:
    try:
        value = ExtractionRunComponentKind(kind)
    except ValueError as exc:
        raise ApplicationStateValidationError("unknown extraction output kind") from exc
    if value == ExtractionRunComponentKind.SOURCE_ARTIFACT:
        raise ApplicationStateValidationError("source bodies belong to the source store")
    return value


def _require_output_owner(run) -> None:
    if "native_recap_source" in run.lineage or run.profile_id == "fresh_recap_native_source_v1":
        raise ApplicationStateConflictError("native source-only runs do not own generic extraction outputs")


def persist_component_payload(*, run_id: str, expected_revision: int,
                              kind: ExtractionRunComponentKind | str, payload: bytes) -> str:
    """Store actual producer bytes, never read a locator or replace a hash claim.

    Staged bytes confer no review/publication authority. Frozen runs permit only
    exact referenced-byte restoration/replay, without changing run metadata.
    """
    kind = _output_kind(kind)
    if not isinstance(payload, bytes):
        raise ApplicationStateValidationError("extraction output must be exact bytes")
    digest = hashlib.sha256(payload).hexdigest()
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SELECT run_id FROM ingest.run WHERE run_id=%s FOR UPDATE", (run_id,))
        run = repository.get_run(conn, run_id)
        if run is None:
            raise ApplicationStateNotFoundError("extraction run not found")
        _require_output_owner(run)
        if run.revision != expected_revision:
            raise ApplicationStateConflictError("extraction run changed before output persistence")
        if run.status in FROZEN_COMPONENT_STATUSES:
            ref = run.components.get(kind.value)
            if ref is None or normalize_content_digest(ref.sha256) != digest:
                raise ApplicationStateConflictError("frozen extraction output binding cannot change")
        _persist_payload(conn, run_id=run_id, kind=kind, digest=digest, payload=payload)
    return digest



def _persist_payload(conn, *, run_id, kind, digest, payload):
    existing = conn.execute(
        "SELECT payload FROM ingest.component_payload WHERE run_id=%s AND kind=%s AND content_sha256=%s",
        (run_id, kind.value, digest),
    ).fetchone()
    if existing is not None:
        if bytes(existing[0]) != payload:
            raise ApplicationStateIntegrityError("stored extraction output differs from its immutable digest")
        return digest
    conn.execute(
        "INSERT INTO ingest.component_payload (run_id, kind, content_sha256, payload) VALUES (%s,%s,%s,%s)",
        (run_id, kind.value, digest, payload),
    )


_EXECUTION_KINDS = frozenset({
    ExtractionRunComponentKind.RAW_MODEL_RESPONSE,
    ExtractionRunComponentKind.PASS_TELEMETRY,
})


def _binding_for(run, *, prepared_revision: int) -> dict:
    _require_output_owner(run)
    source = run.components.get("source_artifact")
    if (source is None or not source.exists or not run.profile_id
            or not isinstance(run.lineage.get("model_id"), str)):
        raise ApplicationStateIntegrityError("execution requires prepared source/profile/model bindings")
    return {
        "run_id": run.run_id,
        "prepared_revision": prepared_revision,
        "source_artifact_id": run.source_artifact_id,
        "source_sha256": _output_digest(source.sha256),
        "profile_id": run.profile_id,
        "model_id": run.lineage["model_id"],
    }


def _execution_run(conn, binding, *, expected_revision: int, writing: bool):
    if (not isinstance(binding, Mapping)
            or type(binding.get("prepared_revision")) is not int
            or binding["prepared_revision"] < 1):
        raise ApplicationStateValidationError("exact prepared execution binding is required")
    run = repository.get_run(conn, binding.get("run_id"))
    if run is None:
        raise ApplicationStateNotFoundError("extraction run not found")
    _require_output_owner(run)
    if run.revision != expected_revision:
        raise ApplicationStateConflictError("execution run revision changed")
    if (run.status in FROZEN_COMPONENT_STATUSES
            or binding != _binding_for(run, prepared_revision=binding["prepared_revision"])
            or binding["prepared_revision"] > run.revision):
        raise ApplicationStateConflictError("execution evidence binding changed or is frozen")
    if writing and (run.status != ExtractionRunStatus.PREPARED
                    or run.revision != binding["prepared_revision"]):
        raise ApplicationStateConflictError("execution capture requires the exact prepared revision")
    return run


def execution_evidence_binding(*, run_id: str, expected_revision: int) -> dict:
    """Bind the real PREPARED owner before dispatch; never reserve a second run."""
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        run = repository.get_run(conn, run_id)
        if run is None:
            raise ApplicationStateNotFoundError("extraction run not found")
        if run.status != ExtractionRunStatus.PREPARED or run.revision != expected_revision:
            raise ApplicationStateConflictError("execution capture requires the exact prepared revision")
        return _binding_for(run, prepared_revision=run.revision)


def _execution_records(conn, binding) -> list[dict]:
    rows = conn.execute(
        "SELECT kind,content_sha256,payload FROM ingest.component_payload "
        "WHERE run_id=%s AND kind IN ('raw_model_response','pass_telemetry') "
        "ORDER BY kind,content_sha256", (binding["run_id"],),
    ).fetchall()
    records = []
    for kind, digest, value in rows:
        raw = bytes(value)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ApplicationStateIntegrityError("stored execution evidence digest mismatch")
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, ValueError):
            continue  # Other private component bodies are not execution events.
        if not isinstance(record, dict) or "execution_binding" not in record:
            continue
        recorded = record["execution_binding"]
        if not isinstance(recorded, dict) or recorded.get("run_id") != binding["run_id"]:
            raise ApplicationStateIntegrityError("stored execution event belongs to another run")
        if recorded.get("prepared_revision") != binding["prepared_revision"]:
            continue  # A different explicit execution revision grants no authority here.
        if recorded != binding or not isinstance(record.get("capture_id"), str):
            raise ApplicationStateIntegrityError("stored execution event binding is invalid")
        records.append({"kind": kind, "sha256": digest, "record": record, "payload": raw})
    return records


def persist_execution_event(*, binding: Mapping, kind: ExtractionRunComponentKind | str,
                            payload: bytes) -> str:
    """Commit private exact-revision capture, including atomic identity replay.

    The existing run lock serializes event-ID validation and insertion. This is
    component staging, never a run transition, review or publication authority.
    """
    kind = _output_kind(kind)
    if not isinstance(binding, Mapping):
        raise ApplicationStateValidationError("exact prepared execution binding is required")
    try:
        record = json.loads(payload)
    except (TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ApplicationStateValidationError("execution event must be exact JSON bytes") from exc
    if (kind not in _EXECUTION_KINDS or not isinstance(payload, bytes)
            or not isinstance(record, dict) or record.get("execution_binding") != binding
            or not isinstance(record.get("capture_id"), str) or not record["capture_id"]):
        raise ApplicationStateValidationError("invalid private execution event")
    digest = hashlib.sha256(payload).hexdigest()
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SELECT run_id FROM ingest.run WHERE run_id=%s FOR UPDATE", (binding.get("run_id"),))
        _execution_run(conn, binding, expected_revision=binding["prepared_revision"], writing=True)
        for prior in _execution_records(conn, binding):
            if prior["record"]["capture_id"] == record["capture_id"]:
                if prior["kind"] != kind.value or prior["payload"] != payload:
                    raise ApplicationStateConflictError("execution event identity has contradictory bytes")
                return digest
        _persist_payload(conn, run_id=binding["run_id"], kind=kind, digest=digest, payload=payload)
    return digest


def list_private_execution_events(*, binding: Mapping, expected_revision: int) -> list[dict]:
    """Recover only committed events for one exact execution and current run.

    INCOMPLETE reconciliation can inspect its retained PREPARED generation. Frozen
    readers must use the final bound bundle through get_component_bytes instead.
    This private operation is not exposed by any HTTP/public output reader.
    """
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        _execution_run(conn, binding, expected_revision=expected_revision, writing=False)
        return _execution_records(conn, binding)

def get_component_bytes(*, run_id: str, kind: ExtractionRunComponentKind | str,
                        content_sha256: str) -> bytes:
    """Open one current exact run binding and verify bytes, with no file fallback."""
    kind = _output_kind(kind)
    digest = _output_digest(content_sha256)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        run = repository.get_run(conn, run_id)
        if run is None:
            raise ApplicationStateNotFoundError("extraction run not found")
        _require_output_owner(run)
        ref = run.components.get(kind.value)
        if ref is None or normalize_content_digest(ref.sha256) != digest:
            raise ApplicationStateConflictError("requested output differs from the extraction run binding")
        return _verified_payload_bytes(conn, run_id=run_id, kind=kind, digest=digest)


def _output_digest(content_sha256: str) -> str:
    digest = normalize_content_digest(content_sha256)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ApplicationStateValidationError("exact output SHA-256 is required")
    return digest


def _verified_payload_bytes(conn, *, run_id: str, kind: ExtractionRunComponentKind, digest: str) -> bytes:
    row = conn.execute(
        "SELECT payload FROM ingest.component_payload WHERE run_id=%s AND kind=%s AND content_sha256=%s",
        (run_id, kind.value, digest),
    ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("referenced extraction output is not durable")
    data = bytes(row[0])
    if hashlib.sha256(data).hexdigest() != digest:
        raise ApplicationStateIntegrityError("stored extraction output digest mismatch")
    return data


def verify_transition_component_bytes(*, run_id: str, expected_revision: int,
                                      kind: ExtractionRunComponentKind | str,
                                      content_sha256: str) -> bytes:
    """Verify stored producer bytes before a revision-fenced lifecycle binding.

    Mutable runs may stage outputs before referencing them. This operation
    grants no bound-read, review or publication authority. Frozen runs still
    permit only their current exact binding; metadata CAS owns the transition.
    """
    kind = _output_kind(kind)
    digest = _output_digest(content_sha256)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        run = repository.get_run(conn, run_id)
        if run is None:
            raise ApplicationStateNotFoundError("extraction run not found")
        _require_output_owner(run)
        if run.revision != expected_revision:
            raise ApplicationStateConflictError("extraction run changed before output verification")
        if run.status in FROZEN_COMPONENT_STATUSES:
            ref = run.components.get(kind.value)
            if ref is None or normalize_content_digest(ref.sha256) != digest:
                raise ApplicationStateConflictError("frozen extraction output binding cannot change")
        return _verified_payload_bytes(conn, run_id=run_id, kind=kind, digest=digest)


@contextmanager
def correction_parent_lease(parent_run_id: str):
    """Serialize correction creation/recovery in the authoritative APP database.

    Dedicated transaction owns only an advisory lock, never a row lock: nested
    owner transactions must remain free to perform their existing CAS updates.
    Connection closure releases the lease even after interruption. No local-file
    fallback exists. Parent scope also serializes legacy/current child lookup.
    """
    if not isinstance(parent_run_id, str) or not parent_run_id.strip():
        raise ApplicationStateValidationError("correction parent run is required")
    key = int.from_bytes(hashlib.sha256(
        ("dmb:recap-correction-parent:v1:" + parent_run_id).encode("utf-8")
    ).digest()[:8], "big", signed=True)
    with unit_of_work(load_runtime_dsn()) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (key,))
        yield
