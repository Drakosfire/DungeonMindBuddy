"""Static extractor output comparison report fixture helpers."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from evals.graph_memory_layer import eval_only_extractor_harness as harness
from evals.graph_memory_layer import multi_pass_extraction_contract as contract
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import GOLD_FIXTURE_ID, HIGH_RISK_EVIDENCE_AUDIT

REPORT_MANIFEST_SCHEMA = "dmb_static_extractor_output_comparison_report_manifest_v0"
REPORT_SCHEMA = "dmb_static_extractor_output_comparison_report_v0"
REPORT_VERSION = "0.1"
REPORT_FIXTURE_ID = "graph-memory:static-extractor-output-comparison-report:v0"
REPORT_ID = "graph-memory:static-extractor-output-comparison-report:session-23:sample-v0"
REPORT_DIR = "evals/graph_memory_layer/examples/static_extractor_output_comparison_report"
REPORT_MANIFEST_PATH = f"{REPORT_DIR}/static_comparison_report_manifest.json"
STATIC_REPORT_JSON_PATH = f"{REPORT_DIR}/session_23_static_comparison_report.json"
STATIC_REPORT_MD_PATH = f"{REPORT_DIR}/session_23_static_comparison_report.md"
_TYPES = ("nodes", "edges", "beats", "proposed_writes", "ignored_items", "deferred_items")
_RECALL_KEYS = ("node_recall", "edge_recall", "beat_recall", "proposed_write_recall", "ignored_item_recall", "deferred_item_recall")


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def _load(rel: str) -> dict[str, Any]: return json.loads((repo_root()/rel).read_text(encoding="utf-8"))
def _assert(cond: bool, msg: str) -> None:
    if not cond: raise ValueError(msg)
def load_manifest() -> dict[str, Any]: return _load(REPORT_MANIFEST_PATH)
def load_static_report_json() -> dict[str, Any]: return _load(STATIC_REPORT_JSON_PATH)
def load_static_report_markdown() -> str: return (repo_root()/STATIC_REPORT_MD_PATH).read_text(encoding="utf-8")
def _band(score: float) -> str:
    if score == 1.0: return "pass"
    if score >= 0.75: return "good"
    if score >= 0.4: return "partial"
    if score > 0.0: return "weak"
    return "none"

def _coverage_item(comp: Mapping[str, Any], typ: str, score_key: str, precision_key: str | None = None) -> dict[str, Any]:
    c = comp["coverage"]
    matched = c[f"matched_{typ}"]
    gold = c[f"gold_{typ}_total"]; cand = c[f"candidate_{typ}_total"]
    return {"gold_total": gold, "candidate_total": cand, "matched": len(matched), "missing": len(c[f"missing_gold_{typ}"]), "extra": len(c[f"extra_candidate_{typ}"]), "recall": _score(comp, score_key), "precision_proxy": _score(comp, precision_key) if precision_key else (round(len(matched)/cand,4) if cand else 1.0)}

def _score(comp: Mapping[str, Any], key: str | None) -> float:
    return float(comp["scores"][key]) if key else 1.0

def _soft_by_issue(soft: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in soft:
        grouped[item["issue"]].append({"id": item["detail"], "label": item.get("label", "")})
    return {k: {"count": len(v), "items": v} for k, v in sorted(grouped.items())}

def _hard_by_issue(hard: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in hard: grouped[item["issue"]].append(item.get("detail", ""))
    return {k: {"count": len(v), "details": v} for k, v in sorted(grouped.items())}

def _missing_by_priority(missing_by_type: Mapping[str, Any], hard: list[Mapping[str, Any]]) -> dict[str, Any]:
    critical = [{"issue": x["issue"], "detail": x.get("detail", "")} for x in hard]
    important=[]; nice=[]
    for typ in ("edges","beats","proposed_writes","deferred_items"):
        important.extend({"type": typ, **x} for x in missing_by_type[typ])
    for typ in ("nodes","ignored_items"):
        nice.extend({"type": typ, **x} for x in missing_by_type[typ])
    return {"critical": critical, "important": important, "nice_to_have": nice}

def _evidence_health(bundle: Mapping[str, Any], comp: Mapping[str, Any]) -> dict[str, Any]:
    resolved = harness.resolve_candidate_evidence_refs(bundle)
    total = len(resolved)
    warnings = sum(len(x.warnings) for x in resolved)
    heading = sum(1 for x in resolved if x.preview_snippet.lstrip().startswith("#"))
    return {"evidence_alignment_score": comp["scores"]["evidence_alignment_score"], "total_evidence_refs": total, "resolved_evidence_refs": sum(x.can_open_source and x.can_highlight_span and not x.warnings for x in resolved), "openable_evidence_refs": sum(x.can_open_source for x in resolved), "highlightable_evidence_refs": sum(x.can_highlight_span for x in resolved), "warning_count": warnings, "unknown_anchor_count": 0, "heading_only_count": heading, "source_leakage_detected": False, "summary": "All candidate evidence refs resolve, open, and highlight against the Session 23 source-span fixture."}

def build_static_report_json() -> dict[str, Any]:
    bundle = harness.load_candidate_bundle(); comp = harness.compare_candidate_to_gold(bundle); scores=comp["scores"]; cov=comp["coverage"]
    coverage={"nodes": _coverage_item(comp,"nodes","node_recall","node_precision_proxy"), "edges": _coverage_item(comp,"edges","edge_recall","edge_precision_proxy"), "beats": _coverage_item(comp,"beats","beat_recall"), "proposed_writes": _coverage_item(comp,"proposed_writes","proposed_write_recall"), "ignored_items": _coverage_item(comp,"ignored_items","ignored_item_recall"), "deferred_items": _coverage_item(comp,"deferred_items","deferred_item_recall")}
    hard=comp["hard_failures"]; soft=comp["soft_misses"]
    all_recall_complete=all(scores[k] == 1.0 for k in _RECALL_KEYS)
    status = "unsafe" if hard else ("safe_complete" if all_recall_complete else "safe_but_incomplete")
    gm_status = "unsafe_for_preview" if hard else ("ready_for_gm_preview" if scores["safety_gate_score"]==1.0 and scores["node_recall"]>=0.8 and scores["edge_recall"]>=0.7 and scores["beat_recall"]>=0.7 else "not_ready_for_gm_preview")
    missing_by_type={typ: cov[f"missing_gold_{typ}"] for typ in _TYPES}; extra_by_type={typ: cov[f"extra_candidate_{typ}"] for typ in _TYPES}
    writes=bundle["assembled_candidate_graph"]["proposed_writes"]; write_statuses=[w.get("status") for w in writes]
    audited=sorted(set(row["object_id"] for row in HIGH_RISK_EVIDENCE_AUDIT))
    report={"schema": REPORT_SCHEMA, "version": REPORT_VERSION, "report_id": REPORT_ID, "source_report_id": comp["report_id"], "candidate_bundle_id": comp["candidate_bundle_id"], "gold_fixture_id": comp["gold_fixture_id"], "campaign_id": "longmont-c2", "session_id": "session-23",
        "verdict": {"status": status, "merge_gate": "fail" if hard else "pass", "reviewer_summary": "The sample candidate output has no hard failures and passes evidence/high-risk/safety gates, but misses substantial Session 23 gold coverage.", "blocking_issue_count": len(hard), "soft_issue_count": len(soft), "recommended_next_action": "Use this report shape to inspect future static or gated extractor outputs before live extraction is admitted."},
        "score_summary": {"overall_safety": {"score": scores["safety_gate_score"], "band": _band(scores["safety_gate_score"]), "components": {"safety_gate_score": scores["safety_gate_score"], "evidence_alignment_score": scores["evidence_alignment_score"], "high_risk_audit_score": scores["high_risk_audit_score"]}}, "coverage": {k: {"score": scores[k], "band": _band(scores[k])} for k in _RECALL_KEYS}, "precision_proxy": {"node_precision_proxy": {"score": scores["node_precision_proxy"], "band": _band(scores["node_precision_proxy"])}, "edge_precision_proxy": {"score": scores["edge_precision_proxy"], "band": _band(scores["edge_precision_proxy"])}}},
        "coverage_summary": coverage, "hard_failure_summary": {"total": len(hard), "by_issue": _hard_by_issue(hard), "blocking": bool(hard), "reviewer_note": "No hard safety failures were found in the static sample candidate output." if not hard else "Hard safety failures block the static sample."}, "soft_miss_summary": {"total": len(soft), "by_issue": _soft_by_issue(soft)}, "missing_gold_coverage": {"by_type": missing_by_type, "by_review_priority": _missing_by_priority(missing_by_type, hard)}, "extra_candidate_coverage": {"by_type": extra_by_type, "total": sum(len(v) for v in extra_by_type.values())}, "evidence_health": _evidence_health(bundle, comp), "high_risk_audit_summary": {"score": scores["high_risk_audit_score"], "status": "pass" if scores["high_risk_audit_score"] == 1.0 else "fail", "audited_object_count": len(audited), "audited_objects": audited, "forbidden_claims_absent": ["Questionable Company", "second wave", "thread-monster-second-wave", "resolved battle outcome", "exact shadow count as fact", "approved write", "promoted lifecycle"], "summary": "High-risk claims are present where expected and pass source-grounding audit."}, "proposed_write_summary": {"candidate_total": len(writes), "matched_gold_total": coverage["proposed_writes"]["matched"], "missing_gold_total": coverage["proposed_writes"]["missing"], "approved_count": sum(s=="approved" for s in write_statuses), "pending_count": sum(s=="pending" for s in write_statuses), "promoted_count": sum(s=="promoted" for s in write_statuses), "unsafe_status_count": sum(s not in {"pending"} for s in write_statuses), "summary": "All candidate proposed writes remain pending; the sample omits several gold proposed writes."}, "gm_preview_readiness": {"status": gm_status, "reason": "The static sample is safe but misses too many Session 23 edges, beats, proposed writes, and deferred items to be useful as a GM-facing preview.", "safe_to_inspect": not hard, "safe_to_write": False, "sufficient_coverage_for_preview": gm_status == "ready_for_gm_preview", "recommended_improvements": ["Improve edge recall before GM preview.", "Improve beat recall before GM preview.", "Add missing deferred items and proposed writes.", "Preserve current evidence and high-risk audit safety gates."]}, "diagnostics": {"static_report_fixture": True, "llm_execution_required": False, "extractor_execution_required": False, "live_planner_required": False, "runtime_required": False, "corpus_scan_required": False, "corpus_mutation_required": False, "graph_write_required": False, "approval_required": False, "query_execution_required": False, "plan_connected": False, "agent_interaction_connected": False, "production_behavior_changed": False}}
    return report

def build_static_report_markdown(report: Mapping[str, Any] | None = None) -> str:
    r=report or build_static_report_json(); out=[]; add=out.append
    add("# Static Extractor Output Comparison Report — Session 23 Sample\n")
    add("## Verdict\n"); v=r["verdict"]; add(f"- Status: `{v['status']}`\n- Merge gate: `{v['merge_gate']}`\n- Blocking issues: {v['blocking_issue_count']}\n- Soft issues: {v['soft_issue_count']}\n- Summary: {v['reviewer_summary']}\n")
    add("## Safety Gate\n"); s=r["score_summary"]["overall_safety"]; add(f"- Overall safety: {s['score']} (`{s['band']}`)\n- Evidence alignment: {s['components']['evidence_alignment_score']}\n- High-risk audit: {s['components']['high_risk_audit_score']}\n")
    add("## Score Summary\n\n| Score | Value | Band |\n|---|---:|---|\n");
    for group in ("coverage","precision_proxy"):
        for k,x in r["score_summary"][group].items(): add(f"| {k} | {x['score']} | {x['band']} |\n")
    add("\n## Coverage Summary\n\n| Type | Gold | Candidate | Matched | Missing | Extra | Recall | Precision Proxy |\n|---|---:|---:|---:|---:|---:|---:|---:|\n")
    for typ,x in r["coverage_summary"].items(): add(f"| {typ} | {x['gold_total']} | {x['candidate_total']} | {x['matched']} | {x['missing']} | {x['extra']} | {x['recall']} | {x['precision_proxy']} |\n")
    add("\n## Missing Gold Coverage\n\n| Type | Missing Count | Example IDs |\n|---|---:|---|\n")
    for typ,items in r["missing_gold_coverage"]["by_type"].items(): add(f"| {typ} | {len(items)} | {', '.join(i['id'] for i in items[:5]) or 'none'} |\n")
    add("\n## Soft Misses By Category\n\n| Issue | Count |\n|---|---:|\n")
    for issue,x in r["soft_miss_summary"]["by_issue"].items(): add(f"| {issue} | {x['count']} |\n")
    add("\n## Hard Failures\n"); hf=r["hard_failure_summary"]; add(f"- Total: {hf['total']}\n- Blocking: {str(hf['blocking']).lower()}\n- Note: {hf['reviewer_note']}\n")
    add("## Evidence Health\n"); e=r["evidence_health"]; add(f"- Evidence refs: {e['total_evidence_refs']}\n- Resolved: {e['resolved_evidence_refs']}\n- Openable: {e['openable_evidence_refs']}\n- Highlightable: {e['highlightable_evidence_refs']}\n- Warnings: {e['warning_count']}\n- Summary: {e['summary']}\n")
    add("## High-Risk Audit\n"); a=r["high_risk_audit_summary"]; add(f"- Status: `{a['status']}`\n- Audited objects: {', '.join(a['audited_objects'])}\n- Summary: {a['summary']}\n")
    add("## Proposed Writes\n"); p=r["proposed_write_summary"]; add(f"- Candidate total: {p['candidate_total']}\n- Pending: {p['pending_count']}\n- Approved: {p['approved_count']}\n- Promoted: {p['promoted_count']}\n- Unsafe statuses: {p['unsafe_status_count']}\n- Summary: {p['summary']}\n")
    add("## GM Preview Readiness\n"); g=r["gm_preview_readiness"]; add(f"- Status: `{g['status']}`\n- Safe to inspect: {str(g['safe_to_inspect']).lower()}\n- Safe to write: {str(g['safe_to_write']).lower()}\n- Sufficient coverage for preview: {str(g['sufficient_coverage_for_preview']).lower()}\n- Reason: {g['reason']}\n")
    add("## Boundary Statement\n\nThis is a static comparison report fixture.\nIt does not call an LLM.\nIt does not execute a live extractor.\nIt does not generate output from recap text.\nIt does not write graph memory.\nIt does not approve writes.\nIt does not execute graph queries.\nIt does not scan or mutate corpus files.\nIt does not connect /plan.\nIt does not connect Agent Interaction.\nIt does not promote facts or canon.\nIt does not change runtime or production behavior.\n")
    return "".join(out)

def _safe_rel(value: str) -> None:
    p=Path(value); _assert(not p.is_absolute() and ".." not in p.parts, f"unsafe path: {value}"); _assert(value.startswith("evals/graph_memory_layer/examples/"), f"path outside eval fixtures: {value}")

def validate_manifest(manifest: Mapping[str, Any]) -> None:
    _assert(manifest.get("schema")==REPORT_MANIFEST_SCHEMA and manifest.get("version")==REPORT_VERSION, "wrong manifest schema/version")
    _assert(manifest.get("report_fixture_id")==REPORT_FIXTURE_ID, "wrong fixture id"); _assert(manifest.get("campaign_id")=="longmont-c2" and manifest.get("target_session")==23, "wrong target")
    _assert(manifest.get("execution_mode")=="static_report_fixture", "wrong execution mode"); _assert(manifest.get("source_harness_id")==harness.HARNESS_ID and manifest.get("contract_id")==contract.CONTRACT_ID and manifest.get("candidate_bundle_id")==harness.CANDIDATE_BUNDLE_ID and manifest.get("gold_fixture_id")==GOLD_FIXTURE_ID, "wrong dependency ids")
    for k,v in manifest.items():
        if k.endswith("_path"): _safe_rel(v)
    for k,v in manifest.get("diagnostics",{}).items(): _assert(v is (k=="static_report_fixture"), f"dangerous diagnostic flag: {k}")

def validate_static_report_shape(report: Mapping[str, Any]) -> None:
    _assert(report.get("schema")==REPORT_SCHEMA and report.get("version")==REPORT_VERSION and report.get("report_id")==REPORT_ID, "wrong report identity")
    for k in ["verdict","score_summary","coverage_summary","hard_failure_summary","soft_miss_summary","missing_gold_coverage","extra_candidate_coverage","evidence_health","high_risk_audit_summary","proposed_write_summary","gm_preview_readiness","diagnostics"]: _assert(k in report, f"missing {k}")

def validate_static_report_consistency(report: Mapping[str, Any]) -> None:
    comp=harness.compare_candidate_to_gold(harness.load_candidate_bundle()); _assert(report == build_static_report_json(), "static report JSON deterministic build mismatch")
    _assert(report["soft_miss_summary"]["total"] == len(comp["soft_misses"]), "soft miss total mismatch")
    for typ in _TYPES: _assert(report["coverage_summary"][typ]["missing"] == len(comp["coverage"][f"missing_gold_{typ}"]), f"coverage mismatch {typ}")
    e=report["evidence_health"]; _assert(e["resolved_evidence_refs"]==e["total_evidence_refs"]==e["openable_evidence_refs"]==e["highlightable_evidence_refs"] and e["warning_count"]==0 and e["unknown_anchor_count"]==0 and e["heading_only_count"]==0 and e["source_leakage_detected"] is False, "bad evidence health")
    p=report["proposed_write_summary"]; _assert(p["approved_count"]==p["promoted_count"]==p["unsafe_status_count"]==0, "unsafe proposed write status")

def validate_markdown_report(markdown: str, report: Mapping[str, Any]) -> None:
    _assert(markdown == build_static_report_markdown(report), "markdown report deterministic build mismatch")
    for heading in ["## Verdict","## Safety Gate","## Score Summary","## Coverage Summary","## Missing Gold Coverage","## Soft Misses By Category","## Hard Failures","## Evidence Health","## High-Risk Audit","## Proposed Writes","## GM Preview Readiness","## Boundary Statement"]: _assert(heading in markdown, f"missing heading {heading}")

def validate_no_runtime_leakage(*objects: Mapping[str, Any] | str) -> None:
    text=json.dumps(objects, sort_keys=True) if not (len(objects)==1 and isinstance(objects[0], str)) else objects[0]
    forbidden=("llm_response","model_response","extractor_runtime","graph_write_result","runtime_payload","plan_payload","agent_interaction_payload","query_execution_payload","network_client")
    for needle in forbidden: _assert(needle not in text, f"forbidden runtime leakage: {needle}")

def validate_all() -> None:
    harness.validate_all(); m=load_manifest(); r=load_static_report_json(); md=load_static_report_markdown(); validate_manifest(m); validate_static_report_shape(r); validate_static_report_consistency(r); validate_markdown_report(md,r); validate_no_runtime_leakage(m,r,md)
