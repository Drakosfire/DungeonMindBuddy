import json
from dataclasses import replace
from hashlib import sha256

import pytest
from generationengine.types import ChoiceDecisionAnswer, DecisionResult, InferenceObservation

from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
from application_state.build_proposal.graph_reference_decision import (
    GRAPH_REFERENCE_OPENING, BuildGraphReferenceCandidate, BuildGraphReferenceDecision,
    resolve_graph_reference_opening,
)
from application_state.build_proposal.prose_catalog import freeze_build_prose_catalog
from application_state.build_proposal.prose_decision import (
    BuildBoundaryJudgment,
    build_boundary_opening,
    prepare_build_boundary_decision,
    resolve_build_boundary,
    resolve_build_boundary_opening,
)
from application_state.build_proposal.types import (
    BuildComposeTargetMismatch, BuildPageBodyOffer, BuildPageEndOffer, BuildProposalBasis,
    normalize_proposal_output,
)


def digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def captured_page():
    def block(kind, text, attrs=None):
        data = {"type": kind, "content": [{"type": "text", "text": text}]}
        if attrs:
            data["attrs"] = attrs
        return data

    editor = json.dumps({"type": "doc", "content": [
        block("heading", "West", {"level": 2}),
        block("paragraph", "The moon is 🌘."),
        block("heading", "East", {"level": 2}),
        block("paragraph", "The moon is 🌘."),
    ]}, ensure_ascii=False)
    draft = "## West\n\nThe moon is 🌘.\n\n## East\n\nThe moon is 🌘.\n"
    basis = BuildProposalBasis(
        world_id="private-world", document_id="private-document", registry_revision=1,
        content_sha256="a" * 64, visibility="internal", caret=1,
        draft_sha256=digest(draft), editor_sha256=digest(editor),
        draft_generation=0, selection_generation=0,
    )
    return basis, editor, draft


@pytest.fixture
def mixed_page(captured_page):
    basis, _, _ = captured_page
    asset = "ac6c15cc-8c68-4732-8ae2-d9f3f051393a"

    def paragraph(text):
        return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

    def heading(text):
        return {**paragraph(text), "type": "heading", "attrs": {"level": 2}}

    def callout(kind, label, text):
        return {"type": "callout", "attrs": {"kind": kind, "label": label},
                "content": [paragraph(text)]}

    def table_row(kind, *texts):
        return {"type": "tableRow", "content": [
            {"type": kind, "attrs": {"colspan": 1, "rowspan": 1, "colwidth": None},
             "content": [paragraph(text)]} for text in texts
        ]}

    blocks = [
        heading("Arrival"), paragraph("The gate is locked."),
        callout("read-aloud", "First sight", "Three blue lanterns light the crossing."),
        callout("gm-note", "Keep it sealed", "Wait for the players to investigate."),
        heading("Signal table"),
        {"type": "table", "content": [
            table_row("tableHeader", "Signal", "State"),
            table_row("tableCell", "Blue lanterns", "Lit"),
        ]},
        {"type": "paragraph", "content": [
            {"type": "mediaImage", "attrs": {
                "assetId": asset, "alt": "Saved boardwalk artwork",
                "width": None, "collapsed": None,
            }},
        ]},
        heading("Rumours"), paragraph("The gate is locked."),
    ]
    draft = (
        "## Arrival\n\nThe gate is locked.\n\n"
        "> [!READ-ALOUD] First sight\n> Three blue lanterns light the crossing.\n\n"
        "> [!GM-NOTE] Keep it sealed\n> Wait for the players to investigate.\n\n"
        "## Signal table\n\n| Signal | State |\n| --- | --- |\n| Blue lanterns | Lit |\n\n"
        f"![Saved boardwalk artwork](dmb-media:{asset})\n\n"
        "## Rumours\n\nThe gate is locked.\n"
    )
    return basis.model_copy(update={"draft_sha256": digest(draft)}), blocks, draft


def freeze_mixed_page(basis, blocks, draft):
    editor_json = json.dumps({"type": "doc", "content": blocks}, ensure_ascii=False)
    return freeze_build_prose_catalog(
        basis.model_copy(update={"editor_sha256": digest(editor_json)}), editor_json, draft,
    )


