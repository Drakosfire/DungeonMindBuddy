from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet
from evals.c1s4_preplanning_vertical_slice.planner_surface_coverage import (
    RETRIEVAL_MODES,
    build_planner_surface_rows,
    lookup_step2_packet,
)
from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import load_support_cards

SUPPORT_KIND = "support_knowledge_card"

MATRIX_COLUMNS = [
    "question_number",
    "question_id",
    "mode",
    "authority_label",
    "support_allowed_for_mode",
    "query_affordances",
    "expected_support_refs_eval_only",
    "baseline_pr65_first_any_support_candidate_rank",
    "first_any_support_candidate_rank",
    "first_required_support_candidate_rank",
    "first_required_support_candidate_ref",
    "first_required_support_admitted_rank",
    "required_support_rendered",
    "support_token_share",
    "support_match_channels",
    "policy_classification",
    "next_failure_surface",
]


def _support_unit_id(card: dict[str, Any]) -> str:
    return f"support:{card.get('support_card_id')}"


def _expected_support_by_question_number() -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for card in load_support_cards():
        ref = _support_unit_id(card)
        for usable in card.get("usable_for_questions") or []:
            text = str(usable)
            if not text.startswith("q"):
                continue
            number_text = text[1:3]
            if not number_text.isdigit():
                continue
            out.setdefault(int(number_text), []).append(ref)
    return {qn: sorted(set(refs)) for qn, refs in out.items()}


def _baseline_pr65_first_support_ranks() -> dict[tuple[int, str], int | None]:
    path = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr65/pr65_planner_surface_coverage_matrix.csv")
    if not path.exists():
        return {}
    out: dict[tuple[int, str], int | None] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                qn = int(row.get("question_number") or 0)
            except ValueError:
                continue
            raw = str(row.get("first_support_candidate_rank") or "").strip()
            out[(qn, str(row.get("mode") or ""))] = int(raw) if raw.isdigit() else None
    return out


def _is_support(item: dict[str, Any]) -> bool:
    return str(item.get("source_kind") or "") == SUPPORT_KIND or str(item.get("unit_id") or "").startswith("support:")


def _rank_of(items: list[dict[str, Any]], refs: set[str] | None = None) -> tuple[int | None, str | None, dict[str, Any] | None]:
    for idx, item in enumerate(items, start=1):
        uid = str(item.get("unit_id") or "")
        if not _is_support(item):
            continue
        if refs is not None and uid not in refs:
            continue
        return idx, uid, item
    return None, None, None


def _query_affordances(packet: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for variant in (packet.get("query_variant_diagnostics") or {}).get("variants") or []:
        for affordance in variant.get("query_affordances") or []:
            if affordance not in values:
                values.append(str(affordance))
    return values


def _channels(item: dict[str, Any] | None) -> dict[str, bool]:
    base = {
        "title_summary": False,
        "retrieval_terms": False,
        "planner_affordances": False,
        "support_alias": False,
    }
    if item and isinstance(item.get("support_match_channels"), dict):
        for key in base:
            base[key] = bool(item["support_match_channels"].get(key))
    elif item:
        base["title_summary"] = True
    return base


def _rendered_refs(packet: dict[str, Any]) -> set[str]:
    rendered = render_context_packet(packet)
    refs: set[str] = set()
    for section in rendered.get("sections") or []:
        if isinstance(section, dict):
            refs.update(str(r) for r in section.get("refs") or [])
    return refs


def build_pr66_diagnostics() -> dict[str, Any]:
    expected_by_qn = _expected_support_by_question_number()
    baseline = _baseline_pr65_first_support_ranks()
    rows = build_planner_surface_rows(include_evaluator_only=True, include_generated_answer=False)
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("planner_facing"):
            continue
        qn = int(row.get("question_number") or 0)
        mode = str(row.get("mode") or "")
        packet = lookup_step2_packet(mode=mode, question_number=qn)
        expected_refs = set(expected_by_qn.get(qn) or [])
        candidate = list((packet or {}).get("candidate_context") or [])
        admitted = list((packet or {}).get("admitted_context") or [])
        any_rank, _, _ = _rank_of(candidate)
        req_rank, req_ref, req_item = _rank_of(candidate, expected_refs if expected_refs else None)
        req_admitted_rank, _, req_admitted_item = _rank_of(admitted, expected_refs if expected_refs else None)
        rendered_refs = _rendered_refs(packet or {}) if packet else set()
        row_out = {
            "question_number": qn,
            "question_id": row.get("question_id"),
            "mode": mode,
            "authority_label": row.get("authority_label"),
            "support_allowed_for_mode": bool(row.get("support_knowledge_allowed")),
            "query_affordances": _query_affordances(packet or {}),
            "expected_support_refs_eval_only": sorted(expected_refs),
            "baseline_pr65_first_any_support_candidate_rank": baseline.get((qn, mode)),
            "first_any_support_candidate_rank": any_rank,
            "first_required_support_candidate_rank": req_rank,
            "first_required_support_candidate_ref": req_ref,
            "first_required_support_admitted_rank": req_admitted_rank,
            "required_support_rendered": bool(expected_refs & rendered_refs),
            "support_token_share": row.get("support_token_share"),
            "support_match_channels": _channels(req_item or req_admitted_item),
            "policy_classification": row.get("support_policy_status"),
            "next_failure_surface": row.get("next_failure_surface"),
        }
        out_rows.append(row_out)
    return {
        "schema": "dmb_pr66_support_affordance_diagnostics_v1",
        "retrieval_modes": list(RETRIEVAL_MODES),
        "rows": out_rows,
    }


def write_pr66_artifacts(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_pr66_diagnostics()
    (output_dir / "pr66_support_affordance_diagnostics.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "pr66_support_affordance_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MATRIX_COLUMNS)
        writer.writeheader()
        for row in payload["rows"]:
            writer.writerow(
                {
                    **row,
                    "query_affordances": "|".join(row.get("query_affordances") or []),
                    "expected_support_refs_eval_only": "|".join(row.get("expected_support_refs_eval_only") or []),
                    "support_match_channels": json.dumps(row.get("support_match_channels") or {}, sort_keys=True),
                }
            )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr66"))
    args = parser.parse_args()
    payload = write_pr66_artifacts(args.output_dir)
    print(json.dumps({"schema": payload["schema"], "rows": len(payload["rows"]), "output_dir": str(args.output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
