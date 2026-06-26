"""Explicit-input live recap ingest run bundle helpers for graph-memory dogfood."""
from __future__ import annotations

import hashlib, json, re, shutil
from pathlib import Path
from typing import Any, Mapping

LIVE_RECAP_INGEST_MANIFEST_SCHEMA = "dmb_live_recap_ingest_fixture_manifest_v0"
LIVE_RECAP_INGEST_RUN_MANIFEST_SCHEMA = "dmb_live_recap_ingest_run_manifest_v0"
LIVE_RECAP_SOURCE_ARTIFACT_SCHEMA = "dmb_live_recap_source_artifact_v0"
LIVE_RECAP_SOURCE_UNITS_SCHEMA = "dmb_live_recap_source_units_v0"
LIVE_RECAP_SOURCE_SPAN_INDEX_SCHEMA = "dmb_live_recap_source_span_index_v0"
LIVE_RECAP_PROVENANCE_INDEX_SCHEMA = "dmb_live_recap_provenance_index_v0"
LIVE_RECAP_DIAGNOSTICS_SCHEMA = "dmb_live_recap_ingest_diagnostics_v0"
LIVE_RECAP_INGEST_VERSION = "0.1"
LIVE_RECAP_INGEST_FIXTURE_ID = "graph-memory:live-recap-ingest-run-bundle:v0"
SESSION_23_SAMPLE_RUN_ID = "graph-memory:live-recap-ingest:session-23:sample-v0"
LIVE_RECAP_EXAMPLE_DIR = "evals/graph_memory_layer/examples/live_recap_ingest_run_bundle"
SESSION_23_SAMPLE_DIR = f"{LIVE_RECAP_EXAMPLE_DIR}/session_23_sample"
LIVE_RECAP_RUNS_DIR = "evals/graph_memory_layer/runs/live_recap_ingest"
SAMPLE_INPUT_PATH = "evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md"
FORBIDDEN_TOKENS = ["llm_response","model_response","extractor_runtime","proposed_write","graph_write_result","runtime_payload","plan_payload","agent_interaction_payload","query_execution_payload","runtime_query_result","approved_memory_claim","network_client","fetch(","XMLHttpRequest","WebSocket","localStorage","sessionStorage"]

class BundleValidationError(ValueError): pass

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _rel(path: Path) -> Path:
    if not path.is_absolute():
        return path
    try:
        return path.resolve().relative_to(repo_root())
    except ValueError:
        return Path(path.name)

def _sha(text: str | bytes) -> str:
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def _is_glob(s: str) -> bool:
    return any(c in s for c in "*?[]{}")

def validate_explicit_input_path(input_path: Path, *, allow_corpus_input: bool = False) -> None:
    raw = str(input_path)
    if _is_glob(raw): raise BundleValidationError("input_is_glob")
    p = input_path if input_path.is_absolute() else repo_root() / input_path
    if not p.exists(): raise BundleValidationError("input_missing")
    if p.is_dir(): raise BundleValidationError("input_is_directory")
    rel = str(_rel(p))
    if (rel == "corpus" or rel.startswith("corpus/")) and not allow_corpus_input:
        raise BundleValidationError("corpus_input_without_explicit_override")

def validate_output_path(out_dir: Path, *, allow_example_output: bool = False) -> None:
    if _is_glob(str(out_dir)): raise BundleValidationError("output_is_glob")
    root = repo_root(); target = (root / out_dir if not out_dir.is_absolute() else out_dir).resolve()
    allowed = (root / LIVE_RECAP_RUNS_DIR).resolve()
    examples = (root / LIVE_RECAP_EXAMPLE_DIR).resolve()
    normal_live_child = target != allowed and allowed in target.parents
    example_child = allow_example_output and target != examples and examples in target.parents
    if not (normal_live_child or example_child):
        raise BundleValidationError("output_outside_allowed_run_dir")

def read_explicit_recap_input(input_path: Path) -> str:
    validate_explicit_input_path(input_path)
    return (repo_root()/input_path if not input_path.is_absolute() else input_path).read_text(encoding="utf-8")

def _safe_id(session_id: str) -> str: return re.sub(r"[^a-zA-Z0-9-]+", "-", session_id).strip("-").lower()