def test_mixed_build_capture_counts_protected_blocks_without_offering_them(mixed_page):
    catalog = freeze_mixed_page(*mixed_page)
    assert catalog.target("passage2", "insert_after").from_ == 209
    assert [(p.alias, p.headings, p.before, p.after) for p in catalog.passages] == [
        ("passage1", ("Arrival",), 9, 30),
        ("passage2", ("Rumours",), 188, 209),
    ]


@pytest.mark.parametrize("change", ["callout_kind", "callout_body", "table", "image", "image_child"])
def test_changed_protected_blocks_cannot_shift_a_valid_later_target(mixed_page, change):
    basis, blocks, draft = mixed_page
    if change == "callout_kind":
        blocks[2]["attrs"]["kind"] = "gm-note"
    elif change == "callout_body":
        blocks[2]["content"][0]["content"][0]["text"] = "A different scene."
    elif change == "table":
        blocks[5]["content"][1]["content"][0]["content"][0]["content"][0]["text"] = "Red"
    elif change == "image":
        blocks[6]["content"][0]["attrs"]["assetId"] = "ff6c15cc-8c68-4732-8ae2-d9f3f051393a"
    else:
        blocks[6]["content"][0]["content"] = []
    with pytest.raises(ValueError):
        freeze_mixed_page(basis, blocks, draft)


def test_duplicate_passage_needs_explicit_unique_scope(captured_page):
    catalog = freeze_build_prose_catalog(*captured_page)
    assert [(p.before, p.after) for p in catalog.passages] == [(6, 23), (29, 46)]
    unscoped = BuildBoundaryJudgment(
        work="place_paragraph", relation="after", scope="unscoped", passage_aliases=("text0",),
    )
    assert resolve_build_boundary(catalog, unscoped).disposition == "ambiguous"
    named = unscoped.model_copy(update={"scope": "named", "scope_aliases": ("scope1",)})
    target = resolve_build_boundary(catalog, named).target
    assert target.model_dump(by_alias=True)["from"] == 46
    assert target.alias == "passage2:insert_after"
    assert target.catalog_sha256 == catalog.choices_sha256
    missing = named.model_copy(update={"scope_aliases": ()})
    assert resolve_build_boundary(catalog, missing).disposition == "missing"


def test_decision_offers_semantics_without_editor_geometry(captured_page):
    catalog = freeze_build_prose_catalog(*captured_page)
    request = prepare_build_boundary_decision("Add a line after the moon in East", "Gate", (), catalog)
    assert request.state["existing_passages"] == {"text0": "The moon is 🌘."}
    assert request.state["existing_heading_paths"] == {"scope0": ["West"], "scope1": ["East"]}
    model_input = request.model_dump_json()
    for metadata in ("private-world", "private-document", "passage2", '"caret":', catalog.choices_sha256):
        assert metadata not in model_input


def test_altered_capture_cannot_grant_a_target(captured_page):
    basis, editor, draft = captured_page
    for edited_json, edited_draft in ((editor + " ", draft), (editor, draft + "\n")):
        with pytest.raises(ValueError, match="exact draft"):
            freeze_build_prose_catalog(basis, edited_json, edited_draft)
    wrong_draft = draft.replace("West", "North")
    inconsistent = basis.model_copy(update={"draft_sha256": digest(wrong_draft)})
    with pytest.raises(ValueError):
        freeze_build_prose_catalog(inconsistent, editor, wrong_draft)


@pytest.mark.parametrize("work,relation,scope,disposition", [
    ("discuss", "after", "named", "discuss"),
    ("different_destination", "after", "named", "different_destination"),
    ("unsupported_or_unclear", "after", "named", "unresolved"),
    ("place_paragraph", "unresolved", "named", "unresolved"),
    ("place_paragraph", "after", "unresolved", "unresolved"),
])
def test_nonplacement_judgment_has_no_target(captured_page, work, relation, scope, disposition):
    catalog = freeze_build_prose_catalog(*captured_page)
    judgment = BuildBoundaryJudgment(
        work=work, relation=relation, scope=scope,
        passage_aliases=("text0",), scope_aliases=("scope1",),
    )
    resolution = resolve_build_boundary(catalog, judgment)
    assert resolution.disposition == disposition
    assert resolution.target is None


