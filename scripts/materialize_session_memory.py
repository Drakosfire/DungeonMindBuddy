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
)
from src.live_play.recap_derivative_provenance import (  # noqa: E402
    archive_existing,
    atomic_write_bytes,
)
from src.corpus.session_recap_paths import (  # noqa: E402
    PILOT_BLESSED_SESSIONS,
    breadcrumbed_relpath,
    resolve_under_corpus,
    session_memory_jsonl_relpath,
    session_memory_meta_relpath,
)

_DEFAULT_CORPUS = _REPO_ROOT / "corpus" / "eldyrwild-markdown"


def _expected_session_memory_outputs(
    *,
    corpus_root: Path,
    campaign_number: int,
    session: int,
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
    jsonl_bytes = (
        "\n".join(json.dumps(record.to_json_dict(), ensure_ascii=False) for record in records)
        + ("\n" if records else "")
    ).encode("utf-8")
    meta_bytes = (json.dumps(meta, indent=2) + "\n").encode("utf-8")
    return {
        "breadcrumb_rel": breadcrumb_rel,
        "jsonl_rel": jsonl_rel,
        "meta_rel": meta_rel,
        "records": records,
        "meta": meta,
        "jsonl_bytes": jsonl_bytes,
        "meta_bytes": meta_bytes,
    }


def _materialize_one(
    *,
    corpus_root: Path,
    campaign_number: int,
    session: int,
    dry_run: bool,
    force: bool = False,
) -> dict[str, object]:
    expected = _expected_session_memory_outputs(
        corpus_root=corpus_root,
        campaign_number=campaign_number,
        session=session,
    )
    breadcrumb_rel = str(expected["breadcrumb_rel"])
    jsonl_rel = str(expected["jsonl_rel"])
    meta_rel = str(expected["meta_rel"])
    records = expected["records"]
    meta = expected["meta"]
    assert isinstance(records, list)
    assert isinstance(meta, dict)
    jsonl_path = resolve_under_corpus(corpus_root, jsonl_rel)
    meta_path = resolve_under_corpus(corpus_root, meta_rel)
    expected_jsonl_bytes = expected["jsonl_bytes"]
    expected_meta_bytes = expected["meta_bytes"]
    assert isinstance(expected_jsonl_bytes, bytes)
    assert isinstance(expected_meta_bytes, bytes)

    existing = [path for path in (jsonl_path, meta_path) if path.exists()]
    current = (
        jsonl_path.is_file()
        and meta_path.is_file()
        and jsonl_path.read_bytes() == expected_jsonl_bytes
        and meta_path.read_bytes() == expected_meta_bytes
    )
    archived: list[dict[str, str]] = []
    if existing and current:
        outcome = "reused"
    elif existing and not force:
        outcome = "stale"
    else:
        outcome = "refreshed" if existing else "created"
        if not dry_run:
            if force and existing:
                archived = archive_existing(paths=existing, corpus_root=corpus_root)
            atomic_write_bytes(jsonl_path, expected_jsonl_bytes)
            atomic_write_bytes(meta_path, expected_meta_bytes)

    return {
        "campaign_number": campaign_number,
        "session": session,
        "breadcrumb_rel": breadcrumb_rel,
        "jsonl_rel": jsonl_rel,
        "meta_rel": meta_rel,
        "record_count": len(records),
        "records_with_routes": meta.get("records_with_routes"),
        "outcome": outcome,
        "archived_artifacts": archived,
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

    expected = _expected_session_memory_outputs(
        corpus_root=corpus_root,
        campaign_number=campaign_number,
        session=session,
    )
    expected_jsonl = expected["jsonl_bytes"]
    expected_meta = json.loads(bytes(expected["meta_bytes"]).decode("utf-8"))
    if jsonl_path.read_bytes() != bytes(expected_jsonl):
        print(f"DRIFT jsonl {jsonl_rel}", file=sys.stderr)
        return False
    on_disk_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if on_disk_meta != expected_meta:
        print(f"DRIFT meta {meta_rel}", file=sys.stderr)
        return False
    print(f"OK {jsonl_rel} ({len(expected_jsonl.decode('utf-8').splitlines())} records)")
    return True


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
            from src.live_play.recap_ingest_pipeline import inspect_recap_ingest_status

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
