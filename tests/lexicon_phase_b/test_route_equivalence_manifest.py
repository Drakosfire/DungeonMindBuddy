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
    assert record.from_route_id == "route:longmont-c1:npc:captain-lysandra-ironveil"
    assert record.to_route_id == "route:elderwyld:npc:lysandra-ironveil"
    assert record.authority_effect == "routing_only"
    assert record.source_type == "npc_registry"


def test_build_route_equivalence_manifest_requires_campaign_path(tmp_path: Path) -> None:
    registry_path = tmp_path / "_npc_registry.json"
    registry_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="unable to infer campaign id"):
        build_route_equivalence_manifest(registry_path)
