"""
DungeonMindBuddy Hermes plugin v0.

This intentionally starts with a dumb lexical markdown search.
Replace internals later with DungeonBuddy's real ingestion/retrieval/canon APIs.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "out",
    ".hermes-runtime",
}


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _repo_root() -> Path:
    configured = os.environ.get("DUNGEONBUDDY_REPO")
    if configured:
        return Path(configured).expanduser().resolve()

    # plugin path: integrations/hermes/plugins/dungeonbuddy/__init__.py
    return Path(__file__).resolve().parents[4]


def _corpus_root() -> Path:
    configured = os.environ.get("DUNGEONBUDDY_CORPUS_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()

    repo = _repo_root()

    # Prefer a repo-local corpus if present.
    for candidate in [
        repo / "corpus",
        repo / "docs",
        repo,
    ]:
        if candidate.exists():
            return candidate.resolve()

    return repo


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def _iter_markdown(root: Path):
    for path in root.rglob("*.md"):
        if not _is_ignored(path):
            yield path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _terms(query: str) -> list[str]:
    return [
        term.lower()
        for term in re.findall(r"[A-Za-z0-9_'-]{3,}", query)
        if term.strip()
    ]


def _title_for(text: str, path: Path) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def _excerpt(text: str, terms: list[str], window: int = 420) -> str:
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return text[:window].strip()

    center = min(positions)
    start = max(0, center - window // 2)
    end = min(len(text), center + window // 2)
    return text[start:end].strip()


DUNGEON_SEARCH_SCHEMA = {
    "name": "dungeon_search",
    "description": (
        "Search the DungeonMindBuddy markdown corpus. "
        "Use this for campaign, worldbuilding, session recap, planning, NPC, location, "
        "continuity, and canon questions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query.",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of matches to return.",
                "default": 8,
            },
        },
        "required": ["query"],
    },
}


def handle_dungeon_search(params: dict[str, Any], **kwargs: Any) -> str:
    del kwargs

    query = str(params.get("query", "")).strip()
    top_k = int(params.get("top_k", 8))

    if not query:
        return _json({"success": False, "error": "query is required"})

    root = _corpus_root()
    if not root.exists():
        return _json(
            {
                "success": False,
                "error": f"corpus root does not exist: {root}",
                "hint": "Set DUNGEONBUDDY_CORPUS_ROOT or DUNGEONBUDDY_REPO.",
            }
        )

    terms = _terms(query)
    matches: list[dict[str, Any]] = []

    for path in _iter_markdown(root):
        try:
            text = _read_text(path)
        except OSError as exc:
            matches.append(
                {
                    "path": str(path.relative_to(root)),
                    "error": str(exc),
                    "score": 0,
                }
            )
            continue

        lowered = text.lower()
        score = sum(lowered.count(term) for term in terms)
        if score <= 0:
            continue

        matches.append(
            {
                "path": str(path.relative_to(root)),
                "absolute_path": str(path),
                "title": _title_for(text, path),
                "score": score,
                "excerpt": _excerpt(text, terms),
            }
        )

    matches.sort(key=lambda item: item.get("score", 0), reverse=True)

    return _json(
        {
            "success": True,
            "tool": "dungeon_search",
            "query": query,
            "corpus_root": str(root),
            "match_count": len(matches),
            "matches": matches[:top_k],
            "warning": (
                "This is v0 lexical markdown search. Treat results as retrieval candidates, "
                "not canon."
            ),
        }
    )


DUNGEON_GET_DOCUMENT_SCHEMA = {
    "name": "dungeon_get_document",
    "description": "Read a markdown document from the DungeonMindBuddy corpus by relative path.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path returned by dungeon_search.",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return.",
                "default": 12000,
            },
        },
        "required": ["path"],
    },
}


def handle_dungeon_get_document(params: dict[str, Any], **kwargs: Any) -> str:
    del kwargs

    root = _corpus_root()
    rel_path = str(params.get("path", "")).strip()
    max_chars = int(params.get("max_chars", 12000))

    if not rel_path:
        return _json({"success": False, "error": "path is required"})

    target = (root / rel_path).resolve()

    try:
        target.relative_to(root)
    except ValueError:
        return _json(
            {
                "success": False,
                "error": "path escapes corpus root",
                "path": rel_path,
            }
        )

    if not target.exists():
        return _json(
            {
                "success": False,
                "error": "document not found",
                "path": rel_path,
            }
        )

    text = _read_text(target)

    return _json(
        {
            "success": True,
            "tool": "dungeon_get_document",
            "path": rel_path,
            "title": _title_for(text, target),
            "chars_total": len(text),
            "truncated": len(text) > max_chars,
            "content": text[:max_chars],
        }
    )


DUNGEON_CHECK_CONTINUITY_SCHEMA = {
    "name": "dungeon_check_continuity",
    "description": (
        "Check a proposed campaign claim against the markdown corpus. "
        "This v0 implementation searches for related evidence and does not decide canon."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "claim": {
                "type": "string",
                "description": "The claim to check, e.g. 'Stacey is a bugbear'.",
            },
            "top_k": {
                "type": "integer",
                "default": 8,
            },
        },
        "required": ["claim"],
    },
}


def handle_dungeon_check_continuity(params: dict[str, Any], **kwargs: Any) -> str:
    claim = str(params.get("claim", "")).strip()
    top_k = int(params.get("top_k", 8))

    if not claim:
        return _json({"success": False, "error": "claim is required"})

    raw = handle_dungeon_search({"query": claim, "top_k": top_k}, **kwargs)
    data = json.loads(raw)

    return _json(
        {
            "success": data.get("success", False),
            "tool": "dungeon_check_continuity",
            "claim": claim,
            "status": "evidence_candidates_only",
            "matches": data.get("matches", []),
            "continuity_warning": (
                "v0 does not adjudicate canon. It only returns evidence candidates. "
                "A later version should call the canon reducer and conflict detector."
            ),
        }
    )


def register(ctx: Any) -> None:
    ctx.register_tool(
        name="dungeon_search",
        toolset="dungeonbuddy",
        schema=DUNGEON_SEARCH_SCHEMA,
        handler=handle_dungeon_search,
        description="Search DungeonMindBuddy markdown corpus.",
    )

    ctx.register_tool(
        name="dungeon_get_document",
        toolset="dungeonbuddy",
        schema=DUNGEON_GET_DOCUMENT_SCHEMA,
        handler=handle_dungeon_get_document,
        description="Read one DungeonMindBuddy markdown corpus document.",
    )

    ctx.register_tool(
        name="dungeon_check_continuity",
        toolset="dungeonbuddy",
        schema=DUNGEON_CHECK_CONTINUITY_SCHEMA,
        handler=handle_dungeon_check_continuity,
        description="Find evidence related to a proposed continuity claim.",
    )

    skill_path = Path(__file__).parent / "skills" / "dungeonbuddy-corpus-qa" / "SKILL.md"
    if skill_path.exists():
        ctx.register_skill("dungeonbuddy:corpus-qa", skill_path)
