"""The DB-only World owner fences older file-authoritative readers."""
import psycopg
import pytest
from alembic import command
from application_state import cli
from application_state.errors import ApplicationStateMigrationError
from application_state.world_catalog import service


def test_cutover_fence_preserves_rows_and_requires_forward_recovery(application_state_dsn, monkeypatch):
    before = service.create_world(name="Retained World", owner_subject="subject:owner")
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE application_state.schema_migrations SET version_num='20261030_0099'")
    cli.upgrade_to_head(dsn=application_state_dsn)
    assert cli._read_current_revision(application_state_dsn) == "20261031_0100"
    assert service.get_world(before.record.world_id) == before
    with monkeypatch.context() as patch:
        patch.setattr(cli, "_alembic_head", lambda: "20261030_0099")
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=application_state_dsn)
    with pytest.raises(RuntimeError, match="World catalog cutover.*recovery forward"):
        command.downgrade(cli.alembic_config(), "20261030_0099")
    cli.assert_at_head(dsn=application_state_dsn)
    assert service.get_world(before.record.world_id) == before