@pytest.mark.parametrize("version", [1, 2])
def test_opening_must_match_retained_catalog_and_requested_work(captured_page, version):
    catalog = freeze_build_prose_catalog(*captured_page)
    question, title = "Insert a line after the moon in East", "Gate"
    state, choices = build_boundary_opening(question, title, catalog, version=version)
    request = {
        "state": {"interaction": {"paragraph_placement": state}},
        "questions": {
            choice.name: {"type": "choice", "instructions": choice.question,
                          "criteria": dict.fromkeys(choice.options)}
            for choice in choices
        },
    }
    request["questions"]["requested_work"] = {}
    labels = dict(paragraph_work="place_paragraph", paragraph_scope="named", paragraph_relation="after",
                  paragraph_text0="include", paragraph_scope0="exclude", paragraph_scope1="include",
                  requested_work="write_current_page")
    if version == 2:
        labels["paragraph_destination"] = "current_page"
    response = DecisionResult(
        answers={name: ChoiceDecisionAnswer(selected=label) for name, label in labels.items()},
        observation=InferenceObservation(
            provider="typesafe", resolved_model="jev-1.14.0", response_model="jev-1.14.0",
            latency_ms=100, retry_count=0, state="completed", provider_attempt_count=1,
        ),
    )
    outcome = resolve_build_boundary_opening(
        catalog, request, response, question=question, title=title, requested_work="write_current_page",
    )
    assert outcome.target.alias == "passage2:insert_after"
    outcome = resolve_build_boundary_opening(
        catalog, request, response, question=question, title=title, requested_work="discuss",
    )
    assert outcome.target is None
    if version == 2:
        response.answers["paragraph_destination"] = ChoiceDecisionAnswer(selected="different_page")
        outcome = resolve_build_boundary_opening(
            catalog, request, response, question=question, title=title, requested_work="write_current_page",
        )
        assert outcome.disposition == "different_destination"
        assert outcome.target is None
        truncated = {**request, "questions": {
            name: choice for name, choice in request["questions"].items()
            if name != "paragraph_destination"
        }}
        with pytest.raises(ValueError, match="exact opening offer"):
            resolve_build_boundary_opening(
                catalog, truncated, response, question=question, title=title, requested_work="write_current_page",
            )
    request["questions"]["paragraph_scope1"]["criteria"]["maybe"] = None
    with pytest.raises(ValueError, match="exact opening offer"):
        resolve_build_boundary_opening(
            catalog, request, response, question=question, title=title, requested_work="write_current_page",
        )


@pytest.mark.parametrize(("requested_work", "location", "relation", "destination", "expected"), [
    ("write_current_page", "unstated", "unresolved", "current_page", "unique"),
    ("write_current_page", "current_caret", "unresolved", "current_page", "unique"),
    ("discuss", "unstated", "unresolved", "current_page", "unresolved"),
    ("write_current_page", "unstated", "after", "current_page", "unresolved"),
    ("write_current_page", "unclear", "unresolved", "current_page", "unresolved"),
    ("write_current_page", "existing_location", "after", "current_page", "missing"),
    ("write_current_page", "unstated", "unresolved", "different_page", "different_destination"),
])
def test_opening_uses_only_the_exact_uncontested_caret(
    mixed_page, requested_work, location, relation, destination, expected,
):
    catalog = freeze_mixed_page(*mixed_page)
    first, duplicate = catalog.passages
    assert first.passage == duplicate.passage
    caret = first.after - 1
    question = "Add two ordinary paragraphs about how the station maintains this road."
    state, choices = build_boundary_opening(question, "Arrival", catalog, caret=caret)
    _, interior_choices = build_boundary_opening(question, "Arrival", catalog, caret=caret - 1)
    assert all(choice.name != "paragraph_insertion_location" for choice in interior_choices)
    request = {
        "state": {"interaction": {"paragraph_placement": state}},
        "questions": {
            choice.name: {"type": "choice", "instructions": choice.question,
                          "criteria": dict.fromkeys(choice.options)}
            for choice in choices
        },
    }
    labels = dict(paragraph_work="place_paragraph", paragraph_scope="named",
                  paragraph_insertion_location=location,
                  paragraph_destination=destination, paragraph_relation=relation,
                  paragraph_text0="include", paragraph_scope0="exclude", paragraph_scope1="exclude")
    response = DecisionResult(
        answers={name: ChoiceDecisionAnswer(selected=label) for name, label in labels.items()},
        observation=InferenceObservation(
            provider="typesafe", resolved_model="jev-1.14.0", response_model="jev-1.14.0",
            latency_ms=100, retry_count=0, state="completed", provider_attempt_count=1,
        ),
    )
    outcome = resolve_build_boundary_opening(
        catalog, request, response, question=question, title="Arrival",
        requested_work=requested_work, caret=caret,
    )
    assert outcome.disposition == expected
    assert outcome.target == (catalog.target(first.alias, "insert_after") if expected == "unique" else None)
    with pytest.raises(ValueError, match="exact opening offer"):
        resolve_build_boundary_opening(
            catalog, request, response, question=question, title="Arrival",
            requested_work=requested_work, caret=caret - 1,
        )


