"""Durable Buddy APP-STATE authority: fingerprint, isolation, backup/restore verification.

This module owns the read-only APP-STATE fingerprint and the recovery-verification
logic for the durable local authority (`compose.postgres.app-state.yml`).

Invariants:
- Schema-at-head alone is never READY. A fingerprint covers every durable domain:
  Content work objects/revisions/working copies, Play runs/manifests/active run,
  IngestRun identity/lifecycle, and Source artifact/revision bindings.
- Fingerprints are deterministic: fixed table order, stable row order, canonical
  JSON serialization, SHA-256 digests.
- Fingerprints and reports never contain secrets; DSNs are redacted before display.
- READY is only a parity verdict against a trusted expected fingerprint (or a
  second live DSN via ``verify``). Observing a reachable database at Alembic
  head is never READY — a wiped empty-at-head database is the failure this
  module exists to catch.
- Restore verifies dump SHA-256 against the sidecar (or an explicit digest)
  before ``pg_restore``. A missing or mismatched digest refuses the restore.
- Restore requires a trusted expected fingerprint (explicit argument or the
  backup ``.fingerprint.json`` sidecar). Without one, READY cannot be claimed
  and restore is refused.
- A restore target must be empty of APP-STATE schemas; destructive restore is not
  a supported operation in this slice.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse, urlunparse
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from application_state.cli import _alembic_head, assert_at_head
from application_state.config import load_runtime_dsn
from application_state.engine import connect
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateIsolationError,
    ApplicationStateMigrationError,
    ApplicationStateUnavailableError,
)
from application_state.naming import (
    WORLD_DSN_ENV_NAMES,
    assert_dsn_is_not_world_graph,
    assert_safe_application_state_dsn,
    database_name_from_dsn,
)

FINGERPRINT_SCHEMA = "dmb_application_state_fingerprint_v1"

# Durable APP-STATE domain tables in fixed fingerprint order.
# (domain name, fully qualified table, row-order column)
_DOMAIN_TABLES: tuple[tuple[str, str, str], ...] = (
    ("content.work_object", "content.work_object", "work_object_id"),
    ("content.work_revision", "content.work_revision", "work_revision_id"),
    ("content.working_copy", "content.working_copy", "work_object_id"),
    ("play.run", "play.run", "run_id"),
    ("play.run_manifest", "play.run_manifest", "run_id"),
    ("play.active_run", "play.active_run", "run_id"),
    ("ingest.run", "ingest.run", "run_id"),
    ("source.artifact", "source.artifact", "source_artifact_id"),
    ("source.revision", "source.revision", "source_revision_id"),
)

# Schemas that mark a database as already holding APP-STATE (restore must refuse).
_APP_STATE_SCHEMAS = ("application_state", "content", "play", "ingest", "source")


@dataclass(frozen=True)
class DomainFingerprint:
    """Digest over one durable domain table."""

    name: str
    row_count: int
    digest: str


@dataclass(frozen=True)
class ApplicationStateFingerprint:
    """Deterministic, secret-free fingerprint of one APP-STATE database."""

    schema: str
    alembic_current: str
    alembic_head: str
    domains: tuple[DomainFingerprint, ...]
    digest: str

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_json_dict(), indent=2, sort_keys=True) + "\n"

    @staticmethod
    def from_json_dict(payload: dict[str, Any]) -> "ApplicationStateFingerprint":
        return ApplicationStateFingerprint(
            schema=str(payload["schema"]),
            alembic_current=str(payload["alembic_current"]),
            alembic_head=str(payload["alembic_head"]),
            domains=tuple(
                DomainFingerprint(
                    name=str(d["name"]),
                    row_count=int(d["row_count"]),
                    digest=str(d["digest"]),
                )
                for d in payload["domains"]
            ),
            digest=str(payload["digest"]),
        )


@dataclass(frozen=True)
class BackupRecord:
    """Result of an external authority backup."""

    backup_path: str
    backup_sha256: str
    fingerprint: ApplicationStateFingerprint
    source: str  # redacted coordinates only


@dataclass(frozen=True)
class RestoreReport:
    """Result of restoring a backup into a clean target."""

    target: str  # redacted coordinates only
    fingerprint: ApplicationStateFingerprint
    ready: bool
    mismatches: tuple[str, ...]


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"value of type {type(value).__name__} is not fingerprintable")


def _canonical_row(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, default=_json_default)


def redact_dsn(dsn: str) -> str:
    """Return the DSN with any password removed (coordinates only)."""
    parsed = urlparse(dsn)
    if not parsed.password:
        return dsn
    netloc = parsed.hostname or ""
    if parsed.username:
        netloc = f"{parsed.username}:***@{netloc}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def redact_secrets(text: str, *dsns: str | None) -> str:
    """Remove raw DSNs and passwords from operator-facing text."""
    redacted = text
    for dsn in dsns:
        if not dsn:
            continue
        redacted = redacted.replace(dsn, redact_dsn(dsn))
        parsed = urlparse(dsn)
        if parsed.password:
            redacted = redacted.replace(unquote(parsed.password), "***")
    return redacted


def _same_server_database(first: str, second: str) -> bool:
    a, b = urlparse(first), urlparse(second)
    return (
        (a.hostname or "").lower() == (b.hostname or "").lower()
        and (a.port or 5432) == (b.port or 5432)
        and a.path.lstrip("/") == b.path.lstrip("/")
    )


def _world_dsns_from_env() -> dict[str, str]:
    """World DSNs from the process environment (entry points load dotenv first)."""
    return {name: os.environ[name] for name in WORLD_DSN_ENV_NAMES if os.environ.get(name)}


def assert_authority_target_isolated(
    target_dsn: str,
    *,
    source_dsn: str | None = None,
    world_dsns: dict[str, str] | None = None,
) -> None:
    """Fail closed unless the target is a Buddy APP-STATE DSN distinct from World/source."""
    assert_safe_application_state_dsn(target_dsn)
    assert_dsn_is_not_world_graph(
        target_dsn,
        world_dsns=world_dsns if world_dsns is not None else _world_dsns_from_env(),
    )
    if source_dsn and _same_server_database(target_dsn, source_dsn):
        raise ApplicationStateIsolationError(
            "authority target DSN must differ from the source DSN; "
            "restore into a second clean target, never onto the source"
        )


def database_has_app_state_schema(dsn: str) -> bool:
    """True when the database already contains any APP-STATE schema."""
    conn = connect(dsn)
    try:
        rows = conn.execute(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = ANY(%s)
            """,
            (list(_APP_STATE_SCHEMAS),),
        ).fetchall()
    finally:
        conn.close()
    return bool(rows)


