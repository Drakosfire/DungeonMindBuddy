"""SQL repository for World-owned Combat encounter records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.combat_encounters.types import CombatEncounterRecord
from application_state.errors import ApplicationStateIntegrityError

_COLUMNS = """
    encounter_id, world_id, campaign_id, session_n, revision,
    ruleset_snapshot, ruleset_digest, draft, created_at, updated_at
"""


def _record(row: dict) -> CombatEncounterRecord:
    payload = {
        "encounter_id": row["encounter_id"],
        "world_id": row["world_id"],
        "campaign_id": row["campaign_id"],
        "session": row["session_n"],
        "revision": row["revision"],
        "ruleset": row["ruleset_snapshot"],
        "ruleset_digest": row["ruleset_digest"],
        "draft": row["draft"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return CombatEncounterRecord.model_validate(payload)


def insert_encounter(conn: psycopg.Connection, record: CombatEncounterRecord) -> CombatEncounterRecord:
    conn.execute(
        f"""
        INSERT INTO combat.encounter (
            {_COLUMNS}
        ) VALUES (
            %(encounter_id)s, %(world_id)s, %(campaign_id)s, %(session_n)s,
            %(revision)s, %(ruleset_snapshot)s, %(ruleset_digest)s, %(draft)s,
            %(created_at)s, %(updated_at)s
        )
        """,
        {
            "encounter_id": record.encounter_id,
            "world_id": record.world_id,
            "campaign_id": record.campaign_id,
            "session_n": record.session,
            "revision": record.revision,
            "ruleset_snapshot": Jsonb(record.ruleset.model_dump(mode="json", by_alias=True)),
            "ruleset_digest": record.ruleset_digest,
            "draft": Jsonb(record.draft.model_dump(mode="json", by_alias=True)),
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        },
    )
    saved = get_encounter(conn, encounter_id=record.encounter_id, world_id=record.world_id)
    if saved is None:
        raise ApplicationStateIntegrityError("Combat encounter insert did not persist")
    return saved


def get_encounter(
    conn: psycopg.Connection, *, encounter_id: UUID, world_id: str
) -> CombatEncounterRecord | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM combat.encounter WHERE encounter_id = %s AND world_id = %s",
            (encounter_id, world_id),
        )
        row = cur.fetchone()
    return None if row is None else _record(row)


def list_encounters(conn: psycopg.Connection, *, world_id: str) -> list[CombatEncounterRecord]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_COLUMNS}
            FROM combat.encounter
            WHERE world_id = %s
            ORDER BY updated_at DESC, encounter_id ASC
            """,
            (world_id,),
        )
        rows = cur.fetchall()
    return [_record(row) for row in rows]


def cas_replace_draft(
    conn: psycopg.Connection,
    *,
    encounter_id: UUID,
    world_id: str,
    expected_revision: int,
    draft: dict,
    updated_at: datetime,
) -> CombatEncounterRecord | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE combat.encounter
            SET draft = %(draft)s,
                revision = revision + 1,
                updated_at = %(updated_at)s
            WHERE encounter_id = %(encounter_id)s
              AND world_id = %(world_id)s
              AND revision = %(expected_revision)s
            RETURNING {_COLUMNS}
            """,
            {
                "draft": Jsonb(draft),
                "updated_at": updated_at,
                "encounter_id": encounter_id,
                "world_id": world_id,
                "expected_revision": expected_revision,
            },
        )
        row = cur.fetchone()
    return None if row is None else _record(row)
