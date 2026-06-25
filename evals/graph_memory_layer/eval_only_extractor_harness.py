"""Eval-only extractor harness fixture helpers (static fixtures only; no extraction)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from evals.graph_memory_layer import multi_pass_extraction_contract as contract
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID, HIGH_RISK_EVIDENCE_AUDIT, SOURCE_ARTIFACT_ID, SOURCE_REF_ID,
    parse_gold_candidate_graph, valid_source_anchor_ids, validate_gold_candidate_graph,
    validate_high_risk_evidence_audit,
)
from evals.graph_memory_layer.session_23_recap_ingest_fixture import (
    FIXTURE_ID as SOURCE_FIXTURE_ID, build_source_span_artifacts, load_expected_normalized_recap,
    load_raw_recap, load_source_span_seed_refs, validate_manifest, load_manifest,
)
from src.graph_memory.candidate_graph_preview import CandidateGraphPreview, candidate_graph_preview_from_dict, validate_candidate_graph_preview
from src.graph_memory.source_span import ResolvedEvidence, SourceSpanRef, resolve_many_source_span_refs

HARNESS_SCHEMA = "dmb_eval_only_extractor_harness_manifest_v0"
HARNESS_VERSION = "0.1"
HARNESS_ID = "graph-memory:eval-only-extractor-harness:v0"
CANDIDATE_BUNDLE_SCHEMA = "dmb_eval_only_candidate_output_bundle_v0"
CANDIDATE_BUNDLE_VERSION = "0.1"
CANDIDATE_BUNDLE_ID = "graph-memory:eval-only-candidate-output:session-23:sample-v0"
COMPARISON_REPORT_SCHEMA = "dmb_eval_only_gold_comparison_report_v0"
COMPARISON_REPORT_VERSION = "0.1"
HARNESS_DIR = "evals/graph_memory_layer/examples/eval_only_extractor_harness"
HARNESS_MANIFEST_PATH = f"{HARNESS_DIR}/eval_only_extractor_harness_manifest.json"
CANDIDATE_BUNDLE_PATH = f"{HARNESS_DIR}/session_23_candidate_output_bundle.sample.json"
EXPECTED_REPORT_PATH = f"{HARNESS_DIR}/session_23_expected_comparison_report.sample.json"


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def _load(rel: str) -> dict[str, Any]: return json.loads((repo_root()/rel).read_text(encoding="utf-8"))
def _assert(cond: bool, msg: str) -> None:
    if not cond: raise ValueError(msg)
def _safe_rel(value: str) -> None:
    p=Path(value); _assert(not p.is_absolute() and ".." not in p.parts, f"unsafe path: {value}")

def _walk(obj: Any):
    if isinstance(obj, Mapping):
        for k,v in obj.items(): yield str(k), v; yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj: yield from _walk(v)
    else: yield "", obj

def load_harness_manifest() -> dict[str, Any]: return _load(HARNESS_MANIFEST_PATH)
def load_candidate_bundle() -> dict[str, Any]: return _load(CANDIDATE_BUNDLE_PATH)
def load_expected_comparison_report() -> dict[str, Any]: return _load(EXPECTED_REPORT_PATH)

def validate_no_runtime_leakage(*objects: Mapping[str, Any]) -> None:
    joined=json.dumps(objects, sort_keys=True)
    forbidden_keys={"llm_response","model_response","extractor_runtime","graph_write_result","approved_write","promoted_write","runtime_payload","plan_payload","agent_interaction_payload","query_execution_payload","network_client"}
    forbidden_text=("Questionable Company","second wave","thread-monster-second-wave","resolved battle outcome","approved write","promoted lifecycle")
    _assert(load_expected_normalized_recap() not in joined and load_raw_recap() not in joined, "full recap leakage")
    for key,value in _walk(list(objects)):
        if key in forbidden_keys: raise ValueError(f"forbidden key {key}")
        if isinstance(value, str):
            _assert(not value.startswith("/"), f"absolute path leakage: {value}")
            _assert(value not in {"approved","committed","written","promoted"}, f"committed state leakage: {value}")
    for needle in forbidden_text: _assert(needle not in joined, f"forbidden high-risk text: {needle}")

def validate_harness_manifest(manifest: Mapping[str, Any]) -> None:
    _assert(manifest.get("schema")==HARNESS_SCHEMA and manifest.get("version")==HARNESS_VERSION, "wrong harness schema/version")
    _assert(manifest.get("harness_id")==HARNESS_ID, "wrong harness id")
    _assert(manifest.get("campaign_id")=="longmont-c2" and manifest.get("target_session")==23, "wrong harness target")
    _assert(manifest.get("execution_mode")=="eval_only_fixture", "wrong execution mode")
    _assert(manifest.get("contract_id")==contract.CONTRACT_ID, "wrong contract id")
    _assert(manifest.get("source_fixture_id")==SOURCE_FIXTURE_ID and manifest.get("gold_fixture_id")==GOLD_FIXTURE_ID, "wrong fixture dependency")
    for key,value in manifest.items():
        if key.endswith("_path"):
            _safe_rel(value); _assert(value.startswith("evals/graph_memory_layer/examples/"), f"path outside eval fixtures: {value}")
    for k,v in manifest.get("diagnostics",{}).items():
        _assert(v is (k=="eval_only_fixture"), f"dangerous diagnostic flag: {k}")

def validate_candidate_bundle_shape(bundle: Mapping[str, Any]) -> None:
    _assert(bundle.get("schema")==CANDIDATE_BUNDLE_SCHEMA and bundle.get("version")==CANDIDATE_BUNDLE_VERSION, "wrong bundle schema/version")
    _assert(bundle.get("bundle_id")==CANDIDATE_BUNDLE_ID and bundle.get("contract_id")==contract.CONTRACT_ID, "wrong bundle ids")
    _assert(bundle.get("campaign_id")=="longmont-c2" and bundle.get("session_id")=="session-23", "wrong session")
    _assert(bundle.get("source_fixture_id")==SOURCE_FIXTURE_ID and bundle.get("gold_fixture_id")==GOLD_FIXTURE_ID, "wrong fixture ids")
    _assert(bundle.get("generation_mode")=="static_fixture", "bundle must be static fixture")
    passes=bundle.get("passes",{})
    _assert(list(passes.keys())==contract.PASS_ORDER, "pass order mismatch")
    for pid,schema in zip(contract.PASS_ORDER, contract.ALLOWED_OUTPUT_SCHEMAS):
        p=passes[pid]; _assert(p.get("schema")==schema, f"wrong pass schema: {pid}")
        _assert(p.get("status")=="fixture_output", f"wrong pass status: {pid}")
        _assert(p.get("depends_on_previous_passes")==contract.EXPECTED_PASS_DEPENDENCIES[pid], f"wrong pass deps: {pid}")
        d=p.get("diagnostics",{}); _assert(d.get("static_fixture") is True and d.get("llm_used") is False and d.get("runtime_used") is False, f"dangerous pass diagnostic: {pid}")
    _assert(bundle.get("assembled_candidate_graph"), "missing assembled candidate graph")
    for k,v in bundle.get("diagnostics",{}).items(): _assert(v is (k=="static_fixture"), f"dangerous bundle diagnostic: {k}")

def _evidence_refs_from(obj: Any) -> list[dict[str, Any]]:
    refs=[]
    if isinstance(obj, Mapping):
        if isinstance(obj.get("evidence_refs"), list): refs.extend(obj["evidence_refs"])
        for v in obj.values(): refs.extend(_evidence_refs_from(v))
    elif isinstance(obj, list):
        for v in obj: refs.extend(_evidence_refs_from(v))
    return refs

def _pass_output_contract(pass_id: str) -> Mapping[str, Any]:
    fixture = contract.load_session_23_contract_fixture()
    for row in fixture["passes"]:
        if row["pass_id"] == pass_id:
            return row["output_contract"]
    raise ValueError(f"unknown contract pass: {pass_id}")

def allowed_identity_policies() -> set[str]:
    return set(_pass_output_contract("named_entity_candidate_extraction")["identity_policies"])

def allowed_concept_policies() -> set[str]:
    return set(_pass_output_contract("unnamed_important_concept_extraction")["allowed_concept_policies"])

def validate_candidate_pass_outputs(bundle: Mapping[str, Any]) -> None:
    p=bundle["passes"]; anchors=valid_source_anchor_ids()
    identity_policies = allowed_identity_policies(); concept_policies = allowed_concept_policies()
    _assert(len(p["source_span_selection"].get("selected_spans",[]))>=8, "not enough selected spans")
    for s in p["source_span_selection"]["selected_spans"]: _assert(s["source_anchor_id"] in anchors and s.get("evidence_refs"), "bad selected span")
    _assert(len(p["session_beat_extraction"].get("beat_candidates",[]))>=5, "not enough beats")
    _assert(len(p["named_entity_candidate_extraction"].get("candidates",[]))>=8, "not enough named candidates")
    _assert(len(p["unnamed_important_concept_extraction"].get("candidates",[]))>=6, "not enough concept candidates")
    _assert(len(p["relationship_edge_proposal"].get("relationship_candidates",[]))>=6, "not enough relation candidates")
    _assert(len(p["ignored_deferred_detection"].get("ignored_items",[]))>=2 and len(p["ignored_deferred_detection"].get("deferred_items",[]))>=3, "missing ignored/deferred")
    for cnd in p["named_entity_candidate_extraction"]["candidates"]:
        _assert(cnd.get("identity_policy") in identity_policies and cnd.get("evidence_refs"), f"named candidate missing/unknown policy or evidence: {cnd.get('candidate_id')}")
    for cnd in p["unnamed_important_concept_extraction"]["candidates"]:
        _assert(cnd.get("concept_policy") in concept_policies and cnd.get("evidence_refs"), f"concept candidate missing/unknown policy or evidence: {cnd.get('candidate_id')}")
    aligned={e["object_id"] for e in p["evidence_alignment"].get("alignment_entries",[])}
    for seq in ("nodes","edges","beats","proposed_writes","ignored_items","deferred_items"):
        for o in bundle["assembled_candidate_graph"][seq]:
            oid=o.get("node_id") or o.get("edge_id") or o.get("beat_id") or o.get("write_id") or o.get("item_id")
            _assert(oid in aligned and o.get("evidence_refs"), f"missing alignment/evidence: {oid}")
    _assert(p["candidate_graph_assembly"].get("assembled_candidate_graph_schema")=="dmb_candidate_graph_preview_v0", "bad graph assembly")
    _assert(p["gold_comparison_report"].get("contains_model_output") is False, "comparison pass contains model output")

def parse_candidate_graph(bundle: Mapping[str, Any] | None=None) -> CandidateGraphPreview:
    return candidate_graph_preview_from_dict((bundle or load_candidate_bundle())["assembled_candidate_graph"])

def validate_candidate_graph(bundle: Mapping[str, Any] | None=None) -> None:
    g=parse_candidate_graph(bundle); report=validate_candidate_graph_preview(g)
    _assert(not report.issues, f"candidate graph preview issues: {report.issues}")
    _assert(len(g.nodes)>=12 and len(g.edges)>=8 and len(g.proposed_writes)>=6, "candidate graph too small")

def collect_candidate_evidence_refs(bundle: Mapping[str, Any]) -> list[dict[str, Any]]: return _evidence_refs_from(bundle)

def _to_source_span_ref(ref: Mapping[str, Any]) -> SourceSpanRef:
    seed=next(r for r in load_source_span_seed_refs()["source_span_refs"] if r["source_anchor_id"]==ref.get("source_anchor_id"))
    allowed=set(SourceSpanRef.__dataclass_fields__); data={k:v for k,v in seed.items() if k in allowed}
    data.update({"label": ref.get("label") or seed.get("label"), "evidence_role": ref.get("evidence_role") or "source_evidence"})
    return SourceSpanRef(**data)

def resolve_candidate_evidence_refs(bundle: Mapping[str, Any]) -> list[ResolvedEvidence]:
    refs=[_to_source_span_ref(r) for r in collect_candidate_evidence_refs(bundle)]
    text,structured=build_source_span_artifacts()
    return list(resolve_many_source_span_refs(refs,text_artifacts=text,structured_artifacts=structured,snippet_max_chars=240,context_lines=0))

def validate_candidate_evidence(bundle: Mapping[str, Any]) -> None:
    anchors=valid_source_anchor_ids(); refs=collect_candidate_evidence_refs(bundle)
    _assert(refs, "missing candidate evidence refs")
    for r in refs:
        _assert(r.get("source_artifact_id")==SOURCE_ARTIFACT_ID and r.get("source_ref_id")==SOURCE_REF_ID, "unknown source artifact/ref")
        _assert(r.get("source_anchor_id") in anchors, "unknown evidence anchor")
        _assert(r.get("can_open_source") is True and r.get("can_highlight_span") is True, "evidence not open/highlight")
    for r in resolve_candidate_evidence_refs(bundle):
        _assert(r.can_open_source and r.can_highlight_span and not r.warnings, "unresolved evidence ref")
        _assert(r.preview_snippet.strip() and not r.preview_snippet.lstrip().startswith("#"), "heading-only snippet")

def validate_candidate_high_risk_audit(bundle: Mapping[str, Any]) -> None:
    preview=parse_candidate_graph(bundle)
    present={row["object_id"] for row in HIGH_RISK_EVIDENCE_AUDIT}
    candidate_ids={getattr(o,"node_id",getattr(o,"edge_id",None)) for seq in (preview.nodes,preview.edges) for o in seq}
    if present <= candidate_ids: validate_high_risk_evidence_audit(preview)

def _ids(seq, attr): return {getattr(o, attr) for o in seq}
def _label_map(seq, attr): return {getattr(o, attr): getattr(o, "label", getattr(o, "title", "")) for o in seq}
def _score(m,total): return round((len(m)/total) if total else 1.0, 4)

def compare_candidate_to_gold(bundle: Mapping[str, Any] | None=None) -> dict[str, Any]:
    bundle=bundle or load_candidate_bundle(); hard=[]
    for fn,cat in ((validate_candidate_evidence,"evidence_alignment"),(validate_candidate_high_risk_audit,"high_risk_audit"),(validate_candidate_graph,"candidate_graph"),(validate_no_runtime_leakage,"runtime_leakage")):
        try: fn(bundle)
        except Exception as e: hard.append({"issue":cat,"detail":str(e)})
    cand=parse_candidate_graph(bundle); gold=parse_gold_candidate_graph()
    pairs=[("nodes",cand.nodes,gold.nodes,"node_id","missing_required_node"),("edges",cand.edges,gold.edges,"edge_id","missing_required_edge"),("beats",cand.beats,gold.beats,"beat_id","missing_required_beat"),("proposed_writes",cand.proposed_writes,gold.proposed_writes,"write_id","missing_proposed_write"),("ignored_items",cand.ignored_items,gold.ignored_items,"item_id","missing_ignored_item"),("deferred_items",cand.deferred_items,gold.deferred_items,"item_id","missing_deferred_item")]
    coverage={}; soft=[]
    for name,cseq,gseq,attr,issue in pairs:
        cids=_ids(cseq,attr); gids=_ids(gseq,attr); matched=sorted(cids & gids); missing=sorted(gids-cids); extra=sorted(cids-gids); labels=_label_map(gseq,attr)|_label_map(cseq,attr)
        coverage[f"gold_{name}_total"]=len(gids); coverage[f"candidate_{name}_total"]=len(cids); coverage[f"matched_{name}"]=matched
        coverage[f"missing_gold_{name}"]=[{"id":i,"label":labels.get(i,"")} for i in missing]; coverage[f"extra_candidate_{name}"]=[{"id":i,"label":labels.get(i,"")} for i in extra]
        soft += [{"issue":issue,"detail":i,"label":labels.get(i,"")} for i in missing]
    scores={"node_recall":_score(coverage["matched_nodes"],coverage["gold_nodes_total"]),"edge_recall":_score(coverage["matched_edges"],coverage["gold_edges_total"]),"beat_recall":_score(coverage["matched_beats"],coverage["gold_beats_total"]),"proposed_write_recall":_score(coverage["matched_proposed_writes"],coverage["gold_proposed_writes_total"]),"ignored_item_recall":_score(coverage["matched_ignored_items"],coverage["gold_ignored_items_total"]),"deferred_item_recall":_score(coverage["matched_deferred_items"],coverage["gold_deferred_items_total"]),"node_precision_proxy":_score(coverage["matched_nodes"],coverage["candidate_nodes_total"]),"edge_precision_proxy":_score(coverage["matched_edges"],coverage["candidate_edges_total"]),"evidence_alignment_score":1.0 if not any(h["issue"]=="evidence_alignment" for h in hard) else 0.0,"high_risk_audit_score":1.0 if not any(h["issue"]=="high_risk_audit" for h in hard) else 0.0,"safety_gate_score":1.0 if not hard else 0.0}
    return {"schema":COMPARISON_REPORT_SCHEMA,"version":COMPARISON_REPORT_VERSION,"report_id":"graph-memory:eval-only-comparison-report:session-23:sample-v0","contract_id":contract.CONTRACT_ID,"candidate_bundle_id":bundle["bundle_id"],"gold_fixture_id":GOLD_FIXTURE_ID,"comparison_mode":"static_fixture_vs_gold","hard_failures":hard,"soft_misses":soft,"scores":scores,"coverage":coverage,"diagnostics":{"llm_used":False,"extractor_runtime_used":False,"graph_written":False,"writes_approved":False,"corpus_scanned":False,"corpus_mutated":False,"plan_connected":False,"agent_interaction_connected":False}}

def validate_expected_comparison_report() -> None:
    _assert(compare_candidate_to_gold(load_candidate_bundle()) == load_expected_comparison_report(), "expected comparison report mismatch")

def validate_all() -> None:
    contract.validate_all(); validate_manifest(load_manifest()); validate_gold_candidate_graph()
    m=load_harness_manifest(); b=load_candidate_bundle()
    validate_harness_manifest(m); validate_candidate_bundle_shape(b); validate_candidate_pass_outputs(b); validate_candidate_graph(b); validate_candidate_evidence(b); validate_candidate_high_risk_audit(b); validate_no_runtime_leakage(m,b); validate_expected_comparison_report()

if __name__ == "__main__": validate_all()
