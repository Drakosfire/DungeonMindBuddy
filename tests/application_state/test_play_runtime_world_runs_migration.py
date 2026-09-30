from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest
from alembic import command
from sqlalchemy.exc import ProgrammingError

from application_state.cli import alembic_config

pytest_plugins = ["tests.application_state.conftest"]


def _insert_run(
    dsn: str,
    *,
    run_id: str,
    campaign_id: str | None,
    world_id: str | None = None,
) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            """
            INSERT INTO play.run (
                run_id, campaign_id, world_id, playable_work_object_id,
                playable_revision_n, playable_work_revision_id,
                playable_content_sha256, run_revision, progress,
                rebased_from_run_revision, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, 1, %s, %s, 1, '{}'::jsonb, NULL,
                now(), now()
            )
            """,
            (run_id, campaign_id, world_id, str(uuid4()), str(uuid4()), "a" * 64),
        )


def test_upgrade_preserves_unbound_campaign_rows_and_downgrade_is_guarded(
    application_state_dsn: str,
) -> None:
    command.downgrade(alembic_config(), "20260929_0008")
    legacy_run_id = str(uuid4())
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        conn.execute(
            """
            INSERT INTO play.run (
                run_id, campaign_id, playable_work_object_id,
                playable_revision_n, playable_work_revision_id,
                playable_content_sha256, run_revision, progress,
                rebased_from_run_revision, created_at, updated_at
            ) VALUES (%s, %s, %s, 1, %s, %s, 1, '{}'::jsonb, NULL, now(), now())
            """,
            (
                legacy_run_id,
                "demo-world-a",
                str(uuid4()),
                str(uuid4()),
                "b" * 64,
            ),
        )

    command.upgrade(alembic_config(), "head")
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        legacy = conn.execute(
            "SELECT campaign_id, world_id FROM play.run WHERE run_id = %s",
            (legacy_run_id,),
        ).fetchone()
    assert legacy == ("demo-world-a", None)

    world_run_id = str(uuid4())
    _insert_run(
        application_state_dsn,
        run_id=world_run_id,
        campaign_id=None,
        world_id="demo-world-a",
    )
    with pytest.raises(
        ProgrammingError,
        match="cannot downgrade while World-owned Play Runs exist",
    ):
        command.downgrade(alembic_config(), "20260929_0008")

    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        assert conn.execute(
            """
            SELECT campaign_id, world_id FROM play.run WHERE run_id = %s
            """,
            (world_run_id,),
        ).fetchone() == (None, "demo-world-a")
        conn.execute("DELETE FROM play.run WHERE run_id = %s", (world_run_id,))

    command.downgrade(alembic_config(), "20260929_0008")
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        legacy_after_downgrade = conn.execute(
            "SELECT campaign_id FROM play.run WHERE run_id = %s",
            (legacy_run_id,),
        ).fetchone()
        world_column = conn.execute(
            """
            SELECT count(*) FROM information_schema.columns
            WHERE table_schema = 'play' AND table_name = 'run'
              AND column_name = 'world_id'
            """
        ).fetchone()[0]
    assert legacy_after_downgrade == ("demo-world-a",)
    assert world_column == 0
    command.upgrade(alembic_config(), "head")
