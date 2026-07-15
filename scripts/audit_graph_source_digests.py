#!/usr/bin/env python3
"""Audit revision-bound contribution source-payload digests for Eldyrwild.

Usage:
  python scripts/audit_graph_source_digests.py
  python scripts/audit_graph_source_digests.py --root out --repair

`--repair` runs rebuild_from_contributions(publish=True) then re-audits.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = REPO_ROOT / "src"
for _path in (str(REPO_ROOT), str(_SRC)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from graph_memory.interaction.digest_audit import (  # noqa: E402
    TRIPOD_CONTRIBUTION_ID,
    audit_contribution_source_digests,
)
from graph_memory.kernel import rebuild_from_contributions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT / "out",
        help="World graph root (default: ./out)",
    )
    parser.add_argument("--world-id", default="eldyrwild")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Rebuild from contributions when digests are incomplete.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full audit payload as JSON.",
    )
    args = parser.parse_args()
    root = args.root.expanduser().resolve()

    report = audit_contribution_source_digests(
        root,
        world_id=args.world_id,
        highlight_contribution_ids=[TRIPOD_CONTRIBUTION_ID],
    )
    needs_init_restore = False
    if args.repair:
        from graph_memory.world_supergraph.storage import load_current_world_graph

        _head, _revision, store = load_current_world_graph(root, args.world_id)
        needs_init_restore = (
            store.initialization_plan_digest is None
            or store.initialization_attestation_digest is None
            or not list(store.initialization_contribution_ids or [])
        )
    if args.repair and (not report["complete"] or needs_init_restore):
        reason = []
        if not report["complete"]:
            reason.append(
                f"digests incomplete (missing={len(report['missing_contribution_ids'])}, "
                f"mismatch={len(report['mismatched_contribution_ids'])})"
            )
        if needs_init_restore:
            reason.append("initialization digests missing on head")
        print("Rebuilding because " + "; ".join(reason) + "…", file=sys.stderr)
        rebuilt = rebuild_from_contributions(root, world_id=args.world_id, publish=True)
        print(
            f"Rebuild published revision={getattr(rebuilt, 'revision_id', rebuilt)}",
            file=sys.stderr,
        )
        report = audit_contribution_source_digests(
            root,
            world_id=args.world_id,
            highlight_contribution_ids=[TRIPOD_CONTRIBUTION_ID],
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        tripod = (report.get("highlighted") or {}).get(TRIPOD_CONTRIBUTION_ID)
        print(f"world_id={report['world_id']} revision_id={report['revision_id']}")
        print(
            f"complete={report['complete']} ok={report['ok_count']}/"
            f"{report['contribution_count']}"
        )
        print(f"missing={len(report['missing_contribution_ids'])}")
        print(f"mismatched={len(report['mismatched_contribution_ids'])}")
        print(f"tripod={json.dumps(tripod, sort_keys=True)}")
        if report.get("migration_guidance"):
            print(f"guidance={report['migration_guidance']}")

    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
