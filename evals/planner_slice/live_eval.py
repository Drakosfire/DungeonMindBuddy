"""Live planner evaluation: real model, prebuilt inputs, expected actions per step + final outputs."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from src.agent.planner import (
    PlanningModelStepRecord,
    PlanningTurnDetail,
    _planner_tools_responses,
    make_tool_dispatcher,
    run_planning_turn_detailed,
)
from src.agent.planner_cache import load_or_build_planner_instructions
from src.agent.planner_telemetry import maybe_full_text, text_sig

from evals.planner_slice.live_report import (
    render_planner_live_report_markdown,
    render_suite_index_markdown,
    write_planner_live_report,
)
from evals.planner_slice.planner_answer_benchmark import instrument_planner_answer
from src.prompts.planner_live_eval_user import AUTONOMOUS_PLANNING_USER_SUFFIX

_log = logging.getLogger("dmb.planner.live_eval")


def _live_eval_log(event: str, payload: dict[str, Any], *, level: int = logging.INFO) -> None:
    row = {"event": event, **payload}
    _log.log(
        level,
        "[dmb.planner.live_eval] %s",
        json.dumps(row, ensure_ascii=False, default=str),
    )


def _report_dir_from_kw_or_env(report_dir: Path | None) -> Path | None:
    if report_dir is not None:
        return report_dir
    raw = os.environ.get("PLANNER_LIVE_REPORT_DIR", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


@dataclass
class LiveEvalResult:
    scenario_id: str
    passed: bool
    violations: dict[str, list[str]] = field(default_factory=dict)
    estimated_cost_usd: float | None = None
    corpus_fingerprint: str | None = None
    report_path: str | None = None


def _fail_prefix(sid: str) -> str:
    return f"[planner_live_eval:{sid}]"


def _norm_rel_path(path: str) -> str:
    return path.strip().replace("\\", "/").lower().lstrip("./")


_CITATION_PATH_IN_TEXT = re.compile(
    r"((?:Elderwyld|Longmont Campaign)/.+?\.md)",
    re.IGNORECASE | re.DOTALL,
)

_H2_HEADING_LINE = re.compile(r"^\s*##\s+\S")

def _count_h2_headings(text: str) -> int:
    return sum(1 for line in text.splitlines() if _H2_HEADING_LINE.match(line))


def extract_cited_markdown_paths_from_final(final_text: str) -> list[str]:
    """
    Extract corpus-relative ``*.md`` paths from the model's final prose.

    Anchors on known corpus roots (``Elderwyld/``, ``Longmont Campaign/``) so we do not
    treat arbitrary ``word/foo.md`` fragments as citations. Folder names may include spaces.
    """
    out: list[str] = []
    seen: set[str] = set()
    for m in _CITATION_PATH_IN_TEXT.finditer(final_text):
        raw = m.group(1).strip().rstrip(").,;:\"'")
        if "/" not in raw or len(raw) < 10:
            continue
        start = m.start()
        prefix = final_text[max(0, start - 8) : start].lower()
        if "http://" in prefix or "https://" in prefix:
            continue
        low = _norm_rel_path(raw)
        if low in seen:
            continue
        seen.add(low)
        out.append(raw)
    return out


def read_paths_from_tool_trace(tool_trace: list[dict[str, Any]]) -> list[str]:
    """``path`` arguments from executed ``read_corpus_file`` calls in order."""
    paths: list[str] = []
    for row in tool_trace:
        if str(row.get("tool", "")) != "read_corpus_file":
            continue
        args = row.get("arguments") or {}
        p = str(args.get("path", "")).strip()
        if p:
            paths.append(p)
    return paths


def dedupe_read_paths_preserve_order(reads: list[str]) -> list[str]:
    """One mention in ``final_text`` suffices per distinct path (duplicate reads are common)."""
    seen: set[str] = set()
    out: list[str] = []
    for r in reads:
        if not r.strip():
            continue
        n = _norm_rel_path(r)
        if n in seen:
            continue
        seen.add(n)
        out.append(r)
    return out


def cite_matches_any_read(cited: str, reads: list[str]) -> bool:
    """True if ``cited`` is the same logical file as some path in ``reads`` (suffix / basename)."""
    c = _norm_rel_path(cited)
    if not c:
        return False
    reads_n = [_norm_rel_path(r) for r in reads if r.strip()]
    if c in reads_n:
        return True
    c_base = c.rsplit("/", 1)[-1]
    for r in reads_n:
        if r.endswith("/" + c.lstrip("/")) or r.endswith(c):
            return True
        r_base = r.rsplit("/", 1)[-1]
        if c_base and r_base and c_base == r_base:
            return True
    return False


def reads_mentioned_in_final(final_text: str, reads: list[str]) -> list[str]:
    """Return read paths whose normalized form or basename is missing from ``final_text``."""
    low = _norm_rel_path(final_text)
    missing: list[str] = []
    for r in reads:
        if not r.strip():
            continue
        n = _norm_rel_path(r)
        base = n.rsplit("/", 1)[-1]
        if n in low or (base and base in low):
            continue
        missing.append(r)
    return missing


def match_calls_satisfy(
    scenario_id: str,
    step_label: str,
    calls: list[dict[str, Any]],
    specs: list[dict[str, Any]],
) -> list[str]:
    """Each matcher in ``specs`` must match a distinct call in ``calls``."""
    violations: list[str] = []
    unused_indices = set(range(len(calls)))
    for mi, spec in enumerate(specs):
        tool = str(spec.get("tool", "")).strip()
        path_contains = str(spec.get("path_contains", "")).lower()
        desc_min = spec.get("description_min_chars")
        matched_idx: int | None = None
        for i in sorted(unused_indices):
            c = calls[i]
            if str(c.get("name", "")) != tool:
                continue
            args = c.get("arguments") or {}
            if tool == "read_corpus_file":
                path = str(args.get("path", "")).lower()
                if path_contains and path_contains not in path:
                    continue
            elif tool == "generate_statblock":
                desc = str(args.get("description", ""))
                if desc_min is not None and len(desc) < int(desc_min):
                    continue
            matched_idx = i
            break
        if matched_idx is None:
            violations.append(
                f"{_fail_prefix(scenario_id)} {step_label}: calls_satisfy[{mi}] not matched "
                f"(tool={tool!r} path_contains={path_contains!r} description_min_chars={desc_min!r}); "
                f"got_calls={calls!r}"
            )
        else:
            unused_indices.discard(matched_idx)
    return violations


def _check_step_require(
    scenario_id: str,
    step_label: str,
    step_record: PlanningModelStepRecord,
    require: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    if not require:
        return violations
    calls = step_record.function_calls
    max_calls = require.get("max_function_calls")
    if max_calls is not None and len(calls) > int(max_calls):
        violations.append(
            f"{_fail_prefix(scenario_id)} {step_label}: max_function_calls want<={max_calls} got {len(calls)}"
        )
    specs = require.get("calls_satisfy") or []
    if specs:
        violations.extend(match_calls_satisfy(scenario_id, step_label, calls, list(specs)))
    return violations


def _check_final_require(
    scenario_id: str,
    detail: PlanningTurnDetail,
    require: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    if not require:
        return violations
    text = detail.final_text
    if detail.hit_tool_round_limit:
        violations.append(f"{_fail_prefix(scenario_id)} final: hit_tool_round_limit")

    for needle in require.get("output_text_contains_all") or []:
        if str(needle) not in text:
            violations.append(
                f"{_fail_prefix(scenario_id)} final: output_text must contain {needle!r}"
            )
    anys = require.get("output_text_contains_any") or []
    if anys and not any(str(a) in text for a in anys):
        violations.append(
            f"{_fail_prefix(scenario_id)} final: output_text must contain one of {anys!r}"
        )
    min_chars = require.get("min_output_chars")
    if min_chars is not None and len(text) < int(min_chars):
        violations.append(
            f"{_fail_prefix(scenario_id)} final: min_output_chars want>={min_chars} got {len(text)}"
        )

    min_h2 = require.get("min_h2_headings")
    if min_h2 is not None:
        got_h2 = _count_h2_headings(text)
        want_h2 = int(min_h2)
        if got_h2 < want_h2:
            violations.append(
                f"{_fail_prefix(scenario_id)} final: min_h2_headings want>={want_h2} "
                f"(markdown `## Section` lines) got {got_h2}"
            )

    one_tool = require.get("tool_trace_must_include_tool")
    if one_tool:
        names = [str(t.get("tool", "")) for t in detail.tool_trace]
        if str(one_tool) not in names:
            violations.append(
                f"{_fail_prefix(scenario_id)} final: tool_trace must include {one_tool!r}; got {names!r}"
            )
    many = require.get("tool_trace_must_include_tools") or []
    names = [str(t.get("tool", "")) for t in detail.tool_trace]
    for tname in many:
        if str(tname) not in names:
            violations.append(
                f"{_fail_prefix(scenario_id)} final: tool_trace must include tool {tname!r}; got {names!r}"
            )

    order = require.get("tool_trace_tools_in_order") or []
    if order:
        idx = 0
        for want in order:
            while idx < len(names) and names[idx] != want:
                idx += 1
            if idx >= len(names):
                violations.append(
                    f"{_fail_prefix(scenario_id)} final: tool_trace_tools_in_order missing {want!r} after "
                    f"position; trace={names!r}"
                )
                break
            idx += 1

    subs = require.get("read_corpus_paths_must_include") or []
    if subs:
        reads_all = read_paths_from_tool_trace(detail.tool_trace)
        if not reads_all:
            violations.append(
                f"{_fail_prefix(scenario_id)} final: read_corpus_paths_must_include set but no "
                f"read_corpus_file paths in tool_trace"
            )
        else:
            for sub in subs:
                s = str(sub).lower()
                if not any(s in p.lower() for p in reads_all):
                    violations.append(
                        f"{_fail_prefix(scenario_id)} final: read_corpus_paths_must_include missing "
                        f"substring {sub!r} in tool_trace read paths {reads_all!r}"
                    )

    if require.get("cited_paths_must_match_reads"):
        reads = read_paths_from_tool_trace(detail.tool_trace)
        if not reads:
            violations.append(
                f"{_fail_prefix(scenario_id)} final: cited_paths_must_match_reads but no "
                f"read_corpus_file paths in tool_trace"
            )
        else:
            cites = extract_cited_markdown_paths_from_final(text)
            min_cites = int(require.get("min_cited_markdown_paths", 1) or 1)
            if len(cites) < min_cites:
                violations.append(
                    f"{_fail_prefix(scenario_id)} final: expected at least {min_cites} distinct .md path "
                    f"citations in final_text; found {len(cites)} ({cites!r})"
                )
            for cite in cites:
                if not cite_matches_any_read(cite, reads):
                    violations.append(
                        f"{_fail_prefix(scenario_id)} final: cited path {cite!r} is not grounded in "
                        f"read_corpus_file tool_trace paths {reads!r}"
                    )

    if require.get("read_paths_must_appear_in_final"):
        reads = dedupe_read_paths_preserve_order(read_paths_from_tool_trace(detail.tool_trace))
        missing = reads_mentioned_in_final(text, reads)
        if missing:
            violations.append(
                f"{_fail_prefix(scenario_id)} final: read_paths_must_appear_in_final missing "
                f"mentions for {missing!r} in final_text"
            )

    return violations


def collect_scenario_violations(
    scenario: dict[str, Any],
    detail: PlanningTurnDetail,
) -> dict[str, list[str]]:
    """Assert fixture expectations against an already-computed ``PlanningTurnDetail``."""
    sid = str(scenario.get("id", "unknown"))
    violations: dict[str, list[str]] = {}
    steps_spec = list(scenario.get("steps") or [])
    for i, spec in enumerate(steps_spec):
        key = f"step_{i}_{spec.get('id', '')}"
        if i >= len(detail.steps):
            if spec.get("optional"):
                continue
            violations.setdefault(key, []).append(
                f"{_fail_prefix(sid)} expected step {i} ({spec.get('id')!r}) but model stopped after "
                f"{len(detail.steps)} response(s)"
            )
            continue
        req = spec.get("require") or {}
        if not req:
            continue
        step_v = _check_step_require(sid, f"step_{i}", detail.steps[i], req)
        if step_v:
            violations.setdefault(key, []).extend(step_v)

    final_req = (scenario.get("final") or {}).get("require") or {}
    fv = _check_final_require(sid, detail, final_req)
    if fv:
        violations.setdefault("final", []).extend(fv)
    return violations


def evaluate_scenario_detail(
    scenario: dict[str, Any],
    detail: PlanningTurnDetail,
    *,
    estimated_cost_usd: float | None = None,
    corpus_fingerprint: str | None = None,
) -> LiveEvalResult:
    """Score a scenario against a pre-recorded planner turn (e.g. from OpenAI Batch)."""
    sid = str(scenario.get("id", "unknown"))
    violations = collect_scenario_violations(scenario, detail)
    return LiveEvalResult(
        scenario_id=sid,
        passed=len(violations) == 0,
        violations=violations,
        estimated_cost_usd=estimated_cost_usd,
        corpus_fingerprint=corpus_fingerprint,
    )


def _read_prior_session_doc(corpus_dir: Path, rel: str) -> tuple[str | None, str | None]:
    """
    Read ``rel`` as a path relative to ``corpus_dir`` (POSIX, no ``..``).

    Returns ``(text, None)`` or ``(None, error_message)``.
    """
    rel_norm = rel.strip().replace("\\", "/")
    if not rel_norm:
        return None, "prior_session_path is empty"
    parts = Path(rel_norm).parts
    if rel_norm.startswith("/") or ".." in parts:
        return None, "prior_session_path must be corpus-relative with no .. components"
    root = corpus_dir.resolve()
    target = (root / rel_norm).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, "prior_session_path resolves outside corpus_dir"
    if not target.is_file():
        return None, f"prior_session_path not found or not a file: {rel_norm!r}"
    try:
        return target.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, f"cannot read prior_session_path {rel_norm!r}: {exc}"


def resolve_planner_user_message(
    scenario: dict[str, Any],
    corpus_dir: Path,
) -> tuple[str, list[str]]:
    """
    Build the planner user line from fixture ``input``.

    **Modes**

    1. **Full message** — Non-empty ``input.user_message`` is sent as-is (legacy / escape hatch).
    2. **Session doc + ask** — Leave ``user_message`` empty; set ``input.planning_ask`` and optionally
       ``input.prior_session_path``. The effective prompt is prior body + planning ask.
    3. **Session doc + goal (autonomous plan)** — Leave ``user_message`` and ``planning_ask`` empty; set
       ``input.planning_goal`` and optionally ``prior_session_path``. A short autonomous-planning
       suffix is appended so the model must choose reads and section structure itself. If both
       ``planning_ask`` and ``planning_goal`` are set, ``planning_ask`` wins.

    **Override:** If ``PLANNER_PRIOR_SESSION_PATH`` is set in the environment, it replaces
    ``input.prior_session_path`` so you can point at a recap file without editing the JSON.
    """
    sid = str(scenario.get("id", "unknown"))
    inp = scenario.get("input") or {}
    direct = str(inp.get("user_message", "")).strip()
    if direct:
        return direct, []

    planning_ask = str(inp.get("planning_ask", "")).strip()
    planning_goal = str(inp.get("planning_goal", "")).strip()
    if not planning_ask and not planning_goal:
        return "", [
            f"{_fail_prefix(sid)} set input.user_message, or input.planning_ask, or input.planning_goal "
            f"(with optional prior_session_path / PLANNER_PRIOR_SESSION_PATH)"
        ]

    env_prior = os.environ.get("PLANNER_PRIOR_SESSION_PATH", "").strip()
    prior_rel = env_prior or str(inp.get("prior_session_path", "")).strip()
    blocks: list[str] = []
    if prior_rel:
        body, err = _read_prior_session_doc(corpus_dir, prior_rel)
        if err:
            return "", [f"{_fail_prefix(sid)} {err}"]
        blocks.append(f"--- Prior session (`{prior_rel}`) ---\n{body}")
    if planning_ask:
        blocks.append(f"--- Planning ask ---\n{planning_ask}")
    else:
        blocks.append(f"--- Planning goal ---\n{planning_goal}\n\n{AUTONOMOUS_PLANNING_USER_SUFFIX}")
    return "\n\n".join(blocks), []


def evaluate_live_scenario(
    scenario: dict[str, Any],
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    cache_root: Path | None = None,
    report_dir: Path | None = None,
    fixture_path: Path | None = None,
) -> LiveEvalResult:
    """Run one turn with a real client; return pass/fail and violation strings."""
    sid = str(scenario.get("id", "unknown"))
    corpus_path = corpus_dir.resolve()
    out_report = _report_dir_from_kw_or_env(report_dir)
    user_message, input_violations = resolve_planner_user_message(scenario, corpus_path)
    if input_violations:
        _live_eval_log(
            "scenario_input_error",
            {"scenario_id": sid, "violations": input_violations},
            level=logging.WARNING,
        )
        return LiveEvalResult(sid, False, {"input": input_violations})
    if not user_message.strip():
        return LiveEvalResult(sid, False, {"input": [f"{_fail_prefix(sid)} empty user message"]})
    instructions, fp = load_or_build_planner_instructions(corpus_path, cache_root=cache_root)
    tools = _planner_tools_responses()
    tool_cost_sink: list[dict[str, Any]] = []
    dispatch = make_tool_dispatcher(
        corpus_path, client, model_id, statblock_stub=None, tool_cost_sink=tool_cost_sink
    )

    _live_eval_log(
        "scenario_start",
        {
            "scenario_id": sid,
            "model_id": model_id,
            "corpus_fingerprint": fp,
            "resolved_user_sig": text_sig(user_message),
            "resolved_user_text": maybe_full_text(user_message),
        },
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
            "suite": "planner_live_eval",
            "corpus_fingerprint": fp,
        },
    )
    statblock_usd = sum(float(x.get("total_usd", 0) or 0) for x in tool_cost_sink)
    tc = dict(detail.telemetry_cost or {})
    planner_usd = float(tc.get("planner_estimated_cost_usd", 0) or 0)
    tc["statblock_tool_estimated_cost_usd"] = round(statblock_usd, 6)
    tc["scenario_estimated_cost_usd"] = round(planner_usd + statblock_usd, 6)
    detail = replace(detail, telemetry_cost=tc)
    scenario_usd = tc["scenario_estimated_cost_usd"]
    result = evaluate_scenario_detail(
        scenario,
        detail,
        estimated_cost_usd=scenario_usd,
        corpus_fingerprint=fp,
    )
    report_written: str | None = None
    bench_payload: dict[str, Any] | None = None
    if out_report is not None:
        bench_payload = instrument_planner_answer(sid, detail.final_text or "", detail.tool_trace)
        md = render_planner_live_report_markdown(
            scenario_id=sid,
            model_id=model_id,
            corpus_fingerprint=fp,
            corpus_dir=str(corpus_path),
            fixture_filename=fixture_path.name if fixture_path else None,
            passed=result.passed,
            violations=result.violations,
            estimated_cost_usd=result.estimated_cost_usd,
            user_message=user_message,
            detail=detail,
            benchmark=bench_payload,
        )
        rp = write_planner_live_report(output_dir=out_report, scenario_id=sid, markdown_body=md)
        report_written = str(rp)
        if bench_payload is not None:
            safe = sid.replace("/", "_").replace("..", "_")
            bpath = (out_report / f"{safe}_benchmark.json").resolve()
            bpath.write_text(
                json.dumps(bench_payload, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )

    result = replace(result, report_path=report_written)

    end_payload: dict[str, Any] = {
        "scenario_id": sid,
        "passed": result.passed,
        "hit_tool_round_limit": detail.hit_tool_round_limit,
        "steps": len(detail.steps),
        "tool_trace_len": len(detail.tool_trace),
        "final_text_chars": len(detail.final_text),
        "estimated_cost_usd": scenario_usd,
        "planner_estimated_cost_usd": round(planner_usd, 6),
        "statblock_tool_estimated_cost_usd": round(statblock_usd, 6),
    }
    if report_written:
        end_payload["report_path"] = report_written
    if out_report is not None and bench_payload is not None:
        safe = sid.replace("/", "_").replace("..", "_")
        end_payload["benchmark_json_path"] = str((out_report / f"{safe}_benchmark.json").resolve())
    if not result.passed:
        end_payload["violations"] = result.violations
        end_payload["final_text_preview"] = maybe_full_text(detail.final_text)
        _live_eval_log("scenario_end", end_payload, level=logging.WARNING)
    else:
        _live_eval_log("scenario_end", end_payload)
    return result


def load_live_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_live_fixtures(fixtures_dir: Path) -> list[Path]:
    if not fixtures_dir.is_dir():
        return []
    return sorted(fixtures_dir.glob("*.json"))


def run_live_suite(
    *,
    corpus_dir: Path,
    client: Any,
    model_id: str,
    fixtures_dir: Path | None = None,
    cache_root: Path | None = None,
    report_dir: Path | None = None,
) -> tuple[list[LiveEvalResult], float]:
    """Run every ``*.json`` in ``fixtures_dir``; return results and pass rate."""
    root = fixtures_dir or (
        Path(__file__).resolve().parent / "live_fixtures"
    )
    paths = discover_live_fixtures(root)
    only_id = os.environ.get("PLANNER_LIVE_SCENARIO_ID", "").strip()
    if only_id:
        filtered: list[Path] = []
        for p in paths:
            try:
                if str(load_live_fixture(p).get("id", "")) == only_id:
                    filtered.append(p)
            except (OSError, json.JSONDecodeError):
                continue
        paths = filtered
    out_report = _report_dir_from_kw_or_env(report_dir)
    _, suite_fp = load_or_build_planner_instructions(corpus_dir.resolve(), cache_root=cache_root)
    _live_eval_log(
        "suite_start",
        {
            "fixture_count": len(paths),
            "fixtures": [p.name for p in paths],
            "model_id": model_id,
            "corpus_fingerprint": suite_fp,
            "report_dir": str(out_report) if out_report else None,
        },
    )
    results = [
        evaluate_live_scenario(
            load_live_fixture(p),
            corpus_dir=corpus_dir,
            client=client,
            model_id=model_id,
            cache_root=cache_root,
            report_dir=out_report,
            fixture_path=p,
        )
        for p in paths
    ]
    if not results:
        _live_eval_log("suite_end", {"pass_rate": 1.0, "note": "no fixtures"})
        return [], 1.0
    rate = sum(1 for r in results if r.passed) / len(results)
    suite_cost = sum((r.estimated_cost_usd or 0.0) for r in results)
    suite_payload: dict[str, Any] = {
        "pass_rate": rate,
        "suite_estimated_cost_usd": round(suite_cost, 6),
        "corpus_fingerprint": results[0].corpus_fingerprint or suite_fp,
        "results": [
            {
                "scenario_id": r.scenario_id,
                "passed": r.passed,
                "estimated_cost_usd": r.estimated_cost_usd,
                "report_path": r.report_path,
            }
            for r in results
        ],
    }
    if out_report is not None:
        rows: list[tuple[str, bool, str | None, float | None]] = []
        for r in results:
            name = Path(r.report_path).name if r.report_path else None
            rows.append((r.scenario_id, r.passed, name, r.estimated_cost_usd))
        idx_body = render_suite_index_markdown(
            model_id=model_id,
            corpus_dir=str(corpus_dir.resolve()),
            corpus_fingerprint=str(suite_payload["corpus_fingerprint"]),
            rows=rows,
        )
        idx_path = out_report / "SUITE_INDEX.md"
        idx_path.write_text(idx_body, encoding="utf-8")
        suite_payload["suite_index_path"] = str(idx_path)
    _live_eval_log("suite_end", suite_payload)
    return results, rate


def min_pass_rate_from_env() -> float:
    raw = os.environ.get("PLANNER_EVAL_MIN_PASS_RATE", "1.0").strip()
    try:
        v = float(raw)
    except ValueError:
        return 1.0
    return max(0.0, min(1.0, v))
