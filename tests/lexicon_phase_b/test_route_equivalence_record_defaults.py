from src.lexicon_phase_b.schemas import RouteEquivalenceRecord


def test_route_equivalence_contract_defaults() -> None:
    record = RouteEquivalenceRecord(
        record_id="route-eq:longmont-c1:npc:lysandra",
        campaign_id="longmont-c1",
        entity_kind="npc",
        display_name="Lysandra",
        from_route_id="route:longmont-c1:npc:lysandra",
        to_route_id="route:elderwyld:npc:lysandra",
    )
    assert record.schema_version == "0.2.0"
    assert record.edge_kind == "setting_fallback"
    # source_type refers to registry file contract (`_npc_registry.json`),
    # not an assertion that resolved entity_kind must be npc.
    assert record.source_type == "npc_registry"
    assert record.authority_effect == "routing_only"