def build_source_units(text: str, *, campaign_id: str, session_id: str, source_artifact_id: str) -> dict[str, Any]:
    if not text.strip(): raise BundleValidationError("empty_recap")
    lines = text.splitlines(keepends=True); units=[]; para=[]; start_line=1; char_pos=0; para_start_char=0; ordinal=0
    def flush(end_line:int, end_char:int):
        nonlocal para, ordinal, para_start_char, start_line
        if not para: return
        ordinal += 1; raw=''.join(para); stripped=raw.strip(); is_heading=stripped.startswith('#')
        kind='heading' if is_heading else 'paragraph'; suffix=('h' if is_heading else 'p')+f"{ordinal:03d}"
        preview=re.sub(r"\s+"," ",stripped)[:96]
        units.append({"source_unit_id":f"srcunit:{_safe_id(session_id)}:{suffix}","unit_type":kind,"ordinal":ordinal,"line_start":start_line,"line_end":end_line,"char_start":para_start_char,"char_end":end_char,"text_preview":preview,"text_hash":_sha(stripped),"contains_raw_full_text":False})
        para=[]
    for idx,line in enumerate(lines, start=1):
        line_start_char=char_pos; char_pos += len(line)
        if not line.strip(): flush(idx-1, line_start_char); start_line=idx+1; para_start_char=char_pos; continue
        if not para: start_line=idx; para_start_char=line_start_char
        para.append(line)
    flush(len(lines), len(text))
    if not units: raise BundleValidationError("no_source_units")
    return {"schema":LIVE_RECAP_SOURCE_UNITS_SCHEMA,"version":LIVE_RECAP_INGEST_VERSION,"source_artifact_id":source_artifact_id,"unitization":{"mode":"markdown_line_and_paragraph_units","line_count":len(text.splitlines()),"paragraph_count":sum(u["unit_type"]=="paragraph" for u in units),"heading_count":sum(u["unit_type"]=="heading" for u in units),"blank_lines_preserved":True},"units":units}

def build_source_span_index(source_units: Mapping[str, Any]) -> dict[str, Any]:
    spans=[]
    for u in source_units["units"]:
        sid=u["source_unit_id"].replace("srcunit:","spref:")
        spans.append({"source_span_ref_id":sid,"source_unit_id":u["source_unit_id"],"line_start":u["line_start"],"line_end":u["line_end"],"char_start":u["char_start"],"char_end":u["char_end"],"span_kind":u["unit_type"],"openable":True,"highlightable":True})
    if not spans: raise BundleValidationError("no_source_spans")
    return {"schema":LIVE_RECAP_SOURCE_SPAN_INDEX_SCHEMA,"version":LIVE_RECAP_INGEST_VERSION,"source_artifact_id":source_units["source_artifact_id"],"span_ref_policy":{"stable_ids":True,"line_addressable":True,"paragraph_addressable":True,"heading_addressable":True},"spans":spans}

def build_provenance_index(input_path: Path, text: str, source_units: Mapping[str, Any], *, operator_note: str | None = None) -> dict[str, Any]:
    return {"schema":LIVE_RECAP_PROVENANCE_INDEX_SCHEMA,"version":LIVE_RECAP_INGEST_VERSION,"source_artifact_id":source_units["source_artifact_id"],"input_provenance":{"input_mode":"explicit_file_path","input_sha256":_sha(text),"input_bytes":len(text.encode()),"input_line_count":len(text.splitlines()),"operator_note":operator_note},"unit_provenance":[{"source_unit_id":u["source_unit_id"],"derived_from":"explicit_input_file","line_start":u["line_start"],"line_end":u["line_end"],"text_hash":u["text_hash"]} for u in source_units["units"]]}

def build_source_artifact(*, campaign_id:str, session_id:str, source_label:str, source_hash:str, source_artifact_id:str) -> dict[str,Any]:
    return {"schema":LIVE_RECAP_SOURCE_ARTIFACT_SCHEMA,"version":LIVE_RECAP_INGEST_VERSION,"source_artifact_id":source_artifact_id,"campaign_id":campaign_id,"session_id":session_id,"source_type":"recap_markdown","source_label":source_label,"source_hash":source_hash,"source_units_path":"source_units.json","source_span_index_path":"source_span_index.json","provenance_index_path":"provenance_index.json","raw_text_included":False,"source_state":"ingested_for_dogfood","memory_state":"not_memory","approval_state":"not_applicable"}

