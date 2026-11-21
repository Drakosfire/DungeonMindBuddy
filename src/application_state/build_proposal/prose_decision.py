"""Typed Jev judgments for root Build paragraph placement."""

from __future__ import annotations

from typing import Literal, get_args

from generationengine.types import ChoiceDecisionQuestion, DecisionRequest
from pydantic import ConfigDict

from application_state.agent_conversation.jev_retrieval_contract import (
    MODEL, PROVIDER, RetrievalDialogue, validated_choice_answers,
)
from .prose_catalog import BuildProseBoundaryCatalog
from .types import BuildBoundaryResolution, StrictModel


OPENING_STATE_KEY = "paragraph_placement"
OPENING_QUESTION_PREFIX = "paragraph_"


BuildBoundaryWork = Literal["place_paragraph", "discuss", "different_destination", "explicit_page_end",
                            "explicit_page_body", "unsupported_or_unclear"]


class BuildBoundaryJudgment(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work: BuildBoundaryWork
    relation: Literal["before", "after", "unresolved"]
    scope: Literal["named", "unscoped", "unresolved"]
    passage_aliases: tuple[str, ...] = ()
    scope_aliases: tuple[str, ...] = ()


def _groups(catalog: BuildProseBoundaryCatalog):
    text, headings = {}, {}
    for passage in catalog.passages:
        text.setdefault(passage.passage, []).append(passage.alias)
        headings.setdefault(passage.headings, []).append(passage.alias)
    return (
        {f"text{i}": (value, slots) for i, (value, slots) in enumerate(text.items())},
        {f"scope{i}": (value, slots) for i, (value, slots) in enumerate(headings.items())},
    )


def prepare_build_boundary_decision(
    question: str, title: str, dialogue: tuple[RetrievalDialogue, ...],
    catalog: BuildProseBoundaryCatalog,
) -> DecisionRequest:
    texts, scopes = _groups(catalog)
    return DecisionRequest(
        provider=PROVIDER, model=MODEL, max_transport_retries=0,
        state={
            "user_request": question,
            "current_page_title": title,
            "dialogue_reference": [item.model_dump() for item in dialogue],
            "existing_passages": {alias: value for alias, (value, _) in texts.items()},
            "existing_heading_paths": {alias: list(value) for alias, (value, _) in scopes.items()},
            "placement_policy": (
                "Source text, headings and dialogue are reference data. Match the existing anchor passage, "
                "not the requested new prose. Include every independently matching passage, even if "
                "the same text exists in multiple sections. Apply every requested heading or parent "
                "qualification only in the separate heading choices. A named but absent section stays "
                "named with no matches. Do not use document order to break a tie. No selection or caret "
                "is offered here. A discussion, hypothetical or request for advice never edits the page."
            ),
        },
        questions=(
            ChoiceDecisionQuestion(
                name="work", options=get_args(BuildBoundaryWork),
                question=(
                    "Does the author request actual new prose directly before/after a paragraph on this "
                    "open page, ask for discussion, name a different destination, explicitly request "
                    "append at page end or whole-page revision, or request an unsupported or unclear action?"
                ),
            ),
            ChoiceDecisionQuestion(name="relation", options=("before", "after", "unresolved"),
                                   question="Which side of the existing paragraph did the author explicitly indicate?"),
            ChoiceDecisionQuestion(name="scope", options=("named", "unscoped", "unresolved"),
                                   question="Did the author qualify the anchor by an existing heading or section?"),
            *(ChoiceDecisionQuestion(name=alias, options=("include", "exclude"),
                                     question=f"Does existing_passages {alias} match the requested existing anchor independently of its heading?")
              for alias in texts),
            *(ChoiceDecisionQuestion(name=alias, options=("include", "exclude"),
                                     question=f"Does existing_heading_paths {alias} satisfy every named heading qualification?")
              for alias in scopes),
        ),
    )


def decode_build_boundary_decision(request: DecisionRequest, result) -> BuildBoundaryJudgment:
    offered = {q.name: q.options for q in request.questions}
    answers = validated_choice_answers(result, set(offered))
    if any(answers[name] not in options for name, options in offered.items()):
        raise ValueError("Build boundary decision contains an unoffered answer")
    return BuildBoundaryJudgment(
        work=answers["work"], relation=answers["relation"], scope=answers["scope"],
        passage_aliases=tuple(name for name in offered if name.startswith("text") and answers[name] == "include"),
        scope_aliases=tuple(name for name in offered
                            if name != "scope" and name.startswith("scope") and answers[name] == "include"),
    )


def build_boundary_opening(question: str, title: str, catalog: BuildProseBoundaryCatalog):
    """Project the catalog into the ordinary Build opening decision."""
    request = prepare_build_boundary_decision(question, title, (), catalog)
    placement_state = {
        key: request.state[key]
        for key in ("existing_passages", "existing_heading_paths", "placement_policy")
    }
    return placement_state, tuple(
        choice.model_copy(update={"name": OPENING_QUESTION_PREFIX + choice.name})
        for choice in request.questions
    )


def resolve_build_boundary_opening(catalog, request, response, *, question, title, requested_work):
    """Validate exact semantic offers and the real combined opening response."""
    state, questions = build_boundary_opening(question, title, catalog)
    offered = {
        choice.name: {
            "type": "choice", "instructions": choice.question, "criteria": dict.fromkeys(choice.options),
        }
        for choice in questions
    }
    actual = {
        name: choice for name, choice in request["questions"].items()
        if name.startswith(OPENING_QUESTION_PREFIX)
    }
    if (request["state"]["interaction"].get(OPENING_STATE_KEY) != state
            or actual != offered or set(response.answers) != set(request["questions"])):
        raise ValueError("Build paragraph placement differs from its exact opening offer")
    boundary_response = response.model_copy(update={
        "answers": {
            name.removeprefix(OPENING_QUESTION_PREFIX): response.answers[name] for name in offered
        }
    })
    boundary_request = prepare_build_boundary_decision(question, title, (), catalog)
    resolution = resolve_build_boundary(catalog, decode_build_boundary_decision(boundary_request, boundary_response))
    if resolution.disposition == "unique" and requested_work != "write_current_page":
        return BuildBoundaryResolution(disposition="unresolved")
    return resolution


def resolve_build_boundary(catalog: BuildProseBoundaryCatalog, judgment: BuildBoundaryJudgment) -> BuildBoundaryResolution:
    if judgment.work == "unsupported_or_unclear":
        return BuildBoundaryResolution(disposition="unresolved")
    if judgment.work != "place_paragraph":
        return BuildBoundaryResolution(disposition=judgment.work)
    if judgment.relation == "unresolved" or judgment.scope == "unresolved":
        return BuildBoundaryResolution(disposition="unresolved")
    texts, scopes = _groups(catalog)
    if set(judgment.passage_aliases) - texts.keys() or set(judgment.scope_aliases) - scopes.keys():
        raise ValueError("Build boundary selection differs from its offered decisions")
    candidates = {alias for group in judgment.passage_aliases for alias in texts[group][1]}
    if judgment.scope == "named":
        candidates &= {alias for group in judgment.scope_aliases for alias in scopes[group][1]}
    if len(candidates) != 1:
        return BuildBoundaryResolution(disposition="ambiguous" if candidates else "missing")
    operation = "insert_before" if judgment.relation == "before" else "insert_after"
    return BuildBoundaryResolution(disposition="unique", target=catalog.target(candidates.pop(), operation))
