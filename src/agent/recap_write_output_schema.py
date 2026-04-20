"""Structured-output schema for the ``recap-write`` skill.

When ``active_skill_id="recap-write"``, the planner uses
:class:`src.agent.planner_skill_output_schema.planner_turn_with_recap_write_text_format`
so the API enforces ``recap_write_v1`` via Responses ``text.format`` (strict JSON
schema). The top-level ``recap_write`` field is the canonical payload.

Graders still use :func:`extract_recap_write_payload_loose` and
:func:`validate_recap_write_payload` as a paranoia check and for forensic replay
of older runs that embedded JSON in ``message``.
"""

from __future__ import annotations

import json
import re
from typing import Any

RECAP_WRITE_SCHEMA_VERSION = "recap_write_v1"

# ``json.loads`` accepts the body of any of these forms:
#   ```json\n{...}\n```
#   ```\n{...}\n```        (no language tag)
# We intentionally do **not** match plain ``{...}`` outside a code fence to avoid
# false positives from prose that happens to contain braces.
def _fence_lang_from_line(line: str) -> str | None:
    """Return language tag after opening backticks, or ``\"\"`` for bare `` ``` ``."""
    s = line.strip()
    if not s.startswith("```"):
        return None
    rest = s[3:].strip()
    return rest.lower() if rest else ""


def _balanced_json_object_from(s: str, start: int) -> str | None:
    """Return the substring from the first ``{`` at ``start`` through its matching
    ``}``, respecting strings and escapes — nested objects/arrays safe (unlike a
    regex with non-greedy ``.*?``).
    """
    if start < 0 or start >= len(s) or s[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    quote_char = ""
    for i in range(start, len(s)):
        ch = s[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_string = False
            continue
        if ch == '"':
            in_string = True
            quote_char = '"'
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None

_RECAP_PREVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "path": {
            "type": "string",
            "description": (
                "Corpus-relative path of the recap file the writer previewed; "
                "must end in ``Session Recaps/Session NN - <slug>.md``."
            ),
        },
        "mode": {
            "type": "string",
            "enum": ["create"],
            "description": "Only ``create`` is allowed for new recaps; this skill never appends.",
        },
        "confirm_token": {
            "type": "string",
            "minLength": 0,
            "description": (
                "Two-phase commit token returned by ``write_corpus_file`` in dry-run "
                "phase. Use empty string as a placeholder until after preview; paste "
                "the real token before final output. The grader does not validate "
                "the token's cryptographic contents."
            ),
        },
    },
    "required": ["path", "mode", "confirm_token"],
}

_DUPLICATE_PARAGRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source_lines": {
            "type": "array",
            "description": "Line numbers (1-indexed) where the duplicate paragraphs were found.",
            "items": {"type": "integer", "minimum": 1},
            "minItems": 2,
        },
        "paragraph_preview": {
            "type": "string",
            "description": "First 100–200 characters of the duplicated paragraph (truncate if longer).",
        },
        "recommended_action": {
            "type": "string",
            "enum": ["remove_later", "keep_both"],
            "description": (
                "``remove_later`` (default) means the recap preview already removed all "
                "but the first occurrence and is reporting the catch. ``keep_both`` is "
                "rare and means the duplicate looks intentional; the GM should confirm."
            ),
        },
    },
    "required": ["source_lines", "paragraph_preview", "recommended_action"],
}

_TIMELINE_APPEND_CANDIDATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "slug": {
            "type": "string",
            "description": "NPC slug folder name under ``<campaign>/NPCs/`` (snake_case).",
        },
        "hub_path": {
            "type": "string",
            "description": "Corpus-relative path to the NPC's existing hub folder (trailing slash).",
        },
        "reason": {
            "type": "string",
            "description": (
                "One-sentence rationale for proposing a timeline-row append. Consumed by "
                "the future ``recap-timeline-append`` skill, one slug per call."
            ),
        },
    },
    "required": ["slug", "hub_path", "reason"],
}

