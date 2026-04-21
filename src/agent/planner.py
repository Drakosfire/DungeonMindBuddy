"""Corpus-grounded session planner: tree manifest + Responses API tool loop (no FactStore).

Uses ``client.responses.create`` (same family as ingestion ``responses.parse`` in
``entity_extractor`` / ``fact_extractor``), not Chat Completions.

Optional DungeonMind statblock integration: set ``DUNGEONMIND_STATBLOCK_URL`` to a POST
endpoint that accepts JSON ``{creature_name, description, challenge_rating?, source_statblock_markdown?, source_statblock_format?}`` and returns
JSON with one of ``statblock``, ``markdown``, ``text``, or ``content`` (string), or plain
text body. When ``source_statblock_markdown`` is present it is the corpus statblock body loaded server-side from ``source_statblock_corpus_path`` (Markdown); ``source_statblock_format`` is ``markdown`` today (``html`` reserved for future corpus/HTML sources). Optional ``DUNGEONMIND_STATBLOCK_API_KEY`` sends ``Authorization: Bearer …``.
If the URL is unset or the request fails, statblocks are generated via a local
``responses.create`` call (Markdown only).
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Sequence
from typing import Any, Callable

import blake3

from src.agent.planner_pricing import usage_cost_usd
from src.agent.planner_turn_output_schema import (
    planner_turn_output_schema_enabled,
    planner_turn_text_format,
)
from src.agent.planner_skill_dispatch_guards import (
    wrap_dispatch_for_skill,
)
from src.agent.planner_skill_output_schema import (
    skill_text_format_for,
)
from src.agent.planner_telemetry import (
    log_telemetry,
    maybe_full_text,
    response_extras,
    summarize_tool_inputs,
    text_sig,
    usage_dict_from_response,
)
from src.agent.synthesis import _load_api_key
from src.llm.api_client import DungeonMindApiClient

_planner_logger = logging.getLogger("dmb.planner")
from src.prompts.corpus_session_planner import (
    STATBLOCK_TOOL_DESCRIPTION,
    STATBLOCK_VIA_RESPONSES_SYSTEM,
    build_corpus_session_planner_instructions,
)

_MAX_FILE_CHARS = 30_000
_MAX_TOOL_ROUNDS_PER_USER_TURN = 25

# Bumped in ``planner_cache`` meta when corpus manifest format changes (tree + ref tokens).
PLANNER_MANIFEST_BUILDER_ID = "corpus_path_refs_v1"
_CORPUS_REF_HEX = re.compile(r"^[0-9a-f]{10,32}$", re.IGNORECASE)

_STATBLOCK_URL_ENV = "DUNGEONMIND_STATBLOCK_URL"
_STATBLOCK_API_KEY_ENV = "DUNGEONMIND_STATBLOCK_API_KEY"

_PLANNER_POLICY_ACTION = "corpus_session_planner"
_DEFAULT_PLANNER_MODEL = "gpt-5.4-mini"


def _model_policy_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [here.parents[2] / "MODEL_POLICY.json", here.parents[3] / "MODEL_POLICY.json"]


def _resolve_planner_model(model: str | None) -> str:
    """
    Model id for ``responses.create`` (planner + statblock fallback in this module).

    Order: explicit ``model`` argument, else ``MODEL_POLICY.json`` action
    ``corpus_session_planner`` → role → ``models`` entry (e.g. ``fast_smart_mini`` → ``gpt-5.4-mini``),
    else ``_DEFAULT_PLANNER_MODEL``.
    """
    if model and str(model).strip():
        return str(model).strip()
    for policy_path in _model_policy_paths():
        if not policy_path.is_file():
            continue
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        role = policy.get("actions", {}).get(_PLANNER_POLICY_ACTION)
        if not role:
            continue
        mid = policy.get("models", {}).get(str(role))
        if isinstance(mid, str) and mid.strip():
            return mid.strip()
    return _DEFAULT_PLANNER_MODEL


def _assign_unique_path_refs(sorted_relpaths: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Deterministic short refs for corpus-relative markdown paths.

    Returns ``(ref_hex -> relpath, relpath -> ref_hex)`` with lowercase hex keys.
    """
    ref_to_rel: dict[str, str] = {}
    rel_to_ref: dict[str, str] = {}
    for rel in sorted_relpaths:
        digest = blake3.blake3(rel.encode("utf-8")).hexdigest()
        width = 10
        chosen: str | None = None
        while width <= 32:
            cand = digest[:width].lower()
            existing = ref_to_rel.get(cand)
            if existing is None or existing == rel:
                chosen = cand
                break
            width += 2
        if chosen is None:
            raise RuntimeError(f"could not assign unique corpus path ref for {rel!r}")
        ref_to_rel[chosen] = rel
        rel_to_ref[rel] = chosen
    return ref_to_rel, rel_to_ref


def build_corpus_path_ref_index(corpus_dir: Path) -> dict[str, str]:
    """Map ``ref_hex`` -> corpus-relative ``.md`` path (posix). Empty when corpus is missing."""
    root = corpus_dir.resolve()
    if not root.is_dir():
        return {}
    rels = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.md") if p.is_file())
    ref_to_rel, _ = _assign_unique_path_refs(rels)
    return ref_to_rel


def build_corpus_manifest_and_ref_index(corpus_dir: Path) -> tuple[str, dict[str, str]]:
    """
    Indented corpus tree plus a ref map for stable ``c:<ref>`` read tokens.

    Each ``.md`` line ends with `` [c:REF]`` so the model can pass ``path: "c:REF"`` without
    transcribing long paths.
    """
    root = corpus_dir.resolve()
    if not root.is_dir():
        return (f"(corpus directory not found: {root})", {})

    rels = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.md") if p.is_file())
    ref_to_rel, rel_to_ref = _assign_unique_path_refs(rels)

    lines: list[str] = [f"Corpus root: {root.name}/", ""]

    def walk(directory: Path, prefix: str) -> None:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for idx, entry in enumerate(entries):
            is_last = idx == len(entries) - 1
            branch = "└── " if is_last else "├── "
            if entry.is_dir():
                lines.append(f"{prefix}{branch}{entry.name}/")
                extension = "    " if is_last else "│   "
                walk(entry, prefix + extension)
            elif entry.suffix.lower() == ".md":
                relpath = entry.relative_to(root).as_posix()
                ref = rel_to_ref[relpath]
                lines.append(f"{prefix}{branch}{entry.name}  [c:{ref}]")

    walk(root, "")
    return "\n".join(lines), ref_to_rel


def build_corpus_manifest(corpus_dir: Path) -> str:
    """Build an indented tree of directories and ``.md`` files (with `` [c:REF]`` tokens per file)."""
    return build_corpus_manifest_and_ref_index(corpus_dir)[0]


def _resolve_planner_read_argument(
    corpus_dir: Path,
    raw: str,
    ref_index: dict[str, str],
) -> str:
    """
    Turn ``read_corpus_file`` / ``load_context_markdown`` ``path`` into a corpus-relative path string.

    Accepts ``c:<ref>`` (or bare ``<ref>`` when it matches the ref map and has no ``/``),
    otherwise returns a normalized literal relative path attempt.
    """
    s = raw.strip().replace("\\", "/")
    if not s:
        return ""
    low = s.lower()
    if low.startswith("c:"):
        tok = s[2:].strip().lower()
        return ref_index.get(tok, "")
    if "/" not in s and _CORPUS_REF_HEX.match(low) and low in ref_index:
        return ref_index[low]
    return s.lstrip("/")


def _canonical_corpus_relpath(corpus_dir: Path, rel: str) -> str | None:
    path = _resolve_safe_corpus_file(corpus_dir, rel)
    if path is None:
        return None
    return path.relative_to(corpus_dir.resolve()).as_posix()


