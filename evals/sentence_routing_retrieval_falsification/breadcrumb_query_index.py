#!/usr/bin/env python3
"""Build a deterministic JSONL session-memory index from a breadcrumb markdown artifact.

This is a thin wrapper around ``breadcrumb_normalize.normalize_breadcrumb_artifact`` +
``write_records_jsonl``. Query logic lives in ``src.agent.session_memory_query``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--breadcrumb-md", type=Path, required=True)
    p.add_argument("--corpus-root", type=Path, required=True)
    p.add_argument("--out-jsonl", type=Path, required=True)
    args = p.parse_args()

    text = args.breadcrumb_md.read_text(encoding="utf-8")
    records, meta = normalize_breadcrumb_artifact(artifact_text=text, corpus_root=args.corpus_root)
    write_records_jsonl(records, args.out_jsonl)
    print(f"wrote {args.out_jsonl} ({len(records)} records); meta={meta}")


if __name__ == "__main__":
    main()
