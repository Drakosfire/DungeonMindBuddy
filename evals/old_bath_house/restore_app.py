"""Restore the scoped Old Bath House application rows into disposable state."""

import argparse
import json
import os
from hashlib import sha256
from pathlib import Path

from .isolation import APP_DSN, _database_identity

TABLES = (
    "content.work_object",
    "content.work_revision",
    "content.working_copy",
    "agent.conversation",
    "agent.turn",
    "agent.conversation_draft_revision",
    "agent.conversation_variant_review",
    "agent.conversation_variant_save",
)


def media_rows(path, digest, pins):
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Scoped media export checksum differs")
    media = json.loads(data)["media"]
    urls = {pins[role]["imageUrl"] for role in ("boss", "minion")}
    ids = {row["asset_id"] for row in media["asset"]}
    if (
        len(media["asset"]) != 2 or len(media["storage"]) != 2
        or pins["boss"]["assetId"] not in ids
        or ids != {row["asset_id"] for row in media["storage"]}
        or {row["receipt"]["delivery_url"] for row in media["storage"]} != urls
        or any(row["state"] != "ready" or row["receipt"]["visibility"] != "public"
               for row in media["storage"])
    ):
        raise ValueError("Saved portrait records differ from the source pins")
    return {
        "media.asset": [dict(row, owner_id="local_operator") for row in media["asset"]],
        "media.storage": media["storage"],
    }

def revision_lineage(path, digest, pins):
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Meatling revision lineage checksum differs")
    lineage = json.loads(data)
    operation, = lineage["operations"]
    payload = operation["payload"]
    minion = pins["minion"]
    if (
        operation["world_id"] != pins["worldId"] or operation["draft_id"] != minion["draftId"]
        or operation["operation_id"] != minion["revisionOperation"] or operation["state"] != "committed"
        or payload["origin"] != minion["originalLocator"] or payload["result"] != minion["locator"]
    ):
        raise ValueError("Meatling revision receipt differs from the source pins")
    return lineage


def restore(path, digest, dsn, identity, pins, *, assets=None):
    from psycopg import connect, sql
    from psycopg.types.json import Jsonb

    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Scoped benchmark export checksum differs")
    rows = json.loads(data)
    if set(rows) != set(TABLES) or any(not rows[table] for table in TABLES):
        raise ValueError("Scoped export does not contain the expected tables")
    plan, = rows["content.work_object"]
    conversation, = rows["agent.conversation"]
    turn, = rows["agent.turn"]
    review, = rows["agent.conversation_variant_review"]
    boss = pins["boss"]
    if (
        plan["work_object_id"] != pins["documentId"]
        or plan["world_id"] != pins["worldId"]
        or conversation["world_id"] != pins["worldId"]
        or conversation["conversation_id"] != boss["conversationId"]
        or turn["turn_id"] != boss["turnId"]
        or turn["conversation_id"] != boss["conversationId"]
        or review["review_id"] != boss["reviewId"]
        or any(row["work_object_id"] != pins["documentId"]
               for table in TABLES[1:3] for row in rows[table])
        or any(row["turn_id"] != boss["turnId"] for table in TABLES[5:] for row in rows[table])
    ):
        raise ValueError("Scoped export identities differ from the source pins")
    saved, = rows["agent.conversation_variant_save"]
    if saved["receipt"] != boss["baseLocator"]:
        raise ValueError("Saved statblock receipt differs from the source pin")
    _database_identity(dsn, identity, writable=True)
    current = plan["current_revision_id"]
    plan["current_revision_id"] = None
    if assets is not None:
        rows.update(assets)
    with connect(dsn) as connection:
        for table in (*TABLES, *(assets or ())):
            identifier = sql.Identifier(*table.split("."))
            statement = sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{}, %s)").format(
                identifier, identifier,
            )
            for row in rows[table]:
                connection.execute(statement, (Jsonb(row),))
        connection.execute(
            "UPDATE content.work_object SET current_revision_id = %s WHERE work_object_id = %s",
            (current, pins["documentId"]),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", required=True, type=Path)
    parser.add_argument("--rows-sha256", required=True)
    parser.add_argument("--database-identity", required=True, type=Path)
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--assets-sha256")
    parser.add_argument("--lineage", type=Path)
    parser.add_argument("--lineage-sha256")
    args = parser.parse_args()
    pins = json.loads(Path(__file__).with_name("source-pins.json").read_text())
    if bool(args.assets) != bool(args.assets_sha256):
        parser.error("--assets and --assets-sha256 must be supplied together")
    assets = media_rows(args.assets, args.assets_sha256, pins) if args.assets else None
    if bool(args.lineage) != bool(args.lineage_sha256):
        parser.error("--lineage and --lineage-sha256 must be supplied together")
    if args.lineage:
        lineage = revision_lineage(args.lineage, args.lineage_sha256, pins)
        assets = {**(assets or {}), "mechanics_revision.operation": lineage["operations"]}
    identity = json.loads(args.database_identity.read_text())
    restore(args.rows, args.rows_sha256, os.environ[APP_DSN],
            identity, pins, assets=assets)


if __name__ == "__main__":
    main()
