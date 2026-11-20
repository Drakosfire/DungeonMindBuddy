"""PostgreSQL ownership boundary for hosted World creation."""

import psycopg
import pytest


def test_creation_policy_starts_disabled_and_requires_complete_positive_limits(application_state_dsn):
    with psycopg.connect(application_state_dsn) as conn:
        row = conn.execute(
            "SELECT enabled, owner_world_limit, global_world_limit FROM workspace.hosted_world_creation_policy"
        ).fetchone()
        assert row == (False, None, None)
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute("UPDATE workspace.hosted_world_creation_policy SET enabled = true")
        conn.execute("""
            UPDATE workspace.hosted_world_creation_policy
            SET enabled=true, owner_world_limit=3, global_world_limit=12,
                owner_rate_limit=4, global_rate_limit=20, rate_window_seconds=60
        """)
        assert conn.execute("SELECT enabled FROM workspace.hosted_world_creation_policy").fetchone() == (True,)


def test_admission_cannot_reference_an_unregistered_world(application_state_dsn):
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                conn.execute(
                    "INSERT INTO workspace.hosted_world_admission (world_id, creator_subject) VALUES (%s, %s)",
                    ("missing-world", "owner"),
                )
