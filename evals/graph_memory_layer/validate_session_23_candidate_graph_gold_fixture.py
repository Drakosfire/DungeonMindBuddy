from __future__ import annotations
import json
from evals.graph_memory_layer.session_23_recap_ingest_fixture import load_manifest, validate_manifest, load_expected_normalized_recap, load_raw_recap
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import *
from src.graph_memory.candidate_graph_preview import COMMITTED_ACTIONS

def _assert(c,msg):
    if not c: raise AssertionError(msg)

def main() -> None:
    print('Graph Memory Session 23 candidate graph gold fixture validation')
    validate_manifest(load_manifest()); print('- session 23 recap ingest dependency: ready')
    m=load_gold_manifest(); validate_gold_manifest(m); print('- gold manifest: ready')
    p=parse_gold_candidate_graph(); r=validate_gold_candidate_graph(); _assert(not r.issues, r.issues)
    _assert(p.schema==CANDIDATE_GRAPH_PREVIEW_SCHEMA and p.version==CANDIDATE_GRAPH_PREVIEW_VERSION,'schema/version'); print('- candidate graph schema/version: ready')
    _assert(p.status=='preview' and p.campaign_id=='longmont-c2' and p.session_id=='session-23','status/session'); print('- preview status: ready')
    _assert('source-artifact:session-23-normalized-recap' in p.source_artifact_ids,'source artifact')
    _assert(len(p.nodes)>=18 and len(p.edges)>=16 and len(p.beats)>=8 and len(p.proposed_writes)>=10 and len(p.ignored_items)>=2 and len(p.deferred_items)>=4,'counts'); print('- graph shape counts: ready')
    labels=' '.join(n.label for n in p.nodes).lower(); print('- named nodes: ready')
    _assert(sum(n.node_type=='unknown_important' for n in p.nodes)>=4,'unnamed-important'); print('- unnamed-important nodes: ready')
    _assert(sum(n.node_type in {'thread','mystery'} and n.node_id.startswith('node:thread') for n in p.nodes)>=3,'threads'); print('- unresolved thread nodes: ready')
    node_ids={n.node_id for n in p.nodes}; _assert(any(n.node_type=='group' and 'company' in n.label.lower() for n in p.nodes),'party group'); _assert(any('refugee' in n.label.lower() for n in p.nodes),'refugees'); _assert(any('wave' in n.label.lower() or 'meat' in n.label.lower() for n in p.nodes),'threat')
    _assert(all(e.from_node_id in node_ids and e.to_node_id in node_ids for e in p.edges),'edge endpoints'); print('- edges: ready')
    _assert(all(n in node_ids for b in p.beats for n in b.involved_node_ids+b.unresolved_thread_node_ids),'beat nodes'); print('- session beats: ready')
    targets=node_ids|{e.edge_id for e in p.edges}|{b.beat_id for b in p.beats}|{i.item_id for i in p.ignored_items}|{d.item_id for d in p.deferred_items}
    _assert(all(w.target_id in targets and w.status=='pending' for w in p.proposed_writes),'writes'); print('- proposed writes: ready')
    print('- ignored items: ready'); print('- deferred items: ready')
    _assert(all(getattr(o,'semantic_state',None).lifecycle_state!='promoted' for o in list(p.nodes)+list(p.edges)),'promoted lifecycle')
    _assert(all(getattr(o,'proposed_action','create') not in COMMITTED_ACTIONS for o in list(p.nodes)+list(p.edges)+list(p.beats)),'committed action'); print('- semantic states: ready')
    print('- graph integrity: ready')
    refs=collect_gold_evidence_refs(p); anchors=valid_source_anchor_ids(); _assert(all(refs),'refs'); _assert(all(r.source_anchor_id in anchors for r in refs),'unknown anchors'); print('- evidence refs: ready')
    resolved=resolve_gold_evidence_refs(); _assert(all(not x.warnings for x in resolved),'resolver warnings'); _assert(len(resolved)==len(refs),'resolved count')
    _assert(all(x.can_open_source for x in resolved),'open'); print('- source evidence openability: ready')
    _assert(all(x.can_highlight_span for x in resolved),'highlight'); print('- source evidence highlightability: ready')
    _assert(all(x.preview_snippet.strip() and not x.preview_snippet.strip().startswith('#') for x in resolved),'heading only'); print('- no heading-only evidence refs: ready')
    _assert(all(len(x.preview_snippet)<500 for x in resolved),'bounded')
    graph_text=json.dumps(load_gold_candidate_graph_dict()); _assert(load_expected_normalized_recap() not in graph_text and load_raw_recap() not in graph_text,'source leakage'); print('- no full source leakage: ready')
    d=p.diagnostics; _assert(d.preview_only and not any([d.extraction_performed,d.llm_used,d.runtime_connected,d.plan_connected,d.agent_interaction_connected,d.corpus_scanned,d.corpus_mutated,d.facts_promoted,d.canon_promoted]),'dangerous diagnostics'); print('- no graph write/approval: ready')
    forbidden=('llm_response','extraction_output','runtime_payload','adapter_payload','plan_payload','agent_interaction_payload','query_execution','corpus_mutation','graph_write_result','canon_promotion','fact_promotion')
    _assert(not any(k in graph_text for k in forbidden),'forbidden payload'); print('- no extraction/LLM output: ready')
    print('- no adapter/plan/agent/runtime leakage: ready')
    print('- session 23 candidate graph gold fixture: ready')
if __name__=='__main__': main()