def build_diagnostics(source_units:Mapping[str,Any], span_index:Mapping[str,Any]) -> dict[str,Any]:
    counts={"lines":source_units["unitization"]["line_count"],"paragraph_units":source_units["unitization"]["paragraph_count"],"heading_units":source_units["unitization"]["heading_count"],"source_span_refs":len(span_index["spans"]),"warnings":0,"hard_failures":0}
    return {"schema":LIVE_RECAP_DIAGNOSTICS_SCHEMA,"version":LIVE_RECAP_INGEST_VERSION,"status":"ready","counts":counts,"boundary":{"explicit_input_only":True,"directory_scan_allowed":False,"corpus_scan_allowed":False,"corpus_mutation_allowed":False,"llm_execution_allowed":False,"extractor_execution_allowed":False,"candidate_graph_allowed":False,"graph_write_allowed":False,"query_execution_allowed":False,"plan_connected":False,"agent_interaction_connected":False},"warnings":[],"hard_failures":[]}

def build_run_manifest(*, run_id:str,campaign_id:str,session_id:str,source_label:str,input_path_record:str,text:str,diagnostics:Mapping[str,Any]) -> dict[str,Any]:
    return {"schema":LIVE_RECAP_INGEST_RUN_MANIFEST_SCHEMA,"version":LIVE_RECAP_INGEST_VERSION,"run_id":run_id,"campaign_id":campaign_id,"session_id":session_id,"execution_mode":"explicit_input_recap_ingest","input_policy":{"input_mode":"explicit_file_path","directory_scan_allowed":False,"corpus_scan_allowed":False,"corpus_mutation_allowed":False,"glob_allowed":False},"source":{"source_label":source_label,"input_path_record":input_path_record,"input_sha256":_sha(text),"input_bytes":len(text.encode()),"input_line_count":len(text.splitlines())},"outputs":{"source_artifact_path":"source_artifact.json","source_units_path":"source_units.json","source_span_index_path":"source_span_index.json","provenance_index_path":"provenance_index.json","diagnostics_path":"diagnostics.json","report_path":"recap_ingest_report.md"},"diagnostics":{"live_recap_ingest_run":True,"llm_execution_required":False,"extractor_execution_required":False,"candidate_graph_generated":False,"graph_write_required":False,"query_execution_required":False,"graph_retrieval_required":False,"corpus_scan_required":False,"corpus_mutation_required":False,"plan_connected":False,"agent_interaction_connected":False,"production_behavior_changed":False}}

def build_bundle(*, campaign_id:str, session_id:str, input_path:Path, source_label:str|None=None, operator_note:str|None=None, run_id:str|None=None, input_path_record:str|None=None, allow_corpus_input:bool=False) -> dict[str,Any]:
    validate_explicit_input_path(input_path, allow_corpus_input=allow_corpus_input); p=(repo_root()/input_path if not input_path.is_absolute() else input_path); text=p.read_text(encoding='utf-8')
    label=source_label or f"{session_id} explicit recap"; rid=run_id or f"graph-memory:live-recap-ingest:{_safe_id(session_id)}:manual-v0"; aid=f"source-artifact:{campaign_id}:{session_id}:live-recap-v0"
    units=build_source_units(text,campaign_id=campaign_id,session_id=session_id,source_artifact_id=aid); spans=build_source_span_index(units); prov=build_provenance_index(p,text,units,operator_note=operator_note); art=build_source_artifact(campaign_id=campaign_id,session_id=session_id,source_label=label,source_hash=_sha(text),source_artifact_id=aid); diag=build_diagnostics(units,spans); manifest=build_run_manifest(run_id=rid,campaign_id=campaign_id,session_id=session_id,source_label=label,input_path_record=input_path_record or p.name,text=text,diagnostics=diag)
    bundle={"run_manifest":manifest,"source_artifact":art,"source_units":units,"source_span_index":spans,"provenance_index":prov,"diagnostics":diag}
    bundle["recap_ingest_report"]=build_recap_ingest_report(bundle); return bundle

