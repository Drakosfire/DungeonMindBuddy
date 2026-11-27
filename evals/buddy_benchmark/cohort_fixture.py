"""Validate retained App fixture inputs before an owned cohort clone is opened."""
from __future__ import annotations

from hashlib import sha256
import json
from uuid import UUID


def load_build_fixture(config, base, *, world, history_pin, history_base=None):
    """Bind retained Build rows to the same history the ordinary route will reopen."""
    from .workflow import read_pin, require_pinned_history

    if set(config) != {"conversation_export", "page_export"}:
        raise ValueError("Build fixture requires pinned conversation and page exports")
    bundle = json.loads(read_pin(config["conversation_export"], base))
    page = json.loads(read_pin(config["page_export"], base))
    history_pin = json.loads(read_pin(history_pin, history_base if history_base is not None else base))

    if set(bundle) != {"conversation", "turns", "references", "proposals"} or (
            len(bundle["conversation"]) != 1):
        raise ValueError("Build fixture must contain exactly one conversation")
    conversation = bundle["conversation"][0]
    conversation_id = conversation["conversation_id"]
    UUID(conversation_id)
    if conversation["world_id"] != world or conversation["status"] != "active":
        raise ValueError("Build fixture conversation must be active in the pinned World")
    turns = bundle["turns"]
    turn_ids = {row["turn_id"] for row in turns}
    if len(turn_ids) != len(turns) or any(
            row["world_id"] != world or row["conversation_id"] != conversation_id
            or row["sequence"] >= conversation["next_turn_sequence"]
            for row in turns):
        raise ValueError("Build fixture turns do not belong to the pinned conversation")
    require_pinned_history({
        "active_conversation_id": conversation_id,
        "turns": [{**row, "lifecycle_status": row["status"]} for row in turns],
    }, history_pin, allow_interrupted=True)
    references = bundle["references"]
    reference_keys = {(row["turn_id"], row["reference_role"], row["ordinal"]) for row in references}
    if len(reference_keys) != len(references) or any(row["turn_id"] not in turn_ids for row in references):
        raise ValueError("Build fixture contains duplicate or unrelated turn references")
    if any(row["world_id"] != world or row["conversation_id"] != conversation_id
           for row in bundle["proposals"]):
        raise ValueError("Build fixture contains an unrelated proposal")

    obj, revision, witness = page["object"], page["revision"], page["reference"]
    def binds_page(reference):
        return (
            reference["kind"] == "build" and reference["resolution"] == "resolved"
            and reference["object_id"] == obj["work_object_id"]
            and reference["revision"] == str(obj["object_revision"])
            and reference["content_sha256"] == revision["content_sha256"]
            and reference["object_revision"] in (None, obj["object_revision"])
            and reference["work_revision_id"] in (None, revision["work_revision_id"])
        )

    if (obj["world_id"] != world or revision["world_id"] != world
            or obj["kind"] != "worldbuilding_source" or obj["status"] != "active"
            or obj["work_object_id"] != revision["work_object_id"]
            or obj["current_revision_id"] != revision["work_revision_id"]
            or sha256(revision["markdown"].encode()).hexdigest() != revision["content_sha256"]
            or not binds_page(witness) or not any(map(binds_page, references))):
        raise ValueError("Build fixture page differs from its retained turn reference")
    return bundle, page


def _insert_rows(conn, relation, rows):
    from psycopg import sql
    from psycopg.types.json import Jsonb

    if not rows:
        return
    table = sql.Identifier(*relation)
    columns = sql.SQL(", ").join(map(sql.Identifier, rows[0]))
    if any(row.keys() != rows[0].keys() for row in rows):
        raise ValueError("Build fixture rows have inconsistent columns")
    conn.execute(sql.SQL(
        "INSERT INTO {table} ({columns}) SELECT {columns} "
        "FROM jsonb_populate_recordset(NULL::{table}, %s)"
    ).format(table=table, columns=columns), (Jsonb(rows),))


def restore_build_fixture(dsn, owned_app, bundle, page, *, seed):
    """Restore an exact Build fixture in one transaction on a verified clone."""
    import psycopg

    from .disposable_database import _identity

    conversation = bundle["conversation"][0]
    world = conversation["world_id"]
    conversation_id = conversation["conversation_id"]
    obj, revision = page["object"], page["revision"]
    document = obj["work_object_id"]
    database = owned_app["database"]
    if not database.startswith("benchmark_run_"):
        raise ValueError("Build fixture requires an owned benchmark clone")

    with psycopg.connect(dsn) as conn:
        if (conn.info.dbname != database
                or _identity(conn, database) != (owned_app["oid"], owned_app["system_identifier"])):
            raise ValueError("Build fixture App database differs from owned clone")
        saved = conn.execute("""
            SELECT w.object_revision, r.content_sha256
            FROM content.work_object w
            JOIN content.work_revision r ON r.work_revision_id = w.current_revision_id
            WHERE w.work_object_id = %s AND w.world_id = %s AND w.kind = %s
            FOR UPDATE OF w
        """, (document, world, obj["kind"])).fetchone()
        if saved != (seed["page_revision"], seed["page_sha256"]):
            raise ValueError("Build fixture seed page differs from pin")
        copy = conn.execute("""
            SELECT working_copy_revision, content_sha256
            FROM content.working_copy WHERE work_object_id = %s FOR UPDATE
        """, (document,)).fetchone()
        expected_copy = seed["working_copy"]
        if (list(copy) if copy else None) != expected_copy:
            raise ValueError("Build fixture seed working copy differs from pin")
        pointer = conn.execute("""
            SELECT active_conversation_id::text, pointer_revision
            FROM agent.world_state WHERE world_id = %s FOR UPDATE
        """, (world,)).fetchone()
        if pointer != (seed["active_conversation_id"], seed["pointer_revision"]):
            raise ValueError("Build fixture seed conversation pointer differs from pin")

        if pointer[0] is not None:
            archived = conn.execute("""
                UPDATE agent.conversation
                SET status = 'archived', archived_at = now(), updated_at = now(), revision = revision + 1
                WHERE conversation_id = %s AND world_id = %s AND status = 'active'
            """, (pointer[0], world)).rowcount
            if archived != 1:
                raise ValueError("Build fixture seed conversation was not active")
        if copy is not None:
            conn.execute("DELETE FROM content.working_copy WHERE work_object_id = %s", (document,))
        _insert_rows(conn, ("content", "work_revision"), [revision])
        conn.execute("""
            UPDATE content.work_object
            SET current_revision_id = %s, object_revision = %s, updated_at = %s
            WHERE world_id = %s AND work_object_id = %s
        """, (revision["work_revision_id"], obj["object_revision"], obj["updated_at"], world, document))
        _insert_rows(conn, ("agent", "conversation"), [conversation])
        _insert_rows(conn, ("agent", "turn"), bundle["turns"])
        _insert_rows(conn, ("agent", "turn_reference"), bundle["references"])
        _insert_rows(conn, ("agent", "build_proposal"), bundle["proposals"])
        conn.execute("""
            UPDATE agent.world_state
            SET active_conversation_id = %s, pointer_revision = pointer_revision + 1, updated_at = now()
            WHERE world_id = %s
        """, (conversation_id, world))
    return {"conversation_id": conversation_id, "document_id": document,
            "page_revision": obj["object_revision"], "turn_count": len(bundle["turns"])}
