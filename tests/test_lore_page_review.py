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


def test_lore_save_body_excludes_conversation_limitations():
    from types import SimpleNamespace

    from application_state.agent_conversation.lore_page_confirmation import _body

    completion = SimpleNamespace(
        native_body_citations=[SimpleNamespace(segment_index=1)],
        answer_segments=[
            SimpleNamespace(kind="limitation", text="Some details were unavailable."),
            SimpleNamespace(kind="source_passage_claim", text="Rowan was named."),
            SimpleNamespace(kind="proposal", text="Possible connection."),
        ],
    )
    body = _body(SimpleNamespace(world_id="test", turn_id="turn", completion=completion))
    assert body.startswith("Rowan was named.\n\n[Source 1]")
    assert body.endswith("**Proposed**\n\nPossible connection.")
    assert "unavailable" not in body


@pytest.mark.parametrize("scenario", ["matching", "topic_switch", "other_page", "inactive", "superseded", "qualified_request"])
def test_save_followup_resolves_only_a_current_same_work_review(monkeypatch, scenario):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from uuid import uuid4

    from application_state.agent_conversation import lore_page_confirmation as owner
    from application_state.agent_conversation.lore_page_review import ProposedLorePage
    from application_state.agent_conversation.native_completion import SurfaceNativeCompletionV1
    from application_state.agent_conversation.types import Turn
    from application_state.errors import ApplicationStateConflictError

    conversation_id, current_id, prior_id = uuid4(), uuid4(), uuid4()
    scope = SimpleNamespace(
        surface_id="build", surface_instance_id="page",
        primary_work=SimpleNamespace(resolution="resolved", object_id="page"),
    )
    prior_scope = scope if scenario != "other_page" else SimpleNamespace(
        surface_id="build", surface_instance_id="other",
        primary_work=SimpleNamespace(resolution="resolved", object_id="other"),
    )
    review = None if scenario == "topic_switch" else ProposedLorePage(
        kind="lore_page", destination=LorePageTitleWitness(instruction="Create a page for Rowan", title="Rowan"),
    )
    completion = SurfaceNativeCompletionV1.model_construct(collaboration=review)
    message = "Create the page with new details." if scenario == "qualified_request" else "Create the page."
    current = Turn.model_construct(turn_id=current_id, conversation_id=conversation_id, user_text=message,
                                   sequence=3, status="running", provenance=scope)
    prior = Turn.model_construct(turn_id=prior_id, conversation_id=conversation_id,
                                 sequence=1, status="completed", provenance=prior_scope, completion=completion)

    def select_previous(query, params):
        assert "sequence < %s" in query
        assert "status NOT IN ('failed', 'interrupted')" in query
        assert params == ("test", conversation_id, current.sequence)
        return SimpleNamespace(fetchone=lambda: (prior_id,))

    def require_current(conn, turn):
        assert turn is prior
        if scenario == "superseded":
            raise ApplicationStateConflictError("Superseded")
    conn = SimpleNamespace(execute=select_previous)
    active_id = uuid4() if scenario == "inactive" else conversation_id
    monkeypatch.setattr(owner, "unit_of_work", lambda dsn: nullcontext(conn))
    monkeypatch.setattr(owner.repository, "lock_world_state", lambda *args: SimpleNamespace(active_conversation_id=active_id))
    monkeypatch.setattr(owner.repository, "lock_conversation", lambda *args: object())
    monkeypatch.setattr(owner.repository, "get_turn", lambda conn, world, key: {current_id: current, prior_id: prior}[key])
    monkeypatch.setattr(owner, "_require_current_review", require_current)

    reference = owner.resolve_lore_save_followup(
        "fixture", world_id="test", conversation_id=conversation_id, current_turn_id=current_id,
    )
    if scenario == "matching":
        assert reference.turn_id == prior_id
        assert reference.review_sha256 == owner.canonical_sha256(completion)
        assert reference.title == "Rowan"
    else:
        assert reference is None