def _fingerprint_table(
    cursor: psycopg.Cursor[dict[str, Any]], domain: str, table: str, order_by: str
) -> DomainFingerprint:
    # Table/column names come only from the static _DOMAIN_TABLES contract.
    rows = cursor.execute(
        f"SELECT * FROM {table} ORDER BY {order_by}",  # noqa: S608
    ).fetchall()
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_canonical_row(dict(row)).encode("utf-8"))
        digest.update(b"\n")
    return DomainFingerprint(
        name=domain, row_count=len(rows), digest=digest.hexdigest()
    )


def compute_fingerprint(dsn: str | None = None) -> ApplicationStateFingerprint:
    """Compute the deterministic APP-STATE fingerprint. Requires schema at head."""
    target = dsn or load_runtime_dsn()
    assert_at_head(dsn=target)
    head = _alembic_head()
    conn = connect(target)
    try:
        conn.read_only = True
        with conn.transaction():
            cursor = conn.cursor(row_factory=dict_row)
            current_row = cursor.execute(
                "SELECT version_num FROM application_state.schema_migrations"
            ).fetchone()
            current = str(current_row["version_num"])
            domains = tuple(
                _fingerprint_table(cursor, domain, table, order_by)
                for domain, table, order_by in _DOMAIN_TABLES
            )
    finally:
        conn.close()
    combined = hashlib.sha256(
        json.dumps(
            {
                "schema": FINGERPRINT_SCHEMA,
                "alembic_current": current,
                "alembic_head": head,
                "domains": [
                    {"name": d.name, "row_count": d.row_count, "digest": d.digest}
                    for d in domains
                ],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return ApplicationStateFingerprint(
        schema=FINGERPRINT_SCHEMA,
        alembic_current=str(current),
        alembic_head=head,
        domains=domains,
        digest=combined,
    )


def compare_fingerprints(
    source: ApplicationStateFingerprint, target: ApplicationStateFingerprint
) -> list[str]:
    """Return human-readable mismatches; empty list means identical state."""
    mismatches: list[str] = []
    if source.schema != target.schema:
        mismatches.append(
            f"fingerprint schema differs: {source.schema} != {target.schema}"
        )
        return mismatches
    if source.alembic_current != target.alembic_current:
        mismatches.append(
            "alembic revision differs: "
            f"source={source.alembic_current} target={target.alembic_current}"
        )
    source_domains = {d.name: d for d in source.domains}
    target_domains = {d.name: d for d in target.domains}
    for name in sorted(set(source_domains) | set(target_domains)):
        s = source_domains.get(name)
        t = target_domains.get(name)
        if s is None or t is None:
            mismatches.append(f"{name}: present on only one side")
            continue
        if s.row_count != t.row_count or s.digest != t.digest:
            mismatches.append(
                f"{name}: source(rows={s.row_count}, digest={s.digest[:12]}…) "
                f"!= target(rows={t.row_count}, digest={t.digest[:12]}…)"
            )
    return mismatches


def verify_parity(
    *, source_dsn: str, target_dsn: str
) -> tuple[bool, list[str], ApplicationStateFingerprint, ApplicationStateFingerprint]:
    """Fingerprint both sides and report READY (True) or NOT_READY (False)."""
    assert_authority_target_isolated(target_dsn, source_dsn=source_dsn)
    source_fp = compute_fingerprint(source_dsn)
    target_fp = compute_fingerprint(target_dsn)
    mismatches = compare_fingerprints(source_fp, target_fp)
    return (not mismatches, mismatches, source_fp, target_fp)


def _pg_env(dsn: str) -> dict[str, str]:
    """Build pg_dump/pg_restore environment without exposing secrets in argv."""
    parsed = urlparse(dsn)
    env = dict(os.environ)
    env["PGHOST"] = parsed.hostname or "127.0.0.1"
    env["PGPORT"] = str(parsed.port or 5432)
    env["PGUSER"] = unquote(parsed.username or "")
    env["PGDATABASE"] = database_name_from_dsn(dsn)
    if parsed.password:
        env["PGPASSWORD"] = unquote(parsed.password)
    return env


def _pg_conninfo(env: dict[str, str]) -> str:
    """Password-free conninfo; PGPASSWORD travels only via the process env."""
    return (
        f"host={env['PGHOST']} port={env['PGPORT']} "
        f"user={env['PGUSER']} dbname={env['PGDATABASE']}"
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_sidecar_path(backup_path: str | Path) -> Path:
    backup = Path(backup_path)
    return backup.with_suffix(backup.suffix + ".sha256")


def fingerprint_sidecar_path(backup_path: str | Path) -> Path:
    backup = Path(backup_path)
    return backup.with_suffix(backup.suffix + ".fingerprint.json")


def parse_sha256_sidecar(text: str) -> str:
    """Parse a sha256sum-format sidecar (``<hex>  <filename>``)."""
    token = text.strip().split()[0] if text.strip() else ""
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token.lower()):
        raise ApplicationStateIntegrityError(
            "backup SHA-256 sidecar is not a 64-character hex digest"
        )
    return token.lower()


def verify_backup_digest(
    backup_path: str | Path, *, expected_sha256: str | None = None
) -> str:
    """Refuse restore when dump bytes do not match a trusted SHA-256.

    ``expected_sha256`` wins when supplied; otherwise the ``.sha256`` sidecar
    next to the dump is required. A missing sidecar is an integrity failure,
    not a skip.
    """
    backup = Path(backup_path)
    if not backup.exists():
        raise ApplicationStateUnavailableError(f"backup file not found: {backup}")
    actual = _sha256_file(backup)
    if expected_sha256 is None:
        sidecar = sha256_sidecar_path(backup)
        if not sidecar.exists():
            raise ApplicationStateIntegrityError(
                "backup SHA-256 sidecar missing; refuse restore of an unverified dump"
            )
        expected_sha256 = parse_sha256_sidecar(sidecar.read_text(encoding="utf-8"))
    else:
        expected_sha256 = parse_sha256_sidecar(expected_sha256)
    if actual != expected_sha256:
        raise ApplicationStateIntegrityError(
            "backup SHA-256 mismatch: dump bytes do not match the trusted digest; "
            "refuse restore"
        )
    return actual


def load_fingerprint_sidecar(backup_path: str | Path) -> ApplicationStateFingerprint:
    sidecar = fingerprint_sidecar_path(backup_path)
    if not sidecar.exists():
        raise ApplicationStateIntegrityError(
            "backup fingerprint sidecar missing; restore cannot claim READY "
            "without a trusted expected fingerprint"
        )
    return ApplicationStateFingerprint.from_json_dict(
        json.loads(sidecar.read_text(encoding="utf-8"))
    )


def backup_authority(*, source_dsn: str, out_path: str | Path) -> BackupRecord:
    """External custom-format backup of the APP-STATE authority.

    Fingerprints the source before and after the dump; a source that changes
    during backup is reported as an integrity failure (recapture required).
    Writes `<out>.sha256` and `<out>.fingerprint.json` sidecars.
    """
    assert_safe_application_state_dsn(source_dsn)
    assert_dsn_is_not_world_graph(source_dsn, world_dsns=_world_dsns_from_env())
    out = Path(out_path)
    env = _pg_env(source_dsn)
    before = compute_fingerprint(source_dsn)
    result = subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--file",
            str(out),
            "--dbname",
            _pg_conninfo(env),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ApplicationStateUnavailableError(
            "pg_dump failed: " + redact_secrets(result.stderr.strip(), source_dsn)
        )
    after = compute_fingerprint(source_dsn)
    if before.digest != after.digest:
        raise ApplicationStateIntegrityError(
            "source APP-STATE changed during backup; recapture required — "
            "never claim a stale dump is current authority"
        )
    backup_sha = _sha256_file(out)
    sha256_sidecar_path(out).write_text(
        f"{backup_sha}  {out.name}\n", encoding="utf-8"
    )
    fingerprint_sidecar_path(out).write_text(before.to_json(), encoding="utf-8")
    return BackupRecord(
        backup_path=str(out),
        backup_sha256=backup_sha,
        fingerprint=before,
        source=redact_dsn(source_dsn),
    )


def restore_authority(
    *,
    target_dsn: str,
    backup_path: str | Path,
    source_dsn: str | None = None,
    expect_fingerprint: ApplicationStateFingerprint | None = None,
    expected_sha256: str | None = None,
) -> RestoreReport:
    """Restore an external backup into a second clean target and verify.

    Fail-closed before ``pg_restore``:
    - dump SHA-256 must match the sidecar or ``expected_sha256``;
    - a trusted expected fingerprint is required (argument or sidecar);
    - the target must exist and be empty of APP-STATE schemas.

    Destructive restore over an existing authority is not supported.
    READY is fingerprint parity against that trusted expected fingerprint,
    never "restore completed" alone.
    """
    assert_authority_target_isolated(target_dsn, source_dsn=source_dsn)
    backup = Path(backup_path)
    verify_backup_digest(backup, expected_sha256=expected_sha256)
    trusted = expect_fingerprint or load_fingerprint_sidecar(backup)
    if database_has_app_state_schema(target_dsn):
        raise ApplicationStateIntegrityError(
            "restore target already contains APP-STATE schemas; "
            "destructive restore is not supported — use a second clean target"
        )
    env = _pg_env(target_dsn)
    result = subprocess.run(
        [
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            _pg_conninfo(env),
            str(backup),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ApplicationStateUnavailableError(
            "pg_restore failed: " + redact_secrets(result.stderr.strip(), target_dsn)
        )
    try:
        fingerprint = compute_fingerprint(target_dsn)
    except ApplicationStateMigrationError as exc:
        raise ApplicationStateMigrationError(
            "restored target is not at Alembic head; run explicit migrations "
            "(`uv run python scripts/bootstrap_local_play.py apply` with the "
            "target DSN configured) before verifying parity"
        ) from exc
    mismatches = tuple(compare_fingerprints(trusted, fingerprint))
    return RestoreReport(
        target=redact_dsn(target_dsn),
        fingerprint=fingerprint,
        ready=not mismatches,
        mismatches=mismatches,
    )