def arguments_for_read_tool_trace(
    corpus_path: Path,
    tool_name: str,
    args_obj: dict[str, Any],
    ref_map: dict[str, str],
) -> dict[str, Any]:
    """Copy tool ``arguments`` with ``path`` rewritten to a canonical corpus-relative ``.md`` path when known."""
    trace_args = dict(args_obj)
    if tool_name in ("read_corpus_file", "load_context_markdown"):
        p0 = str(args_obj.get("path", "")).strip()
        resolved = _resolve_planner_read_argument(corpus_path, p0, ref_map) or p0
        canon = _canonical_corpus_relpath(corpus_path, resolved)
        if canon:
            trace_args["path"] = canon
    return trace_args


def _resolve_safe_corpus_file(corpus_dir: Path, rel_path: str) -> Path | None:
    """Resolve rel_path under corpus_dir; return path only if it is a .md file inside corpus."""
    corpus_root = corpus_dir.resolve()
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


_NOTES_STAGING_SUFFIXES = (".md", ".txt")


def _resolve_safe_corpus_notes_staging_file(corpus_dir: Path, rel_path: str) -> Path | None:
    """Like :func:`_resolve_safe_corpus_file` but allows ``.md`` or ``.txt`` (ingest staging only)."""
    corpus_root = corpus_dir.resolve()
    cleaned = rel_path.strip().replace("\\", "/").lstrip("/")
    if not cleaned or ".." in Path(cleaned).parts:
        return None
    candidate = (corpus_root / cleaned).resolve()
    try:
        candidate.relative_to(corpus_root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    if candidate.suffix.lower() not in _NOTES_STAGING_SUFFIXES:
        return None
    return candidate


def _read_optional_corpus_statblock_attachment(
    corpus_dir: Path, rel_path: str
) -> tuple[str | None, str | None]:
    """
    Load ``rel_path`` for ``generate_statblock`` baseline attachment.

    Returns ``(error_message, None)`` on failure, or ``(None, body)`` on success.
    """
    cleaned = rel_path.strip()
    if not cleaned:
        return None, None
    path = _resolve_safe_corpus_file(corpus_dir, cleaned)
    if path is None:
        return (
            "Error: source_statblock_corpus_path must be a corpus-relative `.md` file "
            "(literal path from the manifest; no `..` or globs).",
            None,
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    total = len(text)
    if total > _MAX_FILE_CHARS:
        text = (
            text[:_MAX_FILE_CHARS]
            + f"\n\n[Truncated at {_MAX_FILE_CHARS} characters; file is {total} chars total.]"
        )
    return None, text


def _read_corpus_file_impl(corpus_dir: Path, rel_path: str) -> str:
    path = _resolve_safe_corpus_file(corpus_dir, rel_path)
    if path is None:
        return (
            "Error: path must be a markdown file relative to the corpus root "
            "(use paths from the corpus tree, e.g. "
            "`Elderwyld/Migrating Forest/the_migrating_forest_executive_dm_summary.md`)."
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > _MAX_FILE_CHARS:
        return (
            text[:_MAX_FILE_CHARS]
            + f"\n\n[Truncated at {_MAX_FILE_CHARS} characters; file is {len(text)} chars total.]"
        )
    return text


def _planner_writer_tools_responses() -> list[dict[str, Any]]:
    """Two-phase corpus-write tools + recap-context resolver (registered together
    when ``allow_corpus_writes=True`` because they form one workflow surface)."""
    return [
        {
            "type": "function",
            "name": "get_recap_context",
            "description": (
                "Deterministic recap-ingest context for the `recap-write` skill. "
                "Returns the active campaign, the target session number, the **3 "
                "most-recent prior recaps** (sorted by frontmatter `session: N`, not "
                "filename), and the unique companion prep doc at "
                "`Session Prep/session_<target>_*.md` (or null). Call this once at the "
                "start of any recap-ingest turn instead of listing `Session Recaps/` "
                "yourself, picking recaps by filename, or globbing for prep docs. "
                "With no arguments it auto-detects the campaign with the freshest "
                "session and uses `target = max(session) + 1`. Pass `campaign_id` to "
                "pin a specific campaign (e.g. ingesting an out-of-order session); "
                "pass `target_session` to pin a session number (e.g. re-ingest)."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": (
                            "Optional. Frontmatter `campaign_id` (e.g. `longmont-c2`)."
                        ),
                    },
                    "target_session": {
                        "type": "integer",
                        "description": (
                            "Optional. Override the auto-detected next-session number."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "assemble_recap_draft",
            "description": (
                "Mechanically build a full recap markdown draft from raw session notes on disk — "
                "same algorithm as `recap_ingest_helpers.assemble_recap` (strip leading title, "
                "split paragraphs, remove duplicate paragraphs deterministically, emit frontmatter + "
                "H1 + body). Call **after** `get_recap_context` and **after** you have read the "
                "prior recaps / prep doc for shape survey. Pass the corpus-relative path to the "
                "staging file that holds the raw notes, plus `target_session` and `campaign_id` "
                "from `get_recap_context`. Use the returned `recap_body` as the `content` argument "
                "to `write_corpus_file` `mode='create'` (two-phase). Do **not** re-judge or "
                "re-merge duplicate paragraphs in prose — the tool already removed them."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_notes_path": {
                        "type": "string",
                        "description": (
                            "Corpus-relative path to `.md` or `.txt` containing the GM's raw notes "
                            "(often a `_ingest_staging/` file mirrored from the user message)."
                        ),
                    },
                    "target_session": {
                        "type": "integer",
                        "description": "Must match `get_recap_context.target_session`.",
                    },
                    "campaign_id": {
                        "type": "string",
                        "description": "Must match `get_recap_context.campaign_id` (frontmatter id).",
                    },
                },
                "required": ["raw_notes_path", "target_session", "campaign_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "build_recap_write_payload",
            "description": (
                "Deterministic ``recap_write_v1`` fields from the same raw notes + context as "
                "`assemble_recap_draft`: `duplicate_paragraphs`, `prep_pointer_proposal` "
                "(when a prep doc exists), `recap_preview.path`/`mode`, and empty "
                "`recap_preview.confirm_token` (paste the token after `write_corpus_file` "
                "dry_run). Also returns empty `npc_audit` lists, `plot_artifacts: []`, and "
                "`notes_for_gm: \"\"` — you fill judgment fields and the token in your final "
                "JSON. Call after `assemble_recap_draft` when you want mechanical payload "
                "fields without hand-copying them from the draft."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_notes_path": {
                        "type": "string",
                        "description": "Same as `assemble_recap_draft.raw_notes_path`.",
                    },
                    "target_session": {
                        "type": "integer",
                        "description": "Same as `assemble_recap_draft.target_session`.",
                    },
                    "campaign_id": {
                        "type": "string",
                        "description": "Same as `assemble_recap_draft.campaign_id`.",
                    },
                },
                "required": ["raw_notes_path", "target_session", "campaign_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "write_corpus_file",
            "description": (
                "Guarded write into the campaign corpus. Two-phase commit: call once with "
                "`dry_run=true` (default) to get a unified-diff `preview` and a `confirm_token`, "
                "then call again with `dry_run=false` and the same `confirm_token` to actually "
                "write. Path allowlist: `mode='create'` is only allowed for "
                "`**/Session Recaps/Session NN - <slug>.md`; `mode='append'` is only allowed for "
                "`**/NPCs/<slug>/timeline.md` and `**/NPCs/<slug>/README.md`. Dossier "
                "(`*_character_dossier.md`), seed (`character_seed.md`), and statblock "
                "(`*_statblock*.md`) files are read-only. Surface the diff to the human and wait "
                "for explicit `apply` before the commit phase."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Corpus-relative `.md` path (no `c:<ref>` tokens here).",
                    },
                    "mode": {"type": "string", "enum": ["create", "append"]},
                    "content": {
                        "type": "string",
                        "description": (
                            "Full file body for `create`; new tail content to append (preserves "
                            "existing prefix) for `append`. Trailing newline added automatically."
                        ),
                    },
                    "dry_run": {"type": "boolean"},
                    "confirm_token": {
                        "type": "string",
                        "description": "Echo the token from the prior `dry_run` call to commit.",
                    },
                },
                "required": ["path", "mode", "content"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "append_timeline_row",
            "description": (
                "Append one row to the campaign-hub `NPCs/<slug>/timeline.md` for an NPC. "
                "Wraps `write_corpus_file` so the model cannot accidentally rewrite the table. "
                "Two-phase: dry-run returns preview + `confirm_token`; second call with "
                "`confirm_token` commits. ``recap_path`` must already exist under the corpus. "
                "If multiple `NPCs/<slug>/timeline.md` exist (e.g. campaign 1 vs campaign 2), "
                "pass `timeline_path` to disambiguate."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "npc_slug": {"type": "string"},
                    "session": {"type": "integer"},
                    "beat": {
                        "type": "string",
                        "description": "One-cell telegraphic summary of this NPC's beat.",
                    },
                    "recap_path": {
                        "type": "string",
                        "description": "Corpus-relative path to the recap `.md` (must exist).",
                    },
                    "timeline_path": {
                        "type": "string",
                        "description": (
                            "Optional explicit path to `NPCs/<slug>/timeline.md` when multiple "
                            "candidates exist."
                        ),
                    },
                    "dry_run": {"type": "boolean"},
                    "confirm_token": {"type": "string"},
                },
                "required": ["npc_slug", "session", "beat", "recap_path"],
                "additionalProperties": False,
            },
        },
    ]


def _planner_tools_responses(*, include_write_tools: bool = False) -> list[dict[str, Any]]:
    """Function tools for ``responses.create`` (flat ``name`` / ``parameters``, not nested ``function``)."""
    base: list[dict[str, Any]] = [
        {
            "type": "function",
            "name": "read_corpus_file",
            "description": (
                "Load the full text of one `.md` file under the campaign corpus root. "
                "Pass either a corpus-relative path (tree or hub README) **or** a `c:…` ref copied from "
                "the ` [c:…] ` suffix after each `.md` line in the tree (server resolves to the real path). "
                "Literal paths only—no `*` or `?` globs. "
                "Returns the file body for grounding; very large files may be truncated with a clear suffix "
                "in the return text. "
                "Call before stating campaign-specific facts from that file; how reads appear in your "
                "final message (path citations vs verbatim quoted excerpts) follows system instructions."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Corpus-relative `.md` path **or** `c:<ref>` from the tree's ` [c:…] ` suffix "
                            "(avoids transcribing long paths)."
                        ),
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "load_context_markdown",
            "description": (
                "Attach one `.md` file from the corpus into the **working context** for this turn: "
                "same body as `read_corpus_file`, but use this when the file should be treated as a "
                "**loaded artifact** the rest of the reasoning depends on (e.g. the canonical mechanical "
                "statblock after you have already skimmed the hub README). "
                "Use `read_corpus_file` for discovery passes (README, dossier, timeline); call "
                "`load_context_markdown` once for the **selected** statblock path. "
                "If you will call `generate_statblock` with `source_statblock_corpus_path` naming a "
                "corpus statblock you discovered, call `load_context_markdown` on that same path first "
                "when the file exists. "
                "Corpus-relative path or `c:<ref>` from the tree—no globs."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Corpus-relative `.md` path or `c:<ref>` token for the file to attach "
                            "(e.g. canonical `*_statblock_*.md`)."
                        ),
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "generate_statblock",
            "description": STATBLOCK_TOOL_DESCRIPTION,
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "creature_name": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": "Physical, tactical, and lore hooks for the stat block.",
                    },
                    "challenge_rating": {
                        "type": "string",
                        "description": "Optional CR hint, e.g. '3' or '1/4'.",
                    },
                    "source_statblock_corpus_path": {
                        "type": "string",
                        "description": (
                            "Optional. Corpus-relative path **or** `c:<ref>` to an existing `.md` statblock "
                            "the tool reads and sends as `source_statblock_markdown` to the statblock service "
                            "(and includes in the local fallback prompt). Use this instead of pasting "
                            "the full statblock into `description`; name the NPC and your deltas in "
                            "`description`. When this path came from research (hub README / tree), "
                            "call `load_context_markdown` on it in the same turn before calling "
                            "`generate_statblock` so the sheet is explicitly attached. "
                            "Format on the wire is Markdown (`source_statblock_format` "
                            "`markdown`); HTML attachment is reserved for a future corpus type."
                        ),
                    },
                    "source_statblock_format": {
                        "type": "string",
                        "description": (
                            "When `source_statblock_corpus_path` is set: wire format for the attached "
                            "body. Use `markdown` (default) for corpus `.md` statblocks. Value `html` "
                            "is accepted for forward compatibility but corpus attach today only loads "
                            "`.md` files as Markdown."
                        ),
                    },
                },
                "required": ["creature_name", "description"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "list_npc_hubs",
            "description": (
                "Deterministic inventory of NPC subject-hub folders under a campaign `NPCs/` directory. "
                "Returns each child slug plus whether `timeline.md` / `README.md` exist — use before "
                "guessing whether a campaign-hub NPC package exists. Read-only."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "npcs_root": {
                        "type": "string",
                        "description": (
                            "Corpus-relative path ending in `/NPCs`, e.g. "
                            "`Longmont Campaign/Campaign 2/NPCs`."
                        ),
                    },
                },
                "required": ["npcs_root"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "list_pc_hubs",
            "description": (
                "Deterministic inventory of PC subject-hub folders under a campaign `PCs/` directory. "
                "Returns each child slug plus whether `timeline.md` / `README.md` exist. Read-only."
            ),
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "pcs_root": {
                        "type": "string",
                        "description": (
                            "Corpus-relative path ending in `/PCs`, e.g. "
                            "`Longmont Campaign/Campaign 2/PCs`."
                        ),
                    },
                },
                "required": ["pcs_root"],
                "additionalProperties": False,
            },
        },
    ]
    if include_write_tools:
        base.extend(_planner_writer_tools_responses())
    return base


def _function_calls_from_response(response: Any) -> list[Any]:
    """Collect output items of type ``function_call`` from a Responses API ``response``."""
    out: list[Any] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) == "function_call":
            out.append(item)
    return out


