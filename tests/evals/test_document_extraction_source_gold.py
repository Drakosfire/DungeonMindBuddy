"""Structural integrity checks for the first source-pinned PDF gold slice."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = ROOT / "evals" / "document_extraction_gold" / "adventure_pdf_source_gold_v1.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CANONICAL_GOLD_SHA256 = "95653c04fa511c1c8853d0550413722b4f3d2d37be9cd79112b83e11bc5df8db"


def load_gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def test_sources_are_exactly_pinned_and_edition_claims_are_explicit() -> None:
    gold = load_gold()
    sources = gold["sources"]
    assert {source["source_id"] for source in sources} == {"conks", "sheep"}
    assert all(SHA256.fullmatch(source["pdf_sha256"]) for source in sources)
    assert all(source["page_count"] > 0 for source in sources)
    sheep = next(source for source in sources if source["source_id"] == "sheep")
    assert "v2" in sheep["operator_edition_label"]
    assert "does not encode v2" in sheep["edition_evidence"]


def test_cases_reference_valid_physical_pages_and_unique_ids() -> None:
    gold = load_gold()
    sources = {source["source_id"]: source for source in gold["sources"]}
    cases = gold["cases"]
    assert len({case["case_id"] for case in cases}) == len(cases)
    for case in cases:
        source = sources[case["source_id"]]
        assert 1 <= case["physical_page"] <= source["page_count"]
        assert case["block_type"] in {"statblock", "table"}
        assert case["block_title"].strip()


def test_statblock_gold_preserves_exact_source_values() -> None:
    cases = {case["case_id"]: case for case in load_gold()["cases"]}
    tree = cases["conks-grotesque-tree-statblock"]["expected_fields"]
    noke = cases["sheep-ahmed-noke-statblock"]["expected_fields"]
    assert tree["senses"] == "blindsight 600 ft. (blind beyond this radius), passive Perception 10"
    assert tree["hit_points"] == "39 (6d8+12)"
    assert noke["hit_points"] == "55 (10d8 + 10)"
    assert set(tree["ability_scores"]) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    assert set(noke["ability_scores"]) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}


def test_table_gold_covers_each_d12_row_once() -> None:
    case = next(
        case
        for case in load_gold()["cases"]
        if case["case_id"] == "conks-appendix-c-male-villager-names"
    )
    rows = case["rows"]
    assert [row["roll"] for row in rows] == list(range(1, 13))
    assert len({row["name"] for row in rows}) == 12
    assert all(row["notes"] == "" for row in rows)


def test_unmatched_map_sources_remain_excluded() -> None:
    gold = load_gold()
    excluded = gold["excluded_asset_lineage"]
    assert len(excluded) == 2
    assert all(SHA256.fullmatch(asset["asset_sha256"]) for asset in excluded)
    assert all(
        asset["declared_source_pdf_sha256"] != asset["selected_source_pdf_sha256"]
        and asset["status"] == "not linked to this PDF; withheld from source gold"
        for asset in excluded
    )


def test_fixture_matches_the_reviewed_canonical_snapshot() -> None:
    payload = json.dumps(
        load_gold(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == CANONICAL_GOLD_SHA256
