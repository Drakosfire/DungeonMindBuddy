"""Semantic Jev offers for one host-bound move of an existing Build image."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Literal

from generationengine.types import ChoiceDecisionQuestion, DecisionResult

from application_state.agent_conversation.plan_authoring import strict_json
from application_state.agent_conversation.jev_retrieval_contract import validated_choice_answers
from application_state.build_proposal.image_move import BuildImageMovePlacement
from application_state.build_proposal.image_move_capture import BuildImageMoveCapture
from application_state.build_proposal.image_move_layout import require_build_image_layout
from application_state.build_proposal.types import BuildImageMoveDisposition
from application_state.content.page_presentation import BlockBinding, PagePresentation, Row
from application_state.content.types import sha256_utf8


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
CONTEXTUAL_IDENTITY = "image_move_contextual_identity"
IMAGE_MOVE_AFFIRMATION = ChoiceDecisionQuestion(
    name="image_move_affirmation",
    options=("author_requests_move", "description_or_discussion", "unresolved"),
    question=(
        "Read only the author's sentence. Does it ask the editor to change where an existing image is placed? "
        "An imperative, a passive request, a desired placement stated as a direction, or an abbreviated "
        "image-and-slot instruction can request a move. Choose description_or_discussion for a description of "
        "where it is or was, advice, a hypothetical or a refusal to move. A requested destination alone "
        "does not prove that the author requests a change. Use unresolved when the desired action is unclear."
    ),
)


def contextual_identity_question(aliases) -> ChoiceDecisionQuestion:
    return ChoiceDecisionQuestion(
        name=CONTEXTUAL_IDENTITY,
        options=("ambiguous", "missing", "no_contextual_reference", *aliases),
        question=(
            "For repeated images, identify the source occurrence by the author's reference to nearby "
            "text. A paraphrase of distinct nearby prose can identify one occurrence. Use row_description "
            "and the part of the request that describes nearby content. Ignore position, slot, destination, "
            "and the shared image name. Use no_contextual_reference for an image name alone, missing for "
            "a reference to absent prose, and ambiguous when two contexts fit or the reference is unclear."
        ),
    )


@dataclass(frozen=True)
class BuildImageMoveNomination:
    disposition: BuildImageMoveDisposition
    placement: BuildImageMovePlacement | None = None


_ACTIVE_MOVE = re.compile(
    r"^\s*(?:(?P<location>(?:in|on|within|under|for)\s+[^,.;!?]{1,180}),\s*)?"
    r"(?:(?:can|could|would|will)\s+(?:you|we|buddy)\s+|"
    r"(?:I\s+(?:want|would like)|I['’]d\s+like)\s+(?:you\s+)?to\s+|let['’]s\s+)?"
    r"(?:please\s+)?(?:move|shift|slide|relocate|transfer|put|place|reposition|nudge|push|drag|scoot|bump|set|bring)\b",
    re.IGNORECASE,
)
_PASSIVE_MOVE = re.compile(
    r"^\s*(?:(?:can|could|would|will)\s+(?P<modal>(?:this|that|the|my|our|an?)\s+[^,.;!?]{1,180}?)\s+(?:please\s+)?be\s+|"
    r"(?:I\s+(?:want|would like)|I['’]d\s+like)\s+(?P<wanted>(?:this|that|the|my|our|an?)\s+[^,.;!?]{1,180}?)"
    r"\s+(?:to\s+be\s+)?)"
    r"(?:moved|shifted|slid|relocated|transferred|put|placed|repositioned|nudged|pushed|dragged)\b",
    re.IGNORECASE,
)
_DESTINATION_START = re.compile(
    r"\s+(?:into\s+|onto\s+|(?<!next\s)(?<!close\s)(?<!adjacent\s)to\s+|"
    r"(?:(?:one|a)\s+(?:slot|column)\s+)?right(?=(?:[-\s]+hand\b)|\s+(?:by|one|a|in|into|onto|within|on|from|slot|column)\b|[,.!?]|\s*$))",
    re.IGNORECASE,
)
_RIGHT_DIRECTION = re.compile(r"\bright(?:wards?)?\b", re.IGNORECASE)
_RIGHT_BEFORE_PRESERVATION = re.compile(r"\s+right\s*;", re.IGNORECASE)
_LEADING_LOCATION = re.compile(r"^\s*(?P<location>(?:in|on|within|under|for)\s+[^,.;!?]{1,180}),\s*", re.IGNORECASE)
_OTHER_ROW = re.compile(r"\b(?:another|different|other|next|previous)\s+row\b", re.IGNORECASE)
_ROW_PREPOSITION = re.compile(r"\b(?:in|into|on|onto|to|of|from|within|inside)\b", re.IGNORECASE)
_ROW_QUALIFIER = re.compile(r"\s*([^,.!?;]{1,110}?)\s+row\b", re.IGNORECASE)
_NUMBERED_ROW = re.compile(r"\s*(?:the\s+)?row\s+(?:number\s+)?([1-9]\d{0,5})\b", re.IGNORECASE)
_ORDINAL_ROWS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6}
_HEADING_REFERENCE = re.compile(r"\b(?:under|beneath|below|beside|next\s+to)\s+([^,.;!?]+)\s*$", re.IGNORECASE)
_IMAGE_LABEL_REFERENCE = re.compile(r"\b(?:named|titled|labelled|labeled|called)\s*$", re.IGNORECASE)
_SOURCE_QUALIFIER = re.compile(
    r"\b(?:by|with|near|beside|alongside|under|beneath|below|above|next\s+to|adjacent\s+to|in|within|from|at|for)\s+([^,.;!?]+)\s*$",
    re.IGNORECASE,
)
_PAGE_QUALIFIER = re.compile(r"\s*([^,.!?;]{1,110}?)\s+page\b", re.IGNORECASE)
_CURRENT_ROW = re.compile(r"(?:(?:the|its|that|this)\s+)?(?:same|current|original)|(?:this|its)\s*", re.IGNORECASE)
_RIGHT_OF = re.compile(r"\bright\s+of\s+([^,.!?;]+)", re.IGNORECASE)
_CURRENT_POSITION = re.compile(
    r"(?:it|that|the\s+image|where\s+it\s+is(?:\s+now)?|its\s+(?:(?:own|current|original)\s+)?(?:place|slot|column|position))",
    re.IGNORECASE,
)
_MULTIPLE_SLOTS = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|(?:[2-9]|\d{2,}))\s+(?:slots|columns)\b", re.IGNORECASE)
_ALTERNATIVE_DIRECTION = re.compile(
    r"\b(?:left|above|below|up(?:wards?)?|down(?:wards?)?|diagonal(?:ly)?|top|bottom|"
    r"instead|or|far|rightmost|last|outermost|elsewhere|and then)\b|"
    r"\bright\s+(?:before|after|now|away)\b|;",
    re.IGNORECASE,
)
_PRESERVE_SURROUNDINGS = re.compile(
    r";\s*(?:keep|leave|retain|preserve)\s+(?:(?:all|the)\s+)?"
    r"(?:(?:surrounding|unrelated|other|existing)\s+"
    r"(?:notes|text|prose|content|images?|figures?|paragraphs?|captions?|written\s+material)|everything\s+else)"
    r"(?:\s+(?:unchanged|untouched|intact))?[.!]?\s*$",
    re.IGNORECASE,
)
_CONDITIONAL = re.compile(r"\b(?:if|assuming|provided|hypothetical(?:ly)?)\b", re.IGNORECASE)
_EXCLUDED_TARGET = re.compile(r"\b(?:not|don['’]t|never|except|excluding|or|both|each|all)\b", re.IGNORECASE)
_QUOTED_LABEL = re.compile(
    r'''"(?:\\.|[^"\\\n])*"|“[^”\n]*”|(?<!\w)'[^'\n]*'(?!\w)|(?<!\w)‘[^’\n]*’(?!\w)|\x60[^\x60\n]+\x60''',
)
_WORDS = re.compile(r"[^\W_]+")
_MOTION_MENTION = re.compile(r"\b(?:mov(?:e[ds]?|ing)|shift(?:s|ed|ing)?|slid(?:e[ds]?|ing)|reposition(?:ed|ing)?|put(?:ting)?|plac(?:e[ds]?|ing))\b", re.IGNORECASE)
_LAYOUT_MENTION = re.compile(r"\b(?:slots?|columns?|rows?|adjacent|left|right)\b", re.IGNORECASE)
_IMAGE_MENTION = re.compile(r"\b(?:image|illustration|picture|photo|map|diagram|drawing|sketch|artwork)s?\b", re.IGNORECASE)
_DISCUSSION_MENTION = re.compile(r"\b(?:what|how|would|if|imagine|hypothetic\w*|should|don['’]t|not)\b", re.IGNORECASE)
_OTHER_AUTHORING = re.compile(
    r"^\s*(?:(?:can|could|would|will)\s+you\s+)?(?:please\s+)?"
    r"(?:write|draft|compose|add|insert|create|generate|replace|revise|summarize)\b",
    re.IGNORECASE,
)
_READ_ONLY = re.compile(
    r"(?:^|[,:.;!?])\s*(?:what|how|why|when|where|whether|should|imagine|suppose|consider|describe|explain|preview|compare|look\s+at)\b"
    r"|(?:^|[,:.;!?])\s*no\s+(?:movement|move|change)\b"
    r"|\b(?:would\s+(?:it|that|this)\s+look|only\s+(?:asking|discussion|a\s+preview)|just\s+(?:asking|a\s+preview)"
    r"|(?:do\s+not|don['’]t|rather\s+not|never)\s+(?:move|shift|put|place|reposition|want|need|prefer|expect|like)"
    r"|(?:must|should|can|ought)\s+not)\b",
    re.IGNORECASE,
)
_LAYOUT_NOUN = re.compile(r"\b(?:slots?|columns?|rows?|cells?)\b", re.IGNORECASE)
_OBSERVED_PLACEMENT = re.compile(
    r"\b(?:was|were|used\s+to|is\s+(?:in|on|already|currently)|sits|yesterday|last\s+time|only\s+describing)\b",
    re.IGNORECASE,
)
_DESIRED_PLACEMENT = re.compile(
    r"\b(?:please|want|prefer|need|belongs?|should\s+(?:be|go)|must\s+(?:be|go)|can\s+go|goes|"
    r"over\s+one\s+slot)\b|,\s*(?:one|a)\s+(?:slot|column)\b",
    re.IGNORECASE,
)
_UNSPECIFIC_WORDS = frozenset(
    "about above across after again all along already also always and another any anything around before"
    " below beside both can could current did does during each empty every existing first for from"
    " have here into its just last left like move near next only original other out over place please"
    " right same second should side slot some than that the their them then there these they this"
    " those through under vacant want was where which while will with within would".split()
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
    return " ".join(_WORDS.findall(text.casefold()))


def _mentions(text: str, phrase: str) -> bool:
    return bool(phrase and f" {phrase} " in f" {text} ")


def _mask_quoted_labels(text: str) -> str:
    # Keep offsets so explicit quoting of a row heading can resolve that label
    # without interpreting words inside the label as additional constraints.
    return _QUOTED_LABEL.sub(lambda match: "~" * len(match[0]), text)


def _mask_literal_phrase(text: str, phrase: str) -> str:
    """Use the same normalization for source spans and identity collisions."""
    target = phrase.split()
    tokens = [(word, match.start(), match.end()) for match in _WORDS.finditer(text)
              for word in _WORDS.findall(match[0].casefold())]
    masked = list(text)
    for index in range(len(tokens) - len(target) + 1):
        window = tokens[index:index + len(target)]
        if [word for word, _, _ in window] == target:
            start, end = window[0][1], window[-1][2]
            masked[start:end] = "~" * (end - start)
    return "".join(masked)


def _move_clause(question: str) -> tuple[str, str] | None:
    masked = _mask_quoted_labels(question)
    active = _ACTIVE_MOVE.match(masked)
    if active is not None:
        location = question[active.start("location"):active.end("location")] if active.group("location") else ""
        return location, question[active.end():]
    passive = _PASSIVE_MOVE.match(masked)
    if passive is not None:
        group = "modal" if passive.group("modal") else "wanted"
        if not re.search(r"\b(?:not|never)\b", passive.group(group), re.IGNORECASE):
            return "", question[passive.start(group):passive.end(group)] + question[passive.end():]
    return None


def admitted_image_move_choice(answers: dict[str, str] | None, question: str) -> str | None:
    choice = answers["image_move_intent"] if answers is not None else None
    if choice != "other":
        return choice
    masked = _mask_quoted_labels(question)
    explicit_image = _IMAGE_MENTION.search(question) and (
        _MOTION_MENTION.search(masked) or _LAYOUT_NOUN.search(masked)
    )
    nominated_layout = (answers["image_move_destination"] in {"same_row_right", "different_row"}
                        and answers["image_move_occurrence"] not in {"ambiguous", "missing"}
                        and _LAYOUT_MENTION.search(masked))
    if (not _OTHER_AUTHORING.match(masked) and _LAYOUT_MENTION.search(masked)
            and (explicit_image or nominated_layout)
            and (_move_clause(question) is not None or _DISCUSSION_MENTION.search(masked))):
        # Retain the existing unresolved action for image-layout discussion.
        # The raw Jev vote remains in the exact proof and never grants a move.
        return "unresolved"
    return choice


def _context_terms(text: str) -> set[str]:
    return {word for word in _phrase(text).split() if len(word) >= 3 and word not in _UNSPECIFIC_WORDS
            and not _IMAGE_MENTION.fullmatch(word) and not _LAYOUT_MENTION.fullmatch(word)}


@dataclass(frozen=True)
class BuildImageMoveDecision:
    capture: BuildImageMoveCapture
    question: str
    presentation_sha256: str
    occurrences: tuple[_Occurrence, ...]
    other_media: tuple[tuple[str, str, str], ...]
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
        media_contexts: Counter[tuple[str, str, str]] = Counter()
        row_labels: dict[str, set[int]] = {}
        row_media_counts: dict[int, int] = {}
        number = 0
        for node, item in zip(editor["content"], layout.items, strict=True):
            if not isinstance(item, Row):
                media_contexts.update((asset, alt, "") for asset, alt in _all_media(node))
                continue
            number += 1
            row_context = _semantic_text(node)[:500]
            row_media = tuple(_all_media(node))
            row_media_counts[number] = len(row_media)
            media_contexts.update((asset, alt, row_context) for asset, alt in row_media)
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
        other_media = media_contexts - Counter((item.asset, item.alt, item.row_context) for item in occurrences)
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

    def questions(self, *, include_affirmation: bool = True,
                  include_contextual_identity: bool = True,
                  modern_language: bool = True) -> tuple[ChoiceDecisionQuestion, ...]:
        intent = "Is the author actually asking to move an existing image occurrence? Discussion, hypotheticals, creation and advice are other."
        destination = ("Which destination does the author request, independent of availability? same_row_right is the "
                       "immediately adjacent slot to the image's right in its current row. A named different row is different_row.")
        occurrence = ("Which existing image occurrence does the author identify? Use its alt text and row description. "
                      "A deliberate selection identifies 'this image'. Choose ambiguous if two fit. "
                      "An unrelated caret and destination eligibility do not distinguish an image.")
        if modern_language:
            intent += " A short image name followed by a placement direction can itself request a move."
            destination += (" Treat 'right into the vacant slot' or 'one column right' as same_row_right "
                            "when the phrase describes a single step in the image's row. A vacant slot alone is unresolved.")
            occurrence += (" When identical copies repeat, match the author's nearby prose cue against the row descriptions. "
                           "A unique contextual paraphrase identifies that occurrence even when the image names match.")
        questions = (
            ChoiceDecisionQuestion(name="image_move_intent", options=("move_existing", "other", "unresolved"),
                question=intent),
            ChoiceDecisionQuestion(name="image_move_destination", options=("same_row_right", "different_row", "unsupported", "unresolved"),
                question=destination),
            ChoiceDecisionQuestion(name="image_move_occurrence", options=("ambiguous", "missing", *(item.alias for item in self.occurrences)),
                question=occurrence),
        )
        if include_affirmation:
            questions += (IMAGE_MOVE_AFFIRMATION,)
        repeat_assets = len({item.asset for item in self.occurrences}) < len(self.occurrences)
        repeat_labels = len({_phrase(item.alt) for item in self.occurrences}) < len(self.occurrences)
        if include_affirmation and include_contextual_identity and self.selected is None and (repeat_assets or repeat_labels):
            questions += (contextual_identity_question(item.alias for item in self.occurrences),)
        return questions

    def require_opening_offer(self, request: dict, *, allow_retained: bool = False) -> None:
        offered = request.get("questions", {})
        image_questions = {name: value for name, value in offered.items() if name.startswith("image_move_")}
        def exact_offer(modern_language):
            return {q.name: {
                "type": "choice", "instructions": q.question, "criteria": dict.fromkeys(q.options),
            } for q in self.questions(
                include_affirmation=not allow_retained or IMAGE_MOVE_AFFIRMATION.name in offered,
                include_contextual_identity=not allow_retained or CONTEXTUAL_IDENTITY in offered,
                modern_language=modern_language,
            )}
        if (request.get("state", {}).get("user_question") != self.question
                or request.get("state", {}).get("interaction", {}).get(OPENING_STATE_KEY) != self.semantic_state()
                or (image_questions != exact_offer(True)
                    and (not allow_retained or image_questions != exact_offer(False)))):
            raise ValueError("Image movement differs from the exact admitted opening offer")

    def opening_answers(self, request: dict, response: DecisionResult, *, allow_retained: bool = False, expected_model=None) -> dict[str, str]:
        self.require_opening_offer(request, allow_retained=allow_retained)
        if set(request["questions"]) != set(response.answers):
            raise ValueError("Image movement requires the complete opening response")
        options = {q.name: q.options for q in self.questions(
            include_affirmation=IMAGE_MOVE_AFFIRMATION.name in request["questions"],
            include_contextual_identity=CONTEXTUAL_IDENTITY in request["questions"],
        )}
        projected = response.model_copy(update={"answers": {name: response.answers[name] for name in options}})
        answers = validated_choice_answers(projected, set(options), **({'expected_model': expected_model} if expected_model else {}))
        if any(answer not in options[name] for name, answer in answers.items()):
            raise ValueError("Image move decision has an unoffered answer")
        return answers

    def resolve(self, answers: dict[str, str]) -> BuildImageMoveNomination:
        affirmation = answers.get(IMAGE_MOVE_AFFIRMATION.name)
        contextual_identity = answers.get(CONTEXTUAL_IDENTITY)
        for question in self.questions(
            include_affirmation=affirmation is not None,
            include_contextual_identity=contextual_identity is not None,
        ):
            if answers.get(question.name) not in question.options:
                raise ValueError("Image move decision has an unoffered answer")
        masked_question = _mask_quoted_labels(self.question)
        clause = _move_clause(self.question)
        if answers["image_move_intent"] != "move_existing" or affirmation == "description_or_discussion":
            return BuildImageMoveNomination("discussion")
        if affirmation == "unresolved":
            return BuildImageMoveNomination("unresolved")
        if clause is None:
            # Jev owns the affirmative language decision. The host checks for
            # conflicting purpose and binds only an explicit right-hand slot.
            if (_READ_ONLY.search(masked_question) or _OTHER_AUTHORING.match(masked_question)
                    or (masked_question.rstrip().endswith("?") and not re.search(r"\bplease\b", masked_question, re.IGNORECASE))
                    or (_OBSERVED_PLACEMENT.search(masked_question) and not _DESIRED_PLACEMENT.search(masked_question))
                    or (affirmation is None and not _DESIRED_PLACEMENT.search(masked_question))
                    or not _LAYOUT_NOUN.search(masked_question) or not _RIGHT_DIRECTION.search(masked_question)):
                return BuildImageMoveNomination("discussion")
            clause = "", self.question
            if contextual_identity is not None and (leading := _LEADING_LOCATION.match(masked_question)):
                clause = self.question[leading.start("location"):leading.end("location")], self.question[leading.end():]
        location, object_and_destination = clause
        masked_clause = _mask_quoted_labels(object_and_destination)
        scope = f"{location}, {object_and_destination}"
        masked_scope = _mask_quoted_labels(scope)
        if _CONDITIONAL.search(masked_scope):
            return BuildImageMoveNomination("discussion")
        if answers["image_move_destination"] == "different_row":
            return BuildImageMoveNomination("different_row")
        if answers["image_move_destination"] != "same_row_right":
            return BuildImageMoveNomination("unsupported")
        split = _DESTINATION_START.search(masked_clause)
        if split is None and affirmation is not None:
            split = _RIGHT_BEFORE_PRESERVATION.search(masked_clause)
        if split is None:
            return BuildImageMoveNomination("unresolved")
        object_text = object_and_destination[:split.start()]
        object_words = _phrase(object_text)
        if _EXCLUDED_TARGET.search(_mask_quoted_labels(location + " " + object_text)):
            return BuildImageMoveNomination("ambiguous")
        destination = masked_clause[split.start():]
        preservation = _PRESERVE_SURROUNDINGS.search(destination) if affirmation is not None else None
        if preservation is not None:
            destination = destination[:preservation.start()]
        if _OTHER_ROW.search(masked_scope):
            return BuildImageMoveNomination("different_row")
        if (not _RIGHT_DIRECTION.search(destination) or _ALTERNATIVE_DIRECTION.search(destination)
                or _MULTIPLE_SLOTS.search(masked_clause)):
            return BuildImageMoveNomination("unsupported")
        alias = answers["image_move_occurrence"]
        if alias in {"ambiguous", "missing"}:
            return BuildImageMoveNomination(alias)
        chosen = next(item for item in self.occurrences if item.alias == alias)
        chosen_words = _phrase(chosen.alt)
        competing_names = {
            _phrase(item.alt) for item in self.occurrences if item.alias != alias
        } | {_phrase(alt) for _, alt, _ in self.other_media}
        masked_object = _mask_quoted_labels(object_text)
        if chosen_words and chosen_words in competing_names:
            masked_object = _mask_literal_phrase(masked_object, chosen_words)
            object_start = len(location) + 2
            masked_scope = masked_scope[:object_start] + masked_object + masked_scope[object_start + len(object_text):]
        # A named row can occur before the right-slot wording. Require it to
        # identify the nominated source row anywhere in the action clause.
        explicitly_named_row = False
        prepositions = list(_ROW_PREPOSITION.finditer(masked_scope))
        for i, preposition in enumerate(prepositions):
            start = preposition.end()
            end = prepositions[i + 1].start() if i + 1 < len(prepositions) else len(scope)
            fragment = masked_scope[start:end]
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
            raw = scope[start + row_qualifier.start(1):start + row_qualifier.end(1)].strip()
            label = re.sub(r"^the\s+", "", _phrase(raw))
            if not _CURRENT_ROW.fullmatch(raw):
                if _ORDINAL_ROWS.get(label) != chosen.row_number and self.row_labels.get(label) != {chosen.row_number}:
                    return BuildImageMoveNomination("different_row")
                explicitly_named_row = True
        for text, masked_text in ((location, _mask_quoted_labels(location)), (object_text, masked_object)):
            heading = _HEADING_REFERENCE.search(masked_text)
            if heading is not None:
                reference = _phrase(text[heading.start(1):heading.end(1)])
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
        if any(name != chosen_words and _mentions(object_words, name)
               and not (_mentions(object_words, chosen_words) and _mentions(chosen_words, name))
               for name in competing_names):
            return BuildImageMoveNomination("ambiguous")
        if self.selected is None:
            conflicts = [
                item.alt for item in self.occurrences
                if item.alias != alias and (item.asset == chosen.asset or _phrase(item.alt) == _phrase(chosen.alt))
            ]
            conflicts.extend(alt for asset, alt, _ in self.other_media
                             if asset == chosen.asset or _phrase(alt) == _phrase(chosen.alt))
            direct = _mentions(object_words, chosen_words) and not any(
                _mentions(object_words, _phrase(alt)) or _mentions(_phrase(alt), chosen_words)
                for alt in conflicts
            )
            if not direct:
                for quote in _QUOTED_LABEL.finditer(object_text):
                    if _IMAGE_LABEL_REFERENCE.search(object_text[:quote.start()]):
                        label = _phrase(quote[0])
                        if _mentions(chosen_words, label) and not any(_mentions(other, label) for other in competing_names):
                            direct = True
                            break
            if conflicts and not direct:
                # Corroborate Jev's alias by context unique to this occurrence.
                # Geometry is excluded: the convenient destination cannot select an image.
                rivals = set().union(*(_context_terms(item.alt + " " + item.row_context)
                                        for item in self.occurrences if item.alias != alias),
                                      *(_context_terms(alt + " " + context) for _, alt, context in self.other_media))
                unique_alt = (_context_terms(chosen.alt) & _context_terms(masked_object)) - rivals
                qualifiers = (_SOURCE_QUALIFIER.search(masked_object),
                              _SOURCE_QUALIFIER.search(_mask_quoted_labels(location)))
                qualified_terms = set().union(*(_context_terms(qualifier.group(1))
                                                for qualifier in qualifiers if qualifier is not None))
                distinguishing_context = _context_terms(chosen.row_context) - rivals
                unique_row = bool(distinguishing_context & qualified_terms)
                semantic_context = (
                    contextual_identity == alias
                    and bool(qualified_terms - _context_terms(chosen.alt))
                    and bool(distinguishing_context)
                    and not any(asset == chosen.asset or _phrase(alt) == chosen_words
                                for asset, alt, _ in self.other_media)
                )
                if not unique_alt and not (
                    self.row_media_counts[chosen.row_number] == 1
                    and (explicitly_named_row or unique_row or semantic_context)
                ):
                    return BuildImageMoveNomination("ambiguous")
        if chosen.destination_slot is None or chosen.destination != "empty_right":
            return BuildImageMoveNomination(chosen.destination)
        return BuildImageMoveNomination("ready", BuildImageMovePlacement(
            basis=self.capture.basis, presentation_sha256=self.presentation_sha256,
            row_id=chosen.row_id, source_slot_id=chosen.source_slot,
            destination_slot_id=chosen.destination_slot, image_block_id=chosen.block.id,
        ))
