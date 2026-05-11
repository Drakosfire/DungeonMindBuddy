from src.lexicon_phase_b.schemas import RouteEquivalenceRecord


def test_route_equivalence_contract_defaults() -> None:
    record = RouteEquivalenceRecord(
        record_id="route-eq:longmont-c1:npc:lysandra",
        campaign_id="longmont-c1",
        entity_kind="npc",
        display_name="Lysandra",
        from_route_id="route:longmont-c1:npc:lysandra",
        to_route_id="route:elderwyld:npc:lysandra",
        producer_registry_path="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json",
        producer_registry_sha256="a" * 64,
        route_equivalence_manifest_hash="b" * 64,
    )
    assert record.schema_version == "0.3.0"
    assert record.producer_registry_path
    assert len(record.producer_registry_sha256) == 64
    assert len(record.route_equivalence_manifest_hash) == 64
    assert record.edge_kind == "setting_fallback"
    # source_type refers to registry file contract (`_npc_registry.json`),
    # not an assertion that resolved entity_kind must be npc.
    assert record.source_type == "npc_registry"
    assert record.authority_effect == "routing_only"
