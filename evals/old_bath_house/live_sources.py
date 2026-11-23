"""Validate the pinned grounding and user turns for the live-provider replay."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re

GOLD_SHA256 = "e4f56188eb2997d75f226bcfe64c49bfd25ef9840bc4dbc5a11360e59530e1b1"
PAGE_PINS = {
    "792026bc-6600-4c2d-ae55-05c045d1502f": (
        "8df6ef11-5447-4678-9afb-6a3fcaa3c1a7",
        "ad8317e90cde73a8676efef3d22860e53871afe77a56cf08bce976dbbd994efc",
    ),
    "77940b05-c350-428a-88a3-2fc433ad6df0": (
        "ddf14d69-1388-4956-972b-a3d82b794db1",
        "45138529c6e89a72dc0974bfe316da93e5c36fe6b9d47349e2a872ba3151ffe4",
    ),
}
ORIGINAL_MEAT_MIND = (
    "sb_35f8bde426044fa681d82b638337409d",
    "rev_b7f54b5ea693404fa20cf8c8b65d20a0",
    "sha256:0c371a68acf117a6572271fded857d66985014685d57639b3c6ab3bd96fe4e7d",
)
MEAT_MIND_NODE = "ent:98f588a86679094d66927b75320bb6dd"
ORIGINAL_GRAPH_REVISION = "rev:5293c1b237a0064bd16fffd080bfa6b1"
OLD_BATH_HOUSE_PAGE = "792026bc-6600-4c2d-ae55-05c045d1502f"
PORTRAIT_PROMPT = (
    "Square fantasy bestiary portrait of the Edge Meat Mind in the Old Bath House. "
    "Pearlescent living tissue fuses to an ivory bath rim in cool steam and warm lamp light. "
    "A calm, watchful presence. No gore or text."
)


def live_manifest(core_head):
    if not re.fullmatch(r"rev:[0-9a-f]{32}", core_head):
        raise ValueError("Live benchmark requires a pinned Graph head")
    return {
        "coreHead": core_head,
        "pageId": OLD_BATH_HOUSE_PAGE,
        "meatMindNodeId": MEAT_MIND_NODE,
        "turns": read_user_turns(),
        "originalStatblockId": ORIGINAL_MEAT_MIND[0],
        "portraitPrompt": PORTRAIT_PROMPT,
    }


def verify_core_snapshot(dsn, head):
    from psycopg import connect

    with connect(dsn) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        row = connection.execute("""
            SELECT head_revision_id,
              EXISTS (SELECT 1 FROM dungeonmind.knowledge_revisions
                      WHERE space_id = 'elderwyld' AND revision_id = %s)
            FROM dungeonmind.knowledge_heads WHERE space_id = 'elderwyld'
        """, (ORIGINAL_GRAPH_REVISION,)).fetchone()
    if row != (head, True):
        raise ValueError("Live Core head or the original reference revision differs from its pin")


def read_user_turns(path=Path(__file__).parents[1] / "meat-mind-brainstorm-gold.md"):
    data = path.read_bytes()
    if sha256(data).hexdigest() != GOLD_SHA256:
        raise ValueError("Brainstorm gold differs from the live benchmark pin")
    sections = re.split(r"^## [1-6] · .+\n", data.decode(), flags=re.MULTILINE)[1:]
    turns = []
    for section in sections:
        lines = section.lstrip("\n").splitlines()
        prompt = []
        for line in lines:
            if not line.startswith("> "):
                break
            prompt.append(line[2:])
        if not prompt:
            raise ValueError("Benchmark gold turn is missing its input")
        turns.append("\n".join(prompt))
    if len(turns) != 6:
        raise ValueError("Expected exactly six pinned user turns")
    return turns


def read_grounding(path, digest):
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Live grounding export checksum differs")
    evidence = json.loads(data)
    pages = {
        row["work_object_id"]: (row["work_revision_id"], row["content_sha256"])
        for row in evidence["content.work_revision"]
    }
    if pages != PAGE_PINS:
        raise ValueError("Live grounding page revisions differ")
    if {row["work_object_id"] for row in evidence["content.work_object"]} != set(PAGE_PINS):
        raise ValueError("Live grounding page inventory differs")
    if any(row["world_id"] != "elderwyld" or row["kind"] != "worldbuilding_source"
           or row["current_revision_id"] != PAGE_PINS[row["work_object_id"]][0]
           for row in evidence["content.work_object"]):
        raise ValueError("Live grounding page ownership differs")
    revision = evidence["statblock_revision"]
    if tuple(revision[key] for key in ("statblock_id", "revision_id", "definition_digest")) != ORIGINAL_MEAT_MIND:
        raise ValueError("Original Meat Mind revision differs")
    return evidence


def restore_grounding(path, digest, dsn, identity):
    """Replay saved page rows before starting the live browser."""
    from psycopg import connect, sql
    from psycopg.types.json import Jsonb

    from .isolation import _database_identity

    evidence = read_grounding(path, digest)
    _database_identity(dsn, identity, writable=True)
    ids = set(PAGE_PINS)
    if {row["work_object_id"] for row in evidence["content.page_metadata"]} != ids:
        raise ValueError("Live grounding page metadata inventory differs")
    with connect(dsn) as connection:
        for table in ("content.work_object", "content.work_revision", "content.page_metadata"):
            name = sql.Identifier(*table.split("."))
            statement = sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{}, %s)").format(name, name)
            for original in evidence[table]:
                row = dict(original)
                if table == "content.work_object":
                    row["current_revision_id"] = None
                connection.execute(statement, (Jsonb(row),))
        for row in evidence["content.work_object"]:
            connection.execute(
                "UPDATE content.work_object SET current_revision_id = %s WHERE work_object_id = %s",
                (row["current_revision_id"], row["work_object_id"]),
            )


def main():
    from .isolation import APP_DSN

    parser = argparse.ArgumentParser(description="Restore the scoped live benchmark page revisions")
    parser.add_argument("--grounding", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--isolation", required=True, type=Path)
    args = parser.parse_args()
    isolation = json.loads(args.isolation.read_text())
    restore_grounding(args.grounding, args.sha256, os.environ[APP_DSN], isolation["app"])


if __name__ == "__main__":
    main()
