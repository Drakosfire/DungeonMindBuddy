"""Tests for the ingested corpus library builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_ingested_corpus_library import SCHEMA_ID, build_library

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "Docs/data/ingested-corpus-library/ingested_corpus_library.json"


def test_build_library_covers_both_campaigns() -> None:
    lib = build_library(root=ROOT)
    ids = {c["campaign_id"] for c in lib["campaigns"]}
    assert ids == {"longmont-c1", "longmont-c2"}


def test_c2_has_normalized_and_breadcrumb_memory_sessions() -> None:
    lib = build_library(root=ROOT)
    c2 = next(c for c in lib["campaigns"] if c["campaign_id"] == "longmont-c2")
    tiers = {s["session"]: s["pipeline_tier"] for s in c2["sessions"]}
    assert tiers[1] == "normalized_only"
    assert tiers[20] == "breadcrumb_memory"
    assert tiers[22] == "full_with_staging"


def test_committed_artifact_matches_schema() -> None:
    assert ARTIFACT.is_file(), "run scripts/build_ingested_corpus_library.py to refresh artifact"
    lib = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert lib["schema"] == SCHEMA_ID
    assert lib["summary"]["total_corpus_md_files"] >= 300
    assert lib["retrieval_activation"]["c2s23_planning_manifest"]["entry_count"] == 43
    dogfood = lib["retrieval_activation"]["c2s23_dogfood_full_manifest"]
    assert dogfood["exists"] is True
    assert dogfood["entry_count"] >= 160
    assert lib["retrieval_activation"]["ingest_routes_in_dogfood_full_manifest"] > lib[
        "retrieval_activation"
    ]["ingest_routes_in_c2s23_manifest"]
