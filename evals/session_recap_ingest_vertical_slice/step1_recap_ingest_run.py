"""Scope-B step 1: run the corpus planner with writes on against a pre-state corpus.

Builds a tmp corpus via :func:`build_pre_state_corpus`, loads Session 20 raw notes from the
slice fixture, prepends the **recap-write** skill body (minus YAML frontmatter),
and runs one :func:`run_planning_turn_detailed` pass with write tools registered.

Run (from repo root)::

    export DUNGEONMIND_PLANNER_ALLOW_WRITES=1   # optional; this module setdefaults to 1
    # OPENAI_API_KEY: repo .env / .env.development via load_dungeonmindbuddy_dotenv (see lysandra step1)
    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run

Other flags::

    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --print-root
    uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run --live-corpus
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evals.lysandra_vertical_slice.step1_planner_trace import (  # noqa: E402
    PlannerStep1Run,
    _empty_fail,
    configure_planner_review_logging,
    resolve_review_mode,
)
from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir  # noqa: E402
from evals.planner_slice.live_eval import (  # noqa: E402
    evaluate_scenario_detail,
    fixture_scenario_id,
    resolve_planner_user_message,
)
from evals.session_recap_ingest_vertical_slice.scope_b_grader import (  # noqa: E402
    collect_scope_b_recap_ingest_violations,
)
from evals.session_recap_ingest_vertical_slice.step0_pre_state import build_pre_state_corpus  # noqa: E402
from src.agent.planner import (  # noqa: E402
    _resolve_planner_model,
    build_corpus_path_ref_index,
    make_tool_dispatcher,
    merge_planning_turn_details,
    run_planning_turn_detailed,
    _planner_tools_responses,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.planner_telemetry import maybe_full_text, text_sig  # noqa: E402
from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

_SLICE_DIR = Path(__file__).resolve().parent
_GOLD_SCENARIO = _SLICE_DIR / "gold" / "scope_b_session_20.json"
_SKILL_PATH = Path(_REPO_ROOT) / ".cursor/skills/recap-write/SKILL.md"
_ALLOW_WRITES_ENV = "DUNGEONMIND_PLANNER_ALLOW_WRITES"


def load_scope_b_scenario() -> dict[str, Any]:
    if not _GOLD_SCENARIO.is_file():
        raise FileNotFoundError(f"missing gold scenario: {_GOLD_SCENARIO}")
    return json.loads(_GOLD_SCENARIO.read_text(encoding="utf-8"))


def _strip_markdown_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].lstrip("\n")
    return text


def load_skill_markdown_for_prompt(*, max_chars: int = 24_000) -> str:
    """Load SKILL.md body (no YAML frontmatter) for inclusion in the user message."""
    if not _SKILL_PATH.is_file():
        return (
            "(Skill file not found at `.cursor/skills/recap-write/SKILL.md`; "
            "use the recap-write skill from the repo.)\n"
        )
    body = _strip_markdown_frontmatter(_SKILL_PATH.read_text(encoding="utf-8")).strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n…(skill excerpt truncated for prompt size)…\n"
    return body


def load_fixture_raw_notes() -> str:
    sc = load_scope_b_scenario()
    rel = str(sc.get("fixture_relpath") or "fixtures/session_20_raw_notes.txt").strip()
    path = (_SLICE_DIR / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"fixture missing: {path}")
    return path.read_text(encoding="utf-8")


def build_recap_ingest_user_message(raw_notes: str, *, raw_notes_corpus_rel: str) -> str:
    skill = load_skill_markdown_for_prompt()
    rel = str(raw_notes_corpus_rel).strip().replace("\\", "/")
    return (
        "You are executing the **recap-write** skill against the "
        "attached campaign corpus. Corpus write tools are enabled: use two-phase "
        "`write_corpus_file` / `append_timeline_row` per the skill.\n\n"
        "**Automated grading (required):** In the planner JSON `message` field, include a "
        "```json fenced block with the full `recap_write_v1` structured payload "
        "(see skill and `src/agent/recap_write_output_schema.py`). The object **must** "
        "include `\"schema_version\": \"recap_write_v1\"` and every required key from that "
        "schema (`notes_for_gm` is a **string**, not an array; `prep_pointer_proposal` is "
        "an object or null). You may put a ```diff preview first, but a diff-only `message` "
        "**fails** the gate — use empty arrays where a section has nothing to report.\n\n"
        "The same raw session notes are also available on disk for "
        f"`assemble_recap_draft` at corpus-relative path `{rel}` "
        "(use this path; do not re-type the notes into `write_corpus_file`).\n\n"
        "--- Skill (reference) ---\n\n"
        f"{skill}\n\n"
        "--- Raw session notes ---\n\n"
        f"{raw_notes.strip()}\n"
    )


def run_session_recap_ingest_turn(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    raw_notes: str | None = None,
    allow_corpus_writes: bool = True,
) -> PlannerStep1Run:
    """One planner turn for Session 20 recap ingest; gates from ``scope_b_session_20.json`` final block."""
    sc = copy.deepcopy(scenario or load_scope_b_scenario())
    notes = raw_notes if raw_notes is not None else load_fixture_raw_notes()
    ingest_rel = str(
        sc.get("ingest_raw_notes_relpath")
        or "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    ).strip()
    staging_path = (corpus_dir / ingest_rel).resolve()
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_text(notes, encoding="utf-8")

    sc.setdefault("input", {})["user_message"] = build_recap_ingest_user_message(
        notes, raw_notes_corpus_rel=ingest_rel
    )

    corpus_path = corpus_dir.resolve()
    sid = fixture_scenario_id(sc)
    user_message, input_violations = resolve_planner_user_message(sc, corpus_path)
    if input_violations:
        return _empty_fail(sid, {"input": input_violations})
    if not user_message.strip():
        return _empty_fail(sid, {"input": [f"[{sid}] empty user message"]})

    instructions, fp = load_or_build_planner_instructions(
        corpus_path,
        cache_root=cache_root,
        include_write_tools=allow_corpus_writes,
    )
    tools = _planner_tools_responses(include_write_tools=allow_corpus_writes)
    tool_cost_sink: list[dict[str, Any]] = []
    ref_index = build_corpus_path_ref_index(corpus_path)
    dispatch = make_tool_dispatcher(
        corpus_path,
        client,
        model_id,
        statblock_stub=None,
        tool_cost_sink=tool_cost_sink,
        corpus_path_ref_index=ref_index,
        allow_corpus_writes=allow_corpus_writes,
    )

    detail = run_planning_turn_detailed(
        client=client,
        model_id=model_id,
        instructions=instructions,
        tools=tools,
        corpus_path=corpus_path,
        user_line=user_message,
        previous_response_id=None,
        dispatch_tool=dispatch,
        telemetry_context={
            "scenario_id": sid,
            "suite": "session_recap_ingest_vertical_slice",
            "corpus_fingerprint": fp,
            "turn_index": 0,
        },
        corpus_path_ref_index=ref_index,
    )
    follow_block = sc.get("followup_turn")
    followup_user_line = ""
    first_turn_final_text = (detail.final_text or "").strip()
    if isinstance(follow_block, dict):
        follow_msg = str(follow_block.get("user_message", "")).strip()
        if follow_msg and detail.last_response_id:
            followup_user_line = follow_msg
            detail2 = run_planning_turn_detailed(
                client=client,
                model_id=model_id,
                instructions=instructions,
                tools=tools,
                corpus_path=corpus_path,
                user_line=follow_msg,
                previous_response_id=detail.last_response_id,
                dispatch_tool=dispatch,
                telemetry_context={
                    "scenario_id": sid,
                    "suite": "session_recap_ingest_vertical_slice",
                    "corpus_fingerprint": fp,
                    "phase": "followup_user",
                    "turn_index": 1,
                },
                corpus_path_ref_index=ref_index,
            )
            detail = merge_planning_turn_details(detail, detail2)
        else:
            first_turn_final_text = ""
    else:
        first_turn_final_text = ""

    statblock_usd = sum(float(x.get("total_usd", 0) or 0) for x in tool_cost_sink)
    tc = dict(detail.telemetry_cost or {})
    planner_usd = float(tc.get("planner_estimated_cost_usd", 0) or 0)
    tc["statblock_tool_estimated_cost_usd"] = round(statblock_usd, 6)
    tc["scenario_estimated_cost_usd"] = round(planner_usd + statblock_usd, 6)
    detail = replace(detail, telemetry_cost=tc)
    scenario_usd = tc["scenario_estimated_cost_usd"]
    result = evaluate_scenario_detail(
        sc,
        detail,
        estimated_cost_usd=scenario_usd,
        corpus_fingerprint=fp,
    )
    scope_v = collect_scope_b_recap_ingest_violations(sc, detail, corpus_path)
    if scope_v:
        merged_violations = dict(result.violations)
        for key, rows in scope_v.items():
            merged_violations.setdefault(key, []).extend(rows)
        result = replace(
            result,
            violations=merged_violations,
            passed=result.passed and not scope_v,
        )

    return PlannerStep1Run(
        detail=detail,
        result=result,
        instructions=instructions,
        user_line=user_message,
        corpus_fingerprint=fp,
        post_planner_step2_benchmark_detail=None,
        scenario_key=sid,
        followup_user_line=followup_user_line,
        first_turn_final_text=first_turn_final_text,
    )


def print_recap_ingest_review(
    run: PlannerStep1Run,
    *,
    corpus_dir: Path,
    model_id: str,
    review_mode: str = "summary",
) -> None:
    """Compact review to stdout (mirrors other vertical slices, recap-specific header)."""
    d = run.detail
    sep = "=" * 72
    print(sep)
    print("SESSION RECAP INGEST — PLANNER REVIEW")
    print(sep)
    print(f"scenario_id:      {run.result.scenario_id}")
    print(f"model_id:         {model_id}")
    print(f"gates_passed:     {run.result.passed}")
    print(f"review_mode:      {review_mode}")
    print(f"corpus_fprint:    {run.corpus_fingerprint}")
    print(f"corpus_dir:       {corpus_dir.resolve()}")
    print(f"hit_tool_limit:   {d.hit_tool_round_limit}")
    print(f"tool_trace rows:  {len(d.tool_trace)}")
    print()
    print(sep)
    print("§ Prompt payload sizes")
    print(sep)
    print(f"instructions:  {text_sig(run.instructions)}")
    print(f"user_line:     {text_sig(run.user_line)}")
    print()
    print(sep)
    print("§ Token usage (per round)")
    print(sep)
    for i, row in enumerate(d.usage_rounds):
        u = row.get("usage") or {}
        print(
            f"  round[{i}] input={u.get('input_tokens')} output={u.get('output_tokens')} "
            f"cached={u.get('cached_tokens')}"
        )
    tc = d.telemetry_cost or {}
    print(f"  scenario_estimated_cost_usd: {tc.get('scenario_estimated_cost_usd')}")
    print()
    if not run.result.passed:
        print(sep)
        print("§ Violations")
        print(sep)
        for k, rows in sorted(run.result.violations.items()):
            for r in rows:
                print(f"  {k}: {r}")
        print()
    print(sep)
    print("§ Final assistant text (preview)")
    print(sep)
    print(maybe_full_text(d.final_text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Session recap ingest — planner step 1 (live API).")
    parser.add_argument(
        "--print-root",
        action="store_true",
        help="Copy corpus, apply pre-state manifest, print tmp corpus root and exit.",
    )
    parser.add_argument(
        "--live-corpus",
        action="store_true",
        help="Use live repo corpus/eldyrwild-markdown (no pre-state strip). For debugging only.",
    )
    parser.add_argument(
        "--tmp-parent",
        type=Path,
        default=None,
        help="Optional parent directory for pre-state copy (default: system temp).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="Override planner model id (else MODEL_POLICY / default).",
    )
    parser.add_argument(
        "--no-writes",
        action="store_true",
        help="Disable corpus write tools (overrides env).",
    )
    args = parser.parse_args()

    if args.print_root:
        if args.tmp_parent is not None:
            args.tmp_parent.mkdir(parents=True, exist_ok=True)
            root = build_pre_state_corpus(tmp_dir=args.tmp_parent)
        else:
            root = build_pre_state_corpus()
        print(root)
        return

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Add the key to repo .env or export it for CI.",
            file=sys.stderr,
        )
        sys.exit(2)

    os.environ.setdefault(_ALLOW_WRITES_ENV, "1")
    allow_writes = not args.no_writes and os.environ.get(_ALLOW_WRITES_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    if args.live_corpus:
        corpus_root = resolve_corpus_dir()
    elif args.tmp_parent is not None:
        args.tmp_parent.mkdir(parents=True, exist_ok=True)
        corpus_root = build_pre_state_corpus(tmp_dir=args.tmp_parent)
    else:
        corpus_root = build_pre_state_corpus()

    if not corpus_root.is_dir():
        print(f"corpus directory missing: {corpus_root}", file=sys.stderr)
        sys.exit(2)

    from openai import OpenAI  # noqa: E402

    configure_planner_review_logging()
    review_mode = resolve_review_mode()
    print(
        f"[recap-ingest] corpus_dir={corpus_root}\n"
        f"[recap-ingest] pre_state={'off' if args.live_corpus else 'on'} "
        f"allow_corpus_writes={allow_writes}\n"
        f"[recap-ingest] PLANNER_REVIEW_MODE={review_mode}\n",
        file=sys.stderr,
    )

    client = OpenAI()
    model_id = _resolve_planner_model(args.model.strip() or None)

    run = run_session_recap_ingest_turn(
        corpus_dir=corpus_root,
        client=client,
        model_id=model_id,
        allow_corpus_writes=allow_writes,
    )
    print_recap_ingest_review(run, corpus_dir=corpus_root, model_id=model_id, review_mode=review_mode)

    if not run.result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
