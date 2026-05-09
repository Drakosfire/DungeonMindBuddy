from pathlib import Path

from src.lexicon_phase_b.route_equivalence_manifest import build_route_equivalence_manifest


def test_entity_kind_inference_location_for_seed_paths(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "corpus" / "eldyrwild-markdown" / "Longmont Campaign" / "Campaign 2"
    campaign_dir.mkdir(parents=True)
    registry_path = campaign_dir / "_npc_registry.json"
    registry_path.write_text(
        """[
  {
    "slug": "wolf-manor",
    "display_name": "Wolf Manor",
    "aliases": [],
    "status": "tracked",
    "first_session": 1,
    "last_session": 13,
    "hub_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Locations/Wolf Manor/README.md",
    "setting_hub_path": "corpus/eldyrwild-markdown/Elderwyld/Locations/Wolf Manor/README.md",
    "notes": ""
  }
]""",
        encoding="utf-8",
    )

    records = build_route_equivalence_manifest(registry_path)
    assert len(records) == 1
    assert records[0].entity_kind == "location"
    assert records[0].record_id == "route-eq:longmont-c2:location:wolf-manor"