@pytest.mark.parametrize("required,submitted", [("page_end", "captured"), ("page_body", "page_end")])
def test_explicit_offers_cannot_be_retargeted_by_writer(required, submitted):
    raw = {"destination": "current_page", "target": submitted, "replacement_markdown": "A lamp.",
           "summary": "A lamp.", "assumptions": []}
    offers = (BuildPageBodyOffer(end=5), BuildPageEndOffer(end=5))
    with pytest.raises(BuildComposeTargetMismatch, match="target_mismatch"):
        normalize_proposal_output(json.dumps(raw), *offers, required_target=required)
    raw["target"] = required
    assert normalize_proposal_output(json.dumps(raw), *offers, required_target=required).target == required


@pytest.fixture
def graph_decision(captured_page):
    basis = captured_page[0]
    candidates = tuple(BuildGraphReferenceCandidate(
        reference=AuthoredGraphReferenceV1(
            managed_world_id=basis.world_id, native_world_id="private-native", binding_version=7,
            graph_revision="private-graph-revision", node_id=node, label="Ivory Sentry",
        ),
        entity_kind=kind, summary=summary,
    ) for node, kind, summary in (
        ("construct:original-ivory", "construct", "Original mechanism at West."),
        ("construct:retuned-ivory", "construct", "Retuned mechanism with a blue vane."),
        ("location:ivory", "location", "An old watchpoint."),
    ))
    return BuildGraphReferenceDecision(
        basis, freeze_build_prose_catalog(*captured_page), candidates,
        "Insert a reference to the retuned Ivory Sentry construct after the moon in East.", "Gate",
        author_selected=candidates[1].reference,
    )


def graph_response(**changes):
    labels = dict(work="place_paragraph", destination="current_page", relation="after", scope="named",
                  anchor_occurrence="passage2", reference_nomination="object2",
                  text0="include", scope0="exclude", scope1="include", reference_intent="place_existing",
                  reference_kind="class1", reference_kind_constraint="requires_or_excludes_type", object1="exclude",
                  object2="include", object3="exclude")
    labels.update(changes)
    return DecisionResult(
        answers={name: ChoiceDecisionAnswer(selected=label) for name, label in labels.items()},
        observation=InferenceObservation(provider="typesafe", resolved_model="jev-1.14.0", response_model="jev-1.14.0",
            latency_ms=100, retry_count=0, state="completed", provider_attempt_count=1),
    )


def test_graph_opening_requires_the_exact_wire_offer_and_real_choice():
    question = GRAPH_REFERENCE_OPENING
    wire = {"type": "choice", "instructions": question.question, "criteria": dict.fromkeys(question.options)}
    request = {"questions": {question.name: wire}}
    response = graph_response().model_copy(update={"answers": {
        question.name: ChoiceDecisionAnswer(selected="place_existing_reference"),
    }})
    assert resolve_graph_reference_opening(request, response) == "place_existing_reference"
    with pytest.raises(ValueError, match="exact admitted offer"):
        resolve_graph_reference_opening({"questions": {}}, response)
    with pytest.raises(ValueError, match="exact admitted offer"):
        resolve_graph_reference_opening(request, graph_response())
    with pytest.raises(ValueError, match="unoffered answer"):
        resolve_graph_reference_opening(request, response.model_copy(update={"answers": {
            question.name: ChoiceDecisionAnswer(selected="write_current_page"),
        }}))
    assert resolve_graph_reference_opening({"questions": {}}, graph_response()) is None


