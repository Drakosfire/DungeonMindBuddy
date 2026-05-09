"""Per-skill dispatch guards that fail-closed on out-of-scope tool calls.

The Scope-B grader for the ``recap-write`` skill enforces that — after the model
calls ``get_recap_context`` once — every subsequent ``read_corpus_file`` /
``load_context_markdown`` path must come from the deterministic context returned
by that tool (``recent_recaps[].path`` ∪ ``prep_doc_path``). Catching that in the
grader is *post-hoc*: the model has already burned the round (and the dollars)
exploring out-of-scope files.

This module moves enforcement to the **dispatch layer**. When the planner is
running with ``active_skill_id="recap-write"``, we wrap the tool dispatcher so
that any out-of-allowlist read returns an explicit ``Error: ...`` string the
model sees on the next round and can self-correct from. The model's behavior
becomes structurally bounded: there is no path through which a Lysandra-side
file can land in the planner's context for this skill.

The allowlist is computed eagerly from ``resolve_recap_context(corpus_path)``
when the wrapper is built, so the guard never depends on the model actually
calling ``get_recap_context`` — that call is still required by the grader (and
useful for the model's own situational awareness), but the guard is a hard
floor underneath it.

Scenario harnesses can extend the allowlist via ``allowlist_extras`` — this
matches the grader's ``read_allowlist_extra`` config knob.

Anything other than ``read_corpus_file`` / ``load_context_markdown`` falls
through unchanged. Other skills with no registered guard get the dispatcher as-is.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from src.agent.recap_context import RecapContext, RecapContextError, resolve_recap_context

DispatchFn = Callable[[str, str], str]

#: Tools whose ``path`` argument is constrained by the recap-write allowlist.
_RECAP_WRITE_PATH_GUARDED_TOOLS = frozenset({"read_corpus_file", "load_context_markdown"})

#: ``get_recap_context`` is allowed but only with the no-pin shape (no
#: ``campaign_id``, no ``target_session``). The skill prompt + planner tool
#: schema both encourage this, but the model has been observed to "be helpful"
#: by passing ``campaign_id`` inferred from the user message; the dispatch
#: guard fail-closes that behavior so the auto-detected campaign is always
#: used. See ``Docs/Plans/archive/2026-05-09/operational-notes/PROCESSING-NOTES-Session-20-Manual-Ingest.md``.
_RECAP_WRITE_NO_PIN_TOOL = "get_recap_context"

#: Skill IDs that have a dispatch guard registered. Public so callers can
#: predicate on "do I need to wrap this dispatcher?".
SKILL_DISPATCH_GUARDS: frozenset[str] = frozenset({"recap-write"})


def _norm_rel_path(p: str) -> str:
    """Normalize a corpus-relative path for set-membership checks (POSIX, lowercase)."""
    return str(p or "").replace("\\", "/").strip().lower()


def compute_recap_write_read_allowlist(
    corpus_path: Path,
    *,
    extras: Iterable[str] | None = None,
    precomputed_recap_context: RecapContext | None = None,
) -> tuple[set[str], str | None]:
    """Build the deterministic read-allowlist for the ``recap-write`` skill.

    Returns ``(allowlist, error_message_or_None)``. When recap-context resolution
    fails (no recaps in this corpus, ambiguous prep doc, …), the allowlist is
    empty and ``error_message`` carries the reason; the wrapper surfaces that to
    the model so failures are debuggable end-to-end.

    Mirrors ``scope_b_grader._collect_scope_b_violations``'s allowlist logic so
    pre-flight enforcement and post-flight grading agree.

    When ``precomputed_recap_context`` is provided, the resolver is **not**
    re-run — the caller has already snapshotted ``resolve_recap_context`` once
    at scenario start (before any planner writes), and that snapshot is the
    source of truth for both turns of a multi-turn ingest. This avoids a
    temporal-coupling bug where a turn-1 commit shifts ``max(session)`` and
    turn-2 / grader resolution returns a stale-future allowlist that excludes
    the very paths the model legitimately read in turn 1.
    """
    if precomputed_recap_context is not None:
        ctx = precomputed_recap_context
    else:
        try:
            ctx = resolve_recap_context(corpus_path.resolve())
        except RecapContextError as exc:
            return set(), f"recap_context resolution failed: {exc}"
    allowed: set[str] = set()
    for entry in ctx.recent_recaps:
        allowed.add(_norm_rel_path(entry.path))
    if ctx.prep_doc_path:
        allowed.add(_norm_rel_path(ctx.prep_doc_path))
    for extra in extras or ():
        s = str(extra).strip()
        if s:
            allowed.add(_norm_rel_path(s))
    return allowed, None


def _format_allowlist_for_error(allowlist: set[str]) -> str:
    """Stable, human-readable rendering of the allowlist for error messages."""
    if not allowlist:
        return "(empty)"
    return ", ".join(sorted(allowlist))


def _check_get_recap_context_no_pin(args: dict) -> str | None:
    """Return an ``Error: ...`` string when ``get_recap_context`` was pinned, else ``None``.

    Mirrors ``scope_b_grader._no_pin_get_recap_context_args`` so dispatch and grading
    share one definition of "pinned." For the recap-write skill the auto-detect path
    is always correct (the corpus only contains one active campaign at the moment),
    and pinning lets the model paper over corpus-state issues that should fail loudly.
    """
    pinned: list[str] = []
    cid = args.get("campaign_id") if isinstance(args, dict) else None
    if cid is not None and str(cid).strip():
        pinned.append(f"campaign_id={cid!r}")
    ts = args.get("target_session") if isinstance(args, dict) else None
    if ts is not None and (not isinstance(ts, str) or str(ts).strip()):
        pinned.append(f"target_session={ts!r}")
    if not pinned:
        return None
    return (
        f"Error: recap-write skill blocked get_recap_context: do not pin "
        f"{', '.join(pinned)}. Call get_recap_context() with no arguments — the "
        f"tool auto-detects the active campaign and the next session. The "
        f"campaign hub mentioned in the user message is informational; you do "
        f"not need to forward it as an argument."
    )


def _wrap_recap_write(
    dispatch: DispatchFn,
    *,
    corpus_path: Path,
    allowlist_extras: Iterable[str] | None,
    precomputed_recap_context: RecapContext | None = None,
) -> DispatchFn:
    # Lazy import: ``planner`` imports this module at package load; importing
    # ``planner`` here would create a circular import at module init time.
    from src.agent.planner import (  # noqa: PLC0415
        _resolve_planner_read_argument,
        build_corpus_path_ref_index,
    )

    allowlist, resolve_err = compute_recap_write_read_allowlist(
        corpus_path,
        extras=allowlist_extras,
        precomputed_recap_context=precomputed_recap_context,
    )
    ref_index = build_corpus_path_ref_index(corpus_path.resolve())

    def wrapped(name: str, raw_args: str) -> str:
        if name == _RECAP_WRITE_NO_PIN_TOOL:
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError as exc:
                return f"Error: invalid JSON arguments for {name}: {exc}"
            err = _check_get_recap_context_no_pin(args if isinstance(args, dict) else {})
            if err is not None:
                return err
            return dispatch(name, raw_args)
        if name not in _RECAP_WRITE_PATH_GUARDED_TOOLS:
            return dispatch(name, raw_args)
        if resolve_err is not None:
            return (
                f"Error: recap-write read-guard cannot enforce allowlist for "
                f"{name}: {resolve_err}. Resolve the corpus state, then retry."
            )
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError as exc:
            return f"Error: invalid JSON arguments for {name}: {exc}"
        path_raw = str((args or {}).get("path", "")).strip()
        if not path_raw:
            return dispatch(name, raw_args)
        resolved = _resolve_planner_read_argument(corpus_path, path_raw, ref_index)
        if path_raw.lower().startswith("c:") and not resolved:
            return (
                f"Error: unknown corpus file ref {path_raw!r}. Copy a ` [c:…] ` token "
                f"from the corpus tree after the `.md` name, or pass the full "
                f"corpus-relative `.md` path."
            )
        check_rel = resolved or path_raw
        if _norm_rel_path(check_rel) in allowlist:
            return dispatch(name, raw_args)
        return (
            f"Error: recap-write skill blocked {name} for path {path_raw!r}: not in "
            f"recent_recaps ∪ prep_doc_path. Use only paths returned by "
            f"`get_recap_context`. Allowed: [{_format_allowlist_for_error(allowlist)}]. "
            f"For raw session notes, call `assemble_recap_draft` (do not read the "
            f"staging file directly)."
        )

    return wrapped


def wrap_dispatch_for_skill(
    dispatch: DispatchFn,
    *,
    corpus_path: Path,
    active_skill_id: str | None,
    allowlist_extras: Iterable[str] | None = None,
    precomputed_recap_context: RecapContext | None = None,
) -> DispatchFn:
    """Return ``dispatch`` wrapped with skill-specific fail-closed guards.

    For ``active_skill_id="recap-write"`` this wraps ``read_corpus_file`` /
    ``load_context_markdown`` so out-of-allowlist paths return an ``Error: ...``
    string the model can recover from on the next round. For any other skill (or
    ``None``), the original dispatcher is returned unchanged so non-recap callers
    pay no cost.

    Args:
        dispatch: The base dispatcher returned by ``make_tool_dispatcher``.
        corpus_path: Same corpus root the dispatcher was built against.
        active_skill_id: The planner's current skill id; only ``"recap-write"``
            is currently guarded (see :data:`SKILL_DISPATCH_GUARDS`).
        allowlist_extras: Optional iterable of corpus-relative paths to add to
            the recap-write allowlist (mirrors the grader's
            ``read_allowlist_extra`` scenario knob).
        precomputed_recap_context: Optional snapshot from
            :func:`src.agent.recap_context.resolve_recap_context` taken **before**
            any planner turn writes to disk. When provided, both this guard and
            the grader (when wired the same way) use the same frozen context for
            every turn of a multi-turn scenario, eliminating the temporal-
            coupling bug where a turn-1 commit shifts ``max(session)`` and turn-2
            re-resolution returns a stale-future allowlist.
    """
    if (active_skill_id or "").strip() != "recap-write":
        return dispatch
    return _wrap_recap_write(
        dispatch,
        corpus_path=corpus_path,
        allowlist_extras=allowlist_extras,
        precomputed_recap_context=precomputed_recap_context,
    )
