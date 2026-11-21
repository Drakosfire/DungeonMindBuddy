"""Author references and complete source binding; none of these values is authority.

The interpreter owns meaning. This module compiles declared literal references
and joins their names to actual heading occurrences in the frozen editor. It
never chooses an available replacement for an unmatched component.
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field, model_validator

from .native_statement_input import Strict

if TYPE_CHECKING:
    from .jev_retrieval_contract import RetrievalDialogue


class LiteralScopeName(Strict):
    kind: Literal['literal_name'] = 'literal_name'
    text: str = Field(min_length=1)

    @model_validator(mode='after')
    def nonblank(self):
        if not self.text.strip():
            raise ValueError('A literal name cannot be blank')
        return self


class DescribedScopeName(Strict):
    kind: Literal['description'] = 'description'
    text: str = Field(min_length=1)

    @model_validator(mode='after')
    def nonblank(self):
        if not self.text.strip():
            raise ValueError('A description cannot be blank')
        return self


class DocumentTitleScopeName(Strict):
    # This is not a string that can collide with a literal heading title.
    kind: Literal['document_title'] = 'document_title'


ScopeName = Annotated[LiteralScopeName | DescribedScopeName | DocumentTitleScopeName,
    Field(discriminator='kind')]


class NamedScopePath(Strict):
    kind: Literal['named_path'] = 'named_path'
    names: tuple[ScopeName, ...] = Field(min_length=1, max_length=6)
    edges: tuple[Literal['any_ancestor', 'direct_parent'], ...] = ()
    rooted: bool = False
    occurrence: int | None = Field(default=None, strict=True, ge=1)

    @model_validator(mode='after')
    def complete_edges(self):
        if len(self.edges) != len(self.names) - 1:
            raise ValueError('Every adjacent author name requires its declared relationship')
        return self


class UnscopedLocation(Strict):
    kind: Literal['unscoped'] = 'unscoped'


class UnresolvedLocation(Strict):
    kind: Literal['unresolved'] = 'unresolved'
    reason: str = Field(min_length=1)


ScopeExpression = Annotated[NamedScopePath | UnscopedLocation | UnresolvedLocation,
    Field(discriminator='kind')]


@dataclass(frozen=True)
class BoundScope:
    status: Literal['unscoped', 'matched', 'missing', 'unsupported']
    heading_indices: tuple[int, ...]
    paragraph_anchors: tuple[str, ...]


def name_key(text: str) -> str:
    """Reference lookup convention; source bytes and occurrence identity stay exact.

    Do NOT remove quotes here. A source title containing quote characters is
    different from the same title without them. Only author syntax is unquoted.
    """
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


_QUOTES = {'"': '"', "'": "'", '“': '”', '‘': '’', '«': '»', '`': '`'}


class AuthorLocationQuote(Strict):
    """Python string indices into the admitted dialogue followed by the request."""

    utterance_index: int = Field(strict=True, ge=0)
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, gt=0)
    text: str = Field(min_length=1)

    def verify(self, request: str, dialogue: tuple[RetrievalDialogue, ...]) -> str:
        if self.utterance_index == len(dialogue):
            utterance = request
        elif self.utterance_index < len(dialogue) and dialogue[self.utterance_index].role == 'user':
            utterance = dialogue[self.utterance_index].content
        else:
            raise ValueError('Location evidence must come from an admitted author utterance')
        if (not self.start < self.end <= len(utterance)
                or utterance[self.start:self.end] != self.text or self.text != self.text.strip()):
            raise ValueError('Location evidence does not match its exact author quote')
        if ((self.start and _word_member(utterance[self.start - 1]) and _word_member(self.text[0]))
                or (self.end < len(utterance) and _word_member(self.text[-1]) and _word_member(utterance[self.end]))):
            raise ValueError('Location evidence cannot cut a word')
        _require_quote_boundaries(utterance, self.start, self.end)
        return self.text


def _word_member(char: str) -> bool:
    return char == '_' or unicodedata.category(char)[0] in 'LMN'


def _require_quote_boundaries(utterance: str, start: int, end: int) -> None:
    closing = None
    escaped = False
    for index, char in enumerate(utterance[:end]):
        if index == start and closing is not None:
            raise ValueError('Location evidence cannot start within a quoted name')
        follows_word = index > 0 and _word_member(utterance[index - 1])
        joins_word = follows_word and index + 1 < len(utterance) and _word_member(utterance[index + 1])
        if closing is not None:
            if not escaped and char == closing and not (char in {"'", '’'} and joins_word):
                closing = None
            escaped = not escaped and char == '\\'
        elif char in _QUOTES and not (char == "'" and follows_word):
            closing = _QUOTES[char]
            escaped = False
        elif start < index < end - 1 and char in '.!?;':
            raise ValueError('Location evidence cannot cross an unquoted sentence boundary')
    if closing is not None:
        raise ValueError('Location evidence cannot end within a quoted name')


def _unquote(text: str) -> tuple[str, bool]:
    text = text.strip()
    if len(text) >= 2 and _QUOTES.get(text[0]) == text[-1]:
        closing, escaped, value = text[-1], False, []
        for index, char in enumerate(text[1:], 1):
            if escaped:
                if char not in {closing, '\\'}:
                    value.append('\\')
                value.append(char)
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == closing:
                if index == len(text) - 1:
                    return ''.join(value), True
                break  # Separate quoted components are not one outer quote.
            else:
                value.append(char)
    return text, False


def literal_reference(text: str, *, path: bool, quoted: bool = False,
                      rooted: bool = False) -> NamedScopePath:
    """Compile the literal grammar explicitly selected by the interpreter.

    A path has slash-separated literal names, with quoted component names able
    to contain slashes. The caller supplies `quoted` only from actual enclosing
    author quote boundaries when the selected substring excludes those quotes.
    This function does not inspect a request to decide whether it is a path.
    """
    value, outer_quotes = _unquote(text)
    if path and (outer_quotes or quoted) and '/' in value:
        raise ValueError('A wholly quoted slash title cannot be interpreted as a path')
    if not path:
        if '/' in value and not (quoted or outer_quotes):
            raise ValueError('An unquoted slash cannot be silently treated as one literal title')
        if not name_key(value):
            raise ValueError('A literal reference requires a nonempty name')
        return NamedScopePath(names=(LiteralScopeName(text=value),), rooted=rooted)
    parts, current, closing = [], [], None
    component_closed = False
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
        elif char == '\\' and closing is not None:
            # Preserve data. This flag only keeps an escaped quote from ending
            # the declared quoted component; it is not general text scrubbing.
            current.append(char)
            escaped = True
        elif closing is not None:
            current.append(char)
            if char == closing:
                closing = None
                component_closed = True
        elif char in _QUOTES and not ''.join(current).strip():
            current.append(char)
            closing = _QUOTES[char]
        elif char == '/':
            part, _ = _unquote(''.join(current))
            if not name_key(part):
                raise ValueError('A literal path cannot omit a named component')
            parts.append(part)
            current = []
            component_closed = False
        else:
            if component_closed and not char.isspace():
                raise ValueError('A quoted path component must end before the separator')
            current.append(char)
    if closing is not None or escaped:
        raise ValueError('A literal path has an unterminated quoted component')
    part, _ = _unquote(''.join(current))
    if not name_key(part):
        raise ValueError('A literal path cannot omit its last component')
    parts.append(part)
    if len(parts) > 6:
        raise ValueError('A literal path exceeds the complete six-level heading grammar')
    return NamedScopePath(names=tuple(LiteralScopeName(text=p) for p in parts),
        edges=('direct_parent',) * (len(parts) - 1), rooted=rooted)


def source_heading_inventory(capture, catalog):
    """Source-only names and occurrence paths; model views omit indices/ranges."""
    from .plan_contextual_targets import anchor_groups
    from .plan_placement import _placement_headings
    catalog.require_original(capture)
    nodes = json.loads(capture.editor_json)['content']
    groups = anchor_groups(capture, catalog)
    paragraphs = [(row['selector'], entries[0].source_root_index)
        for row, entries in groups if row['kind'] == 'paragraph']
    titles, headings, stack = {}, [], []
    for heading in _placement_headings(nodes):
        # Match the owning heading projection, preserving literal title bytes
        # in families rather than parsing the delimiter-joined legacy label.
        title = ''.join(part['text'] for part in nodes[heading['index']].get('content', [])
            if isinstance(part, dict) and part.get('type') == 'text' and isinstance(part.get('text'), str))
        if title not in titles:
            titles[title] = f'title{len(titles)}'
        while stack and stack[-1][0] >= heading['level']:
            stack.pop()
        stack.append((heading['level'], title))
        headings.append(dict(index=heading['index'], path=tuple(t for _, t in stack),
            anchors=tuple(alias for alias, index in paragraphs
                if heading['index'] < index < heading['end'])))
    return dict(titles=tuple(dict(selector=alias, text=title) for title, alias in titles.items()),
        headings=tuple(headings), paragraphs=tuple(alias for alias, _ in paragraphs))


def _path_matches(path, keys, edges, rooted):
    """A complete embedding ending at this primary occurrence, never a range join."""
    if len(path) < len(keys) or name_key(path[-1]) not in keys[-1]:
        return False
    def previous(component, position):
        if component == 0:
            return not rooted or position == 0
        candidates = (position - 1,) if edges[component - 1] == 'direct_parent' else range(position)
        return any(index >= 0 and name_key(path[index]) in keys[component - 1]
            and previous(component - 1, index) for index in candidates)
    return previous(len(keys) - 1, len(path) - 1)


def bind_scope(capture, catalog, scope: ScopeExpression, *, document_title: str | None,
               description_matches: dict[int, tuple[str, ...]] | None = None,
               allow_ordinal: bool = False) -> BoundScope:
    """Bind every mandatory name before expanding actual primary-heading ranges.

    `document_title` is supplied by the frozen Content owner, not an editor H1.
    This helper supplies no producer proof or mutation capability. Its caller
    must validate the actual interpretation and later matcher at their owners.
    """
    inventory = source_heading_inventory(capture, catalog)
    if isinstance(scope, UnscopedLocation):
        return BoundScope('unscoped', (), inventory['paragraphs'])
    if isinstance(scope, UnresolvedLocation) or scope.occurrence is not None and not allow_ordinal:
        return BoundScope('unsupported', (), ())
    matches = description_matches or {}
    descriptions = {i for i, component in enumerate(scope.names) if isinstance(component, DescribedScopeName)}
    if set(matches) != descriptions:
        raise ValueError('Only every declared description may receive semantic title matches')
    offered = {row['selector']: row['text'] for row in inventory['titles']}
    keys = []
    for i, component in enumerate(scope.names):
        if isinstance(component, LiteralScopeName):
            keys.append({name_key(component.text)})
        elif isinstance(component, DocumentTitleScopeName):
            keys.append({name_key(document_title)} if document_title is not None else set())
        else:
            selected = matches[i]
            if len(set(selected)) != len(selected) or set(selected) - offered.keys():
                raise ValueError('Foreign or duplicate semantic title nomination')
            keys.append({name_key(offered[alias]) for alias in selected})
    selected = [heading for heading in inventory['headings']
        if _path_matches(heading['path'], keys, scope.edges, scope.rooted)]
    if scope.occurrence is not None:
        selected = selected[scope.occurrence - 1:scope.occurrence]
    # Union ranges only AFTER joining the primary occurrence to ALL constraints.
    anchors = {alias for heading in selected for alias in heading['anchors']}
    return BoundScope('matched' if selected else 'missing',
        tuple(heading['index'] for heading in selected),
        tuple(alias for alias in inventory['paragraphs'] if alias in anchors))
