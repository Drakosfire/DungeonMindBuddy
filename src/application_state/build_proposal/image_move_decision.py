"""Semantic Jev offers for one host-bound move of an existing Build image."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Literal
from uuid import UUID

from generationengine.types import ChoiceDecisionQuestion, DecisionResult
from pydantic import ConfigDict, Field, model_validator

from application_state.agent_conversation.plan_authoring import strict_json
from application_state.agent_conversation.jev_retrieval_contract import validated_choice_answers
from application_state.build_proposal.image_move import BuildImageMovePlacement
from application_state.build_proposal.image_move_layout import require_build_image_layout
from application_state.build_proposal.types import BuildImageMoveDisposition, BuildProposalBasis, StrictModel
from application_state.content.page_presentation import BlockBinding, Identifier, PagePresentation, Row
from application_state.content.types import sha256_utf8


class BuildImageMoveCapture(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    basis: BuildProposalBasis
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=1)
    editor_json: str = Field(min_length=1, max_length=1_000_000)
    author_selected_block_id: Identifier | None = None

    @model_validator(mode="after")
    def exact_editor(self):
        if (
            self.basis.visibility != "internal"
            or self.basis.content_sha256 != self.basis.draft_sha256
            or sha256_utf8(self.editor_json) != self.basis.editor_sha256
        ):
            raise ValueError("Image movement requires the exact saved internal Page capture")
        return self


@dataclass(frozen=True)
class _Occurrence:
    alias: str
    block: BlockBinding
    asset: str
    alt: str
    row_id: str
    row_number: int
    row_context: str
    source_column: int
    source_slot: str
    destination_slot: str | None
    destination: Literal["empty_right", "occupied", "unavailable", "changes_reading_order"]


OPENING_STATE_KEY = "image_move"


@dataclass(frozen=True)
class BuildImageMoveNomination:
    disposition: BuildImageMoveDisposition
    placement: BuildImageMovePlacement | None = None


_ACTIVE_MOVE = re.compile(
    r"^\s*(?:(?P<location>(?:in|on|within|under|for)\s+[^,.;!?]{1,180}),\s*)?"
    r"(?:(?:can|could|would|will)\s+(?:you|we|buddy)\s+|"
    r"(?:I\s+(?:want|would like)|I['’]d\s+like)\s+(?:you\s+)?to\s+|let['’]s\s+)?"
    r"(?:please\s+)?(?:move|shift|slide|relocate|transfer|put|place|reposition|nudge|push|drag)\b",
    re.IGNORECASE,
)
_DESTINATION_START = re.compile(
    r"\s+(?:into\s+|onto\s+|(?<!next\s)(?<!close\s)to\s+|"
    r"(?:(?:one|a)\s+(?:slot|column)\s+)?right(?=\s+(?:by|one|a|in|within|on|from)\b|[,.!?]|\s*$))",
    re.IGNORECASE,
)
_RIGHT_DIRECTION = re.compile(r"\bright(?:wards?)?\b", re.IGNORECASE)
_OTHER_ROW = re.compile(r"\b(?:another|different|other|next|previous)\s+row\b", re.IGNORECASE)
_ROW_PREPOSITION = re.compile(r"\b(?:in|into|on|onto|to|of|from|within|inside)\b", re.IGNORECASE)
_ROW_QUALIFIER = re.compile(r"\s*([^,.!?;]{1,110}?)\s+row\b", re.IGNORECASE)
_NUMBERED_ROW = re.compile(r"\s*(?:the\s+)?row\s+(?:number\s+)?([1-9]\d{0,5})\b", re.IGNORECASE)
_ORDINAL_ROWS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6}
_HEADING_REFERENCE = re.compile(r"\b(?:under|beneath|below|beside|next\s+to)\s+([^,.;!?]+)\s*$", re.IGNORECASE)
_PAGE_QUALIFIER = re.compile(r"\s*([^,.!?;]{1,110}?)\s+page\b", re.IGNORECASE)
_CURRENT_ROW = re.compile(r"(?:(?:the|its|that|this)\s+)?(?:same|current|original)|(?:this|its)\s*", re.IGNORECASE)
_RIGHT_OF = re.compile(r"\bright\s+of\s+([^,.!?;]+)", re.IGNORECASE)
_CURRENT_POSITION = re.compile(
    r"(?:it|that|the\s+image|where\s+it\s+is(?:\s+now)?|its\s+(?:(?:own|current|original)\s+)?(?:place|slot|column|position))",
    re.IGNORECASE,
)
_MULTIPLE_SLOTS = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|(?:[2-9]|\d{2,}))\s+(?:slots|columns)\b", re.IGNORECASE)
_ALTERNATIVE_DIRECTION = re.compile(
    r"\b(?:left|above|below|instead|or|far|rightmost|last|outermost|elsewhere|and then)\b|;",
    re.IGNORECASE,
)
_CONDITIONAL = re.compile(r"\b(?:if|assuming|provided|hypothetically)\b", re.IGNORECASE)


def _semantic_text(node: dict) -> str:
    if isinstance(node.get("text"), str):
        return node["text"]
    return " ".join(filter(None, (_semantic_text(child) for child in node.get("content", []))))


def _all_media(node: dict):
    if node.get("type") == "mediaImage":
        yield node["attrs"]["assetId"], node["attrs"]["alt"]
    for child in node.get("content", []):
        yield from _all_media(child)


def _phrase(text: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", text.casefold()))


def _mentions(text: str, phrase: str) -> bool:
    return bool(phrase and f" {phrase} " in f" {text} ")


@dataclass(frozen=True)
class BuildImageMoveDecision:
    capture: BuildImageMoveCapture
    question: str
    presentation_sha256: str
    occurrences: tuple[_Occurrence, ...]
    other_media: tuple[tuple[str, str], ...]
    row_labels: dict[str, set[int]]
    row_media_counts: dict[int, int]

    @classmethod
    def from_saved(
        cls, capture: BuildImageMoveCapture, question: str, markdown: str, layout: PagePresentation,
    ) -> BuildImageMoveDecision:
        if sha256_utf8(markdown) != capture.basis.content_sha256:
            raise ValueError("The saved Page changed before image nomination")
        layout.checked(markdown)
        editor = strict_json(capture.editor_json)
        require_build_image_layout(editor, markdown, layout)
        occurrences = []
        row_labels: dict[str, set[int]] = {}
        row_media_counts: dict[int, int] = {}
        number = 0
        for node, item in zip(editor["content"], layout.items, strict=True):
            if not isinstance(item, Row):
                continue
            number += 1
            row_media_counts[number] = sum(1 for _ in _all_media(node))
            row_context = _semantic_text(node)[:500]
            for slot_node in node["content"]:
                for block in slot_node.get("content", []):
                    if block["type"] == "heading" and (label := _phrase(_semantic_text(block))):
                        row_labels.setdefault(label, set()).add(number)
            for column, (slot_node, slot) in enumerate(zip(node["content"], item.slots, strict=True)):
                right = item.slots[column + 1] if column + 1 < len(item.slots) else None
                for index, (block_node, block) in enumerate(zip(slot_node.get("content", []), slot.blocks, strict=True)):
                    children = block_node.get("content", [])
                    if not isinstance(block, BlockBinding) or len(children) != 1 or children[0]["type"] != "mediaImage":
                        continue
                    attrs = children[0]["attrs"]
                    destination = "unavailable" if right is None else (
                        "occupied" if right.blocks else
                        "changes_reading_order" if index + 1 != len(slot.blocks) else "empty_right"
                    )
                    occurrences.append(_Occurrence(
                        alias=f"image{len(occurrences)+1}", block=block,
                        asset=attrs["assetId"], alt=attrs["alt"], row_id=item.id,
                        row_number=number, row_context=row_context, source_column=column + 1,
                        source_slot=slot.id, destination_slot=right.id if right else None, destination=destination,
                    ))
        if capture.author_selected_block_id is not None and not any(
            item.block.id == capture.author_selected_block_id for item in occurrences
        ):
            raise ValueError("Selected image differs from the saved Page occurrence")
        other_media = Counter(_all_media(editor)) - Counter((item.asset, item.alt) for item in occurrences)
        return cls(capture, question, layout.fingerprint(), tuple(occurrences), tuple(other_media.elements()),
                   row_labels, row_media_counts)

    @property
    def selected(self) -> str | None:
        return next((x.alias for x in self.occurrences if x.block.id == self.capture.author_selected_block_id), None)

    def semantic_state(self) -> dict:
        return {
            "existing_occurrences": {
                item.alias: {"alt":item.alt, "row_description":item.row_context,
                             "row_number":item.row_number, "source_column":item.source_column}
                for item in self.occurrences
            },
            **({"author_selected_occurrence": self.selected} if self.selected else {}),
        }

    def questions(self) -> tuple[ChoiceDecisionQuestion, ...]:
        return (
            ChoiceDecisionQuestion(name="image_move_intent", options=("move_existing", "other", "unresolved"),
                question="Is the author actually asking to move an existing image occurrence? Discussion, hypotheticals, creation and advice are other."),
            ChoiceDecisionQuestion(name="image_move_destination", options=("same_row_right", "different_row", "unsupported", "unresolved"),
                question=("Which destination does the author request, independent of availability? same_row_right is the "
                          "immediately adjacent slot to the image's right in its current row. A named different row is different_row.")),
            ChoiceDecisionQuestion(name="image_move_occurrence", options=("ambiguous", "missing", *(item.alias for item in self.occurrences)),
                question=("Which existing image occurrence does the author identify? Use its alt text and row description. "
                          "A deliberate selection identifies 'this image'. Choose ambiguous if two fit. "
                          "An unrelated caret and destination eligibility do not distinguish an image.")),
        )

    def require_opening_offer(self, request: dict) -> None:
        questions = self.questions()
        if (request.get("state", {}).get("user_question") != self.question
                or request.get("state", {}).get("interaction", {}).get(OPENING_STATE_KEY) != self.semantic_state()
                or any(request.get("questions", {}).get(q.name) != {
                    "type": "choice", "instructions": q.question, "criteria": dict.fromkeys(q.options),
                } for q in questions)):
            raise ValueError("Image movement differs from the exact admitted opening offer")

    def opening_answers(self, request: dict, response: DecisionResult) -> dict[str, str]:
        self.require_opening_offer(request)
        if set(request["questions"]) != set(response.answers):
            raise ValueError("Image movement requires the complete opening response")
        options = {q.name: q.options for q in self.questions()}
        projected = response.model_copy(update={"answers": {name: response.answers[name] for name in options}})
        answers = validated_choice_answers(projected, set(options))
        if any(answer not in options[name] for name, answer in answers.items()):
            raise ValueError("Image move decision has an unoffered answer")
        return answers

    def resolve(self, answers: dict[str, str]) -> BuildImageMoveNomination:
        for question in self.questions():
            if answers.get(question.name) not in question.options:
                raise ValueError("Image move decision has an unoffered answer")
        active = _ACTIVE_MOVE.match(self.question)
        if answers["image_move_intent"] != "move_existing" or active is None:
            return BuildImageMoveNomination("discussion")
        object_and_destination = self.question[active.end():]
        location = active.group("location") or ""
        scope = f"{location}, {object_and_destination}"
        if _CONDITIONAL.search(scope):
            return BuildImageMoveNomination("discussion")
        if answers["image_move_destination"] == "different_row":
            return BuildImageMoveNomination("different_row")
        if answers["image_move_destination"] != "same_row_right":
            return BuildImageMoveNomination("unsupported")
        split = _DESTINATION_START.search(object_and_destination)
        if split is None:
            return BuildImageMoveNomination("unresolved")
        object_text = object_and_destination[:split.start()]
        object_words = _phrase(object_text)
        destination = object_and_destination[split.start():]
        if _OTHER_ROW.search(scope):
            return BuildImageMoveNomination("different_row")
        if (not _RIGHT_DIRECTION.search(destination) or _ALTERNATIVE_DIRECTION.search(destination)
                or _MULTIPLE_SLOTS.search(object_and_destination)):
            return BuildImageMoveNomination("unsupported")
        alias = answers["image_move_occurrence"]
        if alias in {"ambiguous", "missing"}:
            return BuildImageMoveNomination(alias)
        chosen = next(item for item in self.occurrences if item.alias == alias)
        # A named row can occur before the right-slot wording. Require it to
        # identify the nominated source row anywhere in the action clause.
        explicitly_named_row = False
        for fragment in _ROW_PREPOSITION.split(scope)[1:]:
            page_qualifier = _PAGE_QUALIFIER.match(fragment)
            if page_qualifier is not None and not _CURRENT_ROW.fullmatch(page_qualifier.group(1).strip()):
                return BuildImageMoveNomination("unsupported")
            number = _NUMBERED_ROW.match(fragment)
            if number is not None:
                if int(number.group(1)) != chosen.row_number:
                    return BuildImageMoveNomination("different_row")
                explicitly_named_row = True
            row_qualifier = _ROW_QUALIFIER.match(fragment)
            if row_qualifier is None:
                continue
            raw = row_qualifier.group(1).strip()
            label = re.sub(r"^the\s+", "", _phrase(raw))
            if not _CURRENT_ROW.fullmatch(raw):
                if _ORDINAL_ROWS.get(label) != chosen.row_number and self.row_labels.get(label) != {chosen.row_number}:
                    return BuildImageMoveNomination("different_row")
                explicitly_named_row = True
        for text in (location, object_text):
            heading = _HEADING_REFERENCE.search(text)
            if heading is not None:
                reference = _phrase(heading.group(1))
                label = re.sub(r"^the\s+|\s+heading$", "", reference)
                owners = self.row_labels.get(label)
                if owners is not None and chosen.row_number not in owners:
                    return BuildImageMoveNomination("ambiguous")
                if owners is None and reference.endswith(" heading"):
                    return BuildImageMoveNomination("missing")
                explicitly_named_row = explicitly_named_row or owners == {chosen.row_number}
        right_of = _RIGHT_OF.search(destination)
        if right_of is not None:
            reference = _ROW_PREPOSITION.split(right_of.group(1), maxsplit=1)[0].strip()
            if not _CURRENT_POSITION.fullmatch(reference):
                return BuildImageMoveNomination("unsupported")
        if self.selected is not None and self.selected != alias:
            return BuildImageMoveNomination("ambiguous")
        chosen_words = _phrase(chosen.alt)
        competing_names = {
            _phrase(item.alt) for item in self.occurrences if item.alias != alias
        } | {_phrase(alt) for _, alt in self.other_media}
        if any(name != chosen_words and _mentions(object_words, name)
               and not (_mentions(object_words, chosen_words) and _mentions(chosen_words, name))
               for name in competing_names):
            return BuildImageMoveNomination("ambiguous")
        if self.selected is None:
            conflicts = [
                item.alt for item in self.occurrences
                if item.alias != alias and (item.asset == chosen.asset or _phrase(item.alt) == _phrase(chosen.alt))
            ]
            conflicts.extend(alt for asset, alt in self.other_media
                             if asset == chosen.asset or _phrase(alt) == _phrase(chosen.alt))
            direct = _mentions(object_words, chosen_words) and not any(
                _mentions(object_words, _phrase(alt)) or _mentions(_phrase(alt), chosen_words)
                for alt in conflicts
            )
            if conflicts and not (direct or (explicitly_named_row and self.row_media_counts[chosen.row_number] == 1)):
                return BuildImageMoveNomination("ambiguous")
        if chosen.destination_slot is None or chosen.destination != "empty_right":
            return BuildImageMoveNomination(chosen.destination)
        return BuildImageMoveNomination("ready", BuildImageMovePlacement(
            basis=self.capture.basis, presentation_sha256=self.presentation_sha256,
            row_id=chosen.row_id, source_slot_id=chosen.source_slot,
            destination_slot_id=chosen.destination_slot, image_block_id=chosen.block.id,
        ))
