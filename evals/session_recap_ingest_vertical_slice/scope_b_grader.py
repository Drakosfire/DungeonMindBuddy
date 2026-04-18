"""Scope-B (Session 20 recap ingest) mechanical gates on planner output + tool trace.

When gold ``schema`` is ``session_recap_ingest_scope_b_v1``, step1 merges these
violations into :class:`evals.planner_slice.live_eval.LiveEvalResult`.

Violations are split into:

* ``scope_b_tool`` — ``get_recap_context`` shape, read allowlist, ``assemble_recap_draft``.
* ``scope_b_payload`` — planner envelope JSON and ``recap_write_v1`` extract/validate.

``scope_b`` is the concatenation of both (stable bucket for combined reporting).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evals.planner_slice.live_eval import (
    _norm_rel_path,
    _parse_final_json_object,
    fixture_scenario_id,
)
from src.agent.planner import PlanningTurnDetail
from src.agent.recap_context import RecapContextError, resolve_recap_context
from src.agent.recap_write_output_schema import (
    extract_recap_write_payload_loose,
    validate_recap_write_payload,
)

_PATH_TOOLS = frozenset({"read_corpus_file", "load_context_markdown"})


def _fail_prefix(sid: str) -> str:
    return f"[scope_b_grader:{sid}]"


def _pack_scope_b_violations(
    tool_v: list[str], payload_v: list[str]
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if tool_v:
        out["scope_b_tool"] = tool_v
    if payload_v:
        out["scope_b_payload"] = payload_v
    if tool_v or payload_v:
        out["scope_b"] = tool_v + payload_v
    return out


def _get_recap_context_calls(
    tool_trace: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    out: list[tuple[int, dict[str, Any]]] = []
    for i, row in enumerate(tool_trace):
        if str(row.get("tool", "")) == "get_recap_context":
            out.append((i, row))
    return out


def _assemble_recap_draft_calls(
    tool_trace: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    out: list[tuple[int, dict[str, Any]]] = []
    for i, row in enumerate(tool_trace):
        if str(row.get("tool", "")) == "assemble_recap_draft":
            out.append((i, row))
    return out


def _no_pin_get_recap_context_args(arguments: dict[str, Any]) -> bool:
    """True when the model did not pin ``campaign_id`` or ``target_session``."""
    cid = arguments.get("campaign_id")
    if cid is not None and str(cid).strip():
        return False
    ts = arguments.get("target_session")
    if ts is None:
        return True
    if isinstance(ts, str) and not str(ts).strip():
        return True
    return False


def _path_tools_after_index(
    tool_trace: list[dict[str, Any]], start_after: int
) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for i, row in enumerate(tool_trace):
        if i <= start_after:
            continue
        name = str(row.get("tool", ""))
        if name not in _PATH_TOOLS:
            continue
        args = row.get("arguments") or {}
        p = str(args.get("path", "")).strip()
        if p:
            found.append((i, p))
    return found


def collect_scope_b_recap_ingest_violations(
    scenario: dict[str, Any],
    detail: PlanningTurnDetail,
    corpus_path: Path,
) -> dict[str, list[str]]:
    if str(scenario.get("schema", "")) != "session_recap_ingest_scope_b_v1":
        return {}
    sid = fixture_scenario_id(scenario)
    prefix = _fail_prefix(sid)
    cfg = scenario.get("scope_b_grader") or {}
    if cfg.get("enabled") is False:
        return {}

    tool_v: list[str] = []
    payload_v: list[str] = []
    tool_trace = list(detail.tool_trace or [])

    ctx_calls = _get_recap_context_calls(tool_trace)
    if len(ctx_calls) != 1:
        tool_v.append(
            f"{prefix} get_recap_context must be called exactly once with no pinned "
            f"arguments; saw {len(ctx_calls)} call(s)."
        )
    else:
        _idx, row = ctx_calls[0]
        args = row.get("arguments") or {}
        if not isinstance(args, dict):
            tool_v.append(f"{prefix} get_recap_context arguments must be an object.")
        elif not _no_pin_get_recap_context_args(args):
            tool_v.append(
                f"{prefix} get_recap_context must be called with no arguments "
                f"(do not pin campaign_id or target_session for this scenario); "
                f"got arguments={args!r}."
            )

    text = detail.final_text or ""
    json_obj, json_err = _parse_final_json_object(text)
    if json_err:
        payload_v.append(f"{prefix} planner final output is not valid JSON: {json_err}")
    elif json_obj is None:
        payload_v.append(f"{prefix} planner final output must be a JSON object.")
    else:
        msg_raw = json_obj.get("message")
        msg = str(msg_raw) if msg_raw is not None else ""
        payload = extract_recap_write_payload_loose(msg) or extract_recap_write_payload_loose(
            text
        )
        if payload is None:
            payload_v.append(
                f"{prefix} could not extract a `recap_write_v1` object from `message` "
                f"(try a ```json fenced block or valid JSON with schema_version "
                f"recap_write_v1)."
            )
        else:
            for v in validate_recap_write_payload(payload):
                payload_v.append(f"{prefix} {v}")

    try:
        ctx = resolve_recap_context(corpus_path.resolve())
    except RecapContextError as exc:
        tool_v.append(f"{prefix} cannot resolve recap context for read allowlist: {exc}")
        return _pack_scope_b_violations(tool_v, payload_v)

    allowed: set[str] = set()
    for entry in ctx.recent_recaps:
        allowed.add(_norm_rel_path(entry.path))
    if ctx.prep_doc_path:
        allowed.add(_norm_rel_path(ctx.prep_doc_path))
    for extra in cfg.get("read_allowlist_extra") or []:
        if str(extra).strip():
            allowed.add(_norm_rel_path(str(extra)))

    ctx_idx = ctx_calls[0][0] if len(ctx_calls) == 1 else -1
    if ctx_idx >= 0:
        for i, p in _path_tools_after_index(tool_trace, ctx_idx):
            n = _norm_rel_path(p)
            if n not in allowed:
                tool_v.append(
                    f"{prefix} after get_recap_context, {tool_trace[i].get('tool')} path "
                    f"{p!r} is not in recent_recaps ∪ prep_doc_path "
                    f"(normalized {n!r} not in allowlist)."
                )

    if cfg.get("require_assemble_recap_draft", True):
        draft_calls = _assemble_recap_draft_calls(tool_trace)
        if len(draft_calls) != 1:
            tool_v.append(
                f"{prefix} assemble_recap_draft must be called exactly once; "
                f"saw {len(draft_calls)} call(s)."
            )
        else:
            _didx, drow = draft_calls[0]
            dargs = drow.get("arguments") or {}
            if not isinstance(dargs, dict):
                tool_v.append(f"{prefix} assemble_recap_draft arguments must be an object.")
            else:
                raw_path = str(dargs.get("raw_notes_path", "")).strip()
                ing_rel = str(
                    scenario.get("ingest_raw_notes_relpath")
                    or "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
                ).strip()
                if _norm_rel_path(raw_path) != _norm_rel_path(ing_rel):
                    tool_v.append(
                        f"{prefix} assemble_recap_draft.raw_notes_path want "
                        f"{ing_rel!r} got {raw_path!r}."
                    )
                ts_arg = dargs.get("target_session")
                try:
                    ts_int = int(ts_arg)
                except (TypeError, ValueError):
                    tool_v.append(
                        f"{prefix} assemble_recap_draft.target_session must be int "
                        f"synced with get_recap_context; got {ts_arg!r}."
                    )
                else:
                    if ts_int != ctx.target_session:
                        tool_v.append(
                            f"{prefix} assemble_recap_draft.target_session want "
                            f"{ctx.target_session} got {ts_int}."
                        )
                cid_arg = str(dargs.get("campaign_id", "")).strip()
                if cid_arg != str(ctx.campaign_id).strip():
                    tool_v.append(
                        f"{prefix} assemble_recap_draft.campaign_id want "
                        f"{ctx.campaign_id!r} got {cid_arg!r}."
                    )

    return _pack_scope_b_violations(tool_v, payload_v)