def test_graph_decision_offers_only_semantic_aliases_and_binds_typed_placement(graph_decision):
    request = graph_decision.request()
    assert request.state["author_placement_words"] == {
        "object_expression": "a reference to the retuned Ivory Sentry construct",
        "anchor_expression": "the moon in East",
    }
    quoted = replace(graph_decision, question='Link Ivory Sentry after the paragraph “The moon is out”.')
    assert "author_placement_words" not in quoted.request().state
    assert request.state["paragraph_order"] == [
        {"occurrence": "passage1", "passage": "text0", "section": "scope0"},
        {"occurrence": "passage2", "passage": "text0", "section": "scope1"},
    ]
    assert "Choose unscoped when no heading" in next(q.question for q in request.questions if q.name == "scope")
    remapped = graph_decision.candidates[0].model_copy(update={
        "reference": graph_decision.candidates[0].reference.model_copy(update={"node_id": "same-wire-foreign-id"}),
    })
    changed = replace(graph_decision, candidates=(remapped, *graph_decision.candidates[1:]))
    assert changed.request() == request
    assert changed.host_inventory_sha256() != graph_decision.host_inventory_sha256()
    assert graph_decision.resolve(graph_response(reference_kind="unspecified")).disposition == "wrong_kind"
    model_input = request.model_dump_json()
    for private in ("private-world", "private-native", "private-document", "private-graph-revision",
                    "construct:retuned-ivory", "location:ivory", graph_decision.catalog.choices_sha256):
        assert private not in model_input
    assert request.state["graph_objects"]["object2"]["name"] == "Ivory Sentry"
    assert request.state["author_selected_object"] == "object2"
    placement = graph_decision.resolve(graph_response()).placement
    assert placement.reference.node_id == "construct:retuned-ivory"
    assert placement.entity_kind == "construct"
    assert placement.boundary.alias == "passage2:insert_after"


@pytest.mark.parametrize("choices,disposition", [
    ({"object1": "include", "object2": "exclude"}, "missing_identity"),
    ({"reference_kind": "class2"}, "wrong_kind"),
    ({"reference_kind": "class2", "object2": "exclude"}, "wrong_kind"),
    ({"reference_kind": "class2", "text0": "exclude"}, "wrong_kind"),
    ({"reference_kind": "other_kind"}, "wrong_kind"),
    ({"reference_kind": "other_kind", "object2": "exclude"}, "wrong_kind"),
    ({"object2": "exclude"}, "missing_identity"),
    ({"scope": "unscoped"}, "ambiguous_boundary"),
    ({"anchor_occurrence": "passage1"}, "ambiguous_boundary"),
    ({"scope1": "exclude"}, "missing_boundary"),
    ({"destination": "different_page"}, "different_page"),
    ({"reference_intent": "discussion"}, "discussion"),
    ({"reference_intent": "new_object"}, "new_object"),
])
def test_graph_decision_refuses_without_a_unique_identity_boundary_and_intent(graph_decision, choices, disposition):
    result = graph_decision.resolve(graph_response(**choices))
    assert result.disposition == disposition
    assert result.placement is None


def test_graph_decision_cannot_take_identity_from_a_quoted_anchor_or_guessed_class(graph_decision):
    unqualified = replace(graph_decision, author_selected=None,
        question='Link Ivory Sentry after the paragraph “retuned Ivory Sentry”.')
    refusal = unqualified.resolve(graph_response())
    assert refusal.disposition == "ambiguous_identity" and refusal.placement is None
    guessed_kind = unqualified.resolve(graph_response(reference_kind="class2", object2="exclude", object3="include"))
    assert guessed_kind.disposition == "ambiguous_identity" and guessed_kind.placement is None


