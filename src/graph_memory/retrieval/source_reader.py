"""Safe, bounded, graph-authorized source reading for PR010A retrieval.

Only two locator families are supported, and both resolve strictly through
graph-admitted context rather than an arbitrary caller-supplied path:

* ``repo://<repo-relative-path>`` + ``heading:<exact heading text>`` —
  resolved under the repository root only, with SHA-256 verification and an
  exact Markdown-heading match.
* ``graph-data://<relative-path>`` + ``jsonptr:<RFC 6901 pointer>`` —
  resolved by applying the JSON pointer to a revision-bound active
  contribution payload that the *caller* has already loaded through the
  integrity-checked Kernel contribution path (never through the
  source-artifact URI as a filesystem path). This module never touches
  world-storage internals directly, so it stays outside the Graph Kernel
  boundary and is safe to import from anywhere.

There is no general file reader here. Unsupported schemes/locators are the
caller's responsibility to label ``unsupported`` before ever reaching this
module.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_URI_PREFIX = "repo://"
GRAPH_DATA_URI_PREFIX = "graph-data://"
HEADING_LOCATOR_PREFIX = "heading:"
JSON_POINTER_LOCATOR_PREFIX = "jsonptr:"

_FRONTMATTER_DELIMITER = "---"
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_MISSING = object()


class SourceReadError(Exception):
    """Stable source-read failure with an API-safe code; never leaks a path."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SourceReadOutcome:
    content: str
    media_type: str
    content_sha256: str
    line_start: int | None
    line_end: int | None
    truncated: bool


def parse_repo_uri(uri: str) -> str | None:
    if uri.startswith(REPO_URI_PREFIX):
        return uri[len(REPO_URI_PREFIX) :]
    return None


def parse_graph_data_uri(uri: str) -> str | None:
    if uri.startswith(GRAPH_DATA_URI_PREFIX):
        return uri[len(GRAPH_DATA_URI_PREFIX) :]
    return None


def parse_heading_locator(locator: str) -> str | None:
    if locator.startswith(HEADING_LOCATOR_PREFIX):
        return locator[len(HEADING_LOCATOR_PREFIX) :]
    return None


def parse_json_pointer_locator(locator: str) -> str | None:
    if locator.startswith(JSON_POINTER_LOCATOR_PREFIX):
        return locator[len(JSON_POINTER_LOCATOR_PREFIX) :]
    return None