def make_tool_dispatcher(
    corpus_path: Path,
    client: Any,
    model_id: str,
    *,
    statblock_stub: str | None = None,
    tool_cost_sink: list[dict[str, Any]] | None = None,
    corpus_path_ref_index: dict[str, str] | None = None,
    allow_corpus_writes: bool = False,
) -> Callable[[str, str], str]:
    """Build the planner tool dispatch closure (corpus reads, context loads, statblock).

    When ``allow_corpus_writes=True``, also routes ``get_recap_context``,
    ``assemble_recap_draft``, ``build_recap_write_payload``, ``write_corpus_file``, and ``append_timeline_row``
    through the recap / corpus-writer stack. The default is ``False`` so the live
    planner used by evals never gains write capability silently.
    """
    ref_index: dict[str, str] = (
        corpus_path_ref_index
        if corpus_path_ref_index is not None
        else build_corpus_path_ref_index(corpus_path)
    )

    def dispatch(name: str, raw_args: str) -> str:
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError as exc:
            return f"Error: invalid JSON arguments for {name}: {exc}"
        if name in ("read_corpus_file", "load_context_markdown"):
            path_raw = str(args.get("path", "")).strip()
            if not path_raw:
                return "Error: missing path."
            if path_raw.lower().startswith("c:") and not _resolve_planner_read_argument(
                corpus_path, path_raw, ref_index
            ):
                return (
                    "Error: unknown corpus file ref "
                    f"{path_raw!r}. Copy a ` [c:…] ` token from the corpus tree after the `.md` name, "
                    "or pass the full corpus-relative `.md` path."
                )
            resolved = _resolve_planner_read_argument(corpus_path, path_raw, ref_index) or path_raw
            body = _read_corpus_file_impl(corpus_path, resolved)
            if body.startswith("Error:"):
                return body
            canon = _canonical_corpus_relpath(corpus_path, resolved)
            if name == "load_context_markdown":
                label = canon or resolved
                return f"[context attached: {label}]\n\n{body}"
            return body
        if name == "generate_statblock":
            cn = str(args.get("creature_name", "")).strip()
            desc = str(args.get("description", "")).strip()
            cr = args.get("challenge_rating")
            cr_str = str(cr).strip() if cr is not None else None
            src_raw = str(args.get("source_statblock_corpus_path", "")).strip()
            if src_raw.lower().startswith("c:") and not _resolve_planner_read_argument(
                corpus_path, src_raw, ref_index
            ):
                return (
                    "Error: unknown corpus file ref "
                    f"{src_raw!r} for source_statblock_corpus_path. Copy a ` [c:…] ` token from the "
                    "corpus tree, or pass the full corpus-relative `.md` path."
                )
            src_rel = (
                _resolve_planner_read_argument(corpus_path, src_raw, ref_index) or src_raw
            ).strip()
            src_fmt = str(args.get("source_statblock_format", "markdown") or "markdown").strip().lower()
            if src_fmt not in ("markdown", "html"):
                src_fmt = "markdown"
            if not cn or not desc:
                return "Error: creature_name and description are required."
            src_err: str | None
            src_body: str | None
            src_err, src_body = _read_optional_corpus_statblock_attachment(corpus_path, src_rel)
            if src_err:
                return src_err
            if statblock_stub is not None:
                if src_body and src_rel:
                    return (
                        f"[Attached corpus statblock: {src_rel} ({len(src_body)} chars), "
                        f"format={src_fmt}]\n\n{statblock_stub}"
                    )
                return statblock_stub
            text, cost = _generate_statblock_impl(
                client,
                model_id,
                cn,
                desc,
                cr_str or None,
                source_statblock_markdown=src_body,
                source_statblock_format=src_fmt,
                source_statblock_relpath=src_rel or None,
            )
            if tool_cost_sink is not None and cost is not None:
                tool_cost_sink.append(cost)
            if src_body and src_rel:
                return (
                    f"[Attached corpus statblock baseline: {src_rel} ({len(src_body)} chars), "
                    f"wire_format={src_fmt}]\n\n{text}"
                )
            return text
        if name == "list_npc_hubs":
            return _list_campaign_subject_hubs_json(
                corpus_path,
                str(args.get("npcs_root", "")).strip(),
                leaf_dir="NPCs",
            )
        if name == "list_pc_hubs":
            return _list_campaign_subject_hubs_json(
                corpus_path,
                str(args.get("pcs_root", "")).strip(),
                leaf_dir="PCs",
            )
        if name == "get_recap_context":
            if not allow_corpus_writes:
                return (
                    "Error: get_recap_context is disabled (planner started with "
                    "allow_corpus_writes=False). Re-launch with corpus writes enabled to use it."
                )
            from src.agent.recap_context import (
                RecapContextError as _RecapContextError,
                resolve_recap_context as _resolve_recap_context,
            )

            cid_arg = args.get("campaign_id")
            cid = str(cid_arg).strip() if cid_arg is not None and str(cid_arg).strip() else None
            ts_arg = args.get("target_session")
            target_int: int | None
            if ts_arg is None or (isinstance(ts_arg, str) and not ts_arg.strip()):
                target_int = None
            else:
                try:
                    target_int = int(ts_arg)
                except (TypeError, ValueError):
                    return "Error: get_recap_context.target_session must be an integer."
            try:
                ctx = _resolve_recap_context(
                    corpus_path, campaign_id=cid, target_session=target_int
                )
            except _RecapContextError as exc:
                return f"Error: {exc}"
            return json.dumps(ctx.to_dict(), ensure_ascii=False)
        if name == "assemble_recap_draft":
            if not allow_corpus_writes:
                return (
                    "Error: assemble_recap_draft is disabled (planner started with "
                    "allow_corpus_writes=False). Re-launch with corpus writes enabled to use it."
                )
            from src.agent.recap_ingest_helpers import assemble_recap as _assemble_recap

            raw_rel = str(args.get("raw_notes_path", "")).strip()
            notes_path = _resolve_safe_corpus_notes_staging_file(corpus_path, raw_rel)
            if notes_path is None:
                return (
                    "Error: raw_notes_path must be a corpus-relative `.md` or `.txt` file under "
                    "the corpus (no `..` or globs)."
                )
            try:
                raw_text = notes_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return f"Error: cannot read raw_notes_path {raw_rel!r}: {exc}"
            ts_raw = args.get("target_session")
            try:
                ts_int = int(ts_raw)
            except (TypeError, ValueError):
                return "Error: assemble_recap_draft.target_session must be an integer."
            cid = str(args.get("campaign_id", "")).strip()
            if not cid:
                return "Error: assemble_recap_draft.campaign_id is required."
            full, ingest_report = _assemble_recap(
                raw_notes=raw_text,
                session=ts_int,
                campaign_id=cid,
                remove_duplicates=True,
            )
            removed = ingest_report.duplicates_removed
            payload = {
                "recap_body": full,
                "duplicates_removed": len(removed),
                "ingest_report": {
                    "title_line_stripped": ingest_report.title_line_stripped,
                    "duplicates_detected": len(ingest_report.duplicates_detected),
                    "duplicates_removed": len(removed),
                    "paragraph_count_in": ingest_report.paragraph_count_in,
                    "paragraph_count_out": ingest_report.paragraph_count_out,
                    "removed_pairs_preview": [
                        {
                            "keep_lines": [m.a.source_line_start, m.a.source_line_end],
                            "drop_lines": [m.b.source_line_start, m.b.source_line_end],
                        }
                        for m in removed[:5]
                    ],
                },
            }
            return json.dumps(payload, ensure_ascii=False)
        if name == "build_recap_write_payload":
            if not allow_corpus_writes:
                return (
                    "Error: build_recap_write_payload is disabled (planner started with "
                    "allow_corpus_writes=False). Re-launch with corpus writes enabled to use it."
                )
            from src.agent.recap_context import RecapContextError, resolve_recap_context
            from src.agent.recap_ingest_helpers import assemble_recap as _assemble_recap
            from src.agent.recap_write_mechanical_payload import (
                build_recap_write_payload_from_ingest,
            )

            raw_rel = str(args.get("raw_notes_path", "")).strip()
            notes_path = _resolve_safe_corpus_notes_staging_file(corpus_path, raw_rel)
            if notes_path is None:
                return (
                    "Error: raw_notes_path must be a corpus-relative `.md` or `.txt` file under "
                    "the corpus (no `..` or globs)."
                )
            try:
                raw_text = notes_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return f"Error: cannot read raw_notes_path {raw_rel!r}: {exc}"
            ts_raw = args.get("target_session")
            try:
                ts_int = int(ts_raw)
            except (TypeError, ValueError):
                return "Error: build_recap_write_payload.target_session must be an integer."
            cid = str(args.get("campaign_id", "")).strip()
            if not cid:
                return "Error: build_recap_write_payload.campaign_id is required."
            _full, ingest_report = _assemble_recap(
                raw_notes=raw_text,
                session=ts_int,
                campaign_id=cid,
                remove_duplicates=True,
            )
            try:
                ctx = resolve_recap_context(
                    corpus_path, campaign_id=cid, target_session=ts_int
                )
            except RecapContextError as exc:
                return f"Error: {exc}"
            payload = build_recap_write_payload_from_ingest(ctx, ingest_report)
            return json.dumps(payload, ensure_ascii=False)
        if name in ("write_corpus_file", "append_timeline_row"):
            if not allow_corpus_writes:
                return (
                    f"Error: {name} is disabled (planner started with "
                    "allow_corpus_writes=False). Re-launch with corpus writes enabled to use it."
                )
            from src.agent.corpus_writer import (
                append_timeline_row as _append_timeline_row,
                write_corpus_file as _write_corpus_file,
            )

            if name == "write_corpus_file":
                result = _write_corpus_file(
                    corpus_path,
                    path=str(args.get("path", "")),
                    mode=str(args.get("mode", "")),
                    content=str(args.get("content", "")),
                    dry_run=bool(args.get("dry_run", True)),
                    confirm_token=(args.get("confirm_token") or None),
                )
            else:
                sess_raw = args.get("session")
                try:
                    sess_int = int(sess_raw)
                except (TypeError, ValueError):
                    return "Error: append_timeline_row.session must be an integer."
                result = _append_timeline_row(
                    corpus_path,
                    npc_slug=str(args.get("npc_slug", "")),
                    session=sess_int,
                    beat=str(args.get("beat", "")),
                    recap_path=str(args.get("recap_path", "")),
                    timeline_path=(args.get("timeline_path") or None),
                    dry_run=bool(args.get("dry_run", True)),
                    confirm_token=(args.get("confirm_token") or None),
                )
            return json.dumps(result, ensure_ascii=False)
        return f"Error: unknown tool {name!r}"

    return dispatch


