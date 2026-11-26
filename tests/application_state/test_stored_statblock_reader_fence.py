"""Application-state readiness protects persisted stored evidence receipts."""

import psycopg
import pytest

from application_state import cli
from application_state.errors import ApplicationStateMigrationError


def test_previous_reader_refuses_stored_statblock_schema(application_state_dsn, monkeypatch):
    with psycopg.connect(application_state_dsn) as conn:
        cli.assert_connection_at_head(conn)
        assert cli._revision_from_connection(conn) == "20261126_0197"
        monkeypatch.setattr(cli, "_alembic_head", lambda: "20261123_0196")
        with pytest.raises(ApplicationStateMigrationError, match="schema is behind Alembic head"):
            cli.assert_connection_at_head(conn)
