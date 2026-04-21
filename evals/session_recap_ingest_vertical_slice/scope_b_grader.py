"""Scope-B (Session 20 recap ingest) mechanical gates on planner output + tool trace.

When gold ``schema`` is ``session_recap_ingest_scope_b_v1``, step1 merges these
violations into :class:`evals.planner_slice.live_eval.LiveEvalResult`.

Violations are split into:

* ``scope_b_tool`` — ``get_recap_context`` shape, read allowlist, ``assemble_recap_draft``,
  optional ``build_recap_write_payload`` (when ``require_build_recap_write_payload``).
* ``scope_b_payload`` — planner envelope JSON and ``recap_write_v1`` extract/validate.
* ``scope_b_unsure_queue`` — top-level ``unsure_queue`` items when the scenario opts in.
* ``scope_b_findings`` — findings/GM-notes substring checks when the scenario opts in.

``scope_b`` is the concatenation of both (stable bucket for combined reporting).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.planner_slice.live_eval import (
    _norm_rel_path,
    _parse_final_json_object,
    fixture_scenario_id,
)
from src.agent.planner import PlanningTurnDetail
from src.agent.recap_context import RecapContext, RecapContextError, resolve_recap_context
from src.agent.recap_ingest_helpers import assemble_recap
from src.agent.recap_write_mechanical_payload import (
    build_recap_write_payload_from_ingest,
)
from src.agent.recap_write_output_schema import (
    extract_recap_write_payload_loose,
    validate_recap_write_payload,
)
from evals.session_recap_ingest_vertical_slice.step3_unsure_queue_grading import (
    grade_unsure_queue,
)

_DEFAULT_INGEST_RAW_NOTES_RELPATH = (
    "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
)
_GOLD_DIR = Path(__file__).resolve().parent / "gold"
# Module-local default (kept in sync with ``gold/scope_b_session_20.json`` and
# the duplicate literal in ``step1_recap_ingest_run.py``). Hoisting the runner
# copy to import this is BACKLOG §2.6 — out of scope here.

_PATH_TOOLS = frozenset({"read_corpus_file", "load_context_markdown"})
_WRITE_TOOLS = frozenset({"write_corpus_file"})

# ``planner_skill_dispatch_guards._wrap_recap_write`` returns this prefix when a
# read path is outside the recap-write allowlist (no file bytes are returned).
_RECAP_WRITE_GUARD_BLOCKED_READ_PREFIX = "Error: recap-write skill blocked"


def _fail_prefix(sid: str) -> str:
    return f"[scope_b_grader:{sid}]"


def _pack_scope_b_violations(
    tool_v: list[str],
    payload_v: list[str],
    unsure_v: list[str] | None = None,
    findings_v: list[str] | None = None,
) -> dict[str, list[str]]:
    unsure_v = unsure_v or []
    findings_v = findings_v or []
    out: dict[str, list[str]] = {}
    if tool_v:
        out["scope_b_tool"] = tool_v
    if payload_v:
        out["scope_b_payload"] = payload_v
    if unsure_v:
        out["scope_b_unsure_queue"] = unsure_v
    if findings_v:
        out["scope_b_findings"] = findings_v
    if tool_v or payload_v or unsure_v or findings_v:
        out["scope_b"] = tool_v + payload_v + unsure_v + findings_v
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


def _build_recap_write_payload_calls(
    tool_trace: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    out: list[tuple[int, dict[str, Any]]] = []
    for i, row in enumerate(tool_trace):
        if str(row.get("tool", "")) == "build_recap_write_payload":
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


def _guard_blocked_recap_write_read(excerpt: Any) -> bool:
    """True when ``output_excerpt`` is the recap-write dispatch guard refusal string."""
    if not isinstance(excerpt, str) or not excerpt:
        return False
    return excerpt.lstrip().startswith(_RECAP_WRITE_GUARD_BLOCKED_READ_PREFIX)


def _assemble_recap_draft_indices(tool_trace: list[dict[str, Any]]) -> list[int]:
    return [
        i
        for i, row in enumerate(tool_trace)
        if str(row.get("tool", "")) == "assemble_recap_draft"
    ]


def _read_allowlist_hard_and_soft(
    tool_trace: list[dict[str, Any]],
    *,
    ctx_idx: int,
    allowed: set[str],
    prefix: str,
) -> tuple[list[str], list[str]]:
    """Split out-of-allowlist path-tool rows into hard failures vs soft observations.

    When the dispatch guard blocked the read (plain ``Error: recap-write …``),
    bytes never reached the model — matching :func:`_wrap_recap_write`. If the
    trace later includes ``assemble_recap_draft``, treat as recoverable soft
    signal; otherwise the model never resolved the workflow → hard violation.

    When the response was not a guard refusal (real file JSON, missing excerpt,
    …), keep the historical hard violation — unguarded reads may have leaked
    staging content into downstream reasoning.
    """
    hard: list[str] = []
    soft: list[str] = []
    if ctx_idx < 0:
        return hard, soft

    assemble_idxs = _assemble_recap_draft_indices(tool_trace)

    for i, p in _path_tools_after_index(tool_trace, ctx_idx):
        n = _norm_rel_path(p)
        if n in allowed:
            continue
        row = tool_trace[i] if i < len(tool_trace) else {}
        excerpt = row.get("output_excerpt") if isinstance(row, dict) else None
        tool_name = str(row.get("tool", "")) if isinstance(row, dict) else ""

        if _guard_blocked_recap_write_read(excerpt):
            recovered = any(j > i for j in assemble_idxs)
            if recovered:
                soft.append(
                    f"{prefix} read_allowlist_soft: {tool_name} path {p!r} was blocked "
                    f"by recap-write dispatch guard (output starts with "
                    f"{_RECAP_WRITE_GUARD_BLOCKED_READ_PREFIX!r}); model recovered with "
                    f"a later assemble_recap_draft."
                )
            else:
                hard.append(
                    f"{prefix} after get_recap_context, {tool_name} path {p!r} was "
                    f"blocked by recap-write dispatch guard but no assemble_recap_draft "
                    f"followed — model did not recover."
                )
        else:
            hard.append(
                f"{prefix} after get_recap_context, {tool_name} path "
                f"{p!r} is not in recent_recaps ∪ prep_doc_path "
                f"(normalized {n!r} not in allowlist)."
            )

    return hard, soft


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


def _write_corpus_file_rows(
    tool_trace: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    """All ``write_corpus_file`` rows in trace order as ``(idx, args, row)`` triples.

    Sibling of :func:`_write_corpus_file_calls` that also yields the full trace
    row so callers can read ``output_excerpt`` (the server's JSON response).
    Used by the commit-success gate (BACKLOG §1.0 fix): the call-shape view is
    not enough to know whether the write actually landed.
    """
    out: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for i, row in enumerate(tool_trace):
        if str(row.get("tool", "")) != "write_corpus_file":
            continue
        args = row.get("arguments")
        out.append((i, args if isinstance(args, dict) else {}, row))
    return out


def _parse_tool_response_excerpt(excerpt: Any) -> dict[str, Any] | None:
    """Best-effort JSON parse of a tool row's ``output_excerpt``.

    Returns ``None`` when the excerpt is missing, isn't a JSON object, or is
    truncated mid-token. Skill-guard / disabled-writes responses are plain
    ``"Error: ..."`` strings (not JSON) and intentionally return ``None`` here;
    callers must handle that case separately (see :func:`_commit_outcome`).
    """
    if not isinstance(excerpt, str) or not excerpt:
        return None
    try:
        obj = json.loads(excerpt)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def _commit_outcome(row: dict[str, Any]) -> dict[str, Any]:
    """Inspect a ``write_corpus_file`` commit row's server response.

    Closes the BACKLOG §1.0 gate hole: the previous gate checked only call
    shape (``dry_run=false`` row exists) and silently passed when the server
    refused the write (stale ``confirm_token``, allowlist rejection, disabled
    writes, ...).

    Returns a stable shape::

        {
            "succeeded": True | False | None,  # None == response unparseable
            "phase": "committed" | "preview" | None,
            "error": str | None,               # server-reported error, if any
        }

    Decision table for ``succeeded``:

    * Plain ``"Error: ..."`` string (skill guard / disabled writes / unknown
      tool) → ``False`` (we know the corpus was not written).
    * JSON ``{"ok": true, "phase": "committed", ...}`` → ``True``.
    * JSON ``{"ok": false, "error": ...}`` → ``False``; ``error`` populated.
    * Anything else (truncated JSON, ``ok`` missing, unexpected ``phase``) →
      ``None`` so callers don't punish ambiguous traces.
    """
    excerpt = row.get("output_excerpt") if isinstance(row, dict) else None
    if isinstance(excerpt, str) and excerpt.lstrip().startswith("Error:"):
        return {"succeeded": False, "phase": None, "error": excerpt.strip()}

    obj = _parse_tool_response_excerpt(excerpt)
    if obj is None:
        return {"succeeded": None, "phase": None, "error": None}

    ok = obj.get("ok")
    phase_raw = obj.get("phase")
    phase = phase_raw if isinstance(phase_raw, str) else None
    err_raw = obj.get("error")
    err = err_raw if isinstance(err_raw, str) else None

    if ok is True and phase == "committed":
        return {"succeeded": True, "phase": phase, "error": None}
    if ok is False:
        return {"succeeded": False, "phase": phase, "error": err or ""}
    return {"succeeded": None, "phase": phase, "error": err}


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
    write_rows: list[tuple[int, dict[str, Any], dict[str, Any]]],
    *,
    prefix: str,
    preview_required: bool,
    commit_required: bool,
) -> tuple[list[str], list[str]]:
    """Hard preview gate + optional commit gate for ``write_corpus_file``.

    Accepts ``(idx, args, row)`` triples (see :func:`_write_corpus_file_rows`)
    so the gate can inspect the server's response, not just the call shape.
    Closing this gap is BACKLOG §1.0: previously a stale ``confirm_token``
    rejection (or any other server refusal) on the final ``dry_run=false`` call
    silently satisfied ``commit_required`` because we only counted that the
    call existed.

    Returns ``(hard_violations, soft_observations)``.

    - ``hard_violations`` go to the ``scope_b_tool`` bucket and fail the run.
      Populated when ``preview_required`` is set and no preview call is
      observed; when ``commit_required`` is set and no commit is observed;
      when an out-of-order shape is seen (e.g. commit before any preview);
      when ``commit_required`` is set and the last commit attempt's server
      response was ``ok=false`` (or a plain ``Error: ...`` string); or when
      ``commit_required`` is set and the last commit attempt's server
      response was unparseable (truncated, non-JSON, or unexpected shape) —
      because the protocol's success cannot be verified in that case.

    - ``soft_observations`` are informational strings the harness can route into
      the run report's ``extras`` (e.g. "previewed but did not commit on this
      turn"). They do **not** fail the run — that distinction is the whole
      point of separating the gate from the metric: the production
      ``recap-write`` skill is human-in-the-loop and may legitimately stop at
      preview while still having satisfied the contract end-to-end across
      multiple operator turns. When ``commit_required`` is **not** set, an
      unparseable response on a voluntarily-issued commit is not a hard
      violation and is left for cohort summaries to flag.
    """
    hard: list[str] = []
    soft: list[str] = []

    if not write_rows:
        if preview_required:
            hard.append(
                f"{prefix} preview_required: write_corpus_file was never called; "
                f"the recap-write skill must at minimum surface a dry_run=true "
                f"preview with a confirm_token before any commit can happen."
            )
        return hard, soft

    previews = [(i, a, r) for i, a, r in write_rows if _dry_run_arg(a)]
    commits = [(i, a, r) for i, a, r in write_rows if not _dry_run_arg(a)]

    if preview_required and not previews:
        hard.append(
            f"{prefix} preview_required: no write_corpus_file preview "
            f"(dry_run=true) call found; saw {len(write_rows)} call(s) all "
            f"with dry_run=false. The skill contract is preview→approve→commit."
        )

    if commit_required:
        if not commits:
            hard.append(
                f"{prefix} commit_required: no write_corpus_file commit "
                f"(dry_run=false) call found; the model previewed but never "
                f"committed."
            )
        else:
            if previews:
                first_idx, first_args, _first_row = write_rows[0]
                last_idx, last_args, _last_row = write_rows[-1]
                if not _dry_run_arg(first_args):
                    hard.append(
                        f"{prefix} commit_required: first write_corpus_file at "
                        f"trace index {first_idx} has dry_run=false; preview "
                        f"must come first."
                    )
                if _dry_run_arg(last_args):
                    hard.append(
                        f"{prefix} commit_required: last write_corpus_file at "
                        f"trace index {last_idx} has dry_run=true; commit "
                        f"(dry_run=false) must follow the preview."
                    )
            # Commit-success gate: the last commit attempt must report
            # ok=true, phase="committed". Earlier failed attempts are tolerated
            # (a model may legitimately retry after a stale-token rejection),
            # but the last attempt is the one that decides whether the corpus
            # got written.
            last_commit_idx, _last_commit_args, last_commit_row = commits[-1]
            outcome = _commit_outcome(last_commit_row)
            if outcome["succeeded"] is False:
                err_text = (outcome.get("error") or "").strip()
                err_suffix = f" Server response: {err_text!r}." if err_text else ""
                hard.append(
                    f"{prefix} commit_required: last write_corpus_file commit "
                    f"at trace index {last_commit_idx} did not succeed "
                    f"(server returned ok=false / Error response).{err_suffix} "
                    f"The two-phase contract requires the final dry_run=false "
                    f"call to land bytes; a refused commit means nothing was "
                    f"written."
                )
            elif outcome["succeeded"] is None:
                hard.append(
                    f"{prefix} commit_outcome=unknown: _commit_outcome could not "
                    f"parse the server response for the last write_corpus_file "
                    f"commit at trace index {last_commit_idx} (truncated, non-JSON, "
                    f"or unexpected shape). Failing this run because commit_required "
                    f"is true and the protocol's success cannot be verified — not "
                    f"because the protocol is known to have failed."
                )
    elif previews and not commits:
        soft.append(
            f"{prefix} commit_observed=false: the model produced "
            f"{len(previews)} preview call(s) but did not issue a "
            f"dry_run=false commit on this turn (HITL-by-design — informational, "
            f"not a failure)."
        )

    return hard, soft


def _read_allowlist_set(ctx: RecapContext, scenario: dict[str, Any]) -> set[str]:
    """Normalized paths the recap-ingest grader treats as readable after ``get_recap_context``."""
    cfg = scenario.get("scope_b_grader") or {}
    allowed: set[str] = set()
    for entry in ctx.recent_recaps:
        allowed.add(_norm_rel_path(entry.path))
    if ctx.prep_doc_path:
        allowed.add(_norm_rel_path(ctx.prep_doc_path))
    for extra in cfg.get("read_allowlist_extra") or []:
        if str(extra).strip():
            allowed.add(_norm_rel_path(str(extra)))
    return allowed


def _resolve_write_phase_knobs(scenario: dict[str, Any]) -> tuple[bool, bool]:
    """Single source of truth for ``preview_required`` / ``commit_required``.

    Mirrors the logic used for hard gates in
    :func:`collect_scope_b_recap_ingest_violations` so cohort report extras
    (``collect_scope_b_recap_ingest_report_extras``) never disagree with the
    grader on asymmetric scenarios (e.g. ``commit_required`` only implies
    ``preview_required``).
    """
    cfg = scenario.get("scope_b_grader") or {}
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

    assert preview_required is not None and commit_required is not None
    return preview_required, commit_required


def _check_unsure_queue(json_obj: dict[str, Any], *, prefix: str, required: bool) -> list[str]:
    if not required:
        return []
    raw_items = json_obj.get("unsure_queue") or []
    items = raw_items if isinstance(raw_items, list) else []
    ok, violations = grade_unsure_queue(items)
    if ok:
        return []
    return [f"{prefix} scope_b_unsure_queue: {v}" for v in violations]


def _findings_surface_parts(payload: dict[str, Any] | None, json_obj: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    if isinstance(payload, dict):
        notes = payload.get("notes_for_gm")
        if notes is not None:
            parts.append(str(notes))
        findings = payload.get("findings")
        if findings is not None:
            parts.append(
                findings
                if isinstance(findings, str)
                else json.dumps(findings, ensure_ascii=False, sort_keys=True)
            )
    message = json_obj.get("message")
    if message is not None:
        parts.append(str(message))
    top_findings = json_obj.get("findings")
    if top_findings is not None:
        parts.append(
            top_findings
            if isinstance(top_findings, str)
            else json.dumps(top_findings, ensure_ascii=False, sort_keys=True)
        )
    return [part for part in parts if part]


def _check_findings(
    json_obj: dict[str, Any],
    payload: dict[str, Any] | None,
    *,
    prefix: str,
    required: bool,
) -> list[str]:
    if not required:
        return []
    gold = json.loads(
        (_GOLD_DIR / "scope_b_session_20_findings.json").read_text(encoding="utf-8")
    )
    needles = [
        str(v) for v in (gold.get("must_substring_any") or []) if str(v).strip()
    ]
    surface = "\n".join(_findings_surface_parts(payload, json_obj)).lower()
    if any(needle.lower() in surface for needle in needles):
        return []
    return [
        f"{prefix} scope_b_findings: findings surface contains none of "
        f"must_substring_any={needles!r}"
    ]


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
    payload: dict[str, Any] | None = None
    unsure_v: list[str] = []
    findings_v: list[str] = []
    if json_err:
        payload_v.append(f"{prefix} planner final output is not valid JSON: {json_err}")
    elif json_obj is None:
        payload_v.append(f"{prefix} planner final output must be a JSON object.")
    else:
        # Prefer the dedicated ``recap_write`` field emitted by the per-skill schema
        # (``planner_turn_output_recap_write``); fall back to fenced JSON inside
        # ``message`` for runs that used the universal envelope.
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
        unsure_v = _check_unsure_queue(
            json_obj,
            prefix=prefix,
            required=cfg.get("require_unsure_queue") is True,
        )
        findings_v = _check_findings(
            json_obj,
            payload,
            prefix=prefix,
            required=cfg.get("require_findings") is True,
        )
        if unsure_v:
            payload_v.extend(unsure_v)
        if findings_v:
            payload_v.extend(findings_v)

    if precomputed_recap_context is not None:
        ctx = precomputed_recap_context
    else:
        try:
            ctx = resolve_recap_context(corpus_path.resolve())
        except RecapContextError as exc:
            tool_v.append(f"{prefix} cannot resolve recap context for read allowlist: {exc}")
            return _pack_scope_b_violations(tool_v, payload_v, unsure_v, findings_v)

    allowed = _read_allowlist_set(ctx, scenario)

    ctx_idx = ctx_calls[0][0] if len(ctx_calls) == 1 else -1
    read_hard, _ = _read_allowlist_hard_and_soft(
        tool_trace,
        ctx_idx=ctx_idx,
        allowed=allowed,
        prefix=prefix,
    )
    tool_v.extend(read_hard)

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
                    or _DEFAULT_INGEST_RAW_NOTES_RELPATH
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

    if cfg.get("require_build_recap_write_payload", False):
        bp_calls = _build_recap_write_payload_calls(tool_trace)
        if len(bp_calls) != 1:
            tool_v.append(
                f"{prefix} build_recap_write_payload must be called exactly once; "
                f"saw {len(bp_calls)} call(s)."
            )
        else:
            _bidx, brow = bp_calls[0]
            bargs = brow.get("arguments") or {}
            if not isinstance(bargs, dict):
                tool_v.append(
                    f"{prefix} build_recap_write_payload arguments must be an object."
                )
            else:
                raw_path = str(bargs.get("raw_notes_path", "")).strip()
                ing_rel = str(
                    scenario.get("ingest_raw_notes_relpath")
                    or _DEFAULT_INGEST_RAW_NOTES_RELPATH
                ).strip()
                if _norm_rel_path(raw_path) != _norm_rel_path(ing_rel):
                    tool_v.append(
                        f"{prefix} build_recap_write_payload.raw_notes_path want "
                        f"{ing_rel!r} got {raw_path!r}."
                    )
                ts_arg = bargs.get("target_session")
                try:
                    ts_int = int(ts_arg)
                except (TypeError, ValueError):
                    tool_v.append(
                        f"{prefix} build_recap_write_payload.target_session must be int "
                        f"synced with get_recap_context; got {ts_arg!r}."
                    )
                else:
                    if ts_int != ctx.target_session:
                        tool_v.append(
                            f"{prefix} build_recap_write_payload.target_session want "
                            f"{ctx.target_session} got {ts_int}."
                        )
                cid_arg = str(bargs.get("campaign_id", "")).strip()
                if cid_arg != str(ctx.campaign_id).strip():
                    tool_v.append(
                        f"{prefix} build_recap_write_payload.campaign_id want "
                        f"{ctx.campaign_id!r} got {cid_arg!r}."
                    )

    preview_required, commit_required = _resolve_write_phase_knobs(scenario)

    if preview_required or commit_required:
        write_rows = _write_corpus_file_rows(tool_trace)
        hard, _soft = _check_write_phases(
            write_rows,
            prefix=prefix,
            preview_required=preview_required,
            commit_required=commit_required,
        )
        tool_v.extend(hard)

    return _pack_scope_b_violations(tool_v, payload_v, unsure_v, findings_v)


# --- Mechanical-payload comparison helpers (BACKLOG §1.5 / option (b)) -------
#
# These compute the *expected* mechanical fields of ``recap_write_v1`` from the
# same inputs ``build_recap_write_payload`` would consume (raw notes + recap
# context snapshot), and compare them to whatever the model actually emitted.
# The comparison runs **whether or not** the model invoked the tool — so cohort
# data can answer "does invoking ``build_recap_write_payload`` reduce mechanical
# field variance vs. hand-authoring?" without flipping any hard gate first.
#
# The result is a soft signal (``mechanical_fields_match`` ∈ {True, False, None})
# in the per-run extras; the cohort aggregator stratifies by
# ``build_recap_write_payload_called``. ``None`` means "not applicable" — either
# the scenario doesn't carry the inputs we need (no ``corpus_path`` /
# ``recap_context_snapshot``), or the model's final payload is unparseable
# (which the hard payload gate already flags separately).


_MECHANICAL_FIELDS: tuple[str, ...] = (
    "recap_preview",
    "duplicate_paragraphs",
    "prep_pointer_proposal",
)

# ``recap_preview.confirm_token`` is intentionally **not** mechanical: the helper
# returns ``""`` as a placeholder, and the model copies the real token in after
# ``write_corpus_file`` dry_run. Comparing it would flip every well-behaved run
# to "mismatch." Strip it from both sides before comparing the recap_preview dict.
_RECAP_PREVIEW_MECHANICAL_KEYS: frozenset[str] = frozenset({"path", "mode"})


def _extract_recap_write_from_final_text(text: str) -> dict[str, Any] | None:
    """Best-effort extract of ``recap_write`` from the planner's final text.

    Mirrors the lookup order in :func:`collect_scope_b_recap_ingest_violations`:
    prefer the dedicated top-level ``recap_write`` field (per-skill schema),
    fall back to a ```json fenced block in ``message`` for legacy envelopes.
    Returns ``None`` if neither path yields a parseable dict.
    """
    json_obj, _ = _parse_final_json_object(text or "")
    if isinstance(json_obj, dict):
        rw_field = json_obj.get("recap_write")
        if isinstance(rw_field, dict):
            return rw_field
        msg_raw = json_obj.get("message")
        msg = str(msg_raw) if msg_raw is not None else ""
        loose = extract_recap_write_payload_loose(msg)
        if isinstance(loose, dict):
            return loose
    loose_full = extract_recap_write_payload_loose(text or "")
    return loose_full if isinstance(loose_full, dict) else None


def _compute_expected_mechanical_payload(
    scenario: dict[str, Any],
    ctx: RecapContext,
    corpus_path: Path,
) -> dict[str, Any] | None:
    """Build the mechanical ``recap_write_v1`` payload the helper *would* return.

    Reads raw notes from ``scenario["ingest_raw_notes_relpath"]`` (or the
    module default), runs :func:`assemble_recap` to get an ``IngestReport``,
    and feeds both into :func:`build_recap_write_payload_from_ingest`. Returns
    ``None`` on any IO / arg error so the caller can degrade to "not applicable"
    rather than fail the soft signal.
    """
    rel = str(
        scenario.get("ingest_raw_notes_relpath")
        or _DEFAULT_INGEST_RAW_NOTES_RELPATH
    ).strip()
    if not rel:
        return None
    notes_path = (corpus_path / rel).resolve()
    try:
        raw_text = notes_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        _full, report = assemble_recap(
            raw_notes=raw_text,
            session=int(ctx.target_session),
            campaign_id=str(ctx.campaign_id),
            remove_duplicates=True,
        )
    except (TypeError, ValueError):
        return None
    return build_recap_write_payload_from_ingest(ctx, report)


def _project_recap_preview_mechanical(value: Any) -> Any:
    """Strip ``confirm_token`` (model-authored, not mechanical) before comparison."""
    if not isinstance(value, dict):
        return value
    return {k: v for k, v in value.items() if k in _RECAP_PREVIEW_MECHANICAL_KEYS}


def _compare_mechanical_fields(
    expected: dict[str, Any], actual: dict[str, Any]
) -> tuple[bool, dict[str, dict[str, Any]]]:
    """Field-by-field equality on ``_MECHANICAL_FIELDS``.

    Returns ``(match_all, diffs)``. ``diffs[field] = {"expected": ..., "actual": ...}``
    only for fields that differ. Comparison is structural (Python ``==``); both
    sides come from JSON dicts, so ordering inside lists is significant — that
    matches the helper contract (``duplicate_paragraphs`` order is deterministic).

    Special-case: ``recap_preview`` is compared on ``path`` + ``mode`` only;
    ``confirm_token`` is model-authored after the dry_run preview and is not a
    mechanical field (the helper returns ``""`` as a placeholder).
    """
    diffs: dict[str, dict[str, Any]] = {}
    for f in _MECHANICAL_FIELDS:
        e = expected.get(f)
        a = actual.get(f)
        if f == "recap_preview":
            e_proj = _project_recap_preview_mechanical(e)
            a_proj = _project_recap_preview_mechanical(a)
            if e_proj != a_proj:
                diffs[f] = {"expected": e_proj, "actual": a_proj}
        else:
            if e != a:
                diffs[f] = {"expected": e, "actual": a}
    return (not diffs), diffs


def _build_recap_write_payload_called(tool_trace: list[dict[str, Any]]) -> bool:
    """``True`` iff at least one ``build_recap_write_payload`` row appears in trace."""
    return bool(_build_recap_write_payload_calls(tool_trace))


def collect_scope_b_recap_ingest_report_extras(
    scenario: dict[str, Any],
    detail: PlanningTurnDetail,
    corpus_path: Path | None = None,
    *,
    recap_context_snapshot: RecapContext | None = None,
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
    * ``read_allowlist_soft_observations`` — when an out-of-allowlist path read
      was refused by the recap-write dispatch guard (no bytes returned) and the
      model recovered via a later ``assemble_recap_draft``. Hard violations for
      unguarded reads remain in ``scope_b_tool``.
    * ``build_recap_write_payload_called`` — ``True`` iff the model invoked the
      mechanical payload helper at least once this run.
    * ``mechanical_fields_match`` — ``True`` / ``False`` / ``None`` (not applicable).
      Compares mechanical sub-fields (``recap_preview``, ``duplicate_paragraphs``,
      ``prep_pointer_proposal``) of the model's final ``recap_write`` against
      what :func:`build_recap_write_payload_from_ingest` would return for this
      scenario + snapshot. Computed regardless of whether the helper was
      actually called (so cohort aggregator can stratify and answer "did the
      tool reduce variance?"). ``None`` when ``corpus_path`` /
      ``recap_context_snapshot`` aren't provided, when the raw notes can't be
      read, or when the model's ``recap_write`` can't be parsed.
    * ``mechanical_fields_diff`` — ``{field: {expected, actual}}`` for fields
      that differed (empty when ``mechanical_fields_match`` is ``True``;
      omitted when ``mechanical_fields_match`` is ``None``).

    ``corpus_path`` and ``recap_context_snapshot`` are optional for backwards
    compatibility with existing call sites and tests; mechanical-fields signals
    degrade to ``None`` when either is missing. New runner callers should pass
    both — the runner already has the snapshot.

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
    write_rows = _write_corpus_file_rows(tool_trace)
    phases = summarize_write_corpus_phases(write_calls)

    preview_required, commit_required = _resolve_write_phase_knobs(scenario)

    _hard, soft = _check_write_phases(
        write_rows,
        prefix=prefix,
        preview_required=preview_required,
        commit_required=commit_required,
    )

    # Last commit attempt's server response. ``None`` here means no commit
    # was attempted; ``succeeded=None`` inside the dict means the response
    # was unparseable (see :func:`_commit_outcome`). Cohort summaries
    # aggregate this to detect stale-token / allowlist regressions that
    # the call-shape view alone can't see (BACKLOG §1.0).
    commit_rows = [(i, a, r) for i, a, r in write_rows if not _dry_run_arg(a)]
    last_commit_outcome: dict[str, Any] | None = None
    if commit_rows:
        last_commit_outcome = _commit_outcome(commit_rows[-1][2])

    extras: dict[str, Any] = {
        "write_corpus_file_phases": phases,
        "write_corpus_file_soft_observations": soft,
        "write_corpus_file_last_commit_outcome": last_commit_outcome,
        "preview_required": preview_required,
        "commit_required": commit_required,
        "build_recap_write_payload_called": _build_recap_write_payload_called(
            tool_trace
        ),
        "mechanical_fields_match": None,
        "read_allowlist_soft_observations": [],
    }

    # Resolve a recap context if the caller didn't pass one but did pass the
    # corpus_path. Prefer the snapshot to avoid the same temporal-coupling
    # bug class the violations grader documents (BACKLOG §1.4).
    ctx: RecapContext | None = recap_context_snapshot
    if ctx is None and corpus_path is not None:
        try:
            ctx = resolve_recap_context(corpus_path.resolve())
        except RecapContextError:
            ctx = None

    if corpus_path is not None and ctx is not None:
        expected = _compute_expected_mechanical_payload(
            scenario, ctx, corpus_path.resolve()
        )
        actual = _extract_recap_write_from_final_text(detail.final_text or "")
        if expected is not None and actual is not None:
            match, diffs = _compare_mechanical_fields(expected, actual)
            extras["mechanical_fields_match"] = match
            extras["mechanical_fields_diff"] = diffs

    ctx_calls = _get_recap_context_calls(tool_trace)
    ctx_idx = ctx_calls[0][0] if len(ctx_calls) == 1 else -1
    if ctx is not None:
        allowed_extras = _read_allowlist_set(ctx, scenario)
        _, read_soft_ex = _read_allowlist_hard_and_soft(
            tool_trace,
            ctx_idx=ctx_idx,
            allowed=allowed_extras,
            prefix=prefix,
        )
        extras["read_allowlist_soft_observations"] = read_soft_ex

    return extras
