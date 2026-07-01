from __future__ import annotations

import json

import pytest

from src.graph_memory.vocabulary import (
    AliasCandidate,
    ContextPacketBudgetPolicy,
    ContextVocabularyPacket,
    ContainmentHint,
    DoNotMergeDecision,
    VocabularyEntry,
    context_packet_to_artifact_payload,
    render_context_vocabulary_packet,
)


def _entry(
    vocab_id: str,
    canonical_label: str,
    entity_kind: str,
    *,
    scope: str = "campaign",
    aliases: list[str] | None = None,
    candidate_aliases: list[str] | None = None,
    negative_aliases: list[str] | None = None,
) -> VocabularyEntry:
    return VocabularyEntry(
        vocab_id=vocab_id,
        canonical_label=canonical_label,
        entity_kind=entity_kind,  # type: ignore[arg-type]
        scope=scope,
        campaign_id="campaign:mireward" if scope == "campaign" else None,
        world_id="world:mirathorn" if scope == "world" else None,
        aliases=aliases or [],
        candidate_aliases=candidate_aliases or [],
        negative_aliases=negative_aliases or [],
    )


def test_renders_packet_from_world_and_campaign_entries_and_round_trips():
    world = _entry("vocab:world:mireward", "Mireward", "place", scope="world")
    campaign = _entry("vocab:campaign:lysandra", "Captain Lysandra", "actor")

    result = render_context_vocabulary_packet(world_entries=[world], campaign_entries=[campaign])
    packet = result.packet

    assert isinstance(packet, ContextVocabularyPacket)
    assert packet.world_entry_refs == ["vocab:world:mireward"]
    assert packet.campaign_entry_refs == ["vocab:campaign:lysandra"]
    assert "Mireward" in packet.known_names
    assert "Captain Lysandra" in packet.known_names
    assert packet.type_hints == {"Mireward": "place", "Captain Lysandra": "actor"}
    assert ContextVocabularyPacket.from_dict(packet.to_dict()) == packet


def test_includes_combat_encounter_hints():
    encounter = _entry("vocab:campaign:north-gate-defense", "North Gate Defense", "combat_encounter")

    packet = render_context_vocabulary_packet(campaign_entries=[encounter]).packet

    assert packet.combat_encounter_hints == ["North Gate Defense"]
    assert packet.type_hints["North Gate Defense"] == "combat_encounter"


def test_deterministic_packet_ids_and_payloads_for_different_entry_order():
    mireward = _entry("vocab:world:mireward", "Mireward", "place", scope="world")
    council = _entry("vocab:campaign:council", "Mireward Council", "collective")
    encounter = _entry("vocab:campaign:north-gate-defense", "North Gate Defense", "combat_encounter")

    first = render_context_vocabulary_packet(world_entries=[mireward], campaign_entries=[encounter, council])
    second = render_context_vocabulary_packet(world_entries=[mireward], campaign_entries=[council, encounter])

    assert first.packet.packet_id == second.packet.packet_id
    assert first.packet.to_dict() == second.packet.to_dict()


def test_known_names_are_canonical_only_and_aliases_are_grouped():
    entry = _entry(
        "vocab:campaign:lysandra",
        "Captain Lysandra",
        "actor",
        aliases=["Lysandra Ironveil", "Captain Ironveil"],
        candidate_aliases=["The Captain"],
        negative_aliases=["Some Wrong Name"],
    )

    result = render_context_vocabulary_packet(
        campaign_entries=[entry],
        predicate_hints={"Captain Lysandra": ["leads"], "The Captain": ["ignored"]},
    )
    packet = result.packet

    assert packet.known_names == ["Captain Lysandra"]
    assert "Lysandra Ironveil" not in packet.known_names
    assert "The Captain" not in packet.known_names
    assert packet.entry_aliases == {"Captain Lysandra": ["Lysandra Ironveil", "Captain Ironveil"]}
    assert packet.candidate_entry_aliases == {"Captain Lysandra": ["The Captain"]}
    assert "Some Wrong Name" not in packet.known_names
    assert "Some Wrong Name" not in packet.entry_aliases.get("Captain Lysandra", [])
    assert "Some Wrong Name" not in packet.candidate_entry_aliases.get("Captain Lysandra", [])
    assert packet.entry_labels == {"vocab:campaign:lysandra": "Captain Lysandra"}
    assert packet.entry_kinds == {"vocab:campaign:lysandra": "actor"}
    assert packet.predicate_hints == {"Captain Lysandra": ["leads"]}
    assert result.diagnostics["entry_alias_count"] == 2
    assert result.diagnostics["candidate_entry_alias_count"] == 1