def test_graph_decision_shared_alias_requires_the_current_author_selected_identity(graph_decision):
    first, second, third = graph_decision.candidates
    first = first.model_copy(update={"reference": first.reference.model_copy(update={"label":"Ivory Guard"}),
                                   "aliases": ("Gate Watch",)})
    second = second.model_copy(update={"reference": second.reference.model_copy(update={"label":"Moon Guard"}),
                                      "aliases": ("gate watch",)})
    shared = replace(graph_decision, candidates=(first, second, third), author_selected=None,
        question="Place a reference to Gate Watch after the moon in East.")
    refusal = shared.resolve(graph_response())
    assert refusal.disposition == "ambiguous_identity" and refusal.placement is None
    selected = replace(shared, author_selected=second.reference).resolve(graph_response())
    assert selected.placement.reference == second.reference


@pytest.mark.parametrize("question,overrides,expected", [
    ("Add a reference to Ivory Sentry location after the moon in East.",
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, "location:ivory"),
    ("Link Ivory Sentry with a blue vane after the moon in East.", {}, "construct:retuned-ivory"),
    ("Link Blue Watch after the moon in East.", {}, "construct:retuned-ivory"),
    ("Could you link Blue Watch after the moon in East?", {}, "construct:retuned-ivory"),
    ("After the moon in East, would you please link Blue Watch?", {}, "construct:retuned-ivory"),
    ("Could you link Ivory Sentry location rather than the construct after the moon in East?",
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, "location:ivory"),
    ("Could you link Ivory Sentry after the paragraph about a location rather than the construct?",
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, None),
    ('Link “Blue Watch” after the moon in East.', {}, "construct:retuned-ivory"),
    ("After the moon in East, add a new link to Blue Watch.", {}, "construct:retuned-ivory"),
    ("Link the location named Ivory Sentry after the moon in East.",
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, "location:ivory"),
    ("Link the location Ivory Sentry after the moon in East.",
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, "location:ivory"),
    ('Link the location “Ivory Sentry” after the moon in East.',
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, "location:ivory"),
    ("I would like you to link Ivory Sentry, the location, after the moon in East.",
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, "location:ivory"),
    ("Link the with a blue vane version of Ivory Sentry after the moon in East.", {}, "construct:retuned-ivory"),
    ("Link Ivory Sentry as a location after the moon in East.",
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, "location:ivory"),
    ('Link Ivory Sentry after the paragraph about “Blue Watch”.', {}, None),
    ('Link Ivory Sentry “location” after the moon in East.',
     {"reference_kind": "class2", "object2": "exclude", "object3": "include"}, None),
    ("Link Ivory Sentry after the paragraph about a blue vane.", {}, None),
    ("Link Blue Watch, or link Ivory Sentry after the moon in East.", {}, None),
    ("Link Ivory Sentry, the location, after the moon in East.", {}, None),
    ("Link Ivory Sentry construct after the moon in East.", {}, None),
])
def test_graph_identity_expression_must_uniquely_match_the_authorized_inventory(
    graph_decision, question, overrides, expected,
):
    first, second, third = graph_decision.candidates
    decision = replace(graph_decision, question=question, author_selected=None, candidates=(
        first, second.model_copy(update={"aliases": ("Blue Watch",)}), third,
    ))
    result = decision.resolve(graph_response(**overrides))
    if expected is None:
        assert result.disposition == "ambiguous_identity" and result.placement is None
    else:
        assert result.placement.reference.node_id == expected


@pytest.mark.parametrize("question", [
    "Link the with a blue vane version of Ivory Sentry after the moon in East.",
    'Link “Blue Watch” after the moon in East.',
])
def test_graph_literal_qualifier_requires_uniqueness_across_excluded_candidates(graph_decision, question):
    first, second, third = graph_decision.candidates
    first = first.model_copy(update={"summary": second.summary, "aliases": ("Blue Watch",)})
    second = second.model_copy(update={"aliases": ("Blue Watch",)})
    decision = replace(graph_decision, question=question, author_selected=None, candidates=(first, second, third))
    result = decision.resolve(graph_response())
    assert result.disposition == "ambiguous_identity" and result.placement is None


