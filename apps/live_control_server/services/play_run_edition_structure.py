"""Ordered Play structure proof over the owning manifest and Markdown parsers.

No content rewriting or client-supplied structure is involved. Unmarked heading
boundaries participate because they change which source ranges attach to scenes.
"""

import hashlib
import json

from markdown_it import MarkdownIt

from apps.live_control_server.services.plan_playable_body_target import (
    PlayableBodyTargetError,
    _attached_heading,
    _line_blocks,
    _root_markers,
    _strip_frontmatter,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    derive_play_run_reference_elements_v2,
    detect_playable_grammar_version,
)


class EditionStructureError(ValueError):
    pass


def structure_signature(markdown: str) -> dict:
    """Retain ordered envelopes, attachment boundaries, parents and edge order."""
    try:
        if detect_playable_grammar_version(markdown) != 2:
            raise EditionStructureError("Run content editions require grammar v2")
        membership = derive_play_run_reference_elements_v2(markdown)
        # Preserve a leading UTF8 BOM with the exact frontmatter envelope while
        # parsing the same canonical header as the owning body parser.
        parse_source = markdown[1:] if markdown.startswith("\ufeff") else markdown
        source = _strip_frontmatter(parse_source)
        frontmatter = markdown[: len(markdown) - len(source)]
        source = source.replace("\r\n", "\n").replace("\r", "\n")
        lines = source.split("\n")
        tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
        blocks = _line_blocks(tokens)
        markers = _root_markers(tokens, blocks, lines)
        # A marker swallowed by fenced/indented code, quotes, HTML containers or
        # frontmatter cannot masquerade as an unchanged live structural marker.
        if markdown.count("dmb-playable-element:") != len(markers):
            raise EditionStructureError(
                "Playable markers must remain active top-level directives"
            )
        if any(marker.version != "v2" for marker in markers):
            raise EditionStructureError("Mixed marker grammar is unsupported")
        attached = _attached_heading(tokens, blocks, markers, lines)
        ordered = []
        headings: list[tuple[int, int]] = []
        for block in blocks:
            marker = attached.get(block.token_index)
            if block.kind == "heading":
                while headings and headings[-1][0] >= block.level:
                    headings.pop()
                ordered.append(
                    {
                        "heading": block.level,
                        "parents": [position for _, position in headings],
                        "envelope": lines[marker.line] if marker else None,
                    }
                )
                headings.append((block.level, len(ordered) - 1))
            elif marker:
                items = [
                    token
                    for token in tokens[block.token_index + 1 :]
                    if token.type == "list_item_open"
                    and token.level == 1
                    and token.map
                    and token.map[0] < block.end
                ]
                if len(items) != 1:
                    raise EditionStructureError(
                        "Option must attach to exactly one top-level list item"
                    )
                ordered.append(
                    {
                        "option": lines[marker.line],
                        "parents": [position for _, position in headings],
                    }
                )
        return {
            "frontmatter": frontmatter,
            "ordered": ordered,
            "membership": {
                name: [
                    item.model_dump(mode="json", exclude_none=True) for item in items
                ]
                for name, items in zip(membership._fields, membership)
            },
        }
    except (PlayableBodyTargetError, PlayRunReferenceManifestError) as exc:
        raise EditionStructureError(str(exc)) from exc


def validate_edition_structure(origin: str, candidate: str, manifest: dict) -> str:
    signature = structure_signature(origin)
    if manifest.get("schema_version") != "dmb_play_run_reference_manifest_v2":
        raise EditionStructureError("Run content editions require a sealed v2 manifest")
    for name, members in signature["membership"].items():
        if manifest.get(name) != members:
            raise EditionStructureError(
                "Origin structure disagrees with the sealed Run manifest"
            )
    if structure_signature(candidate) != signature:
        raise EditionStructureError(
            "Run edition must preserve origin structure, order and attachment boundaries"
        )
    return hashlib.sha256(
        json.dumps(
            signature, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
