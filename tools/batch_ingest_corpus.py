#!/usr/bin/env python3
"""Batch-ingest every markdown file under corpus/eldyrwild-markdown into one store.

Uses the same pipeline as the interactive CLI (frontmatter, gates, MODEL_POLICY).

Usage (from DungeonMindBuddy repo root):
  uv run python tools/batch_ingest_corpus.py --store ./dungeonbuddy_store_nano_full

Optional:
  --corpus-root PATH   default: corpus/eldyrwild-markdown
  --limit N            ingest only first N files (sorted paths)
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cli import DungeonBuddyCLI  # noqa: E402


class Tee:
    def __init__(self, *files: object) -> None:
        self.files = files

    def write(self, data: str) -> None:
        for f in self.files:
            f.write(data)
            f.flush()

    def flush(self) -> None:
        for f in self.files:
            f.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch corpus ingest")
    parser.add_argument(
        "--store",
        type=Path,
        default=Path("./dungeonbuddy_store_nano_full"),
        help="Fact store directory (created if missing)",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path("corpus/eldyrwild-markdown"),
        help="Root directory to scan for *.md",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max files (0 = all)")
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Append full transcript here (default: <store>/logs/batch_ingest.log)",
    )
    args = parser.parse_args()

    corpus_root = args.corpus_root.resolve()
    if not corpus_root.is_dir():
        print(f"Error: corpus root not found: {corpus_root}", file=sys.stderr)
        return 1

    store_dir = args.store.resolve()
    store_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.log or (store_dir / "logs" / "batch_ingest.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    paths = sorted(corpus_root.rglob("*.md"))
    if args.limit > 0:
        paths = paths[: args.limit]

    started = datetime.now(timezone.utc).isoformat()
    summary: dict[str, object] = {
        "started_at": started,
        "store": str(store_dir),
        "corpus_root": str(corpus_root),
        "file_count": len(paths),
        "results": [],
    }

    with log_path.open("a", encoding="utf-8") as logf:
        logf.write(f"\n=== batch_ingest start {started} files={len(paths)} ===\n")
        tee = Tee(sys.__stdout__, logf)
        old_stdout = sys.stdout
        sys.stdout = tee  # type: ignore[assignment]

        try:
            cli = DungeonBuddyCLI(store_dir=store_dir, verbose=True)
            for i, path in enumerate(paths, start=1):
                rel = path.relative_to(corpus_root) if path.is_relative_to(corpus_root) else path
                print(f"\n[{i}/{len(paths)}] ingest {rel}", flush=True)
                facts_before = len(cli.store.facts)
                entities_before = len(cli.store.entities)
                evidence_before = len(cli.store.evidence_units)
                line = f"ingest {shlex.quote(str(path))}"
                cli.handle_line(line)
                entry = {
                    "path": str(path),
                    "facts_delta": len(cli.store.facts) - facts_before,
                    "entities_delta": len(cli.store.entities) - entities_before,
                    "evidence_delta": len(cli.store.evidence_units) - evidence_before,
                }
                summary["results"].append(entry)
        finally:
            sys.stdout = old_stdout

        ended = datetime.now(timezone.utc).isoformat()
        logf.write(f"=== batch_ingest end {ended} ===\n")

    summary["ended_at"] = ended
    summary_path = store_dir / "logs" / "batch_ingest_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote summary: {summary_path}")
    print(f"Transcript: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
