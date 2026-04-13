"""Human-readable Markdown reports for planner live eval runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.agent.planner import PlanningModelStepRecord, PlanningTurnDetail


def _fence_block(body: str, lang: str = "") -> str:
    fence = "```"
    while fence in body:
        fence += "`"
    head = f"{fence}{lang}".rstrip()
    return f"{head}\n{body}\n{fence}\n"


def _clip_user_message(text: str, max_chars: int = 80_000) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        text[:half]
        + f"\n\n… **truncated** ({len(text)} chars total; showing first/last {half} each) …\n\n"
        + text[-half:]
    )


def _fmt_json(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except TypeError:
        return repr(obj)[:20_000]


def _render_benchmark_section(bench: dict[str, Any]) -> list[str]:
    lines = [
        "## Benchmark instrumentation (citations + concepts)",
        "",
        "Manifest: `evals/planner_slice/benchmark/manifest.json`. "
        "**Citation grounding** compares `read_corpus_file` paths to `.md` citations in the final answer. "
        "**Concept coverage** scores manifest phrases with token bag + proximity + exact phrase (formatting-agnostic). "
        "Legacy **substring keyword** fraction is still logged for comparison. "
        "Optional embedding: set `PLANNER_BENCHMARK_EMBED=1` (diagnostic only; often saturated for planner prose).",
        "",
    ]
    qs = bench.get("quality_summary")
    if isinstance(qs, dict) and qs:
        lines.extend(_render_quality_summary_md(qs))
    if bench.get("error"):
        lines.append(f"_Exemplar error: `{bench['error']}`_")
        lines.append("")
        cg = bench.get("citation_grounding")
        if isinstance(cg, dict):
            lines.extend(_render_citation_grounding_md(cg))
        return lines
    lines.append(f"- **Exemplar file:** `{bench.get('exemplar_relpath', '')}`")
    lines.append(f"- **Exemplar chars:** {bench.get('exemplar_chars', '—')}")
    lines.append(f"- **Candidate chars:** {bench.get('candidate_chars', '—')}")
    dmin = bench.get("declared_min_keyword_fraction")
    if dmin is not None:
        lines.append(f"- **Declared min keyword fraction (substring legacy):** `{dmin}`")
    dmwc = bench.get("declared_min_weighted_concept_score")
    if dmwc is not None:
        lines.append(f"- **Declared min weighted concept score:** `{dmwc}`")
    dsc = bench.get("declared_saturation_cosine")
    if dsc is not None:
        lines.append(f"- **Declared saturation cosine (optional diagnostic):** `{dsc}`")
    dsk = bench.get("declared_saturation_keyword_fraction")
    if dsk is not None:
        lines.append(f"- **Declared saturation keyword fraction:** `{dsk}`")
    lines.append("")
    cg = bench.get("citation_grounding")
    if isinstance(cg, dict):
        lines.extend(_render_citation_grounding_md(cg))
    cc = bench.get("concept_coverage") or {}
    if cc.get("per_phrase") is not None:
        wscore = cc.get("weighted_score")
        lines.append(f"### Concept coverage (weighted score **{wscore}**)")
        lines.append("")
        lines.append(
            f"- **Phrases scored:** {cc.get('phrase_count', 0)} "
            f"(total weight `{cc.get('total_weight', '—')}`)"
        )
        weak = sorted(
            (p for p in (cc.get("per_phrase") or []) if isinstance(p, dict)),
            key=lambda x: float(x.get("score", 0) or 0),
        )[:12]
        if weak:
            lines.append("- **Lowest-scoring phrases:**")
            for p in weak:
                ph = str(p.get("phrase", "")).replace("|", "\\|")
                lines.append(
                    f"  - `{ph}` — score {p.get('score')} "
                    f"(bag {p.get('bag_fraction')}, proximity {p.get('proximity_match')}, "
                    f"exact {p.get('exact_substring')}, weight {p.get('weight', 1)})"
                )
        lines.append("")
    kw = bench.get("keyword_coverage") or {}
    frac = kw.get("fraction")
    lines.append(f"### Keyword coverage — substring legacy (fraction **{frac}**)")
    lines.append("")
    present = kw.get("present") or []
    missing = kw.get("missing") or []
    lines.append(f"- **Hits ({len(present)}):** {', '.join(f'`{p}`' for p in present[:40])}")
    if len(present) > 40:
        lines.append(f"- _… and {len(present) - 40} more_")
    lines.append(f"- **Misses ({len(missing)}):** {', '.join(f'`{m}`' for m in missing[:40])}")
    if len(missing) > 40:
        lines.append(f"- _… and {len(missing) - 40} more_")
    lines.append("")
    emb = bench.get("embedding")
    if emb:
        lines.append("### Embedding (optional diagnostic)")
        lines.append("")
        lines.append(_fence_block(_fmt_json(emb), "json"))
        lines.append("")
    return lines


def _render_quality_summary_md(qs: dict[str, Any]) -> list[str]:
    lines = [
        "### Quality summary (dimensions, not suite pass/fail)",
        "",
        "Use this block to **compare runs** and to separate **grounding** from **exemplar concept density**. "
        "Live-eval **PASS/FAIL** stays on fixture predicates; nothing here overrides that.",
        "",
    ]
    ca = qs.get("citation_alignment") or {}
    if ca.get("telemetry_available"):
        ok = ca.get("aligned")
        lines.append(
            f"- **Citation alignment:** {'OK' if ok else 'issues'} "
            f"(reads {ca.get('read_count', 0)}, cites {ca.get('citation_count', 0)}, "
            f"ungrounded cites {ca.get('citations_not_grounded_count', 0)}, "
            f"retrieved-not-echoed-in-prose {ca.get('reads_not_echoed_in_prose_count', 0)})"
        )
    else:
        lines.append("- **Citation alignment:** _no tool trace passed into benchmark instrumentation_")
    ec = qs.get("exemplar_concepts")
    if isinstance(ec, dict):
        lines.append(
            f"- **Exemplar-derived concepts:** weighted **{ec.get('weighted_score')}**, "
            f"mean phrase **{ec.get('mean_phrase_score')}**, "
            f"below 0.5: **{ec.get('phrases_scored_below_0_5')}** / {ec.get('phrase_count', 0)}"
        )
    elif qs.get("exemplar_available_for_concepts") is False:
        lines.append("- **Exemplar-derived concepts:** _skipped (exemplar file missing)_")
    leg = qs.get("legacy_substring_keywords")
    if isinstance(leg, dict) and leg.get("fraction") is not None:
        lines.append(
            f"- **Legacy substring keywords:** fraction **{leg.get('fraction')}** "
            f"({leg.get('hit_count')} hits / {leg.get('miss_count')} misses)"
        )
    emb = qs.get("embedding_diagnostic") or {}
    if emb.get("cosine_similarity") is not None:
        lines.append(f"- **Embedding (diagnostic):** cosine **{emb.get('cosine_similarity')}**")
    elif emb.get("skipped"):
        lines.append(f"- **Embedding:** skipped (`{emb.get('reason', '')}`)")
    else:
        lines.append("- **Embedding:** not computed (set `PLANNER_BENCHMARK_EMBED=1` to enable)")
    for note in qs.get("notes") or []:
        lines.append(f"- **Note:** {note}")
    lines.append("")
    return lines


def _render_citation_grounding_md(cg: dict[str, Any]) -> list[str]:
    lines = [
        "### Citation grounding",
        "",
        f"- **Reads (`read_corpus_file`, deduped):** {cg.get('read_count', 0)}",
        f"- **Citations extracted from final:** {cg.get('citation_count', 0)}",
        f"- **Citations not grounded in reads:** {len(cg.get('citations_not_grounded') or [])}",
        f"- **Retrieved paths not echoed in assistant prose:** {len(cg.get('reads_not_mentioned_in_final') or [])} _(diagnostic only)_",
        "",
    ]
    for label, key in (
        ("Reads", "reads"),
        ("Citations in final", "citations_in_final"),
        ("Not grounded", "citations_not_grounded"),
        ("Not echoed in prose (optional)", "reads_not_mentioned_in_final"),
    ):
        items = cg.get(key) or []
        if not items:
            continue
        clip = items[:8]
        lines.append(f"**{label}** (up to 8):")
        for p in clip:
            ps = str(p).replace("|", "\\|")
            lines.append(f"- `{ps}`")
        if len(items) > 8:
            lines.append(f"- _… and {len(items) - 8} more (see JSON sidecar)_")
        lines.append("")
    return lines


def _render_retrieved_corpus_reads_md(tool_trace: list[dict[str, Any]]) -> list[str]:
    # Lazy import: live_eval imports this module; avoid import cycle at load time.
    from evals.planner_slice.live_eval import dedupe_read_paths_preserve_order, read_paths_from_tool_trace

    paths = dedupe_read_paths_preserve_order(read_paths_from_tool_trace(tool_trace))
    lines = [
        "## Corpus files retrieved (`read_corpus_file`)",
        "",
        "Authoritative list for this turn (deduplicated, opening order preserved). "
        "Does not depend on the model listing sources in the assistant reply.",
        "",
    ]
    if not paths:
        lines.append("_No corpus reads in tool trace._")
        lines.append("")
        return lines
    for p in paths:
        ps = str(p).replace("|", "\\|")
        lines.append(f"- `{ps}`")
    lines.append("")
    return lines


def render_planner_live_report_markdown(
    *,
    scenario_id: str,
    model_id: str,
    corpus_fingerprint: str,
    corpus_dir: str,
    fixture_filename: str | None,
    passed: bool,
    violations: dict[str, list[str]],
    estimated_cost_usd: float | None,
    user_message: str,
    detail: PlanningTurnDetail,
    benchmark: dict[str, Any] | None = None,
) -> str:
    """Build a single Markdown document for one scenario (easy to skim in an editor or GitHub)."""
    lines: list[str] = [
        f"# Planner live eval — `{scenario_id}`",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| **Result** | **{'PASS' if passed else 'FAIL'}** |",
        f"| Model | `{model_id}` |",
        f"| Corpus fingerprint | `{corpus_fingerprint}` |",
        f"| Corpus directory | `{corpus_dir}` |",
    ]
    if fixture_filename:
        lines.append(f"| Fixture file | `{fixture_filename}` |")
    if estimated_cost_usd is not None:
        lines.append(f"| Est. cost (USD) | `{estimated_cost_usd:.6f}` |")
    tc = detail.telemetry_cost or {}
    ut = tc.get("planner_usage_totals") or {}
    if ut:
        lines.append(
            f"| Token usage (planner) | in {ut.get('input_tokens', 0):,} · "
            f"out {ut.get('output_tokens', 0):,} · cached {ut.get('cached_tokens', 0):,} |"
        )
    stb = tc.get("statblock_tool_estimated_cost_usd")
    if stb is not None and float(stb or 0) > 0:
        lines.append(f"| Statblock tool est. (USD) | `{float(stb):.6f}` |")
    lines.append(f"| Model responses (`steps`) | {len(detail.steps)} |")
    lines.append(f"| Tool executions | {len(detail.tool_trace)} |")
    lines.append(f"| Hit tool round limit | {detail.hit_tool_round_limit} |")
    lines.append("")

    if violations:
        lines.extend(["## Violations", ""])
        for bucket, msgs in sorted(violations.items()):
            lines.append(f"### `{bucket}`")
            for m in msgs:
                lines.append(f"- {m}")
            lines.append("")
    else:
        lines.extend(["## Violations", "", "_None._", ""])

    lines.extend(
        [
            "## Resolved user message",
            "",
            "Input sent to the planner (prior session block + planning ask, or full `user_message`).",
            "",
            _fence_block(_clip_user_message(user_message), "text"),
            "",
            "## Agent run — step-by-step",
            "",
        ]
    )

    trace_i = 0
    for si, step in enumerate(detail.steps):
        lines.extend(_render_model_step(si, step))
        n = len(step.function_calls)
        consumed = _render_tool_results_for_calls(detail.tool_trace, trace_i, n)
        lines.extend(consumed.lines)
        trace_i = consumed.next_index

    if trace_i < len(detail.tool_trace):
        lines.append("### Unattached tool rows (unexpected)")
        lines.append("")
        for row in detail.tool_trace[trace_i:]:
            lines.extend(_tool_trace_row_md(row))
        lines.append("")

    lines.extend(
        [
            "## Tool trace (ordered)",
            "",
        ]
    )
    if not detail.tool_trace:
        lines.append("_No tools executed._")
    else:
        for i, row in enumerate(detail.tool_trace, start=1):
            lines.append(f"{i}. **`{row.get('tool', '')}`** — {_tool_one_liner(row)}")
            args = row.get("arguments")
            if isinstance(args, dict) and args:
                lines.append("")
                lines.append(_fence_block(_fmt_json(args), "json"))
            lines.append("")

    lines.extend(
        [
            "## Final output (assistant reply)",
            "",
            "Full last model message for this turn (what you would show a reviewer).",
            "",
        ]
    )
    final = detail.final_text.strip() or "_(empty)_"
    lines.append(_fence_block(final, "markdown"))
    lines.append("")
    lines.extend(_render_retrieved_corpus_reads_md(detail.tool_trace))
    if benchmark:
        lines.extend(_render_benchmark_section(benchmark))
    return "\n".join(lines)


def _tool_one_liner(row: dict[str, Any]) -> str:
    oc = row.get("output_chars")
    parts = []
    if isinstance(oc, int):
        parts.append(f"{oc:,} chars returned")
    ex = row.get("output_excerpt")
    if isinstance(ex, str) and ex.strip():
        parts.append("excerpt below")
    return ", ".join(parts) if parts else "see arguments / excerpt"


def _tool_trace_row_md(row: dict[str, Any]) -> list[str]:
    out: list[str] = [f"- **`{row.get('tool', '')}`** — {_tool_one_liner(row)}"]
    args = row.get("arguments")
    if isinstance(args, dict) and args:
        out.append("")
        out.append(_fence_block(_fmt_json(args), "json"))
    ex = row.get("output_excerpt")
    if isinstance(ex, str) and ex.strip():
        out.append("")
        out.append("**Excerpt:**")
        out.append("")
        out.append(_fence_block(ex[:12_000], "text"))
    out.append("")
    return out


def _render_model_step(si: int, step: PlanningModelStepRecord) -> list[str]:
    lines = [
        f"### Round {si} — model response",
        "",
        f"- **Response id:** `{step.response_id}`",
        "",
    ]
    text = (step.assistant_text or "").strip()
    if text:
        lines.extend(["**Assistant text (same round, before tools):**", "", _fence_block(text, "markdown"), ""])
    else:
        lines.extend(["_No assistant prose this round (tool calls only)._", ""])

    if not step.function_calls:
        lines.append("_No function calls._")
        lines.append("")
        return lines

    lines.append("**Function calls:**")
    lines.append("")
    lines.append("| # | Tool | Arguments |")
    lines.append("| --- | --- | --- |")
    for ci, call in enumerate(step.function_calls, start=1):
        name = str(call.get("name", ""))
        args = call.get("arguments")
        arg_cell = _fmt_json(args) if isinstance(args, dict) else repr(args)
        arg_cell = arg_cell.replace("|", "\\|").replace("\n", "<br>")
        if len(arg_cell) > 600:
            arg_cell = arg_cell[:597] + "…"
        lines.append(f"| {ci} | `{name}` | {arg_cell} |")
    lines.append("")
    return lines


class _Consumed:
    __slots__ = ("lines", "next_index")

    def __init__(self, lines: list[str], next_index: int) -> None:
        self.lines = lines
        self.next_index = next_index


def _render_tool_results_for_calls(
    tool_trace: list[dict[str, Any]],
    start: int,
    num_calls: int,
) -> _Consumed:
    lines: list[str] = []
    if num_calls == 0:
        return _Consumed(lines, start)
    lines.append(f"#### Tool results (next `{num_calls}` execution(s))")
    lines.append("")
    idx = start
    for j in range(num_calls):
        if idx >= len(tool_trace):
            lines.append(f"- _(missing tool_trace row for call {j + 1})_")
            continue
        row = tool_trace[idx]
        lines.append(f"**{j + 1}.** `{row.get('tool', '')}`")
        args = row.get("arguments")
        if isinstance(args, dict) and args:
            lines.append("")
            lines.append(_fence_block(_fmt_json(args), "json"))
        ex = row.get("output_excerpt")
        oc = row.get("output_chars")
        if isinstance(oc, int):
            lines.append("")
            lines.append(f"_Returned **{oc:,}** characters._")
        if isinstance(ex, str) and ex.strip():
            lines.append("")
            lines.append("**Excerpt (first 800 chars of tool output; full text was in model context):**")
            lines.append("")
            lines.append(_fence_block(ex[:12_000], "text"))
        lines.append("")
        idx += 1
    return _Consumed(lines, idx)


def render_suite_index_markdown(
    *,
    model_id: str,
    corpus_dir: str,
    corpus_fingerprint: str,
    rows: list[tuple[str, bool, str | None, float | None]],
) -> str:
    """
    ``rows``: ``(scenario_id, passed, report_filename_or_none, estimated_cost_usd)`` per scenario.
    """
    lines = [
        "# Planner live eval — suite summary",
        "",
        "## Run",
        "",
        f"- **Model:** `{model_id}`",
        f"- **Corpus:** `{corpus_dir}`",
        f"- **Fingerprint:** `{corpus_fingerprint}`",
        "",
        "## Scenarios",
        "",
        "| Scenario | Pass | Est. USD | Report |",
        "| --- | --- | --- | --- |",
    ]
    for sid, ok, rep, usd in rows:
        usd_s = f"{usd:.6f}" if usd is not None else "—"
        link = f"[{rep}]({rep})" if rep else "—"
        lines.append(f"| `{sid}` | {'PASS' if ok else 'FAIL'} | {usd_s} | {link} |")
    lines.append("")
    return "\n".join(lines)


def write_planner_live_report(
    *,
    output_dir: Path,
    scenario_id: str,
    markdown_body: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = scenario_id.replace("/", "_").replace("..", "_")
    path = (output_dir / f"{safe}.md").resolve()
    path.write_text(markdown_body, encoding="utf-8")
    return path
