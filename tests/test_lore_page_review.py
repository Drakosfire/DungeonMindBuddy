import pytest

from application_state.agent_conversation.lore_page_review import LorePageTitleWitness, explicit_lore_page_witness


@pytest.mark.parametrize("article", ["a", "the", ""])
@pytest.mark.parametrize("conversational", [False, True])
def test_named_page_request_binds_with_either_article(article, conversational):
    instruction = f"Create {article + ' ' if article else ''}page about maelthor"
    witness = explicit_lore_page_witness(instruction, conversational=conversational)
    assert witness.title == "maelthor"
    assert witness.instruction == instruction
    assert witness.bind(instruction, has_body=True, conversational=conversational) == "maelthor"
    with pytest.raises(ValueError, match="author turn"):
        witness.bind("Create the page about someone else", conversational=conversational)


def test_definite_article_preserves_blank_and_compound_destination_guards():
    instruction = "Create the blank page about Rowan."
    witness = explicit_lore_page_witness(instruction)
    with pytest.raises(ValueError, match="Blank lore-page request"):
        witness.bind(instruction, has_body=True)
    with pytest.raises(ValueError, match="compound destination"):
        explicit_lore_page_witness("Create the page about Rowan or Willow.")


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
        collaboration=SimpleNamespace(open_questions=()),
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


def test_explicit_create_after_research_binds_only_the_named_page_clause():
    author = 'Consult the travel journal, then create a page titled "The West Road".'
    witness = explicit_lore_page_witness(author)
    assert witness.instruction == 'create a page titled "The West Road"'
    assert witness.bind(author) == "The West Road"

    with pytest.raises(ValueError, match="one explicit page request"):
        explicit_lore_page_witness('Consult the journal, then do not create a page titled "The West Road".')


def test_open_questions_stay_literal_in_saved_markdown():
    from types import SimpleNamespace
    from application_state.agent_conversation.lore_page_confirmation import _body
    from application_state.agent_conversation.lore_page_review import ProposedLorePage

    destination = {"instruction": "Create a page for Rowan", "title": "Rowan"}
    question = "## Is [the report](https://example.test) *certain*?"
    draft = ProposedLorePage(kind="lore_page", destination=destination, open_questions=(question,))
    completion = SimpleNamespace(native_body_citations=[], answer_segments=[], collaboration=draft)
    body = _body(SimpleNamespace(world_id="test", turn_id="turn", completion=completion))
    assert body == r"## Open questions" + "\n\n" + r"- \#\# Is \[the report\]\(https://example\.test\) \*certain\*?"
    with pytest.raises(ValueError, match="Open questions"):
        ProposedLorePage(kind="lore_page", destination=destination,
                         open_questions=("Did Rowan leave?\n# Established fact",))


def test_page_timing_modifier_is_separate_from_the_name():
    assert explicit_lore_page_witness("Create a page for the Blue Lantern now.", conversational=True).title == "Blue Lantern"
    assert explicit_lore_page_witness('Create a page titled "Blue Lantern Now".', conversational=True).title == "Blue Lantern Now"


@pytest.mark.parametrize("preposition", ["called", "named", "titled"])
def test_explicit_name_can_end_in_now(preposition):
    author = f"Create a page {preposition} Blue Lantern Now."
    assert explicit_lore_page_witness(author, conversational=True).title == "Blue Lantern Now"


@pytest.mark.parametrize('instruction,title', [
    ('Create the Maelthor page', 'Maelthor'),
    ('Please make a new Glass Regent page from our conversation.', 'Glass Regent'),
    ('Open the "Blue Lantern Now" page.', 'Blue Lantern Now'),
    ('Create the blank Ashbell page.', 'Ashbell'),
])
def test_title_before_page_is_an_explicit_author_witness(instruction, title):
    witness = explicit_lore_page_witness(instruction, conversational=True)
    assert witness.title == title
    assert witness.bind(instruction, conversational=True) == title
    if 'blank' in instruction:
        with pytest.raises(ValueError, match='Blank lore-page'):
            witness.bind(instruction, has_body=True)


@pytest.mark.parametrize('instruction', [
    'Do not create the Maelthor page.',
    'Could we create the Maelthor page?',
    'Create a new page.',
    'Create the current page.',
    'Create the Maelthor or Dust Walker page.',
    'Create the Maelthor page and another page.',
    'Create the Maelthor page. Create the Ashbell page.',
])
def test_new_title_form_does_not_grant_ambiguous_or_multiple_destinations(instruction):
    with pytest.raises(ValueError):
        explicit_lore_page_witness(instruction, conversational=True)


@pytest.mark.parametrize('clause', ['titled', 'named', 'called', ', titled', 'with the title'])
@pytest.mark.parametrize('title', ['Ashbell', 'Maelthor'])
def test_title_before_page_rejects_an_additional_naming_clause(clause, title):
    with pytest.raises(ValueError, match='multiple naming clauses'):
        explicit_lore_page_witness(f'Create the Maelthor page {clause} "{title}".')


@pytest.mark.parametrize('instruction', [
    'Create the Maelthor page. Create a page titled "Ashbell".',
    'Create a page titled "Ashbell". Create the Maelthor page.',
])
def test_legacy_witness_reopens_under_original_grammar_in_mixed_prose(instruction):
    # These exact old-form witnesses were accepted before the new grammar.
    witness = LorePageTitleWitness(instruction='Create a page titled "Ashbell"', title='Ashbell')
    assert witness.bind(instruction) == 'Ashbell'
    assert explicit_lore_page_witness(instruction).title == 'Ashbell'