@dataclass
class PlanningTurnResult:
    """One user line through the Responses tool loop (for REPL and eval harnesses)."""

    final_text: str
    last_response_id: str
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    hit_tool_round_limit: bool = False


@dataclass
class PlanningModelStepRecord:
    """One model ``responses.create`` result (one 'step' for live evaluation)."""

    step_index: int
    response_id: str
    function_calls: list[dict[str, Any]]
    assistant_text: str


@dataclass
class ClarificationAlignmentReport:
    """Diagnostic record for ``apply_clarification_alignment_to_final_text`` (legacy hook).

    Clarification is expressed only in the model's final JSON; ``mode`` is always
    ``"no_clarification"`` and ``final_text`` is never rewritten here.
    """

    mode: str
    canonical_question: str | None = None
    pre_message_chars: int | None = None
    post_message_chars: int | None = None

    @property
    def changed(self) -> bool:
        return False


@dataclass
class PlanningTurnDetail:
    """Full turn with per-model-response steps (for live eval against a real model)."""

    final_text: str
    last_response_id: str
    tool_trace: list[dict[str, Any]]
    steps: list[PlanningModelStepRecord] = field(default_factory=list)
    hit_tool_round_limit: bool = False
    telemetry_cost: dict[str, Any] | None = None
    #: One entry per ``responses.create`` completion (API ``usage`` for that response).
    usage_rounds: list[dict[str, Any]] = field(default_factory=list)
    #: Raw model output before clarification alignment when alignment changed bytes; else ``None``.
    pre_alignment_final_text: str | None = None
    #: Diagnostic for the clarification alignment pass; ``None`` when alignment was never invoked.
    clarification_alignment: ClarificationAlignmentReport | None = None

    def as_turn_result(self) -> PlanningTurnResult:
        return PlanningTurnResult(
            final_text=self.final_text,
            last_response_id=self.last_response_id,
            tool_trace=self.tool_trace,
            hit_tool_round_limit=self.hit_tool_round_limit,
        )


