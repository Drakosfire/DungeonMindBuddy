"""Localize host-owned Play references before they enter a scene-writer prompt."""
from __future__ import annotations

from dataclasses import dataclass
from markdown_it import MarkdownIt
from apps.live_control_server.services.plan_playable_body_target import _strip_frontmatter, _line_blocks, _root_markers


def _internal_destinations(markdown: str) -> set[str]:
    found: set[str] = set()
    def visit(items):
        for item in items:
            if item.type in {'link_open', 'image'}:
                value = item.attrGet('href' if item.type == 'link_open' else 'src') or ''
                if value.startswith(('dmb-media:', 'dmb-node:', '#dmb-ref:', '#dmb-action:')):
                    found.add(value)
            visit(item.children or [])
    visit(MarkdownIt('commonmark', {'html': True}).parse(markdown))
    return found


@dataclass(frozen=True)
class SceneModelAliases:
    # Exact identities remain host-side. Model-visible aliases are request local.
    replacements: tuple[tuple[str, str], ...]

    def localize(self, value: str) -> str:
        for original, alias in self.replacements:
            value = value.replace(original, alias)
        return value

    def resolve(self, value: str) -> str:
        allowed = {alias for _, alias in self.replacements}
        if _internal_destinations(value) - allowed:
            raise ValueError('The proposal introduces an unknown internal reference')
        for original, alias in sorted(self.replacements, key=lambda item: len(item[1]), reverse=True):
            value = value.replace(alias, original)
        return value


def scene_model_aliases(markdown: str, context: str, instruction: str) -> SceneModelAliases:
    """Resolve canonical markers and Markdown targets into disjoint local names.

    Only parser-admitted structural identities and resource destinations are
    localized; ordinary authored prose and the user's instruction are retained.
    """
    parser = MarkdownIt('commonmark', {'html': True})
    source = _strip_frontmatter(markdown.replace('\ufeff', '', 1))
    tokens = parser.parse(source)
    lines = source.splitlines()
    markers = _root_markers(tokens, _line_blocks(tokens), lines)
    identities = {marker.id for marker in markers}
    for marker in markers:
        for group in marker.edge_attrs:
            identities.update(group.split(','))
    destinations = _internal_destinations(markdown) | _internal_destinations(context)
    combined = markdown + '\n' + context + '\n' + instruction
    # A normalized destination that does not occur verbatim cannot safely be
    # replaced and reconstructed; do not dispatch the model in that case.
    if any(value not in markdown and value not in context for value in destinations):
        raise ValueError('A source reference cannot be represented safely for the scene writer')
    originals = identities | destinations
    replacements = []
    for number, original in enumerate(sorted(originals), 1):
        if original.startswith('#'):
            prefix = ':'.join(original.split(':')[:2]) + ':'
        else:
            prefix = original.split(':', 1)[0] + ':'
        counter = number
        while True:
            alias = f'{prefix}local-reference-{counter}'
            if alias not in combined and all(alias != item[1] for item in replacements):
                break
            counter += len(originals) + 1
        replacements.append((original, alias))
    # Replace longer originals first so IDs with common prefixes do not overlap.
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    return SceneModelAliases(tuple(replacements))
