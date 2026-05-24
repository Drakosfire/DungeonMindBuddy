#!/usr/bin/env python3
"""Write beat-enriched session-memory JSONL + meta next to canonical pilot files.

Prerequisite: a unit-annotations ingest report or raw ``dmb_recap_unit_annotations_v1``
JSON per session (same shape accepted by ``scene_beat_memory.load_unit_annotations_payload``).

Output files (default) sit alongside canonical ``*.records_meta.jsonl``:

  ``Session NN - <slug>.scene_beat.records_meta.jsonl``
  ``Session NN - <slug>.scene_beat.records_meta.json``

This keeps ``uv run python scripts/materialize_session_memory.py --all-blessed --check`` valid
until the project explicitly promotes scene-beat rows into the canonical filenames and
refreshes the materializer check vectors.

Example (after running ``breadcrumb_unit_annotations_run`` for Session 1):

  uv run python scripts/build_scene_beat_session_memory.py \\
    --corpus-root corpus/eldyrwild-markdown \\
    --campaign 1 --session 1 \\
    --unit-annotations-json evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-14/unit_annotations_c1s1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.sentence_routing_retrieval_falsification.scene_beat_memory import (  # noqa: E402
    write_scene_beat_records,
)
from src.corpus.session_recap_paths import (  # noqa: E402
    resolve_under_corpus,
    session_memory_jsonl_relpath,
)


def _scene_beat_paths(*, corpus_root: Path, campaign_number: int, session: int) -> tuple[Path, Path, Path]:
    jsonl_rel = session_memory_jsonl_relpath(
        campaign_number=campaign_number, session=session, corpus_root=corpus_root
    )
    base_jsonl = resolve_under_corpus(corpus_root, jsonl_rel)
    if not base_jsonl.is_file():
        raise FileNotFoundError(f"missing canonical session-memory JSONL: {base_jsonl}")
    name = base_jsonl.name
    suffix = ".records_meta.jsonl"
    if not name.endswith(suffix):
        raise ValueError(f"unexpected session-memory filename: {name!r}")
    prefix = name[: -len(suffix)]
    out_jsonl = base_jsonl.with_name(prefix + ".scene_beat.records_meta.jsonl")
    out_meta = base_jsonl.with_name(prefix + ".scene_beat.records_meta.json")
    return base_jsonl, out_jsonl, out_meta


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus-root", type=Path, default=_REPO_ROOT / "corpus" / "eldyrwild-markdown")
    p.add_argument("--campaign", type=int, required=True, choices=(1, 2))
    p.add_argument("--session", type=int, required=True, help="Single session number (repeat command per session).")
    p.add_argument("--unit-annotations-json", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true", help="Print resolved paths only; do not write.")
    args = p.parse_args()

    corpus_root = args.corpus_root.resolve()
    records_jsonl, out_jsonl, out_meta = _scene_beat_paths(
        corpus_root=corpus_root,
        campaign_number=int(args.campaign),
        session=int(args.session),
    )
    ann = args.unit_annotations_json.resolve()
    if not args.dry_run and not ann.is_file():
        raise SystemExit(f"missing unit annotations JSON: {ann}")

    if args.dry_run:
        print("records_jsonl:", records_jsonl)
        print("unit_annotations:", ann)
        print("out_jsonl:", out_jsonl)
        print("out_meta:", out_meta)
        return 0

    summary = write_scene_beat_records(
        records_jsonl=records_jsonl,
        unit_annotations_json=ann,
        out_jsonl=out_jsonl,
        out_meta=out_meta,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
