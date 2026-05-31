#!/usr/bin/env python3
"""Run C2S23 dogfood seed questions through live corpus planner turns.

Each question is sent as the sole ``user_line`` (discovery mode — no corpus
provisioning). Writes default artifacts under ``evals/c2_live_prep/artifacts/runs/<date>/``.

Examples::

  uv run python evals/c2_live_prep/run_c2s23_dogfood_planner.py

  uv run python evals/c2_live_prep/run_c2s23_dogfood_planner.py \\
    --question-ids s22-ingest-01,xsession-01,npc-01

  uv run python evals/c2_live_prep/run_c2s23_dogfood_planner.py --limit 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.corpus_path_tools import read_paths_from_tool_trace  # noqa: E402
from src.agent.planner import (  # noqa: E402
    _planner_tools_responses,
    _resolve_planner_model,
    build_corpus_path_ref_index,
    make_tool_dispatcher,
    run_planning_turn_detailed,
)
from src.agent.planner_cache import load_or_build_planner_instructions  # noqa: E402
from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

SEED_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json"
DEFAULT_CORPUS = ROOT / "corpus/eldyrwild-markdown"
SESSION_MEMORY_DIR = (
    DEFAULT_CORPUS / "Longmont Campaign/Campaign 2/Session Recaps/_session_memory"
)


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strip_markdown_json_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 3 or not lines[-1].strip().startswith("```"):
        return s
    return "\n".join(lines[1:-1]).strip()


def planner_message_from_final_text(final_text: str) -> tuple[str, str | None]:
    raw = _strip_markdown_json_fence(final_text or "")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return (final_text or "").strip(), f"invalid_json:{exc}"
    if isinstance(obj, dict) and isinstance(obj.get("message"), str):
        return obj["message"].strip(), None
    return (final_text or "").strip(), "missing_message_key"


def load_seed(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = str(data.get("schema") or "")
    if schema != "dmb_c2s23_dogfood_planning_benchmark_v0":
        raise ValueError(f"unexpected seed schema {schema!r} in {path}")
    return data


def resolve_session_memory_paths(sessions: tuple[int, ...]) -> list[Path]:
    paths: list[Path] = []
    for session in sessions:
        matches = sorted(SESSION_MEMORY_DIR.glob(f"Session {session:02d} - *.records_meta.jsonl"))
        if not matches:
            raise FileNotFoundError(f"No session memory JSONL for session {session} under {SESSION_MEMORY_DIR}")
        paths.append(matches[0])
    return paths


def merge_session_memory_jsonls(sources: list[Path], dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for path in sources:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                lines.append(line.strip())
    dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return dest


@contextmanager
def _session_memory_env_jsonl(path: Path | None):
    key = "DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL"
    prev = os.environ.get(key)
    if path is not None:
        os.environ[key] = str(path.resolve())
    try:
        yield
    finally:
        if path is None:
            return
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev


def _tool_names(tool_trace: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("tool") or "") for row in tool_trace if row.get("tool")]


def _summarize_turn(detail: Any) -> dict[str, Any]:
    tool_trace = list(detail.tool_trace or [])
    message, parse_err = planner_message_from_final_text(detail.final_text or "")
    tc = detail.telemetry_cost if hasattr(detail, "telemetry_cost") else {}
    if not isinstance(tc, dict):
        tc = {}
    return {
        "turn_count": len(detail.steps or []),
        "tool_calls": _tool_names(tool_trace),
        "corpus_paths_read": read_paths_from_tool_trace(tool_trace),
        "final_message": message,
        "final_message_parse_error": parse_err,
        "user_intent": _extract_user_intent(detail.final_text or ""),
        "scenario_estimated_cost_usd": tc.get("scenario_estimated_cost_usd"),
        "planner_estimated_cost_usd": tc.get("planner_estimated_cost_usd"),
    }


def _extract_user_intent(final_text: str) -> str | None:
    raw = _strip_markdown_json_fence(final_text or "")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and obj.get("user_intent") is not None:
        return str(obj.get("user_intent"))
    return None


def run_question(
    *,
    question_row: dict[str, Any],
    client: Any,
    model_id: str,
    corpus_path: Path,
    instructions: str,
    tools: list[dict[str, Any]],
    ref_index: dict[str, str],
    cache_root: Path | None,
) -> dict[str, Any]:
    qid = str(question_row.get("id") or "").strip()
    question = str(question_row.get("question") or "").strip()
    if not qid or not question:
        raise ValueError("seed row missing id or question")

    tool_cost_sink: list[dict[str, Any]] = []
    dispatch = make_tool_dispatcher(
        corpus_path,
        client,
        model_id,
        statblock_stub=None,
        tool_cost_sink=tool_cost_sink,
        corpus_path_ref_index=ref_index,
    )
    detail = run_planning_turn_detailed(
        client=client,
        model_id=model_id,
        instructions=instructions,
        tools=tools,
        corpus_path=corpus_path,
        user_line=question,
        previous_response_id=None,
        dispatch_tool=dispatch,
        telemetry_context={"scenario_id": qid, "harness": "c2s23_dogfood_planner"},
    )
    summary = _summarize_turn(detail)
    return {
        "question_id": qid,
        "question": question,
        "category": question_row.get("category"),
        "expected_source_roles": question_row.get("expected_source_roles"),
        "forbidden_source_roles_for_play_facts": question_row.get("forbidden_source_roles_for_play_facts"),
        "expected_artifact_actions": question_row.get("expected_artifact_actions"),
        "answer_requirements": question_row.get("answer_requirements"),
        "planner": summary,
        "tool_trace": detail.tool_trace,
        "final_text": detail.final_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "evals/c2_live_prep/artifacts/runs" / date.today().isoformat(),
    )
    parser.add_argument("--question-ids", type=str, default="", help="Comma-separated question ids")
    parser.add_argument("--category", type=str, default="", help="Only run questions in this category")
    parser.add_argument("--limit", type=int, default=0, help="Max questions to run (0 = all)")
    parser.add_argument("--planner-model", type=str, default="")
    parser.add_argument(
        "--session-memory-sessions",
        type=str,
        default="21,22",
        help="Comma-separated sessions to merge into planner session-memory JSONL (empty to disable)",
    )
    parser.add_argument("--cache-root", type=Path, default=None)
    args = parser.parse_args()

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py).",
            file=sys.stderr,
        )
        return 2

    seed = load_seed(args.seed.resolve())
    filter_ids = {s.strip() for s in args.question_ids.split(",") if s.strip()}
    category_filter = args.category.strip()

    questions: list[dict[str, Any]] = []
    for row in seed.get("questions") or []:
        if not isinstance(row, dict):
            continue
        qid = str(row.get("id") or "").strip()
        if filter_ids and qid not in filter_ids:
            continue
        if category_filter and str(row.get("category") or "") != category_filter:
            continue
        questions.append(row)
        if args.limit and len(questions) >= args.limit:
            break

    if not questions:
        print("No questions matched filters.", file=sys.stderr)
        return 1

    out_dir: Path = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sm_path: Path | None = None
    session_nums = [int(x.strip()) for x in args.session_memory_sessions.split(",") if x.strip()]
    if session_nums:
        sm_sources = resolve_session_memory_paths(tuple(session_nums))
        sm_path = merge_session_memory_jsonls(sm_sources, out_dir / "merged_session_memory_s21_s22.jsonl")

    from openai import OpenAI

    client = OpenAI()
    model_id = _resolve_planner_model(args.planner_model.strip() or None)
    corpus_path = args.corpus_root.resolve()

    rows: list[dict[str, Any]] = []
    costs: list[float] = []

    with _session_memory_env_jsonl(sm_path):
        instructions, corpus_fp = load_or_build_planner_instructions(
            corpus_path,
            cache_root=args.cache_root.resolve() if args.cache_root else None,
        )
        tools = _planner_tools_responses()
        ref_index = build_corpus_path_ref_index(corpus_path)

        for idx, row in enumerate(questions, start=1):
            qid = str(row.get("id") or "")
            print(f"[{idx}/{len(questions)}] {qid} …", file=sys.stderr, flush=True)
            try:
                result = run_question(
                    question_row=row,
                    client=client,
                    model_id=model_id,
                    corpus_path=corpus_path,
                    instructions=instructions,
                    tools=tools,
                    ref_index=ref_index,
                    cache_root=args.cache_root.resolve() if args.cache_root else None,
                )
            except Exception as exc:
                result = {
                    "question_id": qid,
                    "question": row.get("question"),
                    "error": str(exc),
                }
            rows.append(result)
            per_path = out_dir / f"c2s23_dogfood_{qid}.json"
            per_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

            cost = (result.get("planner") or {}).get("planner_estimated_cost_usd")
            if isinstance(cost, (int, float)):
                costs.append(float(cost))

    cost_min = min(costs) if costs else 0.0
    cost_max = max(costs) if costs else 0.0
    cost_sum = sum(costs)
    cost_mean = cost_sum / len(costs) if costs else 0.0

    summary = {
        "schema": "dmb_c2s23_dogfood_planner_run_v0",
        "generated_at": _utc_now_z(),
        "campaign_id": seed.get("campaign_id"),
        "planning_session": seed.get("planning_session"),
        "source_sessions": seed.get("source_sessions"),
        "model_id": model_id,
        "corpus_fingerprint": corpus_fp,
        "session_memory_jsonl": str(sm_path.relative_to(ROOT)) if sm_path else None,
        "question_count": len(rows),
        "aggregate": {
            "cost_usd": {
                "min": round(cost_min, 6),
                "mean": round(cost_mean, 6),
                "max": round(cost_max, 6),
                "sum": round(cost_sum, 6),
            }
        },
        "results": [
            {
                "question_id": r.get("question_id"),
                "category": r.get("category"),
                "error": r.get("error"),
                "final_message_excerpt": (r.get("planner") or {}).get("final_message", "")[:400]
                if r.get("planner")
                else None,
                "corpus_paths_read": (r.get("planner") or {}).get("corpus_paths_read"),
                "planner_estimated_cost_usd": (r.get("planner") or {}).get("planner_estimated_cost_usd"),
            }
            for r in rows
        ],
    }

    summary_path = out_dir / "c2s23_dogfood_planner_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    last_mirror = ROOT / "evals/c2_live_prep/artifacts/last_c2s23_dogfood_planner_summary.json"
    last_mirror.parent.mkdir(parents=True, exist_ok=True)
    last_mirror.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# C2S23 dogfood — planner run",
        "",
        f"**Generated:** {summary['generated_at']}",
        f"**Model:** `{model_id}`",
        f"**Questions:** {len(rows)}",
        f"**Cost sum:** ${cost_sum:.4f} (mean ${cost_mean:.4f})",
        "",
    ]
    for r in rows:
        planner = r.get("planner") or {}
        md_lines.extend(
            [
                f"## {r.get('question_id')}",
                "",
                f"**Q:** {r.get('question')}",
                "",
            ]
        )
        if r.get("error"):
            md_lines.append(f"**Error:** {r['error']}")
        else:
            md_lines.append(planner.get("final_message") or "(no message)")
            paths = planner.get("corpus_paths_read") or []
            if paths:
                md_lines.extend(["", "**Paths read:**"] + [f"- `{p}`" for p in paths[:12]])
        md_lines.extend(["", "---", ""])

    report_md = out_dir / "c2s23_dogfood_planner_report.md"
    report_md.write_text("\n".join(md_lines), encoding="utf-8")
    last_md = ROOT / "evals/c2_live_prep/artifacts/last_c2s23_dogfood_planner_report.md"
    last_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(json.dumps({"ok": True, "output_dir": str(out_dir.relative_to(ROOT)), "summary": summary_path.name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