_NEW_HUB_PROPOSAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "proposed_slug": {
            "type": "string",
            "description": "Suggested NPC slug (snake_case).",
        },
        "campaign_or_setting": {
            "type": "string",
            "enum": ["campaign", "setting", "both"],
            "description": (
                "Where the hub should live. ``campaign`` is the default for first-appearance "
                "NPCs; escalate to ``both`` when the NPC clearly recurs across campaigns."
            ),
        },
        "proposed_location": {
            "type": "string",
            "description": (
                "Corpus-relative folder path for the proposed hub (e.g. "
                "``Longmont Campaign/Campaign 2/NPCs/marla_brambleback/``)."
            ),
        },
        "initial_files": {
            "type": "array",
            "description": "File basenames the new hub should contain on creation.",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "evidence_quote": {
            "type": "string",
            "description": "Short quote from the recap that motivates the hub proposal.",
        },
        "rationale": {
            "type": "string",
            "description": "One-sentence explanation of why this NPC is hub-worthy.",
        },
    },
    "required": [
        "proposed_slug",
        "campaign_or_setting",
        "proposed_location",
        "initial_files",
        "evidence_quote",
        "rationale",
    ],
}

_DISMISSED_NPC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {
            "type": "string",
            "description": "Name (or descriptor) of the NPC as referenced in the recap.",
        },
        "reason": {
            "type": "string",
            "description": "One-sentence explanation for not proposing a hub.",
        },
    },
    "required": ["name", "reason"],
}

_PLOT_ARTIFACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {
            "type": "string",
            "description": "Short name for the new in-world object or location.",
        },
        "evidence_quote": {
            "type": "string",
            "description": "Short quote from the recap that introduces the artifact.",
        },
        "proposed_locations": {
            "type": "array",
            "description": (
                "Two or three corpus-relative path candidates where this artifact could "
                "live. The GM picks; this skill does not commit them."
            ),
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
    },
    "required": ["name", "evidence_quote", "proposed_locations"],
}

_PREP_POINTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "prep_path": {
            "type": "string",
            "description": "Corpus-relative path to the discovered ``Session Prep/session_<N>_*.md`` file.",
        },
        "recap_path": {
            "type": "string",
            "description": "Corpus-relative path to the new recap (matches ``recap_preview.path``).",
        },
        "prep_append_line": {
            "type": "string",
            "description": "Proposed append line to add at the bottom of the prep doc (Markdown blockquote).",
        },
        "recap_append_line": {
            "type": "string",
            "description": "Proposed append line to add at the bottom of the recap (Markdown blockquote).",
        },
    },
    "required": ["prep_path", "recap_path", "prep_append_line", "recap_append_line"],
}

_NPC_AUDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "timeline_append_candidates": {
            "type": "array",
            "description": (
                "Existing-hub NPCs warranting a timeline row. Consumed one-at-a-time by "
                "the future ``recap-timeline-append`` skill."
            ),
            "items": _TIMELINE_APPEND_CANDIDATE_SCHEMA,
        },
        "new_hub_proposals": {
            "type": "array",
            "description": (
                "First-appearance, hub-worthy NPCs. Text-only proposal; no write tool "
                "covers new-hub creation today."
            ),
            "items": _NEW_HUB_PROPOSAL_SCHEMA,
        },
        "dismissed": {
            "type": "array",
            "description": (
                "Named NPCs explicitly considered and not proposed (audit trail). PCs "
                "are skipped silently and do not appear here."
            ),
            "items": _DISMISSED_NPC_SCHEMA,
        },
    },
    "required": ["timeline_append_candidates", "new_hub_proposals", "dismissed"],
}