@pytest.mark.parametrize("question,nomination,expected", [
    ("Link Blue Watch after the moon in East.", "object2", "ready"),
    ("Link Blue Watch after the moon in East.", "object1", "ambiguous_identity"),
    ("Link Blue Watch after the moon in East.", "unresolved", "ambiguous_identity"),
    ("Link Ivory Sentry after the paragraph mentioning Blue Watch.", "object2", "ambiguous_identity"),
])
def test_multiple_graph_matches_require_model_nomination_and_unique_author_evidence(
    graph_decision, question, nomination, expected,
):
    first, second, third = graph_decision.candidates
    decision = replace(graph_decision, question=question, author_selected=None, candidates=(
        first, second.model_copy(update={"aliases": ("Blue Watch",)}), third,
    ))
    result = decision.resolve(graph_response(object1="include", reference_nomination=nomination))
    assert result.disposition == expected
    if expected == "ready":
        assert result.placement.reference == second.reference
    else:
        assert result.placement is None


@pytest.mark.parametrize("question", [
    "If you were to link Ivory Sentry after the moon in East, where would it go?",
    "Could you not link Ivory Sentry after the moon in East?",
    "Don't link Ivory Sentry after the moon in East.",
])
def test_graph_explicit_negation_and_hypothetical_refuse_even_with_an_author_selection(graph_decision, question):
    decision = replace(graph_decision, question=question)
    result = decision.resolve(graph_response())
    assert result.disposition == "discussion" and result.placement is None


def test_graph_occurrence_vote_cannot_override_multiple_compatible_passages(graph_decision, captured_page):
    votes = graph_response(scope="unscoped", anchor_occurrence="passage2")
    assert graph_decision.resolve(votes).disposition == "ambiguous_boundary"

    basis, editor, draft = captured_page
    editor = editor.replace("The moon is 🌘.", "The sun is high.", 1)
    draft = draft.replace("The moon is 🌘.", "The sun is high.", 1)
    basis = basis.model_copy(update={"editor_sha256": digest(editor), "draft_sha256": digest(draft)})
    distinct = replace(graph_decision, basis=basis, catalog=freeze_build_prose_catalog(basis, editor, draft),
                       question="Reference the selected construct after the paragraph about the moon.")
    nominated = distinct.resolve(graph_response(scope="unscoped", text1="include", anchor_occurrence="passage2"))
    assert nominated.disposition == "ambiguous_boundary" and nominated.placement is None


@pytest.mark.parametrize("question,occurrence,expected", [
    ("Add the selected reference after the first paragraph of the West section.", "passage1", "ready"),
    ("Add the selected reference after the first paragraph of the West section.", "passage2", "ambiguous_boundary"),
    ("Link Ivory Sentry before the third paragraph or after the first paragraph of the West section.", "passage1", "ambiguous_boundary"),
    ("Do not add the selected reference after the first paragraph of the West section.", "passage1", "discussion"),
    ("Put a note saying to add the selected reference after the first paragraph of the West section.", "passage1", "ambiguous_boundary"),
    ("Explain whether to add the selected reference after the first paragraph of the West section.", "passage1", "ambiguous_boundary"),
    ("Add the selected reference after the first paragraph of the West Coast section.", "passage1", "ambiguous_boundary"),
    ('Add the selected reference beside “after the first paragraph of the West section”.', "passage1", "ambiguous_boundary"),
])
def test_graph_occurrence_ordinal_needs_literal_author_scope(graph_decision, question, occurrence, expected):
    shaped = replace(graph_decision, question=question)
    nomination = shaped.resolve(graph_response(scope0="include", anchor_occurrence=occurrence))
    assert nomination.disposition == expected
    if expected == "ready":
        assert nomination.placement.boundary.alias == "passage1:insert_after"


def test_graph_decision_rejects_foreign_stale_and_unoffered_identity_proof(graph_decision):
    original = graph_decision.candidates[0]
    foreign = original.model_copy(update={"reference": original.reference.model_copy(update={
        "managed_world_id": "foreign",
    })})
    with pytest.raises(ValueError, match="admitted World and revision"):
        replace(graph_decision, candidates=(foreign,))
    stale = graph_decision.author_selected.model_copy(update={"graph_revision": "stale"})
    with pytest.raises(ValueError, match="selected Graph object differs"):
        replace(graph_decision, author_selected=stale)
    with pytest.raises(ValueError, match="unoffered answer"):
        graph_decision.resolve(graph_response(reference_kind="private-id"))
