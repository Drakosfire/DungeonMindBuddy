"""Read-only assembled-runtime preflight checks (SURFACE-INTEGRATION SI-1)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from application_state.config import APPLICATION_STATE_DSN_ENV
from apps.live_control_server import config
from apps.live_control_server.config import (
    EXTRACT_PROMOTE_SOURCE_ROOT_ENV,
    WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV,
    WorldGraphAuthorityConfigurationError,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
    DirectWorldGraphReadError,
    WorldHeadSummary,
    _load_direct_authority_binding,
    list_world_heads,
)
from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
    GraphIngestRunRegistryError,
    discover_graph_ingest_runs,
    inspect_graph_ingest_registry_roots,
)
from scripts.bootstrap_local_play import inspect_readiness

RuntimePreflightStatus = Literal[
    "READY",
    "EMPTY",
    "NOT_CONFIGURED",
    "UNAVAILABLE",
    "INTEGRITY_ERROR",
    "NOT_READY",
]

OverallPreflightStatus = Literal["READY", "NOT READY"]

PreflightDetailValue = str | int | bool | list[str] | list[dict[str, str]]


@dataclass(frozen=True)
class RuntimePreflightCheck:
    id: str
    label: str
    required: bool
    status: RuntimePreflightStatus
    summary: str
    details: dict[str, PreflightDetailValue] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimePreflightReport:
    status: OverallPreflightStatus
    checks: tuple[RuntimePreflightCheck, ...]


def redact_dsn(dsn: str) -> str:
    """Return a host/port/database diagnostic without secret material."""
    parsed = urlparse(dsn)
    host = parsed.hostname or ""
    port = str(parsed.port) if parsed.port else "5432"
    database = (parsed.path or "").lstrip("/").split("/")[0]
    username = parsed.username or ""
    if parsed.password:
        username = f"{username}:***" if username else "***"
    credential = f"{username}@" if username else ""
    return f"postgresql://{credential}{host}:{port}/{database}"


def overall_status(checks: tuple[RuntimePreflightCheck, ...]) -> OverallPreflightStatus:
    for check in checks:
        if not check.required:
            continue
        if check.status in ("READY", "EMPTY"):
            continue
        return "NOT READY"
    return "READY"


def run_runtime_preflight(
    *,
    repo_root: Path,
    require_world: str | None = None,
    load_env: bool = True,
) -> RuntimePreflightReport:
    checks = (
        _check_app_state(repo_root, load_env=load_env),
        _check_dungeonmind_world(require_world=require_world),
        _check_campaign_registry(),
        _check_ingest_registry(repo_root),
        _check_source_roots(),
    )
    return RuntimePreflightReport(status=overall_status(checks), checks=checks)


def format_runtime_preflight_report(report: RuntimePreflightReport) -> str:
    lines = ["DungeonBuddy Assembled Runtime Preflight", ""]
    lines.append(f"Overall: {report.status}")
    lines.append("")
    for check in report.checks:
        required = "required" if check.required else "informational"
        lines.append(f"{check.label} ({required}): {check.status}")
        lines.append(f"  {check.summary}")
        for key, value in check.details.items():
            rendered = _format_detail_value(value)
            if "\n" in rendered:
                lines.append(f"  {key}:")
                lines.extend(f"    {row}" for row in rendered.splitlines())
            else:
                lines.append(f"  {key}: {rendered}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _format_detail_value(value: PreflightDetailValue) -> str:
    if isinstance(value, list):
        if not value:
            return "0"
        if isinstance(value[0], dict):
            return "\n".join(
                ", ".join(f"{k}={v}" for k, v in item.items()) for item in value
            )
        return ", ".join(str(item) for item in value)
    return str(value)


def _check_app_state(repo_root: Path, *, load_env: bool) -> RuntimePreflightCheck:
    readiness = inspect_readiness(repo_root=repo_root, load_env=load_env)
    details: dict[str, PreflightDetailValue] = {}
    if readiness.coordinates is not None:
        details["host"] = readiness.coordinates.host
        details["port"] = readiness.coordinates.port
        details["database"] = readiness.coordinates.database
    if readiness.dsn_for_redaction:
        details["database_url_redacted"] = redact_dsn(readiness.dsn_for_redaction)
    if readiness.schema_current:
        details["schema_current"] = readiness.schema_current
    if readiness.schema_head:
        details["schema_head"] = readiness.schema_head

    if not readiness.configured or readiness.play_readiness == "NEEDS CONFIGURATION":
        return RuntimePreflightCheck(
            id="app_state",
            label="Buddy application state",
            required=True,
            status="NOT_CONFIGURED",
            summary=f"{APPLICATION_STATE_DSN_ENV} is not configured",
            details=details,
        )
    if readiness.isolation == "rejected" or readiness.play_readiness == "BLOCKED":
        details["isolation"] = readiness.isolation
        summary = readiness.notes[0] if readiness.notes else (
            "Application-state DSN failed isolation guard"
        )
        return RuntimePreflightCheck(
            id="app_state",
            label="Buddy application state",
            required=True,
            status="NOT_READY",
            summary=summary,
            details=details,
        )
    if readiness.play_readiness == "UNAVAILABLE" or readiness.database_reachable is False:
        return RuntimePreflightCheck(
            id="app_state",
            label="Buddy application state",
            required=True,
            status="UNAVAILABLE",
            summary="Application-state database is unavailable",
            details=details,
        )
    if readiness.database_exists is False:
        return RuntimePreflightCheck(
            id="app_state",
            label="Buddy application state",
            required=True,
            status="NOT_READY",
            summary="Application-state logical database does not exist",
            details=details,
        )
    if readiness.schema_status != "ready":
        details["schema_status"] = readiness.schema_status
        return RuntimePreflightCheck(
            id="app_state",
            label="Buddy application state",
            required=True,
            status="NOT_READY",
            summary=f"Application-state schema is {readiness.schema_status}",
            details=details,
        )

    startable = readiness.startable_runbooks or 0
    details["startable_runbooks"] = startable
    summary = "Application-state schema is ready"
    if startable == 0:
        details["note"] = "No startable runbooks; empty application state is valid"
    return RuntimePreflightCheck(
        id="app_state",
        label="Buddy application state",
        required=True,
        status="READY",
        summary=summary,
        details=details,
    )


def _check_dungeonmind_world(*, require_world: str | None) -> RuntimePreflightCheck:
    details: dict[str, PreflightDetailValue] = {}
    try:
        mode = config.world_graph_authority_mode()
    except WorldGraphAuthorityConfigurationError as exc:
        return RuntimePreflightCheck(
            id="dungeonmind_world",
            label="DungeonMind World Graph",
            required=True,
            status="NOT_READY",
            summary=str(exc),
            details={"authority_mode": "invalid"},
        )

    details["authority_mode"] = mode
    database_url = config.world_graph_authority_database_url()
    if not database_url:
        return RuntimePreflightCheck(
            id="dungeonmind_world",
            label="DungeonMind World Graph",
            required=True,
            status="NOT_CONFIGURED",
            summary=f"{WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV} is not configured",
            details=details,
        )

    details["database_url_redacted"] = redact_dsn(database_url)
    details["database"] = redact_dsn(database_url)

    try:
        worlds = list_world_heads(database_url=database_url)
    except DirectWorldGraphReadError as exc:
        status: RuntimePreflightStatus
        if exc.code == "authority_unavailable":
            status = "UNAVAILABLE"
        elif exc.code == "authority_integrity":
            status = "INTEGRITY_ERROR"
        else:
            status = "NOT_READY"
        return RuntimePreflightCheck(
            id="dungeonmind_world",
            label="DungeonMind World Graph",
            required=True,
            status=status,
            summary=str(exc),
            details=details,
        )

    world_lines = [_format_world_line(world) for world in worlds]
    details["world_count"] = len(worlds)
    if world_lines:
        details["worlds"] = world_lines

    integrity_errors: list[str] = []
    bundle = PostgresRepositoryBundle(PostgresDatabase(database_url))
    for world in worlds:
        if not world.head_revision_id:
            continue
        try:
            binding = _load_direct_authority_binding(bundle, world.world_id)
            details[f"{world.world_id}_genesis"] = binding.genesis
        except DirectWorldGraphReadError as exc:
            if exc.code == "authority_integrity":
                integrity_errors.append(f"{world.world_id}: {exc}")
            else:
                integrity_errors.append(f"{world.world_id}: {exc}")

    if integrity_errors:
        details["integrity_errors"] = integrity_errors
        return RuntimePreflightCheck(
            id="dungeonmind_world",
            label="DungeonMind World Graph",
            required=True,
            status="INTEGRITY_ERROR",
            summary="One or more worlds failed genesis/head integrity checks",
            details=details,
        )

    if require_world:
        known_world_ids = {world.world_id for world in worlds}
        if require_world not in known_world_ids:
            details["required_world"] = require_world
            return RuntimePreflightCheck(
                id="dungeonmind_world",
                label="DungeonMind World Graph",
                required=True,
                status="NOT_READY",
                summary=f"Required world {require_world!r} was not found in the authority database",
                details=details,
            )

    if not worlds:
        return RuntimePreflightCheck(
            id="dungeonmind_world",
            label="DungeonMind World Graph",
            required=True,
            status="READY",
            summary="Authority database is reachable with 0 worlds",
            details=details,
        )

    return RuntimePreflightCheck(
        id="dungeonmind_world",
        label="DungeonMind World Graph",
        required=True,
        status="READY",
        summary=f"Discovered {len(worlds)} world(s) with readable heads",
        details=details,
    )


def _format_world_line(world: WorldHeadSummary) -> str:
    head = world.head_revision_id or "none"
    short_head = head if len(head) <= 12 else f"{head[:12]}..."
    return f"{world.world_id} rev:{short_head}"


def _check_campaign_registry() -> RuntimePreflightCheck:
    return RuntimePreflightCheck(
        id="campaign_registry",
        label="Campaign registry",
        required=False,
        status="NOT_CONFIGURED",
        summary=(
            "No read-only campaign registry enumeration contract is mounted at SI-1"
        ),
        details={"reason": "dungeonmind_campaign_enumeration_unavailable"},
    )


def _check_ingest_registry(repo_root: Path) -> RuntimePreflightCheck:
    roots = inspect_graph_ingest_registry_roots(repo_root)
    root_lines = [
        f"{root.configured_path} exists={root.exists} readable={root.readable}"
        for root in roots
    ]
    details: dict[str, PreflightDetailValue] = {"roots": root_lines}

    missing_env_roots = [root for root in roots if root.env_override and not root.exists]
    if missing_env_roots:
        details["reason"] = "configured ingest root does not exist"
        return RuntimePreflightCheck(
            id="ingest_registry",
            label="Ingest registry",
            required=True,
            status="NOT_READY",
            summary="Configured graph-ingest root is missing",
            details=details,
        )

    unreadable_roots = [root for root in roots if root.exists and not root.readable]
    if unreadable_roots:
        details["reason"] = "ingest root exists but is not readable"
        return RuntimePreflightCheck(
            id="ingest_registry",
            label="Ingest registry",
            required=True,
            status="NOT_READY",
            summary="Graph-ingest root is unreadable",
            details=details,
        )

    try:
        runs = discover_graph_ingest_runs(repo_root)
    except GraphIngestRunRegistryError as exc:
        details["reason"] = str(exc)
        return RuntimePreflightCheck(
            id="ingest_registry",
            label="Ingest registry",
            required=True,
            status="NOT_READY",
            summary="Graph-ingest discovery failed",
            details=details,
        )

    details["discovered_runs"] = len(runs)
    existing_roots = [root for root in roots if root.exists]
    if not existing_roots:
        details["reason"] = (
            "configured ingest root does not exist"
            if any(root.env_override for root in roots)
            else "default ingest root does not exist"
        )
        return RuntimePreflightCheck(
            id="ingest_registry",
            label="Ingest registry",
            required=True,
            status="NOT_READY",
            summary="Graph-ingest root is missing or unreadable",
            details=details,
        )
    if not runs:
        return RuntimePreflightCheck(
            id="ingest_registry",
            label="Ingest registry",
            required=True,
            status="EMPTY",
            summary="Ingest roots are valid; 0 runs discovered",
            details=details,
        )
    return RuntimePreflightCheck(
        id="ingest_registry",
        label="Ingest registry",
        required=True,
        status="READY",
        summary=f"Discovered {len(runs)} ingest run(s)",
        details=details,
    )


def _check_source_roots() -> RuntimePreflightCheck:
    details: dict[str, PreflightDetailValue] = {}
    roots_reported: list[str] = []

    extract_root = config.extract_promote_source_root()
    if extract_root is not None:
        exists = extract_root.exists()
        readable = exists and os.access(extract_root, os.R_OK)
        roots_reported.append(
            f"{EXTRACT_PROMOTE_SOURCE_ROOT_ENV}={extract_root} "
            f"exists={exists} readable={readable}"
        )
        if not exists:
            details["missing_root"] = str(extract_root)
    else:
        roots_reported.append(f"{EXTRACT_PROMOTE_SOURCE_ROOT_ENV}=unset")

    ingest_env = os.environ.get(GRAPH_INGEST_RUNS_ENV, "").strip()
    if ingest_env:
        roots_reported.append(f"{GRAPH_INGEST_RUNS_ENV}={ingest_env}")

    details["configured_roots"] = roots_reported
    if details.get("missing_root"):
        return RuntimePreflightCheck(
            id="source_roots",
            label="Product-local source roots",
            required=False,
            status="NOT_READY",
            summary="Configured extract/promote source root does not exist",
            details=details,
        )
    return RuntimePreflightCheck(
        id="source_roots",
        label="Product-local source roots",
        required=False,
        status="READY",
        summary="Configured source roots reported",
        details=details,
    )
