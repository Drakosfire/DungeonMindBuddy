"""Exact passage proof from an immutable UTF-8 source; no Graph authority."""
from __future__ import annotations

import hashlib


def exact_saved_section(markdown: str, content_sha256: str, line_start: int, line_end: int) -> str:
    if not isinstance(markdown, str) or hashlib.sha256(markdown.encode('utf-8')).hexdigest() != content_sha256:
        raise ValueError('Immutable source body differs from the frozen content digest')
    if (type(line_start) is not int or type(line_end) is not int
            or line_start < 1 or line_end < line_start):
        raise ValueError('Saved section range is invalid')
    lines = markdown.splitlines(keepends=True)
    if line_end > len(lines):
        raise ValueError('Saved section range exceeds immutable source')
    text = ''.join(lines[line_start - 1:line_end])
    if not text.strip():
        raise ValueError('Saved section is empty')
    return text
