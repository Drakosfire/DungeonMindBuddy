from __future__ import annotations

from src.reducer.canon_projection import project_entity_state
from src.reducer.projection_compare import (
    assert_attribute_keys_match_golden_contract,
    normalize_projection_for_compare,
)
from tests.evals.scenario_utils import load_json, load_manifest, scenario_paths


def test_projection_matches_all_golden_outputs() -> None:
    manifest = load_manifest()
    for scenario in manifest["scenarios"]:
        paths = scenario_paths(scenario["id"])
        campaign_id = scenario["campaign_id"]

        evidence_units = load_json(paths["evidence_units"])
        facts = load_json(paths["facts"])
        conflicts = load_json(paths["conflicts"])
        canon_decisions = load_json(paths["canon_decisions"])

        world_projection = project_entity_state(
            evidence_units=evidence_units,
            facts=facts,
            conflicts=conflicts,
            canon_decisions=canon_decisions,
            campaign_id=None,
        )
        expected_world = load_json(paths["world_expected"])
        assert_attribute_keys_match_golden_contract(
            actual_projection=world_projection,
            expected_projection=expected_world,
            label=f"{scenario['id']}/world",
        )
        assert normalize_projection_for_compare(world_projection) == expected_world, (
            f"world mismatch in {scenario['id']}"
        )

        campaign_projection = project_entity_state(
            evidence_units=evidence_units,
            facts=facts,
            conflicts=conflicts,
            canon_decisions=canon_decisions,
            campaign_id=campaign_id,
        )
        expected_campaign = load_json(
            paths["world_expected"].parent / f"campaign_{campaign_id}_projection.json"
        )
        assert_attribute_keys_match_golden_contract(
            actual_projection=campaign_projection,
            expected_projection=expected_campaign,
            label=f"{scenario['id']}/campaign",
        )
        assert normalize_projection_for_compare(campaign_projection) == expected_campaign, (
            f"campaign mismatch in {scenario['id']}"
        )
