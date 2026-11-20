"""Transactional primitives for disabled-by-default hosted World creation.

These primitives do not authenticate HTTP requests or expose a hosted route.
The caller must supply the already verified principal and enforce origin.
"""

from __future__ import annotations

import hashlib
import re

import psycopg

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work
from application_state.world_catalog import service as catalog
from application_state.world_catalog.types import _validate_subject

_KEY = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


def _validated_input(subject: str, name: str, request_key: str) -> tuple[str, str, str]:
    try:
        subject = _validate_subject(subject)
    except ValueError as exc:
        raise ApplicationStateValidationError("invalid authenticated subject") from exc
    if not subject or not isinstance(name, str) or len(name.encode("utf-8")) > 400:
        raise ApplicationStateValidationError("invalid World name or subject")
    display = catalog.display_world_name(name)
    if len(display) > 100 or not isinstance(request_key, str) or not _KEY.fullmatch(request_key):
        raise ApplicationStateValidationError("invalid World name or request key")
    return subject, display, hashlib.sha256(display.encode("utf-8")).hexdigest()


def _policy(conn: psycopg.Connection) -> tuple:
    row = conn.execute(
        "SELECT enabled, owner_world_limit, global_world_limit, owner_rate_limit, "
        "global_rate_limit, rate_window_seconds FROM workspace.hosted_world_creation_policy "
        "WHERE singleton = true FOR UPDATE"
    ).fetchone()
    if row is None or not row[0]:
        raise ApplicationStateError("hosted World creation unavailable", status_code=503)
    return row


def _charge_attempt(dsn: str, subject: str) -> None:
    # This transaction commits independently of a later create conflict.
    with unit_of_work(dsn) as conn:
        _, _, _, owner_rate, global_rate, seconds = _policy(conn)
        now = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        conn.execute(
            "DELETE FROM workspace.hosted_world_creation_attempt WHERE attempt_id IN "
            "(SELECT attempt_id FROM workspace.hosted_world_creation_attempt "
            "WHERE attempted_at < %s - interval '1 day' ORDER BY attempt_id LIMIT 256)",
            (now,),
        )
        counts = conn.execute(
            "SELECT count(*) FILTER (WHERE creator_subject = %s), count(*) "
            "FROM workspace.hosted_world_creation_attempt "
            "WHERE attempted_at >= %s - (%s * interval '1 second')",
            (subject, now, seconds),
        ).fetchone()
        if counts[0] >= owner_rate or counts[1] >= global_rate:
            raise ApplicationStateError("hosted World creation rate limit reached", status_code=429)
        conn.execute(
            "INSERT INTO workspace.hosted_world_creation_attempt (creator_subject, attempted_at) VALUES (%s, %s)",
            (subject, now),
        )


def create_owned_world(*, subject: str, name: str, request_key: str) -> catalog.StoredWorld:
    """Create once, or recover an active exact prior result, under one owner."""
    subject, display, fingerprint = _validated_input(subject, name, request_key)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    _charge_attempt(dsn, subject)
    try:
        with unit_of_work(dsn) as conn:
            _, owner_limit, global_limit, _, _, _ = _policy(conn)
            conn.execute("LOCK TABLE workspace.managed_world IN EXCLUSIVE MODE")
            previous = conn.execute(
                "SELECT r.request_sha256, r.world_id, a.revoked_at "
                "FROM workspace.hosted_world_creation_receipt r "
                "JOIN workspace.hosted_world_admission a ON a.world_id = r.world_id "
                "WHERE r.creator_subject = %s AND r.request_key = %s "
                "AND a.creator_subject = %s",
                (subject, request_key, subject),
            ).fetchone()
            records = catalog._records(conn)
            if previous:
                if previous[0] != fingerprint or previous[2] is not None:
                    raise ApplicationStateConflictError("creation receipt is unavailable")
                result = next((r for r in records if r.record.world_id == previous[1]), None)
                if result is None or result.record.owner_subject != subject:
                    raise ApplicationStateConflictError("creation receipt is unavailable")
                return result
            counts = conn.execute(
                "SELECT count(*) FILTER (WHERE creator_subject = %s), count(*) "
                "FROM workspace.hosted_world_admission", (subject,),
            ).fetchone()
            if counts[0] >= owner_limit or counts[1] >= global_limit:
                raise ApplicationStateError("hosted World creation allocation limit reached", status_code=429)
            comparison = catalog.normalize_world_name_for_compare(display)
            if any(r.record.owner_subject == subject and catalog.normalize_world_name_for_compare(r.record.name) == comparison for r in records):
                raise ApplicationStateConflictError("World name already exists for this owner")
            world_id = catalog._world_id_for_owner(
                [r.record for r in records], base_world_id=catalog.derive_world_id_from_name(display),
                owner_subject=subject, compare_name=comparison,
            )
            record = catalog._validated_record(catalog._new_world_record(world_id, name=display, owner_subject=subject))
            catalog._write(conn, record, revision=1)
            conn.execute("INSERT INTO workspace.hosted_world_admission (world_id, creator_subject) VALUES (%s, %s)", (world_id, subject))
            conn.execute("INSERT INTO workspace.hosted_world_creation_receipt (creator_subject, request_key, request_sha256, world_id) VALUES (%s, %s, %s, %s)", (subject, request_key, fingerprint, world_id))
            return catalog.StoredWorld(record, 1)
    except psycopg.IntegrityError as exc:
        raise ApplicationStateConflictError("World creation conflicts with retained metadata") from exc
