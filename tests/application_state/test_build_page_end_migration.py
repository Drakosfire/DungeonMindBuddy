"""Page-end records cannot be opened by an older strict runtime reader."""
import pytest
from alembic import command
from application_state import cli
from application_state.errors import ApplicationStateMigrationError


def test_page_end_reader_fence_requires_forward_recovery(application_state_dsn,monkeypatch):
    assert cli._read_current_revision(application_state_dsn)=="20261029_0090"
    cli.assert_at_head(dsn=application_state_dsn)
    with monkeypatch.context() as patch:
        patch.setattr(cli,"_alembic_head",lambda:"20261028_0089")
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=application_state_dsn)
    with pytest.raises(RuntimeError,match="page-end.*recovery forward"):
        command.downgrade(cli.alembic_config(),"20261028_0089")
    cli.assert_at_head(dsn=application_state_dsn)
