"""Author references and complete source binding; none of these values is authority.

The interpreter owns meaning. This module compiles declared literal references
and joins their names to actual heading occurrences in the frozen editor. It
never chooses an available replacement for an unmatched component.
"""
from __future__ import annotations

import json
import re
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


class ScopeWithExclusion(Strict):
    kind: Literal['scope_with_exclusion'] = 'scope_with_exclusion'
    positive: NamedScopePath
    excluded: NamedScopePath


ScopeExpression = Annotated[NamedScopePath | ScopeWithExclusion | UnscopedLocation | UnresolvedLocation,
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

    def _utterance(self, request: str, dialogue: tuple[RetrievalDialogue, ...]) -> str:
        if self.utterance_index == len(dialogue):
            return request
        if self.utterance_index < len(dialogue) and dialogue[self.utterance_index].role == 'user':
            return dialogue[self.utterance_index].content
        raise ValueError('Location evidence must come from an admitted author utterance')

    def verify(self, request: str, dialogue: tuple[RetrievalDialogue, ...]) -> str:
        utterance = self._utterance(request, dialogue)
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


ScopeGrammar = Literal[
    'literal_name', 'literal_path', 'natural_path', 'document_title', 'description', 'exclusion']


class AuthorScopeHypothesis(Strict):
    """One replayable author quote and its separately declared grammar."""

    evidence: AuthorLocationQuote
    grammar: ScopeGrammar

    def compile(self, request: str, dialogue: tuple[RetrievalDialogue, ...]) -> NamedScopePath | ScopeWithExclusion:
        quote = self.evidence.verify(request, dialogue)
        if _scope_syntax(quote).rstrip().endswith(('.', '!', '?', ';')):
            raise ValueError('Unquoted closing punctuation is not part of a scope reference')
        utterance = self.evidence._utterance(request, dialogue)
        for contrast in _scope_directives(utterance):
            start, end = _trimmed_span(utterance, contrast.span())
            if (self.evidence.start < end and self.evidence.end > start
                    and ((self.evidence.start, self.evidence.end) != (start, end) or self.grammar != 'exclusion')):
                raise ValueError('Location evidence must preserve both parts of an explicit scope contrast')
        before = utterance[:self.evidence.start].rstrip()
        after = utterance[self.evidence.end:].lstrip()
        if before.endswith('/') or after.startswith('/'):
            raise ValueError('Location evidence cannot omit a slash-connected path component')
        if (_RELATION_BEFORE.search(before) or _RELATION_AFTER.match(after)):
            raise ValueError('Location evidence cannot omit a natural path operand')
        if _EXCLUSION_BEFORE.search(before) or _EXCLUSION_AFTER.match(after):
            raise ValueError('Location evidence cannot omit an exclusion operand')
        if self.grammar == 'exclusion':
            return _compile_exclusion(quote)
        path = _compile_scope_expression(quote, self.grammar)
        if after.startswith(',') and _has_excluded_restatement(path, after[1:]):
            raise ValueError('Location evidence cannot omit a restated exclusion')
        return path


_TITLE_REFERENCE = re.compile(
    r'(?:(?:the )?section (?:with |having )(?:the )?)?'
    r'same (?:name|title) as (?:this|the current) (?:page|document)', re.IGNORECASE)
_DESCRIPTION_REFERENCE = re.compile(r'(?:the )?section about\s+(.+)', re.IGNORECASE)
_NATURAL_CONNECTORS = re.compile(r'(?<=\s)(directly under|whose parent is|inside)(?=\s)', re.IGNORECASE)
_RELATION_BEFORE = re.compile(r'\b(?:directly under|whose parent is)$', re.IGNORECASE)
_RELATION_AFTER = re.compile(r'^(?:section\s+)?(?:directly under|whose parent is|inside)\b', re.IGNORECASE)
_EXCLUSION_BEFORE = re.compile(r'\b(?:rather than|except)(?:\s+the one inside)?$', re.IGNORECASE)
_EXCLUSION_AFTER = re.compile(r'^,?\s*(?:rather than|except)\b', re.IGNORECASE)
_EXCLUSION_SEPARATOR = re.compile(r'\b(?:rather than|except)\b', re.IGNORECASE)
_SCOPE_DIRECTIVE_CONTRAST = re.compile(
    r'\buse\b(?P<positive>[^,.!?;:\n]+?)(?:\bfor this (?:change|edit))?,\s*not\b'
    r'(?P<excluded>[^,.!?;:\n]+)(?=[,:.!?;\n]|$)', re.IGNORECASE)
_INCLUDE_DESCENDANTS = re.compile(
    r',\s*including\s+(?:all\s+)?(?:its\s+)?(?:subsections|descendant sections)\b', re.IGNORECASE)
_NAMED_SCOPE_DECLARATIONS = (
    re.compile(r'\buse\b(?P<label>[^,.!?;:\n]+?)\bfor (?:this|the next) (?:edit|change)(?=[:.!?;\n]|$)',
        re.IGNORECASE),
    re.compile(r'(?:^|[,;:\n])(?P<label>[^,.!?;:\n]+?)\bis\s+the\s+(?:section|heading)\s+I\s+mean\b',
        re.IGNORECASE),
)
_DEMONSTRATIVE_SCOPE = re.compile(r'(?:that|this|the same)(?:\s+(?:section|heading|part))?', re.IGNORECASE)
_ANCESTOR_EXCLUSION = re.compile(r'^the one inside\s+', re.IGNORECASE)
_COMPOUND_REFERENCE = re.compile(r'\b(?:either|or|both|and|except|rather than)\b', re.IGNORECASE)
_LOCATION_CLAUSE = re.compile(r'\b(?:paragraph|heading)\s+(?:in|inside|under)\b', re.IGNORECASE)
_ORDINAL_REFERENCE = re.compile(
    r'^(?:the\s+)?(?:first|second|third|fourth|fifth|last|\d+(?:st|nd|rd|th))\b', re.IGNORECASE)


def _scope_syntax(text: str) -> str:
    """Keep original indices while treating quoted name content as data."""
    result = []
    closing = None
    escaped = False
    for index, char in enumerate(text):
        if closing is not None:
            result.append(' ')
            joins_word = (char in {"'", '’'} and index and index + 1 < len(text)
                and _word_member(text[index - 1]) and _word_member(text[index + 1]))
            if char == closing and not escaped and not joins_word:
                closing = None
            escaped = not escaped and char == '\\'
        elif char in _QUOTES and not (char == "'" and index and _word_member(text[index - 1])):
            closing = _QUOTES[char]
            result.append(' ')
        else:
            result.append(char)
    return ''.join(result)


def _scope_directives(text: str):
    syntax = _scope_syntax(text)
    for match in _SCOPE_DIRECTIVE_CONTRAST.finditer(syntax):
        operands = (text[match.start(name):match.end(name)].strip() for name in ('positive', 'excluded'))
        if (_active_declaration(syntax, match.start())
                and all(value and (value[0].isupper() or value[0] in _QUOTES) for value in operands)):
            yield match


def _active_declaration(syntax: str, start: int) -> bool:
    prefix = re.split(r'[.!?;:\n]', syntax[:start])[-1].strip().casefold()
    return (prefix in {'', 'please', 'instead', 'please instead'}
        or re.fullmatch(r'for (?:this|the next) (?:edit|change),?\s*(?:please)?', prefix) is not None)


def _declared_scope_spans(text: str):
    syntax = _scope_syntax(text)
    for pattern in _NAMED_SCOPE_DECLARATIONS:
        for match in pattern.finditer(syntax):
            start, end = _trimmed_span(text, match.span('label'))
            label = text[start:end]
            if (_active_declaration(syntax, match.start() if pattern is _NAMED_SCOPE_DECLARATIONS[0] else start)
                    and label and (label[0].isupper() or label[0] in _QUOTES)):
                yield start, end


def explicit_contrast_conflict(question: str, scope: ScopeExpression) -> bool:
    for directive in _scope_directives(question):
        start, end = _trimmed_span(question, directive.span())
        try:
            required = _compile_exclusion(question[start:end])
        except ValueError:
            return True
        if scope != required:
            return True
    return False


def explicit_scope_conflict(question: str, scope: ScopeExpression) -> bool:
    if explicit_contrast_conflict(question, scope):
        return True
    for start, end in _declared_scope_spans(question):
        try:
            required = _declared_path(question[start:end])
        except ValueError:
            return True
        if scope != required:
            return True
    return False


def _compile_scope_expression(text: str, grammar: str, depth: int = 1) -> NamedScopePath:
    if depth > 6:
        raise ValueError('A scope hypothesis exceeds the complete six-level heading grammar')
    if grammar == 'document_title':
        if not _TITLE_REFERENCE.fullmatch(text):
            raise ValueError('Document-title evidence must explicitly refer to the current page title')
        return NamedScopePath(names=(DocumentTitleScopeName(),))
    syntax = _scope_syntax(text)
    if _DEMONSTRATIVE_SCOPE.fullmatch(syntax.strip()):
        raise ValueError('A demonstrative scope requires an earlier author reference')
    if _INCLUDE_DESCENDANTS.search(syntax):
        raise ValueError('Descendant coverage is a scope qualifier, not part of the heading label')
    if _COMPOUND_REFERENCE.search(syntax):
        raise ValueError('A single scope hypothesis cannot omit compound or excluded operands')
    if grammar == 'description':
        match = _DESCRIPTION_REFERENCE.fullmatch(text)
        if match is None:
            raise ValueError('Description evidence must describe an existing section explicitly')
        return NamedScopePath(names=(DescribedScopeName(text=match[1]),))
    if _TITLE_REFERENCE.fullmatch(text) or _DESCRIPTION_REFERENCE.fullmatch(text):
        raise ValueError('Typed reference evidence cannot be interpreted as a literal name')
    if _LOCATION_CLAUSE.search(syntax):
        raise ValueError('Literal scope evidence cannot include a separate location clause')
    if _ORDINAL_REFERENCE.match(syntax):
        raise ValueError('An ordinal scope requires an explicit occurrence interpretation')
    if grammar == 'natural_path':
        match = _NATURAL_CONNECTORS.search(syntax)
        if match is None:
            raise ValueError('A natural path must preserve its declared relationship')
        child_text = re.sub(r'\s+section$', '', text[:match.start()].rstrip(), flags=re.IGNORECASE)
        if child_text[:4].casefold() == 'the ':
            child_text = child_text[4:]
        child = _compile_scope_expression(child_text, 'literal_name', depth + 1)
        parent_text = text[match.end():].lstrip()
        parent_syntax = _scope_syntax(parent_text)
        parent_grammar = ('natural_path' if _NATURAL_CONNECTORS.search(parent_syntax) else
            'document_title' if _TITLE_REFERENCE.fullmatch(parent_text) else
            'literal_path' if '/' in parent_syntax else 'literal_name')
        parent = _compile_scope_expression(parent_text, parent_grammar, depth + 1)
        edge = 'any_ancestor' if match[1].casefold() == 'inside' else 'direct_parent'
        return NamedScopePath(names=(*parent.names, *child.names), edges=(*parent.edges, edge))
    if _NATURAL_CONNECTORS.search(syntax) or (grammar == 'literal_name' and '/' in syntax):
        raise ValueError('Literal scope evidence cannot omit its path structure')
    if grammar == 'literal_name':
        return literal_reference(text, path=False)
    separators = [index for index, char in enumerate(syntax) if char == '/']
    if not separators:
        raise ValueError('Literal path evidence must include its path separator')
    positions = [-1, *separators, len(text)]
    for start, end in zip(positions, positions[1:]):
        component = text[start + 1:end].strip()
        if _ORDINAL_REFERENCE.match(_scope_syntax(component)):
            raise ValueError('An ordinal scope requires an explicit occurrence interpretation')
        if _TITLE_REFERENCE.fullmatch(component) or _DESCRIPTION_REFERENCE.fullmatch(component):
            raise ValueError('Typed reference evidence cannot be interpreted as a literal name')
    return literal_reference(text, path=True)


def _path_grammar(text: str, syntax: str) -> ScopeGrammar:
    if _TITLE_REFERENCE.fullmatch(text):
        return 'document_title'
    if _DESCRIPTION_REFERENCE.fullmatch(text):
        return 'description'
    if _NATURAL_CONNECTORS.search(syntax):
        return 'natural_path'
    return 'literal_path' if '/' in syntax else 'literal_name'


def _declared_path(text: str) -> NamedScopePath:
    return _compile_scope_expression(text, _path_grammar(text, _scope_syntax(text)))


def _path_key(path: NamedScopePath) -> tuple:
    return (tuple((n.kind, name_key(getattr(n, 'text', ''))) for n in path.names), path.edges)


def _compile_exclusion(text: str) -> ScopeWithExclusion:
    syntax = _scope_syntax(text)
    directive = _SCOPE_DIRECTIVE_CONTRAST.fullmatch(syntax)
    if directive is not None:
        start, end = directive.span('positive')
        positive = _declared_path(text[start:end].strip())
        start, end = directive.span('excluded')
        return ScopeWithExclusion(positive=positive, excluded=_declared_path(text[start:end].strip()))
    separators = list(_EXCLUSION_SEPARATOR.finditer(syntax))
    if len(separators) != 1:
        raise ValueError('Exclusion evidence requires one explicit excluded operand')
    separator = separators[0]
    positive_text = text[:separator.start()].rstrip().rstrip(',').rstrip()
    comma = _scope_syntax(positive_text).find(',')
    positive = _declared_path(positive_text if comma < 0 else positive_text[:comma].strip())
    if comma >= 0 and _path_key(positive) != _path_key(_declared_path(positive_text[comma + 1:].strip())):
        raise ValueError('A restated path must preserve every primary scope constraint')
    excluded_text = text[separator.end():].strip()
    if not excluded_text:
        raise ValueError('Exclusion evidence must preserve its excluded path')
    parent = _ANCESTOR_EXCLUSION.match(excluded_text)
    if parent is not None:
        ancestor = _declared_path(excluded_text[parent.end():])
        excluded = NamedScopePath(names=(*ancestor.names, positive.names[-1]),
            edges=(*ancestor.edges, 'any_ancestor'))
    else:
        excluded = _declared_path(excluded_text)
    return ScopeWithExclusion(positive=positive, excluded=excluded)


def _has_excluded_restatement(path: NamedScopePath, after: str) -> bool:
    syntax = _scope_syntax(after)
    clause = re.split(r'[.!?;]', syntax, maxsplit=1)[0]
    separator = _EXCLUSION_SEPARATOR.search(clause)
    if separator is None:
        return False
    try:
        return _path_key(path) == _path_key(_declared_path(after[:separator.start()].strip()))
    except ValueError:
        return False


_SCOPE_TOKEN = re.compile(r"\w+(?:['’]\w+)*|[^\w\s]", re.UNICODE)
_SCOPE_START = re.compile(r'\b(?:in|within|under|inside)\b', re.IGNORECASE)
_SCOPE_END = re.compile(r'\b(?:paragraph|heading|section)\b', re.IGNORECASE)
_PROSE_LOCATION = r'(?:paragraph|passage|instruction|step|note)'
_PROSE_DESCRIPTION = r'(?:about|describing|explaining|detailing|concerning)'
_QUOTED_PROSE_CUE = r'(?:that (?:says|reads)|containing(?: the exact words)?|with the text)'
_QUALIFIED_PROSE_LOCATION = re.compile(
    r'\b(?:before|after)\s+[^,.!?;]+?\b(?:paragraph|passage|instruction|step|note)\s+'
    r'(?:in|inside|under|within)\s+([^,.!?;]+)', re.IGNORECASE)
_NAMED_PROSE_LOCATOR = re.compile(
    r'\b(?i:before|after)\s+(?P<article>the\s+)?(?P<label>\w[^,.!?;/\n]*?)\s+'
    rf'(?i:{_PROSE_LOCATION})\s+(?i:{_PROSE_DESCRIPTION}|{_QUOTED_PROSE_CUE})\b')
_NOMINAL_PROSE_LOCATOR = re.compile(
    r'\b(?i:before|after)\s+(?:the\s+)?(?P<label>\w[^,.!?;/\n]*?)\s+'
    rf'(?i:{_PROSE_LOCATION})\b(?!\s+(?i:{_PROSE_DESCRIPTION}|{_QUOTED_PROSE_CUE}|in|under|within|inside)\b)')


def _paragraph_label_match(question: str):
    matches = list(_NAMED_PROSE_LOCATOR.finditer(_scope_syntax(question)))
    if len(matches) != 1:
        return None
    match = matches[0]
    label = match['label']
    if not label[0].isupper() or _NATURAL_CONNECTORS.search(label) or _COMPOUND_REFERENCE.search(label):
        return None
    return match


def _nominal_scope_prefixes(text: str) -> tuple[str, tuple[tuple[int, int], ...]]:
    matches = list(_NOMINAL_PROSE_LOCATOR.finditer(_scope_syntax(text)))
    if len(matches) != 1:
        return '', ()
    match = matches[0]
    start, end = match.span('label')
    label = text[start:end]
    if not label[0].isupper() or _COMPOUND_REFERENCE.search(_scope_syntax(label)):
        return '', ()
    prefixes = tuple((start, prefix_end) for word in _SCOPE_TOKEN.finditer(label)
        if word.start() > 0 and word[0].islower()
        and (prefix_end := start + len(label[:word.start()].rstrip())) > start)
    return label, prefixes


def nominal_scope_needs_review(question: str, scope: ScopeExpression) -> bool:
    label, prefixes = _nominal_scope_prefixes(question)
    return (bool(prefixes) and isinstance(scope, NamedScopePath) and len(scope.names) == 1
        and isinstance(scope.names[0], LiteralScopeName) and name_key(scope.names[0].text) == name_key(label))


def nominal_scope_subject(hypothesis: AuthorScopeHypothesis, question: str,
                          dialogue: tuple[RetrievalDialogue, ...]) -> str | None:
    evidence = hypothesis.evidence
    label, prefixes = _nominal_scope_prefixes(question)
    if evidence.utterance_index != len(dialogue) or (evidence.start, evidence.end) not in prefixes:
        return None
    return question[evidence.end:evidence.start + len(label)].strip() or None


def paragraph_label_conflict(question, scope, capture, catalog) -> bool:
    """Preserve an explicit label and refuse an ambiguous unquoted article."""
    match = _paragraph_label_match(question)
    path = scope.positive if isinstance(scope, ScopeWithExclusion) else scope
    if match is None:
        label, prefixes = _nominal_scope_prefixes(question)
        if (prefixes and isinstance(path, NamedScopePath) and len(path.names) == 1
                and isinstance(path.names[0], LiteralScopeName)):
            alternatives = {name_key(label), *(name_key(question[start:end]) for start, end in prefixes)}
            if name_key(path.names[0].text) in alternatives:
                present = {name_key(heading['path'][-1])
                    for heading in source_heading_inventory(capture, catalog)['headings']}
                return len(alternatives & present) > 1
        return False
    if (not isinstance(path, NamedScopePath) or not isinstance(path.names[-1], LiteralScopeName)
            or name_key(path.names[-1].text) != name_key(match['label'])):
        return True
    if match['article'] is None or len(path.names) != 1:
        return False
    alternative = name_key(match['article'] + match['label'])
    return any(name_key(heading['path'][-1]) == alternative
        for heading in source_heading_inventory(capture, catalog)['headings'])


def unsupported_paragraph_scope(question: str) -> bool:
    """Recognize explicit location constraints outside the supported path grammar."""
    return any(clause.count('/') > 5
        or re.search(r'\b(?:either\b.+\bor|both\b.+\band)\b', clause, re.IGNORECASE)
        for clause in _QUALIFIED_PROSE_LOCATION.findall(_scope_syntax(question)))


def explicit_paragraph_locator(question: str, relation: str) -> str | None:
    """Keep the author's exact locator when one before/after clause supplies it."""
    if relation not in {'before_paragraph', 'after_paragraph'}:
        return None
    side = relation.removesuffix('_paragraph')
    matches = list(re.finditer(rf'\b{side}\s+[^,.!?;\n]*?\b'
        rf'{_PROSE_LOCATION}\s+{_PROSE_DESCRIPTION}\b([^,.!?;\n]+)',
        _scope_syntax(question), re.IGNORECASE))
    if len(matches) != 1:
        return None
    start, end = matches[0].span(1)
    return question[start:end].strip() or None


def quoted_paragraph_locator(question: str, relation: str) -> tuple[str, bool] | None:
    """Return a quoted excerpt and whether its locator clause is complete."""
    if relation not in {'before_paragraph', 'after_paragraph'}:
        return None
    side = relation.removesuffix('_paragraph')
    pattern = rf'\b{side}\s+[^,.!?;\n]*?\b{_PROSE_LOCATION}\s+{_QUOTED_PROSE_CUE}\b'
    matches = list(re.finditer(pattern, _scope_syntax(question), re.IGNORECASE))
    if len(matches) != 1:
        return None
    tail = question[matches[0].end():].lstrip()
    closing = _QUOTES.get(tail[0]) if tail else None
    if closing is None:
        return None
    escaped = False
    for index, char in enumerate(tail[1:], start=1):
        joins_word = (char in {"'", '’'} and index + 1 < len(tail)
            and _word_member(tail[index - 1]) and _word_member(tail[index + 1]))
        if char == closing and not escaped and not joins_word:
            value, quoted = _unquote(tail[:index + 1])
            if not quoted or not value.strip():
                return None
            suffix = tail[index + 1:].strip()
            complete = suffix in {'', '.', '!', '?'} or re.match(
                r',\s*(?:please\s+)?(?:add|insert|place|put|write|draft|include)\b',
                suffix, re.IGNORECASE) is not None
            return value, complete
        escaped = not escaped and char == '\\'
    return None


def contains_exact_paragraph_excerpt(paragraph: str, excerpt: str) -> bool:
    """Match full words, punctuation and line breaks in the frozen paragraph."""
    text = unicodedata.normalize('NFC', paragraph.replace('\r\n', '\n'))
    needle = unicodedata.normalize('NFC', excerpt.replace('\r\n', '\n'))
    if not needle:
        return False
    for match in re.finditer(re.escape(needle), text):
        left = (match.start() > 0 and _word_member(needle[0]) and _word_member(text[match.start() - 1]))
        right = (match.end() < len(text) and _word_member(needle[-1]) and _word_member(text[match.end()]))
        if not left and not right:
            return True
    return False


def explicit_direction_options(question: str, *, allow_plain_prose: bool = False) -> tuple[str, ...]:
    """Offer structural interpretations of one explicit editing direction."""
    syntax = _scope_syntax(question)
    directions = re.findall(r'\b(before|after)\b', syntax, re.IGNORECASE)
    adjacent = re.search(r'\b(?:just|directly|immediately|right)\s+(before|after)\b', syntax, re.IGNORECASE)
    if (len(directions) != 1
            or not re.search(r'\b(?:add|insert|place|put|append)\b', syntax, re.IGNORECASE)):
        return ()
    if not adjacent:
        prose = re.search(rf'\b(?:before|after)\s+(?:(?:the|that|this)\s+)?'
            rf'(?:(?:existing|current)\s+)?{_PROSE_LOCATION}\b', syntax, re.IGNORECASE)
        return (f'{directions[0].casefold()}_paragraph',) if allow_plain_prose and prose else ()
    if adjacent[1].casefold() == 'before':
        return 'before_paragraph', 'before_heading'
    return 'after_paragraph', 'after_heading', 'after_section'


def _trimmed_span(text: str, span: tuple[int, int]) -> tuple[int, int]:
    start, end = span
    value = text[start:end]
    return start + len(value) - len(value.lstrip()), start + len(value.rstrip())


def author_scope_hypotheses(request: str, dialogue: tuple[RetrievalDialogue, ...], *,
                            max_span_attempts: int) -> dict[str, AuthorScopeHypothesis]:
    """Offer checked author-only hypotheses. Capacity exhaustion grants no partial offer."""
    if max_span_attempts < 1:
        raise ValueError('Author scope hypothesis budget must be positive')
    hypotheses = {}
    attempts = 0
    utterances = [(i, row.content) for i, row in enumerate(dialogue) if row.role == 'user']
    utterances.append((len(dialogue), request))
    for utterance_index, text in utterances:
        syntax = _scope_syntax(text)
        label = _paragraph_label_match(text)
        tokens = list(_SCOPE_TOKEN.finditer(text))
        spans = set()

        def offer(start: int, end: int) -> None:
            nonlocal attempts
            if start >= end or (start, end) in spans:
                return
            attempts += 1
            if attempts > max_span_attempts:
                raise ValueError('Author scope hypotheses exceed the configured span budget')
            spans.add((start, end))

        for marker in _SCOPE_END.finditer(syntax):
            previous = next((token for token in reversed(tokens) if token.end() <= marker.start()), None)
            if previous is not None:
                for token in tokens:
                    if token.start() >= previous.end():
                        break
                    offer(token.start(), previous.end())
        for marker in _SCOPE_START.finditer(syntax):
            first = next((i for i, token in enumerate(tokens) if token.start() >= marker.end()), len(tokens))
            if first < len(tokens):
                starts = [tokens[first].start()]
                if tokens[first][0].casefold() == 'the' and first + 1 < len(tokens):
                    starts.append(tokens[first + 1].start())
                for token in reversed(tokens):
                    if token.end() <= starts[0]:
                        break
                    for start in starts:
                        offer(start, token.end())
        for marker in _TITLE_REFERENCE.finditer(syntax):
            offer(marker.start(), marker.end())
        for span in _declared_scope_spans(text):
            offer(*span)
        for span in _nominal_scope_prefixes(text)[1]:
            offer(*span)
        contrasts = {_trimmed_span(text, match.span()) for match in _scope_directives(text)}
        for span in sorted(contrasts):
            offer(*span)

        for start, end in sorted(spans):
            if label is not None and end == label.end('label') and start != label.start('label'):
                continue
            quote = text[start:end]
            fragment = syntax[start:end]
            grammar = ('exclusion' if _EXCLUSION_SEPARATOR.search(fragment)
                or (start, end) in contrasts else _path_grammar(quote, fragment))
            evidence = AuthorLocationQuote(utterance_index=utterance_index, start=start, end=end, text=quote)
            hypothesis = AuthorScopeHypothesis(evidence=evidence, grammar=grammar)
            try:
                hypothesis.compile(request, dialogue)
            except ValueError:
                continue
            hypotheses[f'scope{len(hypotheses)}'] = hypothesis
    return hypotheses


def author_scope_offer_view(request: str, dialogue: tuple[RetrievalDialogue, ...],
                            hypotheses: dict[str, AuthorScopeHypothesis], *,
                            include_quote_context: bool = False) -> dict:
    """Project only dialogue, verified author quotes, and local hypothesis aliases."""
    offers = {}
    for index, (alias, hypothesis) in enumerate(hypotheses.items()):
        if alias != f'scope{index}':
            raise ValueError('Author scope offers require consecutive local aliases')
        scope = hypothesis.compile(request, dialogue)
        evidence = hypothesis.evidence
        utterance = evidence._utterance(request, dialogue)
        quote = {'utterance': f'utterance{evidence.utterance_index}', 'text': evidence.text}
        if include_quote_context:
            quote.update(text_before=utterance[max(0, evidence.start - 32):evidence.start],
                text_after=utterance[evidence.end:evidence.end + 32])
        positive = scope.positive if isinstance(scope, ScopeWithExclusion) else scope
        offer = {'components': [name.model_dump() for name in positive.names],
            'edges': list(positive.edges), 'author_quote': quote}
        if isinstance(scope, ScopeWithExclusion):
            offer['excluded_path'] = {'components': [n.model_dump() for n in scope.excluded.names],
                'edges': list(scope.excluded.edges)}
        offers[alias] = offer
    return {'current_request': request, 'dialogue': [
        {'role': row.role, 'content': row.content} for row in dialogue], 'scope_hypotheses': offers}


def is_complete_scope_recovery(hypothesis: AuthorScopeHypothesis, request: str,
                               dialogue: tuple[RetrievalDialogue, ...]) -> bool:
    """Recover a whole verified scope clause without selecting one operand."""
    if hypothesis.grammar == 'exclusion':
        return True
    evidence = hypothesis.evidence
    text = evidence._utterance(request, dialogue)
    if (evidence.start, evidence.end) in _declared_scope_spans(text):
        return True
    utterance = _scope_syntax(text)
    clause_prefix = re.split(r'[.!?;:\n]', utterance[:evidence.start])[-1]
    prefix = clause_prefix.rsplit(',', 1)[-1]
    suffix = utterance[evidence.end:]
    introducer = re.search(r'\b(?:in|within|inside|under)\s+(the\s+)?$', prefix, re.IGNORECASE)
    label = evidence.text.strip()
    return (introducer is not None
        and (introducer[1] is None or label[0] in _QUOTES)
        and not label.startswith('the ')
        and _SCOPE_START.search(clause_prefix[:-len(prefix)]) is None
        and _COMPOUND_REFERENCE.search(prefix) is None
        and re.search(r'\bnot\b', prefix + _scope_syntax(label), re.IGNORECASE) is None
        and not re.match(r'\s*[,;:]?\s*(?:not|either|and not|in|inside|within|under|directly under|'
            r'whose parent is|except|rather than)\b', suffix, re.IGNORECASE)
        and re.match(r'\s*(?:(?:section|heading)\b\s*)?(?:[.!?;,:]|$)', suffix, re.IGNORECASE) is not None)


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
        stack.append((heading['level'], title, heading['index']))
        headings.append(dict(selector=f'heading{len(headings)}', index=heading['index'], end=heading['end'],
            path=tuple(title for _, title, _ in stack), occurrence_path=tuple(index for _, _, index in stack),
            anchors=tuple(alias for alias, index in paragraphs
                if heading['index'] < index < heading['end'])))
    return dict(titles=tuple(dict(selector=alias, text=title) for title, alias in titles.items()),
        headings=tuple(headings), paragraphs=tuple(alias for alias, _ in paragraphs))


def _path_matches(heading, keys, edges, rooted):
    """A complete embedding ending at this primary occurrence, never a range join."""
    path = heading['path']

    def matches(component, position):
        return (name_key(path[position]) in keys[component]
            or heading['occurrence_path'][position] in keys[component])

    if len(path) < len(keys) or not matches(len(keys) - 1, len(path) - 1):
        return False
    def previous(component, position):
        if component == 0:
            return not rooted or position == 0
        candidates = (position - 1,) if edges[component - 1] == 'direct_parent' else range(position)
        return any(index >= 0 and matches(component - 1, index)
            and previous(component - 1, index) for index in candidates)
    return previous(len(keys) - 1, len(path) - 1)


def bind_scope(capture, catalog, scope: ScopeExpression, *, document_title: str | None,
               description_matches: dict[int, tuple[str, ...]] | None = None,
               excluded_description_matches: dict[int, tuple[str, ...]] | None = None,
               allow_ordinal: bool = False) -> BoundScope:
    """Bind every mandatory name before expanding actual primary-heading ranges.

    `document_title` is supplied by the frozen Content owner, not an editor H1.
    This helper supplies no producer proof or mutation capability. Its caller
    must validate the actual interpretation and later matcher at their owners.
    """
    if isinstance(scope, ScopeWithExclusion):
        if document_title is None and any(isinstance(name, DocumentTitleScopeName) for name in scope.excluded.names):
            return BoundScope('unsupported', (), ())
        positive = bind_scope(capture, catalog, scope.positive, document_title=document_title,
            description_matches=description_matches, allow_ordinal=allow_ordinal)
        excluded = bind_scope(capture, catalog, scope.excluded, document_title=document_title,
            description_matches=excluded_description_matches, allow_ordinal=allow_ordinal)
        if positive.status == 'unsupported' or excluded.status == 'unsupported':
            return BoundScope('unsupported', (), ())
        if excluded_description_matches is not None and excluded.status != 'matched':
            return BoundScope('unsupported', (), ())
        # A named section excludes its subtree, including descendant heading
        # addresses as well as paragraphs in that same range.
        excluded_headings = set(excluded.heading_indices)
        ranges = [(row['index'], row['end']) for row in source_heading_inventory(capture, catalog)['headings']
            if row['index'] in excluded_headings]
        headings = tuple(i for i in positive.heading_indices
            if not any(start <= i < end for start, end in ranges))
        paragraphs = tuple(alias for alias in positive.paragraph_anchors if alias not in excluded.paragraph_anchors)
        return BoundScope('matched' if headings else 'missing', headings, paragraphs)
    if excluded_description_matches is not None:
        raise ValueError('An excluded description requires its own excluded path')
    inventory = source_heading_inventory(capture, catalog)
    if isinstance(scope, UnscopedLocation):
        return BoundScope('unscoped', (), inventory['paragraphs'])
    if isinstance(scope, UnresolvedLocation) or scope.occurrence is not None and not allow_ordinal:
        return BoundScope('unsupported', (), ())
    matches = description_matches or {}
    descriptions = {i for i, component in enumerate(scope.names) if isinstance(component, DescribedScopeName)}
    if set(matches) != descriptions:
        raise ValueError('Only every declared description may receive semantic title matches')
    offered = {row['selector']: row['index'] for row in inventory['headings']}
    keys = []
    for i, component in enumerate(scope.names):
        if isinstance(component, LiteralScopeName):
            keys.append({name_key(component.text)})
        elif isinstance(component, DocumentTitleScopeName):
            keys.append({name_key(document_title)} if document_title is not None else set())
        else:
            selected = matches[i]
            if len(set(selected)) != len(selected) or set(selected) - offered.keys():
                raise ValueError('Foreign or duplicate semantic heading nomination')
            keys.append({offered[alias] for alias in selected})
    selected = [heading for heading in inventory['headings']
        if _path_matches(heading, keys, scope.edges, scope.rooted)]
    if scope.occurrence is not None:
        selected = selected[scope.occurrence - 1:scope.occurrence]
    # Union ranges only AFTER joining the primary occurrence to ALL constraints.
    anchors = {alias for heading in selected for alias in heading['anchors']}
    return BoundScope('matched' if selected else 'missing',
        tuple(heading['index'] for heading in selected),
        tuple(alias for alias in inventory['paragraphs'] if alias in anchors))
