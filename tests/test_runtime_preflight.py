from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from apps.live_control_server.config import (
    WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV,
    WORLD_GRAPH_AUTHORITY_ENV,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
    DirectWorldGraphReadError,
    WorldHeadSummary,
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


def test_ingest_unavailable_when_app_state_dsn_unset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "UNAVAILABLE"
    assert report.status == "NOT READY"


def test_ingest_unavailable_when_configured_app_state_dsn_unreachable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)
    monkeypatch.setenv(
        APPLICATION_STATE_DSN_ENV,
        "postgresql://buddy:secret@127.0.0.1:1/dungeonbuddy_application_state"
        "?connect_timeout=2",
    )

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "UNAVAILABLE"
    assert report.status == "NOT READY"


def test_ingest_not_ready_when_ingest_schema_behind(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    import psycopg
    from alembic import command

    from application_state.cli import _current_and_head, alembic_config

    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)
    try:
        command.downgrade(alembic_config(), "20260825_0004")
        current, head = _current_and_head(application_state_dsn)
        assert current == "20260825_0004"
        assert current != head
        with psycopg.connect(application_state_dsn) as conn:
            ingest_schema = conn.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'ingest'"
            ).fetchone()
        assert ingest_schema is None
        report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
        ingest = next(check for check in report.checks if check.id == "ingest_registry")
        assert ingest.status == "NOT_READY"
        assert report.status == "NOT READY"
        assert "behind" in ingest.summary.lower()
    finally:
        command.upgrade(alembic_config(), "head")


def test_ingest_empty_when_schema_current_and_zero_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "EMPTY"
    assert ingest.details.get("run_count") == 0
    assert "0 runs" in ingest.summary


def test_ingest_integrity_when_persisted_row_malformed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    import psycopg

    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            """
            INSERT INTO ingest.run (
                run_id, schema_version, record_version, source_artifact_id,
                source_domain, status, revision, components, diagnostics, lineage
            ) VALUES (
                'er_preflight_bad', 'not-a-schema', '1.0', 'sa_world_1',
                'worldbuilding', 'draft', 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb
            )
            """
        )
        conn.commit()

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "INTEGRITY_ERROR"
    assert report.status == "NOT READY"


def test_format_report_preserves_redacted_dsn_host(
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
    assert "localhost:5432/app" in rendered
    assert "<redacted-dsn>" not in rendered


def test_app_state_isolation_rejection_surfaces_explicit_reason(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    world_dsn = (
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind"
    )
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, world_dsn)
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, world_dsn)
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    app_state = next(check for check in report.checks if check.id == "app_state")
    assert app_state.status == "NOT_READY"
    assert app_state.details.get("isolation") == "rejected"
    assert "dungeonmind" in app_state.summary.lower()
    assert report.status == "NOT READY"


def test_campaign_registry_not_configured_without_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)

    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    campaign = next(check for check in report.checks if check.id == "campaign_registry")
    assert campaign.status == "NOT_CONFIGURED"
    assert campaign.required is False


def test_genesis_receipt_without_head_reports_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.setenv(
        WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV,
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind",
    )

    integrity_exc = DirectWorldGraphReadError(
        "DungeonMind existing-world adoption receipt exists for world 'orphan' "
        "but no published head is present.",
        code="authority_integrity",
        status_code=500,
        diagnostics=[{"reason": "genesis_receipt_without_head", "world_id": "orphan"}],
    )

    with (
        patch(
            "apps.live_control_server.services.runtime_preflight.list_world_heads",
            return_value=[
                WorldHeadSummary(world_id="orphan", head_revision_id=None),
            ],
        ),
        patch(
            "apps.live_control_server.services.runtime_preflight._load_direct_authority_binding",
            side_effect=integrity_exc,
        ),
    ):
        report = run_runtime_preflight(
            repo_root=tmp_path,
            require_world="orphan",
            load_env=False,
        )

    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    assert world.status == "INTEGRITY_ERROR"
    assert "integrity_errors" in world.details
    assert report.status == "NOT READY"
    assert world.details.get("required_world") is None