def test_budget_trims_known_names_and_reports_trimmed_counts():
    entries = [
        _entry(f"vocab:campaign:name-{index}", f"Name {index}", "actor")
        for index in range(3)
    ]

    result = render_context_vocabulary_packet(
        campaign_entries=entries,
        budget_policy=ContextPacketBudgetPolicy(max_known_names=2),
    )

    assert len(result.packet.known_names) == 2
    assert result.diagnostics["trimmed_counts"]["known_names"] > 0


def test_supplied_hints_are_included_but_not_inferred():
    entry = _entry("vocab:campaign:guard", "Mireward Guard", "collective", aliases=["The Guard"])
    candidate_alias = AliasCandidate(
        alias_candidate_id="alias:candidate:guard",
        left_surface="Mireward Guard",
        right_surface="The Guard",
        left_vocab_id="vocab:campaign:guard",
    )
    do_not_merge = DoNotMergeDecision(
        decision_id="dnm:guard-gate",
        left_vocab_id="vocab:campaign:guard",
        right_vocab_id="vocab:campaign:north-gate-defense",
    )
    containment = ContainmentHint(
        hint_id="contain:guard-mireward",
        child_label="Mireward Guard",
        parent_label="Mireward",
    )

    packet = render_context_vocabulary_packet(
        campaign_entries=[entry],
        candidate_alias_hints=[candidate_alias],
        do_not_merge_hints=[do_not_merge],
        containment_hints=[containment],
    ).packet

    assert packet.alias_hints == []
    assert packet.candidate_alias_hints == [candidate_alias]
    assert packet.do_not_merge_hints == [do_not_merge]
    assert packet.containment_hints == [containment]


def test_predicate_hints_are_scoped_and_deduped():
    encounter = _entry("vocab:campaign:north-gate-defense", "North Gate Defense", "combat_encounter")

    packet = render_context_vocabulary_packet(
        campaign_entries=[encounter],
        predicate_hints={
            "North Gate Defense": ["occurred_at", "occurred_at", "involved"],
            "Out Of Packet": ["ignored"],
        },
    ).packet

    assert packet.predicate_hints == {"North Gate Defense": ["occurred_at", "involved"]}


def test_diagnostics_are_json_serializable_and_quote_free():
    entry = _entry("vocab:campaign:mireward-council", "Mireward Council", "collective")

    diagnostics = render_context_vocabulary_packet(campaign_entries=[entry]).diagnostics
    diagnostics_json = json.dumps(diagnostics, sort_keys=True)

    assert diagnostics["known_name_count"] == 1
    assert diagnostics["render_method"] == "deterministic_context_vocabulary_packet_render_v1"
    assert "quote" not in diagnostics_json


def test_invalid_budget_fails_clearly():
    with pytest.raises(ValueError, match="max_known_names"):
        ContextPacketBudgetPolicy(max_known_names=-1).validate()

    with pytest.raises(ValueError, match="max_known_names"):
        ContextPacketBudgetPolicy(max_known_names=1.2).validate()  # type: ignore[arg-type]


def test_old_style_packet_payload_loads_with_alias_group_defaults():
    packet = ContextVocabularyPacket.from_dict(
        {
            "packet_id": "packet:vocab:old-style",
            "scope": "campaign",
            "known_names": ["Captain Lysandra"],
            "type_hints": {"Captain Lysandra": "actor"},
        }
    )

    assert packet.entry_aliases == {}
    assert packet.candidate_entry_aliases == {}
    assert packet.entry_labels == {}
    assert packet.entry_kinds == {}


def test_packet_payload_helper_round_trips():
    entry = _entry("vocab:campaign:mireward-council", "Mireward Council", "collective")
    packet = render_context_vocabulary_packet(campaign_entries=[entry]).packet

    payload = context_packet_to_artifact_payload(packet)
    restored = ContextVocabularyPacket.from_dict(payload)

    assert restored == packet
