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
    r"^\s*(?:(?:can|could|would|will)\s+you\s+|I\s+(?:want|would like)\s+you\s+to\s+)?"
    r"(?:please\s+)?(?:move|shift|slide|relocate|transfer|put|place)\b",
    re.IGNORECASE,
)
_DESTINATION_START = re.compile(
    r"\s+(?:into\s+|to\s+|(?:one\s+slot\s+)?right(?:\s+(?:by\s+)?one\s+slot)?[.!?]?\s*$)",
    re.IGNORECASE,
)
_RIGHT_DIRECTION = re.compile(r"\bright\b", re.IGNORECASE)
_OTHER_ROW = re.compile(r"\b(?:another|different|other|next|previous)\s+row\b", re.IGNORECASE)
_ROW_QUALIFIER = re.compile(
    r"\b(?:in|of|on(?!\s+(?:the|its)\s+right\b))\s+([^.!?]+)", re.IGNORECASE,
)
_CURRENT_ROW = re.compile(r"(?:(?:the|this)\s+)?(?:same|current)\s+row", re.IGNORECASE)
_MULTIPLE_SLOTS = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|(?:[2-9]|\d{2,}))\s+(?:slots|columns)\b", re.IGNORECASE)
_ALTERNATIVE_DIRECTION = re.compile(
    r"\b(?:left|above|below|instead|or|far|rightmost|last|outermost|and then)\b",
    re.IGNORECASE,
)


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
        number = 0
        for node, item in zip(editor["content"], layout.items, strict=True):
            if not isinstance(item, Row):
                continue
            number += 1
            row_context = _semantic_text(node)[:500]
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
        return cls(capture, question, layout.fingerprint(), tuple(occurrences), tuple(other_media.elements()))

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
        if _OTHER_ROW.search(self.question) or answers["image_move_destination"] == "different_row":
            return BuildImageMoveNomination("different_row")
        if answers["image_move_destination"] != "same_row_right":
            return BuildImageMoveNomination("unsupported")
        object_and_destination = self.question[active.end():]
        split = _DESTINATION_START.search(object_and_destination)
        if split is None:
            return BuildImageMoveNomination("unresolved")
        object_words = _phrase(object_and_destination[:split.start()])
        destination = object_and_destination[split.start():]
        if (not _RIGHT_DIRECTION.search(destination) or _ALTERNATIVE_DIRECTION.search(destination)
                or _MULTIPLE_SLOTS.search(object_and_destination)):
            return BuildImageMoveNomination("unsupported")
        row_qualifier = _ROW_QUALIFIER.search(destination)
        if row_qualifier is not None and not _CURRENT_ROW.fullmatch(row_qualifier.group(1).strip()):
            return BuildImageMoveNomination("different_row")
        alias = answers["image_move_occurrence"]
        if alias in {"ambiguous", "missing"}:
            return BuildImageMoveNomination(alias)
        chosen = next(item for item in self.occurrences if item.alias == alias)
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
            if conflicts and (
                not _mentions(object_words, chosen_words)
                or any(_mentions(object_words, _phrase(alt)) for alt in conflicts)
            ):
                return BuildImageMoveNomination("ambiguous")
        if chosen.destination_slot is None or chosen.destination != "empty_right":
            return BuildImageMoveNomination(chosen.destination)
        return BuildImageMoveNomination("ready", BuildImageMovePlacement(
            basis=self.capture.basis, presentation_sha256=self.presentation_sha256,
            row_id=chosen.row_id, source_slot_id=chosen.source_slot,
            destination_slot_id=chosen.destination_slot, image_block_id=chosen.block.id,
        ))
