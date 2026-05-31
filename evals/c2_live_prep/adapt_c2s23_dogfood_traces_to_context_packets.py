#!/usr/bin/env python3
"""Adapt C2S23 dogfood planner traces into prototype context packets.

This is a trace adapter, not a manifest-backed query/admission runner.
It maps previously read planner trace paths onto manifest metadata and emits
prototype packet artifacts so authority/capability contracts can be evaluated.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MANIFEST = ROOT / "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
DEFAULT_DOGFOOD_SUMMARY = ROOT / "evals/c2_live_prep/artifacts/last_c2s23_dogfood_planner_summary.json"
DEFAULT_DOGFOOD_RUN_DIR = ROOT / "evals/c2_live_prep/artifacts/runs" / str(date.today())
DEFAULT_SCHEMA = ROOT / "evals/c2_live_prep/schemas/enriched_planning_context_packet.schema.json"

PRECONDITION_PATHS: dict[str, str] = {
    "canonical_recap_s22": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
    "normalized_recap_s22": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md",
    "breadcrumb_recap_s22": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md",
    "session_memory_jsonl_s22": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.jsonl",
    "session_memory_meta_s22": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.json",
    "live_workspace_s23_packet": "evals/c2_live_prep/live/session_23/live_packet.json",
    "activated_manifest": "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json",
}

PLAY_FACT_ALLOWED = ["canon_play", "derived_memory"]
PLAY_FACT_FORBIDDEN = ["pre_canonical_evidence", "planning_scaffold", "reference_tool", "live_observation"]


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(path: str) -> str:
    return path.strip().replace("\\", "/").lower().lstrip("./")


def _manifest_route_variants(route: str) -> set[str]:
    r = _norm(route)
    variants = {r}
    corpus_prefix = "corpus/eldyrwild-markdown/"
    if r.startswith(corpus_prefix):
        variants.add(r[len(corpus_prefix) :])
    return variants


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest_index(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    by_route: dict[str, dict[str, Any]] = {}
    entries = list(manifest.get("entries") or [])
    for row in entries:
        if not isinstance(row, dict):
            continue
        route = str(row.get("route") or "").strip()
        if not route:
            continue
        for variant in _manifest_route_variants(route):
            by_route[variant] = row
    return by_route, entries


def corpus_preconditions() -> dict[str, Any]:
    checks = []
    for key, rel in PRECONDITION_PATHS.items():
        p = ROOT / rel
        checks.append({"key": key, "path": rel, "exists": p.exists()})
    return {"all_required_present": all(bool(c["exists"]) for c in checks), "checks": checks}


def capability_status_for_question(question_id: str, tool_calls: list[str], blocked: list[dict[str, str]]) -> dict[str, Any]:
    q = question_id.lower()
    if "manifest" in q:
        blocked.append(
            {
                "code": "missing_manifest_query_admission",
                "message": "Manifest-backed query/admission is not executed in this trace-adapter run.",
            }
        )
        return {"status": "missing", "evidence": ["trace_adapter_not_manifest_query_admission"]}
    if q in {"loc-02", "roll-02", "npc-02"}:
        if not tool_calls:
            blocked.append(
                {
                    "code": "missing_live_write_capability",
                    "message": "No live write/create entrypoint was exercised for requested mutation.",
                }
            )
        return {"status": "missing", "evidence": ["no_write_tool_in_trace"]}
    return {"status": "partial", "evidence": ["inferred_from_current_dogfood_behavior"]}


def claim_type_for_question(question_id: str) -> str:
    if question_id.startswith("auth-"):
        return "authority_guardrail"
    if question_id.startswith("s22-ingest-"):
        return "pipeline_state" if question_id == "s22-ingest-03" else "play_fact"
    if question_id.startswith("xsession-"):
        return "continuity"
    if question_id.startswith("roll-"):
        return "capability_check" if question_id == "roll-02" else "planning_tooling"
    if question_id.startswith("loc-") or question_id.startswith("npc-"):
        return "capability_check" if question_id.endswith("-02") else "planning_context"
    if question_id.startswith("manifest-"):
        return "capability_check"
    return "planning_context"


def intent_class_for_question(question_id: str) -> str:
    if question_id.startswith("auth-"):
        return "authority_check"
    if question_id.startswith("s22-ingest-"):
        return "ingest_state_check"
    if question_id.startswith("manifest-"):
        return "capability_check"
    if question_id.startswith("roll-") or question_id.startswith("loc-") or question_id.startswith("npc-"):
        return "planning_mutation_or_tooling"
    return "cross_session_planning"


def build_packet(
    *,
    result_row: dict[str, Any],
    per_question: dict[str, Any],
    manifest_by_route: dict[str, dict[str, Any]],
    preconditions: dict[str, Any],
) -> dict[str, Any]:
    qid = str(result_row.get("question_id") or "")
    tool_calls = list((per_question.get("planner") or {}).get("tool_calls") or [])
    read_paths = list((result_row.get("corpus_paths_read") or []))
    final_excerpt = str(result_row.get("final_message_excerpt") or "")

    retrieved_evidence: list[dict[str, Any]] = []
    activation_manifest_refs: list[dict[str, Any]] = []
    rejected_evidence: list[dict[str, Any]] = []
    admitted_evidence: list[dict[str, Any]] = []
    route_context: list[dict[str, Any]] = []

    for path in read_paths:
        key = _norm(path)
        entry = manifest_by_route.get(key)
        if entry is None:
            retrieved_evidence.append(
                {
                    "path": path,
                    "source_role": "unknown",
                    "authority": "unknown",
                    "session_scope": [],
                    "unit_id": None,
                    "breadcrumb_id": None,
                    "line_start": None,
                    "line_end": None,
                    "admissible": False,
                    "allowed_uses": [],
                    "forbidden_uses": [],
                    "routes": [path],
                }
            )
            rejected_evidence.append(
                {
                    "evidence": retrieved_evidence[-1],
                    "reason_code": "missing_manifest_entry",
                }
            )
            continue

        e = {
            "path": path,
            "source_role": str(entry.get("source_role") or ""),
            "authority": str(entry.get("authority") or ""),
            "session_scope": list(entry.get("session_scope") or []),
            "unit_id": None,
            "breadcrumb_id": None,
            "line_start": None,
            "line_end": None,
            "admissible": bool(entry.get("admissible")),
            "allowed_uses": list(entry.get("allowed_uses") or []),
            "forbidden_uses": list(entry.get("forbidden_uses") or []),
            "routes": [str(entry.get("route") or path)],
        }
        retrieved_evidence.append(e)
        activation_manifest_refs.append(
            {
                "source_id": str(entry.get("source_id") or ""),
                "route": str(entry.get("route") or ""),
                "source_role": str(entry.get("source_role") or ""),
                "authority": str(entry.get("authority") or ""),
                "admissible": bool(entry.get("admissible")),
                "allowed_uses": list(entry.get("allowed_uses") or []),
                "forbidden_uses": list(entry.get("forbidden_uses") or []),
            }
        )

        claim_type = claim_type_for_question(qid)
        reject_reason: str | None = None
        if not e["admissible"]:
            reject_reason = "manifest_not_admissible"
        elif claim_type == "play_fact" and e["authority"] in PLAY_FACT_FORBIDDEN:
            reject_reason = "authority_forbidden_for_play_fact"

        if reject_reason:
            rejected_evidence.append({"evidence": e, "reason_code": reject_reason})
        else:
            admitted_evidence.append(e)
            route_context.append(
                {
                    "route": str(entry.get("route") or ""),
                    "source_role": str(entry.get("source_role") or ""),
                    "authority": str(entry.get("authority") or ""),
                }
            )

    blocked_or_missing: list[dict[str, str]] = []
    capability_status = capability_status_for_question(qid, tool_calls, blocked_or_missing)

    support_status = "supported" if admitted_evidence else "unsupported"
    if admitted_evidence and rejected_evidence:
        support_status = "partial"

    claim = {
        "claim_id": f"{qid}_primary_claim",
        "claim_type": claim_type_for_question(qid),
        "support_status": support_status,
        "supporting_evidence_refs": [str(e["path"]) for e in admitted_evidence],
        "route_refs": [str(r["route"]) for r in route_context],
        "planning_implication": "Use admitted evidence only; rejected evidence remains audit-visible.",
        "authority_notes": "Play-fact claims require canon_play/derived_memory only.",
    }

    packet = {
        "schema": "dmb_enriched_planning_context_packet_v1",
        "question_id": qid,
        "intent_class": intent_class_for_question(qid),
        "corpus_preconditions": preconditions,
        "activation_manifest_refs": activation_manifest_refs,
        "retrieved_evidence": retrieved_evidence,
        "admitted_evidence": admitted_evidence,
        "rejected_evidence": rejected_evidence,
        "claims": [claim],
        "route_context": route_context,
        "planning_implications": [
            "Packet is evidence-first; unsupported claims should remain blocked.",
            "Capability responses should default to missing/partial/unknown without evidence.",
        ],
        "capability_status": capability_status,
        "blocked_or_missing": blocked_or_missing,
        "citation_policy": {
            "play_fact_allowed_authorities": PLAY_FACT_ALLOWED,
            "play_fact_forbidden_authorities": PLAY_FACT_FORBIDDEN,
        },
        "source_excerpt": final_excerpt,
    }
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dogfood-summary", type=Path, default=DEFAULT_DOGFOOD_SUMMARY)
    parser.add_argument("--dogfood-run-dir", type=Path, default=DEFAULT_DOGFOOD_RUN_DIR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "evals/c2_live_prep/artifacts/runs" / str(date.today()),
    )
    args = parser.parse_args()

    manifest = load_json(args.manifest.resolve())
    summary = load_json(args.dogfood_summary.resolve())
    _schema = load_json(args.schema.resolve())
    manifest_by_route, _entries = build_manifest_index(manifest)
    preconditions = corpus_preconditions()

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    packets = []
    for row in list(summary.get("results") or []):
        qid = str(row.get("question_id") or "")
        per_path = args.dogfood_run_dir.resolve() / f"c2s23_dogfood_{qid}.json"
        if not per_path.is_file():
            per_question = {}
        else:
            per_question = load_json(per_path)

        packet = build_packet(
            result_row=row,
            per_question=per_question,
            manifest_by_route=manifest_by_route,
            preconditions=preconditions,
        )
        packets.append(packet)
        (out_dir / f"c2s23_context_packet_{qid}.json").write_text(
            json.dumps(packet, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    summary_out = {
        "schema": "dmb_c2s23_trace_context_packet_adapter_run_v1",
        "generated_at": _utc_now_z(),
        "manifest_path": str(args.manifest.resolve().relative_to(ROOT)),
        "dogfood_summary_path": str(args.dogfood_summary.resolve().relative_to(ROOT)),
        "packet_schema_path": str(args.schema.resolve().relative_to(ROOT)),
        "packet_count": len(packets),
        "all_preconditions_present": bool(preconditions["all_required_present"]),
        "packets": [
            {
                "question_id": p["question_id"],
                "intent_class": p["intent_class"],
                "retrieved_count": len(p["retrieved_evidence"]),
                "admitted_count": len(p["admitted_evidence"]),
                "rejected_count": len(p["rejected_evidence"]),
                "capability_status": p["capability_status"]["status"],
                "blocked_or_missing_count": len(p["blocked_or_missing"]),
            }
            for p in packets
        ],
    }
    summary_path = out_dir / "c2s23_trace_context_packet_adapter_summary.json"
    summary_path.write_text(json.dumps(summary_out, indent=2, ensure_ascii=False), encoding="utf-8")
    last = ROOT / "evals/c2_live_prep/artifacts/last_c2s23_trace_context_packet_adapter_summary.json"
    last.write_text(json.dumps(summary_out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(out_dir.relative_to(ROOT)),
                "summary": summary_path.name,
                "packet_count": len(packets),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
