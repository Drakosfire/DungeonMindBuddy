"""add World-wide Agent turn receipts

Revision ID: 20261001_0011
Revises: 20261001_0010
Create Date: 2026-10-01

"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from alembic import op

revision = "20261001_0011"
down_revision = "20261001_0010"
branch_labels = None
depends_on = None


def _fingerprint(world_id: str, user_text: str, provenance: Mapping[str, Any]) -> str:
    """Frozen equivalent of turn_idempotency_fingerprint for migration backfill."""

    payload = {
        "world_id": world_id,
        "user_text": user_text,
        "provenance": provenance,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _reference(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "resolution": row["resolution"],
        "kind": row["kind"],
        "object_id": row["object_id"],
        "revision": row["revision"],
        "content_sha256": row["content_sha256"],
    }


def _backfill_idempotency_fingerprints() -> None:
    connection = op.get_bind()
    rows = connection.exec_driver_sql(
        """
        SELECT
            t.turn_id, t.world_id, t.user_text, t.surface_resolution, t.surface_id,
            r.reference_role, r.ordinal, r.resolution, r.kind, r.object_id,
            r.revision, r.content_sha256
        FROM agent.turn AS t
        LEFT JOIN agent.turn_reference AS r ON r.turn_id = t.turn_id
        ORDER BY t.turn_id,
            CASE r.reference_role WHEN 'primary' THEN 0 WHEN 'supporting' THEN 1 ELSE 2 END,
            r.ordinal
        """
    ).mappings().all()

    current_turn_id = None
    current: dict[str, Any] | None = None

    def persist(record: dict[str, Any]) -> None:
        primary = record["primary_work"]
        selected = record["selected_object"]
        if primary is None or selected is None:
            raise RuntimeError(
                "cannot migrate Agent turn without typed primary and selected provenance"
            )
        provenance = {
            "world_id": record["world_id"],
            "surface_resolution": record["surface_resolution"],
            "surface_id": record["surface_id"],
            "primary_work": primary,
            "supporting_work": record["supporting_work"],
            "selected_object": selected,
        }
        digest = _fingerprint(record["world_id"], record["user_text"], provenance)
        connection.exec_driver_sql(
            "UPDATE agent.turn SET idempotency_fingerprint = %s WHERE turn_id = %s",
            (digest, record["turn_id"]),
        )

    for row in rows:
        if current_turn_id != row["turn_id"]:
            if current is not None:
                persist(current)
            current_turn_id = row["turn_id"]
            current = {
                "turn_id": row["turn_id"],
                "world_id": row["world_id"],
                "user_text": row["user_text"],
                "surface_resolution": row["surface_resolution"],
                "surface_id": row["surface_id"],
                "primary_work": None,
                "supporting_work": [],
                "selected_object": None,
            }
        if row["reference_role"] is None:
            continue
        reference = _reference(row)
        if row["reference_role"] == "primary":
            current["primary_work"] = reference
        elif row["reference_role"] == "supporting":
            current["supporting_work"].append(reference)
        elif row["reference_role"] == "selected":
            current["selected_object"] = reference
    if current is not None:
        persist(current)


def upgrade() -> None:
    connection = op.get_bind()
    duplicate = connection.exec_driver_sql(
        """
        SELECT world_id, idempotency_key, count(*) AS copies
        FROM agent.turn
        GROUP BY world_id, idempotency_key
        HAVING count(*) > 1
        LIMIT 1
        """
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "cannot enforce World-wide Agent turn idempotency: existing duplicate "
            f"world_id={duplicate[0]!r}, idempotency_key={duplicate[1]!r}; "
            "preserve and resolve these receipts before retrying the migration"
        )

    op.execute("ALTER TABLE agent.turn ADD COLUMN idempotency_fingerprint TEXT NULL")
    _backfill_idempotency_fingerprints()
    op.execute(
        "ALTER TABLE agent.turn ALTER COLUMN idempotency_fingerprint SET NOT NULL"
    )
    op.execute(
        """
        ALTER TABLE agent.turn
        ADD CONSTRAINT agent_turn_idempotency_fingerprint_check
        CHECK (idempotency_fingerprint ~ '^[0-9a-f]{64}$')
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX agent_turn_world_idempotency_unique
        ON agent.turn (world_id, idempotency_key)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS agent.agent_turn_world_idempotency_unique")
    op.execute(
        "ALTER TABLE agent.turn DROP CONSTRAINT IF EXISTS "
        "agent_turn_idempotency_fingerprint_check"
    )
    op.execute("ALTER TABLE agent.turn DROP COLUMN IF EXISTS idempotency_fingerprint")