def merge_planning_turn_details(
    first: PlanningTurnDetail,
    second: PlanningTurnDetail,
) -> PlanningTurnDetail:
    """Merge two chained turns (same ``previous_response_id`` thread) for scoring and artifacts.

    ``final_text`` and ``last_response_id`` come from ``second``; ``tool_trace`` and ``steps`` are
    concatenated. Telemetry costs are summed where numeric.
    """
    tc1 = dict(first.telemetry_cost or {})
    tc2 = dict(second.telemetry_cost or {})
    u1 = dict(tc1.get("planner_usage_totals") or {})
    u2 = dict(tc2.get("planner_usage_totals") or {})
    merged_usage = {k: int(u1.get(k, 0)) + int(u2.get(k, 0)) for k in set(u1) | set(u2)}
    rounds1 = list(tc1.get("planner_cost_by_round_usd") or [])
    rounds2 = list(tc2.get("planner_cost_by_round_usd") or [])
    planner_est = float(tc1.get("planner_estimated_cost_usd", 0) or 0) + float(
        tc2.get("planner_estimated_cost_usd", 0) or 0
    )
    stat_est = float(tc1.get("statblock_tool_estimated_cost_usd", 0) or 0) + float(
        tc2.get("statblock_tool_estimated_cost_usd", 0) or 0
    )
    merged_tc = {
        "planner_estimated_cost_usd": round(planner_est, 6),
        "statblock_tool_estimated_cost_usd": round(stat_est, 6),
        "scenario_estimated_cost_usd": round(planner_est + stat_est, 6),
        "planner_cost_by_round_usd": rounds1 + rounds2,
        "planner_usage_totals": merged_usage,
        "pricing_note": tc2.get("pricing_note") or tc1.get("pricing_note"),
    }
    return PlanningTurnDetail(
        final_text=second.final_text,
        last_response_id=second.last_response_id,
        tool_trace=list(first.tool_trace) + list(second.tool_trace),
        steps=list(first.steps) + list(second.steps),
        hit_tool_round_limit=first.hit_tool_round_limit or second.hit_tool_round_limit,
        telemetry_cost=merged_tc,
        usage_rounds=list(first.usage_rounds) + list(second.usage_rounds),
        pre_alignment_final_text=second.pre_alignment_final_text,
        clarification_alignment=second.clarification_alignment,
    )


def merge_planning_turn_details_chain(
    details: Sequence[PlanningTurnDetail],
) -> PlanningTurnDetail:
    """Fold an ordered sequence of chained turns into one detail (concat traces, last final_text).

    Pairwise uses :func:`merge_planning_turn_details` so telemetry costs and usage rounds
    accumulate the same way as manually merging two turns at a time.
    """
    seq = list(details)
    if not seq:
        raise ValueError("merge_planning_turn_details_chain requires at least one PlanningTurnDetail")
    acc = seq[0]
    for nxt in seq[1:]:
        acc = merge_planning_turn_details(acc, nxt)
    return acc


def _list_campaign_subject_hubs_json(
    corpus_path: Path,
    rel_root: str,
    *,
    leaf_dir: str,
) -> str:
    """Return JSON listing immediate child hub folders under ``…/NPCs`` or ``…/PCs``."""
    raw = str(rel_root or "").strip().replace("\\", "/").strip("/")
    if not raw:
        return json.dumps(
            {"ok": False, "error": f"missing corpus-relative {leaf_dir} root path"},
            ensure_ascii=False,
        )
    parts = Path(raw).parts
    if ".." in parts:
        return json.dumps(
            {"ok": False, "error": "path must not contain '..'", "subject_root": raw},
            ensure_ascii=False,
        )
    if parts[-1] != leaf_dir:
        return json.dumps(
            {
                "ok": False,
                "error": f"path must end with /{leaf_dir} (got {raw!r})",
                "subject_root": raw,
            },
            ensure_ascii=False,
        )
    root = (corpus_path / raw).resolve()
    try:
        root.relative_to(corpus_path.resolve())
    except ValueError:
        return json.dumps(
            {"ok": False, "error": "path resolves outside corpus root", "subject_root": raw},
            ensure_ascii=False,
        )
    if not root.is_dir():
        return json.dumps(
            {"ok": False, "error": f"not a directory: {raw!r}", "subject_root": raw},
            ensure_ascii=False,
        )
    hubs: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        slug = child.name
        timeline = child / "timeline.md"
        readme = child / "README.md"
        hubs.append(
            {
                "slug": slug,
                "folder_relative": f"{raw}/{slug}".replace("\\", "/"),
                "has_timeline_md": timeline.is_file(),
                "has_readme_md": readme.is_file(),
            }
        )
    return json.dumps(
        {
            "ok": True,
            "subject_root": raw,
            "subject_class": "npc" if leaf_dir == "NPCs" else "pc",
            "hub_count": len(hubs),
            "hubs": hubs,
        },
        ensure_ascii=False,
    )


def _telemetry_cost_fields(model_id: str, usage: dict[str, int]) -> dict[str, Any]:
    c = usage_cost_usd(
        model_id=model_id,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        cached_tokens=int(usage.get("cached_tokens", 0)),
    )
    return {
        "estimated_cost_usd": round(float(c["total_usd"]), 6),
        "cost_input_uncached_usd": round(float(c["input_usd"]), 6),
        "cost_cached_input_usd": round(float(c["cached_input_usd"]), 6),
        "cost_output_usd": round(float(c["output_usd"]), 6),
        "pricing_table_matched": c["pricing_table_matched"],
    }


