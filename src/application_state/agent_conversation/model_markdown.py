"""Project managed image Markdown into author-visible evidence for models."""

import re

from markdown_it import MarkdownIt


def _managed(destination: str | None) -> bool:
    return bool(destination and destination.startswith("dmb-media:"))


def _has_managed_image(tokens) -> bool:
    return any(
        (token.type == "image" and _managed(token.attrGet("src")))
        or _has_managed_image(token.children or ())
        for token in tokens
    )


def _visible_inline(tokens) -> str:
    parts = []
    for token in tokens:
        if token.type == "image":
            alt = _visible_inline(token.children or ()).strip()
            parts.append(f"[Image: {alt}]" if alt else "[Image]")
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append("\n")
        elif token.type in {"text", "code_inline", "html_inline"}:
            parts.append(token.content)
    return "".join(parts)


def project_model_markdown(markdown: str) -> str:
    """Keep source line numbers and strip only structurally identified image targets.

    APP continues to own the original source bytes and citation bindings. Affected
    inline blocks expose their readable text. Other blocks retain their Markdown.
    """
    if "dmb-media" not in markdown and "&" not in markdown:
        return markdown
    env = {}
    tokens = MarkdownIt("commonmark").parse(markdown, env)
    replacements = {
        tuple(reference["map"]): ""
        for reference in env.get("references", {}).values()
        if _managed(reference["href"])
    }
    for token in tokens:
        if token.type == "inline" and token.map and _has_managed_image(token.children or ()):
            replacements[tuple(token.map)] = _visible_inline(token.children or ())
    if not replacements:
        return markdown
    lines = re.split(r"(\r\n|\r|\n)", markdown)
    for (start, end), replacement in sorted(replacements.items(), reverse=True):
        # A multiline image or reference can collapse to one visible label.
        # Keep the consumed source lines so later evidence retains its location.
        projected = replacement.split("\n", maxsplit=end - start - 1)
        projected.extend([""] * (end - start - len(projected)))
        for index, value in enumerate(projected, start):
            lines[2 * index] = value
    return "".join(lines)


def _buddy_navigation(destination):
    """Recognize owned editor/citation controls, not arbitrary external links."""
    from urllib.parse import parse_qs, urlsplit
    from uuid import UUID
    if not isinstance(destination, str):
        return False
    try:
        url = urlsplit(destination)
        if (url.scheme not in {'', 'http', 'https'}
                or url.hostname not in {None, 'buddy.dungeonmind.net', 'localhost', '127.0.0.1'}):
            return False
        if url.path == '/build':
            values = parse_qs(url.query).get('documentId', [])
            if len(values) != 1:
                return False
            UUID(values[0])
            return True
        parts = url.path.strip('/').split('/')
        if (len(parts) == 10 and parts[:4] == ['api', 'live', 'agent', 'worlds']
                and parts[5:7] == ['conversation', 'turns']
                and parts[8] in {'native-body-excerpts', 'source-sections'}
                and parts[9].isdecimal()):
            UUID(parts[7])
            return True
    except (ValueError, AttributeError):
        return False
    return False


def _pdf_identity_field(children):
    """The extraction wrapper's standalone provenance field is host identity."""
    return (len(children) == 3 and children[0].type == 'text'
        and children[0].content.strip() == 'Original PDF SHA-256:'
        and children[1].type == 'code_inline' and len(children[1].content) == 64
        and all(char in '0123456789abcdefABCDEF' for char in children[1].content)
        and children[2].type == 'text' and children[2].content.strip() == '.')


def _retained_parser():
    from markdown_it.rules_inline.link import link
    from markdown_it.rules_inline.autolink import autolink
    from markdown_it.rules_inline.image import image
    parser = MarkdownIt('commonmark')

    def marked(rule, automatic=False):
        def run(state, silent):
            start, count = state.pos, len(state.tokens)
            label_end = (state.md.helpers.parseLinkLabel(state, start, True)
                         if not silent and not automatic and state.src[start] == '[' else None)
            accepted = rule(state, silent)
            if accepted and not silent:
                opened = next((i for i in range(count, len(state.tokens))
                               if state.tokens[i].type == 'link_open'), None)
                if opened is not None:
                    token = state.tokens[opened]
                    if _buddy_navigation(token.attrGet('href')):
                        token.meta['retained_navigation'] = dict(start=start, end=state.pos,
                            label_start=None if automatic else start + 1, label_end=label_end,
                            visible=_visible_inline(state.tokens[opened + 1:-1]),
                            title=token.attrGet('title'))
            return accepted
        return run

    def marked_image(state, silent):
        start, count = state.pos, len(state.tokens)
        label_end = (state.md.helpers.parseLinkLabel(state, start + 1, False)
                     if not silent and state.src.startswith('![', start) else None)
        accepted = image(state, silent)
        if accepted and not silent:
            token = next(item for item in state.tokens[count:] if item.type == 'image')
            token.meta['retained_image'] = dict(start=start, end=state.pos,
                label_start=start + 2, label_end=label_end,
                managed=_managed(token.attrGet('src')), title=token.attrGet('title'),
                visible=_visible_inline(token.children or ()))
        return accepted

    parser.inline.ruler.at('image', marked_image)
    parser.inline.ruler.at('link', marked(link))
    parser.inline.ruler.at('autolink', marked(autolink, True))
    return parser


