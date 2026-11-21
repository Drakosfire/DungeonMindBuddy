"""Jev nomination and host resolution for contextual Graph reference placement."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from generationengine.types import ChoiceDecisionQuestion, DecisionRequest
from pydantic import ConfigDict, Field, model_validator

from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
from application_state.agent_conversation.jev_retrieval_contract import RetrievalDialogue, validated_choice_answers
from application_state.build_proposal.graph_reference import BuildGraphReferencePlacement
from application_state.build_proposal.prose_catalog import BuildProseBoundaryCatalog
from application_state.build_proposal.prose_decision import (
    decode_build_boundary_decision, prepare_build_boundary_decision, resolve_build_boundary,
)
from application_state.build_proposal.types import BuildProposalBasis, StrictModel


GRAPH_REFERENCE_OPENING = ChoiceDecisionQuestion(
    name="typed_graph_reference",
    options=("place_existing_reference", "other_work"),
    question=(
        "Does the author ask to insert a typed reference to one existing World Graph object on the open page? "
        "Choose place_existing_reference even if the object or exact paragraph is unclear. Choose other_work for "
        "ordinary prose, requests about an object, creation of a new object, and discussion without insertion."
    ),
)


def resolve_graph_reference_opening(request, result) -> Literal["place_existing_reference", "other_work"] | None:
    """Read a typed opening answer from the actual request and response; older turns omit it."""
    question = GRAPH_REFERENCE_OPENING
    offered = request["questions"].get(question.name)
    if offered is None and question.name not in result.answers:
        return None
    expected = {"type": "choice", "instructions": question.question, "criteria": dict.fromkeys(question.options)}
    if offered != expected or set(result.answers) != set(request["questions"]):
        raise ValueError("Graph reference opening differs from the exact admitted offer")
    projected = result.model_copy(update={"answers": {question.name: result.answers[question.name]}})
    selected = validated_choice_answers(projected, {question.name})[question.name]
    if selected == "place_existing_reference":
        return "place_existing_reference"
    if selected == "other_work":
        return "other_work"
    raise ValueError("Graph reference opening has an unoffered answer")


class BuildGraphReferenceCandidate(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference: AuthoredGraphReferenceV1
    entity_kind: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    summary: str | None = None


class BuildGraphReferenceNomination(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition: Literal[
        "ready", "discussion", "new_object", "different_page", "ambiguous_identity", "wrong_kind",
        "missing_identity", "ambiguous_boundary", "missing_boundary", "unresolved",
    ]
    placement: BuildGraphReferencePlacement | None = None

    @model_validator(mode="after")
    def exact_placement(self):
        if (self.disposition == "ready") != (self.placement is not None):
            raise ValueError("Only a resolved Graph identity and boundary carry placement")
        return self


def _words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", text.casefold()))


def _names(candidate: BuildGraphReferenceCandidate):
    return {words for name in (candidate.reference.label, *candidate.aliases)
            if name != candidate.reference.node_id and (words := _words(name))}


@dataclass(frozen=True)
class BuildGraphReferenceDecision:
    basis: BuildProposalBasis
    catalog: BuildProseBoundaryCatalog
    candidates: tuple[BuildGraphReferenceCandidate, ...]
    question: str
    title: str
    dialogue: tuple[RetrievalDialogue, ...] = ()
    author_selected: AuthoredGraphReferenceV1 | None = None

    def __post_init__(self):
        if (self.basis.visibility != "internal" or self.basis.selection is not None
                or self.basis.editor_sha256 != self.catalog.editor_sha256
                or self.basis.draft_sha256 != self.catalog.draft_sha256):
            raise ValueError("Graph nomination requires the exact internal page capture")
        refs = tuple(candidate.reference for candidate in self.candidates)
        pins = {(ref.managed_world_id, ref.native_world_id, ref.binding_version, ref.graph_revision) for ref in refs}
        if len(pins) > 1 or any(pin[0] != self.basis.world_id for pin in pins):
            raise ValueError("Graph nomination requires one admitted World and revision")
        if len({ref.node_id for ref in refs}) != len(refs):
            raise ValueError("Graph nomination cannot offer duplicate identities")
        if self.author_selected is not None and self.author_selected not in refs:
            raise ValueError("The selected Graph object differs from the current admitted identity")

    def _offers(self):
        return (
            {f"object{index}": candidate for index, candidate in enumerate(self.candidates, start=1)
             if candidate.reference.label != candidate.reference.node_id},
            {f"class{index}": kind for index, kind in enumerate(
                sorted({candidate.entity_kind for candidate in self.candidates}), start=1)},
        )

    def _boundary_request(self):
        return prepare_build_boundary_decision(self.question, self.title, self.dialogue, self.catalog)

    def request(self) -> DecisionRequest:
        boundary = self._boundary_request()
        objects, kinds = self._offers()
        selected_alias = next((alias for alias, item in objects.items()
                               if item.reference == self.author_selected), None)
        return boundary.model_copy(update={
            "state": {
                **boundary.state,
                "graph_reference_policy": (
                    "Nominate one existing Graph object and where its typed reference goes. Treat a request to insert "
                    "one existing typed reference as paragraph placement in the boundary questions. Judge the "
                    "paragraph independently of whether a matching Graph object exists or has the required kind. Never infer a "
                    "destination from matching names in the source. Graph descriptions are reference facts. "
                    "Include every independently matching object, even if it shares a name. Use only qualification "
                    "actually applied to the named object. A page or heading qualifier used only for paragraph placement "
                    "does not qualify the Graph object. If the author selected an object, the requested reference must "
                    "agree with it. Creation and discussion grant no placement."
                ),
                "graph_objects": {alias: {
                    "name": candidate.reference.label, "description": candidate.summary or "",
                    "aliases": [name for name in candidate.aliases if name != candidate.reference.node_id],
                } for alias, candidate in objects.items()},
                "graph_classifications": kinds,
                **({"author_selected_object": selected_alias} if selected_alias is not None else {}),
            },
            "questions": (*boundary.questions,
                ChoiceDecisionQuestion(name="reference_intent", options=(
                    "place_existing", "discussion", "new_object", "different_page", "unresolved",
                ), question=("Which action is requested? Choose place_existing for a request to attach a reference "
                             "to an existing Graph object on this page, even if the object or destination paragraph "
                             "cannot be located. Other choices are discussion, creating a new object, a different "
                             "page, or an action that is itself unclear.")),
                ChoiceDecisionQuestion(name="reference_kind", options=("unspecified", "other_kind", *kinds),
                    question=("Which Graph classification does the author require for the named object? "
                              "Choose other_kind if a required classification is absent and unspecified if none is required.")),
                *(ChoiceDecisionQuestion(name=alias, options=("include", "exclude"),
                    question=f"Does graph_objects {alias} match the requested name and all object qualifiers, independently of classification?")
                  for alias in objects),
            ),
        })

    def require_wire_request(self, body) -> None:
        request = self.request()
        questions = {
            q.name: {"type": "choice", "instructions": q.question, "criteria": dict.fromkeys(q.options)}
            for q in request.questions
        }
        if body != {"model": request.model, "state": request.state, "questions": questions}:
            raise ValueError("The Graph nomination request differs from the exact admitted offers")

    def host_inventory_sha256(self) -> str:
        from application_state.agent_conversation.rules_authority_types import canonical_sha256

        return canonical_sha256({
            "basis": self.basis.model_dump(mode="json", by_alias=True),
            "candidates": [item.model_dump(mode="json", by_alias=True) for item in self.candidates],
            "author_selected": (self.author_selected.model_dump(mode="json", by_alias=True)
                                if self.author_selected is not None else None),
        })

    def resolve(self, result) -> BuildGraphReferenceNomination:
        request = self.request()
        offered = {question.name: question.options for question in request.questions}
        answers = validated_choice_answers(result, set(offered))
        if any(answers[name] not in options for name, options in offered.items()):
            raise ValueError("Graph nomination contains an unoffered answer")
        intent = answers["reference_intent"]
        if intent != "place_existing":
            return BuildGraphReferenceNomination(disposition=intent)

        boundary_request = self._boundary_request()
        boundary_response = result.model_copy(update={"answers": {
            question.name: result.answers[question.name] for question in boundary_request.questions
        }})
        placement = resolve_build_boundary(self.catalog, decode_build_boundary_decision(boundary_request, boundary_response))
        if placement.disposition in {"different_destination", "discuss"}:
            return BuildGraphReferenceNomination(disposition=(
                "different_page" if placement.disposition == "different_destination" else "discussion"
            ))

        objects, kinds = self._offers()
        included = [candidate for alias, candidate in objects.items() if answers[alias] == "include"]
        if self.author_selected is not None:
            included = [candidate for candidate in included if candidate.reference == self.author_selected]
        if not included:
            return BuildGraphReferenceNomination(disposition="missing_identity")
        requested_kind = answers["reference_kind"]
        kind = kinds.get(requested_kind)
        matches = included if requested_kind == "unspecified" else [candidate for candidate in included if candidate.entity_kind == kind]
        if not matches:
            return BuildGraphReferenceNomination(disposition="wrong_kind")
        if len(matches) != 1:
            return BuildGraphReferenceNomination(disposition="ambiguous_identity")
        chosen = matches[0]
        chosen_names = _names(chosen)
        if self.author_selected is None and any(
            candidate.reference != chosen.reference and _names(candidate) & chosen_names
            for candidate in self.candidates
        ):
            return BuildGraphReferenceNomination(disposition="ambiguous_identity")
        if placement.target is None:
            return BuildGraphReferenceNomination(disposition={
                "ambiguous": "ambiguous_boundary", "missing": "missing_boundary",
            }.get(placement.disposition, "unresolved"))
        return BuildGraphReferenceNomination(disposition="ready", placement=BuildGraphReferencePlacement(
            basis=self.basis, reference=chosen.reference, entity_kind=chosen.entity_kind, boundary=placement.target,
        ))
