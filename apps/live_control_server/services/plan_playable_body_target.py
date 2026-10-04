"""Resolve a typed Playable body from the exact submitted Plan Markdown."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from markdown_it import MarkdownIt

PlayableKind = Literal["scene", "beat", "choice", "option"]
MarkerGrammar = Literal["v1", "v2"]
BodyScope = Literal["heading_body", "beat_direct_body", "option_item_content"]

_ID = re.compile(r"^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$")
_V1_MARKER = re.compile(
    r"^<!-- dmb-playable-element:v1 kind=(scene|beat|choice|option) "
    r"id=((?:scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}) -->$"
)
_V2_MARKER = re.compile(
    r"^<!-- dmb-playable-element:v2 kind=(beat|scene|choice|option) "
    r"id=((?:beat|scene|choice|option):[a-z0-9][a-z0-9._-]{0,127})"
    r"(?: beat_kind=(spine|optional|interrupt))?"
    r"(?: scene=(scene:[a-z0-9][a-z0-9._-]{0,127}))?"
    r"(?: activates=((?:(?:beat|scene):[a-z0-9][a-z0-9._-]{0,127})"
    r"(?:,(?:beat|scene):[a-z0-9][a-z0-9._-]{0,127})*))?"
    r"(?: suppresses=((?:(?:beat|scene):[a-z0-9][a-z0-9._-]{0,127})"
    r"(?:,(?:beat|scene):[a-z0-9][a-z0-9._-]{0,127})*))? -->$"
)
_FRONTMATTER = re.compile(r"^---[ \t]*(?:\r\n|\n)([\s\S]*?)(?:\r\n|\n)---[ \t]*(?:(?:\r\n|\n)|$)")
_YAML_KEY = re.compile(r"(?:^|\r?\n)[A-Za-z0-9_.-]+:\s*")
_LIST_MARKER = re.compile(r"^( {0,3})([-+*]|[0-9]{1,9}[.)])[ \t]+")
_GRAPH_NODE_HREF = re.compile(r"^dmb-node:([a-z0-9][a-z0-9_.:-]*)$", re.IGNORECASE)
_RUNBOOK_HREF = re.compile(r"^#dmb-(ref|action):([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_.:-]*)$")
_RUNBOOK_REF_TYPES = {"npc", "location", "statblock", "roll-table", "citation", "graph-node"}
_RUNBOOK_ACTION_TYPES = {"combat"}
_GRAPH_NODE_ID = re.compile(r"^[a-z0-9][a-z0-9_.:-]*$", re.IGNORECASE)
_CORPUS_REF_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class PlayableBodyTargetError(ValueError):
    """The submitted draft does not contain one safe, canonical body range."""


@dataclass(frozen=True)
class PlayableTarget:
    kind: PlayableKind
    id: str


@dataclass(frozen=True)
class ResolvedPlayableBodyTarget:
    target: PlayableTarget
    marker_grammar_version: MarkerGrammar
    body_scope: BodyScope
    range_semantics_version: Literal["plan-playable-ranges-v1"]
    body_serialization_version: Literal["plan-playable-body-markdown-v1"]
    target_body_markdown: str
    target_body_sha256: str


@dataclass(frozen=True)
class _Marker:
    version: MarkerGrammar
    kind: PlayableKind
    id: str
    line: int
    token_index: int
    edge_attrs: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Block:
    kind: str
    start: int
    end: int
    level: int | None = None
    token_index: int = -1


def _strip_frontmatter(markdown: str) -> str:
    match = _FRONTMATTER.match(markdown)
    if not match or not _YAML_KEY.search(match.group(1) or ""):
        return markdown
    return markdown[match.end() :]


def _parse_marker(raw: str, *, line: int, token_index: int) -> _Marker | None:
    value = raw.strip()
    if "dmb-playable-element:" not in value:
        return None
    match = _V1_MARKER.fullmatch(value)
    if match:
        kind, identity = match.groups()
        if identity.split(":", 1)[0] != kind:
            raise PlayableBodyTargetError(f"Playable marker kind and ID disagree on line {line + 1}.")
        return _Marker("v1", kind, identity, line, token_index)
    match = _V2_MARKER.fullmatch(value)
    if match:
        kind, identity, beat_kind, scene_id, activates, suppresses = match.groups()
        if identity.split(":", 1)[0] != kind:
            raise PlayableBodyTargetError(f"Playable marker kind and ID disagree on line {line + 1}.")
        edges = tuple(filter(None, (activates, suppresses)))
        flattened = [edge for group in edges for edge in group.split(",")]
        if len(flattened) != len(set(flattened)) or (
            activates and suppresses and set(activates.split(",")) & set(suppresses.split(","))
        ):
            raise PlayableBodyTargetError(f"Playable Option edges are malformed on line {line + 1}.")
        if beat_kind and kind != "beat":
            raise PlayableBodyTargetError(f"Playable beat attributes are malformed on line {line + 1}.")
        if scene_id and kind != "choice":
            raise PlayableBodyTargetError(f"Playable Scene attributes are malformed on line {line + 1}.")
        if (activates or suppresses) and kind != "option":
            raise PlayableBodyTargetError(f"Playable Option edges are malformed on line {line + 1}.")
        return _Marker("v2", kind, identity, line, token_index, edges)
    raise PlayableBodyTargetError(f"Malformed or unsupported Playable marker on line {line + 1}.")


def _line_blocks(tokens: list[object]) -> list[_Block]:
    blocks: list[_Block] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        token_type = getattr(token, "type", "")
        token_level = getattr(token, "level", -1)
        token_map = getattr(token, "map", None)
        if token_level == 0 and token_map is not None:
            kind = token_type
            level: int | None = None
            if token_type == "heading_open":
                level = int(str(getattr(token, "tag", "h0"))[1:])
                kind = "heading"
            elif token_type in {"bullet_list_open", "ordered_list_open"}:
                kind = "list"
            elif token_type == "html_block":
                kind = "html"
            blocks.append(_Block(kind, int(token_map[0]), int(token_map[1]), level, index))
        index += 1
    return blocks


def _root_markers(tokens: list[object], blocks: list[_Block], lines: list[str]) -> list[_Marker]:
    markers: list[_Marker] = []
    code_ranges = [
        (int(token.map[0]), int(token.map[1]))
        for token in tokens
        if getattr(token, "type", "") in {"fence", "code_block"} and getattr(token, "map", None)
    ]
    parsed_line_numbers: set[int] = set()
    for block in blocks:
        if block.kind != "html":
            continue
        token = tokens[block.token_index]
        raw = str(getattr(token, "content", ""))
        if "dmb-playable-element:" not in raw:
            continue
        marker = _parse_marker(raw, line=block.start, token_index=block.token_index)
        if marker:
            markers.append(marker)
            parsed_line_numbers.update(range(block.start, block.end))
    for line_number, line in enumerate(lines):
        if "dmb-playable-element:" not in line:
            continue
        if any(start <= line_number < end for start, end in code_ranges):
            continue
        if line_number not in parsed_line_numbers:
            raise PlayableBodyTargetError(f"Playable marker is not a canonical top-level directive on line {line_number + 1}.")
    versions = {marker.version for marker in markers}
    if len(versions) > 1:
        raise PlayableBodyTargetError("This Plan mixes v1 and v2 Playable marker grammars.")
    ids = [marker.id for marker in markers]
    if len(ids) != len(set(ids)):
        raise PlayableBodyTargetError("This Plan contains duplicate Playable identities.")
    return markers


def _heading_text(tokens: list[object], block: _Block) -> str:
    token = tokens[block.token_index + 1] if block.token_index + 1 < len(tokens) else None
    return str(getattr(token, "content", "")) if getattr(token, "type", "") == "inline" else ""


def _attached_heading(
    tokens: list[object], blocks: list[_Block], markers: list[_Marker], lines: list[str]
) -> dict[int, _Marker]:
    by_token = {marker.token_index: marker for marker in markers}
    attached: dict[int, _Marker] = {}
    for marker in markers:
        marker_position = next((i for i, block in enumerate(blocks) if block.token_index == marker.token_index), None)
        if marker_position is None or marker_position + 1 >= len(blocks):
            raise PlayableBodyTargetError("Playable marker is orphaned from its target block.")
        following = blocks[marker_position + 1]
        if marker.version == "v2" and marker.kind == "option":
            if following.kind != "list" or marker.line + 1 != following.start:
                raise PlayableBodyTargetError("v2 Option marker must immediately precede one top-level list.")
            attached[following.token_index] = marker
            continue
        if following.kind != "heading" or marker.line + 1 != following.start:
            raise PlayableBodyTargetError("Playable heading marker must immediately precede its heading.")
        expected_level = (
            {"scene": 2, "beat": 3, "choice": 3, "option": 4}[marker.kind]
            if marker.version == "v1"
            else {"beat": 2, "scene": 3, "choice": 3}.get(marker.kind)
        )
        if expected_level is None or following.level != expected_level:
            raise PlayableBodyTargetError("Playable marker kind does not match its heading level.")
        attached[following.token_index] = marker
    return attached


def _normal_body(raw: str) -> str:
    value = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    return f"{value}\n" if value else "\n"


def _supported_typed_link(href: object) -> bool:
    if not isinstance(href, str):
        return False
    graph_match = _GRAPH_NODE_HREF.fullmatch(href)
    if graph_match:
        return bool(_GRAPH_NODE_ID.fullmatch(graph_match.group(1)))
    reference_match = _RUNBOOK_HREF.fullmatch(href)
    if not reference_match:
        return False
    kind, ref_type, ref_id = reference_match.groups()
    if kind == "ref" and ref_type in _RUNBOOK_REF_TYPES:
        id_pattern = _GRAPH_NODE_ID if ref_type == "graph-node" else _CORPUS_REF_ID
        return bool(id_pattern.fullmatch(ref_id))
    if kind == "action" and ref_type in _RUNBOOK_ACTION_TYPES:
        return bool(_CORPUS_REF_ID.fullmatch(ref_id))
    return False


def _contains_unsupported_links(tokens: list[object]) -> bool:
    for token in tokens:
        children = getattr(token, "children", None)
        if not children:
            continue
        index = 0
        while index < len(children):
            child = children[index]
            if getattr(child, "type", "") != "link_open":
                index += 1
                continue
            attrs = getattr(child, "attrs", None) or {}
            if not _supported_typed_link(attrs.get("href")) or attrs.get("title") is not None:
                return True
            index += 1
            label_parts: list[str] = []
            while index < len(children) and getattr(children[index], "type", "") != "link_close":
                label = children[index]
                if getattr(label, "type", "") != "text":
                    return True
                label_parts.append(str(getattr(label, "content", "")))
                index += 1
            if index >= len(children) or not "".join(label_parts).strip():
                return True
            index += 1
        if _contains_unsupported_links(children):
            return True
    return False


def _canonical_body(raw: str, parser: MarkdownIt) -> str:
    """Rebuild body bytes from independently parsed root block boundaries."""
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    tokens = parser.parse(normalized)

    def contains_unsupported_markup(items: list[object]) -> bool:
        for token in items:
            if getattr(token, "type", "") in {"hardbreak", "html_block", "html_inline", "fence", "code_block"}:
                return True
            children = getattr(token, "children", None)
            if children and contains_unsupported_markup(children):
                return True
        return False

    if contains_unsupported_markup(tokens):
        raise PlayableBodyTargetError("Playable body contains a hard break or raw HTML that is unavailable in this codec version.")
    blocks = _line_blocks(tokens)
    if not blocks:
        return "\n"
    fragments = ["\n".join(lines[block.start : block.end]).strip() for block in blocks]
    fragments = [fragment for fragment in fragments if fragment]
    return _normal_body("\n\n".join(fragments))


def _option_body(lines: list[str], list_block: _Block, list_token_index: int, tokens: list[object]) -> str:
    items = [
        token for token in tokens[list_token_index + 1 :]
        if getattr(token, "type", "") == "list_item_open"
        and getattr(token, "level", -1) == 1
        and getattr(token, "map", None)
        and int(token.map[0]) < list_block.end
    ]
    if len(items) != 1:
        raise PlayableBodyTargetError("v2 Option target must resolve to exactly one canonical top-level list item.")
    item = items[0]
    start, end = int(item.map[0]), int(item.map[1])
    item_lines = lines[start:end]
    if not item_lines:
        raise PlayableBodyTargetError("v2 Option has no list item body.")
    match = _LIST_MARKER.match(item_lines[0])
    if not match:
        raise PlayableBodyTargetError("v2 Option list item does not use a supported top-level list marker.")
    indent_width = match.end()
    body_lines = [item_lines[0][indent_width:]]
    for continuation in item_lines[1:]:
        if continuation.strip() == "":
            body_lines.append("")
        elif continuation.startswith(" " * indent_width):
            body_lines.append(continuation[indent_width:])
        else:
            raise PlayableBodyTargetError("v2 Option child blocks cannot be dedented without changing structure.")
    body_source = "\n".join(body_lines)
    body_parser = MarkdownIt("commonmark", {"html": True})
    body_tokens = body_parser.parse(body_source)
    body_blocks = _line_blocks(body_tokens)
    if sum(block.kind == "paragraph_open" for block in body_blocks) > 1:
        raise PlayableBodyTargetError("This Option has multiple paragraphs that the current editor serializer cannot preserve safely.")
    return _canonical_body(body_source, body_parser)


def resolve_playable_body_target(
    draft_markdown: str,
    target: PlayableTarget,
) -> ResolvedPlayableBodyTarget:
    if not _ID.fullmatch(target.id) or target.id.split(":", 1)[0] != target.kind:
        raise PlayableBodyTargetError("Playable target kind and canonical ID do not match.")
    source = _strip_frontmatter(draft_markdown)
    normalized_source = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized_source.split("\n")
    parser = MarkdownIt("commonmark", {"html": True})
    tokens = parser.parse(normalized_source)
    if _contains_unsupported_links(tokens):
        raise PlayableBodyTargetError("The submitted Plan contains links the mounted editor cannot preserve in this codec version.")
    blocks = _line_blocks(tokens)
    markers = _root_markers(tokens, blocks, lines)
    attached = _attached_heading(tokens, blocks, markers, lines)
    matches = [marker for marker in markers if marker.kind == target.kind and marker.id == target.id]
    if len(matches) != 1:
        raise PlayableBodyTargetError("Playable target is missing or duplicated in the submitted draft.")
    marker = matches[0]
    marker_grammar: MarkerGrammar = marker.version
    target_block = next((block for block in blocks if attached.get(block.token_index) == marker), None)
    if target_block is None:
        raise PlayableBodyTargetError("Playable target has no canonical top-level source range.")

    if marker.kind == "option" and marker.version == "v2":
        body = _option_body(lines, target_block, target_block.token_index, tokens)
        scope: BodyScope = "option_item_content"
    else:
        heading_index = blocks.index(target_block)
        boundary = len(lines)
        option_markers: list[tuple[_Marker, _Block]] = []
        for block in blocks[heading_index + 1 :]:
            following_marker = attached.get(block.token_index)
            if block.kind == "heading":
                if following_marker is not None:
                    boundary = following_marker.line
                    break
                if block.level is not None and block.level <= 2:
                    boundary = block.start
                    break
            if following_marker is not None and following_marker.kind == "option" and following_marker.version == "v2":
                option_markers.append((following_marker, block))
        if marker.version == "v2" and marker.kind == "choice" and option_markers:
            option_start = min(option_marker.line for option_marker, _ in option_markers)
            trailing = all(option_block.start >= option_start for _, option_block in option_markers)
            last_option_end = max(option_block.end for _, option_block in option_markers)
            later_nonblank = any(line.strip() for line in lines[last_option_end:boundary])
            if not trailing or later_nonblank:
                raise PlayableBodyTargetError("Choice body is split by marked Options and has no single safe range.")
            # Any unmarked item in an Option list remains Choice content. The
            # server declines the Choice target when that would splice ranges.
            for option_marker, option_block in option_markers:
                list_items = [
                    token for token in tokens[option_block.token_index + 1 :]
                    if getattr(token, "type", "") == "list_item_open"
                    and getattr(token, "level", -1) == 1
                    and getattr(token, "map", None)
                    and int(token.map[0]) < option_block.end
                ]
                if len(list_items) != 1:
                    raise PlayableBodyTargetError("Choice body is mixed with an Option list and is non-contiguous.")
            boundary = option_start
        start_line = target_block.end
        body = _canonical_body("\n".join(lines[start_line:boundary]), parser)
        scope = "beat_direct_body" if marker.version == "v2" and marker.kind == "beat" else "heading_body"

    if body == "\n" or len(body) > 8_000:
        raise PlayableBodyTargetError("Playable target body is empty or exceeds 8,000 Unicode scalar values.")
    body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return ResolvedPlayableBodyTarget(
        target=target,
        marker_grammar_version=marker_grammar,
        body_scope=scope,
        range_semantics_version="plan-playable-ranges-v1",
        body_serialization_version="plan-playable-body-markdown-v1",
        target_body_markdown=body,
        target_body_sha256=body_digest,
    )
