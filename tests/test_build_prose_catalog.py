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
                  anchor_occurrence="passage2",
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
    ("Link Ivory Sentry after the paragraph about a blue vane.", {}, None),
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
    ("Do not add the selected reference after the first paragraph of the West section.", "passage1", "ambiguous_boundary"),
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
