from __future__ import annotations

from pathlib import Path

from tests.evals.scenario_utils import load_manifest, scenario_paths


def test_manifest_has_exactly_six_required_scenarios() -> None:
    manifest = load_manifest()
    assert len(manifest["scenarios"]) == 6


def test_all_scenarios_have_required_behavior_tags() -> None:
    manifest = load_manifest()
    required_tags = set(manifest["required_behavior_tags"])
    for scenario in manifest["scenarios"]:
        tags = set(scenario["behavior_tags"])
        assert required_tags.issubset(tags)


def test_all_scenarios_have_required_files() -> None:
    manifest = load_manifest()
    for scenario in manifest["scenarios"]:
        campaign_id = scenario["campaign_id"]
        paths = scenario_paths(scenario["id"])
        for path in paths.values():
            assert path.exists(), f"Missing required scenario file: {path}"
        campaign_expected = (
            Path(paths["world_expected"].parent)
            / f"campaign_{campaign_id}_projection.json"
        )
        assert campaign_expected.exists(), (
            "Missing required campaign projection file "
            f"for scenario {scenario['id']}: {campaign_expected}"
        )

