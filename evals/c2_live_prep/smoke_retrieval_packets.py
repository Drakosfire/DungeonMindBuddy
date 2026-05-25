#!/usr/bin/env python3
"""C2 live-prep retrieval smoke — PR58–67 module chain over S20+S21 session memory."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.context_admission import build_lane_budgeted_admission
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet
from evals.c1s4_preplanning_vertical_slice.planner_prompt_payload import build_planner_prompt_payload
from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.query_alias_expansion import build_step2c_query_variants
from evals.c1s4_preplanning_vertical_slice.query_lane_router import build_lane_plan
from evals.c1s4_preplanning_vertical_slice.query_variant_retrieval import retrieve_query_variants
from evals.c1s4_preplanning_vertical_slice.source_derived_context_gaps import build_source_derived_context_gaps
from src.agent.session_memory_query import load_session_memory_records_jsonl

CORPUS_ROOT = ROOT / "corpus" / "eldyrwild-markdown"
SESSION_MEMORY_DIR = (
    CORPUS_ROOT / "Longmont Campaign" / "Campaign 2" / "Session Recaps" / "_session_memory"
)

CAMPAIGN_ID = "longmont-c2"
SESSION_MIN = 0
SESSION_MAX = 21
RETRIEVAL_MODE = "prior_only"
MAX_HITS = 50
BUDGET_CHARS = 8000

DEFAULT_SMOKE_QUESTIONS = [
    (
        "active_npcs_thrin_lysandra",
        "For Session 22 prep: which beats matter for Thrin Branchbound (keep him in foreground) "
        "and Captain Lysandra Ironveil (weird week, Mirathorn comms, Caelynn bond)?",
    ),
    (
        "mirathorn_turnaround",
        "If the party turns back toward Mirathorn or calls again, what happened there and what "
        "open threads must we honor from Sessions 20–21?",
    ),
    (
        "travel_north_mireward",
        "Moving forward on the Mireward Reach: what is the next town, how far away, storm pressure, "
        "and what travel encounter tables apply?",
    ),
    (
        "raucous_saints_dustwalker",
        "Celtic punk band / organized music north toward the swamp — Raucous Saints vs Dustwalker "
        "rumors from Mossford and Session 21?",
    ),
    (
        "boots_crowing_wings",
        "Boots of Crowing Wings from the geomantic drake nest — what does the table know and what "
        "mechanics or loot notes exist?",
    ),
]


class _Merged:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self.hits = hits


def _resolve_session_memory_paths(sessions: tuple[int, ...]) -> list[Path]:
    paths: list[Path] = []
    for session in sessions:
        matches = sorted(SESSION_MEMORY_DIR.glob(f"Session {session:02d} - *.records_meta.jsonl"))
        if not matches:
            raise FileNotFoundError(f"No session memory JSONL for session {session} under {SESSION_MEMORY_DIR}")
        paths.append(matches[0])
    return paths


def load_c2_combined_records(sessions: tuple[int, ...] = (20, 21)) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    combined: list[dict[str, Any]] = []
    sources: list[str] = []
    for path in _resolve_session_memory_paths(sessions):
        rows = load_session_memory_records_jsonl(path)
        combined.extend(rows)
        sources.append(str(path.relative_to(ROOT)))
    records_by_unit_id = {str(r.get("unit_id")): r for r in combined if r.get("unit_id")}
    return combined, records_by_unit_id, sources


def build_live_prep_packet(
    *,
    question: str,
    question_id: str,
    combined_records: list[dict[str, Any]],
    records_by_unit_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    lane_plan = build_lane_plan(
        question_text=question,
        retrieval_mode=RETRIEVAL_MODE,
        candidate_depth=MAX_HITS,
        total_budget_chars=BUDGET_CHARS,
    )
    variants = build_step2c_query_variants(
        question_text=question,
        retrieval_mode=RETRIEVAL_MODE,
        lane_plan=lane_plan,
    )
    merged_hits, query_variant_diagnostics = retrieve_query_variants(
        records=combined_records,
        query_variants=variants,
        campaign_id=CAMPAIGN_ID,
        session_min=SESSION_MIN,
        session_max=SESSION_MAX,
        candidate_depth=MAX_HITS,
    )

    bundle = build_preplanning_context_bundle(
        kb_id=f"{CAMPAIGN_ID}-live-prep-v1",
        campaign_id=CAMPAIGN_ID,
        allowed_sessions=list(range(1, SESSION_MAX + 1)),
        heldout_sessions=[],
        query=question,
        retrieval_result=_Merged(merged_hits),
        forbidden_oracle_relpaths=[],
        records_by_unit_id=records_by_unit_id,
        max_items=MAX_HITS,
    )
    candidate_context = bundle["items"]

    admission = build_lane_budgeted_admission(
        question_text=question,
        retrieval_mode=RETRIEVAL_MODE,
        candidates=candidate_context,
        lane_plan=lane_plan,
        candidate_depth=MAX_HITS,
        total_budget_chars=BUDGET_CHARS,
    )

    packet: dict[str, Any] = {
        "schema": "dmb_c2_live_prep_context_packet_v0",
        "question_id": question_id,
        "campaign_id": CAMPAIGN_ID,
        "question": question,
        "retrieval_mode": RETRIEVAL_MODE,
        "session_memory_window": {"min": SESSION_MIN, "max": SESSION_MAX, "indexed_sessions": [20, 21]},
        "candidate_context_count": len(candidate_context),
        "candidate_context": candidate_context,
        "query_variant_diagnostics": query_variant_diagnostics,
        "lane_plan": lane_plan,
        **admission,
    }

    gaps = build_source_derived_context_gaps(
        question_id=question_id,
        question_text=question,
        retrieval_mode=RETRIEVAL_MODE,
        candidate_context=packet.get("candidate_context") or candidate_context,
        admitted_context=packet.get("admitted_context") or [],
        query_features=lane_plan.get("query_features"),
    )
    if gaps:
        packet["source_derived_context_gaps"] = gaps

    rendered = render_context_packet(packet)
    packet["rendered_context_packet"] = rendered
    packet["planner_prompt_payload"] = build_planner_prompt_payload(
        context_packet=packet,
        rendered_context_packet=rendered,
    )
    return packet


def _summarize_admitted(item: dict[str, Any]) -> dict[str, Any]:
    prov = item.get("provenance") or item.get("source_provenance") or {}
    return {
        "unit_id": item.get("unit_id"),
        "session_number": item.get("session_number"),
        "route": item.get("route") or item.get("primary_route"),
        "snippet": (item.get("snippet") or item.get("text") or "")[:240],
        "source_path": prov.get("source_path") or item.get("source_path"),
    }


def _packet_summary(packet: dict[str, Any]) -> dict[str, Any]:
    admitted = packet.get("admitted_context") or []
    diag = packet.get("admission_decision_diagnostics") or {}
    gaps = packet.get("source_derived_context_gaps") or []
    rendered = packet.get("rendered_context_packet") or {}
    return {
        "question_id": packet.get("question_id"),
        "question": packet.get("question"),
        "candidate_count": packet.get("candidate_context_count"),
        "admitted_count": len(admitted),
        "lane_id": (packet.get("lane_plan") or {}).get("lane_id"),
        "admission_diagnostics": {
            "first_admitted_match": diag.get("first_admitted_match"),
            "first_raw_match": diag.get("first_raw_match"),
            "failure_stage": diag.get("failure_stage"),
            "miss_root_cause": diag.get("miss_root_cause"),
        },
        "admitted_top": [_summarize_admitted(x) for x in admitted[:8]],
        "source_derived_context_gaps": gaps[:6],
        "rendered_sections": list((rendered.get("sections") or {}).keys()) if isinstance(rendered.get("sections"), dict) else [],
        "rendered_text_excerpt": (rendered.get("rendered_text") or "")[:1200],
    }


def _write_markdown_report(path: Path, summaries: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    lines = [
        "# C2 Session 22 prep — retrieval smoke",
        "",
        f"**Date:** {meta['run_date']}",
        f"**Record pool:** {meta['record_count']} records from {', '.join(meta['sources'])}",
        f"**Stack:** PR58–67 lane-budgeted admission (`{RETRIEVAL_MODE}`)",
        "",
        "See `HANDOFF-session-22-travel-north-active-NPCs.md` for corpus index; "
        "this artifact is **session-memory retrieval only** (no hub chunks, no d100 tables in index).",
        "",
    ]
    for s in summaries:
        lines.extend(
            [
                f"## {s['question_id']}",
                "",
                f"**Question:** {s['question']}",
                "",
                f"- **Admitted:** {s['admitted_count']} / {s['candidate_count']} candidates",
                f"- **Lane:** `{s.get('lane_id')}`",
                f"- **Admission:** first_admitted={s['admission_diagnostics'].get('first_admitted_match')!r}, "
                f"miss_root_cause={s['admission_diagnostics'].get('miss_root_cause')!r}",
                "",
            ]
        )
        if s["admitted_top"]:
            lines.append("### Top admitted")
            for i, row in enumerate(s["admitted_top"], 1):
                lines.append(
                    f"{i}. `{row.get('route')}` (S{row.get('session_number')}) — "
                    f"{row.get('snippet', '')[:180]!r}"
                )
            lines.append("")
        if s["source_derived_context_gaps"]:
            lines.append("### Source-derived gaps")
            for g in s["source_derived_context_gaps"]:
                lines.append(f"- {g}")
            lines.append("")
        excerpt = s.get("rendered_text_excerpt") or ""
        if excerpt.strip():
            lines.extend(["### Rendered excerpt", "", excerpt, ""])
        lines.append("---")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="C2 live-prep retrieval smoke")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "evals" / "c2_live_prep" / "artifacts" / "runs" / date.today().isoformat(),
    )
    args = parser.parse_args()
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    combined, records_by_unit_id, sources = load_c2_combined_records((20, 21))
    packets: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for qid, question in DEFAULT_SMOKE_QUESTIONS:
        packet = build_live_prep_packet(
            question=question,
            question_id=qid,
            combined_records=combined,
            records_by_unit_id=records_by_unit_id,
        )
        packets.append(packet)
        summaries.append(_packet_summary(packet))
        (out_dir / f"{qid}.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")

    meta = {
        "run_date": date.today().isoformat(),
        "record_count": len(combined),
        "sources": sources,
        "questions": [q[0] for q in DEFAULT_SMOKE_QUESTIONS],
    }
    (out_dir / "c2s22_smoke_summary.json").write_text(
        json.dumps({"meta": meta, "summaries": summaries}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_markdown_report(out_dir / "c2s22_smoke_report.md", summaries, meta)

    print(json.dumps({"ok": True, "output_dir": str(out_dir.relative_to(ROOT)), "summaries": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
