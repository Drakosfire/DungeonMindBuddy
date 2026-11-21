"""Host-side binding of a reviewed paragraph insertion to an existing Plan slot."""

from __future__ import annotations

from copy import deepcopy
from typing import Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from application_state.content.page_presentation import (
    BlockBinding,
    Identifier,
    PagePresentation,
    Row,
    leading_yaml,
)


class PlanSlotAddressV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    row_index: int = Field(ge=0)
    row_id: Identifier
    slot_index: int = Field(ge=0, le=2)
    slot_id: Identifier
    child_index: int = Field(ge=0)
    block_id: Identifier
    relation: Literal["before", "after"]

    @property
    def insertion_index(self) -> int:
        return self.child_index + (self.relation == "after")


def _children(node: dict, expected_count: int) -> list[dict]:
    children = node.get("content", [])
    if (
        not isinstance(children, list)
        or len(children) != expected_count
        or any(not isinstance(child, dict) for child in children)
    ):
        raise ValueError("Plan editor structure differs from its layout")
    return children


def _require_block(node: dict, binding, source: bytes) -> BlockBinding:
    if not isinstance(binding, BlockBinding):
        raise ValueError(
            "Plan slot authoring requires prose, headings, or horizontal rules"
        )
    attrs = node.get("attrs")
    if not isinstance(attrs, dict) or attrs.get("pageBlockId") != binding.id:
        raise ValueError("Plan editor block differs from its layout identity")
    text = source[binding.byte_start : binding.byte_end].decode("utf-8")
    _require_matching_block(node, text)
    return binding


def require_editor_layout(
    editor: dict, markdown: str, layout: PagePresentation
) -> list[BlockBinding]:
    """Join every editor block and wrapper to its exact checked source."""
    if editor.get("type") != "doc":
        raise ValueError("Plan layout requires an exact editor document")
    source = markdown.encode("utf-8")
    bindings = []
    for node, item in zip(_children(editor, len(layout.items)), layout.items):
        if not isinstance(item, Row):
            bindings.append(_require_block(node, item, source))
            continue
        attrs = node.get("attrs")
        if (
            node.get("type") != "pageRow"
            or not isinstance(attrs, dict)
            or (attrs.get("id"), attrs.get("min_height"), attrs.get("line_mode"))
            != (item.id, item.min_height, item.line_mode)
        ):
            raise ValueError("Plan editor row differs from its layout")
        for slot_node, slot in zip(_children(node, len(item.slots)), item.slots):
            attrs = slot_node.get("attrs")
            if (
                slot_node.get("type") != "pageSlot"
                or not isinstance(attrs, dict)
                or (attrs.get("id"), attrs.get("width")) != (slot.id, slot.width)
            ):
                raise ValueError("Plan editor slot differs from its layout")
            for child, block in zip(
                _children(slot_node, len(slot.blocks)), slot.blocks
            ):
                bindings.append(_require_block(child, block, source))
    return bindings


def require_slot_paragraph(
    editor: dict, markdown: str, layout: PagePresentation, address: PlanSlotAddressV1
) -> list[BlockBinding]:
    bindings = require_editor_layout(editor, markdown, layout)
    try:
        row = layout.items[address.row_index]
        if not isinstance(row, Row):
            raise ValueError("Plan target is outside a row")
        slot = row.slots[address.slot_index]
        block = slot.blocks[address.child_index]
    except IndexError as exc:
        raise ValueError("Plan slot address is outside the captured layout") from exc
    paragraph = _editor_slot(editor, address)["content"][address.child_index]
    if (
        not isinstance(block, BlockBinding)
        or (row.id, slot.id, block.id)
        != (address.row_id, address.slot_id, address.block_id)
        or paragraph.get("type") != "paragraph"
    ):
        raise ValueError("Plan slot address differs from the captured paragraph")
    return bindings


def _editor_slot(editor: dict, address: PlanSlotAddressV1) -> dict:
    return editor["content"][address.row_index]["content"][address.slot_index]


_MARKS = {"strong": "bold", "em": "italic", "s": "strike", "link": "link"}
_TEXT_MARKS = {"bold", "italic", "strike", "code"}
_PARSER = MarkdownIt("commonmark", {"html": True}).enable("strikethrough")


def _link(href, title) -> tuple[str, ...]:
    if not isinstance(href, str) or not href.startswith(("https://", "http://")):
        raise ValueError("Plan slot prose cannot introduce an object reference")
    if title is not None and not isinstance(title, str):
        raise ValueError("Plan slot prose requires an exact link title")
    return "link", href, title or ""


def _append(runs: list[tuple], text: str, marks) -> None:
    if not text:
        return
    keys = tuple(sorted(marks))
    if runs and runs[-1][0] == keys:
        runs[-1] = keys, runs[-1][1] + text
    else:
        runs.append((keys, text))


def _markdown_runs(tokens) -> list[tuple]:
    runs: list[tuple] = []
    active: list[tuple] = []
    for token in tokens:
        name, _, edge = token.type.partition("_")
        if name in _MARKS and edge in {"open", "close"}:
            if edge == "close":
                active.pop()
            elif name == "link":
                active.append(_link(token.attrGet("href"), token.attrGet("title")))
            else:
                active.append((_MARKS[name],))
        elif token.type == "text":
            _append(runs, token.content, active)
        elif token.type == "code_inline":
            _append(runs, token.content, [*active, ("code",)])
        elif token.type == "softbreak":
            _append(runs, " ", active)
        elif token.type == "hardbreak":
            _append(runs, "\n", [("hardBreak",)])
        else:
            raise ValueError(
                "Plan slot insertion requires prose represented by the editor"
            )
    return runs


