import pytest

from application_state.agent_conversation.lore_page_review import LorePageTitleWitness, explicit_lore_page_witness


def test_title_is_bound_to_the_selected_instruction():
    witness = LorePageTitleWitness(instruction="Create a blank page for Rowan.", title="Rowan")
    assert witness.bind(
        "Rowan came up in the discussion. Create a blank page for Rowan. Leave it empty."
    ) == "Rowan"


@pytest.mark.parametrize(
    "instruction,title,author_text",
    [
        ("Create a blank page for Willow.", "Willow", "Create a blank page for Rowan."),
        ("Create a blank page for Rowan.", "Willow", "Create a blank page for Rowan."),
        ("Create a page for Rowan.", "Row", "Create a page for Rowan."),
        ("Create a page for Rowan.", "Rowan", "Create a page for Rowan. Create a page for Rowan."),
        ("Use either Rowan or Rowan.", "Rowan", "Use either Rowan or Rowan."),
    ],
)
def test_unproven_title_witness_is_rejected(instruction, title, author_text):
    with pytest.raises(ValueError):
        LorePageTitleWitness(instruction=instruction, title=title).bind(author_text)


def test_native_review_schema_and_admission_use_the_author_witness():
    from application_state.agent_conversation.build_intentional_response import (
        Capabilities,
        native_review_schema,
        normalize_native_review,
        resolve,
    )

    capabilities = Capabilities(("answer_from_sources",), ("lore_page",), None, None)
    frame = {
        "response_contract": resolve("review_lore_page", capabilities),
        "artifact_under_edit": {"sections": []},
        "source_basis": {},
    }
    candidate = {
        "kind": "lore_page",
        "destination": {"instruction": "Open a blank page for Rowan.", "title": "Rowan"},
    }
    schema, definitions = native_review_schema(frame)
    assert "LorePageTitleWitness" in definitions
    assert "destination" in schema["anyOf"][0]["required"]
    review = normalize_native_review(
        candidate, [], frame, author_text="Open a blank page for Rowan."
    )
    assert review.destination.title == "Rowan"
    with pytest.raises(ValueError, match="author turn"):
        normalize_native_review(candidate, [], frame, author_text="Open a blank page for Willow.")
    frame["response_contract"] = resolve("discuss", capabilities)
    with pytest.raises(ValueError, match="resolved supported work"):
        normalize_native_review(candidate, [], frame, author_text="Open a blank page for Rowan.")


def test_title_witness_cannot_promote_an_unrelated_subject_from_the_same_turn():
    text = "Consider the Bath House. Create a blank page for the threat that is Rowan."
    with pytest.raises(ValueError, match="explicit page request"):
        LorePageTitleWitness(instruction="Consider the Bath House.", title="Bath House").bind(text)
    witness = LorePageTitleWitness(
        instruction="Create a blank page for the threat that is Rowan.", title="Rowan",
    )
    assert witness.bind(text) == "Rowan"


def test_two_explicit_page_requests_require_disambiguation():
    text = "Create a page for Rowan. Create a page for Willow."
    with pytest.raises(ValueError, match="one explicit page request"):
        LorePageTitleWitness(instruction="Create a page for Willow.", title="Willow").bind(text)


def test_explicit_blank_request_rejects_a_populated_body():
    author = "Create a blank lore page for Rowan."
    witness = LorePageTitleWitness(instruction=author, title="Rowan")
    with pytest.raises(ValueError, match="Blank lore-page request"):
        witness.bind(author, has_body=True)
    assert witness.bind(author) == "Rowan"


@pytest.mark.parametrize("subject", ["Rowan or Willow", "Rowan and make a page for Willow"])
def test_unquoted_compound_destination_requires_clarification(subject):
    author = f"Create a page for {subject}."
    with pytest.raises(ValueError, match="compound destination"):
        LorePageTitleWitness(instruction=author, title=subject).bind(author)


@pytest.mark.parametrize("quote", ['"', "'"])
def test_quoted_compound_title_is_one_explicit_destination(quote):
    author = f"Please create a blank page called {quote}Rowan and Willow{quote}."
    witness = LorePageTitleWitness(instruction=author, title="Rowan and Willow")
    assert witness.bind(author) == "Rowan and Willow"


def test_two_coordinated_quoted_titles_are_not_one_destination():
    author = 'Create a page for "Rowan" and make a page for "Willow".'
    with pytest.raises(ValueError, match="compound destination"):
        LorePageTitleWitness(instruction=author, title="Rowan").bind(author)


def test_derives_title_before_writing_from_an_explicit_pivot():
    author = "Discuss the observatory. Create a blank page for the threat that is Rowan. Leave it empty."
    witness = explicit_lore_page_witness(author)
    assert witness.title == "Rowan"
    assert witness.instruction == "Create a blank page for the threat that is Rowan"
    assert witness.bind(author) == "Rowan"


@pytest.mark.parametrize("blank", [False, True])
def test_writer_schema_offers_only_the_author_bound_title(blank):
    from types import SimpleNamespace

    from application_state.agent_conversation.build_intentional_response import Capabilities, resolve
    from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA
    from application_state.agent_conversation.native_build_work_view import semantic_frame
    from application_state.agent_conversation.native_writer import SCHEMA
    from application_state.agent_conversation.plan_writer_output_schema import ASSERTION_POLICY, native_output_format
    from application_state.agent_conversation.rules_authority_plan_packet import PlanRulesEvidenceFrameV1

    modifier = "blank " if blank else ""
    message = f"Discuss the observatory. Create a {modifier}page for the threat that is Rowan."
    execution = SimpleNamespace(policy=SimpleNamespace(action=SimpleNamespace(intent=SimpleNamespace(message=message))), events=())
    capabilities = Capabilities(("answer_from_sources",), ("lore_page",), None, None)
    host = {
        "schema": NATIVE_WORK_SCHEMA,
        "response_contract": resolve("review_lore_page", capabilities),
        "artifact_under_edit": {"sections": []},
        "source_basis": {"visibility": "gm"},
    }
    evidence = {
        "schema": SCHEMA, "answer_policy": ASSERTION_POLICY,
        "native_statements": {"statements": []},
        "native_body_evidence": {"excerpts": [{"excerpt_handle": "s1"}]},
        "native_assertions": None,
    }
    rules = PlanRulesEvidenceFrameV1(
        schema="dmb_plan_rules_evidence_v1", ruleset="synthetic", lookups=(), supports=(),
    )
    projected = semantic_frame(host, execution, bind_lore_page=True)
    assert projected["build_work"]["lore_page_destination"]["title"] == "Rowan"
    schema = native_output_format(evidence, rules, host | projected, build_local=True)["schema"]
    assert schema["$defs"]["LorePageTitleWitness"]["properties"]["title"]["enum"] == ["Rowan"]
    assert schema["properties"]["answer_segments"].get("maxItems") == (0 if blank else None)
    assert "destination" in schema["properties"]["collaboration"]["required"]
    if not blank:
        assert {item["properties"]["kind"]["const"]
                for item in schema["properties"]["answer_segments"]["items"]["anyOf"]} == {
                    "native_body_claim", "proposal",
                }
    historical = native_output_format(evidence, rules, host, build_local=True)["schema"]
    assert "enum" not in historical["$defs"]["LorePageTitleWitness"]["properties"]["title"]
