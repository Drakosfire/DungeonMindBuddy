from pathlib import Path

from src.lexicon_phase_b.route_equivalence_manifest import build_route_equivalence_manifest


def _write_registry(path: Path, hub_path: str, setting_hub_path: str, slug: str = "lysandra") -> None:
    path.write_text(
        f"""[
  {{
    "slug": "{slug}",
    "display_name": "Lysandra",
    "aliases": [],
    "status": "tracked",
    "first_session": 1,
    "last_session": 13,
    "hub_path": "{hub_path}",
    "setting_hub_path": "{setting_hub_path}",
    "notes": ""
  }}
]""",
        encoding="utf-8",
    )


def test_route_id_slug_uses_entity_folder_for_file_style_paths(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "corpus" / "eldyrwild-markdown" / "Longmont Campaign" / "Campaign 1"
    campaign_dir.mkdir(parents=True)
    registry_path = campaign_dir / "_npc_registry.json"
    _write_registry(
        registry_path,
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/Captain Lysandra Ironveil/README.md",
        "corpus/eldyrwild-markdown/Elderwyld/NPCs/Captain Lysandra Ironveil/README.md",
    )

    records = build_route_equivalence_manifest(registry_path)

    assert records[0].from_route_id == "route:longmont-c1:npc:captain-lysandra-ironveil"
    assert records[0].to_route_id == "route:elderwyld:npc:captain-lysandra-ironveil"


def test_route_id_slug_uses_entity_folder_for_directory_style_paths(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "corpus" / "eldyrwild-markdown" / "Longmont Campaign" / "Campaign 1"
    campaign_dir.mkdir(parents=True)
    registry_path = campaign_dir / "_npc_registry.json"
    _write_registry(
        registry_path,
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/Captain Lysandra Ironveil/",
        "corpus/eldyrwild-markdown/Elderwyld/NPCs/Captain Lysandra Ironveil/",
    )

    records = build_route_equivalence_manifest(registry_path)

    assert records[0].from_route_id == "route:longmont-c1:npc:captain-lysandra-ironveil"
    assert records[0].to_route_id == "route:elderwyld:npc:captain-lysandra-ironveil"