def _editor_runs(paragraph: dict) -> list[tuple]:
    runs: list[tuple] = []
    inline_nodes = paragraph.get("content", [])
    if not isinstance(inline_nodes, list) or not all(
        isinstance(node, dict) for node in inline_nodes
    ):
        raise ValueError("Plan slot paragraph has invalid editor content")
    for inline in inline_nodes:
        if inline.get("type") == "hardBreak":
            _append(runs, "\n", [("hardBreak",)])
            continue
        if inline.get("type") != "text" or not isinstance(inline.get("text"), str):
            raise ValueError(
                "Plan slot insertion requires prose represented by the editor"
            )
        marks = []
        raw_marks = inline.get("marks", [])
        if not isinstance(raw_marks, list) or not all(
            isinstance(mark, dict) for mark in raw_marks
        ):
            raise ValueError("Plan slot prose has invalid editor marks")
        for mark in raw_marks:
            kind = mark.get("type")
            if isinstance(kind, str) and kind in _TEXT_MARKS:
                marks.append((kind,))
            elif kind == "link":
                attrs = mark.get("attrs", {})
                if not isinstance(attrs, dict):
                    raise ValueError("Plan slot link lacks exact editor attributes")
                marks.append(_link(attrs.get("href"), attrs.get("title")))
            else:
                raise ValueError("Plan slot prose contains an unsupported editor mark")
        _append(runs, inline["text"], marks)
    return runs


def _require_matching_block(node: dict, markdown: str) -> None:
    tokens = _PARSER.parse(markdown)
    kinds = [token.type for token in tokens]
    kind = node.get("type")
    if kind == "horizontalRule" and kinds == ["hr"]:
        _children(node, 0)
        return
    if kind == "heading" and kinds == ["heading_open", "inline", "heading_close"]:
        if tokens[0].tag != f"h{node['attrs'].get('level')}":
            raise ValueError(
                "Plan editor heading level differs from its exact Markdown"
            )
    elif kind != "paragraph" or kinds != [
        "paragraph_open",
        "inline",
        "paragraph_close",
    ]:
        raise ValueError(
            "Plan slot authoring requires prose, headings, or horizontal rules"
        )
    if _editor_runs(node) != _markdown_runs(tokens[1].children or []):
        raise ValueError("Plan editor text differs from its exact Markdown")


def require_exact_slot_insertion(
    *,
    address: PlanSlotAddressV1,
    before_editor: dict,
    before_markdown: str,
    before_layout: PagePresentation,
    after_editor: dict,
    after_markdown: str,
    after_layout: PagePresentation,
    reviewed_markdown: str,
) -> None:
    """Admit only an insertion at the named slot boundary, including exact source."""
    original_bindings = require_slot_paragraph(
        before_editor, before_markdown, before_layout, address
    )
    after_layout.checked(after_markdown)
    next_bindings = require_editor_layout(after_editor, after_markdown, after_layout)
    comparison = deepcopy(after_editor)
    try:
        before_children = _editor_slot(before_editor, address)["content"]
        after_children = _editor_slot(comparison, address)["content"]
    except (KeyError, IndexError) as exc:
        raise ValueError("Plan slot application removed its target container") from exc
    insert = address.insertion_index
    count = len(after_children) - len(before_children)
    inserted = after_children[insert : insert + count]
    if (
        count < 1
        or len(inserted) != count
        or any(node.get("type") != "paragraph" for node in inserted)
    ):
        raise ValueError(
            "Plan application did not insert paragraphs at its captured boundary"
        )
    del after_children[insert : insert + count]
    if comparison != before_editor:
        raise ValueError(
            "Plan slot application changed unrelated editor content or geometry"
        )

    row = after_layout.items[address.row_index]
    if not isinstance(row, Row):
        raise ValueError("Plan slot application removed its target row")
    added = row.slots[address.slot_index].blocks[insert : insert + count]
    if any(not isinstance(block, BlockBinding) for block in added):
        raise ValueError("Plan slot application changed the new paragraph binding type")
    first = next_bindings.index(added[0])
    if next_bindings[first : first + count] != added:
        raise ValueError("Plan slot paragraphs are out of source order")
    retained = next_bindings[:first] + next_bindings[first + count :]
    if [block.id for block in original_bindings] != [block.id for block in retained]:
        raise ValueError("Plan slot application changed existing block identities")

    reviewed = reviewed_markdown.rstrip("\r\n")
    before = before_markdown.encode("utf-8")
    after = after_markdown.encode("utf-8")
    written = after[added[0].byte_start : added[-1].byte_end]
    if written.rstrip(b"\r\n") != reviewed.encode("utf-8") or leading_yaml(
        before_markdown
    ) != leading_yaml(after_markdown):
        raise ValueError("Plan slot application differs from the reviewed Markdown")
    for index, (old, new) in enumerate(zip(original_bindings, retained)):
        original = before[old.byte_start : old.byte_end]
        retained_source = after[new.byte_start : new.byte_end]
        if original == retained_source:
            continue
        # Appending after the last paragraph may require the sole extra blank
        # line that separates the retained paragraph from the reviewed prose.
        if (
            index == first - 1 == len(original_bindings) - 1
            and original.endswith(b"\n")
            and not original.endswith(b"\n\n")
            and retained_source == original + b"\n"
        ):
            continue
        raise ValueError("Plan slot application changed existing Markdown bytes")
