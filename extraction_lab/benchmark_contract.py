from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from extraction_lab.anchor_schema import EntityGoldAnchor, FactGoldAnchor


BENCHMARK_CONTRACT_VERSION = 1


def _stable_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _logical_source_locator(path: Path, corpus_source_root: Path) -> str | None:
    try:
        return path.resolve().relative_to(corpus_source_root.resolve()).as_posix()
    except ValueError:
        return None


def compute_corpus_identity(
    *, source_paths: Iterable[Path], corpus_source_root: Path | None
) -> dict[str, Any]:
    if corpus_source_root is None:
        return {
            "available": False,
            "fingerprint": None,
            "source_count": 0,
            "unavailable_reasons": ["corpus_source_root_required"],
        }

    paths = list(source_paths)
    if not paths:
        return {
            "available": False,
            "fingerprint": None,
            "source_count": 0,
            "unavailable_reasons": ["source_cohort_unproven"],
        }

    sources: list[dict[str, str]] = []
    reasons: list[str] = []
    for path in paths:
        locator = _logical_source_locator(path, corpus_source_root)
        if locator is None:
            reasons.append("source_outside_corpus_root")
            continue
        if not path.is_file():
            reasons.append(f"source_missing:{locator}")
            continue
        sources.append(
            {
                "locator": locator,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    if reasons or not sources:
        if not sources and not reasons:
            reasons.append("corpus_sources_empty")
        return {
            "available": False,
            "fingerprint": None,
            "source_count": len(sources),
            "unavailable_reasons": sorted(set(reasons)),
        }

    sources.sort(key=lambda row: row["locator"])
    return {
        "available": True,
        "fingerprint": _stable_sha256(sources),
        "source_count": len(sources),
        "unavailable_reasons": [],
    }


def _canonical_anchors(
    anchors: Iterable[EntityGoldAnchor | FactGoldAnchor], surface: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for anchor in anchors:
        if anchor.surface != surface:
            continue
        row = anchor.model_dump(mode="json", exclude_none=True)
        for unordered_field in (
            "expected_names",
            "match_keywords",
            "alternative_attributes",
        ):
            if unordered_field in row:
                row[unordered_field] = sorted(row[unordered_field])
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("anchor_id", "")),
            json.dumps(row, sort_keys=True),
        ),
    )


def compute_benchmark_contract(
    *,
    surface: str,
    source_paths: Iterable[Path],
    corpus_source_root: Path | None,
    entity_anchors: Iterable[EntityGoldAnchor],
    fact_anchors: Iterable[FactGoldAnchor],
) -> dict[str, Any]:
    canonical_entities = _canonical_anchors(entity_anchors, surface)
    canonical_facts = _canonical_anchors(fact_anchors, surface)
    corpus = compute_corpus_identity(
        source_paths=source_paths, corpus_source_root=corpus_source_root
    )
    gold_payload = {
        "entity_anchors": canonical_entities,
        "fact_anchors": canonical_facts,
    }
    return {
        "contract_version": BENCHMARK_CONTRACT_VERSION,
        "surface": surface,
        "corpus": corpus,
        "gold": {
            "fingerprint": _stable_sha256(gold_payload),
            "entity_fingerprint": _stable_sha256(canonical_entities),
            "fact_fingerprint": _stable_sha256(canonical_facts),
            "entity_anchor_count": len(canonical_entities),
            "fact_anchor_count": len(canonical_facts),
        },
    }
