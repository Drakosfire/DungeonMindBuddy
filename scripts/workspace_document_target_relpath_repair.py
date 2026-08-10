#!/usr/bin/env python3
"""Read-only duplicate target_relpath preflight + bounded release-target repair.

Default is report-only (exit 1 when duplicates exist). Apply requires explicit flags.

Examples::

  uv run python scripts/workspace_document_target_relpath_repair.py
  uv run python scripts/workspace_document_target_relpath_repair.py \\
    --apply-release-target \\
    --survivor-id 381d62b4-7a53-4452-8eb2-b90dbea8ae54 \\
    --retire-id bcaa65da-e9c9-4ae9-afba-2d8190ec09d5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    find_duplicate_target_relpath_ownership,
    get_workspace_document,
    reinstate_workspace_document_record,
    release_target_relpath_from_discarded_duplicate,
)


def _print_groups(groups: list[tuple[str, list[WorkspaceDocumentRecord]]]) -> None:
    if not groups:
        print("OK: no duplicate non-null target_relpath ownership")
        return
    print(f"STOP: {len(groups)} duplicate target_relpath group(s)")
    for path, owners in groups:
        print(f"  {path}")
        for record in owners:
            print(
                f"    {record.document_id} status={record.status} "
                f"kind={record.kind} session={record.target_session} "
                f"title={record.title!r} created_at={record.created_at}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing out/registries/workspace_documents.json",
    )
    parser.add_argument(
        "--apply-release-target",
        action="store_true",
        help="Apply bounded repair: retiree must be discarded; clears its target_relpath",
    )
    parser.add_argument("--survivor-id", type=str, default=None)
    parser.add_argument("--retire-id", type=str, default=None)
    parser.add_argument(
        "--reinstate-retiree-discarded-without-path",
        action="store_true",
        help=(
            "If retire-id is missing from the registry, reinstate it as discarded "
            "with target_relpath=null before release (uses --retire-title/--retire-session)"
        ),
    )
    parser.add_argument("--retire-title", type=str, default="C2 Session 23 Prep")
    parser.add_argument("--retire-session", type=int, default=23)
    parser.add_argument("--retire-campaign-id", type=str, default="longmont-c2")
    parser.add_argument(
        "--retire-created-at",
        type=str,
        default="2026-08-08T18:00:00.000000Z",
        help="Preserved created_at when reinstating a deleted identity",
    )
    args = parser.parse_args()

    groups = find_duplicate_target_relpath_ownership(args.root)
    _print_groups(groups)

    if not args.apply_release_target:
        return 1 if groups else 0

    if not args.survivor_id or not args.retire_id:
        print("ERROR: --apply-release-target requires --survivor-id and --retire-id")
        return 2

    try:
        get_workspace_document(args.root, args.survivor_id)
    except WorkspaceDocumentRegistryError as exc:
        print(f"ERROR: survivor not found: {exc}")
        return 2

    try:
        get_workspace_document(args.root, args.retire_id)
    except WorkspaceDocumentRegistryError:
        if not args.reinstate_retiree_discarded_without_path:
            print(
                f"ERROR: retiree {args.retire_id} not found; pass "
                "--reinstate-retiree-discarded-without-path to restore identity"
            )
            return 2
        now = args.retire_created_at
        reinstate_workspace_document_record(
            args.root,
            WorkspaceDocumentRecord(
                document_id=args.retire_id,
                title=args.retire_title,
                campaign_id=args.retire_campaign_id,
                target_session=args.retire_session,
                kind="plan",
                target_relpath=None,
                status="discarded",
                content_status="draft",
                revision=2,
                created_at=now,
                updated_at=now,
            ),
        )
        print(f"reinstated discarded identity {args.retire_id} with target_relpath=null")

    retire = get_workspace_document(args.root, args.retire_id)
    if retire.target_relpath is None or retire.target_relpath == "":
        print(
            f"OK: retiree {args.retire_id} already has released target_relpath; "
            "no release step needed"
        )
    else:
        released = release_target_relpath_from_discarded_duplicate(
            args.root,
            survivor_document_id=args.survivor_id,
            retire_document_id=args.retire_id,
        )
        print(
            f"released target_relpath from {released.document_id}; "
            f"revision={released.revision}"
        )

    groups_after = find_duplicate_target_relpath_ownership(args.root)
    _print_groups(groups_after)
    return 1 if groups_after else 0


if __name__ == "__main__":
    raise SystemExit(main())
