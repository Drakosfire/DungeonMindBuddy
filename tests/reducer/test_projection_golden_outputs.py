from __future__ import annotations

from src.reducer.canon_projection import project_entity_state
from tests.evals.scenario_utils import load_json, load_manifest, scenario_paths


def _normalize_projection_for_compare(projection: dict) -> dict:
    # local deep copy without importing copy for a tiny fixture-sized payload
    payload = {"campaign_id": projection.get("campaign_id"), "entities": {}, "conflicts": projection.get("conflicts", []), "metrics": projection.get("metrics", {})}
    for entity_id, entity_payload in projection.get("entities", {}).items():
        attrs = {}
        for attr_name, attr_payload in entity_payload.get("attributes", {}).items():
            cleaned = dict(attr_payload)
            cleaned.pop("source_class", None)
            cleaned.pop("source_truth_state", None)
            attrs[attr_name] = cleaned
        payload["entities"][entity_id] = {"attributes": attrs}
    return payload


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
        assert _normalize_projection_for_compare(world_projection) == expected_world, (
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
        assert _normalize_projection_for_compare(campaign_projection) == expected_campaign, (
            f"campaign mismatch in {scenario['id']}"
        )

