from __future__ import annotations

import json
from hashlib import sha256

from src.reducer.canon_projection import project_entity_state
from tests.evals.scenario_utils import load_json, load_manifest, scenario_paths


def _hash_projection(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def test_provenance_is_present_for_every_projected_attribute() -> None:
    manifest = load_manifest()
    for scenario in manifest["scenarios"]:
        paths = scenario_paths(scenario["id"])
        campaign_projection = project_entity_state(
            evidence_units=load_json(paths["evidence_units"]),
            facts=load_json(paths["facts"]),
            conflicts=load_json(paths["conflicts"]),
            canon_decisions=load_json(paths["canon_decisions"]),
            campaign_id=scenario["campaign_id"],
        )
        for entity_data in campaign_projection["entities"].values():
            for attribute_data in entity_data["attributes"].values():
                assert attribute_data["provenance_evidence_ids"]


def test_world_projection_remains_world_layer_only() -> None:
    manifest = load_manifest()
    for scenario in manifest["scenarios"]:
        paths = scenario_paths(scenario["id"])
        world_projection = project_entity_state(
            evidence_units=load_json(paths["evidence_units"]),
            facts=load_json(paths["facts"]),
            conflicts=load_json(paths["conflicts"]),
            canon_decisions=load_json(paths["canon_decisions"]),
            campaign_id=None,
        )
        for entity_data in world_projection["entities"].values():
            for attribute_data in entity_data["attributes"].values():
                assert attribute_data["source_layer"] == "world"


def test_projection_is_deterministic_over_five_runs() -> None:
    manifest = load_manifest()
    run_hashes: list[str] = []
    for _ in range(5):
        bundle = {}
        for scenario in manifest["scenarios"]:
            paths = scenario_paths(scenario["id"])
            bundle[scenario["id"]] = project_entity_state(
                evidence_units=load_json(paths["evidence_units"]),
                facts=load_json(paths["facts"]),
                conflicts=load_json(paths["conflicts"]),
                canon_decisions=load_json(paths["canon_decisions"]),
                campaign_id=scenario["campaign_id"],
            )
        run_hashes.append(_hash_projection(bundle))
    assert len(set(run_hashes)) == 1

