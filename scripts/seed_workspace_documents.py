#!/usr/bin/env python3
"""One-time seed for the opaque workspace document registry.

Scans Longmont Session Prep Markdown files that match the writer allowlist
(``Session N Prep.md``) and the two Tiptap spike runbook targets, then creates
registry records with server-issued UUIDs. Existing browser-local drafts are
intentionally not migrated.

Example::

  uv run python scripts/seed_workspace_documents.py
  uv run python scripts/seed_workspace_documents.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    list_workspace_documents,
    workspace_documents_path,
)

_PLAN_PREP_RE = re.compile(r"^Session (\d+) Prep\.md$")
_CAMPAIGN_DIR_RE = re.compile(r"^Campaign (\d+)$")

SPIKE_RUNBOOKS: tuple[tuple[str, str, int, str], ...] = (
    (
        "North Gate Session Runbook",
        "longmont-c2",
        23,
        "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md",
    ),
    (
        "North Gate Callout Spike",
        "longmont-c2",
        23,
        "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md",
    ),
)


def _campaign_id_from_dir(name: str) -> str | None:
    match = _CAMPAIGN_DIR_RE.fullmatch(name)
    if not match:
        return None
    return f"longmont-c{match.group(1)}"


def _scan_plan_prep_targets(root: Path) -> list[tuple[str, str, int, str]]:
    """Return (title, campaign_id, target_session, target_relpath) for allowlisted prep files."""
    found: list[tuple[str, str, int, str]] = []
    ambiguous: list[str] = []
    campaigns_root = root / "corpus/eldyrwild-markdown/Longmont Campaign"
    if not campaigns_root.is_dir():
        return found

    for campaign_dir in sorted(campaigns_root.iterdir()):
        if not campaign_dir.is_dir():
            continue
        campaign_id = _campaign_id_from_dir(campaign_dir.name)
        if campaign_id is None:
            continue
        prep_dir = campaign_dir / "Session Prep"
        if not prep_dir.is_dir():
            continue
        for path in sorted(prep_dir.glob("*.md")):
            match = _PLAN_PREP_RE.fullmatch(path.name)
            if not match:
                ambiguous.append(path.relative_to(root).as_posix())
                continue
            session = int(match.group(1))
            relpath = path.relative_to(root).as_posix()
            campaign_label = f"C{campaign_id.rsplit('c', 1)[-1]}"
            title = f"{campaign_label} Session {session} Prep"
            found.append((title, campaign_id, session, relpath))
    return found


def _already_seeded_paths(root: Path) -> set[str]:
    records = list_workspace_documents(root, status=None)
    return {r.target_relpath for r in records if r.target_relpath}


def seed(*, root: Path, dry_run: bool) -> int:
    plan_targets = _scan_plan_prep_targets(root)
    spike_targets = list(SPIKE_RUNBOOKS)
    seeded_paths = _already_seeded_paths(root)
    created = 0
    skipped = 0

    print(f"Registry path: {workspace_documents_path(root)}")
    print(f"Plan prep allowlist matches: {len(plan_targets)}")
    print(f"Spike runbooks: {len(spike_targets)}")

    # Report ambiguous Session Prep files (present but not allowlisted).
    campaigns_root = root / "corpus/eldyrwild-markdown/Longmont Campaign"
    ambiguous: list[str] = []
    if campaigns_root.is_dir():
        for campaign_dir in sorted(campaigns_root.iterdir()):
            prep_dir = campaign_dir / "Session Prep"
            if not prep_dir.is_dir():
                continue
            for path in sorted(prep_dir.glob("*.md")):
                if not _PLAN_PREP_RE.fullmatch(path.name):
                    ambiguous.append(path.relative_to(root).as_posix())
    if ambiguous:
        print("\nAmbiguous Session Prep files (not seeded; resolve manually):")
        for rel in ambiguous:
            print(f"  - {rel}")

    for title, campaign_id, target_session, target_relpath in [*plan_targets, *spike_targets]:
        kind = "runbook" if target_relpath.startswith("evals/") else "plan"
        if target_relpath in seeded_paths:
            print(f"SKIP already seeded: {target_relpath}")
            skipped += 1
            continue
        if dry_run:
            print(
                f"DRY-RUN would create {kind}: {title!r} → {target_relpath} "
                f"(campaign={campaign_id}, session={target_session})"
            )
            created += 1
            continue
        record = create_workspace_document(
            root,
            title=title,
            campaign_id=campaign_id,
            kind=kind,  # type: ignore[arg-type]
            target_session=target_session,
            target_relpath=target_relpath,
        )
        print(
            f"CREATED {record.document_id} kind={kind} title={title!r} "
            f"path={target_relpath}"
        )
        created += 1
        seeded_paths.add(target_relpath)

    print(f"\nDone. created_or_would_create={created} skipped={skipped}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root (default: inferred from script location)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing the registry",
    )
    args = parser.parse_args(argv)
    return seed(root=args.root.resolve(), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
