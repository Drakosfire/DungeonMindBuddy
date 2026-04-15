"""Planner tools that take a corpus-relative ``path`` (shared trace / gate semantics)."""

from __future__ import annotations

from typing import Any

CORPUS_PATH_TOOL_NAMES = frozenset({"read_corpus_file", "load_context_markdown"})


def read_paths_from_tool_trace(tool_trace: list[dict[str, Any]]) -> list[str]:
    """``path`` arguments from corpus path tools, in trace order."""
    paths: list[str] = []
    for row in tool_trace:
        if str(row.get("tool", "")) not in CORPUS_PATH_TOOL_NAMES:
            continue
        args = row.get("arguments") or {}
        p = str(args.get("path", "")).strip()
        if p:
            paths.append(p)
    return paths