def recap_write_output_json_schema() -> dict[str, Any]:
    """Full structured-payload schema for the ``recap-write`` skill.

    Embedded in :func:`src.agent.planner_skill_output_schema.planner_turn_with_recap_write_schema`
    as the ``recap_write`` property when the recap-write skill is active. Validation
    is grader-side via :func:`validate_recap_write_payload` and API-side via
    ``text.format`` when strict mode is on.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [RECAP_WRITE_SCHEMA_VERSION],
                "description": "Pinned to the current schema version; bump on breaking changes.",
            },
            "recap_preview": _RECAP_PREVIEW_SCHEMA,
            "duplicate_paragraphs": {
                "type": "array",
                "description": "Duplicate paragraphs caught during the mechanical pass; empty list if none.",
                "items": _DUPLICATE_PARAGRAPH_SCHEMA,
            },
            "npc_audit": _NPC_AUDIT_SCHEMA,
            "plot_artifacts": {
                "type": "array",
                "description": "Major new in-world objects with proposed placement candidates; empty list if none.",
                "items": _PLOT_ARTIFACT_SCHEMA,
            },
            "prep_pointer_proposal": {
                "anyOf": [_PREP_POINTER_SCHEMA, {"type": "null"}],
                "description": "Bidirectional prep ↔ recap pointer when a companion prep doc exists; ``null`` otherwise.",
            },
            "notes_for_gm": {
                "type": "string",
                "description": "Free-form caveats; empty string when no notes apply.",
            },
        },
        "required": [
            "schema_version",
            "recap_preview",
            "duplicate_paragraphs",
            "npc_audit",
            "plot_artifacts",
            "prep_pointer_proposal",
            "notes_for_gm",
        ],
    }


def _recap_payload_parse_score(obj: dict[str, Any]) -> int:
    """Heuristic: prefer the outer ``recap_write_v1`` object over nested dicts."""
    score = 0
    if obj.get("schema_version") == RECAP_WRITE_SCHEMA_VERSION:
        score += 100
    for k in ("recap_preview", "npc_audit", "plot_artifacts", "prep_pointer_proposal"):
        if k in obj:
            score += 2
    if "duplicate_paragraphs" in obj:
        score += 1
    return score


def _first_dict_in_fenced_chunk(chunk: str) -> dict[str, Any] | None:
    """Parse a JSON object dict from a fenced code block (best-effort).

    Model output sometimes includes many ``{`` positions; :func:`json.JSONDecoder.raw_decode`
    from an inner offset can return a nested object. We score candidates and keep the best.
    """
    s = chunk.strip()
    if not s:
        return None
    dec = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    brace_at = s.find("{")
    if brace_at >= 0:
        raw_bal = _balanced_json_object_from(s, brace_at)
        if raw_bal is not None:
            try:
                o = json.loads(raw_bal)
            except json.JSONDecodeError:
                pass
            else:
                if isinstance(o, dict):
                    candidates.append(o)
    try:
        o = json.loads(s)
    except json.JSONDecodeError:
        pass
    else:
        if isinstance(o, dict):
            candidates.append(o)
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            o, _ = dec.raw_decode(s, i)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            candidates.append(o)
    if not candidates:
        return None
    candidates.sort(key=_recap_payload_parse_score, reverse=True)
    return candidates[0]


def extract_recap_write_payload_loose(haystack: str) -> dict[str, Any] | None:
    """Try :func:`extract_recap_write_payload`, then scan for a top-level recap dict.

    Used by Scope-B grading when models nest or partially stringify JSON inside
    ``message`` so fenced-block parsing alone fails.

    When multiple objects declare ``schema_version: recap_write_v1``, prefers the
    **last** one in the haystack that passes :func:`validate_recap_write_payload`
    (models sometimes emit a truncated object before the full payload).
    """
    direct = extract_recap_write_payload(haystack)
    if direct is not None and direct.get("schema_version") == RECAP_WRITE_SCHEMA_VERSION:
        if not validate_recap_write_payload(direct):
            return direct
    dec = json.JSONDecoder()
    last_valid: dict[str, Any] | None = None
    for i, ch in enumerate(haystack):
        if ch != "{":
            continue
        try:
            o, _ = dec.raw_decode(haystack, i)
        except json.JSONDecodeError:
            continue
        if not isinstance(o, dict):
            continue
        if o.get("schema_version") != RECAP_WRITE_SCHEMA_VERSION:
            continue
        if validate_recap_write_payload(o):
            continue
        last_valid = o
    return last_valid


def extract_recap_write_payload(message_text: str) -> dict[str, Any] | None:
    """Pull the first fenced ```json``` block out of a planner ``message`` body.

    Returns the parsed object, or ``None`` if no fenced JSON object is present or the
    block is malformed. Graders should treat ``None`` as a hard skill-output failure;
    do not silently fall back to scanning prose.
    """
    if not message_text:
        return None
    lines = message_text.splitlines()
    i = 0
    while i < len(lines):
        lang = _fence_lang_from_line(lines[i])
        if lang is None:
            i += 1
            continue
        i += 1
        chunk_lines: list[str] = []
        while i < len(lines) and _fence_lang_from_line(lines[i]) is None:
            chunk_lines.append(lines[i])
            i += 1
        if i >= len(lines):
            return None
        i += 1  # closing ```
        if lang not in ("json", ""):
            continue
        chunk = "\n".join(chunk_lines)
        parsed = _first_dict_in_fenced_chunk(chunk)
        if parsed is not None:
            return parsed
    return None


def validate_recap_write_payload(payload: dict[str, Any]) -> list[str]:
    """Return a list of human-readable violations; empty list means structurally valid.

    Validation is intentionally lightweight (presence + type + enum + minItems) so the
    schema module has no third-party dependency. Graders can layer richer, scenario-
    specific assertions on top (e.g. ``recap_preview.path`` ends in the expected slug).
    """
    violations: list[str] = []

    def _err(msg: str) -> None:
        violations.append(msg)

    if not isinstance(payload, dict):
        return [f"payload must be a JSON object, got {type(payload).__name__}"]

    schema = recap_write_output_json_schema()
    required_top = schema["required"]
    for key in required_top:
        if key not in payload:
            _err(f"missing required top-level key: {key!r}")

    sv = payload.get("schema_version")
    if sv != RECAP_WRITE_SCHEMA_VERSION:
        _err(f"schema_version must be {RECAP_WRITE_SCHEMA_VERSION!r}, got {sv!r}")

    rp = payload.get("recap_preview")
    if isinstance(rp, dict):
        for k in _RECAP_PREVIEW_SCHEMA["required"]:
            if k not in rp:
                _err(f"recap_preview missing required key: {k!r}")
        if rp.get("mode") not in (None, "create"):
            _err(f"recap_preview.mode must be 'create', got {rp.get('mode')!r}")
    elif rp is not None:
        _err("recap_preview must be an object")

    dups = payload.get("duplicate_paragraphs")
    if not isinstance(dups, list):
        _err("duplicate_paragraphs must be a list (use [] when none)")
    else:
        for i, item in enumerate(dups):
            if not isinstance(item, dict):
                _err(f"duplicate_paragraphs[{i}] must be an object")
                continue
            for k in _DUPLICATE_PARAGRAPH_SCHEMA["required"]:
                if k not in item:
                    _err(f"duplicate_paragraphs[{i}] missing required key: {k!r}")
            sl = item.get("source_lines")
            if isinstance(sl, list) and len(sl) < 2:
                _err(f"duplicate_paragraphs[{i}].source_lines needs at least 2 entries")

    audit = payload.get("npc_audit")
    if isinstance(audit, dict):
        for k in _NPC_AUDIT_SCHEMA["required"]:
            if k not in audit:
                _err(f"npc_audit missing required key: {k!r}")
            elif not isinstance(audit.get(k), list):
                _err(f"npc_audit.{k} must be a list (use [] when none)")
    elif audit is not None:
        _err("npc_audit must be an object")

    pa = payload.get("plot_artifacts")
    if not isinstance(pa, list):
        _err("plot_artifacts must be a list (use [] when none)")
    else:
        for i, item in enumerate(pa):
            if not isinstance(item, dict):
                _err(f"plot_artifacts[{i}] must be an object")
                continue
            for k in _PLOT_ARTIFACT_SCHEMA["required"]:
                if k not in item:
                    _err(f"plot_artifacts[{i}] missing required key: {k!r}")
            locs = item.get("proposed_locations")
            if isinstance(locs, list) and len(locs) < 2:
                _err(f"plot_artifacts[{i}].proposed_locations needs at least 2 entries")

    pp = payload.get("prep_pointer_proposal")
    if pp is not None:
        if not isinstance(pp, dict):
            _err("prep_pointer_proposal must be an object or null")
        else:
            for k in _PREP_POINTER_SCHEMA["required"]:
                if k not in pp:
                    _err(f"prep_pointer_proposal missing required key: {k!r}")

    notes = payload.get("notes_for_gm")
    if not isinstance(notes, str):
        _err("notes_for_gm must be a string (use \"\" when no notes)")

    return violations
