"""Planner tools that take a corpus-relative ``path`` (shared trace / gate semantics)."""

from __future__ import annotations

import json
from typing import Any

CORPUS_PATH_TOOL_NAMES = frozenset({"read_corpus_file", "load_context_markdown"})
SESSION_MEMORY_QUERY_TOOL_NAMES = frozenset({"query_session_memory"})


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


def unit_ids_from_query_session_memory_trace(tool_trace: list[dict[str, Any]]) -> list[str]:
    """``unit_id`` fields from successful ``query_session_memory`` tool outputs, in trace order."""
    out: list[str] = []
    for row in tool_trace:
        if str(row.get("tool", "")) not in SESSION_MEMORY_QUERY_TOOL_NAMES:
            continue
        raw = row.get("output_excerpt") or row.get("output") or ""
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if payload.get("ok") is not True:
            continue
        for hit in payload.get("hits") or []:
            uid = str(hit.get("unit_id", "")).strip()
            if uid:
                out.append(uid)
    return out
