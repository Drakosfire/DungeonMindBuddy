"""The established schema-head boundary fences older readers of new targets."""
import pytest
from alembic import command
from application_state import cli
from application_state.errors import ApplicationStateMigrationError


def test_body_target_reader_fence_requires_forward_recovery(application_state_dsn,monkeypatch):
    assert cli._read_current_revision(application_state_dsn)=="20261028_0089"
    cli.assert_at_head(dsn=application_state_dsn)
    with monkeypatch.context() as patch:
        patch.setattr(cli,"_alembic_head",lambda:"20261028_0088")
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=application_state_dsn)
    with pytest.raises(RuntimeError,match="whole-page.*recovery forward"):
        command.downgrade(cli.alembic_config(),"20261028_0088")
    cli.assert_at_head(dsn=application_state_dsn)
