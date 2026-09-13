from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Sequence

from src.ingestion.chunker import chunk_document
from src.ingestion.frontmatter import load_document_frontmatter


def _summary(values: list[int]) -> dict[str, float | int]:
    ordered = sorted(values)
    if not ordered:
        return {"min": 0, "median": 0, "p95": 0, "max": 0}
    return {
        "min": ordered[0],
        "median": median(ordered),
        "p95": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
        "max": ordered[-1],
    }


def _iter_markdown(root: Path, paths: Sequence[Path] | None) -> list[Path]:
    if paths is not None:
        return [path.resolve() for path in paths]
    return sorted(path for path in root.rglob("*.md") if "_dungeonbuddy" not in path.parts)


def census_corpus(
    corpus_root: Path,
    *,
    batch_size: int = 5,
    paths: Sequence[Path] | None = None,
) -> dict[str, Any]:
    root = corpus_root.resolve()
    discovered = _iter_markdown(root, paths)
    rows: list[dict[str, Any]] = []
    failures: Counter[str] = Counter()
    normalized = 0
    for path in discovered:
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        raw_bytes = path.stat().st_size if path.is_file() else 0
        try:
            needed_normalization = False
            try:
                load_document_frontmatter(path)
            except Exception:
                needed_normalization = True
            metadata, _ = load_document_frontmatter(path, normalize_legacy=True)
            units = chunk_document(path, normalize_legacy_frontmatter=True)
            if needed_normalization:
                normalized += 1
            unit_bytes = sum(len(str(unit.get("text", "")).encode("utf-8")) for unit in units)
            is_recap = bool(metadata and metadata.document_class == "play")
            rows.append(
                {
                    "path": rel,
                    "raw_bytes": raw_bytes,
                    "evidence_units": len(units),
                    "evidence_text_bytes": unit_bytes,
                    "compatibility_normalized": needed_normalization,
                    "expected_entity_calls": (
                        len(units) if is_recap else math.ceil(len(units) / batch_size)
                    ),
                    "expected_fact_calls": math.ceil(len(units) / batch_size),
                }
            )
        except Exception as exc:
            failures[type(exc).__name__] += 1
            rows.append({"path": rel, "raw_bytes": raw_bytes, "error": type(exc).__name__})
    accepted = [row for row in rows if "error" not in row]
    if paths is not None and len(discovered) != len(paths):
        raise ValueError("census path list changed during discovery")
    return {
        "schema": "dmb_campaign_memory_corpus_census_v1",
        "corpus_root": str(root),
        "markdown_source_count": len(discovered),
        "raw_source_bytes": sum(int(row["raw_bytes"]) for row in rows),
        "parseable_source_count": len(accepted),
        "compatibility_normalized_source_count": normalized,
        "rejected_source_count": len(discovered) - len(accepted),
        "rejection_buckets": dict(sorted(failures.items())),
        "evidence_unit_count": sum(int(row["evidence_units"]) for row in accepted),
        "evidence_unit_text_bytes": sum(int(row["evidence_text_bytes"]) for row in accepted),
        "expected_entity_calls": sum(int(row["expected_entity_calls"]) for row in accepted),
        "expected_fact_calls": sum(int(row["expected_fact_calls"]) for row in accepted),
        "batch_size": batch_size,
        "source_bytes_distribution": _summary([int(row["raw_bytes"]) for row in rows]),
        "evidence_units_distribution": _summary(
            [int(row["evidence_units"]) for row in accepted]
        ),
        "largest_sources": sorted(
            accepted, key=lambda row: int(row["evidence_units"]), reverse=True
        )[:20],
        "sources": rows,
        "model_calls": 0,
        "silent_skip_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = census_corpus(args.corpus_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key not in {"sources", "largest_sources"}},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
