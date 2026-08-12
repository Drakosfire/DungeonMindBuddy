"""
DungeonMindBuddy Hermes plugin.

v1: manifest-backed context lookup via ``build_context_packet`` (production retrieval).
v0 lexical ``dungeon_search`` remains available only when
``DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK=1``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
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
    "_dungeonbuddy",
}

_STRONG_ROLES = frozenset({"play_recap", "hub_evidence"})
_STRONG_AUTHORITIES = frozenset({"canon_play", "played_truth"})
_ENDING_BEAT_MARKERS = (
    "lightning bolt",
    "turn the tide",
    "overrun",
    "will this be enough",
    "cliffhanger",
    "and that is how",
    "that's when",
    "finally",
    "at the end",
)
_ELDYRWILD_PREFIX = "corpus/eldyrwild-markdown/"
_DEFAULT_MANIFEST_REL = "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _repo_root() -> Path:
    configured = os.environ.get("DUNGEONBUDDY_REPO")
    if configured:
        return Path(configured).expanduser().resolve()

    # plugin path: integrations/hermes/plugins/dungeonbuddy/__init__.py
    return Path(__file__).resolve().parents[4]


def _ensure_repo_on_path() -> Path:
    root = _repo_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def _env_flag_enabled(name: str) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _lexical_fallback_enabled() -> bool:
    return _env_flag_enabled("DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK")


def _eldyrwild_corpus_dir() -> Path:
    configured = os.environ.get("DUNGEONBUDDY_ELDYRWILD_CORPUS")
    if configured:
        return Path(configured).expanduser().resolve()
    return _repo_root() / "corpus" / "eldyrwild-markdown"


def _corpus_root() -> Path:
    """Legacy lexical-search root (broader than eldyrwild-only reader)."""
    configured = os.environ.get("DUNGEONBUDDY_CORPUS_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()

    repo = _repo_root()
    for candidate in [repo / "corpus", repo / "docs", repo]:
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


def _resolve_safe_md_under(root: Path, rel_path: str) -> Path | None:
    corpus_root = root.resolve()
    cleaned = rel_path.strip().replace("\\", "/").lstrip("/")
    if not cleaned or ".." in Path(cleaned).parts:
        return None
    candidate = (corpus_root / cleaned).resolve()
    try:
        candidate.relative_to(corpus_root)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix.lower() != ".md":
        return None
    return candidate


def _resolve_document_path(rel_path: str) -> Path | None:
    rel = rel_path.strip().replace("\\", "/")
    if not rel:
        return None

    lowered = rel.lower()
    if lowered.startswith(_ELDYRWILD_PREFIX):
        rel = rel[len(_ELDYRWILD_PREFIX) :].lstrip("/")
        return _resolve_safe_md_under(_eldyrwild_corpus_dir(), rel)

    hit = _resolve_safe_md_under(_eldyrwild_corpus_dir(), rel)
    if hit is not None:
        return hit

    return _resolve_safe_md_under(_repo_root(), rel)


def _manifest_imports() -> tuple[Any, ...]:
    _ensure_repo_on_path()
    from src.live_play.live_query_context import (
        _default_query_config,
        assign_evidence_ids,
        resolve_manifest_path,
    )
    from src.live_play.manifest_context_query import (
        build_context_packet,
        load_manifest,
        QueryRequest,
    )

    return (
        _default_query_config,
        assign_evidence_ids,
        resolve_manifest_path,
        build_context_packet,
        load_manifest,
        QueryRequest,
    )


def _resolve_manifest_path_for_plugin(explicit: str | None = None) -> Path:
    (
        _default_query_config,
        _assign_evidence_ids,
        resolve_manifest_path,
        _build_context_packet,
        load_manifest,
        _QueryRequest,
    ) = _manifest_imports()

    del _default_query_config, _assign_evidence_ids, _build_context_packet, load_manifest, _QueryRequest

    root = _repo_root()
    if explicit and explicit.strip():
        resolved = resolve_manifest_path(
            request_manifest_path=explicit.strip(),
            packet={},
            root=root,
        )
        if resolved is not None:
            return resolved
        raise FileNotFoundError(f"manifest not found: {explicit.strip()}")

    env_manifest = os.environ.get("DUNGEONBUDDY_MANIFEST_PATH", "").strip()
    if env_manifest:
        resolved = resolve_manifest_path(
            request_manifest_path=env_manifest,
            packet={},
            root=root,
        )
        if resolved is not None:
            return resolved

    default = (root / _DEFAULT_MANIFEST_REL).resolve()
    if default.is_file():
        return default

    resolved = resolve_manifest_path(request_manifest_path=None, packet={}, root=root)
    if resolved is not None:
        return resolved

    raise FileNotFoundError(
        "No manifest found. Set DUNGEONBUDDY_MANIFEST_PATH or ensure "
        f"{_DEFAULT_MANIFEST_REL} exists."
    )


def _session_number_from_path(path: str) -> int | None:
    match = re.search(r"session\s+(\d{1,2})", path, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _looks_like_session_ending_excerpt(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _ENDING_BEAT_MARKERS)


def _recap_line_position(row: dict[str, Any]) -> int:
    line_end = row.get("line_end")
    line_start = row.get("line_start")
    if isinstance(line_end, int):
        return line_end
    if isinstance(line_start, int):
        return line_start
    return 0


def _is_late_recap_beat(row: dict[str, Any], max_line: int) -> bool:
    excerpt = str(row.get("text_excerpt") or "")
    if _looks_like_session_ending_excerpt(excerpt):
        return True
    line = _recap_line_position(row)
    if line >= 25:
        return True
    if max_line >= 25 and line >= max_line * 0.65:
        return True
    return False


def _filter_admitted_to_target_session(
    admitted: list[dict[str, Any]],
    session_numbers: list[int] | None,
) -> list[dict[str, Any]]:
    if not session_numbers or len(session_numbers) != 1:
        return admitted
    target = session_numbers[0]
    out: list[dict[str, Any]] = []
    for row in admitted:
        path = str(row.get("path") or "")
        session = _session_number_from_path(path)
        if session is None or session == target:
            out.append(row)
    return out


def _is_canon_recap_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return (
        "/session recaps/session " in normalized
        and "/_normalized/" not in normalized
        and "/_breadcrumbed/" not in normalized
        and "/_session_memory/" not in normalized
    )


def _suggested_routes(
    admitted: list[dict[str, Any]],
    session_numbers: list[int] | None,
) -> list[str]:
    routes: list[str] = []
    seen: set[str] = set()
    for row in admitted:
        path = str(row.get("path") or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        routes.append(path)

    if session_numbers and len(session_numbers) == 1:
        target = session_numbers[0]
        pattern = re.compile(rf"session\s+{target}\b", flags=re.IGNORECASE)
        routes = [route for route in routes if pattern.search(route)]

    canon = [route for route in routes if _is_canon_recap_path(route)]
    other = [route for route in routes if not _is_canon_recap_path(route)]
    return (canon + other)[:6]


def _compact_sufficiency_summary(packet: dict[str, Any]) -> dict[str, Any]:
    signals = dict(packet.get("query_signals") or {})
    session_numbers = list(signals.get("session_numbers") or [])
    admitted = _filter_admitted_to_target_session(
        list(packet.get("admitted_evidence") or []),
        session_numbers if session_numbers else None,
    )
    rejected = list(packet.get("rejected_evidence") or [])
    claim = dict((packet.get("claims") or [{}])[0] if packet.get("claims") else {})
    asks_for_last_or_final = bool(signals.get("asks_for_last_or_final"))

    strong = 0
    okay = 0
    weak = 0
    for row in admitted:
        excerpt = str(row.get("text_excerpt") or "").strip()
        role = str(row.get("source_role") or "")
        authority = str(row.get("authority") or "")
        if len(excerpt) < 40:
            weak += 1
        elif role in _STRONG_ROLES or authority in _STRONG_AUTHORITIES or role == "session_memory":
            strong += 1
        else:
            okay += 1

    max_line = max(_recap_line_position(row) for row in admitted) if admitted else 0
    has_closing_beat = any(
        _is_late_recap_beat(row, max_line)
        for row in admitted
        if len(str(row.get("text_excerpt") or "").strip()) >= 40
    )

    loaded_routes = [
        str(row.get("path") or "")
        for row in admitted
        if len(str(row.get("text_excerpt") or "").strip()) >= 40
    ]
    missing_routes = [
        str(row.get("path") or "")
        for row in admitted
        if len(str(row.get("text_excerpt") or "").strip()) < 40
    ]

    if strong >= 1 and asks_for_last_or_final and not has_closing_beat:
        status = "weak_context"
        reason = (
            "Admitted excerpts are from earlier session beats; open the recap closing lines "
            "before answering."
        )
        answerable_now = False
    elif strong >= 1:
        status = "enough_context"
        reason = "At least one strong campaign-text excerpt was admitted."
        answerable_now = True
    elif okay >= 1 and weak == 0:
        status = "enough_context"
        reason = "Anchored excerpts were admitted without broad fallback routes."
        answerable_now = True
    elif weak >= 1 and strong == 0 and okay == 0:
        status = "weak_context"
        reason = "Only broad recap routes or low-signal items were admitted; open source reads next."
        answerable_now = False
    elif strong == 0 and okay == 0 and missing_routes:
        status = "missing_context"
        reason = "No usable excerpts were admitted; inspect the suggested source routes."
        answerable_now = False
    else:
        status = "weak_context"
        reason = "Some excerpts were admitted, but additional source reads are still recommended."
        answerable_now = False

    rejected_counts: dict[str, int] = {}
    for row in rejected:
        code = str(row.get("reason_code") or "unknown")
        rejected_counts[code] = rejected_counts.get(code, 0) + 1

    return {
        "status": status,
        "reason": reason,
        "answerable_now": answerable_now,
        "support_status": claim.get("support_status"),
        "claim_type": claim.get("claim_type"),
        "admitted_count": len(admitted),
        "rejected_count": len(rejected),
        "quality_counts": {"strong": strong, "okay": okay, "weak": weak},
        "asks_for_last_or_final": asks_for_last_or_final,
        "has_closing_beat": has_closing_beat,
        "loaded_routes": loaded_routes[:8],
        "missing_routes": missing_routes[:8],
        "suggested_routes": _suggested_routes(admitted, session_numbers or None),
        "rejected_reason_counts": rejected_counts,
        "policy_verdict": packet.get("source_excerpt"),
        "capability_status": packet.get("capability_status"),
    }


DUNGEON_CONTEXT_LOOKUP_SCHEMA = {
    "name": "dungeon_context_lookup",
    "description": (
        "Run manifest-backed context retrieval for a natural-language question. "
        "Returns admitted/rejected evidence, retrieval trace, and a compact sufficiency summary. "
        "Prefer this over dungeon_search for campaign, recap, continuity, and planning questions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Natural-language question (GM or operator ask).",
            },
            "question_id": {
                "type": "string",
                "description": "Optional stable id for telemetry; auto-generated when omitted.",
            },
            "category": {
                "type": "string",
                "description": "Optional intent/category label for benchmarks.",
            },
            "manifest_path": {
                "type": "string",
                "description": (
                    "Optional repo-relative manifest path. Defaults to the active planning manifest."
                ),
            },
        },
        "required": ["question"],
    },
}


def handle_dungeon_context_lookup(params: dict[str, Any], **kwargs: Any) -> str:
    del kwargs

    question = str(params.get("question", "")).strip()
    if not question:
        return _json({"success": False, "error": "question is required"})

    (
        default_query_config,
        assign_evidence_ids,
        _resolve_manifest_path,
        build_context_packet,
        load_manifest,
        QueryRequest,
    ) = _manifest_imports()

    try:
        manifest_path = _resolve_manifest_path_for_plugin(
            str(params.get("manifest_path") or "").strip() or None
        )
    except FileNotFoundError as exc:
        return _json({"success": False, "error": str(exc)})

    question_id = str(params.get("question_id") or "").strip()
    if not question_id:
        digest = hashlib.sha1(question.encode("utf-8")).hexdigest()[:10]
        question_id = f"hermes-{digest}"

    category_raw = params.get("category")
    category = str(category_raw).strip() if category_raw is not None and str(category_raw).strip() else None

    root = _repo_root()
    manifest = load_manifest(manifest_path)
    request = QueryRequest(question_id=question_id, question=question, category=category)
    packet = build_context_packet(
        request,
        manifest,
        root=root,
        config=default_query_config(),
    )
    packet = assign_evidence_ids(packet)
    summary = _compact_sufficiency_summary(packet)

    return _json(
        {
            "success": True,
            "tool": "dungeon_context_lookup",
            "question": question,
            "question_id": question_id,
            "manifest_path": str(manifest_path.relative_to(root)),
            "context_packet": packet,
            "sufficiency_summary": summary,
        }
    )


DUNGEON_MANIFEST_INDEX_SCHEMA = {
    "name": "dungeon_manifest_index",
    "description": (
        "List activated manifest entries (routes, roles, session scope) from the planning manifest. "
        "Read-only index for discovery before follow-up reads."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "manifest_path": {
                "type": "string",
                "description": "Optional repo-relative manifest path.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum entries to return.",
                "default": 200,
            },
            "source_role": {
                "type": "string",
                "description": "Optional filter on source_role.",
            },
            "session_number": {
                "type": "integer",
                "description": "Optional filter: entries whose session_scope includes this session.",
            },
        },
    },
}


def handle_dungeon_manifest_index(params: dict[str, Any], **kwargs: Any) -> str:
    del kwargs

    (
        _default_query_config,
        _assign_evidence_ids,
        _resolve_manifest_path,
        _build_context_packet,
        load_manifest,
        _QueryRequest,
    ) = _manifest_imports()

    del _default_query_config, _assign_evidence_ids, _resolve_manifest_path, _build_context_packet, _QueryRequest

    limit = max(1, int(params.get("limit", 200)))
    role_filter = str(params.get("source_role") or "").strip().lower()
    session_filter = params.get("session_number")
    session_number = int(session_filter) if session_filter is not None else None

    try:
        manifest_path = _resolve_manifest_path_for_plugin(
            str(params.get("manifest_path") or "").strip() or None
        )
    except FileNotFoundError as exc:
        return _json({"success": False, "error": str(exc)})

    root = _repo_root()
    manifest = load_manifest(manifest_path)
    entries_out: list[dict[str, Any]] = []
    for row in list(manifest.get("entries") or []):
        if not isinstance(row, dict):
            continue
        role = str(row.get("source_role") or "")
        session_scope = list(row.get("session_scope") or [])
        if role_filter and role.lower() != role_filter:
            continue
        if session_number is not None and session_number not in session_scope:
            continue
        entries_out.append(
            {
                "source_id": row.get("source_id"),
                "route": row.get("route"),
                "source_role": role,
                "authority": row.get("authority"),
                "session_scope": session_scope,
                "admissible": row.get("admissible"),
                "allowed_uses": list(row.get("allowed_uses") or []),
                "forbidden_uses": list(row.get("forbidden_uses") or []),
                "route_exists": row.get("route_exists"),
            }
        )
        if len(entries_out) >= limit:
            break

    return _json(
        {
            "success": True,
            "tool": "dungeon_manifest_index",
            "manifest_path": str(manifest_path.relative_to(root)),
            "schema": manifest.get("schema"),
            "campaign_id": manifest.get("campaign_id"),
            "planning_session": manifest.get("planning_session"),
            "source_sessions": list(manifest.get("source_sessions") or []),
            "entry_count": len(entries_out),
            "entries": entries_out,
        }
    )


DUNGEON_SEARCH_SCHEMA = {
    "name": "dungeon_search",
    "description": (
        "Legacy lexical markdown search. Disabled by default; set "
        "DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK=1 to enable. Prefer dungeon_context_lookup."
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

    if not _lexical_fallback_enabled():
        return _json(
            {
                "success": False,
                "tool": "dungeon_search",
                "error": "dungeon_search is disabled. Use dungeon_context_lookup instead.",
                "hint": "Set DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK=1 only for legacy lexical fallback.",
            }
        )

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
                "Lexical fallback only. Treat results as retrieval candidates, not canon. "
                "Prefer dungeon_context_lookup."
            ),
        }
    )


DUNGEON_GET_DOCUMENT_SCHEMA = {
    "name": "dungeon_get_document",
    "description": (
        "Read a markdown document by corpus-relative or manifest route path. "
        "Accepts eldyrwild corpus paths (e.g. Longmont Campaign/...) and "
        "repo-relative manifest routes (e.g. corpus/eldyrwild-markdown/... or evals/...)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path from dungeon_manifest_index or admitted evidence.",
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

    rel_path = str(params.get("path", "")).strip()
    max_chars = int(params.get("max_chars", 12000))

    if not rel_path:
        return _json({"success": False, "error": "path is required"})

    target = _resolve_document_path(rel_path)
    if target is None:
        return _json(
            {
                "success": False,
                "error": (
                    "document not found or path is not an allowed markdown file under "
                    "corpus/eldyrwild-markdown or repo root"
                ),
                "path": rel_path,
            }
        )

    text = _read_text(target)
    root = _repo_root()
    eldyrwild = _eldyrwild_corpus_dir().resolve()
    try:
        display_path = target.relative_to(eldyrwild).as_posix()
        path_kind = "eldyrwild_corpus_relative"
    except ValueError:
        display_path = target.relative_to(root.resolve()).as_posix()
        path_kind = "repo_relative"

    return _json(
        {
            "success": True,
            "tool": "dungeon_get_document",
            "path": display_path,
            "path_kind": path_kind,
            "title": _title_for(text, target),
            "chars_total": len(text),
            "truncated": len(text) > max_chars,
            "content": text[:max_chars],
        }
    )


DUNGEON_CHECK_CONTINUITY_SCHEMA = {
    "name": "dungeon_check_continuity",
    "description": (
        "Check a proposed campaign claim against corpus evidence. "
        "Uses manifest lookup when lexical fallback is disabled."
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

    if _lexical_fallback_enabled():
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
                    "Lexical fallback only. Does not adjudicate canon. "
                    "Prefer dungeon_context_lookup for grounded evidence."
                ),
            }
        )

    lookup_raw = handle_dungeon_context_lookup({"question": claim}, **kwargs)
    lookup = json.loads(lookup_raw)
    if not lookup.get("success"):
        return _json(
            {
                "success": False,
                "tool": "dungeon_check_continuity",
                "claim": claim,
                "error": lookup.get("error", "context lookup failed"),
            }
        )

    admitted = list(lookup.get("context_packet", {}).get("admitted_evidence") or [])
    matches = [
        {
            "path": row.get("path"),
            "source_role": row.get("source_role"),
            "authority": row.get("authority"),
            "evidence_id": row.get("evidence_id"),
            "excerpt": row.get("text_excerpt"),
            "line_start": row.get("line_start"),
            "line_end": row.get("line_end"),
        }
        for row in admitted[:top_k]
    ]

    return _json(
        {
            "success": True,
            "tool": "dungeon_check_continuity",
            "claim": claim,
            "status": "manifest_evidence_candidates",
            "matches": matches,
            "sufficiency_summary": lookup.get("sufficiency_summary"),
            "continuity_warning": (
                "Does not adjudicate canon. Returns manifest-admitted evidence candidates only."
            ),
        }
    )


def register(ctx: Any) -> None:
    ctx.register_tool(
        name="dungeon_context_lookup",
        toolset="dungeonbuddy",
        schema=DUNGEON_CONTEXT_LOOKUP_SCHEMA,
        handler=handle_dungeon_context_lookup,
        description="Manifest-backed context lookup for campaign questions.",
    )

    ctx.register_tool(
        name="dungeon_manifest_index",
        toolset="dungeonbuddy",
        schema=DUNGEON_MANIFEST_INDEX_SCHEMA,
        handler=handle_dungeon_manifest_index,
        description="Read-only manifest route index.",
    )

    ctx.register_tool(
        name="dungeon_get_document",
        toolset="dungeonbuddy",
        schema=DUNGEON_GET_DOCUMENT_SCHEMA,
        handler=handle_dungeon_get_document,
        description="Read one allowed markdown document.",
    )

    ctx.register_tool(
        name="dungeon_check_continuity",
        toolset="dungeonbuddy",
        schema=DUNGEON_CHECK_CONTINUITY_SCHEMA,
        handler=handle_dungeon_check_continuity,
        description="Find evidence related to a proposed continuity claim.",
    )

    if _lexical_fallback_enabled():
        ctx.register_tool(
            name="dungeon_search",
            toolset="dungeonbuddy",
            schema=DUNGEON_SEARCH_SCHEMA,
            handler=handle_dungeon_search,
            description="Legacy lexical markdown search (fallback only).",
        )

    skill_path = Path(__file__).parent / "skills" / "dungeonbuddy-corpus-qa" / "SKILL.md"
    if skill_path.exists():
        ctx.register_skill("corpus-qa", skill_path)
