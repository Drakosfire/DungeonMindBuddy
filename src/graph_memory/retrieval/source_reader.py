"""Source-read result types and inert import-locator parsing.

Product source bodies are read through their exact database owner after
DungeonMind authorization. This module opens no files and grants no authority.
"""
from __future__ import annotations

from dataclasses import dataclass

REPO_URI_PREFIX = "repo://"


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


__all__ = ["REPO_URI_PREFIX", "SourceReadError", "SourceReadOutcome", "parse_repo_uri"]
