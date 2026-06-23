from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field

MAX_SOURCE_BYTES = 200_000
ALLOWED_SOURCE_ROOTS = ("corpus", "Docs", "evals")
ALLOWED_SOURCE_EXTENSIONS = frozenset({".md", ".markdown", ".txt", ".json", ".jsonl"})


class CitationSourceRequest(BaseModel):
    path: str = Field(min_length=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    text_excerpt: str | None = None


class CitationSourceHighlight(BaseModel):
    line_start: int | None = None
    line_end: int | None = None
    text_excerpt: str | None = None
    match_source: Literal["line_range", "excerpt_search", "none"] = "none"


class CitationSourceResponse(BaseModel):
    schema_version: Literal["dmb_citation_source_v1"] = "dmb_citation_source_v1"
    path: str
    content_type: Literal["text/markdown", "text/plain"]
    content: str
    truncated: bool = False
    highlight: CitationSourceHighlight
    diagnostics: list[str] = Field(default_factory=list)


class CitationSourceError(ValueError):
    status_code: int = 422

    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def _validate_relative_source_path(path: str) -> PurePosixPath:
    raw = path.strip().replace("\\", "/")
    if raw.startswith("/") or ":" in raw.split("/", 1)[0]:
        raise CitationSourceError("citation source path must be repo-relative")
    rel = PurePosixPath(raw)
    if any(part in ("", ".", "..") for part in rel.parts):
        raise CitationSourceError("citation source path cannot contain traversal")
    if not rel.parts or rel.parts[0] not in ALLOWED_SOURCE_ROOTS:
        raise CitationSourceError("citation source path is outside allowed source roots")
    if rel.suffix.lower() not in ALLOWED_SOURCE_EXTENSIONS:
        raise CitationSourceError("citation source file type is not supported")
    return rel


def _resolve_under_repo(root: Path, rel: PurePosixPath) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / Path(*rel.parts)).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise CitationSourceError("citation source path escapes repository")
    if not candidate.is_file():
        raise CitationSourceError("citation source not found", status_code=404)
    return candidate


def _content_type(path: PurePosixPath) -> Literal["text/markdown", "text/plain"]:
    return "text/markdown" if path.suffix.lower() in {".md", ".markdown"} else "text/plain"


def _line_excerpt(lines: list[str], line_start: int | None, line_end: int | None) -> tuple[str | None, int | None, int | None]:
    if line_start is None and line_end is None:
        return None, None, None
    start = line_start or line_end or 1
    end = line_end or line_start or start
    start = max(1, min(start, len(lines)))
    end = max(start, min(end, len(lines)))
    return "\n".join(lines[start - 1 : end]), start, end


def _find_excerpt(lines: list[str], excerpt: str | None) -> tuple[str | None, int | None, int | None]:
    needle = (excerpt or "").strip()
    if not needle:
        return None, None, None
    haystack = "\n".join(lines)
    index = haystack.find(needle)
    if index < 0:
        return None, None, None
    before = haystack[:index]
    start = before.count("\n") + 1
    end = start + needle.count("\n")
    return needle, start, end


def read_citation_source(root: Path, request: CitationSourceRequest) -> CitationSourceResponse:
    rel = _validate_relative_source_path(request.path)
    source_path = _resolve_under_repo(root, rel)
    data = source_path.read_bytes()
    truncated = len(data) > MAX_SOURCE_BYTES
    if truncated:
        data = data[:MAX_SOURCE_BYTES]
    content = data.decode("utf-8", errors="replace")
    lines = content.splitlines()

    excerpt, start, end = _line_excerpt(lines, request.line_start, request.line_end)
    match_source: Literal["line_range", "excerpt_search", "none"] = "line_range" if excerpt else "none"
    if excerpt is None:
        excerpt, start, end = _find_excerpt(lines, request.text_excerpt)
        match_source = "excerpt_search" if excerpt else "none"

    diagnostics = ["read-only source lookup", "no events or jobs written"]
    if truncated:
        diagnostics.append(f"source truncated to {MAX_SOURCE_BYTES} bytes")

    return CitationSourceResponse(
        path=rel.as_posix(),
        content_type=_content_type(rel),
        content=content,
        truncated=truncated,
        highlight=CitationSourceHighlight(
            line_start=start,
            line_end=end,
            text_excerpt=excerpt,
            match_source=match_source,
        ),
        diagnostics=diagnostics,
    )
