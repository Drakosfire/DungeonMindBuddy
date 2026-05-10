from pathlib import Path

import pytest

from src.lexicon_phase_b.route_equivalence_manifest import build_route_equivalence_manifest


def test_build_route_equivalence_manifest_from_registry(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "corpus" / "eldyrwild-markdown" / "Longmont Campaign" / "Campaign 1"
    campaign_dir.mkdir(parents=True)
    registry_path = campaign_dir / "_npc_registry.json"
    registry_path.write_text(
        """[
  {
    "slug": "lysandra",
    "display_name": "Lysandra",
    "aliases": ["Captain Lysandra Ironveil"],
    "status": "tracked",
    "first_session": 1,
    "last_session": 13,
    "hub_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/Captain Lysandra Ironveil/README.md",
    "setting_hub_path": "corpus/eldyrwild-markdown/Elderwyld/NPCs/Lysandra Ironveil/README.md",
    "notes": ""
  }
]""",
        encoding="utf-8",
    )

    records = build_route_equivalence_manifest(registry_path)

    assert len(records) == 1
    record = records[0]
    assert record.record_id == "route-eq:longmont-c1:npc:lysandra"
    assert record.entity_kind == "npc"
    assert record.from_route_id == "route:longmont-c1:npc:captain-lysandra-ironveil"
    assert record.to_route_id == "route:elderwyld:npc:lysandra-ironveil"


def test_infers_non_npc_kind_from_hub_path_segments(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "corpus" / "eldyrwild-markdown" / "Longmont Campaign" / "Campaign 1"
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
    "hub_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/Wolf Manor/README.md",
    "setting_hub_path": "corpus/eldyrwild-markdown/Elderwyld/Locations/Wolf Manor/README.md",
    "notes": ""
  }
]""",
        encoding="utf-8",
    )

    records = build_route_equivalence_manifest(registry_path)

    assert len(records) == 1
    assert records[0].entity_kind == "location"
    assert records[0].record_id == "route-eq:longmont-c1:location:wolf-manor"
    assert records[0].from_route_id == "route:longmont-c1:location:wolf-manor"


def test_build_route_equivalence_manifest_requires_campaign_path(tmp_path: Path) -> None:
    registry_path = tmp_path / "_npc_registry.json"
    registry_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="unable to infer campaign id"):
        build_route_equivalence_manifest(registry_path)
