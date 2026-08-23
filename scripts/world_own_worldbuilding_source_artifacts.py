#!/usr/bin/env -S uv run python
"""World-own session-less worldbuilding corpus artifacts (CUTOVER R.3).

The Eldyrwild adoption assigned ``campaign_id=longmont-c2`` to world-universal
worldbuilding corpus documents (``corpus:eldyrwild:*`` with no session) because
the whole-world reanchor ran under the c2 identity. Buddy's legacy kernel
scoped *objects*, never evidence chains, so those docs still supported
world-universal objects (e.g. ``location:mirathorn``) under any campaign lens.
DungeonMind's native read path is fail-closed per evidence chain: an object
whose evidence artifact belongs to another campaign is excluded from that
campaign's read.

This migration reassigns exactly the session-less ``corpus:`` worldbuilding
documents to world ownership (``campaign_id=NULL``), which is their correct
semantic classification, and recomputes the tamper-evident
``record_fingerprint`` plus the adoption receipt's ``membership_sha256`` (the
digest covers adopted artifact payloads). Session recaps and campaign-native
artifacts are deliberately untouched: they are genuine campaign chronology.

Idempotent; dry-run by default — pass ``--apply`` to write.

⚠️  V3 CONTRACT VIOLATION: This migration directly mutates ``source_artifacts``
and rewrites the V3 receipt's ``membership_sha256``. The V3 contract defines
that digest as the checkpoint over the exact sealed bundle's durable history.
This migration was applied to the live database before the contract violation
was identified. A fix-forward plan is required to repair the adoption history
through DungeonMind authority.

Usage:
    uv run python scripts/world_own_worldbuilding_source_artifacts.py \
        --database-url postgresql://... --world-id eldyrwild \
        --frozen-root /path/to/repo/out --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", ""),
        help="DungeonMind authority PostgreSQL DSN (or DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL).",
    )
    parser.add_argument("--world-id", default="eldyrwild")
    parser.add_argument(
        "--frozen-root",
        default="",
        help="Frozen Buddy store root (repo 'out' dir) — required for the receipt membership recompute.",
    )
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run).")
    args = parser.parse_args(argv)
    if not args.database_url:
        print("error: --database-url or DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL required", file=sys.stderr)
        return 2

    import psycopg
    from dungeonmind.contracts.evidence import SourceArtifactV2
    from dungeonmind.infrastructure.postgres.serialization import dump_payload, model_fingerprint

    with psycopg.connect(args.database_url, autocommit=False) as conn:
        rows = conn.execute(
            "SELECT source_artifact_id, payload FROM source_artifacts "
            "WHERE world_id = %s AND source_artifact_id LIKE 'corpus:%%' "
            "AND session_id IS NULL AND campaign_id IS NOT NULL "
            "ORDER BY source_artifact_id",
            (args.world_id,),
        ).fetchall()

        print(f"world={args.world_id}: {len(rows)} session-less corpus artifacts still campaign-owned")
        for artifact_id, payload in rows:
            print(
                f"  candidate: {artifact_id} "
                f"(campaign={payload.get('campaign_id')} domain={payload.get('source_domain_key')})"
            )
        if not args.apply:
            print("dry-run; pass --apply to write")
            return 0

        updated = 0
        for artifact_id, payload in rows:
            artifact = SourceArtifactV2.model_validate(payload)
            fixed = artifact.model_copy(update={"campaign_id": None})
            new_payload = dump_payload(fixed)
            new_fingerprint = model_fingerprint(fixed)
            conn.execute(
                "UPDATE source_artifacts "
                "SET payload = %s, campaign_id = NULL, record_fingerprint = %s "
                "WHERE source_artifact_id = %s AND world_id = %s",
                (json.dumps(new_payload), new_fingerprint, artifact_id, args.world_id),
            )
            updated += 1
        conn.commit()
        print(f"phase 1: world-owned {updated} artifact rows")

    if not args.frozen_root:
        print("error: --frozen-root is required with --apply to recompute the receipt membership digest", file=sys.stderr)
        return 2
    from scripts.migrate_adopted_source_artifact_visibility import _update_receipt_membership

    return _update_receipt_membership(args)


if __name__ == "__main__":
    raise SystemExit(main())
