"""Typed Jev judgments for root Build paragraph placement."""

from __future__ import annotations

from typing import Literal, get_args

from generationengine.types import ChoiceDecisionQuestion, DecisionRequest
from pydantic import ConfigDict

from application_state.agent_conversation.jev_retrieval_contract import (
    MODEL, PROVIDER, RetrievalDialogue, validated_choice_answers,
)
from .prose_catalog import BuildProseBoundaryCatalog
from .types import BuildBoundaryResolution, BuildProseBoundaryTarget, StrictModel


OPENING_STATE_KEY = "paragraph_placement"
OPENING_QUESTION_PREFIX = "paragraph_"


BuildBoundaryWork = Literal["place_paragraph", "discuss", "different_destination", "explicit_page_end",
                            "explicit_page_body", "unsupported_or_unclear"]


class BuildBoundaryJudgment(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work: BuildBoundaryWork
    relation: Literal["before", "after", "unresolved"]
    scope: Literal["named", "unscoped", "unresolved"]
    destination: Literal["current_page", "different_page", "unclear"] | None = None
    insertion_location: Literal["unstated", "current_caret", "existing_location", "unclear"] | None = None
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
    catalog: BuildProseBoundaryCatalog, *, version: Literal[1, 2] = 2, offer_caret: bool = False,
) -> DecisionRequest:
    texts, scopes = _groups(catalog)
    work_options = get_args(BuildBoundaryWork)
    offer_caret = offer_caret and version == 2
    work_question = (
        "Does the author request actual new prose directly before/after a paragraph on this "
        "open page, ask for discussion, name a different destination, explicitly request "
        "append at page end or whole-page revision, or request an unsupported or unclear action?"
    )
    scope_question = "Did the author qualify the anchor by an existing heading or section?"
    caret_guidance = "No selection or caret is offered here."
    destination_questions = ()
    if version == 2:
        work_options = tuple(option for option in work_options if option != "different_destination")
        work_question = (
            "What action does the author request, independently of where it should happen? "
            "Distinguish actual paragraph placement, discussion, explicit page-end append, "
            "explicit whole-page revision, and unsupported or unclear actions."
        )
        scope_question = (
            "Did the author name a heading, section or heading path for the anchor? "
            "Choose named even when that heading is absent from the offered paths."
        )
        destination_questions = (ChoiceDecisionQuestion(
            name="destination", options=("current_page", "different_page", "unclear"),
            question=(
                "Which page does the author intend to act on? Choose different_page only when the "
                "author explicitly identifies another page or document as the destination. A location "
                "within this page is current_page even when its named heading is missing. Mentions "
                "of sources or comparisons do not identify the destination."
            ),
        ),)
    location_questions = ()
    if offer_caret:
        work_question += (
            " Requests to add new prose, including read-aloud passages or GM notes, are "
            "place_paragraph even when the author did not name their location."
        )
        caret_guidance = (
            "A verified current caret is available. The insertion_location choice judges "
            "whether the request specifies a location. The other location choices identify "
            "and match an existing anchor only when one is named."
        )
        location_questions = (ChoiceDecisionQuestion(
            name="insertion_location", options=("unstated", "current_caret", "existing_location", "unclear"),
            question=(
                "Where does the user ask new material to go? Judge only placement instructions "
                "in the current request. The topic, length, and purpose of the new writing do "
                "not specify where to insert it. 'Add a paragraph about night patrols' is unstated. "
                "'Add a paragraph after the existing patrol description' is existing_location. "
                "An absent named location is still existing_location. Choose current_caret only "
                "when the author explicitly chooses the caret, and unclear for conflicting "
                "directions or when the author does not request new material."
            ),
        ),)
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
                "named with no matches. Do not use document order to break a tie. "
                + caret_guidance + " A discussion, hypothetical or request for advice never edits the page."
            ),
        },
        questions=(
            ChoiceDecisionQuestion(
                name="work", options=work_options, question=work_question,
            ),
            *destination_questions,
            *location_questions,
            ChoiceDecisionQuestion(name="relation", options=("before", "after", "unresolved"),
                                   question="Which side of the existing paragraph did the author explicitly indicate?"),
            ChoiceDecisionQuestion(name="scope", options=("named", "unscoped", "unresolved"),
                                   question=scope_question),
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
        destination=answers.get("destination"),
        insertion_location=answers.get("insertion_location"),
        passage_aliases=tuple(name for name in offered if name.startswith("text") and answers[name] == "include"),
        scope_aliases=tuple(name for name in offered
                            if name != "scope" and name.startswith("scope") and answers[name] == "include"),
    )


def build_boundary_opening(
    question: str, title: str, catalog: BuildProseBoundaryCatalog, *,
    version: Literal[1, 2] = 2, caret: int | None = None,
):
    """Project the catalog into the ordinary Build opening decision."""
    offer_caret = caret is not None and catalog.target_at_caret(caret) is not None
    request = prepare_build_boundary_decision(question, title, (), catalog, version=version, offer_caret=offer_caret)
    placement_state = {
        key: request.state[key]
        for key in ("existing_passages", "existing_heading_paths", "placement_policy")
    }
    return placement_state, tuple(
        choice.model_copy(update={"name": OPENING_QUESTION_PREFIX + choice.name})
        for choice in request.questions
    )


def resolve_build_boundary_opening(catalog, request, response, *, question, title, requested_work, caret=None):
    """Validate exact semantic offers and the real combined opening response."""
    version = 2 if OPENING_QUESTION_PREFIX + "destination" in request["questions"] else 1
    if OPENING_QUESTION_PREFIX + "insertion_location" not in request["questions"]:
        # Retained openings without the caret question keep their original interpretation.
        caret = None
    state, questions = build_boundary_opening(question, title, catalog, version=version, caret=caret)
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
    caret_target = catalog.target_at_caret(caret) if caret is not None else None
    boundary_request = prepare_build_boundary_decision(
        question, title, (), catalog, version=version, offer_caret=caret_target is not None)
    resolution = resolve_build_boundary(
        catalog, decode_build_boundary_decision(boundary_request, boundary_response), caret_target=caret_target)

    write_dispositions = {"unique", "explicit_page_end", "explicit_page_body"} if version == 2 else {"unique"}
    if resolution.disposition in write_dispositions and requested_work != "write_current_page":
        return BuildBoundaryResolution(disposition="unresolved")
    return resolution


def resolve_build_boundary(
    catalog: BuildProseBoundaryCatalog, judgment: BuildBoundaryJudgment, *,
    caret_target: BuildProseBoundaryTarget | None = None,
) -> BuildBoundaryResolution:
    if judgment.work == "discuss":
        return BuildBoundaryResolution(disposition="discuss")
    if judgment.destination == "different_page":
        return BuildBoundaryResolution(disposition="different_destination")
    if judgment.destination == "unclear":
        return BuildBoundaryResolution(disposition="unresolved")
    if judgment.work == "unsupported_or_unclear":
        return BuildBoundaryResolution(disposition="unresolved")
    if judgment.work != "place_paragraph":
        return BuildBoundaryResolution(disposition=judgment.work)
    if judgment.insertion_location == "unclear":
        return BuildBoundaryResolution(disposition="unresolved")
    if judgment.insertion_location in {"unstated", "current_caret"}:
        # Passage and heading votes describe existing anchors. They cannot choose
        # a different location when the request leaves it open or names the caret.
        if (caret_target is None or judgment.destination != "current_page"
                or judgment.relation != "unresolved"):
            return BuildBoundaryResolution(disposition="unresolved")
        return BuildBoundaryResolution(disposition="unique", target=caret_target)
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
