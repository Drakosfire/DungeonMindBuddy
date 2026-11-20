"""Exact passage proof from an immutable UTF-8 source; no Graph authority."""
from __future__ import annotations

import hashlib


def _source_lines(markdown):
    return markdown.splitlines(keepends=True)


def exact_saved_section(markdown: str, content_sha256: str, line_start: int, line_end: int) -> str:
    if not isinstance(markdown, str) or hashlib.sha256(markdown.encode('utf-8')).hexdigest() != content_sha256:
        raise ValueError('Immutable source body differs from the frozen content digest')
    if (type(line_start) is not int or type(line_end) is not int
            or line_start < 1 or line_end < line_start):
        raise ValueError('Saved section range is invalid')
    lines = _source_lines(markdown)
    if line_end > len(lines):
        raise ValueError('Saved section range exceeds immutable source')
    text = ''.join(lines[line_start - 1:line_end])
    if not text.strip():
        raise ValueError('Saved section is empty')
    return text


def saved_section_catalog(markdown, basis):
    """Reuse exact authored blocks; expose line metadata, never their bodies."""
    from .authored_excerpt_blocks import partition
    from .types import canonical_sha256
    from .jev_retrieval_contract import RetrievalCandidate
    if hashlib.sha256(markdown.encode('utf-8')).hexdigest()!=basis.content_sha256:
        raise ValueError('Saved catalog differs from its frozen source basis')
    offsets={0:1}
    cursor=0
    for number,line in enumerate(_source_lines(markdown),1):
        if line:
            cursor+=len(line.encode('utf-8'))
            offsets[cursor]=number+1
    owner='saved-build:'+canonical_sha256(basis)
    return {block.block_handle:(RetrievalCandidate(handle=block.block_handle,
        label=f'Saved authored page, lines {offsets[block.byte_start]}–{offsets[block.byte_end]-1}',
        kind='Saved authored page block; select to open exact saved text, not played World facts'),
        (offsets[block.byte_start],offsets[block.byte_end]-1))
        for block in partition(markdown,owner) if block.text.strip()}
