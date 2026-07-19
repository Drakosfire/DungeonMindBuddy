#!/usr/bin/env python3
"""Governed catch-up: drop overlapping Session 24 PC node assertions.

Session 24 confirm published ``contribution:a01be11c6967afd9`` with full node
assertions for already-resolved PCs (Baergrom / Caelynn / Karsemine / Stafl).
Projection refused competing fingerprints. This script supersedes that
contribution with the same edges + new nodes, omitting those four PC node
asserts — no hand-edit of revision JSON.

Idempotent: if the old contribution is already ``superseded`` and head is past
``rev:dc988ccc…``, prints current state and exits 0.

Live world root requires ``--allow-live-world``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT / "src", REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import graph_memory.kernel as kernel
from graph_memory.world_supergraph.contribution_store import load_contribution_record

DEFAULT_ROOT = REPO_ROOT / "out"
DEFAULT_WORLD_ID = "eldyrwild"
DEFAULT_OLD_CONTRIBUTION_ID = "contribution:a01be11c6967afd9"
DEFAULT_PARENT_REVISION_ID = "rev:dc988ccc2f37163da7d4de29ba276db2"
DROP_SUBJECTS = frozenset(
    {
        "pc:baergrom",
        "pc:caelynn",
        "pc:karsemine",
        "pc:stafl",
    }
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--world-id", default=DEFAULT_WORLD_ID)
    parser.add_argument(
        "--old-contribution-id",
        default=DEFAULT_OLD_CONTRIBUTION_ID,
    )
    parser.add_argument(
        "--allow-live-world",
        action="store_true",
        help="Required when --root resolves under the live out/ world tree.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    live_marker = (DEFAULT_ROOT / "graph_memory" / "worlds" / args.world_id).resolve()
    if live_marker.exists() and root == DEFAULT_ROOT.resolve() and not args.allow_live_world:
        print(
            "Refusing live world mutation without --allow-live-world.",
            file=sys.stderr,
        )
        return 2

    old = load_contribution_record(root, args.world_id, args.old_contribution_id)
    head = kernel.open_world_graph_head(root, args.world_id)
    if old.status == "superseded" and head.head_revision_id != DEFAULT_PARENT_REVISION_ID:
        print(
            json.dumps(
                {
                    "already_done": True,
                    "old_contribution_id": args.old_contribution_id,
                    "old_status": old.status,
                    "head_revision_id": head.head_revision_id,
                },
                indent=2,
            )
        )
        return 0

    kept = []
    dropped = []
    for assertion in old.accepted_assertions:
        subject = assertion.subject_node_id or ""
        if assertion.assertion_kind == "node" and subject in DROP_SUBJECTS:
            dropped.append(f"{assertion.assertion_id} {subject}")
        else:
            kept.append(assertion)

    summary = {
        "old_contribution_id": args.old_contribution_id,
        "head_before": head.head_revision_id,
        "dropped": dropped,
        "kept_count": len(kept),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0

    new = kernel.create_graph_contribution(
        world_id=args.world_id,
        source_kind=old.source_kind,
        source_artifact_id=old.source_artifact_id,
        source_revision_id=old.source_revision_id,
        extraction_profile=old.extraction_profile,
        campaign_scope=old.campaign_scope,
        authored_by="operator:pc_identity_catchup",
        accepted_assertions=kept,
        rejected_assertions=list(old.rejected_assertions),
        unresolved_mentions=list(old.unresolved_mentions),
        diagnostics=[
            *list(old.diagnostics),
            "catchup:drop_overlapping_pc_node_assertions",
            f"supersedes:{args.old_contribution_id}",
        ],
    )
    result = kernel.supersede_graph_contribution(
        root,
        world_id=args.world_id,
        new_contribution=new,
        superseded_contribution_id=args.old_contribution_id,
        expected_parent_revision_id=head.head_revision_id,
    )
    summary.update(
        {
            "published": result.published,
            "new_contribution_id": new.contribution_id,
            "new_revision_id": result.revision_id,
            "parent_revision_id": result.parent_revision_id,
            "diagnostics": list(result.diagnostics or [])[:12],
        }
    )
    print(json.dumps(summary, indent=2))
    return 0 if result.published else 1


if __name__ == "__main__":
    raise SystemExit(main())
