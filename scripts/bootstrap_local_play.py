#!/usr/bin/env python3
"""Explicit local Play / application-state bootstrap. No migrate-on-boot."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, urlunparse

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from application_state.cli import (  # noqa: E402
    _alembic_head,
    _read_current_revision,
    upgrade_to_head,
)
from application_state.config import APPLICATION_STATE_DSN_ENV, load_runtime_dsn  # noqa: E402
from application_state.content.import_runbooks import import_runbooks_from_snapshots  # noqa: E402
from application_state.content.service import (  # noqa: E402
    current_committed_revision,
    exact_committed_revision,
    list_runbooks,
)
from application_state.content.types import ImportReport  # noqa: E402
from application_state.errors import (  # noqa: E402
    ApplicationStateConflictError,
    ApplicationStateError,
    ApplicationStateIntegrityError,
    ApplicationStateIsolationError,
    ApplicationStateMigrationError,
    ApplicationStateUnavailableError,
)
from application_state.naming import database_name_from_dsn  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

STANDARD_DATABASE_NAME = "dungeonbuddy_application_state"
_STANDARD_PREFIX = STANDARD_DATABASE_NAME + "_"
_SAFE_SUFFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]*$")

CONFIGURATION_HELP = """\
Set this in repo .env or .env.development:

DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=<postgresql URL for a separate Buddy database>

Recommended local database name:
  dungeonbuddy_application_state

Do not point this at:
  dungeonmind
  dungeonmind_cutover_live
  the configured World Graph database

Then run:
  uv run python scripts/bootstrap_local_play.py apply