def build_recap_ingest_report(bundle:Mapping[str,Any]) -> str:
    m=bundle['run_manifest']; d=bundle['diagnostics']; su=bundle['source_units']; title=m['source']['source_label']
    return f"""# Live Recap Ingest Run Bundle — {title}\n\n## Purpose\n\nCreate a deterministic source-spanned dogfood run bundle from one explicitly supplied recap file.\n\n## Boundary\n\nThis is a live recap ingest run bundle.\nIt was created from an explicit input file.\nIt does not call an LLM.\nIt does not execute extraction.\nIt does not generate a candidate graph.\nIt does not write graph memory.\nIt does not execute graph queries.\nIt does not connect /plan.\nIt does not connect Agent Interaction.\nIt does not scan or mutate corpus.\nIt does not promote facts or canon.\nIt does not change runtime behavior.\n\n## Input Summary\n\n- Run ID: `{m['run_id']}`\n- Campaign: `{m['campaign_id']}`\n- Session: `{m['session_id']}`\n- Input path record: `{m['source']['input_path_record']}`\n- Input SHA-256: `{m['source']['input_sha256']}`\n- Input bytes: {m['source']['input_bytes']}\n- Input lines: {m['source']['input_line_count']}\n\n## Source Artifact Summary\n\n- Source artifact: `{bundle['source_artifact']['source_artifact_id']}`\n- Source type: `recap_markdown`\n- Memory state: `not_memory`\n- Approval state: `not_applicable`\n\n## Source Units\n\n- Total units: {len(su['units'])}\n- Paragraph units: {d['counts']['paragraph_units']}\n- Heading units: {d['counts']['heading_units']}\n\n## Source Span Index\n\n- Source span refs: {d['counts']['source_span_refs']}\n- Stable IDs: true\n- Line addressable: true\n- Openable and highlightable: true\n\n## Provenance\n\nEvery source unit is derived from the explicit input file and records line range plus text hash.\n\n## Diagnostics\n\n- Status: `{d['status']}`\n- Warnings: {d['counts']['warnings']}\n- Hard failures: {d['counts']['hard_failures']}\n\n## Readiness For Live Extractor Dogfood\n\nThis run is ready to be used as input to a future gated live extractor dogfood harness if all source units and source span refs validate.\n\n## What This Does Not Do\n\nIt does not call an LLM, execute extraction, generate candidate graph memory, write graph memory, execute graph retrieval or queries, connect /plan, connect Agent Interaction, scan or mutate corpus, promote facts, promote canon, or change runtime behavior.\n"""

def write_run_bundle(bundle:Mapping[str,Any], out_dir:Path, *, allow_overwrite:bool=False, allow_example_output:bool=False) -> None:
    validate_output_path(out_dir, allow_example_output=allow_example_output); target=(repo_root()/out_dir if not out_dir.is_absolute() else out_dir)
    if target.exists() and any(target.iterdir()):
        if not allow_overwrite: raise BundleValidationError("output_exists")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for key,name in [("run_manifest","run_manifest.json"),("source_artifact","source_artifact.json"),("source_units","source_units.json"),("source_span_index","source_span_index.json"),("provenance_index","provenance_index.json"),("diagnostics","diagnostics.json")]:
        (target/name).write_text(json.dumps(bundle[key],indent=2,sort_keys=True)+"\n",encoding='utf-8')
    (target/"recap_ingest_report.md").write_text(bundle['recap_ingest_report'],encoding='utf-8')

def load_json(path:str)->dict[str,Any]: return json.loads((repo_root()/path).read_text(encoding='utf-8'))
def load_example_manifest()->dict[str,Any]: return load_json(f"{LIVE_RECAP_EXAMPLE_DIR}/live_recap_ingest_manifest.json")
def load_example_run_bundle()->dict[str,Any]:
    base=repo_root()/SESSION_23_SAMPLE_DIR
    return {"run_manifest":json.loads((base/'run_manifest.json').read_text()),"source_artifact":json.loads((base/'source_artifact.json').read_text()),"source_units":json.loads((base/'source_units.json').read_text()),"source_span_index":json.loads((base/'source_span_index.json').read_text()),"provenance_index":json.loads((base/'provenance_index.json').read_text()),"diagnostics":json.loads((base/'diagnostics.json').read_text()),"recap_ingest_report":(base/'recap_ingest_report.md').read_text()}

