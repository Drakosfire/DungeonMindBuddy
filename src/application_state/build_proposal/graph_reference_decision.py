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


_RETAINED_GRAPH_REFERENCE_OPENING = ChoiceDecisionQuestion(
    name="typed_graph_reference",
    options=("place_existing_reference", "other_work"),
    question=(
        "Does the author ask to insert a typed reference to one existing World Graph object on the open page? "
        "Choose place_existing_reference even if the object or exact paragraph is unclear. Choose other_work for "
        "ordinary prose, requests about an object, creation of a new object, and discussion without insertion."
    ),
)
GRAPH_REFERENCE_OPENING = _RETAINED_GRAPH_REFERENCE_OPENING.model_copy(update={"question": (
    "Does the author ask to insert a typed reference to one existing World Graph object? Choose "
    "place_existing_reference even if the object, paragraph, or destination page is unclear, or if the author "
    "explicitly names a different page. The placement decision handles those destinations. Choose other_work for "
    "ordinary prose, questions about a reference without insertion, and creation of a new Graph object."
)})


def resolve_graph_reference_opening(request, result) -> Literal["place_existing_reference", "other_work"] | None:
    """Read a typed opening answer from the actual request and response; older turns omit it."""
    question = GRAPH_REFERENCE_OPENING
    offered = request["questions"].get(question.name)
    if offered is None and question.name not in result.answers:
        return None
    expected = tuple({"type": "choice", "instructions": variant.question, "criteria": dict.fromkeys(variant.options)}
                     for variant in (question, _RETAINED_GRAPH_REFERENCE_OPENING))
    if offered not in expected or set(result.answers) != set(request["questions"]):
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


def _placement_clause(question: str):
    request = re.sub(r''' "[^"\n]*" | “[^”\n]*” | ‘[^’\n]*’ | (?<!\w)'[^'\n]*' ''',
                     " ", question, flags=re.VERBOSE)
    return re.fullmatch(
        r"\s*(?:please\s+)?(?P<action>add|insert|place|put|link|reference)\s+"
        r"(?P<object>[^.,!?;:\n]+?)\s+(?:(?:just|right|immediately)\s+)?"
        r"(?P<relation>before|after)\s+(?P<anchor>[^.,!?;:\n]+?)\s*[.!]?\s*",
        request, flags=re.IGNORECASE,
    )


def _has_distinguishing_expression(question, chosen, candidates, kind):
    clause = _placement_clause(question)
    if clause is None:
        return False
    expression = re.sub(
        r"^(?:(?:a|an|the|typed|existing|graph)\s+)*(?:reference|link)\s+to\s+",
        "", clause["object"], flags=re.IGNORECASE,
    )
    expression = _words(expression)
    while expression and expression[0] in {"a", "an", "the", "existing"}:
        expression = expression[1:]
    if not expression or {"not", "except", "or", "and", "instead", "without"} & set(expression):
        return False
    eligible = set()
    for candidate in candidates:
        description = _words(candidate.summary or "")
        for name in _names(candidate):
            if expression[:len(name)] != name:
                continue
            qualifier = expression[len(name):]
            literal_kind = kind == candidate.entity_kind and qualifier == _words(candidate.entity_kind)
            literal_description = len(qualifier) >= 3 and any(
                description[index:index + len(qualifier)] == qualifier
                for index in range(len(description) - len(qualifier) + 1)
            )
            if not qualifier or literal_kind or literal_description:
                eligible.add(candidate.reference.node_id)
    return eligible == {chosen.reference.node_id}