"""


@dataclass
class DsnCoordinates:
    host: str
    port: str
    database: str
    username: str


@dataclass
class ReadinessReport:
    play_readiness: str
    configured: bool = False
    isolation: str = "unknown"
    coordinates: DsnCoordinates | None = None
    database_exists: bool | None = None
    database_reachable: bool | None = None
    schema_current: str | None = None
    schema_head: str | None = None
    schema_status: str = "unknown"
    legacy_available: int | None = None
    startable_runbooks: int | None = None
    created_database: bool = False
    import_report: ImportReport | None = None
    notes: list[str] = field(default_factory=list)
    dsn_for_redaction: str | None = None


def may_create_logical_database(name: str) -> bool:
    if name == STANDARD_DATABASE_NAME:
        return True
    if not name.startswith(_STANDARD_PREFIX):
        return False
    suffix = name[len(_STANDARD_PREFIX) :]
    return bool(suffix) and _SAFE_SUFFIX_RE.fullmatch(suffix) is not None


def coordinates_from_dsn(dsn: str) -> DsnCoordinates:
    parsed = urlparse(dsn)
    path = (parsed.path or "").lstrip("/")
    database = path.split("/")[0] if path else ""
    port = str(parsed.port) if parsed.port else "5432"
    return DsnCoordinates(
        host=parsed.hostname or "",
        port=port,
        database=database,
        username=parsed.username or "",
    )


def _maintenance_dsn(dsn: str) -> str:
    parsed = urlparse(dsn)
    return urlunparse(parsed._replace(path="/postgres"))


def redact_secrets(text: str, dsn: str | None) -> str:
    cleaned = text
    if not dsn:
        return cleaned
    parsed = urlparse(dsn)
    if parsed.password:
        cleaned = cleaned.replace(parsed.password, "***")
    cleaned = cleaned.replace(dsn, "<redacted-dsn>")
    maintenance = _maintenance_dsn(dsn)
    if maintenance != dsn:
        cleaned = cleaned.replace(maintenance, "<redacted-dsn>")
    return cleaned


def _load_env(*, load_env: bool) -> None:
    if load_env:
        load_dungeonmindbuddy_dotenv()


def _validate_configured_dsn() -> str:
    raw = os.environ.get(APPLICATION_STATE_DSN_ENV, "").strip()
    if not raw:
        raise ApplicationStateUnavailableError(
            f"{APPLICATION_STATE_DSN_ENV} is not set; DungeonBuddy application state is unavailable"
        )
    return load_runtime_dsn()


def _probe_target_database(dsn: str) -> tuple[bool | None, bool | None, str | None]:
    """Return (exists, reachable, error_kind). Never CREATE/DROP."""
    import psycopg
    from psycopg.errors import InvalidCatalogName

    name = database_name_from_dsn(dsn)
    try:
        with psycopg.connect(_maintenance_dsn(dsn), autocommit=True, connect_timeout=5) as conn:
            row = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
            return (row is not None, True, None)
    except InvalidCatalogName:
        return (None, False, "unavailable")
    except psycopg.Error as exc:
        if isinstance(exc, InvalidCatalogName):
            return (None, False, "unavailable")
        try:
            with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
                conn.execute("SELECT 1")
            return (True, True, None)
        except InvalidCatalogName:
            return (False, True, None)
        except psycopg.Error:
            return (None, False, "unavailable")


def _schema_status(dsn: str) -> tuple[str | None, str, str]:
    head = _alembic_head()
    current = _read_current_revision(dsn)
    if current == head:
        return current, head, "ready"
    if current is None:
        return current, head, "behind"
    return current, head, "behind"


def _legacy_snapshot_count(repo_root: Path) -> int:
    from apps.live_control_server.services.workspace_document_registry import (
        capture_legacy_runbook_snapshots,
    )

    return len(capture_legacy_runbook_snapshots(repo_root))


def _capture_legacy_snapshots(repo_root: Path):
    from apps.live_control_server.services.workspace_document_registry import (
        capture_legacy_runbook_snapshots,
    )

    return capture_legacy_runbook_snapshots(repo_root)


def count_startable_runbooks() -> int:
    count = 0
    for obj in list_runbooks(status="active"):
        document_id = str(obj.work_object_id)
        try:
            committed = current_committed_revision(document_id, kind="runbook")
            exact_committed_revision(
                document_id,
                committed.work_revision.revision_n,
                kind="runbook",
                expected_sha256=committed.work_revision.content_sha256,
            )
        except ApplicationStateError:
            continue
        count += 1
    return count


def _readiness_after_schema(
    *,
    schema_status: str,
    startable: int | None,
    legacy_available: int | None,
) -> str:
    if schema_status != "ready":
        return "NEEDS BOOTSTRAP"
    if startable and startable > 0:
        return "READY"
    if legacy_available:
        return "NEEDS BOOTSTRAP"
    return "PLAY CONTENT NOT READY"


def inspect_readiness(*, repo_root: Path, load_env: bool = True) -> ReadinessReport:
    _load_env(load_env=load_env)
    raw = os.environ.get(APPLICATION_STATE_DSN_ENV, "").strip()
    if not raw:
        return ReadinessReport(
            play_readiness="NEEDS CONFIGURATION",
            configured=False,
            isolation="missing",
            notes=["application-state DSN is not set"],
        )
    try:
        dsn = _validate_configured_dsn()
    except (ApplicationStateUnavailableError, ApplicationStateIsolationError) as exc:
        message = str(exc)
        isolation = "rejected"
        if "not set" in message:
            isolation = "missing"
        return ReadinessReport(
            play_readiness="BLOCKED" if isolation == "rejected" else "NEEDS CONFIGURATION",
            configured=isolation != "missing",
            isolation=isolation,
            notes=[redact_secrets(message, raw)],
            dsn_for_redaction=raw,
        )

    report = ReadinessReport(
        play_readiness="NEEDS BOOTSTRAP",
        configured=True,
        isolation="safe",
        coordinates=coordinates_from_dsn(dsn),
        dsn_for_redaction=dsn,
    )
    exists, reachable, error_kind = _probe_target_database(dsn)
    report.database_exists = exists
    report.database_reachable = reachable
    if reachable is False or error_kind == "unavailable":
        report.play_readiness = "UNAVAILABLE"
        report.notes.append("PostgreSQL is unavailable")
        return report
    if exists is False:
        report.schema_status = "missing"
        report.legacy_available = _legacy_snapshot_count(repo_root)
        report.play_readiness = "NEEDS BOOTSTRAP"
        report.notes.append("target logical database does not exist")
        return report

    try:
        current, head, schema_status = _schema_status(dsn)
    except ApplicationStateUnavailableError as exc:
        report.play_readiness = "UNAVAILABLE"
        report.notes.append(redact_secrets(str(exc), dsn))
        return report
    report.schema_current = current
    report.schema_head = head
    report.schema_status = schema_status
    report.legacy_available = _legacy_snapshot_count(repo_root)
    if schema_status == "ready":
        report.startable_runbooks = count_startable_runbooks()
    report.play_readiness = _readiness_after_schema(
        schema_status=schema_status,
        startable=report.startable_runbooks,
        legacy_available=report.legacy_available,
    )
    return report


def _create_logical_database(dsn: str) -> None:
    import psycopg
    from psycopg import sql
    from psycopg.errors import DuplicateDatabase, InsufficientPrivilege

    name = database_name_from_dsn(dsn)
    try:
        with psycopg.connect(_maintenance_dsn(dsn), autocommit=True, connect_timeout=5) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except DuplicateDatabase:
        return
    except InsufficientPrivilege as exc:
        raise ApplicationStateUnavailableError(
            f"Database {name} does not exist and could not be created "
            "with the configured PostgreSQL user.\n\n"
            "Create that logical database with an account that has CREATEDB permission,\n"
            "then rerun:\n\n"
            "  uv run python scripts/bootstrap_local_play.py apply"
        ) from exc
    except psycopg.Error as exc:
        raise ApplicationStateUnavailableError(
            f"Database {name} does not exist and could not be created "
            "with the configured PostgreSQL user.\n\n"
            "Create that logical database with an account that has CREATEDB permission,\n"
            "then rerun:\n\n"
            "  uv run python scripts/bootstrap_local_play.py apply"
        ) from exc


def apply_bootstrap(*, repo_root: Path, load_env: bool = True) -> ReadinessReport:
    _load_env(load_env=load_env)
    raw = os.environ.get(APPLICATION_STATE_DSN_ENV, "").strip()
    if not raw:
        return inspect_readiness(repo_root=repo_root, load_env=False)
    try:
        dsn = _validate_configured_dsn()
    except (ApplicationStateUnavailableError, ApplicationStateIsolationError) as exc:
        return ReadinessReport(
            play_readiness="BLOCKED",
            configured=True,
            isolation="rejected",
            notes=[redact_secrets(str(exc), raw)],
            dsn_for_redaction=raw,
        )

    report = ReadinessReport(
        play_readiness="NEEDS BOOTSTRAP",
        configured=True,
        isolation="safe",
        coordinates=coordinates_from_dsn(dsn),
        dsn_for_redaction=dsn,
    )
    exists, reachable, error_kind = _probe_target_database(dsn)
    report.database_exists = exists
    report.database_reachable = reachable
    if reachable is False or error_kind == "unavailable":
        report.play_readiness = "UNAVAILABLE"
        report.notes.append("PostgreSQL is unavailable")
        return report

    name = database_name_from_dsn(dsn)
    if exists is False:
        if not may_create_logical_database(name):
            report.play_readiness = "BLOCKED"
            report.notes.append(
                f"Database {name} does not exist. Bootstrap will not create an arbitrary "
                "custom database name. Create it first, or use "
                f"{STANDARD_DATABASE_NAME} / {STANDARD_DATABASE_NAME}_<suffix>."
            )
            return report
        try:
            _create_logical_database(dsn)
        except ApplicationStateUnavailableError as exc:
            report.play_readiness = "BLOCKED"
            report.notes.append(redact_secrets(str(exc), dsn))
            return report
        report.created_database = True
        report.database_exists = True

    try:
        upgrade_to_head(dsn=dsn)
        current, head, schema_status = _schema_status(dsn)
    except (ApplicationStateMigrationError, ApplicationStateUnavailableError) as exc:
        report.play_readiness = "BLOCKED"
        report.notes.append(redact_secrets(str(exc), dsn))
        return report
    report.schema_current = current
    report.schema_head = head
    report.schema_status = schema_status

    snapshots = _capture_legacy_snapshots(repo_root)
    report.legacy_available = len(snapshots)
    try:
        report.import_report = import_runbooks_from_snapshots(snapshots)
    except (ApplicationStateConflictError, ApplicationStateIntegrityError, ApplicationStateError) as exc:
        report.play_readiness = "BLOCKED"
        report.notes.append(redact_secrets(str(exc), dsn))
        return report

    report.startable_runbooks = count_startable_runbooks()
    report.play_readiness = _readiness_after_schema(
        schema_status=schema_status,
        startable=report.startable_runbooks,
        legacy_available=0,
    )
    return report


def format_report(report: ReadinessReport, *, command: str) -> str:
    lines: list[str] = ["DungeonBuddy Local Play Readiness", ""]
    lines.append("Application state DSN")
    lines.append(f"  configured: {'yes' if report.configured else 'no'}")
    if report.coordinates is not None:
        lines.append(f"  host: {report.coordinates.host}")
        lines.append(f"  port: {report.coordinates.port}")
        lines.append(f"  database: {report.coordinates.database}")
        if report.coordinates.username:
            lines.append(f"  username: {report.coordinates.username}")
    lines.append(f"  isolation: {report.isolation}")
    lines.append("")
    lines.append("Database")
    lines.append(f"  exists: {_tri(report.database_exists)}")
    lines.append(f"  reachable: {_tri(report.database_reachable)}")
    if report.created_database:
        lines.append("  created: yes")
    lines.append("")
    lines.append("Schema")
    lines.append(f"  current: {report.schema_current or 'none'}")
    lines.append(f"  head: {report.schema_head or 'none'}")
    lines.append(f"  status: {report.schema_status}")
    lines.append("")
    lines.append("Legacy Runbooks")
    lines.append(f"  available for adoption: {_num(report.legacy_available)}")
    if report.import_report is not None:
        lines.append(f"  imported: {report.import_report.imported}")
        lines.append(f"  noop: {report.import_report.noop}")
        lines.append(f"  skipped empty: {report.import_report.skipped_empty}")
    lines.append("")
    lines.append("Content")
    lines.append(f"  active startable Runbooks: {_num(report.startable_runbooks)}")
    lines.append("")
    if report.play_readiness == "PLAY CONTENT NOT READY":
        lines.append("Application state: READY")
        lines.append("Play content: NOT READY")
        lines.append("")
        lines.append("No active committed Runbook is available.")
        lines.append("No sample or fake Runbook was created.")
        lines.append("")
        lines.append("PLAY READINESS: NOT READY")
    else:
        lines.append(f"PLAY READINESS: {report.play_readiness}")
    if report.play_readiness == "NEEDS CONFIGURATION":
        lines.append("")
        lines.append(CONFIGURATION_HELP.strip())
    elif report.play_readiness == "NEEDS BOOTSTRAP" and command == "check":
        lines.append("")
        lines.append("Run:")
        lines.append("  uv run python scripts/bootstrap_local_play.py apply")
    if report.notes:
        lines.append("")
        lines.extend(report.notes)
    rendered = "\n".join(lines) + "\n"
    return redact_secrets(rendered, report.dsn_for_redaction)


def _tri(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _num(value: int | None) -> str:
    return "unknown" if value is None else str(value)


def main(argv: list[str] | None = None, *, load_env: bool = True, repo_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local Play application-state bootstrap")
    parser.add_argument("command", choices=("check", "apply"))
    args = parser.parse_args(argv)
    root = repo_root or _REPO_ROOT
    if args.command == "check":
        report = inspect_readiness(repo_root=root, load_env=load_env)
    else:
        report = apply_bootstrap(repo_root=root, load_env=load_env)
    sys.stdout.write(format_report(report, command=args.command))
    return 0 if report.play_readiness == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
