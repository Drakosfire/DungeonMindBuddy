from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.synthetic_prep_packet_harness import SECTION_QUESTION_MAP

ORACLE_COMPARISON_SCHEMA = "dmb_c1s4_oracle_comparison_report_v1"
DEFAULT_ORACLE_POLICY_PATH = Path(__file__).resolve().parent / "gold" / "c1s4_oracle_policy.json"
FORBIDDEN_REPORT_PATH_MARKERS = ("step2", "step3", "step4", "step5", "support_knowledge")
ORACLE_SENSITIVE_TERMS = [
    "hempholm", "torvak", "torbin", "jove", "steve", "grotesque tree", "metallic tree", "precious metal leaves",
    "root-like beetles", "caretakers", "marrow", "guardian", "celebration", "deeper threat",
]


def load_oracle_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or DEFAULT_ORACLE_POLICY_PATH
    return json.loads(policy_path.read_text(encoding="utf-8"))


def load_oracle_text(policy: dict[str, Any]) -> dict[str, Any]:
    bundle = {"oracle_sources_loaded": [], "oracle_text": "", "source_texts": []}
    for source in policy.get("oracle_sources", []):
        source_path = Path(source["path"])
        text = source_path.read_text(encoding="utf-8")
        bundle["oracle_sources_loaded"].append({
            "source_id": source.get("source_id"),
            "path": source.get("path"),
            "role": source.get("role"),
        })
        bundle["source_texts"].append({"source_id": source.get("source_id"), "text": text})
    bundle["oracle_text"] = "\n\n".join(t["text"] for t in bundle["source_texts"])
    return bundle


def normalize_for_comparison(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_terms(text: str) -> set[str]:
    norm = normalize_for_comparison(text)
    out = set(norm.split())
    for phrase in ORACLE_SENSITIVE_TERMS:
        p = normalize_for_comparison(phrase)
        if p and p in norm:
            out.add(p)
    return out


def build_oracle_comparison_report(*, prep_packet: dict[str, Any], oracle_policy: dict[str, Any], oracle_text_bundle: dict[str, Any]) -> dict[str, Any]:
    oracle_terms = extract_terms(oracle_text_bundle.get("oracle_text", ""))
    section_comparisons = []
    unsupported_claims: list[dict[str, Any]] = []

    for section in prep_packet.get("sections", []):
        section_text = " ".join(str(e.get("answer_text") or "") for e in section.get("prep_entries", []))
        prep_terms = extract_terms(section_text)
        overlap = sorted(prep_terms & oracle_terms)
        prep_only = sorted(prep_terms - oracle_terms)
        oracle_only = sorted(oracle_terms - prep_terms)
        risky = sorted(t for t in prep_only if t in {normalize_for_comparison(x) for x in ORACLE_SENSITIVE_TERMS})
        for rt in risky:
            unsupported_claims.append({"section_id": section.get("section_id"), "term": rt, "kind": "generated_only_oracle_sensitive"})

        section_comparisons.append({
            "section_id": section.get("section_id"),
            "title": section.get("title"),
            "prep_question_numbers": section.get("question_numbers", []),
            "oracle_overlap_terms": overlap,
            "prep_terms_not_seen_in_oracle": prep_only[:30],
            "oracle_terms_not_seen_in_prep": oracle_only[:30],
            "coarse_overlap_note": "Lexical overlap detected." if overlap else "No lexical overlap detected in high-signal terms.",
            "risk_notes": [f"Potential unsupported oracle-sensitive term: {t}" for t in risky],
            "known_gaps_respected": list(section.get("section_known_gaps", [])),
            "unsupported_claims": [u for u in unsupported_claims if u["section_id"] == section.get("section_id")],
        })

    report = {
        "schema": ORACLE_COMPARISON_SCHEMA,
        "campaign_id": prep_packet.get("campaign_id", "longmont-c1"),
        "comparison_status": "scaffold_coarse_comparison",
        "retrieval_mode": prep_packet.get("retrieval_mode"),
        "generator": prep_packet.get("generator"),
        "oracle_visibility": "step6_only",
        "planner_visibility": "forbidden",
        "synthetic_prep_packet_schema": prep_packet.get("schema"),
        "oracle_sources_loaded": oracle_text_bundle.get("oracle_sources_loaded", []),
        "oracle_loaded_only_in_step6": True,
        "does_not_claim_final_quality_score": True,
        "section_comparisons": section_comparisons,
        "oracle_sensitive_findings": unsupported_claims,
        "missed_major_beats": [s["section_id"] for s in section_comparisons if not s["oracle_overlap_terms"]],
        "safe_generated_prep_notes": ["Scaffold report only; no final quality score emitted."],
        "known_gap_handling": prep_packet.get("known_gaps", []),
        "unsupported_claims": unsupported_claims,
        "summary": {
            "sections_compared": len(section_comparisons),
            "sections_with_overlap": sum(1 for s in section_comparisons if s["oracle_overlap_terms"]),
            "sections_with_no_overlap": sum(1 for s in section_comparisons if not s["oracle_overlap_terms"]),
            "oracle_sensitive_terms_found": len({u["term"] for u in unsupported_claims}),
            "unsupported_claims_found": len(unsupported_claims),
            "final_score": None,
        },
    }
    return report


def validate_oracle_comparison_report(report: dict[str, Any]) -> list[str]:
    errs = []
    if report.get("schema") != ORACLE_COMPARISON_SCHEMA:
        errs.append("invalid schema")
    if report.get("oracle_visibility") != "step6_only":
        errs.append("oracle_visibility must be step6_only")
    if report.get("planner_visibility") != "forbidden":
        errs.append("planner_visibility must be forbidden")
    if report.get("oracle_loaded_only_in_step6") is not True:
        errs.append("oracle_loaded_only_in_step6 must be true")
    if report.get("does_not_claim_final_quality_score") is not True:
        errs.append("does_not_claim_final_quality_score must be true")
    if (report.get("summary") or {}).get("final_score") is not None:
        errs.append("summary.final_score must be null")
    if not report.get("oracle_sources_loaded"):
        errs.append("oracle_sources_loaded must be non-empty")
    if not report.get("section_comparisons"):
        errs.append("section_comparisons missing")
    if report.get("synthetic_prep_packet_schema") != "dmb_c1s4_synthetic_prep_packet_v1":
        errs.append("synthetic prep packet schema mismatch")
    for marker in FORBIDDEN_REPORT_PATH_MARKERS:
        if marker in json.dumps(report.get("oracle_sources_loaded", [])).lower():
            errs.append("report contains planner-visible output paths")
            break
    required = set(SECTION_QUESTION_MAP)
    got = {s.get("section_id") for s in report.get("section_comparisons", []) if isinstance(s, dict)}
    if required - got:
        errs.append("required section_comparisons missing")
    return errs
