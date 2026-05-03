"""Generate breadcrumb query review canvas data from benchmark report artifacts.

The breadcrumb query semantic review canvas is rendered from an inline
``canvasData`` block. This module is the single producer of that block —
everything dynamic (pass counts, costs, scenario rows, recovered/missed
evidence) is derived deterministically from the LLM benchmark report
(``breadcrumb_query_run.py`` output) plus the gold scenario file, with
optional baseline and deterministic reports for comparison.

Usage (refresh after a benchmark run):

    uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload \\
        --report evals/.../breadcrumb_query_natural_llm_semantic_expanded_report.json \\
        --deterministic-report evals/.../breadcrumb_query_natural_expanded_deterministic_report.json \\
        --canvas-tsx /home/.../canvases/breadcrumb-query-semantic-review.canvas.tsx

Pass ``--check`` to verify the canvas generated block is up to date without
mutating the file (exits non-zero if regenerating would change the canvas).

Maintenance rules:
    - Do not hand-edit the region between ``BEGIN GENERATED
      BREADCRUMB_QUERY_CANVAS_DATA`` and ``END GENERATED
      BREADCRUMB_QUERY_CANVAS_DATA``. Rerun this module instead.
    - When adding new report fields, update :func:`build_payload` and the
      tests in ``tests/test_breadcrumb_query_canvas_payload.py`` together.
    - The static structural rows (architecture, prompt prose, entity index,
      record index, suite focus) live as constants in this module so the
      canvas TSX file imports nothing and remains a single self-contained
      file (Cursor canvas constraint).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PAYLOAD_SCHEMA = "breadcrumb_query_canvas_payload_v1"
CANVAS_BLOCK_BEGIN = "// BEGIN GENERATED BREADCRUMB_QUERY_CANVAS_DATA"
CANVAS_BLOCK_END = "// END GENERATED BREADCRUMB_QUERY_CANVAS_DATA"

# ---------------------------------------------------------------------------
# Static structural rows. These describe the benchmark architecture, the
# constructed retrieval index, and the LLM prompt surfaces. They are not
# derived from any specific run; they describe the suite itself.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_DEFAULT = (
    "You are assisting a tabletop RPG GM. Answer the question using ONLY the evidence in the retrieved "
    "excerpts and corpus route lines below. If the excerpts do not support a confident answer, say what is "
    "missing. Stay concise (roughly 3-8 sentences). Do not invent specifics that are not grounded in the "
    "excerpts."
)

USER_PROMPT_TEMPLATE_DEFAULT = (
    "Question:\\n{scenario.question}\\n\\n### Retrieved excerpts and routes (only source you may use)\\n"
    "{hit_context}"
)

EMBEDDING_INPUT_DEFAULT = (
    "For each scenario, embed [expected_answer, llm_answer] with text-embedding-3-large and record cosine "
    "similarity. This is a diagnostic similarity score only. It does not override route, unit, token, or "
    "negation gates."
)

ARCHITECTURE_ROWS_DEFAULT: list[list[str]] = [
    [
        "1",
        "Gold scenario",
        "Natural question, expected_answer, required tokens, expected routes, optional expected unit ids, and negation guards.",
    ],
    [
        "2",
        "Candidate retrieval",
        (
            "Normalize Session 20 breadcrumbs into source-anchored records; lexical + route-token first pass; "
            "optional second-pass expansion (adjacency on same recap slice, shared exact routes from seeds, "
            "route prefix/sibling families in-session) filling remaining slots up to max_hits; gold records "
            "expand_context + expand_first_pass_cap in default_query_spec."
        ),
    ],
    [
        "3",
        "LLM synthesis",
        "Send only the question plus retrieved hit context. No gold tokens or expected answer are passed to the model.",
    ],
    [
        "4",
        "Hard grading",
        "Check expected route recall, expected unit recall, token support, stale/negated token guards, and LLM answer support ratio.",
    ],
    [
        "5",
        "Embedding diagnostic",
        "Compare expected_answer to actual output with text-embedding-3-large. Similarity is reported, not used as pass/fail.",
    ],
]

PROMOTION_BLOCKERS_DEFAULT: list[list[str]] = [
    [
        "Deferred row is policy-shaped",
        "q_timeline_vs_recap asks which facts belong in timelines vs recap-only context. The current LLM prompt can only answer from retrieved excerpts, so it cannot grade project write policy honestly.",
    ],
    [
        "Needs a separate grader",
        "To make it executable, add a write-destination benchmark with policy inputs: subject type, durable-state criteria, recap-only texture criteria, and expected target artifact class.",
    ],
    [
        "Twelve rows are now executable",
        "The other review rows now live in breadcrumb_query_natural_v1.json with expected answers, route/unit expectations, must-hit tokens, thresholds, and default_query_spec expansion knobs for the falsification harness.",
    ],
]

ENTITY_INDEX_ROWS_DEFAULT: list[list[str]] = [
    ["Party", "questionable_company", "Longmont Campaign/Campaign 2/Parties/questionable_company/", "proposed party hub; collective actor only"],
    ["PCs", "baergrom, bonogo, caelynn, ephanna, karsemine, stafl", "Longmont Campaign/Campaign 2/PCs/<slug>/", "6 roster slugs; Baergrom not named directly"],
    ["NPC", "captain_lysandra_ironveil", "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/", "existing route"],
    ["NPC", "sara_mirathorn_operator", "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/", "existing route"],
    ["NPCs", "marla, stacey, stuart, sheriff, thrin", "Mossford / C2 NPC hub routes", "existing routes"],
    ["Location", "mirathorn", "Elderwyld/Cities and Towns/Mirathorn/", "existing route"],
    ["Location", "stormspire_academy", "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/", "existing route"],
    ["Location", "mossford, migrating_forest", "Elderwyld/Cities and Towns/Mossford/; Elderwyld/Migrating Forest/", "existing routes"],
    ["NewHubCandidate", "professor_merril_tealeaf", "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/", "not a committed hub yet"],
    ["NewHubCandidate", "voices_tower_blueprint", "Elderwyld/Unknown Sites/Voices Tower/", "not a committed hub yet"],
    ["NewHubCandidate", "half_burned_warehouse", "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md", "not a committed hub yet"],
]

# Suite focus is hand-curated review framing per scenario id. If a scenario id is not
# listed here, the canvas falls back to the gold ``notes`` field.
SUITE_FOCUS_DEFAULT: dict[str, dict[str, str]] = {
    "nat_captain_after_forest": {
        "status": "Executable",
        "focus": "Lysandra after forest retreat; Sara relay; spell/tea recovery; fragmented memory; tower clue.",
    },
    "nat_mirathorn_threads": {
        "status": "Executable",
        "focus": "Sara, Mirathorn, Tealeaf/Stormspire, tainted meat, trust concern in the city.",
    },
    "nat_voices_tower_officer": {
        "status": "Executable",
        "focus": "Lysandra, voices, tower, drawing in dirt, top-down blueprint, shimmery eyes, tea recovery.",
    },
    "q_lysandra_change_unresolved": {
        "status": "Executable",
        "focus": "State change plus unresolved tower/voices, cult-like shimmer, tainted meat, Tealeaf non-response, storm.",
    },
    "q_lysandra_regroups": {
        "status": "Executable",
        "focus": "Tracked to wagon camp; drawing/voices; shimmer eyes; antidote tea; disorientation; camp setup.",
    },
    "q_relevant_locations": {
        "status": "Executable",
        "focus": "Mossford, migrating forest, field fortifications, Lysandra wagon camp, Mirathorn, tower clue.",
    },
    "q_communication_chain": {
        "status": "Executable",
        "focus": "Caelynn uses rockie-talkie; Sara relays/patches Lysandra; later Sara tries Tealeaf and gets no answer.",
    },
    "q_lysandra_memory_contrast": {
        "status": "Executable",
        "focus": "Remembers fragments: voices, forest/time oddness, meat smell; cannot explain where/how she arrived.",
    },
    "q_mirathorn_vs_mossford": {
        "status": "Executable",
        "focus": "Mirathorn: comms, Sara, Tealeaf, tainted supply trust. Mossford: defense, townsfolk, social aftermath.",
    },
    "q_tower_knowns": {
        "status": "Executable",
        "focus": "Voices source; Lysandra says she knows where it is; drawing/blueprint; route is still a new-site candidate.",
    },
    "q_party_learned_next_prep": {
        "status": "Executable",
        "focus": "Forest responds to ground changes/ditch fires; tainted meat; Lysandra condition; storm and magical rain.",
    },
    "q_open_loops_next_session": {
        "status": "Executable",
        "focus": "Tower/voices, Lysandra follow-up, Tealeaf/Sara trust thread, storm shelter, Ephanna supply run.",
    },
    "q_timeline_vs_recap": {
        "status": "Deferred",
        "focus": "Still review-only: this asks write-policy judgement, not retrieval-only corpus recall.",
        "question": "Which recovered details should be written into subject timelines, and which should remain recap-only context?",
    },
}

# Order in which suite rows appear in the canvas. Entries not present in gold (the
# deferred policy row in particular) still render via SUITE_FOCUS_DEFAULT fallback.
SUITE_ROW_ORDER: list[str] = [
    "nat_captain_after_forest",
    "nat_mirathorn_threads",
    "nat_voices_tower_officer",
    "q_lysandra_change_unresolved",
    "q_lysandra_regroups",
    "q_relevant_locations",
    "q_communication_chain",
    "q_lysandra_memory_contrast",
    "q_mirathorn_vs_mossford",
    "q_tower_knowns",
    "q_party_learned_next_prep",
    "q_open_loops_next_session",
    "q_timeline_vs_recap",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_records_text(report: dict[str, Any], override: Path | None) -> dict[str, str]:
    """Build ``unit_id -> lexical_plain`` map from the records JSONL referenced by the report."""
    src: Path | None = override
    if src is None:
        rs = report.get("records_source")
        if rs:
            candidate = Path(str(rs))
            if candidate.is_file():
                src = candidate
    if src is None or not src.is_file():
        return {}
    out: dict[str, str] = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        uid = str(row.get("unit_id") or "").strip()
        text = str(row.get("lexical_plain") or "").strip()
        if uid:
            out[uid] = text
    return out


def _route_tail(route: str) -> str:
    s = (route or "").rstrip("/")
    if not s:
        return ""
    if "/" not in s:
        return s
    return s.rsplit("/", 1)[-1]


def _format_routes(routes: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for r in routes or []:
        nr = str(r.get("normalized_route") or "")
        tail = _route_tail(nr) or nr.strip("/")
        if not tail or tail in seen:
            continue
        seen.add(tail)
        parts.append(tail)
    return "; ".join(parts)


def _hits_unit_ids(hits: list[dict[str, Any]] | None) -> list[str]:
    return [str(h.get("unit_id") or "") for h in (hits or [])]


def _hits_route_blob(hits: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for h in hits or []:
        for r in h.get("routes") or []:
            nr = str(r.get("normalized_route") or "")
            if nr:
                parts.append(nr)
    return "\n".join(parts).lower()


def _missing_units(expected: list[str], hits: list[dict[str, Any]] | None) -> list[str]:
    uids = _hits_unit_ids(hits)
    return [s for s in expected if not any(s in u for u in uids)]


def _missing_routes(expected: list[str], hits: list[dict[str, Any]] | None) -> list[str]:
    blob = _hits_route_blob(hits)
    return [s for s in expected if s.lower() not in blob]


def _ratio_label(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def _embedding_label(row: dict[str, Any]) -> str:
    emb = row.get("embedding_similarity") or {}
    cos = emb.get("cosine_similarity")
    if cos is None:
        return "n/a"
    try:
        return f"{float(cos):.4f}"
    except (TypeError, ValueError):
        return "n/a"


def _row_by_id(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in report.get("results") or []:
        sid = str(r.get("scenario_id") or "")
        if sid:
            out[sid] = r
    return out


# ---------------------------------------------------------------------------
# Per-scenario card / deep-dive derivation
# ---------------------------------------------------------------------------


def _build_required_evidence(scenario: dict[str, Any]) -> list[str]:
    out: list[str] = []
    must = scenario.get("must_hit_tokens") or []
    if must:
        out.append("Tokens: " + ", ".join(str(x) for x in must))
    units = scenario.get("expect_unit_id_substrings") or []
    if units:
        out.append("Expected units: " + ", ".join(str(x) for x in units))
    routes = scenario.get("expect_route_substrings") or []
    if routes:
        out.append("Routes: " + ", ".join(str(x) for x in routes))
    min_ratio = scenario.get("min_context_support_ratio")
    if min_ratio is not None:
        try:
            out.append(f"Minimum support ratio: {float(min_ratio):.2f}")
        except (TypeError, ValueError):
            pass
    must_not = scenario.get("must_not_cooccur") or {}
    if must_not:
        out.append("Negation guards: " + ", ".join(sorted(str(k) for k in must_not.keys())))
    return out


def _build_retrieved_hits(
    hits: list[dict[str, Any]],
    records_text: dict[str, str],
    *,
    limit: int = 5,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for idx, h in enumerate(hits[:limit], start=1):
        unit = str(h.get("unit_id") or "")
        score = h.get("score")
        out.append(
            {
                "rank": str(idx),
                "unit": unit,
                "score": "" if score is None else str(score),
                "text": records_text.get(unit, ""),
                "routes": _format_routes(h.get("routes") or []),
            }
        )
    return out


def _critique(
    *,
    verdict: str,
    violations: list[str],
    missing_units: list[str],
    missing_routes: list[str],
    recovered_units: list[str],
    recovered_routes: list[str],
) -> str:
    parts: list[str] = []
    if verdict == "PASS":
        parts.append("Hard gates pass.")
    else:
        if violations:
            parts.append("Violations: " + "; ".join(violations) + ".")
        if missing_units:
            parts.append("Missing expected units: " + ", ".join(missing_units) + ".")
        if missing_routes:
            parts.append("Missing expected routes: " + ", ".join(missing_routes) + ".")
        if not parts:
            parts.append("Failed soft gates only; review LLM support and embedding similarity.")
    if recovered_units:
        parts.append("Recovered units vs baseline: " + ", ".join(recovered_units) + ".")
    if recovered_routes:
        parts.append("Recovered routes vs baseline: " + ", ".join(recovered_routes) + ".")
    return " ".join(parts)


def _build_scenario_card(
    *,
    scenario: dict[str, Any],
    row: dict[str, Any],
    baseline_row: dict[str, Any] | None,
    records_text: dict[str, str],
) -> dict[str, Any]:
    full_result = row.get("full_result") or {}
    hits = list(full_result.get("hits") or [])
    expected_units = [str(x) for x in (scenario.get("expect_unit_id_substrings") or [])]
    expected_routes = [str(x) for x in (scenario.get("expect_route_substrings") or [])]

    missing_units_now = _missing_units(expected_units, hits)
    missing_routes_now = _missing_routes(expected_routes, hits)

    baseline_hits = (baseline_row or {}).get("full_result", {}).get("hits") if baseline_row else None
    baseline_missing_units = (
        _missing_units(expected_units, baseline_hits) if baseline_row is not None else None
    )
    baseline_missing_routes = (
        _missing_routes(expected_routes, baseline_hits) if baseline_row is not None else None
    )
    recovered_units = (
        [u for u in (baseline_missing_units or []) if u not in missing_units_now]
        if baseline_missing_units is not None
        else []
    )
    recovered_routes = (
        [r for r in (baseline_missing_routes or []) if r not in missing_routes_now]
        if baseline_missing_routes is not None
        else []
    )

    top_hit = row.get("top_hit") or {}
    top_unit = str(top_hit.get("unit_id") or "")
    top_score = top_hit.get("score")
    top_label = (
        f"{top_unit}, score {top_score}" if top_unit and top_score is not None else top_unit
    )

    llm_usage = row.get("llm_usage") or {}
    in_tok = llm_usage.get("input_tokens") or 0
    out_tok = llm_usage.get("output_tokens") or 0
    tokens_label = f"{in_tok} in / {out_tok} out"

    cost = row.get("llm_cost_usd")
    cost_label = (
        f"${float(cost):.8f}" if isinstance(cost, (int, float)) and cost is not None else "n/a"
    )

    verdict = "PASS" if row.get("ok") else "FAIL"
    tone = "success" if verdict == "PASS" else "warning"
    violations = [str(v) for v in (row.get("violations") or [])]

    answer_preview = str(row.get("llm_answer_preview") or row.get("hit_context_preview") or "")
    expected_gold = str(scenario.get("expected_answer") or "")

    missing_expected: list[str] = []
    for u in missing_units_now:
        text = records_text.get(u, "")
        suffix = f" — {text}" if text else ""
        missing_expected.append(f"Missing expected unit: {u}{suffix}")
    for r in missing_routes_now:
        missing_expected.append(f"Missing expected route hit: {r}")
    if not missing_expected:
        missing_expected.append("None: expected routes and units were present in the top hits.")
    if recovered_units or recovered_routes:
        rec: list[str] = []
        if recovered_units:
            rec.append("units " + ", ".join(recovered_units))
        if recovered_routes:
            rec.append("routes " + ", ".join(recovered_routes))
        missing_expected.append("Recovered vs baseline: " + "; ".join(rec))

    card = {
        "id": str(row.get("scenario_id") or ""),
        "verdict": verdict,
        "tone": tone,
        "query": str(scenario.get("question") or ""),
        "expectedGold": expected_gold,
        "requiredEvidence": _build_required_evidence(scenario),
        "violations": violations,
        "actualOutput": answer_preview,
        "retrievedHits": _build_retrieved_hits(hits, records_text),
        "metrics": {
            "retrievalSupport": _ratio_label(row.get("context_support_ratio")),
            "llmSupport": _ratio_label(row.get("llm_context_support_ratio")),
            "embeddingSimilarity": _embedding_label(row),
            "topHit": top_label,
            "hitCount": str(row.get("hit_count") or len(hits)),
            "tokens": tokens_label,
            "llmCost": cost_label,
        },
        "missingExpected": missing_expected,
        "critique": _critique(
            verdict=verdict,
            violations=violations,
            missing_units=missing_units_now,
            missing_routes=missing_routes_now,
            recovered_units=recovered_units,
            recovered_routes=recovered_routes,
        ),
    }

    return card


# ---------------------------------------------------------------------------
# Top-level summary / suite / run rows
# ---------------------------------------------------------------------------


def _summary(
    *,
    report: dict[str, Any],
    gold: dict[str, Any],
    deterministic: dict[str, Any] | None,
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    results = list(report.get("results") or [])
    pass_count = sum(1 for r in results if r.get("ok"))
    total = len(results)
    fail_count = total - pass_count

    deterministic_pass: int | None = None
    deterministic_total: int | None = None
    if deterministic is not None:
        det_results = list(deterministic.get("results") or [])
        deterministic_pass = sum(1 for r in det_results if r.get("ok"))
        deterministic_total = len(det_results)

    baseline_pass: int | None = None
    baseline_total: int | None = None
    if baseline is not None:
        base_results = list(baseline.get("results") or [])
        baseline_pass = sum(1 for r in base_results if r.get("ok"))
        baseline_total = len(base_results)

    spec = dict(gold.get("default_query_spec") or {})
    expand_first_pass_cap = spec.get("expand_first_pass_cap")
    max_hits = int(spec.get("max_hits") or 12)
    expand_enabled = bool(spec.get("expand_context"))

    if expand_enabled and isinstance(expand_first_pass_cap, int):
        slots = max_hits - int(expand_first_pass_cap)
        expansion_label = (
            f"{int(expand_first_pass_cap)} lexical + {slots} expansion slots"
            if slots > 0
            else f"{int(expand_first_pass_cap)} lexical hits, expansion enabled"
        )
    else:
        expansion_label = f"{max_hits} lexical hits"

    cost = report.get("scenario_estimated_cost_usd") or report.get("aggregate_llm_cost_usd")
    cost_label = (
        f"${float(cost):.4f}" if isinstance(cost, (int, float)) and cost is not None else "n/a"
    )

    summary: dict[str, Any] = {
        "executableCount": total,
        "deferredCount": _count_deferred(gold),
        "llmPassCount": pass_count,
        "llmFailCount": fail_count,
        "llmPassLabel": f"{pass_count}/{total}" if total else "0/0",
        "deterministicPassCount": deterministic_pass,
        "deterministicTotal": deterministic_total,
        "deterministicPassLabel": (
            f"{deterministic_pass}/{deterministic_total}"
            if deterministic_pass is not None and deterministic_total is not None
            else None
        ),
        "baselinePassCount": baseline_pass,
        "baselineTotal": baseline_total,
        "baselinePassLabel": (
            f"{baseline_pass}/{baseline_total}"
            if baseline_pass is not None and baseline_total is not None
            else None
        ),
        "maxHits": max_hits,
        "expandEnabled": expand_enabled,
        "expandFirstPassCap": expand_first_pass_cap if expand_enabled else None,
        "expansionLabel": expansion_label,
        "scenarioEstimatedCostUsd": cost,
        "costLabel": cost_label,
        "aggregateLlmCostUsd": report.get("aggregate_llm_cost_usd"),
        "aggregateEmbeddingCostUsd": report.get("aggregate_embedding_cost_usd"),
        "llmModel": report.get("llm_model"),
        "embeddingModel": report.get("embedding_model"),
    }

    pass_tone = "success" if total and pass_count == total else "warning"
    pass_label = "Hard-gate pass" + (" (expanded)" if expand_enabled else "")
    summary["statTiles"] = [
        {"label": pass_label, "value": summary["llmPassLabel"], "tone": pass_tone},
        {"label": "Executable rows", "value": str(total)},
        {"label": "Deferred policy row", "value": str(summary["deferredCount"])},
        {"label": f"Max hits ({expansion_label})", "value": str(max_hits)},
        {"label": "LLM + embed cost", "value": cost_label},
    ]
    return summary


def _count_deferred(_gold: dict[str, Any]) -> int:
    return sum(
        1
        for sid in SUITE_ROW_ORDER
        if str((SUITE_FOCUS_DEFAULT.get(sid) or {}).get("status", "")).lower() == "deferred"
    )


def _build_suite_rows(gold: dict[str, Any]) -> list[list[str]]:
    """Render the canonical suite list, merging gold questions where available.

    Order is fixed by ``SUITE_ROW_ORDER`` so the deferred policy row remains visible
    even when it is intentionally absent from the executable gold file.
    """
    questions_by_id: dict[str, str] = {
        str(s.get("id") or ""): str(s.get("question") or "")
        for s in (gold.get("scenarios") or [])
    }
    rows: list[list[str]] = []
    for sid in SUITE_ROW_ORDER:
        focus_meta = SUITE_FOCUS_DEFAULT.get(sid) or {}
        question = questions_by_id.get(sid) or str(focus_meta.get("question") or "")
        rows.append(
            [
                str(focus_meta.get("status") or "Executable"),
                sid,
                question,
                str(focus_meta.get("focus") or ""),
            ]
        )
    return rows


def _build_run_rows(report: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for r in report.get("results") or []:
        verdict = "PASS" if r.get("ok") else "FAIL"
        violations = [str(v) for v in (r.get("violations") or [])]
        rows.append(
            [
                str(r.get("scenario_id") or ""),
                verdict,
                _ratio_label(r.get("context_support_ratio")),
                _ratio_label(r.get("llm_context_support_ratio")),
                _embedding_label(r),
                str((r.get("top_hit") or {}).get("unit_id") or ""),
                "; ".join(violations) if violations else "none",
            ]
        )
    return rows


def _build_callouts(summary: dict[str, Any], baseline: dict[str, Any] | None) -> list[dict[str, str]]:
    callouts: list[dict[str, str]] = []
    if summary.get("expandEnabled"):
        cap = summary.get("expandFirstPassCap")
        max_hits = summary.get("maxHits")
        slots = (
            int(max_hits) - int(cap)
            if isinstance(cap, int) and isinstance(max_hits, int)
            else None
        )
        det_label = summary.get("deterministicPassLabel") or "not measured this run"
        baseline_label = summary.get("baselinePassLabel")
        cap_part = (
            f"expand_first_pass_cap={cap} so {slots} slot(s) fill via adjacency / shared-route / "
            f"route-family signals after the top {cap} lexical hits"
            if isinstance(cap, int) and isinstance(slots, int) and slots > 0
            else "expand_context with default expansion budget"
        )
        body = (
            f"Promoted natural gold sets {cap_part}. "
            f"Deterministic retrieval-only pass is {det_label}. "
            f"LLM+embedding hard-gate pass is {summary['llmPassLabel']}."
        )
        if baseline_label:
            body += f" Baseline (pre-expansion) was {baseline_label}."
        callouts.append({"tone": "neutral", "title": "Two-step retrieval expansion", "body": body})
    callouts.append(
        {
            "tone": "warning",
            "title": "Interpret similarity skeptically",
            "body": (
                "Embedding similarity is useful as a drift signal, but it is not an oracle. "
                "Failing rows can still score in the 0.7–0.85 band when topic vocabulary overlaps but "
                "gold-critical details are missing or negated. The executable query cards below carry "
                "the review details for all rows."
            ),
        }
    )
    return callouts


def _build_record_index_rows(records_text: dict[str, str]) -> list[list[str]]:
    """Static unit ids that anchor the canvas evidence narrative."""
    anchor_unit_ids = [
        "u-L0019-05",
        "u-L0019-06",
        "u-L0019-08",
        "u-L0019-10",
        "u-L0019-11",
        "u-L0021-03",
        "u-L0021-07",
        "u-L0021-08",
        "u-L0021-09",
        "u-L0023-01",
    ]
    rows: list[list[str]] = []
    for uid in anchor_unit_ids:
        text = records_text.get(uid, "")
        rows.append([uid, text or "(text unavailable; rebuild records_meta.jsonl)", ""])
    return rows


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------


def build_payload(
    *,
    report: dict[str, Any],
    gold: dict[str, Any],
    baseline: dict[str, Any] | None = None,
    deterministic: dict[str, Any] | None = None,
    records_text: dict[str, str] | None = None,
    report_path: str | None = None,
    gold_path: str | None = None,
    baseline_path: str | None = None,
    deterministic_path: str | None = None,
) -> dict[str, Any]:
    records_text = dict(records_text or {})
    summary = _summary(
        report=report,
        gold=gold,
        deterministic=deterministic,
        baseline=baseline,
    )

    scenarios_by_id = {str(s.get("id") or ""): s for s in (gold.get("scenarios") or [])}
    baseline_rows_by_id = _row_by_id(baseline)

    scenario_cards: list[dict[str, Any]] = []
    for row in report.get("results") or []:
        sid = str(row.get("scenario_id") or "")
        scen = scenarios_by_id.get(sid) or {"id": sid}
        baseline_row = baseline_rows_by_id.get(sid)
        scenario_cards.append(
            _build_scenario_card(
                scenario=scen,
                row=row,
                baseline_row=baseline_row,
                records_text=records_text,
            )
        )

    payload: dict[str, Any] = {
        "schema": PAYLOAD_SCHEMA,
        "sources": {
            "report": report_path,
            "gold": gold_path,
            "baselineReport": baseline_path,
            "deterministicReport": deterministic_path,
        },
        "title": "Breadcrumb Query Semantic Review",
        "subtitle": "Natural Session 20 breadcrumb benchmark with LLM synthesis and embedding similarity.",
        "sourceLabel": (
            f"Source artifact: {report_path}" if report_path else "Source artifact: (path unset)"
        ),
        "summary": summary,
        "callouts": _build_callouts(summary, baseline),
        "architectureRows": ARCHITECTURE_ROWS_DEFAULT,
        "suiteRows": _build_suite_rows(gold),
        "promotionBlockers": PROMOTION_BLOCKERS_DEFAULT,
        "runRows": _build_run_rows(report),
        "scenarioCards": scenario_cards,
        "entityIndexRows": ENTITY_INDEX_ROWS_DEFAULT,
        "recordIndexRows": _build_record_index_rows(records_text),
        "systemPrompt": SYSTEM_PROMPT_DEFAULT,
        "userPromptTemplate": USER_PROMPT_TEMPLATE_DEFAULT,
        "embeddingInput": EMBEDDING_INPUT_DEFAULT,
    }
    return payload


# ---------------------------------------------------------------------------
# Generated-block rendering / canvas update
# ---------------------------------------------------------------------------


def render_generated_block(payload: dict[str, Any]) -> str:
    """Render the canvas-ready generated block (TypeScript ``const canvasData``)."""
    json_text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)
    lines = [
        CANVAS_BLOCK_BEGIN,
        "// Auto-generated by",
        "// evals/sentence_routing_retrieval_falsification/breadcrumb_query_canvas_payload.py",
        "// Do not edit by hand. Refresh by rerunning the module against an updated report.",
        "// eslint-disable",
        f"const canvasData = {json_text} as const;",
        "type CanvasData = typeof canvasData;",
        CANVAS_BLOCK_END,
    ]
    return "\n".join(lines)


def update_canvas_text(canvas_text: str, generated_block: str) -> str:
    """Replace the generated block region in ``canvas_text`` with ``generated_block``."""
    if CANVAS_BLOCK_BEGIN not in canvas_text or CANVAS_BLOCK_END not in canvas_text:
        raise ValueError(
            "canvas is missing the generated-block markers "
            f"({CANVAS_BLOCK_BEGIN!r} / {CANVAS_BLOCK_END!r}); "
            "insert them once around the canvasData declaration and rerun."
        )
    start = canvas_text.index(CANVAS_BLOCK_BEGIN)
    end = canvas_text.index(CANVAS_BLOCK_END, start) + len(CANVAS_BLOCK_END)
    return canvas_text[:start] + generated_block + canvas_text[end:]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_gold_path(report: dict[str, Any], cli_value: Path | None) -> Path:
    if cli_value is not None:
        return cli_value
    raw = report.get("gold")
    if not raw:
        raise SystemExit("report.gold missing; pass --gold <path>")
    return Path(str(raw))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True, help="Benchmark report JSON (LLM+semantic).")
    parser.add_argument("--gold", type=Path, default=None, help="Gold scenarios JSON; defaults to report.gold.")
    parser.add_argument("--baseline-report", type=Path, default=None, help="Optional baseline (pre-change) report.")
    parser.add_argument(
        "--deterministic-report",
        type=Path,
        default=None,
        help="Optional deterministic-only report for the same gold and corpus.",
    )
    parser.add_argument(
        "--records-jsonl",
        type=Path,
        default=None,
        help="Override records JSONL (defaults to report.records_source).",
    )
    parser.add_argument(
        "--canvas-tsx",
        type=Path,
        required=True,
        help="Canvas .tsx file to refresh (must contain generated-block markers).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if regenerating would change the canvas; do not write.",
    )
    parser.add_argument(
        "--payload-out",
        type=Path,
        default=None,
        help="Optional path to also write the payload JSON for inspection.",
    )
    args = parser.parse_args(argv)

    report = _load_json(args.report)
    if not isinstance(report, dict):
        raise SystemExit(f"could not load report at {args.report}")

    gold_path = _resolve_gold_path(report, args.gold)
    gold = _load_json(gold_path)
    if not isinstance(gold, dict):
        raise SystemExit(f"could not load gold at {gold_path}")

    baseline = _load_json(args.baseline_report) if args.baseline_report else None
    deterministic = _load_json(args.deterministic_report) if args.deterministic_report else None
    records_text = _load_records_text(report, args.records_jsonl)

    payload = build_payload(
        report=report,
        gold=gold,
        baseline=baseline,
        deterministic=deterministic,
        records_text=records_text,
        report_path=str(args.report.resolve()),
        gold_path=str(Path(gold_path).resolve()),
        baseline_path=str(args.baseline_report.resolve()) if args.baseline_report else None,
        deterministic_path=str(args.deterministic_report.resolve()) if args.deterministic_report else None,
    )
    if args.payload_out:
        args.payload_out.parent.mkdir(parents=True, exist_ok=True)
        args.payload_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    block = render_generated_block(payload)
    canvas_path: Path = args.canvas_tsx
    canvas_text = canvas_path.read_text(encoding="utf-8")
    new_text = update_canvas_text(canvas_text, block)
    changed = new_text != canvas_text

    if args.check:
        if changed:
            print(
                f"canvas {canvas_path} generated block is stale; "
                "rerun without --check to refresh.",
                file=sys.stderr,
            )
            return 1
        print(f"canvas {canvas_path} up to date")
        return 0

    if changed:
        canvas_path.write_text(new_text, encoding="utf-8")
        print(f"updated {canvas_path}")
    else:
        print(f"{canvas_path} already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
