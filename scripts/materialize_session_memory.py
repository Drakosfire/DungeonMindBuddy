#!/usr/bin/env python3
"""Materialize committed session-memory JSONL + meta JSON from corpus breadcrumb files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.session_memory.breadcrumb_normalize import (  # noqa: E402
    BreadcrumbNormalizeError,
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)
from src.corpus.session_recap_paths import (  # noqa: E402
    PILOT_BLESSED_SESSIONS,
    breadcrumbed_relpath,
    resolve_under_corpus,
    session_memory_jsonl_relpath,
    session_memory_meta_relpath,
)

_DEFAULT_CORPUS = _REPO_ROOT / "corpus" / "eldyrwild-markdown"


def _materialize_one(
    *,
    corpus_root: Path,
    campaign_number: int,
    session: int,
    dry_run: bool,
) -> dict[str, object]:
    breadcrumb_rel = breadcrumbed_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    breadcrumb_path = resolve_under_corpus(corpus_root, breadcrumb_rel)
    if not breadcrumb_path.is_file():
        raise FileNotFoundError(f"missing breadcrumb artifact: {breadcrumb_rel}")

    text = breadcrumb_path.read_text(encoding="utf-8")
    records, meta = normalize_breadcrumb_artifact(artifact_text=text, corpus_root=corpus_root)

    jsonl_rel = session_memory_jsonl_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    meta_rel = session_memory_meta_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    jsonl_path = resolve_under_corpus(corpus_root, jsonl_rel)
    meta_path = resolve_under_corpus(corpus_root, meta_rel)

    if not dry_run:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        write_records_jsonl(records, jsonl_path)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return {
        "campaign_number": campaign_number,
        "session": session,
        "breadcrumb_rel": breadcrumb_rel,
        "jsonl_rel": jsonl_rel,
        "meta_rel": meta_rel,
        "record_count": len(records),
        "records_with_routes": meta.get("records_with_routes"),
    }


def _check_one(*, corpus_root: Path, campaign_number: int, session: int) -> bool:
    jsonl_rel = session_memory_jsonl_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    meta_rel = session_memory_meta_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    jsonl_path = resolve_under_corpus(corpus_root, jsonl_rel)
    meta_path = resolve_under_corpus(corpus_root, meta_rel)
    if not jsonl_path.is_file() or not meta_path.is_file():
        print(f"MISSING {jsonl_rel} or {meta_rel}", file=sys.stderr)
        return False

    breadcrumb_rel = breadcrumbed_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    breadcrumb_path = resolve_under_corpus(corpus_root, breadcrumb_rel)
    text = breadcrumb_path.read_text(encoding="utf-8")
    records, meta = normalize_breadcrumb_artifact(artifact_text=text, corpus_root=corpus_root)
    expected_jsonl = "\n".join(
        json.dumps(r.to_json_dict(), ensure_ascii=False) for r in records
    ) + ("\n" if records else "")
    if jsonl_path.read_text(encoding="utf-8") != expected_jsonl:
        print(f"DRIFT jsonl {jsonl_rel}", file=sys.stderr)
        return False
    on_disk_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if on_disk_meta != meta:
        print(f"DRIFT meta {meta_rel}", file=sys.stderr)
        return False
    print(f"OK {jsonl_rel} ({len(records)} records, routes={meta.get('records_with_routes')})")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus-root", type=Path, default=_DEFAULT_CORPUS)
    p.add_argument("--campaign", type=int, choices=(1, 2))
    p.add_argument("--session", type=int)
    p.add_argument("--all-blessed", action="store_true")
    p.add_argument("--check", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.all_blessed:
        targets = list(PILOT_BLESSED_SESSIONS)
    elif args.campaign is not None and args.session is not None:
        targets = [(args.campaign, args.session)]
    else:
        p.error("specify --campaign and --session, or --all-blessed")

    ok = True
    for campaign_number, session in targets:
        try:
            if args.check:
                ok = _check_one(corpus_root=args.corpus_root, campaign_number=campaign_number, session=session) and ok
            else:
                summary = _materialize_one(
                    corpus_root=args.corpus_root,
                    campaign_number=campaign_number,
                    session=session,
                    dry_run=args.dry_run,
                )
                print(
                    f"{'DRY' if args.dry_run else 'WROTE'} "
                    f"C{campaign_number}S{session}: {summary['jsonl_rel']} "
                    f"({summary['record_count']} records, routes={summary['records_with_routes']})"
                )
        except (FileNotFoundError, BreadcrumbNormalizeError) as exc:
            print(f"FAIL C{campaign_number}S{session}: {exc}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
