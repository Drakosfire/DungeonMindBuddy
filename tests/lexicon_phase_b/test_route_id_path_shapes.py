from src.lexicon_phase_b.route_equivalence_manifest import _path_to_route_id


def test_path_to_route_id_file_shape_uses_entity_folder_slug() -> None:
    route_id, kind = _path_to_route_id(
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/Captain Lysandra Ironveil/README.md",
        "longmont-c1",
    )
    assert kind == "npc"
    assert route_id == "route:longmont-c1:npc:captain-lysandra-ironveil"


def test_path_to_route_id_directory_shape_uses_entity_folder_slug() -> None:
    route_id, kind = _path_to_route_id(
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/Wolf Manor/",
        "longmont-c1",
    )
    assert kind == "location"
    assert route_id == "route:longmont-c1:location:wolf-manor"
