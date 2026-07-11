"""Tests for candidate → contribution mapping (PR006)."""

from __future__ import annotations

import json
from pathlib import Path

import graph_memory.kernel as kernel

from graph_memory.materialization.candidate_to_contribution import (
    bundle_sources_to_contributions,
    map_inventory_domain_to_kernel,
    source_entry_to_contribution,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_candidate_bundle.json"


def test_domain_mapping() -> None:
    assert map_inventory_domain_to_kernel("recap") == "recap"
    assert map_inventory_domain_to_kernel("pc_hub") == "worldbuilding"
    assert map_inventory_domain_to_kernel("mechanical") == "statblock"
    assert (
        map_inventory_domain_to_kernel(
            "campaign_hub",
            source_uri="corpus/.../Journey - Mireward Reach (Campaign 2).md",
        )
        == "worldbuilding"
    )


def test_recap_contribution_includes_pc_edge_stub_nodes() -> None:
    bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))
    recap = next(s for s in bundle["sources"] if s["source_domain"] == "recap")
    contrib = source_entry_to_contribution(recap)
    node_ids = {a.subject_node_id for a in contrib.accepted_assertions if a.assertion_kind == "node"}
    assert "pc_caelynn" in node_ids
    edge_assertions = [a for a in contrib.accepted_assertions if a.assertion_kind == "edge"]
    assert edge_assertions
    for assertion in contrib.accepted_assertions:
        if assertion.acceptance_state == "accepted":
            assert assertion.source_artifact_id
            assert assertion.source_revision_id


def test_bundle_contributions_have_deterministic_ids() -> None:
    bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))
    first = bundle_sources_to_contributions(bundle)
    second = bundle_sources_to_contributions(bundle)
    assert [c.contribution_id for c in first] == [c.contribution_id for c in second]
