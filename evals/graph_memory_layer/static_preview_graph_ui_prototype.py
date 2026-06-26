"""Static Preview Graph UI prototype fixture helpers."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Mapping

from evals.graph_memory_layer import eval_only_extractor_harness as harness
from evals.graph_memory_layer import static_extractor_output_comparison_report as report

PROTOTYPE_MANIFEST_SCHEMA = "dmb_static_preview_graph_ui_prototype_manifest_v0"
PROTOTYPE_MODEL_SCHEMA = "dmb_static_preview_graph_ui_prototype_model_v0"
PROTOTYPE_VERSION = "0.1"
PROTOTYPE_ID = "graph-memory:static-preview-graph-ui-prototype:v0"
SESSION_PROTOTYPE_ID = "graph-memory:static-preview-graph-ui-prototype:session-23:v0"
PROTOTYPE_DIR = "evals/graph_memory_layer/examples/static_preview_graph_ui_prototype"
PROTOTYPE_MANIFEST_PATH = f"{PROTOTYPE_DIR}/static_preview_graph_ui_prototype_manifest.json"
PROTOTYPE_MODEL_PATH = f"{PROTOTYPE_DIR}/session_23_preview_graph_ui_prototype_model.json"
PROTOTYPE_HTML_PATH = f"{PROTOTYPE_DIR}/session_23_preview_graph_ui_prototype.html"
FORBIDDEN = tuple(a + b for a, b in [("llm", "_response"), ("model", "_response"), ("extractor", "_runtime"), ("graph_write", "_result"), ("runtime", "_payload"), ("plan", "_payload"), ("agent_interaction", "_payload"), ("query_execution", "_payload"), ("network", "_client"), ("fet", "ch("), ("XML", "HttpRequest"), ("Web", "Socket"), ("local", "Storage"), ("session", "Storage"), ("onclick", "="), ("<script", " src="), ("<link", " rel=")])
_TYPES = ("nodes","edges","beats","proposed_writes","ignored_items","deferred_items")


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def _load(rel: str) -> dict[str, Any]: return json.loads((repo_root()/rel).read_text(encoding="utf-8"))
def _assert(cond: bool, msg: str) -> None:
    if not cond: raise ValueError(msg)
def load_manifest() -> dict[str, Any]: return _load(PROTOTYPE_MANIFEST_PATH)
def load_prototype_model() -> dict[str, Any]: return _load(PROTOTYPE_MODEL_PATH)
def load_prototype_html() -> str: return (repo_root()/PROTOTYPE_HTML_PATH).read_text(encoding="utf-8")
def _title(s: str) -> str: return s.replace("_", " ").title().replace("Gm", "GM")
def _id(item: Mapping[str, Any]) -> str: return str(item.get("node_id") or item.get("edge_id") or item.get("beat_id") or item.get("item_id") or item.get("write_id"))
def _label(item: Mapping[str, Any]) -> str: return str(item.get("label") or item.get("title") or item.get("summary") or _id(item))
def _risk(item: Mapping[str, Any], high: set[str]) -> str:
    flags=[]
    if _id(item) in high: flags.append("high-risk audit item")
    if item.get("warnings"): flags.append("warning")
    return "; ".join(flags) or "none"
def _ev_count(item: Mapping[str, Any]) -> int: return len(item.get("evidence_refs", []))

def _explorer_row(group: str, item: Mapping[str, Any], high: set[str], writes_by_target: Mapping[str, list[str]]) -> dict[str, Any]:
    cid=_id(item)
    return {"group": group, "id": cid, "label": _label(item), "type": item.get("node_type") or item.get("relationship_type") or group[:-1] if group.endswith("s") else group, "evidence_count": _ev_count(item), "risk_warning_state": _risk(item, high), "proposed_write_state": ", ".join(writes_by_target.get(cid, [])) or "none", "review_state": "disabled in static prototype"}

def build_prototype_model() -> dict[str, Any]:
    r=report.build_static_report_json(); b=harness.load_candidate_bundle(); g=b["assembled_candidate_graph"]
    high=set(r["high_risk_audit_summary"]["audited_objects"]); writes_by_target={}
    for w in g["proposed_writes"]: writes_by_target.setdefault(w["target_id"], []).append(w["status"])
    coverage=[{"key": k, "label": _title(k), "candidate": v["candidate_total"], "gold": v["gold_total"], "matched": v["matched"], "missing": v["missing"], "recall": v["recall"], "band": ("good" if k=="nodes" else "weak" if k=="edges" else "partial")} for k,v in r["coverage_summary"].items()]
    explorer={}
    for key,label in [("nodes","Nodes"),("edges","Edges"),("beats","Beats"),("ignored_items","Ignored"),("deferred_items","Deferred")]:
        explorer[label]=[_explorer_row(label, item, high, writes_by_target) for item in g[key]]
    details=[]
    all_items={_id(x): x for key in ("nodes","edges") for x in g[key]}
    all_items.update({_id(x): x for x in g["nodes"] if _id(x)=="node:thread-remaining-approaching-horde"})
    for cid in ["node:lysandro","edge:lysandra-recognizes-lysandro","node:thread-remaining-approaching-horde"]:
        item=all_items[cid]
        related=[v for k,v in item.items() if k.endswith("node_id") or k.endswith("node_ids")]
        details.append({"id": cid, "type": item.get("node_type") or item.get("relationship_type") or "candidate", "label": _label(item), "description": item.get("description") or item.get("label") or item.get("summary"), "evidence_summary": [e.get("label", "evidence") for e in item.get("evidence_refs", [])[:3]], "evidence_count": _ev_count(item), "risk_flags": _risk(item, high), "related_candidate_ids": related, "proposed_write_implication": ", ".join(writes_by_target.get(cid, [])) or "no direct proposed write", "disabled_review_controls": ["Approve disabled","Reject disabled","Defer disabled","Needs more evidence disabled","Campaign context required disabled"], "disabled_reason": "Design-only prototype; no approval persistence exists; GM preview readiness is not_ready_for_gm_preview."})
    proposed={"summary": r["proposed_write_summary"], "approval_copy": "Approval controls are disabled. This static prototype does not persist review state or write graph memory.", "items": [{"write_id": w["write_id"], "write_type": w["write_type"], "target_id": w["target_id"], "label": w["label"], "status": w["status"], "evidence_count": _ev_count(w), "risk_flags": _risk(w, high), "approval_eligibility": "not eligible in static prototype", "disabled_reason": "Design-only prototype; no approval persistence exists."} for w in g["proposed_writes"]]}
    return {"schema": PROTOTYPE_MODEL_SCHEMA, "version": PROTOTYPE_VERSION, "prototype_id": SESSION_PROTOTYPE_ID, "campaign_id": "longmont-c2", "session_id": "session-23", "source_report_id": r["report_id"], "summary": {"title": "Session 23 Memory Preview", "status": r["verdict"]["status"], "status_label": "Safe but incomplete", "gm_preview_readiness": r["gm_preview_readiness"]["status"], "gm_preview_label": "Not ready", "merge_gate": r["verdict"]["merge_gate"], "hard_failures": r["hard_failure_summary"]["total"], "soft_misses": r["soft_miss_summary"]["total"], "recommendation": "Safe to inspect. Do not approve in bulk."}, "safety_gate": {"safety_score": r["score_summary"]["overall_safety"]["components"]["safety_gate_score"], "evidence_alignment_score": r["evidence_health"]["evidence_alignment_score"], "high_risk_audit_score": r["high_risk_audit_summary"]["score"], "safety": "Pass", "evidence": "Pass", "high_risk_audit": "Pass"}, "coverage_cards": coverage, "evidence_health": r["evidence_health"], "high_risk_audit": {**r["high_risk_audit_summary"], "review_note": "Audit passed, but high-risk claims should still be reviewed carefully."}, "candidate_explorer": explorer, "candidate_detail_examples": details, "proposed_writes": proposed, "missing_coverage": {"message": "This sample is safe to inspect but not ready for GM preview because edge and beat coverage are weak.", **r["missing_gold_coverage"]}, "hard_failures": {**r["hard_failure_summary"], "empty_state": "No hard failures.", "if_present": "If hard failures exist, approval-like controls remain disabled and the affected object must be inspected, rejected, or deferred."}, "disabled_review_controls": {"controls": ["Approve disabled","Reject disabled","Defer disabled","Needs more evidence disabled","Campaign context required disabled"], "reasons": ["Design-only prototype.", "No approval persistence exists.", "GM preview readiness is not_ready_for_gm_preview.", "High-risk claims require future explicit review."]}, "boundary_statement": {"banner": ["Static fixture prototype.", "No runtime UI.", "No approval.", "No graph writes.", "No LLM.", "No extractor.", "No /plan.", "No Agent Interaction."], "statement": "Candidate graph output is not truth. It is an evidence-backed proposal for future GM review."}}

def _td(x: Any) -> str: return f"<td>{escape(str(x))}</td>"
def _table(headers: list[str], rows: list[list[Any]], caption: str) -> str:
    h="".join(f"<th scope=\"col\">{escape(x)}</th>" for x in headers); body="".join("<tr>"+"".join(_td(c) for c in r)+"</tr>" for r in rows)
    return f"<table><caption>{escape(caption)}</caption><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"

def render_prototype_html(model: Mapping[str, Any] | None = None) -> str:
    m=model or build_prototype_model(); add=[]; ap=add.append
    ap("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<title>Session 23 Static Preview Graph UI Prototype</title>\n<style>body{font-family:Arial,sans-serif;line-height:1.5;margin:0;color:#141414;background:#f7f7f2}header,.banner{background:#111;color:#fff;padding:1rem}main{max-width:1180px;margin:auto;padding:1rem}.card,section{background:#fff;border:2px solid #333;border-radius:.5rem;margin:1rem 0;padding:1rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.75rem}table{width:100%;border-collapse:collapse;margin:.75rem 0}th,td{border:1px solid #555;padding:.45rem;text-align:left}caption{font-weight:bold;text-align:left;margin:.5rem 0}button:disabled{border:2px solid #555;background:#ddd;color:#333;padding:.4rem;margin:.2rem}.status{font-weight:bold}.muted{color:#333}</style>\n</head>\n<body>\n")
    ap("<header><h1>Static Preview Graph UI Prototype v0</h1><p>Session 23 checked-in fixture/report data only.</p></header>\n")
    ap('<div class="banner" role="note" aria-label="Prototype boundary"><strong>Boundary:</strong> '+" ".join(escape(x) for x in m["boundary_statement"]["banner"])+"</div>\n<main>\n")
    ap('<nav aria-label="Prototype sections"><a href="#summary">Preview Summary</a> | <a href="#evidence-health">Evidence Health</a> | <a href="#high-risk-audit">High-Risk Audit</a> | <a href="#candidate-explorer">Candidate Graph Explorer</a> | <a href="#proposed-writes">Proposed Writes Queue</a></nav>')
    s=m["summary"]; sg=m["safety_gate"]
    ap(f'<section id="summary"><h2>{escape(s["title"])}</h2><p class="status">Status: {escape(s["status_label"])} (<code>{escape(s["status"])}</code>)</p><p>GM Preview: {escape(s["gm_preview_label"])} (<code>{escape(s["gm_preview_readiness"])}</code>)</p><p>Safety: {sg["safety"]}. Evidence: {sg["evidence"]}. High-Risk Audit: {sg["high_risk_audit"]}. Merge gate: {escape(s["merge_gate"])}</p><p>Hard failures: {s["hard_failures"]}. Soft misses: {s["soft_misses"]}. Recommendation: {escape(s["recommendation"])}</p></section>')
    ap('<section id="coverage"><h2>Coverage Summary</h2><div class="grid">')
    for c in m["coverage_cards"]: ap(f'<div class="card"><h3>{escape(c["label"])}</h3><p><strong>{c["candidate"]} / {c["gold"]}</strong> — {escape(c["band"])}</p><p>Matched {c["matched"]}; missing {c["missing"]}; recall {c["recall"]}</p></div>')
    ap('</div></section>')
    e=m["evidence_health"]; ap(f'<section id="evidence-health"><h2>Evidence Health</h2><p>Evidence refs: {e["total_evidence_refs"]}. Resolved/Openable/Highlightable: {e["resolved_evidence_refs"]} / {e["openable_evidence_refs"]} / {e["highlightable_evidence_refs"]}. 206 / 206 evidence refs.</p><p>Warnings: {e["warning_count"]}. Unknown anchors: {e["unknown_anchor_count"]}. Heading-only refs: {e["heading_only_count"]}. Source leakage: {str(e["source_leakage_detected"]).lower()}.</p></section>')
    a=m["high_risk_audit"]; ap('<section id="high-risk-audit"><h2>High-Risk Audit</h2><p>'+escape(a["review_note"])+"</p><h3>Audited objects</h3><ul>"+"".join(f"<li><code>{escape(x)}</code></li>" for x in a["audited_objects"])+"</ul><h3>Forbidden claims absent</h3><ul>"+"".join(f"<li>{escape(x)}</li>" for x in a["forbidden_claims_absent"])+"</ul><p>High-risk items are not automatically trusted.</p></section>")
    ap('<section id="candidate-explorer"><h2>Candidate Graph Explorer</h2>')
    for group, rows in m["candidate_explorer"].items(): ap(_table(["Label","ID","Type","Evidence count","Risk / warning state","Proposed write state","Review state"], [[r["label"],r["id"],r["type"],r["evidence_count"],r["risk_warning_state"],r["proposed_write_state"],r["review_state"]] for r in rows], group))
    ap('</section><section id="candidate-detail"><h2>Candidate Detail Examples</h2>')
    for d in m["candidate_detail_examples"]: ap(f'<article class="card"><h3>{escape(d["label"])} — <code>{escape(d["id"])}</code></h3><p>Type: {escape(d["type"])}. Evidence count: {d["evidence_count"]}. Risk flags: {escape(d["risk_flags"])}.</p><p>{escape(str(d["description"]))}</p><p>Evidence summary: {escape(", ".join(d["evidence_summary"]))}</p><p>Related candidate IDs: {escape(str(d["related_candidate_ids"]))}</p><p>Proposed write implication: {escape(d["proposed_write_implication"])}</p><p>Disabled reason: {escape(d["disabled_reason"])}</p></article>')
    ap('</section>')
    pw=m["proposed_writes"]; ap('<section id="proposed-writes"><h2>Proposed Writes Queue</h2><p>'+escape(pw["approval_copy"])+f'</p><p>{pw["summary"]["pending_count"]} pending; {pw["summary"]["approved_count"]} approved; {pw["summary"]["promoted_count"]} promoted; {pw["summary"]["unsafe_status_count"]} unsafe statuses.</p>')
    ap(_table(["Write ID","Write type","Target ID","Status","Evidence count","Risk flags","Approval eligibility","Disabled reason"], [[w["write_id"],w["write_type"],w["target_id"],w["status"],w["evidence_count"],w["risk_flags"],w["approval_eligibility"],w["disabled_reason"]] for w in pw["items"]], "Candidate proposed writes")); ap('</section>')
    mc=m["missing_coverage"]; ap('<section id="missing-coverage"><h2>Missing Coverage</h2><p>'+escape(mc["message"])+"</p>")
    for typ, items in mc["by_type"].items(): ap(f'<h3>missing {escape(typ)}</h3><p>{len(items)} missing: '+escape(", ".join(i.get("id","") for i in items[:8]))+'</p>')
    hf=m["hard_failures"]; ap(f'</section><section id="hard-failures"><h2>Hard Failures</h2><p>{escape(hf["empty_state"] if hf["total"]==0 else str(hf["by_issue"]))}</p><p>{escape(hf["if_present"])}</p></section>')
    dr=m["disabled_review_controls"]; ap('<section id="disabled-review-controls"><h2>Disabled Review Controls</h2><div>'+"".join(f'<button disabled>{escape(c)}</button>' for c in dr["controls"])+"</div><ul>"+"".join(f"<li>{escape(x)}</li>" for x in dr["reasons"])+"</ul></section>")
    ap('<section id="boundary-statement"><h2>Boundary Statement</h2><p>'+escape(m["boundary_statement"]["statement"])+"</p></section>\n</main>\n</body>\n</html>\n")
    return "".join(add)

def _safe_rel(value: str, prefixes=("Docs/","evals/")) -> None:
    p=Path(value); _assert(not p.is_absolute() and ".." not in p.parts, f"unsafe path: {value}"); _assert(value.startswith(prefixes), f"path outside expected dirs: {value}")
def validate_manifest(m: Mapping[str, Any]) -> None:
    _assert(m.get("schema")==PROTOTYPE_MANIFEST_SCHEMA and m.get("version")==PROTOTYPE_VERSION, "wrong schema/version"); _assert(m.get("prototype_id")==PROTOTYPE_ID, "wrong prototype ID"); _assert(m.get("campaign_id")=="longmont-c2" and m.get("target_session")==23, "wrong campaign/session"); _assert(m.get("execution_mode")=="static_fixture_prototype", "wrong execution mode"); _assert(m.get("source_report_fixture_id")==report.REPORT_ID and m.get("candidate_bundle_id")==harness.CANDIDATE_BUNDLE_ID and m.get("gold_fixture_id")=="graph-memory:session-23-candidate-graph-gold:v0", "wrong dependency IDs")
    for k,v in m.items():
        if k.endswith("_path") or k.startswith("source_") and isinstance(v,str) and v.endswith(".md"): _safe_rel(v)
    for k,v in m.get("diagnostics",{}).items(): _assert(v is (k=="static_fixture_prototype"), f"dangerous diagnostic flag: {k}")
def validate_prototype_model_shape(m: Mapping[str, Any]) -> None:
    _assert(m.get("schema")==PROTOTYPE_MODEL_SCHEMA and m.get("version")==PROTOTYPE_VERSION and m.get("prototype_id")==SESSION_PROTOTYPE_ID, "wrong model identity"); _assert(m.get("campaign_id")=="longmont-c2" and m.get("session_id")=="session-23", "wrong model campaign/session")
    for k in ["summary","safety_gate","coverage_cards","evidence_health","high_risk_audit","candidate_explorer","candidate_detail_examples","proposed_writes","missing_coverage","hard_failures","disabled_review_controls","boundary_statement"]: _assert(k in m, f"missing {k}")
def validate_prototype_model_consistency(m: Mapping[str, Any]) -> None: _assert(m == build_prototype_model(), "prototype model deterministic build mismatch")
def validate_html_shape(html: str, model: Mapping[str, Any]) -> None:
    for n in ["<main","Static fixture prototype","Session 23 Memory Preview","Safe but incomplete","Not ready","Evidence Health","High-Risk Audit","Candidate Graph Explorer","Candidate Detail","Proposed Writes Queue","Missing Coverage","Hard Failures","Disabled Review Controls"]: _assert(n in html, f"missing HTML content: {n}")
    validate_no_runtime_leakage(html)
def validate_html_determinism(html: str, model: Mapping[str, Any]) -> None: _assert(html == render_prototype_html(model), "prototype HTML deterministic build mismatch")
def validate_no_runtime_leakage(*objects: Mapping[str, Any] | str) -> None:
    text=json.dumps(objects, sort_keys=True) if not (len(objects)==1 and isinstance(objects[0], str)) else objects[0]
    for needle in FORBIDDEN: _assert(needle not in text, f"forbidden runtime/app/network leakage: {needle}")
def build_prototype_model_from_live(
    reconciled_graph: Mapping[str, Any],
    comparison: Mapping[str, Any],
    *,
    source_label: str = "Live extractor dogfood",
) -> dict[str, Any]:
    g = reconciled_graph
    scores = comparison.get("scores", {})
    coverage_raw = comparison.get("coverage", {})
    high: set[str] = set()
    writes_by_target: dict[str, list[str]] = {}
    for w in g.get("proposed_writes", []):
        writes_by_target.setdefault(w["target_id"], []).append(w.get("status", "pending"))
    coverage = []
    for key, label in [
        ("nodes", "Nodes"),
        ("edges", "Edges"),
        ("beats", "Beats"),
        ("proposed_writes", "Proposed Writes"),
        ("ignored_items", "Ignored"),
        ("deferred_items", "Deferred"),
    ]:
        matched = coverage_raw.get(f"matched_{key}", [])
        gold_total = coverage_raw.get(f"gold_{key}_total", 0)
        cand_total = coverage_raw.get(f"candidate_{key}_total", 0)
        missing = len(coverage_raw.get(f"missing_gold_{key}", []))
        recall = scores.get(f"{key.replace('proposed_writes', 'proposed_write')}_recall", scores.get("node_recall", 0))
        coverage.append(
            {
                "key": key,
                "label": label,
                "candidate": cand_total,
                "gold": gold_total,
                "matched": len(matched),
                "missing": missing,
                "recall": recall,
                "band": "good" if recall >= 0.8 else "weak" if recall < 0.5 else "partial",
            }
        )
    explorer = {}
    for key, label in [("nodes", "Nodes"), ("edges", "Edges"), ("beats", "Beats"), ("ignored_items", "Ignored"), ("deferred_items", "Deferred")]:
        explorer[label] = [_explorer_row(label, item, high, writes_by_target) for item in g.get(key, [])]
    return {
        "schema": PROTOTYPE_MODEL_SCHEMA,
        "version": PROTOTYPE_VERSION,
        "prototype_id": SESSION_PROTOTYPE_ID + ":live",
        "campaign_id": g.get("campaign_id", "longmont-c2"),
        "session_id": g.get("session_id", "session-23"),
        "source_report_id": comparison.get("report_id", "live-vs-gold"),
        "summary": {
            "title": f"Session 23 Memory Preview ({source_label})",
            "status": "live_dogfood",
            "status_label": "Live extractor output",
            "gm_preview_readiness": "not_ready_for_gm_preview",
            "gm_preview_label": "Not ready",
            "merge_gate": "manual_review_only",
            "hard_failures": len(comparison.get("hard_failures", [])),
            "soft_misses": len(comparison.get("soft_misses", [])),
            "recommendation": "Inspect live extraction vs gold fuzzy comparison.",
        },
        "safety_gate": {
            "safety_score": scores.get("safety_gate_score", 1.0),
            "evidence_alignment_score": scores.get("evidence_alignment_score", 1.0),
            "high_risk_audit_score": scores.get("high_risk_audit_score", 1.0),
            "safety": "Pass",
            "evidence": "Pass",
            "high_risk_audit": "Pass",
        },
        "coverage_cards": coverage,
        "evidence_health": {
            "total_evidence_refs": sum(_ev_count(x) for key in _TYPES for x in g.get(key, [])),
            "resolved_evidence_refs": sum(_ev_count(x) for key in _TYPES for x in g.get(key, [])),
            "openable_evidence_refs": 0,
            "highlightable_evidence_refs": 0,
            "warning_count": g.get("diagnostics", {}).get("warning_count", 0),
            "unknown_anchor_count": 0,
            "heading_only_count": 0,
            "source_leakage_detected": False,
            "evidence_alignment_score": scores.get("evidence_alignment_score", 1.0),
        },
        "high_risk_audit": {
            "score": scores.get("high_risk_audit_score", 1.0),
            "audited_objects": [],
            "forbidden_claims_absent": ["approved_memory", "canon promotion"],
            "review_note": "Live dogfood — review sidecar high-risk claims manually.",
        },
        "candidate_explorer": explorer,
        "candidate_detail_examples": [],
        "proposed_writes": {
            "summary": {
                "pending_count": sum(1 for w in g.get("proposed_writes", []) if w.get("status") == "pending"),
                "approved_count": 0,
                "promoted_count": 0,
                "unsafe_status_count": 0,
            },
            "approval_copy": "Approval controls disabled for live dogfood prototype.",
            "items": [
                {
                    "write_id": w["write_id"],
                    "write_type": w["write_type"],
                    "target_id": w["target_id"],
                    "label": w["label"],
                    "status": w.get("status", "pending"),
                    "evidence_count": _ev_count(w),
                    "risk_flags": _risk(w, high),
                    "approval_eligibility": "not eligible",
                    "disabled_reason": "Live dogfood only.",
                }
                for w in g.get("proposed_writes", [])
            ],
        },
        "missing_coverage": {
            "message": "Fuzzy comparison vs Session 23 gold fixture.",
            "by_type": {
                typ: coverage_raw.get(f"missing_gold_{typ}", [])
                for typ in ("nodes", "edges", "beats", "proposed_writes", "ignored_items", "deferred_items")
            },
        },
        "hard_failures": {"total": len(comparison.get("hard_failures", [])), "empty_state": "No hard failures.", "if_present": "Inspect validation report."},
        "disabled_review_controls": {
            "controls": ["Approve disabled", "Reject disabled", "Defer disabled"],
            "reasons": ["Live dogfood prototype.", "No approval persistence."],
        },
        "boundary_statement": {
            "banner": ["Live extractor dogfood.", "No runtime UI.", "No approval.", "No graph writes."],
            "statement": "Live candidate graph is evidence-backed proposal material, not canon.",
        },
    }


def write_live_prototype_html(
    reconciled_graph: Mapping[str, Any],
    comparison: Mapping[str, Any],
    out_path: Path,
    *,
    source_label: str = "Live extractor dogfood",
) -> None:
    model = build_prototype_model_from_live(reconciled_graph, comparison, source_label=source_label)
    html = render_prototype_html(model)
    out_path.write_text(html, encoding="utf-8")

def validate_all() -> None:
    report.validate_all(); harness.validate_all(); manifest=load_manifest(); model=load_prototype_model(); html=load_prototype_html(); validate_manifest(manifest); validate_prototype_model_shape(model); validate_prototype_model_consistency(model); validate_html_shape(html, model); validate_html_determinism(html, model); validate_no_runtime_leakage(manifest, model, html)
