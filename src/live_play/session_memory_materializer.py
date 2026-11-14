"""Materialize session memory from corpus breadcrumbs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.session_memory.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
)
from src.live_play.recap_derivative_provenance import (
    archive_existing,
    atomic_write_bytes,
)
from corpus.session_recap_paths import (
    breadcrumbed_relpath,
    resolve_under_corpus,
    session_memory_jsonl_relpath,
    session_memory_meta_relpath,
)


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
