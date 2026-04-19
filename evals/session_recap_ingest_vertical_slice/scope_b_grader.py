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
from src.agent.recap_context import RecapContext, RecapContextError, resolve_recap_context
from src.agent.recap_write_output_schema import (
    extract_recap_write_payload_loose,
    validate_recap_write_payload,
)

_PATH_TOOLS = frozenset({"read_corpus_file", "load_context_markdown"})
_WRITE_TOOLS = frozenset({"write_corpus_file"})


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


def _write_corpus_file_calls(
    tool_trace: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    """All ``write_corpus_file`` rows in trace order, paired with their (parsed) arguments."""
    out: list[tuple[int, dict[str, Any]]] = []
    for i, row in enumerate(tool_trace):
        if str(row.get("tool", "")) != "write_corpus_file":
            continue
        args = row.get("arguments")
        out.append((i, args if isinstance(args, dict) else {}))
    return out


def _dry_run_arg(args: dict[str, Any]) -> bool:
    """Mirror ``write_corpus_file``'s server-side ``dry_run`` default (``True`` when omitted)."""
    v = args.get("dry_run", True)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v)


def summarize_write_corpus_phases(
    write_calls: list[tuple[int, dict[str, Any]]],
) -> dict[str, Any]:
    """Structured summary of ``write_corpus_file`` calls' preview/commit shape.

    Returns ``{"calls": int, "previews": int, "commits": int, "phases": str}`` where
    ``phases`` is e.g. ``"preview"``, ``"preview→commit"``, ``"preview→preview"``,
    or ``"none"`` (no calls). Used both by the grader (decide pass/fail per the
    scenario's preview/commit knobs) and by the run report (surface the actual
    phase shape so cohort summaries can track commit rate without re-grading).
    """
    n = len(write_calls)
    if n == 0:
        return {"calls": 0, "previews": 0, "commits": 0, "phases": "none"}
    parts: list[str] = []
    previews = 0
    commits = 0
    for _i, args in write_calls:
        if _dry_run_arg(args):
            previews += 1
            parts.append("preview")
        else:
            commits += 1
            parts.append("commit")
    return {
        "calls": n,
        "previews": previews,
        "commits": commits,
        "phases": "→".join(parts),
    }


def _check_write_phases(
    write_calls: list[tuple[int, dict[str, Any]]],
    *,
    prefix: str,
    preview_required: bool,
    commit_required: bool,
) -> tuple[list[str], list[str]]:
    """Hard preview gate + optional commit gate for ``write_corpus_file``.

    Returns ``(hard_violations, soft_observations)``.

    - ``hard_violations`` go to the ``scope_b_tool`` bucket and fail the run.
      Always populated when ``preview_required`` is set and no preview call is
      observed, OR when ``commit_required`` is set and no commit is observed,
      OR when an out-of-order shape is seen (e.g. commit before any preview).

    - ``soft_observations`` are informational strings the harness can route into
      the run report's ``extras`` (e.g. "previewed but did not commit on this
      turn"). They do **not** fail the run — that distinction is the whole
      point of separating the gate from the metric: the production
      ``recap-write`` skill is human-in-the-loop and may legitimately stop at
      preview while still having satisfied the contract end-to-end across
      multiple operator turns.
    """
    hard: list[str] = []
    soft: list[str] = []

    if not write_calls:
        if preview_required:
            hard.append(
                f"{prefix} preview_required: write_corpus_file was never called; "
                f"the recap-write skill must at minimum surface a dry_run=true "
                f"preview with a confirm_token before any commit can happen."
            )
        return hard, soft

    previews = [(i, a) for i, a in write_calls if _dry_run_arg(a)]
    commits = [(i, a) for i, a in write_calls if not _dry_run_arg(a)]

    if preview_required and not previews:
        hard.append(
            f"{prefix} preview_required: no write_corpus_file preview "
            f"(dry_run=true) call found; saw {len(write_calls)} call(s) all "
            f"with dry_run=false. The skill contract is preview→approve→commit."
        )

    if commit_required:
        if not commits:
            hard.append(
                f"{prefix} commit_required: no write_corpus_file commit "
                f"(dry_run=false) call found; the model previewed but never "
                f"committed."
            )
        elif previews:
            first_idx, first_args = write_calls[0]
            last_idx, last_args = write_calls[-1]
            if not _dry_run_arg(first_args):
                hard.append(
                    f"{prefix} commit_required: first write_corpus_file at trace "
                    f"index {first_idx} has dry_run=false; preview must come first."
                )
            if _dry_run_arg(last_args):
                hard.append(
                    f"{prefix} commit_required: last write_corpus_file at trace "
                    f"index {last_idx} has dry_run=true; commit (dry_run=false) "
                    f"must follow the preview."
                )
    elif previews and not commits:
        soft.append(
            f"{prefix} commit_observed=false: the model produced "
            f"{len(previews)} preview call(s) but did not issue a "
            f"dry_run=false commit on this turn (HITL-by-design — informational, "
            f"not a failure)."
        )

    return hard, soft


