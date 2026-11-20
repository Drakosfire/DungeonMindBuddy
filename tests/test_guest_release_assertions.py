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
    assertions["name"] = replace(name, metadata=replace(metadata, claim_mode="dungeonbuddy.claim:speculation"))
    with pytest.raises(selections.GuestReleaseAssertionError, match="semantics"):
        selections.select_node(**common, entity_id="entity", name_assertion_id="name",
            kind_assertion_id="kind", name_evidence=citation, kind_evidence=citation)
