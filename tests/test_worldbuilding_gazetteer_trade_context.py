from __future__ import annotations

from copy import deepcopy

from src.graph_memory.extraction.worldbuilding_gazetteer_trade_context import (
    GAZETTEER_TRADE_CONTEXT_PROFILE,
    PROFILE,
    _apply_trade_context,
    compile_gazetteer_trade_context,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import (
    PUBLISHABLE_WORLDBUILDING_PROFILES,
)


ARTIFACT = "artifact:worldbuilding:synthetic-city:r1:abc123"
SOURCE_REF = f"{ARTIFACT}:text"
TRADE_SENTENCE = (
    "A trading hub with access to moonlit ferries, sky barges, and clockwork rail."
)


def _rows(*groups: tuple[int, int, str]) -> list[dict[str, object]]:
    return [
        {
            "source_span_ref_id": f"{ARTIFACT}:span:{start}-{end}",
            "line_start": start,
            "line_end": end,
            "text": text,
        }
        for start, end, text in groups
    ]


def _existing_evidence() -> dict[str, object]:
    span = f"{ARTIFACT}:span:6-6"
    return {
        "source_span_ref_id": span,
        "anchor_quotes": ["Asterport is a city."],
        "source_artifact_id": ARTIFACT,
        "source_ref_id": SOURCE_REF,
        "source_anchor_id": f"anchor:{span}",
        "label": span,
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
    }


def _candidate() -> dict[str, object]:
    return {
        "nodes": [
            {
                "node_id": "loc_asterport",
                "label": "Asterport",
                "node_type": "location",
                "description": "A city beside a deep-blue lake.",
                "evidence_refs": [_existing_evidence()],
            },
        ],
        "edges": [],
    }


def _rows_with_trade(
    *, sentence: str = TRADE_SENTENCE, heading: str = "### Economy and Trade:",
) -> list[dict[str, object]]:
    return _rows(
        (1, 3, '---\ntitle: "The City of Asterport"\n---'),
        (4, 5, f"{heading}\nMajor industries include brewing and fishing. {sentence}"),
    )


def test_trade_profile_adds_exact_trade_access_and_openable_evidence_once():
    rows = _rows_with_trade()
    original = _candidate()

    result, diagnostics = _apply_trade_context(original, rows)

    assert original == _candidate()
    location = result["nodes"][0]
    assert location["description"] == (
        "A city beside a deep-blue lake.\n\n"
        "Trade access: moonlit ferries, sky barges, and clockwork rail."
    )
    evidence = next(
        ref for ref in location["evidence_refs"]
        if ref["source_span_ref_id"] == f"{ARTIFACT}:span:4-5"
    )
    assert evidence["anchor_quotes"] == [TRADE_SENTENCE]
    assert evidence["source_artifact_id"] == ARTIFACT
    assert evidence["source_ref_id"] == SOURCE_REF
    assert evidence["can_open_source"] is True
    assert result["edges"] == []
    assert diagnostics["status"] == "added"
    assert diagnostics["evidence_status"] == "attached"

    repeated, repeated_diagnostics = _apply_trade_context(result, rows)
    assert repeated == result
    assert repeated_diagnostics["status"] == "already_present"


def test_trade_detail_must_be_in_one_unique_economy_section():
    rows = _rows_with_trade(heading="### History:")
    result, diagnostics = _apply_trade_context(_candidate(), rows)
    assert result == _candidate()
    assert diagnostics["reason"] == "trade_section_not_unique"

    rows = _rows(
        (1, 3, '---\ntitle: "The City of Asterport"\n---'),
        (4, 5, "### Economy and Trade:\nMajor industries include brewing and fishing."),
        (6, 7, f"### Economy and Trade:\n{TRADE_SENTENCE}"),
    )
    result, diagnostics = _apply_trade_context(_candidate(), rows)
    assert result == _candidate()
    assert diagnostics["section_count"] == 2


def test_trade_detail_and_location_must_each_be_unambiguous():
    rows = _rows_with_trade(sentence=f"{TRADE_SENTENCE} {TRADE_SENTENCE}")
    result, diagnostics = _apply_trade_context(_candidate(), rows)
    assert result == _candidate()
    assert diagnostics["reason"] == "trade_access_claim_not_unique"

    graph = _candidate()
    graph["nodes"].append(deepcopy(graph["nodes"][0]))
    result, diagnostics = _apply_trade_context(graph, _rows_with_trade())
    assert result["nodes"][0]["description"] == graph["nodes"][0]["description"]
    assert diagnostics["reason"] == "city_location_not_unique"


def test_negated_or_qualified_access_is_not_added_as_affirmative():
    for sentence in (
        "A trading hub with no access to canal boats.",
        "A trading hub with limited access to canal boats.",
        "A trading hub without access to canal boats.",
        "A trading hub could gain access to canal boats.",
    ):
        result, diagnostics = _apply_trade_context(
            _candidate(), _rows_with_trade(sentence=sentence),
        )
        assert result == _candidate()
        assert diagnostics["reason"] == "trade_access_claim_not_affirmative"

    # A separate earlier sentence must not poison an affirmative trade claim.
    sentence = (
        "It has no trade with rivals. Asterport is a trading hub with access "
        "to moonlit ferries."
    )
    result, diagnostics = _apply_trade_context(
        _candidate(), _rows_with_trade(sentence=sentence),
    )
    assert diagnostics["status"] == "added"
    assert "Trade access: moonlit ferries." in result["nodes"][0]["description"]


def test_explicit_trade_city_must_match_the_document_city():
    other_city = "Otherport is a trading hub with access to moonlit ferries."
    result, diagnostics = _apply_trade_context(
        _candidate(), _rows_with_trade(sentence=other_city),
    )
    assert result == _candidate()
    assert diagnostics["reason"] == "trade_city_subject_mismatch"

    town_of_other_city = (
        "The town of Otherport is a trading hub with access to moonlit ferries."
    )
    result, diagnostics = _apply_trade_context(
        _candidate(), _rows_with_trade(sentence=town_of_other_city),
    )
    assert result == _candidate()
    assert diagnostics["reason"] == "trade_city_subject_mismatch"

    named_city_with_dash = "Otherport — a trading hub with access to moonlit ferries."
    result, diagnostics = _apply_trade_context(
        _candidate(), _rows_with_trade(sentence=named_city_with_dash),
    )
    assert result == _candidate()
    assert diagnostics["reason"] == "trade_city_subject_mismatch"

    same_city = "Asterport is a trading hub with access to moonlit ferries."
    result, diagnostics = _apply_trade_context(
        _candidate(), _rows_with_trade(sentence=same_city),
    )
    assert diagnostics["status"] == "added"
    assert "Trade access: moonlit ferries." in result["nodes"][0]["description"]

    generic_subject = "A trading hub has access to moonlit ferries."
    result, diagnostics = _apply_trade_context(
        _candidate(), _rows_with_trade(sentence=generic_subject),
    )
    assert diagnostics["status"] == "added"

    other_city_location = (
        "Near Otherport, a trading hub with access to moonlit ferries."
    )
    result, diagnostics = _apply_trade_context(
        _candidate(), _rows_with_trade(sentence=other_city_location),
    )
    assert result == _candidate()
    assert diagnostics["reason"] == "trade_city_subject_mismatch"


def test_trade_evidence_must_belong_to_the_existing_location_source():
    rows = _rows(
        (1, 3, '---\ntitle: "The City of Asterport"\n---'),
        (4, 5, f"### Economy and Trade:\n{TRADE_SENTENCE}"),
    )
    rows[1]["source_span_ref_id"] = "artifact:worldbuilding:other-source:span:4-5"
    result, diagnostics = _apply_trade_context(_candidate(), rows)
    assert result == _candidate()
    assert diagnostics["reason"] == "trade_source_binding_unverified"

    graph = _candidate()
    other = deepcopy(_existing_evidence())
    other["source_artifact_id"] = "artifact:worldbuilding:other-source:r1"
    other["source_ref_id"] = "artifact:worldbuilding:other-source:r1:text"
    graph["nodes"][0]["evidence_refs"].append(other)
    result, diagnostics = _apply_trade_context(graph, _rows_with_trade())
    assert result == graph
    assert diagnostics["reason"] == "trade_source_binding_unverified"

    graph = _candidate()
    graph["nodes"][0]["evidence_refs"][0]["can_open_source"] = False
    result, diagnostics = _apply_trade_context(graph, _rows_with_trade())
    assert result["nodes"][0]["description"] == graph["nodes"][0]["description"]
    assert diagnostics["reason"] == "trade_source_binding_unverified"


def test_profile_is_catalogued_as_an_immutable_extension():
    assert PROFILE == "worldbuilding_gazetteer_v1@1.10"
    assert GAZETTEER_TRADE_CONTEXT_PROFILE.profile_id == "worldbuilding_gazetteer_v1"
    assert GAZETTEER_TRADE_CONTEXT_PROFILE.profile_version == "1.10"
    assert PROFILE in PUBLISHABLE_WORLDBUILDING_PROFILES


def test_profile_composes_governance_and_trade_without_new_entities_or_edges():
    governance_sentence = (
        "A synthetic city-state governed by a council selected by ballots."
    )
    rows = _rows(
        (1, 3, '---\ntitle: "The City of Asterport"\n---'),
        (4, 5, f"### Governance:\n{governance_sentence}"),
        (6, 7, f"### Economy and Trade:\n{TRADE_SENTENCE}"),
    )
    governance_ref = {
        **_existing_evidence(),
        "source_span_ref_id": rows[1]["source_span_ref_id"],
        "source_anchor_id": f"anchor:{rows[1]['source_span_ref_id']}",
        "label": rows[1]["source_span_ref_id"],
        "anchor_quotes": [governance_sentence],
    }
    semantic_state = {
        "authority_state": "system_derived",
        "canon_state": "worldbuilding_draft",
        "evidence_role": "source_evidence",
        "lifecycle_state": "candidate",
        "visibility_state": "gm_private",
    }
    graph = {
        "nodes": [
            {
                "node_id": "loc_asterport",
                "label": "Asterport",
                "node_type": "location",
                "description": "A city beside a deep-blue lake.",
                "semantic_state": deepcopy(semantic_state),
                "evidence_refs": [deepcopy(governance_ref)],
            },
            {
                "node_id": "org_asterport_council",
                "label": "Asterport Council",
                "node_type": "organization",
                "description": "A city council.",
                "semantic_state": deepcopy(semantic_state),
                "evidence_refs": [deepcopy(governance_ref)],
            },
        ],
        "edges": [],
    }

    result, diagnostics = compile_gazetteer_trade_context(graph, rows)

    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["relationship_type"] == "governs"
    assert edge["from_node_id"] == "org_asterport_council"
    assert edge["to_node_id"] == "loc_asterport"
    location = next(node for node in result["nodes"] if node["node_id"] == "loc_asterport")
    assert "Trade access: moonlit ferries, sky barges, and clockwork rail." in location["description"]
    assert diagnostics["source_grounded_governance"]["status"] == "added"
    assert diagnostics["source_grounded_trade_context"]["status"] == "added"

    repeated, repeated_diagnostics = compile_gazetteer_trade_context(result, rows)
    assert repeated == result
    assert repeated_diagnostics["source_grounded_governance"]["status"] == "already_present"
    assert repeated_diagnostics["source_grounded_trade_context"]["status"] == "already_present"
