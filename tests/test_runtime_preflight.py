from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from apps.live_control_server.config import (
    WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV,
    WORLD_GRAPH_AUTHORITY_ENV,
)
from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestRegistryRootStatus,
)
from apps.live_control_server.services.runtime_preflight import (
    RuntimePreflightCheck,
    RuntimePreflightReport,
    format_runtime_preflight_report,
    overall_status,
    redact_dsn,
    run_runtime_preflight,
)
from application_state.config import APPLICATION_STATE_DSN_ENV


def test_redact_dsn_hides_password() -> None:
    dsn = "postgresql://dungeonmind:super-secret@127.0.0.1:54329/dungeonmind"
    redacted = redact_dsn(dsn)
    assert "super-secret" not in redacted
    assert "***" in redacted
    assert "127.0.0.1:54329/dungeonmind" in redacted


def test_overall_status_ready_when_required_checks_ready_or_empty() -> None:
    checks = (
        RuntimePreflightCheck(
            id="a",
            label="A",
            required=True,
            status="READY",
            summary="ok",
        ),
        RuntimePreflightCheck(
            id="b",
            label="B",
            required=True,
            status="EMPTY",
            summary="empty",
        ),
        RuntimePreflightCheck(
            id="c",
            label="C",
            required=False,
            status="NOT_READY",
            summary="info only",
        ),
    )
    assert overall_status(checks) == "READY"


def test_overall_status_not_ready_when_required_check_fails() -> None:
    checks = (
        RuntimePreflightCheck(
            id="a",
            label="A",
            required=True,
            status="NOT_CONFIGURED",
            summary="missing",
        ),
    )
    assert overall_status(checks) == "NOT READY"


def test_dungeonmind_not_configured_when_dsn_unset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    assert world.status == "NOT_CONFIGURED"
    assert report.status == "NOT READY"


def test_ingest_empty_when_default_root_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "EMPTY"
    assert "0 runs" in ingest.summary or "0 runs discovered" in ingest.summary


def test_ingest_not_ready_when_env_root_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", "missing/ingest/root")

    with patch(
        "apps.live_control_server.services.runtime_preflight.inspect_graph_ingest_registry_roots",
        return_value=[
            GraphIngestRegistryRootStatus(
                configured_path="missing/ingest/root",
                resolved_path=str(tmp_path / "missing/ingest/root"),
                exists=False,
                readable=False,
                env_override=True,
            )
        ],
    ):
        report = run_runtime_preflight(repo_root=tmp_path, load_env=False)

    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "NOT_READY"
    assert report.status == "NOT READY"


def test_format_report_redacts_secret_bearing_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "password-should-not-leak"
    dsn = f"postgresql://user:{secret}@localhost:5432/app"
    check = RuntimePreflightCheck(
        id="app_state",
        label="Buddy application state",
        required=True,
        status="READY",
        summary="ready",
        details={"database_url_redacted": redact_dsn(dsn)},
    )
    rendered = format_runtime_preflight_report(
        RuntimePreflightReport(status="READY", checks=(check,))
    )
    assert secret not in rendered
