from dataclasses import replace
from types import SimpleNamespace

import pytest
from dungeonmind.application.vnext import (
    ParsedAssertion, ParsedAssertionMetadata, ParsedEntityRefValue,
    ParsedLiteralValue, ParsedPublicVisibility, ParsedTermRefValue,
    ParsedTimelessTemporalScope, ParsedUnknownTemporalScope,
)

from apps.live_control_server.services import guest_release_assertions as selections


def test_explicit_fields_require_admitted_assertions_and_their_own_evidence(monkeypatch):
    metadata = ParsedAssertionMetadata(scope=(), visibility=ParsedPublicVisibility(),
        epistemic_basis="asserted", claim_mode="dungeonbuddy.claim:fact", standing="established",
        evidence_ref_ids=("evidence",), temporal_scope=ParsedTimelessTemporalScope(), domain_metadata=())
    name = ParsedAssertion("name", "entity", "dnd5e:name", ParsedLiteralValue("Sizzek", '"Sizzek"'), metadata)
    kind = ParsedAssertion("kind", "entity", "dnd5e:classification", ParsedTermRefValue("dnd5e:character"), metadata)
    link = ParsedAssertion("link", "entity", "dnd5e:knows", ParsedEntityRefValue("other"), metadata)
    assertions = {a.assertion_id: a for a in (name, kind, link)}
    context = SimpleNamespace(parsed=SimpleNamespace(get_assertion=assertions.get))
    monkeypatch.setattr(selections, "verify_source_citation", lambda **kwargs: kwargs["excerpt"]["id"])
    common = dict(context=context, admitted_ids=set(assertions), access=object(), native_world_id="world", revision_id="rev")
    citation = ("evidence", {"id": "excerpt"}, ())
    node, binding = selections.select_node(**common, entity_id="entity", name_assertion_id="name",
        kind_assertion_id="kind", name_evidence=citation, kind_evidence=citation)
    assert node["label"] == "Sizzek" and node["name_citations"] == ["excerpt"]
    assert binding[1:] == ("entity", "name", "evidence", "excerpt", "kind", "evidence", "excerpt")
    with pytest.raises(selections.GuestReleaseAssertionError, match="does not support"):
        selections.select_node(**common, entity_id="entity", name_assertion_id="name",
            kind_assertion_id="kind", name_evidence=("other", {}, ()), kind_evidence=citation)
    with pytest.raises(selections.GuestReleaseAssertionError, match="endpoints"):
        selections.select_relationship(**common, assertion_id="link", subject_id="entity", predicate="dnd5e:knows",
            node_ids={"entity": node["id"]}, evidence=citation)
    assertions["name"] = replace(name, metadata=replace(metadata, temporal_scope=ParsedUnknownTemporalScope()))
    unknown, _ = selections.select_node(**common, entity_id="entity", name_assertion_id="name",
        kind_assertion_id="kind", name_evidence=citation, kind_evidence=citation)
    assert unknown["name_temporal"] == "unknown" and unknown["kind_temporal"] == "timeless"
    assertions["name"] = replace(name, metadata=replace(metadata, epistemic_basis="inferred"))
    inferred, _ = selections.select_node(**common, entity_id="entity", name_assertion_id="name",
        kind_assertion_id="kind", name_evidence=citation, kind_evidence=citation)
    assert inferred["name_basis"] == "inferred" and inferred["kind_basis"] == "asserted"
    assertions["name"] = replace(name, metadata=replace(metadata, claim_mode="dungeonbuddy.claim:speculation"))
    with pytest.raises(selections.GuestReleaseAssertionError, match="semantics"):
        selections.select_node(**common, entity_id="entity", name_assertion_id="name",
            kind_assertion_id="kind", name_evidence=citation, kind_evidence=citation)


@pytest.mark.parametrize("term,expected", [
    ("dnd5e:located_in", "dnd5e · located in"), ("dungeonbuddy:item", "buddy · item"),
    ("dungeonbuddy.custom:knows", "custom · knows"),
    ("dungeonbuddy.custom:works-for", "custom · works-for"),
    ("dungeonbuddy.custom:2.part_name", "custom · 2 · part name"),
])
def test_display_terms_preserve_known_namespace(term, expected):
    assert selections._term_label(term) == expected


@pytest.mark.parametrize("term", ["https://private.example", "other:knows", "dnd5e:../secret", "dnd5e:"])
def test_display_terms_reject_unknown_or_destination_syntax(term):
    with pytest.raises(selections.GuestReleaseAssertionError):
        selections._term_label(term)


def test_display_terms_do_not_collapse_namespace_or_local_separators():
    terms = ["dnd5e:bond", "dungeonbuddy:bond", "dungeonbuddy.custom:bond",
             "dungeonbuddy.custom:a_b", "dungeonbuddy.custom:a.b", "dungeonbuddy.custom:a-b",
             "dnd5e:custom.knows", "dungeonbuddy.custom:knows", "dnd5e:buddy.item", "dungeonbuddy:item"]
    assert len({selections._term_label(term) for term in terms}) == len(terms)