def test_binding_authority_unavailable_is_not_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.setenv(
        WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV,
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind",
    )

    unavailable_exc = DirectWorldGraphReadError(
        "DungeonMind authority database is unavailable",
        code="authority_unavailable",
        status_code=503,
    )

    with (
        patch(
            "apps.live_control_server.services.runtime_preflight.list_world_heads",
            return_value=[
                WorldHeadSummary(world_id="eldyrwild", head_revision_id="rev-1"),
            ],
        ),
        patch(
            "apps.live_control_server.services.runtime_preflight._load_direct_authority_binding",
            side_effect=unavailable_exc,
        ),
    ):
        report = run_runtime_preflight(repo_root=tmp_path, load_env=False)

    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    assert world.status == "UNAVAILABLE"
    assert world.details.get("failure_stage") == "authority_binding"
    assert "integrity_errors" not in world.details
    assert report.status == "NOT READY"


def test_require_world_missing_reports_not_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.setenv(WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.setenv(
        WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV,
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind",
    )

    class FakeBinding:
        genesis = "existing_world_adoption"

    with (
        patch(
            "apps.live_control_server.services.runtime_preflight.list_world_heads",
            return_value=[
                WorldHeadSummary(world_id="otherworld", head_revision_id="rev-1")
            ],
        ),
        patch(
            "apps.live_control_server.services.runtime_preflight._load_direct_authority_binding",
            return_value=FakeBinding(),
        ),
    ):
        report = run_runtime_preflight(
            repo_root=tmp_path,
            require_world="eldyrwild",
            load_env=False,
        )

    world = next(check for check in report.checks if check.id == "dungeonmind_world")
    assert world.status == "NOT_READY"
    assert world.details.get("required_world") == "eldyrwild"
    assert report.status == "NOT READY"


def test_cli_exit_code_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from scripts.preflight_surface_runtime import main

    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)

    with patch(
        "scripts.preflight_surface_runtime.run_runtime_preflight",
        return_value=RuntimePreflightReport(status="READY", checks=()),
    ):
        assert main(["--no-dotenv"]) == 0


def test_cli_exit_code_not_ready_on_required_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from scripts.preflight_surface_runtime import main

    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    monkeypatch.delenv(WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV, raising=False)

    with patch(
        "scripts.preflight_surface_runtime.run_runtime_preflight",
        return_value=RuntimePreflightReport(
            status="NOT READY",
            checks=(
                RuntimePreflightCheck(
                    id="ingest_registry",
                    label="Ingest registry",
                    required=True,
                    status="NOT_READY",
                    summary="missing root",
                ),
            ),
        ),
    ):
        assert main(["--no-dotenv"]) == 1


def test_list_world_heads_uses_repository_ports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads

    class FakeHead:
        def __init__(self, world_id: str, head_revision_id: str) -> None:
            self.world_id = world_id
            self.head_revision_id = head_revision_id

    class FakeWorldGraph:
        def list_heads(self) -> list[FakeHead]:
            return [FakeHead("alpha", "head-a")]

        def get_head(self, world_id: str) -> FakeHead | None:
            if world_id == "alpha":
                return FakeHead("alpha", "head-a")
            if world_id == "beta":
                return None
            return None

    class FakeAdoptions:
        def list_world_ids(self) -> list[str]:
            return ["beta"]

    class FakeInit:
        def list_world_ids(self) -> list[str]:
            return []

    class FakeBundle:
        world_graph = FakeWorldGraph()
        existing_world_adoptions = FakeAdoptions()
        reviewed_world_initializations = FakeInit()

    monkeypatch.setattr(
        world_graph_reads,
        "PostgresRepositoryBundle",
        lambda _database: FakeBundle(),
    )
    monkeypatch.setattr(
        world_graph_reads,
        "PostgresDatabase",
        lambda _url: object(),
    )

    summaries = world_graph_reads.list_world_heads(
        database_url="postgresql://u:p@127.0.0.1:5432/dungeonmind"
    )
    assert [(item.world_id, item.head_revision_id) for item in summaries] == [
        ("alpha", "head-a"),
        ("beta", None),
    ]
