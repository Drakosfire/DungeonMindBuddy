"""Shared benchmark evidence operations; no question or provider policy."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path


ROW_KEYS = (
    "world_id", "conversation_id", "turn_id", "command_id",
    "reference_role", "ordinal", "version_num",
)


def immutable_save(directory: Path, name: str, value) -> None:
    """Create a checkpoint once; equal replay is allowed, replacement is not."""
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / (name + ".json")
    if target.exists():
        if json.loads(target.read_text()) != value:
            raise ValueError("checkpoint collision: " + name)
        return
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def row_inventory(dsn, *, readonly, keys=ROW_KEYS):
    """One exact repeatable-read inventory through the caller's read-only owner.

    Explicit routing keys preserve historical evidence formats. The database
    connection and isolation authorization remain with the existing caller.
    """
    from psycopg import sql

    result = {}
    with readonly(dsn) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        tables = conn.execute(
            "SELECT table_schema,table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema NOT IN "
            "('pg_catalog','information_schema') ORDER BY 1,2"
        ).fetchall()
        for table in tables:
            name = table["table_schema"] + "." + table["table_name"]
            rows = conn.execute(
                sql.SQL("SELECT row_to_json(t)::text AS body FROM {}.{} t").format(
                    sql.Identifier(table["table_schema"]),
                    sql.Identifier(table["table_name"]),
                )
            ).fetchall()
            inventory = []
            for row in rows:
                body = json.loads(row["body"])
                inventory.append({
                    "sha256": sha256(row["body"].encode()).hexdigest(),
                    "keys": {key: body[key] for key in keys if key in body},
                })
            result[name] = sorted(inventory, key=lambda row: row["sha256"])
    return result
