"""Exact source spans shared by content presentation and authored evidence.

Offsets are UTF-8 byte positions, not editor identities. No normalization occurs.
"""

import re
from markdown_it import MarkdownIt


def source_block_spans(text: str) -> tuple[tuple[int, int], ...]:
    if not isinstance(text, str):
        raise ValueError("Authored body must be exact text")
    if not text:
        return ()
    # Match parser line boundaries without normalizing the frozen raw bytes.
    raw_lines = re.findall(r".*?(?:\r\n|\n|\r|$)", text, flags=re.S)
    raw_lines = [line for line in raw_lines if line]
    offsets = [0]
    for line in raw_lines:
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    tokens = MarkdownIt("commonmark", {"html": True}).enable("table").parse(text)
    spans = [
        (token.map[0], token.map[1])
        for token in tokens
        if token.level == 0 and token.map
    ]
    fences = [
        token.map
        for token in tokens
        if token.type in {"fence", "code_block"} and token.map
    ]
    stack = []
    for index, line in enumerate(raw_lines):
        if any(start <= index < end for start, end in fences):
            continue
        marker = re.match(r"^ {0,3}:::[ \t]*(.*?)[\r\n]*$", line)
        if not marker:
            continue
        if marker.group(1).strip():
            stack.append(index)
        elif stack:
            start = stack.pop()
            if not stack:
                spans.append((start, index + 1))
    if stack:
        spans.append((stack[0], len(raw_lines)))
    starts = {0, len(raw_lines)} | {start for start, _ in spans}
    starts = sorted(
        start
        for start in starts
        if not any(left < start < right for left, right in spans)
    )
    encoded = text.encode("utf-8")
    if len(starts) > 2 and not encoded[: offsets[starts[1]]].strip():
        starts.pop(1)
    result = tuple(
        (offsets[first], offsets[last])
        for first, last in zip(starts, starts[1:])
        if offsets[first] != offsets[last]
    )
    if b"".join(encoded[left:right] for left, right in result) != encoded:
        raise ValueError("Authored block partition changed frozen text")
    return result