def validate_run_manifest(m):
    assert m['schema']==LIVE_RECAP_INGEST_RUN_MANIFEST_SCHEMA and m['version']==LIVE_RECAP_INGEST_VERSION; assert m['input_policy']['input_mode']=='explicit_file_path'; assert not any(v for k,v in m['diagnostics'].items() if k!='live_recap_ingest_run')
def validate_source_artifact(a): assert a['schema']==LIVE_RECAP_SOURCE_ARTIFACT_SCHEMA and a['memory_state']=='not_memory' and a['raw_text_included'] is False
def validate_source_units(s):
    ids=[u['source_unit_id'] for u in s['units']]; assert s['schema']==LIVE_RECAP_SOURCE_UNITS_SCHEMA and len(ids)==len(set(ids)) and ids
    for u in s['units']: assert u['line_start']<=u['line_end'] and u['char_start']<u['char_end'] and len(u['text_preview'])<=96 and not u['contains_raw_full_text']
def validate_source_span_index(si,su):
    known={u['source_unit_id'] for u in su['units']}; ids=[sp['source_span_ref_id'] for sp in si['spans']]; assert si['schema']==LIVE_RECAP_SOURCE_SPAN_INDEX_SCHEMA and len(ids)==len(set(ids)) and ids
    for sp in si['spans']: assert sp['source_unit_id'] in known and sp['openable'] and sp['highlightable'] and sp['line_start']<=sp['line_end']
def validate_provenance_index(p,su):
    known={u['source_unit_id'] for u in su['units']}; assert p['schema']==LIVE_RECAP_PROVENANCE_INDEX_SCHEMA and p['input_provenance']['input_mode']=='explicit_file_path'
    for up in p['unit_provenance']: assert up['source_unit_id'] in known

def validate_diagnostics(d):
    assert d['schema']==LIVE_RECAP_DIAGNOSTICS_SCHEMA and d['status']=='ready'; assert d['counts']['warnings']==len(d['warnings']) and d['counts']['hard_failures']==len(d['hard_failures'])
    b=d['boundary']; assert b['explicit_input_only']; assert not any(v for k,v in b.items() if k!='explicit_input_only')
def validate_report(r):
    for s in ['## Purpose','## Boundary','## Input Summary','## Source Artifact Summary','## Source Units','## Source Span Index','## Provenance','## Diagnostics','## Readiness For Live Extractor Dogfood','## What This Does Not Do','does not call an LLM','does not execute extraction','does not generate a candidate graph','does not write graph memory','does not execute graph queries','does not connect /plan','does not connect Agent Interaction','does not scan or mutate corpus','ready to be used as input to a future gated live extractor dogfood harness']:
        assert s in r

def validate_bundle_consistency(b):
    validate_run_manifest(b['run_manifest']); validate_source_artifact(b['source_artifact']); validate_source_units(b['source_units']); validate_source_span_index(b['source_span_index'],b['source_units']); validate_provenance_index(b['provenance_index'],b['source_units']); validate_diagnostics(b['diagnostics']); validate_report(b['recap_ingest_report'])
    aid=b['source_artifact']['source_artifact_id']; assert b['source_units']['source_artifact_id']==aid and b['source_span_index']['source_artifact_id']==aid and b['provenance_index']['source_artifact_id']==aid
    assert b['diagnostics']['counts']['source_span_refs']==len(b['source_span_index']['spans'])

def validate_no_runtime_leakage(*objects):
    text=json.dumps(objects,sort_keys=True) if not any(isinstance(o,str) for o in objects) else "\n".join(o if isinstance(o,str) else json.dumps(o,sort_keys=True) for o in objects)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in text
    assert str(repo_root()) not in text

def build_sample_bundle():
    return build_bundle(campaign_id='longmont-c2',session_id='session-23',input_path=Path(SAMPLE_INPUT_PATH),source_label='Session 23 Sample',run_id=SESSION_23_SAMPLE_RUN_ID,input_path_record=SAMPLE_INPUT_PATH)

def validate_all():
    manifest=load_example_manifest(); assert manifest['schema']==LIVE_RECAP_INGEST_MANIFEST_SCHEMA and manifest['fixture_id']==LIVE_RECAP_INGEST_FIXTURE_ID
    b=load_example_run_bundle(); validate_bundle_consistency(b); validate_no_runtime_leakage(manifest,b)
    expected=build_sample_bundle(); assert {k:v for k,v in expected.items()}==b