def collect_scope_b_recap_ingest_violations(
    scenario: dict[str, Any],
    detail: PlanningTurnDetail,
    corpus_path: Path,
    *,
    precomputed_recap_context: RecapContext | None = None,
) -> dict[str, list[str]]:
    """Mechanical Scope-B gates on the planner's tool trace and final payload.

    When ``precomputed_recap_context`` is provided (the harness snapshotted
    :func:`resolve_recap_context` before any planner turn ran), the grader uses
    that frozen snapshot for the read-allowlist and ``target_session`` /
    ``campaign_id`` cross-checks instead of re-resolving against the post-commit
    corpus. This is required for multi-turn ingest scenarios: once turn 1
    commits ``Session N - Recap.md``, a fresh resolve at grade-time sees
    ``max(session) = N`` and returns ``target = N + 1`` with a recent-recaps
    window shifted forward by one — which would falsely flag the model's
    legitimate turn-1 reads as out-of-allowlist.
    """
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
        # Prefer the dedicated ``recap_write`` field emitted by the per-skill schema
        # (``planner_turn_output_recap_write``); fall back to fenced JSON inside
        # ``message`` for runs that used the universal envelope.
        payload: dict[str, Any] | None = None
        rw_field = json_obj.get("recap_write")
        if isinstance(rw_field, dict):
            payload = rw_field
        else:
            msg_raw = json_obj.get("message")
            msg = str(msg_raw) if msg_raw is not None else ""
            payload = extract_recap_write_payload_loose(
                msg
            ) or extract_recap_write_payload_loose(text)
        if payload is None:
            payload_v.append(
                f"{prefix} could not find a `recap_write_v1` object on the planner "
                f"reply (looked at `recap_write` field and a ```json fenced block in "
                f"`message`)."
            )
        else:
            for v in validate_recap_write_payload(payload):
                payload_v.append(f"{prefix} {v}")

    if precomputed_recap_context is not None:
        ctx = precomputed_recap_context
    else:
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

    expected_trace = scenario.get("expected_tool_trace") or {}
    legacy_two_phase = expected_trace.get("two_phase_commit_required")
    cfg_two_phase = cfg.get("two_phase_commit_required")
    expected_preview = expected_trace.get("preview_required")
    expected_commit = expected_trace.get("commit_required")
    cfg_preview = cfg.get("preview_required")
    cfg_commit = cfg.get("commit_required")

    preview_required: bool | None = None
    commit_required: bool | None = None
    if cfg_preview is not None:
        preview_required = bool(cfg_preview)
    elif expected_preview is not None:
        preview_required = bool(expected_preview)
    if cfg_commit is not None:
        commit_required = bool(cfg_commit)
    elif expected_commit is not None:
        commit_required = bool(expected_commit)

    if preview_required is None and commit_required is None:
        if cfg_two_phase is not None:
            two_phase = bool(cfg_two_phase)
        elif legacy_two_phase is not None:
            two_phase = bool(legacy_two_phase)
        else:
            two_phase = False
        preview_required = two_phase
        commit_required = two_phase
    else:
        if preview_required is None:
            preview_required = bool(commit_required)
        if commit_required is None:
            commit_required = False

    if preview_required or commit_required:
        write_calls = _write_corpus_file_calls(tool_trace)
        hard, _soft = _check_write_phases(
            write_calls,
            prefix=prefix,
            preview_required=preview_required,
            commit_required=commit_required,
        )
        tool_v.extend(hard)

    return _pack_scope_b_violations(tool_v, payload_v)


def collect_scope_b_recap_ingest_report_extras(
    scenario: dict[str, Any],
    detail: PlanningTurnDetail,
) -> dict[str, Any]:
    """Soft, informational signals for the run sidecar / cohort summary.

    These are intentionally **not** violations:

    * ``write_corpus_file_phases`` — structured ``{calls, previews, commits, phases}``
      (e.g. ``"preview→commit"``) so cohort aggregators can compute commit rate
      without re-grading.
    * ``write_corpus_file_soft_observations`` — strings emitted when the scenario
      did not require a commit but one was missing (HITL-by-design note).
      Empty when the run satisfied both gates or the scenario didn't ask for
      either knob.

    Always returns a dict (possibly empty); callers should attach to
    ``RecapIngestRunSummary.extras``.
    """
    if str(scenario.get("schema", "")) != "session_recap_ingest_scope_b_v1":
        return {}
    cfg = scenario.get("scope_b_grader") or {}
    if cfg.get("enabled") is False:
        return {}

    sid = fixture_scenario_id(scenario)
    prefix = _fail_prefix(sid)
    tool_trace = list(detail.tool_trace or [])
    write_calls = _write_corpus_file_calls(tool_trace)
    phases = summarize_write_corpus_phases(write_calls)

    expected_trace = scenario.get("expected_tool_trace") or {}
    legacy_two_phase = expected_trace.get("two_phase_commit_required")
    cfg_two_phase = cfg.get("two_phase_commit_required")
    expected_preview = expected_trace.get("preview_required")
    expected_commit = expected_trace.get("commit_required")
    cfg_preview = cfg.get("preview_required")
    cfg_commit = cfg.get("commit_required")
    preview_required = (
        bool(cfg_preview) if cfg_preview is not None
        else bool(expected_preview) if expected_preview is not None
        else (bool(cfg_two_phase) if cfg_two_phase is not None else bool(legacy_two_phase))
    )
    commit_required = (
        bool(cfg_commit) if cfg_commit is not None
        else bool(expected_commit) if expected_commit is not None
        else (bool(cfg_two_phase) if cfg_two_phase is not None else bool(legacy_two_phase))
    )

    _hard, soft = _check_write_phases(
        write_calls,
        prefix=prefix,
        preview_required=preview_required,
        commit_required=commit_required,
    )
    return {
        "write_corpus_file_phases": phases,
        "write_corpus_file_soft_observations": soft,
        "preview_required": preview_required,
        "commit_required": commit_required,
    }
