"""Static query vocabulary fixture helpers for graph memory."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from evals.graph_memory_layer import eval_only_extractor_harness as harness
from evals.graph_memory_layer import static_extractor_output_comparison_report as report
from evals.graph_memory_layer import static_preview_graph_ui_prototype as prototype

QUERY_VOCABULARY_MANIFEST_SCHEMA = "dmb_graph_memory_query_vocabulary_manifest_v0"
QUERY_VOCABULARY_SCHEMA = "dmb_graph_memory_query_vocabulary_fixture_v0"
QUERY_VOCABULARY_VERSION = "0.1"
QUERY_VOCABULARY_FIXTURE_ID = "graph-memory:query-vocabulary-fixture:v0"
SESSION_QUERY_VOCABULARY_ID = "graph-memory:query-vocabulary-fixture:session-23:v0"
QUERY_VOCABULARY_DIR = "evals/graph_memory_layer/examples/query_vocabulary_fixture"
QUERY_VOCABULARY_MANIFEST_PATH = f"{QUERY_VOCABULARY_DIR}/query_vocabulary_manifest.json"
QUERY_VOCABULARY_FIXTURE_PATH = f"{QUERY_VOCABULARY_DIR}/session_23_query_vocabulary_fixture.json"
QUERY_VOCABULARY_REPORT_PATH = f"{QUERY_VOCABULARY_DIR}/session_23_query_vocabulary_report.md"
FORBIDDEN = tuple(a + b for a, b in [("llm", "_response"), ("model", "_response"), ("extractor", "_runtime"), ("network", "_client"), ("fet", "ch("), ("XML", "HttpRequest"), ("Web", "Socket"), ("local", "Storage"), ("session", "Storage")])


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def _load(rel: str) -> dict[str, Any]: return json.loads((repo_root()/rel).read_text(encoding="utf-8"))
def _assert(cond: bool, msg: str) -> None:
    if not cond: raise ValueError(msg)
def load_manifest() -> dict[str, Any]: return _load(QUERY_VOCABULARY_MANIFEST_PATH)
def load_query_vocabulary_fixture() -> dict[str, Any]: return _load(QUERY_VOCABULARY_FIXTURE_PATH)
def load_query_vocabulary_report() -> str: return (repo_root()/QUERY_VOCABULARY_REPORT_PATH).read_text(encoding="utf-8")
def _safe_rel(value: str) -> None:
    p=Path(value); _assert(not p.is_absolute() and ".." not in p.parts, f"unsafe path: {value}"); _assert(value.startswith(QUERY_VOCABULARY_DIR), f"path outside expected eval fixture directory: {value}")

def validate_manifest(manifest: Mapping[str, Any]) -> None:
    _assert(manifest.get("schema")==QUERY_VOCABULARY_MANIFEST_SCHEMA and manifest.get("version")==QUERY_VOCABULARY_VERSION, "wrong schema/version")
    _assert(manifest.get("fixture_id")==QUERY_VOCABULARY_FIXTURE_ID, "wrong fixture ID")
    _assert(manifest.get("campaign_id")=="longmont-c2" and manifest.get("target_session")==23, "wrong campaign/session")
    _assert(manifest.get("execution_mode")=="static_query_vocabulary_fixture", "wrong execution mode")
    _assert(manifest.get("source_static_preview_prototype_id")==prototype.SESSION_PROTOTYPE_ID and manifest.get("source_report_fixture_id")==report.REPORT_ID and manifest.get("candidate_bundle_id")==harness.CANDIDATE_BUNDLE_ID and manifest.get("gold_fixture_id")=="graph-memory:session-23-candidate-graph-gold:v0", "wrong source IDs")
    for k in ["query_vocabulary_path","report_path"]: _safe_rel(str(manifest.get(k,"")))
    for k,v in manifest.get("diagnostics",{}).items(): _assert(v is (k=="static_query_vocabulary_fixture"), f"dangerous diagnostic flag: {k}")

def validate_query_vocabulary_shape(fixture: Mapping[str, Any]) -> None:
    _assert(fixture.get("schema")==QUERY_VOCABULARY_SCHEMA and fixture.get("version")==QUERY_VOCABULARY_VERSION, "wrong fixture schema/version")
    _assert(fixture.get("fixture_id")==SESSION_QUERY_VOCABULARY_ID and fixture.get("campaign_id")=="longmont-c2" and fixture.get("session_id")=="session-23", "wrong fixture identity")
    for key in ["query_intents","safe_queries","unsafe_queries","deferred_queries","unknown_answer_examples","evidence_answer_examples","high_risk_answer_examples","proposed_write_query_examples","answer_shapes","evidence_policies","agent_interaction_readiness","diagnostics"]: _assert(key in fixture, f"missing {key}")

def validate_query_intents(fixture: Mapping[str, Any]) -> None:
    intents=fixture["query_intents"]; ids=[i["intent_id"] for i in intents]
    _assert(len(ids)==len(set(ids)), "duplicate intent IDs")
    for req in ["intent:summarize-session-preview","intent:explain-candidate","intent:ask-what-happened","intent:ask-relationship","intent:list-unresolved-threats","intent:proposed-write-status","intent:canonical-fact-claim"]: _assert(req in ids, f"missing intent {req}")
    for i in intents: _assert(i.get("may_write_memory") is False and i.get("may_execute_runtime_query") is False, "intent allows unsafe behavior")
    by={i["intent_id"]:i for i in intents}; _assert(by["intent:canonical-fact-claim"]["requires_approved_memory"] is True, "canonical fact intent must require approved memory"); _assert(by["intent:ask-relationship"]["requires_evidence"] is True, "relationship intent requires evidence")

def _intent_ids(fixture: Mapping[str, Any]) -> set[str]: return {i["intent_id"] for i in fixture["query_intents"]}
def validate_safe_queries(fixture: Mapping[str, Any]) -> None:
    _assert(len(fixture["safe_queries"])>=12, "too few safe queries")
    for q in fixture["safe_queries"]: _assert(q["intent_id"] in _intent_ids(fixture) and q.get("expected_answer_shape") and ("evidence" in q.get("required_evidence_policy","") or "report" in q.get("required_evidence_policy","")) and q.get("may_write_memory") is False and q.get("must_label_preview") is True, "invalid safe query")
def validate_unsafe_queries(fixture: Mapping[str, Any]) -> None:
    qs=fixture["unsafe_queries"]; text=json.dumps(qs)
    _assert(len(qs)>=10, "too few unsafe queries")
    for q in qs: _assert(q.get("blocked_reason"), "unsafe query missing blocked reason")
    for n in ["Questionable Company","second wave","lightning bolt","How many shadows","Approve all","Write this graph memory","/plan","Agent Interaction","Promote this preview","Run a graph query"]: _assert(n in text, f"missing unsafe example: {n}")
def validate_deferred_queries(fixture: Mapping[str, Any]) -> None:
    qs=fixture["deferred_queries"]; text=json.dumps(qs)
    _assert(len(qs)>=6, "too few deferred queries")
    for q in qs: _assert(q.get("expected_answer_shape")=="unknown_or_deferred" and "does not resolve" in q.get("expected_behavior",""), "invalid deferred query")
    for n in ["golem-like creature","monster eye changes","refugees contaminated","lightning bolt cliffhanger"]: _assert(n in text, f"missing deferred example: {n}")
def validate_answer_shapes(fixture: Mapping[str, Any]) -> None:
    ids={a["answer_shape_id"]:a for a in fixture["answer_shapes"]}
    for req in ["answer:evidence-backed-summary","answer:candidate-with-evidence","answer:high-risk-evidence-backed","answer:unknown-or-deferred","answer:pending-write-explanation"]: _assert(req in ids, f"missing answer shape {req}")
    text=json.dumps(fixture["answer_shapes"]); _assert("graph_write_result" in text and "agent_action" in text and "runtime_query_result" in text, "answer shapes must forbid runtime write/agent fields")
def validate_evidence_policies(fixture: Mapping[str, Any]) -> None:
    ids={p["policy_id"]:p for p in fixture["evidence_policies"]}
    for req in ["evidence:positive-answer-requires-refs","evidence:high-risk-warning-required","evidence:preview-label-required","evidence:no-canon-promotion"]: _assert(ids.get(req,{}).get("hard_failure_if_missing") is True, f"missing hard evidence policy {req}")
def validate_known_object_references(fixture: Mapping[str, Any]) -> None:
    graph=harness.load_candidate_bundle()["assembled_candidate_graph"]; known=set()
    for key in ["nodes","edges","beats","deferred_items","proposed_writes","ignored_items"]:
        for item in graph.get(key,[]): known.add(str(item.get("node_id") or item.get("edge_id") or item.get("beat_id") or item.get("item_id") or item.get("write_id")))
    known.update({"deferred:golem-like-creature-identity","deferred:monster-eye-changes-source","deferred:edge-refugee-contamination-risk"})
    for oid in fixture.get("known_object_references",[]): _assert(oid in known, f"unknown object reference {oid}")
def validate_agent_interaction_boundary(fixture: Mapping[str, Any]) -> None:
    ai=fixture["agent_interaction_readiness"]; _assert(ai.get("status")=="not_ready" and ai.get("allowed_now")==[], "Agent Interaction must be not_ready")
    for n in ["approved_memory_contract","agent_interaction_chip_payload_contract"]: _assert(n in ai.get("blocked_until_future_rungs",[]), f"missing future rung {n}")
    for n in ["agent_action","plan_payload","agent_interaction_payload","runtime_query_result","approved_memory_claim"]: _assert(n in ai.get("must_not_emit",[]), f"missing must_not_emit {n}")

def build_query_vocabulary_report(fixture: Mapping[str, Any] | None = None) -> str:
    f=fixture or load_query_vocabulary_fixture(); lines=["# Graph Memory Query Vocabulary Fixture — Session 23", "", "## Purpose", "", "Defines safe query, unsafe query, and deferred query vocabulary before runtime retrieval exists.", "", "## Boundary", "", "This is a static query vocabulary fixture.", "It does not execute graph retrieval.", "It does not execute graph queries.", "It does not call an LLM.", "It does not write graph memory.", "It does not approve writes.", "It does not connect /plan.", "It does not connect Agent Interaction.", "It does not promote facts or canon.", "It does not change runtime behavior.", "", "## Query Intent Summary", ""]
    lines += [f"- `{i['intent_id']}` — {i['label']} ({i['category']}): {i['answer_mode']}" for i in f["query_intents"]]
    lines += ["", "## Safe Query Examples", "", f"Safe query examples: {len(f['safe_queries'])}"] + [f"- `{q['query_id']}` — {q['natural_language_query']}" for q in f["safe_queries"]]
    lines += ["", "## Unsafe Query Examples", "", f"Unsafe query examples: {len(f['unsafe_queries'])}"] + [f"- `{q['query_id']}` — {q['natural_language_query']} ({q['unsafe_category']})" for q in f["unsafe_queries"]]
    lines += ["", "## Deferred Query Examples", "", f"Deferred query examples: {len(f['deferred_queries'])}"] + [f"- `{q['query_id']}` — {q['natural_language_query']}" for q in f["deferred_queries"]]
    lines += ["", "## Evidence Policy", ""] + [f"- `{p['policy_id']}` — {p['description']}" for p in f["evidence_policies"]]
    lines += ["", "## Answer Shapes", ""] + [f"- `{a['answer_shape_id']}` requires {', '.join(a['required_fields'])}." for a in f["answer_shapes"]]
    lines += ["", "## High-Risk Query Behavior", "", "High-risk query answers require explicit warnings, evidence refs, separate span notes, limitations, and no alias binding as fact.", "", "## Proposed Write Query Behavior", "", "Proposed-write answers may explain pending writes only; they must not approve writes or write graph memory.", "", "## Unknown / Deferred Answer Behavior", "", "Unknown/deferred answers must say the source does not resolve the question, preserve deferred item IDs, and must not invent.", "", "## Agent Interaction Readiness", "", f"Agent Interaction readiness: {f['agent_interaction_readiness']['status']}. {f['agent_interaction_readiness']['reason']}", "", "## What This Does Not Do", "", "No graph retrieval, graph query execution, graph traversal, LLM calls, extraction, graph writes, approval persistence, corpus scanning, corpus mutation, /plan integration, Agent Interaction integration, fact promotion, canon promotion, or runtime behavior changes.", ""]
    return "\n".join(lines)

def validate_report(report_markdown: str, fixture: Mapping[str, Any]) -> None:
    _assert(report_markdown == build_query_vocabulary_report(fixture), "report markdown deterministic build mismatch")
    for n in ["## Purpose","## Boundary","## Query Intent Summary","## Safe Query Examples","## Unsafe Query Examples","## Deferred Query Examples","## Evidence Policy","## Answer Shapes","## High-Risk Query Behavior","## Proposed Write Query Behavior","## Unknown / Deferred Answer Behavior","## Agent Interaction Readiness","## What This Does Not Do","does not execute graph retrieval","does not execute graph queries","does not call an LLM","does not write graph memory","Agent Interaction readiness: not_ready"]: _assert(n in report_markdown, f"missing report content: {n}")
def validate_no_runtime_leakage(*objects: Mapping[str, Any] | str) -> None:
    text=json.dumps(objects, sort_keys=True) if not (len(objects)==1 and isinstance(objects[0], str)) else objects[0]
    for needle in FORBIDDEN: _assert(needle not in text, f"forbidden runtime/query/agent leakage: {needle}")
    for obj in objects:
        if isinstance(obj, Mapping):
            for k,v in obj.get("diagnostics",{}).items(): _assert(v is (k=="static_query_vocabulary_fixture"), f"dangerous diagnostic flag: {k}")
def validate_all() -> None:
    prototype.validate_all(); report.validate_all(); harness.validate_all(); manifest=load_manifest(); fixture=load_query_vocabulary_fixture(); md=load_query_vocabulary_report(); validate_manifest(manifest); validate_query_vocabulary_shape(fixture); validate_query_intents(fixture); validate_safe_queries(fixture); validate_unsafe_queries(fixture); validate_deferred_queries(fixture); validate_answer_shapes(fixture); validate_evidence_policies(fixture); validate_known_object_references(fixture); validate_agent_interaction_boundary(fixture); validate_report(md, fixture); validate_no_runtime_leakage(manifest, fixture, md)
