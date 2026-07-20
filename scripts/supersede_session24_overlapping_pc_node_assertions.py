#!/usr/bin/env python3
"""Governed catch-up: drop overlapping Session 24 PC node assertions.

Session 24 confirm published ``contribution:a01be11c6967afd9`` with full node
assertions for already-resolved PCs (Baergrom / Caelynn / Karsemine / Stafl).
Projection refused competing fingerprints. This script supersedes that
contribution with the same edges + new nodes, omitting those four PC node
asserts — no hand-edit of revision JSON.

Idempotent: if the old contribution is already ``superseded`` by a successor
that carries this script's own repair marker, prints current state and exits
0 without re-running the supersession.

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
from graph_memory.world_supergraph.contribution_store import (
    list_contribution_records,
    load_contribution_record,
)

DEFAULT_ROOT = REPO_ROOT / "out"
DEFAULT_WORLD_ID = "eldyrwild"
DEFAULT_OLD_CONTRIBUTION_ID = "contribution:a01be11c6967afd9"
REPAIR_DIAGNOSTIC_MARKER = "catchup:drop_overlapping_pc_node_assertions"
DROP_SUBJECTS = frozenset(
    {
        "pc:baergrom",
        "pc:caelynn",
        "pc:karsemine",
        "pc:stafl",
    }
)


def _is_live_world_root(root: Path, world_id: str) -> bool:
    """True when ``root`` is (or is configured as) the live product world store.

    Checked unconditionally against the *resolved* ``--root`` argument — not
    just the repo default — so pointing ``--root`` at another live world tree
    (e.g. via a symlink or an explicit absolute path) still trips the guard.
    """
    if (root / "graph_memory" / "worlds" / world_id).exists():
        return True
    if root == DEFAULT_ROOT.resolve():
        return True
    try:
        from apps.live_control_server.config import live_world_graph_root

        if root == live_world_graph_root():
            return True
    except Exception:
        pass
    return False


def _repair_successor_contribution_id(
    root: Path, world_id: str, old_contribution_id: str
) -> str | None:
    """Find the contribution that this script's own repair created, if any.

    A contribution merely being ``superseded`` is not proof this specific
    repair ran — any later supersession would set that status. Require the
    successor to both name ``old_contribution_id`` as
    ``supersedes_contribution_id`` and carry this script's diagnostic marker.
    """
    for record in list_contribution_records(root, world_id):
        if record.supersedes_contribution_id != old_contribution_id:
            continue
        if REPAIR_DIAGNOSTIC_MARKER in list(record.diagnostics):
            return record.contribution_id
    return None


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
    if _is_live_world_root(root, args.world_id) and not args.allow_live_world:
        print(
            "Refusing live world mutation without --allow-live-world.",
            file=sys.stderr,
        )
        return 2

    old = load_contribution_record(root, args.world_id, args.old_contribution_id)
    head = kernel.open_world_graph_head(root, args.world_id)
    successor_contribution_id = _repair_successor_contribution_id(
        root, args.world_id, args.old_contribution_id
    )
    if old.status == "superseded" and successor_contribution_id is not None:
        print(
            json.dumps(
                {
                    "already_done": True,
                    "old_contribution_id": args.old_contribution_id,
                    "old_status": old.status,
                    "successor_contribution_id": successor_contribution_id,
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
        supersedes_contribution_id=args.old_contribution_id,
        diagnostics=[
            *list(old.diagnostics),
            REPAIR_DIAGNOSTIC_MARKER,
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