@pytest.mark.parametrize("title", ["The Memory Ferry", "A Ferry", "Échos — ‘Mémoire’", "Bridge: Three? Yes!"])
def test_current_request_reference_preserves_proposed_title_without_instruction_echo(title):
    from application_state.agent_conversation.build_intentional_response import Capabilities, resolve, normalize_native_review, native_review_schema
    frame = {"response_contract": resolve("review_lore_page_from_conversation", Capabilities(("answer_from_sources",), ("lore_page",), None, None)),
             "artifact_under_edit": {"sections": []}, "source_basis": {}}
    # Exact real rejected instruction: includes separate, article, and trailing
    # context wording; none must be re-parsed or reproduced by the writer.
    message = "Create a separate new lore page titled The Memory Ferry from the full context we just discussed. Reuse our conversation only; do not search or re-fetch sources. Preserve the early details, later correction, authored-proposal status, open questions, and all constraints. Leave this workpad unchanged."
    candidate = {"kind": "lore_page", "destination": {"request": "current_author_request", "title": title}, "open_questions": ["Who wrote the ledger?"]}
    result = normalize_native_review(candidate, [], frame, author_text=message, request_reference=True)
    assert result.destination.title == title
    assert result.model_dump(mode='json') == candidate
    schema, definitions = native_review_schema(frame, request_reference=True)
    assert 'LorePageRequestReference' in definitions
    assert 'LorePageTitleWitness' not in definitions
    with pytest.raises(ValueError, match="producing writer contract"):
        normalize_native_review(candidate, [], frame, author_text=message)
    for bad in ({"request": "prior_author_request", "title": title},
                {"request": "current_author_request", "instruction": message, "title": title}):
        with pytest.raises(ValueError):
            normalize_native_review({**candidate, "destination": bad}, [], frame, author_text=message, request_reference=True)


def test_blank_mode_is_admitted_independently_of_writer_reference():
    from application_state.agent_conversation.build_intentional_response import Capabilities, resolve, normalize_native_review
    frame = {"response_contract": resolve("review_blank_lore_page", Capabilities(("answer_from_sources",), ("lore_page",), None, None)),
             "artifact_under_edit": {"sections": []}, "source_basis": {}}
    candidate = {"kind": "lore_page", "destination": {"request": "current_author_request", "title": "The Empty Ferry"}}
    result = normalize_native_review(candidate, [], frame, author_text="Please leave the new ferry page empty.", request_reference=True)
    assert result.destination.title == 'The Empty Ferry'
    with pytest.raises(ValueError, match="Blank lore-page request"):
        normalize_native_review({**candidate, "open_questions": ["Who wrote the ledger?"]}, [], frame,
            author_text="Please leave the new ferry page empty.", request_reference=True)


def test_app207_menu_and_literal_review_schema_bytes_remain_unchanged():
    # Frozen from exact serving79d4, not recomputed from the current inventory.
    from application_state.agent_conversation import build_intentional_response as c
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    menu = '3e65cfdc73f7ea8b0df24158471d0a2fbec800a326c7bd8bf69b261808ff2ca4'
    resolver = '1f734fecdd45366e7ddf0eeaea5a7d995b99a874ff5f58e2eb0524b210663064'
    assert c.known_semantics(menu, resolver)
    assert 'review_blank_lore_page' not in c._menu_work(menu)
    for label, expected in {
        'review_lore_page': '2c40f2fda05636749e5e35ff31b53cbbfe558e04bbd7b2e8a201b95f3b83ad79',
        'review_lore_page_from_conversation': 'c9c1343f5b29dce9fedf72294e3d9d94becaaedeeef6d6f4bc41e2d7ccc1a097',
    }.items():
        frame = {'response_contract': c.resolve(label, c.Capabilities(('answer_from_sources',), ('lore_page',), None, None), work_options=c._menu_work(menu)),
                 'artifact_under_edit': {'sections': []}, 'source_basis': {}}
        assert canonical_sha256(c.native_review_schema(frame)) == expected



def test_request_review_normalizes_proposal_formatting_without_changing_legacy_readers():
    from application_state.agent_conversation.lore_page_review import ProposedLorePageReference, ProposedLorePage
    review=ProposedLorePageReference.model_validate({'kind':'lore_page',
        'destination':{'request':'current_author_request','title':' \n The Memory Ferry — Échos \t'},
        'open_questions':['  Who wrote\n the ledger?  ','\tWhat is its origin?\n']})
    assert review.destination.title=='The Memory Ferry — Échos'
    assert review.open_questions==('Who wrote the ledger?','What is its origin?')
    assert review.destination.bind('Create the ferry page from our discussion.')==review.destination.title
    with pytest.raises(ValueError):
        ProposedLorePage.model_validate({'kind':'lore_page',
            'destination':{'instruction':'Create a page for Ferry.','title':'Ferry'},
            'open_questions':['Who wrote\n the ledger?']})
    with pytest.raises(ValueError):
        ProposedLorePageReference.model_validate({'kind':'lore_page',
            'destination':{'request':'current_author_request','title':' \n\t '}})
    with pytest.raises(ValueError):
        ProposedLorePageReference.model_validate({'kind':'lore_page',
            'destination':{'request':'current_author_request','title':'Ferry'},'open_questions':[' \n ']})