def _source_position(source_lines, token, position):
    before = token.content[:position]
    line = before.count('\n')
    column = len(before.rsplit('\n', 1)[-1])
    source_line = token.map[0] + line
    logical = token.content.split('\n')[line]
    offset = source_lines[source_line].find(logical)
    if offset < 0:
        raise ValueError('Retained navigation cannot be mapped to original Markdown')
    return sum(map(len, source_lines[:source_line])) + offset + column


def _origin_wrapper(children):
    # Exact connected_page_authoring._initial_markdown provenance structure.
    if (len(children) != 4 or children[0].type != 'link_open'
            or 'retained_navigation' not in children[0].meta
            or children[1].type != 'text' or not children[1].content.startswith('From ')
            or children[2].type != 'link_close' or children[3].type != 'text'):
        return False
    tail = children[3].content
    if tail == ' · captured working copy':
        return True
    if not tail.startswith(' · saved revision '):
        return False
    revision, separator, extent = tail.removeprefix(' · saved revision ').partition(', lines ')
    start, dash, end = extent.partition('–')
    return bool(separator and dash and revision.isdecimal() and start.isdecimal() and end.isdecimal())


def _project_retained_source(markdown):
    # Preserve surrounding source exactly. Only owned controls/provenance become
    # visible labels; read hashes/ranges continue to use the original bytes.
    environment = {}
    tokens = _retained_parser().parse(markdown, environment)
    source_lines = markdown.splitlines(keepends=True)
    nodes = []
    definitions = [*environment.get('references', {}).values(),
                   *environment.get('duplicate_refs', [])]
    for definition in definitions:
        if _buddy_navigation(definition['href']) or _managed(definition['href']):
            start, end = definition['map']
            nodes.append(dict(start=sum(map(len, source_lines[:start])),
                end=sum(map(len, source_lines[:end])), kind='blank'))
    for token in tokens:
        if token.type != 'inline' or not token.map:
            continue
        children = token.children or ()
        position = lambda value: _source_position(source_lines, token, value)
        if _pdf_identity_field(children):
            nodes.append(dict(start=position(0), end=position(len(token.content)), kind='blank'))
            continue
        wrapper = _origin_wrapper(children)
        def collect(items, base=0):
            for child in items:
                navigation = child.meta.get('retained_navigation')
                picture = child.meta.get('retained_image')
                data = navigation or picture
                if data is None:
                    continue
                if navigation is not None or picture['managed']:
                    node = dict(data, start=position(base + data['start']),
                        end=position(len(token.content) if wrapper else base + data['end']),
                        kind='link' if navigation is not None else 'image')
                    if data['label_start'] is not None:
                        node.update(label_start=position(base + data['label_start']),
                                    label_end=position(base + data['label_end']))
                    if navigation is not None:
                        node['fallback'] = ('Saved page navigation' if child.attrGet('href').split('?', 1)[0].endswith('/build')
                                            else 'Source citation')
                    nodes.append(node)
                if picture is not None:
                    collect(child.children or (), base + picture['label_start'])
        collect(children)

    def render(start, end):
        result, cursor = [], start
        for node in sorted(nodes, key=lambda item: (item['start'], -item['end'])):
            left, right = node['start'], node['end']
            if left < start or right > end:
                continue
            if left < cursor:
                if right <= cursor:
                    continue  # Already rendered inside its enclosing control.
                raise ValueError('Overlapping retained navigation projections')
            result.append(markdown[cursor:left])
            if node['kind'] == 'blank':
                value = ''
            elif node['kind'] == 'link' and (node['label_start'] is None or _buddy_navigation(node['visible'])):
                value = node['fallback']
            else:
                value = render(node['label_start'], node['label_end'])
                if node['kind'] == 'image':
                    value = '[Image: ' + value + ']' if value and not _managed(node['visible']) else '[Image]'
                title = node['title']
                if title and not _buddy_navigation(title) and not _managed(title):
                    value += ' (' + title.replace('\n', ' ') + ')'
            original_ends = re.findall(r'\r\n|\r|\n', markdown[left:right])
            projected_ends = re.findall(r'\r\n|\r|\n', value)
            value += ''.join(original_ends[len(projected_ends):])
            result.append(value)
            cursor = right
        return ''.join(result) + markdown[cursor:end]
    return render(0, len(markdown))


# Pure immutable text projection, never access/receipt/permission caching. Match
# the existing dialogue cache's bounded value size; larger inputs still project.
from functools import lru_cache

_cached_retained_source = lru_cache(maxsize=128)(_project_retained_source)


def project_retained_source_markdown(markdown):
    """Current retained-context presentation, separate from historical codecs."""
    return (_cached_retained_source(markdown) if len(markdown.encode('utf-8')) <= 65_536
            else _project_retained_source(markdown))
