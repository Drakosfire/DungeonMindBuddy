"""Join a Build image editor capture to the saved Markdown and presentation."""

import re

from markdown_it import MarkdownIt

from application_state.agent_conversation.plan_slot_layout import require_matching_prose_block
from application_state.content.page_presentation import BlockBinding, ImageText, PagePresentation, Row


_IMAGE_STYLE = re.compile(r"dmb-image:v1 width=(20|[2-9][0-9]|100) collapsed=(true|false)")


def _children(node, total):
    children = node.get("content", [])
    if not isinstance(children, list) or len(children) != total or any(not isinstance(n, dict) for n in children):
        raise ValueError("Editor structure differs from the saved Page")
    return children


def _attrs(node, expected, *, allow_null_extra=False):
    attrs = node.get("attrs")
    if not isinstance(attrs, dict) or any(attrs.get(key) != value for key, value in expected.items()):
        raise ValueError("Editor attributes differ from the saved Page")
    if any(not allow_null_extra or value is not None for key, value in attrs.items() if key not in expected):
        raise ValueError("Editor attributes are absent from the saved Page")


def _block(node, binding, source):
    if set(node) - {"type", "attrs", "content"}:
        raise ValueError("Editor block carries unsupported data")
    if isinstance(binding, ImageText):
        if node.get("type") != "pageImageText":
            raise ValueError("Editor image stack differs from the saved Page")
        _attrs(node, {"id":binding.id, "anchor":binding.anchor, "inset":binding.inset, "backing":binding.backing})
        image, text = _children(node, 2)
        _block(image, binding.image, source)
        _block(text, binding.text, source)
        return
    if not isinstance(binding, BlockBinding):
        raise ValueError("Unsupported saved block")
    text = source[binding.byte_start:binding.byte_end].decode("utf-8")
    tokens = MarkdownIt("commonmark", {"html": True}).parse(text)
    node_attrs = {"pageBlockId":binding.id}
    if node.get("type") == "heading":
        node_attrs["level"] = node.get("attrs", {}).get("level")
    _attrs(node, node_attrs, allow_null_extra=True)
    if (
        [token.type for token in tokens] == ["paragraph_open", "inline", "paragraph_close"]
        and len(tokens[1].children or []) == 1
        and tokens[1].children[0].type == "image"
    ):
        saved_image = tokens[1].children[0]
        (editor_image,) = _children(node, 1)
        url = saved_image.attrGet("src") or ""
        if (
            not url.startswith("dmb-media:") or node.get("type") != "paragraph"
            or editor_image.get("type") != "mediaImage"
            or set(editor_image) != {"type", "attrs"}
            or any(child.type != "text" for child in saved_image.children or [])
        ):
            raise ValueError("Editor image differs from the exact saved image")
        alt = "".join(child.content for child in saved_image.children or [])
        title = saved_image.attrGet("title")
        style = _IMAGE_STYLE.fullmatch(title or "")
        if title and not style:
            raise ValueError("Saved media presentation is unsupported")
        _attrs(editor_image, {
            "assetId": url[10:], "alt": alt,
            "width": int(style[1]) if style else None,
            "collapsed": style[2] == "true" if style else None,
        })
    else:
        require_matching_prose_block(node, text)


def require_build_image_layout(editor: dict, markdown: str, layout: PagePresentation) -> None:
    """Reject an editor capture that cannot be proved from its authoritative saved before-image."""
    if editor.get("type") != "doc" or set(editor) != {"type", "content"}:
        raise ValueError("The image move needs an exact editor document")
    source = markdown.encode("utf-8")
    for node, item in zip(_children(editor, len(layout.items)), layout.items, strict=True):
        if not isinstance(item, Row):
            _block(node, item, source)
            continue
        if node.get("type") != "pageRow" or set(node) != {"type", "attrs", "content"}:
            raise ValueError("Editor row differs from its saved presentation")
        _attrs(node, {"id":item.id, "min_height":item.min_height, "line_mode":item.line_mode})
        for slot_node, slot in zip(_children(node, len(item.slots)), item.slots, strict=True):
            if slot_node.get("type") != "pageSlot" or set(slot_node) - {"type", "attrs", "content"}:
                raise ValueError("Editor slot differs from its saved presentation")
            _attrs(slot_node, {"id":slot.id, "width":slot.width})
            for child, block in zip(_children(slot_node, len(slot.blocks)), slot.blocks, strict=True):
                _block(child, block, source)
