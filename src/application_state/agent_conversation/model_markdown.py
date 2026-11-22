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