def _function_calls_payload(response: Any) -> list[dict[str, Any]]:
    """Parse ``function_call`` output items into ``{name, arguments}`` dicts."""
    rows: list[dict[str, Any]] = []
    for call in _function_calls_from_response(response):
        raw = getattr(call, "arguments", None) or "{}"
        try:
            args_obj = json.loads(raw) if isinstance(raw, str) else {}
        except json.JSONDecodeError:
            args_obj = {"_raw": raw}
        rows.append({"name": getattr(call, "name", ""), "arguments": args_obj})
    return rows


def apply_clarification_alignment_to_final_text(
    tool_trace: list[dict[str, Any]],
    final_text: str,
) -> tuple[str, ClarificationAlignmentReport]:
    """Passthrough: the planner no longer has a clarification tool; GM-facing text is only in JSON."""
    _ = tool_trace
    return final_text, ClarificationAlignmentReport(mode="no_clarification")


def run_planning_turn_detailed(
    *,
    client: Any,
    model_id: str,
    instructions: str,
    tools: list[dict[str, Any]],
    corpus_path: Path,
    user_line: str,
    previous_response_id: str | None,
    dispatch_tool: Callable[[str, str], str],
    telemetry_context: dict[str, Any] | None = None,
    corpus_path_ref_index: dict[str, str] | None = None,
    active_skill_id: str | None = None,
    skill_read_allowlist_extras: list[str] | None = None,
    skill_recap_context: Any | None = None,
) -> PlanningTurnDetail:
    """Like ``run_planning_turn`` but records each model response as a ``PlanningModelStepRecord``.

    When ``active_skill_id`` resolves via :func:`skill_text_format_for` to a per-skill
    Responses ``text=`` block, that block replaces the universal planner envelope for
    every round of this turn. The caller is responsible for matching prompt instructions
    to the chosen schema.

    When ``active_skill_id`` is registered in
    :data:`src.agent.planner_skill_dispatch_guards.SKILL_DISPATCH_GUARDS`,
    ``dispatch_tool`` is wrapped with a fail-closed guard so out-of-scope tool
    calls are rejected at dispatch time (e.g. recap-write blocks
    ``read_corpus_file`` paths outside ``recent_recaps`` ∪ ``prep_doc_path``).
    Pass ``skill_read_allowlist_extras`` to extend the guard's allowlist (mirrors
    the Scope-B grader's ``read_allowlist_extra`` knob).

    Pass ``skill_recap_context`` (a ``RecapContext`` snapshot taken **before**
    any planner write) to freeze the recap-write read-allowlist for this turn.
    Multi-turn ingest scenarios MUST pass the same snapshot to every turn so a
    turn-1 commit cannot shift the resolver's view of ``max(session)`` and
    rewrite the allowlist mid-scenario. Typed ``Any`` to avoid importing
    ``RecapContext`` at module-load time for callers that don't use the
    recap-write skill; the dispatch-guard layer enforces the type at use site.
    """
    dispatch_tool = wrap_dispatch_for_skill(
        dispatch_tool,
        corpus_path=corpus_path,
        active_skill_id=active_skill_id,
        allowlist_extras=skill_read_allowlist_extras,
        precomputed_recap_context=skill_recap_context,
    )
    api_client = DungeonMindApiClient.wrap(client)
    ctx: dict[str, Any] = {"op": "planning_turn", **(telemetry_context or {})}
    turn_index = int(ctx.get("turn_index", 0) or 0)
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0}
    latency_ms_rounds: list[float] = []
    planner_round_cost_usd: list[float] = []

    def _absorb_usage(resp: Any, elapsed_ms: float) -> None:
        latency_ms_rounds.append(round(elapsed_ms, 2))
        u = usage_dict_from_response(resp)
        for k in usage_totals:
            usage_totals[k] += int(u.get(k, 0))

    tool_trace: list[dict[str, Any]] = []
    steps: list[PlanningModelStepRecord] = []
    usage_rounds: list[dict[str, Any]] = []
    ref_map: dict[str, str] = (
        corpus_path_ref_index
        if corpus_path_ref_index is not None
        else build_corpus_path_ref_index(corpus_path)
    )
    create_kw: dict[str, Any] = {
        "model": model_id,
        "instructions": instructions,
        "input": [{"type": "message", "role": "user", "content": user_line}],
        "tools": tools,
        "tool_choice": "auto",
        "truncation": "auto",
    }
    if planner_turn_output_schema_enabled():
        skill_fmt = skill_text_format_for(active_skill_id)
        create_kw["text"] = skill_fmt if skill_fmt is not None else planner_turn_text_format()
    if previous_response_id:
        create_kw["previous_response_id"] = previous_response_id

    log_telemetry(
        {
            **ctx,
            "event": "request",
            "response_index": 0,
            "phase": "initial_user",
            "model": model_id,
            "instructions_sig": text_sig(instructions),
            "user_message_sig": text_sig(user_line),
            "user_message_text": maybe_full_text(user_line),
            "corpus_path": str(corpus_path),
            "create_kw_keys": sorted(create_kw.keys()),
        }
    )
    first_call = api_client.responses_create(action="planner.turn.initial_user", **create_kw)
    response = first_call.response
    elapsed_ms = first_call.elapsed_ms
    _absorb_usage(response, elapsed_ms)
    u0 = usage_dict_from_response(response)
    c0 = usage_cost_usd(
        model_id=model_id,
        input_tokens=u0["input_tokens"],
        output_tokens=u0["output_tokens"],
        cached_tokens=u0["cached_tokens"],
    )
    planner_round_cost_usd.append(float(c0["total_usd"]))
    log_telemetry(
        {
            **ctx,
            "event": "response",
            "response_index": 0,
            "phase": "initial_user",
            "latency_ms": round(elapsed_ms, 2),
            "response_id": str(getattr(response, "id", "")),
            "model": getattr(response, "model", None),
            "usage": u0,
            **_telemetry_cost_fields(model_id, u0),
            "output_text": maybe_full_text((getattr(response, "output_text", None) or "").strip()),
            "extras": response_extras(response),
        }
    )
    usage_rounds.append(
        {
            "turn_index": turn_index,
            "response_index": 0,
            "phase": "initial_user",
            "latency_ms": round(elapsed_ms, 2),
            "response_id": str(getattr(response, "id", "")),
            "usage": dict(u0),
        }
    )

    hit_limit = False
    step_index = 0
    response_index = 1

    for _ in range(_MAX_TOOL_ROUNDS_PER_USER_TURN):
        fc_payload = _function_calls_payload(response)
        steps.append(
            PlanningModelStepRecord(
                step_index=step_index,
                response_id=str(response.id),
                function_calls=list(fc_payload),
                assistant_text=(response.output_text or "").strip(),
            )
        )
        step_index += 1

        calls = _function_calls_from_response(response)
        if not calls:
            text = (response.output_text or "").strip()
            aligned_text, align_report = apply_clarification_alignment_to_final_text(
                tool_trace, text
            )
            pre_alignment_final_text = text if aligned_text != text else None
            if align_report.mode != "no_clarification":
                log_telemetry(
                    {
                        **ctx,
                        "event": "clarification_align",
                        "mode": align_report.mode,
                        "question_chars": (
                            len(align_report.canonical_question)
                            if align_report.canonical_question is not None
                            else 0
                        ),
                        "pre_message_chars": align_report.pre_message_chars,
                        "post_message_chars": align_report.post_message_chars,
                        "changed": align_report.changed,
                    }
                )
            tc_full = usage_cost_usd(
                model_id=model_id,
                input_tokens=int(usage_totals["input_tokens"]),
                output_tokens=int(usage_totals["output_tokens"]),
                cached_tokens=int(usage_totals["cached_tokens"]),
            )
            log_telemetry(
                {
                    **ctx,
                    "event": "turn_complete",
                    "ok": True,
                    "hit_tool_round_limit": False,
                    "final_text_chars": len(aligned_text),
                    "usage_totals": dict(usage_totals),
                    "latency_ms_by_round": list(latency_ms_rounds),
                    "model_response_count": len(steps),
                    "planner_cost_by_round_usd": [round(x, 6) for x in planner_round_cost_usd],
                    "planner_estimated_cost_usd": round(float(tc_full["total_usd"]), 6),
                    "cost_input_uncached_usd": round(float(tc_full["input_usd"]), 6),
                    "cost_cached_input_usd": round(float(tc_full["cached_input_usd"]), 6),
                    "cost_output_usd": round(float(tc_full["output_usd"]), 6),
                    "pricing_table_matched": tc_full["pricing_table_matched"],
                }
            )
            return PlanningTurnDetail(
                final_text=aligned_text,
                last_response_id=response.id,
                tool_trace=tool_trace,
                steps=steps,
                hit_tool_round_limit=False,
                telemetry_cost={
                    "planner_estimated_cost_usd": round(float(tc_full["total_usd"]), 6),
                    "planner_cost_by_round_usd": [round(x, 6) for x in planner_round_cost_usd],
                    "planner_usage_totals": dict(usage_totals),
                    "pricing_note": "approximate public list prices; verify against billing",
                },
                usage_rounds=list(usage_rounds),
                pre_alignment_final_text=pre_alignment_final_text,
                clarification_alignment=align_report,
            )

        tool_inputs: list[dict[str, Any]] = []
        for call in calls:
            name = call.name
            raw = call.arguments or "{}"
            try:
                args_obj = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                args_obj = {"_raw": raw}
            out = dispatch_tool(name, raw)
            trace_args = arguments_for_read_tool_trace(corpus_path, name, args_obj, ref_map)
            tool_trace.append(
                {
                    "tool": name,
                    "arguments": trace_args,
                    "output_chars": len(out),
                    "output_excerpt": out[:800],
                }
            )
            tool_inputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": out,
                }
            )

        log_telemetry(
            {
                **ctx,
                "event": "request",
                "response_index": response_index,
                "phase": "tool_outputs",
                "model": model_id,
                "instructions_sig": text_sig(instructions),
                "previous_response_id": str(response.id),
                "tool_calls": [
                    {"name": call.name, "call_id": getattr(call, "call_id", None)} for call in calls
                ],
                "tool_inputs_summary": summarize_tool_inputs(tool_inputs),
            }
        )
        follow_kw: dict[str, Any] = {
            "model": model_id,
            "instructions": instructions,
            "previous_response_id": response.id,
            "input": tool_inputs,
            "tools": tools,
            "tool_choice": "auto",
            "truncation": "auto",
        }
        if planner_turn_output_schema_enabled():
            skill_fmt = skill_text_format_for(active_skill_id)
            follow_kw["text"] = (
                skill_fmt if skill_fmt is not None else planner_turn_text_format()
            )
        follow_call = api_client.responses_create(action="planner.turn.tool_outputs", **follow_kw)
        response = follow_call.response
        elapsed_follow = follow_call.elapsed_ms
        _absorb_usage(response, elapsed_follow)
        uf = usage_dict_from_response(response)
        cf = usage_cost_usd(
            model_id=model_id,
            input_tokens=uf["input_tokens"],
            output_tokens=uf["output_tokens"],
            cached_tokens=uf["cached_tokens"],
        )
        planner_round_cost_usd.append(float(cf["total_usd"]))
        log_telemetry(
            {
                **ctx,
                "event": "response",
                "response_index": response_index,
                "phase": "tool_outputs",
                "latency_ms": round(elapsed_follow, 2),
                "response_id": str(getattr(response, "id", "")),
                "model": getattr(response, "model", None),
                "usage": uf,
                **_telemetry_cost_fields(model_id, uf),
                "output_text": maybe_full_text((getattr(response, "output_text", None) or "").strip()),
                "extras": response_extras(response),
            }
        )
        usage_rounds.append(
            {
                "turn_index": turn_index,
                "response_index": response_index,
                "phase": "tool_outputs",
                "latency_ms": round(elapsed_follow, 2),
                "response_id": str(getattr(response, "id", "")),
                "usage": dict(uf),
            }
        )
        response_index += 1
    else:
        hit_limit = True
        fc_payload = _function_calls_payload(response)
        steps.append(
            PlanningModelStepRecord(
                step_index=step_index,
                response_id=str(response.id),
                function_calls=list(fc_payload),
                assistant_text=(response.output_text or "").strip(),
            )
        )

    text = (response.output_text or "").strip()
    aligned_text, align_report = apply_clarification_alignment_to_final_text(tool_trace, text)
    pre_alignment_final_text = text if aligned_text != text else None
    if align_report.mode != "no_clarification":
        log_telemetry(
            {
                **ctx,
                "event": "clarification_align",
                "mode": align_report.mode,
                "question_chars": (
                    len(align_report.canonical_question)
                    if align_report.canonical_question is not None
                    else 0
                ),
                "pre_message_chars": align_report.pre_message_chars,
                "post_message_chars": align_report.post_message_chars,
                "changed": align_report.changed,
            }
        )
    tc_full = usage_cost_usd(
        model_id=model_id,
        input_tokens=int(usage_totals["input_tokens"]),
        output_tokens=int(usage_totals["output_tokens"]),
        cached_tokens=int(usage_totals["cached_tokens"]),
    )
    log_telemetry(
        {
            **ctx,
            "event": "turn_complete",
            "ok": not hit_limit,
            "hit_tool_round_limit": hit_limit,
            "final_text_chars": len(aligned_text),
            "usage_totals": dict(usage_totals),
            "latency_ms_by_round": list(latency_ms_rounds),
            "model_response_count": len(steps),
            "planner_cost_by_round_usd": [round(x, 6) for x in planner_round_cost_usd],
            "planner_estimated_cost_usd": round(float(tc_full["total_usd"]), 6),
            "cost_input_uncached_usd": round(float(tc_full["input_usd"]), 6),
            "cost_cached_input_usd": round(float(tc_full["cached_input_usd"]), 6),
            "cost_output_usd": round(float(tc_full["output_usd"]), 6),
            "pricing_table_matched": tc_full["pricing_table_matched"],
        }
    )
    return PlanningTurnDetail(
        final_text=aligned_text,
        last_response_id=response.id,
        tool_trace=tool_trace,
        steps=steps,
        hit_tool_round_limit=hit_limit,
        telemetry_cost={
            "planner_estimated_cost_usd": round(float(tc_full["total_usd"]), 6),
            "planner_cost_by_round_usd": [round(x, 6) for x in planner_round_cost_usd],
            "planner_usage_totals": dict(usage_totals),
            "pricing_note": "approximate public list prices; verify against billing",
        },
        usage_rounds=list(usage_rounds),
        pre_alignment_final_text=pre_alignment_final_text,
        clarification_alignment=align_report,
    )