def _explicit_ordinal_target(question, catalog, occurrence, relation):
    """Corroborate an occurrence vote with a literal paragraph ordinal and section."""
    chosen = next((item for item in catalog.passages if item.alias == occurrence), None)
    if chosen is None or not chosen.headings:
        return None
    clause = _placement_clause(question)
    if clause is None or clause["relation"].casefold() != relation:
        return None
    referent = clause["object"]
    if {"not", "except", "instead", "unless", "without", "avoid", "whether", "saying", "quote"} & set(_words(referent)):
        return None
    if clause["action"].casefold() not in {"link", "reference"} and not re.fullmatch(
        r"(?:(?:a|an|the|typed|existing|graph|selected)\s+)*(?:reference|link)(?:\s+to\s+.+)?"
        r"|(?:the|an?)\s+(?:existing|selected)\s+.+\s+(?:reference|link)",
        referent, flags=re.IGNORECASE,
    ):
        return None
    heading = re.escape(chosen.headings[-1])
    mention = re.fullmatch(
        rf"(?:the\s+)?(first|second|third|last|[1-9][0-9]{{0,2}}(?:st|nd|rd|th))"
        rf"\s+paragraph\s+(?:of|in|under)\s+(?:the\s+)?{heading}(?:\s+section)?",
        clause["anchor"], flags=re.IGNORECASE,
    )
    if mention is None:
        return None
    # Repeated section names and gaps can hide another heading or non-prose
    # content, so a catalog ordinal must belong to one contiguous section.
    if len({item.headings for item in catalog.passages if item.headings and
            item.headings[-1].casefold() == chosen.headings[-1].casefold()}) != 1:
        return None
    section = [item for item in catalog.passages if item.headings == chosen.headings]
    if any(left.after != right.before for left, right in zip(section, section[1:])):
        return None
    ordinal = mention[1].casefold()
    known = {"first": 0, "second": 1, "third": 2, "last": len(section) - 1}
    index = known[ordinal] if ordinal in known else int(ordinal[:-2]) - 1
    if index >= len(section) or section[index] != chosen:
        return None
    return catalog.target(occurrence, "insert_before" if relation == "before" else "insert_after")


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
        passages = {text: alias for alias, text in boundary.state["existing_passages"].items()}
        headings = {tuple(path): alias for alias, path in boundary.state["existing_heading_paths"].items()}
        paragraph_order = [
            {"occurrence": item.alias, "passage": passages[item.passage], "section": headings[item.headings]}
            for item in self.catalog.passages
        ]
        boundary_questions = tuple(
            question.model_copy(update={"question": (
                "Which heading restriction applies to the anchor paragraph? Choose unscoped when no heading "
                "or section is named, including when the author identifies a paragraph by its words or subject. "
                "Choose named for an explicit section, even if it is missing. Choose unresolved only for a heading "
                "reference whose meaning cannot be determined. The Graph object's own location is never a heading restriction."
            )}) if question.name == "scope" else question
            for question in boundary.questions
        )
        selected_alias = next((alias for alias, item in objects.items()
                               if item.reference == self.author_selected), None)
        return boundary.model_copy(update={
            "state": {
                **boundary.state,
                "paragraph_order": paragraph_order,
                "graph_reference_policy": (
                    "Nominate one existing Graph object and where its typed reference goes. Treat a request to insert "
                    "one existing typed reference as paragraph placement in the boundary questions. Judge the "
                    "paragraph independently of whether a matching Graph object exists or has the required kind. "
                    "paragraph_order lists the existing paragraph occurrences in reading order using the same passage and section "
                    "aliases as the questions. Use the order only when the author specifies a position such as the first paragraph "
                    "under a heading. A paragraph identified by its subject does not require a heading. Never infer a "
                    "destination from matching names in the source. Graph descriptions are reference facts. "
                    "Include every independently matching object, even if it shares a name. Use only qualification "
                    "actually applied to the named object. A page or heading qualifier used only for paragraph placement "
                    "does not qualify the Graph object. If the author selected an object, the requested reference must "
                    "agree with it. The current request's object type and exclusions still apply to a selected object. "
                    "Read type constraints from the request independently of the available objects. Creation and discussion grant no placement."
                ),
                "graph_objects": {alias: {
                    "name": candidate.reference.label, "description": candidate.summary or "",
                    "aliases": [name for name in candidate.aliases if name != candidate.reference.node_id],
                } for alias, candidate in objects.items()},
                "graph_classifications": kinds,
                **({"author_selected_object": selected_alias} if selected_alias is not None else {}),
            },
            "questions": (*boundary_questions,
                ChoiceDecisionQuestion(name="anchor_occurrence", options=("missing", "ambiguous",
                    *(item.alias for item in self.catalog.passages)),
                    question=("Which single paragraph occurrence is the author's anchor? Use paragraph_order to join "
                              "each occurrence to its passage and section. Select the exact occurrence only if it is "
                              "uniquely identified by the request. Choose ambiguous when more than one fits and "
                              "missing when none fits. The reference object, the proposed insertion, and the editor "
                              "caret do not identify the anchor.")),
                ChoiceDecisionQuestion(name="reference_intent", options=(
                    "place_existing", "discussion", "new_object", "different_page", "unresolved",
                ), question=("Which action is requested? Choose place_existing for a request to attach a reference "
                             "to an existing Graph object on this page, even if the object or destination paragraph "
                             "cannot be located. Other choices are discussion, creating a new object, a different "
                             "page, or an action that is itself unclear.")),
                ChoiceDecisionQuestion(name="reference_kind", options=("unspecified", "other_kind", *kinds),
                    question=("Read the user's words before considering what is available. Which classification must the referenced "
                              "object have? Choose its graph_classifications alias only if it is allowed by the request. If a "
                              "required classification is missing, or the request excludes the available classification, choose "
                              "other_kind. Choose unspecified only when the request permits an object of any classification. "
                              "An instruction to use a location instead of a threat requires a location even if a threat is selected.")),
                ChoiceDecisionQuestion(name="reference_kind_constraint", options=("any_type", "requires_or_excludes_type"),
                    question=("Ignoring what objects exist and what the author selected, does the user expressly require or rule "
                              "out a type for the object being referenced? For example 'as an existing location', 'use the "
                              "construct', and 'do not use a threat' all impose a type constraint. A location mentioned only "
                              "as the destination or heading is not a type constraint on the object.")),
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
        judgment = decode_build_boundary_decision(boundary_request, boundary_response)
        placement = resolve_build_boundary(self.catalog, judgment)
        if placement.disposition in {"different_destination", "discuss"}:
            return BuildGraphReferenceNomination(disposition=(
                "different_page" if placement.disposition == "different_destination" else "discussion"
            ))

        objects, kinds = self._offers()
        requested_kind = answers["reference_kind"]
        kind_constrained = answers["reference_kind_constraint"] == "requires_or_excludes_type"
        if self.author_selected is not None and kind_constrained and requested_kind != "unspecified":
            selected = next(item for item in self.candidates if item.reference == self.author_selected)
            if kinds.get(requested_kind) != selected.entity_kind:
                return BuildGraphReferenceNomination(disposition="wrong_kind")
        included = [candidate for alias, candidate in objects.items() if answers[alias] == "include"]
        if self.author_selected is not None:
            included = [candidate for candidate in included if candidate.reference == self.author_selected]
        if not included:
            return BuildGraphReferenceNomination(disposition="missing_identity")
        if requested_kind == "unspecified" and kind_constrained:
            return BuildGraphReferenceNomination(disposition="wrong_kind")
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
        ) and not _has_distinguishing_expression(
            self.question, chosen, self.candidates, kind,
        ):
            return BuildGraphReferenceNomination(disposition="ambiguous_identity")
        occurrence = answers["anchor_occurrence"]
        target = placement.target
        if target is not None and occurrence != target.alias.split(":", 1)[0]:
            return BuildGraphReferenceNomination(disposition="ambiguous_boundary")
        if placement.disposition == "ambiguous" and occurrence not in {"ambiguous", "missing"}:
            rows = request.state["paragraph_order"]
            if any(row["occurrence"] == occurrence and row["passage"] in judgment.passage_aliases
                   and (judgment.scope != "named" or row["section"] in judgment.scope_aliases)
                   for row in rows):
                target = _explicit_ordinal_target(self.question, self.catalog, occurrence, judgment.relation)
        if target is None:
            return BuildGraphReferenceNomination(disposition={
                "ambiguous": "ambiguous_boundary", "missing": "missing_boundary",
            }.get(placement.disposition, "unresolved"))
        return BuildGraphReferenceNomination(disposition="ready", placement=BuildGraphReferencePlacement(
            basis=self.basis, reference=chosen.reference, entity_kind=chosen.entity_kind, boundary=target,
        ))
