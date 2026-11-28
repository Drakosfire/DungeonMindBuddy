"""Readiness rejects readers predating durable surface intent."""

import psycopg
import pytest

from application_state import cli
from application_state.errors import ApplicationStateMigrationError


def test_previous_reader_refuses_surface_intent_schema(application_state_dsn, monkeypatch):
    with psycopg.connect(application_state_dsn) as conn:
        cli.assert_connection_at_head(conn)
        monkeypatch.setattr(cli, "_alembic_head", lambda: "20261127_0201")
        with pytest.raises(ApplicationStateMigrationError, match="schema is behind Alembic head"):
            cli.assert_connection_at_head(conn)
