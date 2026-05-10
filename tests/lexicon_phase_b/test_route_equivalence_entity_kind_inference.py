from pathlib import Path

from src.lexicon_phase_b.route_equivalence_manifest import build_route_equivalence_manifest


def test_live_registry_seed_builds_for_campaign_1() -> None:
    registry = Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json")
    edges = build_route_equivalence_manifest(registry)
    assert edges
    assert all(e.campaign_id == "longmont-c1" for e in edges)
    assert all(e.source_type == "npc_registry" for e in edges)


def test_unknown_kind_is_filtered_out(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "corpus" / "eldyrwild-markdown" / "Longmont Campaign" / "Campaign 1"
    campaign_dir.mkdir(parents=True)
    registry_path = campaign_dir / "_npc_registry.json"
    registry_path.write_text(
        """[
  {
    "slug": "mystery",
    "display_name": "Mystery",
    "aliases": [],
    "status": "tracked",
    "first_session": 1,
    "last_session": 1,
    "hub_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/People/Mystery/README.md",
    "setting_hub_path": "corpus/eldyrwild-markdown/Elderwyld/People/Mystery/README.md",
    "notes": ""
  }
]""",
        encoding="utf-8",
    )

    edges = build_route_equivalence_manifest(registry_path)
    assert edges == []
