#!/usr/bin/env python3
"""Materialize committed session-memory JSONL + meta JSON from corpus breadcrumb files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from corpus.session_recap_paths import PILOT_BLESSED_SESSIONS  # noqa: E402
from live_play.session_memory_materializer import _check_one, _materialize_one  # noqa: E402
from src.session_memory.breadcrumb_normalize import BreadcrumbNormalizeError  # noqa: E402

_DEFAULT_CORPUS = _REPO_ROOT / "corpus" / "eldyrwild-markdown"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus-root", type=Path, default=_DEFAULT_CORPUS)
    p.add_argument("--campaign", type=int, choices=(1, 2))
    p.add_argument("--session", type=int)
    p.add_argument("--all-blessed", action="store_true")
    p.add_argument("--check", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="Archive existing session-memory outputs before replacing them.")
    args = p.parse_args(argv)

    if args.all_blessed:
        targets = list(PILOT_BLESSED_SESSIONS)
    elif args.campaign is not None and args.session is not None:
        targets = [(args.campaign, args.session)]
    else:
        p.error("specify --campaign and --session, or --all-blessed")

    ok = True
    for campaign_number, session in targets:
        try:
            # The CLI is also a public materialization entry point, so enforce
            # the same upstream lineage gate used by the API pipeline.
            from live_play.recap_ingest_pipeline import inspect_recap_ingest_status

            lineage = inspect_recap_ingest_status(
                campaign_id=f"longmont-c{campaign_number}",
                session=session,
                title=None,
                slug=None,
                corpus=args.corpus_root,
            )
            if "breadcrumb_current" not in lineage.get("states", []):
                print(
                    f"FAIL C{campaign_number}S{session}: breadcrumb lineage is not verified; "
                    "review and refresh upstream recap artifacts before materializing session memory",
                    file=sys.stderr,
                )
                ok = False
                continue
            if args.check:
                ok = _check_one(corpus_root=args.corpus_root, campaign_number=campaign_number, session=session) and ok
            else:
                summary = _materialize_one(
                    corpus_root=args.corpus_root,
                    campaign_number=campaign_number,
                    session=session,
                    dry_run=args.dry_run,
                    force=args.force,
                )
                if summary["outcome"] == "stale":
                    print(
                        f"STALE C{campaign_number}S{session}: existing session-memory output differs; "
                        "use --force to archive and replace it",
                        file=sys.stderr,
                    )
                    ok = False
                    continue
                action = "WOULD " if args.dry_run else ""
                print(
                    f"{action}{summary['outcome'].upper()} "
                    f"C{campaign_number}S{session}: {summary['jsonl_rel']} "
                    f"({summary['record_count']} records, routes={summary['records_with_routes']})"
                )
                for item in summary.get("archived_artifacts", []):
                    print(f"archived: {item['from']} -> {item['to']}")
        except (FileNotFoundError, OSError, ValueError, BreadcrumbNormalizeError) as exc:
            print(f"FAIL C{campaign_number}S{session}: {exc}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
