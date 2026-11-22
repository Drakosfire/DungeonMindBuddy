"""Read the canonical callout header and quoted body used at Build boundaries."""

import re

_HEADER = re.compile(
    r"^ {0,3}>[ \t]*\[!(READ-ALOUD|GM-NOTE|WARNING|RULES)\](?:[ \t]+(.*))?$"
)
_QUOTE_LINE = re.compile(r"^ {0,3}>[ \t]?(.*)$")


def split_boundary_callout(lines: list[str]) -> tuple[str, str | None, str] | None:
    if not lines or not (header := _HEADER.fullmatch(lines[0])):
        return None
    body = [_QUOTE_LINE.fullmatch(line) for line in lines[1:]]
    if any(line is None or line[1].lstrip().startswith("[!") for line in body):
        return None
    return header[1].lower(), (header[2] or "").strip() or None, "\n".join(
        line[1] for line in body if line is not None
    )