def _strip_frontmatter(text: str) -> tuple[dict[str, str] | None, str, int]:
    """Split a leading YAML frontmatter block from the Markdown body.

    Returns ``(frontmatter, body, body_line_offset)`` where ``body_line_offset``
    is the 0-based line index in the original file where body line 0 begins.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        return None, text, 0
    end_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == _FRONTMATTER_DELIMITER:
            end_index = index
            break
    if end_index is None:
        return None, text, 0
    frontmatter: dict[str, str] = {}
    for raw_line in lines[1:end_index]:
        if ":" not in raw_line:
            continue
        key, _, value = raw_line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            frontmatter[key] = value
    body_line_offset = end_index + 1
    body_lines = lines[end_index + 1 :]
    return frontmatter, "\n".join(body_lines), body_line_offset


def _find_headings(body_lines: list[str]) -> list[tuple[int, int, str]]:
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(body_lines):
        match = _HEADING_PATTERN.match(line)
        if match:
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            headings.append((index, level, heading_text))
    return headings


def _extract_heading_section(
    body_lines: list[str],
    heading_index: int,
    heading_level: int,
) -> tuple[int, int]:
    end = len(body_lines)
    for index in range(heading_index + 1, len(body_lines)):
        match = _HEADING_PATTERN.match(body_lines[index])
        if match and len(match.group(1)) <= heading_level:
            end = index
            break
    return heading_index, end


def _resolve_repo_relative_path(repo_root: Path, relative_path: str) -> Path:
    if not relative_path or relative_path.startswith("/") or ".." in Path(relative_path).parts:
        raise SourceReadError(
            "repo:// locator path must be a safe repository-relative path.",
            code="unsupported_locator",
        )
    resolved_root = repo_root.resolve()
    candidate = resolved_root / relative_path
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SourceReadError(
            "repo:// source path could not be resolved.",
            code="source_unavailable",
        ) from exc
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise SourceReadError(
            "repo:// source path escapes the repository root.",
            code="path_escape",
        ) from exc
    return resolved


def read_repo_heading_anchor(
    *,
    repo_root: Path,
    relative_path: str,
    heading_text: str,
    expected_content_sha256: str,
    max_chars: int,
) -> SourceReadOutcome:
    if not isinstance(expected_content_sha256, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", expected_content_sha256
    ):
        raise SourceReadError(
            "repo:// heading read requires an admitted content digest.",
            code="source_integrity_error",
        )
    resolved_path = _resolve_repo_relative_path(repo_root, relative_path)
    if not resolved_path.is_file():
        raise SourceReadError(
            "repo:// source file is unavailable.",
            code="source_unavailable",
        )
    raw_bytes = resolved_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256.lower() != expected_content_sha256.lower():
        raise SourceReadError(
            "repo:// source content does not match the admitted digest.",
            code="source_integrity_error",
        )
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceReadError(
            "repo:// source file is not valid UTF-8 text.",
            code="source_unavailable",
        ) from exc

    _frontmatter, body, body_line_offset = _strip_frontmatter(text)
    body_lines = body.splitlines()
    headings = _find_headings(body_lines)
    matches = [item for item in headings if item[2] == heading_text]

    if len(matches) > 1:
        raise SourceReadError(
            "Multiple headings match the requested heading text.",
            code="ambiguous_heading",
        )
    if len(matches) != 1:
        raise SourceReadError(
            "Requested heading was not found in the source document.",
            code="heading_not_found",
        )

    heading_index, heading_level, _heading_text = matches[0]
    start, end = _extract_heading_section(body_lines, heading_index, heading_level)
    section_lines = body_lines[start:end]
    section_text = "\n".join(section_lines).strip("\n")
    truncated = len(section_text) > max_chars
    bounded_text = section_text[:max_chars]
    line_start = start + body_line_offset + 1
    if not bounded_text:
        line_end = None
    elif not truncated:
        # Exclusive end index from _extract_heading_section → inclusive last line.
        line_end = end + body_line_offset
    else:
        # Describe only the returned bytes (including a partial final line).
        returned_line_count = bounded_text.count("\n") + 1
        line_end = line_start + returned_line_count - 1
    return SourceReadOutcome(
        content=bounded_text,
        media_type="text/markdown",
        content_sha256=actual_sha256,
        line_start=line_start if bounded_text else None,
        line_end=line_end,
        truncated=truncated,
    )


def _decode_json_pointer_token(raw_token: str) -> str:
    decoded: list[str] = []
    index = 0
    while index < len(raw_token):
        char = raw_token[index]
        if char != "~":
            decoded.append(char)
            index += 1
            continue
        if index + 1 >= len(raw_token):
            raise SourceReadError(
                "JSON pointer escape sequence is incomplete.",
                code="invalid_json_pointer",
            )
        escaped = raw_token[index + 1]
        if escaped == "0":
            decoded.append("~")
        elif escaped == "1":
            decoded.append("/")
        else:
            raise SourceReadError(
                "JSON pointer escape sequence is invalid.",
                code="invalid_json_pointer",
            )
        index += 2
    return "".join(decoded)


def _resolve_json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise SourceReadError(
            "JSON pointer must be empty or start with '/'.",
            code="invalid_json_pointer",
        )
    tokens = pointer.split("/")[1:]
    current = document
    for raw_token in tokens:
        token = _decode_json_pointer_token(raw_token)
        if isinstance(current, list):
            if not re.fullmatch(r"\d+", token):
                raise SourceReadError(
                    "JSON pointer array index is invalid.",
                    code="invalid_json_pointer",
                )
            index = int(token)
            if index >= len(current):
                return _MISSING
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                return _MISSING
            current = current[token]
        else:
            return _MISSING
    return current


def read_graph_data_json_pointer_anchor(
    *,
    contribution_payload: dict[str, Any],
    json_pointer: str,
    max_chars: int,
) -> SourceReadOutcome:
    value = _resolve_json_pointer(contribution_payload, json_pointer)
    if value is _MISSING:
        raise SourceReadError(
            "graph-data:// JSON pointer did not resolve within the contribution payload.",
            code="invalid_json_pointer",
        )

    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
    content_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    truncated = len(text) > max_chars
    return SourceReadOutcome(
        content=text[:max_chars],
        media_type="application/json",
        content_sha256=content_sha256,
        line_start=None,
        line_end=None,
        truncated=truncated,
    )


def read_repo_line_span_text(
    *,
    repo_root: Path,
    relative_path: str,
    start_line: int,
    end_line: int,
    max_chars: int,
    expected_content_sha256: str,
) -> SourceReadOutcome:
    """Authorization-neutral digest-checked line-span slice of a repo file.

    Callers must already authorize the path and span identity. This primitive
    only verifies current bytes match ``expected_content_sha256`` before
    slicing 1-based inclusive ``start_line``..``end_line``.
    """
    if not isinstance(expected_content_sha256, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", expected_content_sha256
    ):
        raise SourceReadError(
            "Line-span read requires an admitted content digest.",
            code="source_integrity_error",
        )
    if start_line < 1 or end_line < start_line:
        raise SourceReadError(
            "Line-span bounds are invalid.",
            code="unsupported_locator",
        )
    resolved_path = _resolve_repo_relative_path(repo_root, relative_path)
    if not resolved_path.is_file():
        raise SourceReadError(
            "repo:// source file is unavailable.",
            code="source_unavailable",
        )
    raw_bytes = resolved_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256.lower() != expected_content_sha256.lower():
        raise SourceReadError(
            "repo:// source content does not match the admitted digest.",
            code="source_integrity_error",
        )
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceReadError(
            "repo:// source file is not valid UTF-8 text.",
            code="source_unavailable",
        ) from exc

    lines = text.splitlines()
    if end_line > len(lines):
        raise SourceReadError(
            "Line-span is outside the admitted source bounds.",
            code="source_unavailable",
        )
    section_lines = lines[start_line - 1 : end_line]
    section_text = "\n".join(section_lines)
    truncated = len(section_text) > max_chars
    bounded_text = section_text[:max_chars]
    if not bounded_text:
        line_end: int | None = None
        line_start: int | None = None
    elif not truncated:
        line_start = start_line
        line_end = end_line
    else:
        # Describe only the returned bytes (including a partial final line).
        line_start = start_line
        returned_line_count = bounded_text.count("\n") + 1
        line_end = line_start + returned_line_count - 1
    return SourceReadOutcome(
        content=bounded_text,
        media_type="text/markdown",
        content_sha256=actual_sha256,
        line_start=line_start,
        line_end=line_end,
        truncated=truncated,
    )


__all__ = [
    "GRAPH_DATA_URI_PREFIX",
    "HEADING_LOCATOR_PREFIX",
    "JSON_POINTER_LOCATOR_PREFIX",
    "REPO_URI_PREFIX",
    "SourceReadError",
    "SourceReadOutcome",
    "parse_graph_data_uri",
    "parse_heading_locator",
    "parse_json_pointer_locator",
    "parse_repo_uri",
    "read_graph_data_json_pointer_anchor",
    "read_repo_heading_anchor",
    "read_repo_line_span_text",
]
