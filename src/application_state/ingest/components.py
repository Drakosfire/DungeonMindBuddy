"""Immutable extraction output storage. Source bodies remain with source owner."""
from __future__ import annotations

import hashlib

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError, ApplicationStateIntegrityError,
    ApplicationStateNotFoundError, ApplicationStateValidationError,
)
from application_state.ingest import repository
from application_state.unit_of_work import unit_of_work
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind, FROZEN_COMPONENT_STATUSES, normalize_content_digest,
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
    return digest


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
