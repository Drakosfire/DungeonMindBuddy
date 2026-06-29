from __future__ import annotations
import json, re
from pathlib import Path
from src.graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict, validate_candidate_graph_preview, CANDIDATE_GRAPH_PREVIEW_SCHEMA, CANDIDATE_GRAPH_PREVIEW_VERSION
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'evals/graph_memory_layer/examples/candidate_graph_preview_minimal.json'
SRC=ROOT/'evals/graph_memory_layer/examples/source_span_resolver_fixture.json'
FORBIDDEN=['/plan','Agent Interaction payload','runtime_ui','query_payload','llm_prompt','extraction_prompt','facts_promoted_payload','canon_promoted_payload','adapter_payload','_normalized/','_breadcrumbed/','.records_meta.jsonl','corpus_impact']
def _assert(c,m):
    if not c: raise AssertionError(m)
def main():
    raw=FIXTURE.read_text(); data=json.loads(raw); p=candidate_graph_preview_from_dict(data); report=validate_candidate_graph_preview(p)
    src=json.loads(SRC.read_text()); valid={(r['source_ref_id'],r['source_artifact_id'],r.get('source_anchor_id')) for r in src['source_span_refs'] if not r['source_ref_id'].startswith('source-ref:missing') and r.get('start_line',1)<90}
    refs=[]
    for seq in (p.nodes,p.edges,p.beats,p.proposed_writes,p.ignored_items,p.deferred_items):
        for o in seq: refs.extend(o.evidence_refs)
    _assert(FIXTURE.exists(),'fixture missing'); _assert(p.schema==CANDIDATE_GRAPH_PREVIEW_SCHEMA and p.version==CANDIDATE_GRAPH_PREVIEW_VERSION,'schema/version'); _assert(p.status=='preview','status')
    _assert(len(p.nodes)>=5 and len(p.edges)>=4 and len(p.beats)>=3 and p.proposed_writes and p.ignored_items and p.deferred_items,'shape')
    _assert(not report.issues, report.issues)
    for r in refs:
        _assert((r.source_ref_id,r.source_artifact_id,r.source_anchor_id) in valid, f'unresolved {r}')
        _assert(r.can_open_source,'unopenable');
        if r.evidence_role=='source_evidence': _assert(r.can_highlight_span,'unhighlightable')
    for art in src.get('text_artifacts',[]): _assert(art['text'] not in raw,'raw source leak')
    _assert(not re.search(r'(^|[\s"])(/[A-Za-z0-9_.-]+){2,}', raw),'absolute path leak')
    for token in FORBIDDEN: _assert(token not in raw, f'forbidden leakage {token}')
    d=p.diagnostics; _assert(d.preview_only and not any([d.extraction_performed,d.llm_used,d.runtime_connected,d.plan_connected,d.agent_interaction_connected,d.corpus_scanned,d.corpus_mutated,d.facts_promoted,d.canon_promoted]),'diagnostics')
    lines=['Graph Memory candidate graph preview IR validation','- fixture: ready','- schema/version: ready','- preview status: ready','- nodes: ready','- edges: ready','- beats: ready','- proposed writes: ready','- ignored/deferred items: ready','- semantic states: ready','- edge endpoints: ready','- beat node refs: ready','- write targets: ready','- evidence refs: ready','- source evidence openability: ready','- source evidence highlightability: ready','- preview-only diagnostics: ready','- no full raw source leakage: ready','- no absolute path leakage: ready','- no adapter/plan/agent/runtime leakage: ready','- candidate graph preview IR: ready']
    print('\n'.join(lines))
if __name__=='__main__': main()
