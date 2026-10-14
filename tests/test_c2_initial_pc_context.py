"""Historical C2 context reaches extraction without importing future companions."""
from pathlib import Path

from src.graph_memory.party_context import build_party_context_for_campaign
from src.graph_memory.extraction.known_entity_registry import build_known_entity_registry
from src.graph_memory.extraction.known_entity_mention_matcher import match_known_entities_in_spans

CORPUS = Path(__file__).resolve().parents[1] / "corpus/eldyrwild-markdown"
REL = "Longmont Campaign/Campaign 2"


def test_initial_c2_identity_context_reaches_source_mentions():
    party = build_party_context_for_campaign("longmont-c2", 2, corpus_root=CORPUS)
    registry = build_known_entity_registry("longmont-c2", 2, corpus_root=CORPUS, party_ctx=party)
    recap = (CORPUS / REL / "Session Recaps/Session 2 - Recap.md").read_text()
    sidecar = match_known_entities_in_spans(
        [{"source_span_ref_id": "fixture:c2s2", "text": recap}], registry, session_id="session-2"
    )
    assert len(party.pcs()) == 6
    assert not party.companions()
    assert {m.entity_slug for m in sidecar.mentions} == {
        "baergrom", "bonogo", "caelynn", "ephanna", "karsemine", "stafl"
    }
    assert all(m.entity_kind == "pc" for m in sidecar.mentions)
    assert registry.by_slug()["karsemine"].corpus_ref["type"] == "pc"
    assert "ogonob" not in registry.by_slug()
    assert party.warnings == ("roster_carry_forward: session_pc_rosters['2'] using '1'",)


def test_initial_c2_context_does_not_backdate_later_companions():
    before = build_party_context_for_campaign("longmont-c2", 0, corpus_root=CORPUS)
    assert not before.members
    early = build_party_context_for_campaign("longmont-c2", 16, corpus_root=CORPUS)
    assert len(early.pcs()) == 6
    assert not early.companions()
    later = build_party_context_for_campaign("longmont-c2", 22, corpus_root=CORPUS)
    assert {m.slug for m in later.companions()} == {"thrin_branchborn", "captain_lysandra_ironveil"}
