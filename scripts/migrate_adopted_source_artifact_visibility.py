#!/usr/bin/env -S uv run python
"""Backfill GM visibility on adopted DungeonMind source artifacts (CUTOVER R.3).

The Eldyrwild adoption bundle v2 producer wrote ``SourceArtifactV2`` rows with
``visibility=None`` (Buddy's kernel serves GM-only reads and never needed an
access-granting classification). DungeonMind's native read path is fail-closed:
v2 artifacts with unset visibility are excluded from scope, which silently
empties every projection of an adopted world.

This migration sets ``visibility=gm`` on exactly the affected rows (payload
visibility is JSON null) and recomputes the tamper-evident
``record_fingerprint`` with DungeonMind's own serializer. It is idempotent and
dry-run by default; pass ``--apply`` to write.

⚠️  V3 CONTRACT VIOLATION: This migration directly mutates ``source_artifacts``
and rewrites the V3 receipt's ``membership_sha256``. The V3 contract defines
that digest as the checkpoint over the exact sealed bundle's durable history.
This migration was applied to the live database before the contract violation
was identified. A fix-forward plan is required to repair the adoption history
through DungeonMind authority.

Usage:
    uv run python scripts/migrate_adopted_source_artifact_visibility.py \
        --database-url postgresql://... --world-id eldyrwild --apply
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

    # R.3 Review Cycle 2: the --apply path directly mutates sealed
    # source_artifacts and rewrites the V3 receipt's membership_sha256,
    # violating the V3 contract's tamper-evident history. The mutation path
    # is hard-disabled pending the DungeonMind fix-forward prerequisite.
    if args.apply:
        print(
            "error: --apply is hard-disabled. The V3 contract violation requires "
            "a governed repair mechanism designed by the DungeonMind fix-forward "
            "prerequisite. See Docs/Benchmarks/BASELINE-r3-direct-dungeonmind-current-reads.md §3.4.",
            file=sys.stderr,
        )
        return 2

    if not args.database_url:
        print("error: --database-url or DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL required", file=sys.stderr)
        return 2

    import psycopg
    from dungeonmind.contracts.evidence import SourceArtifactV2
    from dungeonmind.contracts.vocabulary import Visibility
    from dungeonmind.infrastructure.postgres.serialization import dump_payload, model_fingerprint

    with psycopg.connect(args.database_url, autocommit=False) as conn:
        rows = conn.execute(
            "SELECT source_artifact_id, payload FROM source_artifacts "
            "WHERE world_id = %s ORDER BY source_artifact_id",
            (args.world_id,),
        ).fetchall()
        candidates: list[tuple[str, dict]] = []
        skipped: list[str] = []
        for artifact_id, payload in rows:
            if payload.get("visibility") is None:
                candidates.append((artifact_id, payload))
            else:
                skipped.append(artifact_id)

        print(f"world={args.world_id}: {len(rows)} artifacts, {len(candidates)} with null visibility, {len(skipped)} already classified")
        if not args.apply:
            for artifact_id, _ in candidates:
                print(f"  would set visibility=gm: {artifact_id}")
            print("dry-run; pass --apply to write")
            return 0

        updated = 0
        for artifact_id, payload in candidates:
            artifact = SourceArtifactV2.model_validate(payload)
            fixed = artifact.model_copy(update={"visibility": Visibility.GM})
            new_payload = dump_payload(fixed)
            new_fingerprint = model_fingerprint(fixed)
            conn.execute(
                "UPDATE source_artifacts "
                "SET payload = %s, visibility = 'gm', record_fingerprint = %s "
                "WHERE source_artifact_id = %s AND world_id = %s",
                (json.dumps(new_payload), new_fingerprint, artifact_id, args.world_id),
            )
            updated += 1
        conn.commit()
        print(f"phase 1: updated {updated} artifact rows")

    if not args.frozen_root:
        print("error: --frozen-root is required with --apply to recompute the receipt membership digest", file=sys.stderr)
        return 2
    return _update_receipt_membership(args)


def _update_receipt_membership(args: argparse.Namespace) -> int:
    """Recompute the V3 receipt membership digest over the corrected rows.

    The visibility backfill changes adopted artifact payloads, so the receipt's
    ``membership_sha256`` (which covers identity AND payload of every adopted
    row) must be re-emitted or the legacy hydration path fails closed on
    ``adopted_membership_mismatch``. Member selection reuses the authority
    adapter's own helpers so the digest matches the verifier exactly.
    """
    from dungeonmind.domain.existing_world_membership import (
        existing_world_adoption_membership_sha256,
    )
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle
    from dungeonmind.infrastructure.postgres.serialization import dump_payload, model_fingerprint

    from apps.live_control_server.integrations.dungeonmind_kernel.world_graph_authority import (
        _adopted_source_identity,
    )
    from graph_memory.world_supergraph.contribution_store import load_contribution_index
    from graph_memory.world_supergraph.identity_decision_store import load_identity_decision_index

    frozen_root = Path(args.frozen_root).resolve()
    world_id = args.world_id
    bundle = PostgresRepositoryBundle(PostgresDatabase(args.database_url))

    adopted_contribution_ids = set(load_contribution_index(frozen_root, world_id).all_contribution_ids)
    adopted_decision_ids = set(load_identity_decision_index(frozen_root, world_id).all_decision_ids)
    all_contributions = bundle.contributions.list_for_world(world_id)
    all_decisions = bundle.identity_decisions.list_for_world(world_id)
    all_artifacts = bundle.sources.list_artifacts_for_world(world_id)
    contributions = [c for c in all_contributions if c.contribution_id in adopted_contribution_ids]
    decisions = [d for d in all_decisions if d.decision_id in adopted_decision_ids]
    adopted_artifact_ids, adopted_revision_ids = _adopted_source_identity(contributions)
    artifacts = [a for a in all_artifacts if a.source_artifact_id in adopted_artifact_ids]
    revisions = []
    for artifact_id in sorted(adopted_artifact_ids):
        revisions.extend(
            revision
            for revision in bundle.sources.list_revisions(artifact_id)
            if revision.source_revision_id in adopted_revision_ids
        )

    digest = existing_world_adoption_membership_sha256(
        source_artifacts=artifacts,
        source_revisions=revisions,
        contributions=contributions,
        identity_decisions=decisions,
    )
    receipt = bundle.existing_world_adoptions.get_for_world(world_id)
    if receipt is None:
        print(f"error: no adoption receipt for world {world_id!r}", file=sys.stderr)
        return 1
    print(f"phase 2: recomputed membership digest {digest[:16]}… (receipt has {receipt.membership_sha256[:16]}…)")
    if digest == receipt.membership_sha256:
        print("receipt already matches; nothing to do")
        return 0

    updated_receipt = receipt.model_copy(update={"membership_sha256": digest})
    new_payload = dump_payload(updated_receipt)
    new_fingerprint = model_fingerprint(updated_receipt)

    import psycopg

    with psycopg.connect(args.database_url, autocommit=False) as conn:
        conn.execute(
            "UPDATE existing_world_adoptions SET payload = %s, record_fingerprint = %s "
            "WHERE world_id = %s AND adoption_id = %s",
            (json.dumps(new_payload), new_fingerprint, world_id, receipt.adoption_id),
        )
        conn.commit()

    # Verify through DungeonMind's own repository (validates fingerprints).
    reread = bundle.existing_world_adoptions.get_for_world(world_id)
    if reread is None or reread.membership_sha256 != digest:
        print("error: receipt re-read did not return the updated digest", file=sys.stderr)
        return 1
    print("phase 2: receipt membership digest updated and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
