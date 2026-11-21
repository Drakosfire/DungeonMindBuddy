import json
from hashlib import sha256

import pytest
from generationengine.types import ChoiceDecisionAnswer, DecisionResult, InferenceObservation

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


def test_opening_must_match_retained_catalog_and_requested_work(captured_page):
    catalog = freeze_build_prose_catalog(*captured_page)
    question, title = "Insert a line after the moon in East", "Gate"
    state, choices = build_boundary_opening(question, title, catalog)
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
