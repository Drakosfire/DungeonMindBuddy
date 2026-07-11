"""Tests for candidate bundle validation (PR006)."""

from __future__ import annotations

import json
from pathlib import Path

from graph_memory.materialization.acceptance_manifest import (
    build_inventory,
    load_acceptance_manifest,
)
from graph_memory.materialization.candidate_bundle import (
    build_ambiguous_mention_fixture_candidate,
    build_deterministic_acceptance_bundle,
    validate_candidate_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MINIMAL_MANIFEST = (
    REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_acceptance_manifest.json"
)


def test_validate_minimal_fixture_bundle() -> None:
    fixture = REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_candidate_bundle.json"
    bundle = json.loads(fixture.read_text(encoding="utf-8"))
    errors = validate_candidate_bundle(bundle)
    assert errors == []


def test_ambiguous_mention_fixture_has_unresolved() -> None:
    graph = build_ambiguous_mention_fixture_candidate()
    assert graph["unresolved_mentions"]
    assert graph["unresolved_mentions"][0]["candidate_node_ids"]


def test_build_deterministic_bundle_matches_inventory_paths() -> None:
    manifest = load_acceptance_manifest(MINIMAL_MANIFEST)
    bundle = build_deterministic_acceptance_bundle(
        REPO_ROOT,
        manifest,
        manifest_path=MINIMAL_MANIFEST,
    )
    inventory = build_inventory(
        manifest,
        repo_root=REPO_ROOT,
        manifest_path=MINIMAL_MANIFEST,
    )
    inv_paths = {item["path"] for item in inventory["source_items"]}
    bundle_paths = {entry["source_uri"] for entry in bundle["sources"]}
    assert inv_paths == bundle_paths
