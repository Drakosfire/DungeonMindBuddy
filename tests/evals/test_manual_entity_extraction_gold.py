"""Structural checks for manual entity-extraction gold (mirathorn M1 sources).

Scoring against stage_entities.json is intentionally not implemented here; add when
you wire chunk-to-segment alignment and fuzzy name matching.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = ROOT / "evals" / "llm_ingestion_slice" / "gold" / "manual_entity_extraction_gold.json"
MANIFEST_PATH = ROOT / "evals" / "llm_ingestion_slice" / "slice_manifest.json"


def _load_gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def test_manual_entity_gold_file_exists() -> None:
    assert GOLD_PATH.is_file(), f"missing {GOLD_PATH}"


def test_manual_entity_gold_matches_manifest_paths() -> None:
    gold = _load_gold()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for src in gold["sources"]:
        key = src["key"]
        assert key in manifest["sources"]
        assert src["path"] == manifest["sources"][key]["path"]
        full = ROOT / src["path"]
        assert full.is_file(), f"gold source path missing: {src['path']}"


def test_manual_entity_gold_segment_shape() -> None:
    gold = _load_gold()
    allowed = set(gold.get("entity_classes_allowed", gold.get("entity_types_allowed", [])))
    for src in gold["sources"]:
        for seg in src["segments"]:
            assert "segment_id" in seg
            for ent in seg.get("expected_entities", []):
                assert "display_name" in ent and ent["display_name"].strip()
                assert ent.get("entity_class", ent.get("entity_type")) in allowed
                tags = ent.get("entity_tags")
                if tags is not None:
                    assert isinstance(tags, list)
                    assert all(isinstance(t, str) and t.strip() for t in tags)
                imp = ent.get("importance")
                if imp is not None:
                    assert imp in {"core", "supporting", "optional"}


def test_manual_entity_gold_slice_catalog_ids_unique() -> None:
    gold = _load_gold()
    catalog = gold["slice_evidence_catalog_entities"]["entities"]
    ids = [e["entity_id"] for e in catalog]
    assert len(ids) == len(set(ids))


def test_temporal_provenance_matches_deterministic_slice_rows() -> None:
    gold = _load_gold()
    rows = gold["temporal_provenance"]["deterministic_slice_evidence_gold"]
    assert len(rows) == 6
    seen: set[str] = set()
    for row in rows:
        eid = row["evidence_id"]
        assert eid not in seen
        seen.add(eid)
        must = row["facts_derived_must_include_temporal"]
        assert "asserted_in_session" in must
        assert "sequence_index_within_session" in must
        assert row["source_order_index"] == must["sequence_index_within_session"]


def test_aligned_segments_fact_temporal_matches_slice_table() -> None:
    gold = _load_gold()
    by_eid = {
        r["evidence_id"]: r for r in gold["temporal_provenance"]["deterministic_slice_evidence_gold"]
    }
    for src in gold["sources"]:
        for seg in src["segments"]:
            eid = seg.get("aligns_with_slice_evidence_id")
            if not eid:
                continue
            row = by_eid[eid]
            ft = seg["expected_fact_temporal"]
            ev = seg["expected_evidence_temporal"]
            assert ft == row["facts_derived_must_include_temporal"]
            assert ev["canon_layer"] == row["canon_layer"]
            assert ev["campaign_id"] == row["campaign_id"]
            assert ev["source_class"] == row["source_class"]
            assert ev["inferred_session"] == row["inferred_session"]
            assert ev["document_session"] == row["document_session"]
            assert ev["source_order_index"] == row["source_order_index"]
