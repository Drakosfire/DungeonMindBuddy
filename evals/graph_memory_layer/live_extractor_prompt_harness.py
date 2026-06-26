"""Gated live extractor prompt harness helpers (manual LLM dogfood only)."""
from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
from typing import Any, Mapping

SCHEMA="dmb_live_extractor_prompt_manifest_v0"; VERSION="0.1"; FIXTURE_ID="graph-memory:live-extractor-prompt-harness:v0"
PACKET_SCHEMA="dmb_live_extractor_prompt_packet_manifest_v0"; SUMMARY_SCHEMA="dmb_live_extractor_source_packet_summary_v0"
EXAMPLE_DIR="evals/graph_memory_layer/examples/live_extractor_prompt_harness"
MANIFEST_PATH=f"{EXAMPLE_DIR}/live_extractor_prompt_manifest.json"; SAMPLE_PACKET_PATH=f"{EXAMPLE_DIR}/session_23_prompt_packet_manifest.json"
RUNS_DIR="evals/graph_memory_layer/runs/live_extractor_prompt_harness"
SESSION_23_RUN_BUNDLE="evals/graph_memory_layer/examples/live_recap_ingest_run_bundle/session_23_sample"
SESSION_23_SOURCE_RECAP="evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md"
MODES=("one_shot","two_shot")
PROMPT_FILES={"one_shot":["one_shot_prompt.md"],"two_shot":["observation_extraction_prompt.md","graph_assembly_prompt.md"]}
REQUIRED_SECTIONS=("candidate_nodes","candidate_edges","session_beats","unnamed_important_concepts","ignored_items","deferred_items","proposed_writes","high_risk_claims","diagnostics")
FORBIDDEN_OUTPUT_TOKENS=("approved_memory","committed graph","canon promotion","fact promotion","write_execution_result","query_result","runtime_payload","/plan payload","Agent Interaction payload","corpus mutation")

class HarnessValidationError(ValueError): pass

def repo_root()->Path: return Path(__file__).resolve().parents[2]
def _abs(p:Path)->Path: return p if p.is_absolute() else repo_root()/p
def _load_json(p:Path)->dict[str,Any]: return json.loads(_abs(p).read_text(encoding="utf-8"))
def _sha_text(t:str)->str: return hashlib.sha256(t.encode()).hexdigest()
def _is_glob(s:str)->bool: return any(c in s for c in "*?[]{}")
def _assert(c:bool,msg:str)->None:
    if not c: raise HarnessValidationError(msg)

def validate_source_recap_path(path:Path)->Path:
    _assert(not _is_glob(str(path)),"source_recap_is_glob"); p=_abs(path)
    _assert(p.exists(),"source_recap_missing"); _assert(p.is_file(),"source_recap_is_directory")
    return p

def validate_output_path(out_dir:Path,*,allow_overwrite:bool=False)->Path:
    _assert(not _is_glob(str(out_dir)),"output_is_glob"); root=repo_root(); target=_abs(out_dir).resolve(); allowed=(root/RUNS_DIR).resolve()
    _assert(target != allowed and allowed in target.parents,"output_outside_allowed_run_dir")
    if allow_overwrite: _assert(target != allowed,"cannot_overwrite_run_root")
    return target

def load_run_bundle(run_bundle:Path)->dict[str,Any]:
    base=_abs(run_bundle); _assert(base.exists() and base.is_dir(),"run_bundle_missing")
    names=("run_manifest","source_artifact","source_units","source_span_index","provenance_index","diagnostics")
    return {n:json.loads((base/f"{n}.json").read_text(encoding="utf-8")) for n in names}

def verify_run_bundle_and_source(run_bundle:Path, source_recap:Path)->dict[str,Any]:
    b=load_run_bundle(run_bundle); p=validate_source_recap_path(source_recap); text=p.read_text(encoding="utf-8")
    m=b["run_manifest"]; d=b["diagnostics"]; boundary=d.get("boundary",{})
    _assert(_sha_text(text)==m["source"]["input_sha256"],"source_recap_sha256_mismatch")
    _assert(len(text.splitlines())==m["source"]["input_line_count"],"source_recap_line_count_mismatch")
    _assert(d.get("status")=="ready","run_bundle_diagnostics_not_ready")
    for k in ("graph_write_allowed","query_execution_allowed","plan_connected","agent_interaction_connected","corpus_scan_allowed","corpus_mutation_allowed"):
        _assert(boundary.get(k) is False, f"unsafe_run_bundle_boundary:{k}")
    units=b["source_units"]["units"]; spans=b["source_span_index"]["spans"]; span_by_unit={s["source_unit_id"]:s for s in spans}
    _assert(len(span_by_unit)==len(spans),"duplicate_source_span_refs")
    for u in units:
        sp=span_by_unit.get(u["source_unit_id"]); _assert(bool(sp and sp.get("source_span_ref_id")),"source_unit_missing_span_ref")
    return {"bundle":b,"source_text":text,"source_path":p,"span_by_unit":span_by_unit}