def run_planning_turn(
    *,
    client: Any,
    model_id: str,
    instructions: str,
    tools: list[dict[str, Any]],
    corpus_path: Path,
    user_line: str,
    previous_response_id: str | None,
    dispatch_tool: Callable[[str, str], str],
    corpus_path_ref_index: dict[str, str] | None = None,
) -> PlanningTurnResult:
    """Run a single planning turn: user message → tool loop → final assistant text."""
    return run_planning_turn_detailed(
        client=client,
        model_id=model_id,
        instructions=instructions,
        tools=tools,
        corpus_path=corpus_path,
        user_line=user_line,
        previous_response_id=previous_response_id,
        dispatch_tool=dispatch_tool,
        corpus_path_ref_index=corpus_path_ref_index,
    ).as_turn_result()


def _generate_statblock_http(
    url: str,
    creature_name: str,
    description: str,
    challenge_rating: str | None,
    *,
    source_statblock_markdown: str | None = None,
    source_statblock_format: str = "markdown",
) -> tuple[str, None]:
    payload: dict[str, Any] = {
        "creature_name": creature_name,
        "description": description,
    }
    if challenge_rating:
        payload["challenge_rating"] = challenge_rating
    if source_statblock_markdown:
        payload["source_statblock_markdown"] = source_statblock_markdown
        payload["source_statblock_format"] = (
            "html" if str(source_statblock_format).lower() == "html" else "markdown"
        )
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    token = os.environ.get(_STATBLOCK_API_KEY_ENV, "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            ct = resp.headers.get("Content-Type", "") or ""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return (
            (
                f"Error: DungeonMind statblock request failed ({exc!s}). "
                f"Unset {_STATBLOCK_URL_ENV} to use the local Responses API fallback, or fix the URL."
            ),
            None,
        )

    if "json" in ct.lower():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip() or "(Empty JSON body from statblock service.)", None
        for key in ("statblock", "markdown", "text", "content", "body"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip(), None
        return raw.strip() or "(Statblock JSON had no known text field.)", None
    return raw.strip() or "(Empty response body from statblock service.)", None


def _generate_statblock_via_responses(
    client: Any,
    model: str,
    creature_name: str,
    description: str,
    challenge_rating: str | None,
    *,
    source_statblock_markdown: str | None = None,
    source_statblock_format: str = "markdown",
    source_statblock_relpath: str | None = None,
) -> tuple[str, dict[str, Any]]:
    api_client = DungeonMindApiClient.wrap(client)
    cr_line = f"Challenge rating hint: {challenge_rating}\n\n" if challenge_rating else ""
    fence_lang = "html" if str(source_statblock_format).lower() == "html" else "markdown"
    baseline = ""
    if source_statblock_markdown:
        baseline = (
            "### Existing statblock baseline (from corpus; revise or level from this)\n\n"
            f"```{fence_lang}\n{source_statblock_markdown}\n```\n\n"
        )
    user_content = (
        baseline
        + f"Creature name: {creature_name}\n\n{cr_line}"
        f"Description and design notes:\n{description}\n\n"
        "Produce the Markdown stat block."
    )
    st_ctx: dict[str, Any] = {"op": "statblock_via_responses", "creature_name": creature_name}
    if source_statblock_relpath:
        st_ctx["source_statblock_relpath"] = source_statblock_relpath
    if source_statblock_markdown:
        st_ctx["source_statblock_attach_chars"] = len(source_statblock_markdown)
    log_telemetry(
        {
            **st_ctx,
            "event": "request",
            "response_index": 0,
            "phase": "statblock_user",
            "model": model,
            "instructions_sig": text_sig(STATBLOCK_VIA_RESPONSES_SYSTEM),
            "user_message_sig": text_sig(user_content),
            "user_message_text": maybe_full_text(user_content),
        }
    )
    stat_call = api_client.responses_create(
        action="planner.statblock_fallback",
        model=model,
        instructions=STATBLOCK_VIA_RESPONSES_SYSTEM,
        input=[{"type": "message", "role": "user", "content": user_content}],
    )
    response = stat_call.response
    elapsed_ms = stat_call.elapsed_ms
    u_stat = usage_dict_from_response(response)
    c_stat = usage_cost_usd(
        model_id=model,
        input_tokens=u_stat["input_tokens"],
        output_tokens=u_stat["output_tokens"],
        cached_tokens=u_stat["cached_tokens"],
    )
    log_telemetry(
        {
            **st_ctx,
            "event": "response",
            "response_index": 0,
            "phase": "statblock_user",
            "latency_ms": round(elapsed_ms, 2),
            "response_id": str(getattr(response, "id", "")),
            "model": getattr(response, "model", None),
            "usage": u_stat,
            **_telemetry_cost_fields(model, u_stat),
            "output_text": maybe_full_text((getattr(response, "output_text", None) or "").strip()),
            "extras": response_extras(response),
        }
    )
    text = getattr(response, "output_text", "") or ""
    return text.strip() or "(Statblock model returned empty content.)", c_stat


def _generate_statblock_impl(
    client: Any,
    model: str,
    creature_name: str,
    description: str,
    challenge_rating: str | None,
    *,
    source_statblock_markdown: str | None = None,
    source_statblock_format: str = "markdown",
    source_statblock_relpath: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    url = os.environ.get(_STATBLOCK_URL_ENV, "").strip()
    if url:
        http_body, http_cost = _generate_statblock_http(
            url,
            creature_name,
            description,
            challenge_rating,
            source_statblock_markdown=source_statblock_markdown,
            source_statblock_format=source_statblock_format,
        )
        if http_body.startswith("Error: DungeonMind statblock request failed"):
            return _generate_statblock_via_responses(
                client,
                model,
                creature_name,
                description,
                challenge_rating,
                source_statblock_markdown=source_statblock_markdown,
                source_statblock_format=source_statblock_format,
                source_statblock_relpath=source_statblock_relpath,
            )
        return http_body, http_cost
    return _generate_statblock_via_responses(
        client,
        model,
        creature_name,
        description,
        challenge_rating,
        source_statblock_markdown=source_statblock_markdown,
        source_statblock_format=source_statblock_format,
        source_statblock_relpath=source_statblock_relpath,
    )


def _build_system_prompt(manifest: str, *, include_write_tools: bool = False) -> str:
    return build_corpus_session_planner_instructions(
        manifest,
        statblock_url_env_var=_STATBLOCK_URL_ENV,
        include_write_tools=include_write_tools,
    )


_ALLOW_WRITES_ENV = "DUNGEONMIND_PLANNER_ALLOW_WRITES"


def _env_allow_corpus_writes() -> bool:
    return os.environ.get(_ALLOW_WRITES_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def run_planning_session(
    corpus_dir: Path,
    model: str | None = None,
    *,
    stdin_lines: list[str] | None = None,
    allow_corpus_writes: bool | None = None,
) -> None:
    """
    Interactive planning REPL. If stdin_lines is set (tests), read prompts from it instead of input().
    """
    corpus_path = corpus_dir.resolve()
    if not corpus_path.is_dir():
        print(f"Error: corpus directory does not exist: {corpus_path}")
        return

    api_key = _load_api_key()
    if not api_key:
        print("Error: OPENAI_API_KEY is required for plan mode.")
        return

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("OpenAI SDK is required for plan mode.") from exc

    client = OpenAI(api_key=api_key)
    model_id = _resolve_planner_model(model)

    writes_on = (
        bool(allow_corpus_writes) if allow_corpus_writes is not None else _env_allow_corpus_writes()
    )
    manifest, ref_index = build_corpus_manifest_and_ref_index(corpus_path)
    system_prompt = _build_system_prompt(manifest, include_write_tools=writes_on)
    tools = _planner_tools_responses(include_write_tools=writes_on)
    dispatch_tool = make_tool_dispatcher(
        corpus_path,
        client,
        model_id,
        corpus_path_ref_index=ref_index,
        allow_corpus_writes=writes_on,
    )

    pending_input = list(stdin_lines or [])
    input_idx = 0

    def next_line(prompt: str) -> str:
        nonlocal input_idx
        if pending_input:
            if input_idx < len(pending_input):
                line = pending_input[input_idx]
                input_idx += 1
                print(f"{prompt}{line}")
                return line
            raise EOFError
        return input(prompt)

    print("Corpus-grounded planner (OpenAI Responses API). Type 'quit' or 'exit' to leave.")
    print(f"Corpus: {corpus_path}")
    print(f"Model: {model_id}")
    if writes_on:
        print(
            "Corpus writes: ENABLED (write_corpus_file + append_timeline_row registered; "
            "two-phase commit required, dossier/seed/statblock read-only)."
        )

    last_response_id: str | None = None

    while True:
        try:
            line = next_line("plan> ").strip()
        except EOFError:
            print()
            return
        except KeyboardInterrupt:
            print()
            return

        if not line:
            continue
        if line.lower() in {"quit", "exit"}:
            return

        turn = run_planning_turn(
            client=client,
            model_id=model_id,
            instructions=system_prompt,
            tools=tools,
            corpus_path=corpus_path,
            user_line=line,
            previous_response_id=last_response_id,
            dispatch_tool=dispatch_tool,
            corpus_path_ref_index=ref_index,
        )
        last_response_id = turn.last_response_id
        if turn.hit_tool_round_limit:
            print(
                f"Warning: stopped after {_MAX_TOOL_ROUNDS_PER_USER_TURN} tool rounds; "
                "reply may be incomplete."
            )
        if turn.final_text:
            print(turn.final_text)
        else:
            print("(No text content in model response.)")
