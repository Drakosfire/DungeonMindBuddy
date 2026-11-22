"""Verify protected Build blocks before counting their editor positions."""

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from application_state.agent_conversation.plan_slot_layout import (
    require_matching_prose_block,
    require_matching_prose_inline,
)
from application_state.content.markdown_source_blocks import source_block_spans

from .boundary_markdown import split_boundary_callout
from .image_move_layout import require_matching_build_image

_MARKDOWN = MarkdownIt("commonmark").enable(("table", "strikethrough"))


def _children(node: dict, kind: str, expected_attrs: dict | None = None) -> list[dict]:
    attrs = node.get("attrs", {})
    expected = expected_attrs or {}
    children = node.get("content", [])
    if (
        node.get("type") != kind or node.keys() - {"type", "attrs", "content"}
        or not isinstance(attrs, dict)
        or any(attrs.get(key) != value for key, value in expected.items())
        or any(value is not None and key not in expected and key != "pageBlockId"
               for key, value in attrs.items())
        or not isinstance(children, list) or not all(isinstance(child, dict) for child in children)
    ):
        raise ValueError("Build protected block differs from the exact Markdown")
    return children


def require_boundary_callout(node: dict, markdown: str) -> None:
    lines = markdown.rstrip("\r\n").replace("\r\n", "\n").replace("\r", "\n")
    split = split_boundary_callout(lines.split("\n"))
    if split is None:
        raise ValueError("Build callout requires its exact marker and quoted body")
    kind, label, body = split
    paragraphs = _children(node, "callout", {"kind": kind, "label": label})
    if not body.strip():
        (paragraph,) = paragraphs
        if _children(paragraph, "paragraph"):
            raise ValueError("Build empty callout differs from the captured Markdown")
        return
    source = body.encode("utf-8")
    for paragraph, (start, end) in zip(paragraphs, source_block_spans(body), strict=True):
        _children(paragraph, "paragraph")
        require_matching_prose_block(paragraph, source[start:end].decode("utf-8"))


def require_boundary_table(node: dict, markdown: str) -> None:
    root = SyntaxTreeNode(_MARKDOWN.parse(markdown))
    if len(root.children) != 1 or root.children[0].type != "table":
        raise ValueError("Build table requires its exact Markdown table")
    rows = [(row, "tableHeader" if part.type == "thead" else "tableCell")
            for part in root.children[0].children for row in part.children]
    for editor_row, (row, cell_kind) in zip(_children(node, "table"), rows, strict=True):
        for editor_cell, cell in zip(_children(editor_row, "tableRow"), row.children, strict=True):
            (paragraph,) = _children(editor_cell, cell_kind, {"colspan": 1, "rowspan": 1})
            _children(paragraph, "paragraph")
            if cell.attrs:
                raise ValueError("Build table alignment is absent from the editor capture")
            require_matching_prose_inline(paragraph, cell.children[0].token.children or [])


def require_boundary_image(node: dict, markdown: str) -> None:
    tokens = _MARKDOWN.parse(markdown)
    if [token.type for token in tokens] != ["paragraph_open", "inline", "paragraph_close"]:
        raise ValueError("Build artwork requires its exact Markdown image")
    children = tokens[1].children or []
    if len(children) != 1 or children[0].type != "image":
        raise ValueError("Build artwork requires a standalone Markdown image")
    _children(node, "paragraph")
    require_matching_build_image(node, children[0])