def source_packet_rows(verified:Mapping[str,Any])->list[dict[str,Any]]:
    lines=verified["source_text"].splitlines(); rows=[]
    for u in verified["bundle"]["source_units"]["units"]:
        sp=verified["span_by_unit"][u["source_unit_id"]]
        text="\n".join(lines[u["line_start"]-1:u["line_end"]])
        rows.append({"source_span_ref_id":sp["source_span_ref_id"],"source_unit_id":u["source_unit_id"],"line_start":u["line_start"],"line_end":u["line_end"],"text":text})
    return rows

def _source_packet_md(rows:list[dict[str,Any]])->str:
    parts=[]
    for r in rows:
        parts.append(f"### {r['source_span_ref_id']} / {r['source_unit_id']} / lines {r['line_start']}-{r['line_end']}\n\n```text\n{r['text']}\n```")
    return "\n\n".join(parts)

def safety_instructions()->str:
    return """You are producing preview-only graph-memory candidates for manual benchmark review.
Return only JSON shaped like Candidate Graph Preview IR with sections: candidate_nodes, candidate_edges, session_beats, unnamed_important_concepts, ignored_items, deferred_items, proposed_writes, high_risk_claims, diagnostics.
Every positive factual candidate MUST include evidence_refs with source_span_ref_id values from the source packet.
Preserve uncertainty: do not resolve cliffhangers, bind aliases or identities, infer relationships, or produce exact counts unless directly supported by cited spans.
High-risk claims include alias binding, identity binding, inferred relationships, cliffhanger outcomes, uncertain counts, unsupported canon promotion, and any claim with weak evidence.
Forbidden: do not approve memory, do not commit graph records, do not promote canon or facts, do not execute writes, do not produce query results, do not emit runtime payloads, do not emit /plan payloads, do not emit Agent Interaction payloads, and do not mutate corpus.
Proposed writes are allowed only as pending preview intent with risk flags and evidence_refs; they are not approved or persisted."""

def render_prompts(mode:str, verified:Mapping[str,Any])->dict[str,str]:
    _assert(mode in MODES,"unknown_mode"); rows=source_packet_rows(verified); src=_source_packet_md(rows); instr=safety_instructions()
    schema='''Expected JSON top-level sections: candidate_nodes, candidate_edges, session_beats, unnamed_important_concepts, ignored_items, deferred_items, proposed_writes, high_risk_claims, diagnostics. Each meaningful object needs candidate id, label or summary, candidate type, evidence_refs, extraction_confidence, risk_flags, semantic/lifecycle state, and preview-only state.'''
    if mode=="one_shot":
        return {"one_shot_prompt.md":f"# Live Graph Memory Extractor — One Shot\n\n{instr}\n\n{schema}\n\n## Source Packet\n\n{src}\n"}
    return {
      "observation_extraction_prompt.md":f"# Live Graph Memory Extractor — Observation Extraction\n\n{instr}\n\nExtract source-grounded observations, session beats, named entities, unnamed important concepts, uncertainty/deferred material, and ignored/non-memory details. Return JSON observations only; every observation cites source_span_ref_id.\n\n## Source Packet\n\n{src}\n",
      "graph_assembly_prompt.md":f"# Live Graph Memory Extractor — Graph Assembly\n\n{instr}\n\nUsing the manually supplied observation_extraction JSON, assemble Candidate Graph Preview IR-shaped JSON. {schema}\n\nDo not add facts not present in the observation JSON and its cited source_span_ref_id evidence.\n"
    }

def build_prompt_packet_manifest(mode:str, verified:Mapping[str,Any], out_dir:Path|None=None)->dict[str,Any]:
    b=verified["bundle"]; rows=source_packet_rows(verified)
    return {"schema":PACKET_SCHEMA,"version":VERSION,"fixture_id":FIXTURE_ID,"mode":mode,"run_id":b["run_manifest"]["run_id"],"campaign_id":b["run_manifest"]["campaign_id"],"session_id":b["run_manifest"]["session_id"],"source":{"input_sha256":b["run_manifest"]["source"]["input_sha256"],"input_line_count":b["run_manifest"]["source"]["input_line_count"],"source_units":len(rows),"source_span_refs":[r["source_span_ref_id"] for r in rows]},"prompt_files":PROMPT_FILES[mode],"output_contract":{"target":"Candidate Graph Preview IR-shaped JSON","required_sections":list(REQUIRED_SECTIONS),"preview_only":True},"safety":{"manual_llm_only":True,"no_api_key_required":True,"graph_writes_allowed":False,"query_execution_allowed":False,"runtime_connected":False,"plan_connected":False,"agent_interaction_connected":False,"corpus_scan_allowed":False,"corpus_mutation_allowed":False},"out_dir":str(out_dir) if out_dir else None}

