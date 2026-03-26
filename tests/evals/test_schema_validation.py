from __future__ import annotations

import copy

import pytest

from src.contracts.schema_validation import validate_many
from tests.evals.scenario_utils import load_json, load_manifest, scenario_paths


def test_scenario_inputs_validate_against_contracts() -> None:
    manifest = load_manifest()
    for scenario in manifest["scenarios"]:
        paths = scenario_paths(scenario["id"])
        validate_many(load_json(paths["evidence_units"]), "evidence_unit.schema.json")
        validate_many(load_json(paths["facts"]), "fact.schema.json")
        validate_many(load_json(paths["conflicts"]), "conflict.schema.json")
        validate_many(load_json(paths["canon_decisions"]), "canon_decision.schema.json")


def test_campaign_evidence_requires_campaign_id() -> None:
    manifest = load_manifest()
    paths = scenario_paths(manifest["scenarios"][0]["id"])
    evidence = load_json(paths["evidence_units"])
    invalid = copy.deepcopy(evidence[0])
    invalid["canon_layer"] = "campaign"
    invalid["campaign_id"] = None
    with pytest.raises(Exception):
        validate_many([invalid], "evidence_unit.schema.json")

