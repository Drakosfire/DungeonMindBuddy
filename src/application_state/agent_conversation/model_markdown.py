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


def _project_retained_source(markdown):
    # This is presentation of the original read. Citation ranges/hashes continue
    # to use its unmodified bytes. Fenced literals and ordinary prose are intact.
    projected = project_model_markdown(markdown)
    tokens = MarkdownIt('commonmark').parse(projected)
    replacements = {}
    for token in tokens:
        if token.type != 'inline' or not token.map:
            continue
        children = token.children or ()
        if _pdf_identity_field(children):
            replacements[tuple(token.map)] = ''
        elif any(child.type == 'link_open' and _buddy_navigation(child.attrGet('href'))
                 for child in children):
            visible = _visible_inline(children)
            # The editor navigation wrapper adds this host revision counter.
            prefix, separator, revision = visible.rpartition(' · saved revision ')
            if separator and revision.strip().isdecimal():
                visible = prefix
            replacements[tuple(token.map)] = visible
    if not replacements:
        return projected
    lines = re.split(r'(\r\n|\r|\n)', projected)
    for (start, end), replacement in sorted(replacements.items(), reverse=True):
        values = replacement.split('\n', maxsplit=end - start - 1)
        values.extend([''] * (end - start - len(values)))
        for index, value in enumerate(values, start):
            lines[2 * index] = value
    return ''.join(lines)


# Pure immutable text projection, never access/receipt/permission caching. Match
# the existing dialogue cache's bounded value size; larger inputs still project.
from functools import lru_cache

_cached_retained_source = lru_cache(maxsize=128)(_project_retained_source)


def project_retained_source_markdown(markdown):
    """Current retained-context presentation, separate from historical codecs."""
    return (_cached_retained_source(markdown) if len(markdown.encode('utf-8')) <= 65_536
            else _project_retained_source(markdown))