def build_source_packet_summary(verified:Mapping[str,Any])->dict[str,Any]:
    rows=source_packet_rows(verified); b=verified["bundle"]
    return {"schema":SUMMARY_SCHEMA,"version":VERSION,"run_id":b["run_manifest"]["run_id"],"source_sha256":b["run_manifest"]["source"]["input_sha256"],"source_line_count":b["run_manifest"]["source"]["input_line_count"],"source_units":len(rows),"source_span_refs":[{"source_span_ref_id":r["source_span_ref_id"],"source_unit_id":r["source_unit_id"],"line_start":r["line_start"],"line_end":r["line_end"]} for r in rows],"raw_full_text_included":False}

def write_prompt_packet(mode:str, run_bundle:Path, source_recap:Path, out_dir:Path,*,allow_overwrite:bool=False)->dict[str,Any]:
    target=validate_output_path(out_dir,allow_overwrite=allow_overwrite); verified=verify_run_bundle_and_source(run_bundle,source_recap)
    if target.exists() and any(target.iterdir()):
        _assert(allow_overwrite,"output_exists"); shutil.rmtree(target)
    target.mkdir(parents=True,exist_ok=True)
    prompts=render_prompts(mode,verified); manifest=build_prompt_packet_manifest(mode,verified,target); summary=build_source_packet_summary(verified)
    (target/"prompt_packet_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (target/"source_packet_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    for name,text in prompts.items(): (target/name).write_text(text,encoding="utf-8")
    (target/"manual_run_notes.md").write_text("# Manual Live Extractor Notes\n\nPaste prompts into a model manually. Save untrusted JSON output as candidate_output.json, then validate before review. No graph writes or promotion occur here.\n",encoding="utf-8")
    return manifest

def load_manifest()->dict[str,Any]: return _load_json(Path(MANIFEST_PATH))
def load_sample_packet_manifest()->dict[str,Any]: return _load_json(Path(SAMPLE_PACKET_PATH))

def validate_prompt_manifest(m:Mapping[str,Any])->None:
    _assert(m.get("schema")==SCHEMA and m.get("version")==VERSION,"wrong_manifest_schema")
    _assert(m.get("fixture_id")==FIXTURE_ID,"wrong_fixture_id"); _assert(set(m.get("modes",{}))==set(MODES),"wrong_modes")
    for mode in MODES: _assert(m["modes"][mode]["prompt_files"]==PROMPT_FILES[mode],f"bad_prompt_files:{mode}")
    for k,v in m.get("safety",{}).items(): _assert(v is (k in {"manual_llm_only","preview_only","source_span_required"}),f"unsafe_manifest:{k}")

def validate_prompt_packet_manifest(p:Mapping[str,Any])->None:
    _assert(p.get("schema")==PACKET_SCHEMA and p.get("version")==VERSION,"wrong_packet_schema"); _assert(p.get("mode") in MODES,"bad_packet_mode")
    _assert(p.get("prompt_files")==PROMPT_FILES[p["mode"]],"bad_packet_files"); _assert(set(REQUIRED_SECTIONS)<=set(p["output_contract"]["required_sections"]),"missing_required_sections")
    for k,v in p.get("safety",{}).items(): _assert(v is (k in {"manual_llm_only","no_api_key_required"}),f"unsafe_packet:{k}")

def validate_candidate_output(candidate:Mapping[str,Any], allowed_span_refs:set[str]|None=None)->dict[str,Any]:
    text=json.dumps(candidate,sort_keys=True)
    for tok in FORBIDDEN_OUTPUT_TOKENS: _assert(tok not in text, f"forbidden_candidate_output:{tok}")
    for section in REQUIRED_SECTIONS: _assert(section in candidate, f"missing_section:{section}")
    classes={s:len(candidate.get(s,[])) for s in REQUIRED_SECTIONS if isinstance(candidate.get(s),list)}
    if allowed_span_refs:
        refs=[]
        def walk(o):
            if isinstance(o,dict):
                for r in o.get("evidence_refs",[]):
                    if isinstance(r,dict) and "source_span_ref_id" in r: refs.append(r["source_span_ref_id"])
                    elif isinstance(r,str): refs.append(r)
                for v in o.values(): walk(v)
            elif isinstance(o,list):
                for v in o: walk(v)
        walk(candidate); _assert(all(r in allowed_span_refs for r in refs),"unknown_source_span_ref")
    return {"candidate_class_counts":classes,"benchmark_comparison_ready":True,"preview_only":True}

def validate_all()->None:
    validate_prompt_manifest(load_manifest()); validate_prompt_packet_manifest(load_sample_packet_manifest())
    verified=verify_run_bundle_and_source(Path(SESSION_23_RUN_BUNDLE),Path(SESSION_23_SOURCE_RECAP))
    for mode in MODES:
        prompts=render_prompts(mode,verified); packet=build_prompt_packet_manifest(mode,verified); validate_prompt_packet_manifest(packet)
        joined="\n".join(prompts.values()); _assert("source_span_ref_id" in joined and "Preserve uncertainty" in joined and "High-risk claims" in joined,"prompt_missing_safety_text")
