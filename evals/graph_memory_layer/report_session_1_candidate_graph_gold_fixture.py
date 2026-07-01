from __future__ import annotations
from evals.graph_memory_layer.session_1_candidate_graph_gold_fixture import *

def esc(s): return str(s).replace('|','\\|').replace('\n',' ')
def main():
    p=parse_gold_candidate_graph(); refs=collect_gold_evidence_refs(p); res=resolve_gold_evidence_refs()
    print('# Session 1 Candidate Graph Gold Fixture Report\n')
    print('## Summary\n\n| Metric | Count |\n|---|---:|')
    for k,v in [('Nodes',len(p.nodes)),('Edges',len(p.edges)),('Session beats',len(p.beats)),('Proposed writes',len(p.proposed_writes)),('Ignored items',len(p.ignored_items)),('Deferred items',len(p.deferred_items)),('Evidence refs',len(refs)),('Resolved evidence refs',len(res)),('Unnamed-important nodes',sum(n.node_type=='unknown_important' for n in p.nodes)),('Thread/mystery/quest nodes',sum(n.node_type in {'thread','mystery','quest'} for n in p.nodes)),('Combat_encounter nodes',sum(n.node_type=='combat_encounter' for n in p.nodes)),('Landmark nodes',sum(n.node_type=='landmark' for n in p.nodes))]: print(f'| {k} | {v} |')
    print('\n## Session Outline\n\n| Order | Beat | Summary | Evidence |\n|---:|---|---|---:|')
    for b in sorted(p.beats,key=lambda x:x.order): print(f'| {b.order} | {esc(b.title)} | {esc(b.summary)} | {len(b.evidence_refs)} |')
    print('\n## Nodes\n\n| ID | Label | Type | Importance | Confidence | Evidence |\n|---|---|---|---|---|---:|')
    for n in p.nodes: print(f'| {n.node_id} | {esc(n.label)} | {n.node_type} | {n.importance} | {n.confidence} | {len(n.evidence_refs)} |')
    byid={n.node_id:n.label for n in p.nodes}
    print('\n## Edges\n\n| ID | From | Label | To | Type | Confidence | Evidence |\n|---|---|---|---|---|---|---:|')
    for e in p.edges: print(f'| {e.edge_id} | {esc(byid[e.from_node_id])} | {esc(e.label)} | {esc(byid[e.to_node_id])} | {e.relationship_type} | {e.confidence} | {len(e.evidence_refs)} |')
    print('\n## Proposed Writes\n\n| ID | Type | Target | Status | Reason |\n|---|---|---|---|---|')
    for w in p.proposed_writes: print(f'| {w.write_id} | {w.write_type} | {w.target_id} | {w.status} | {esc(w.reason)} |')
    print('\n## Ignored Items\n\n| ID | Label | Reason | Evidence |\n|---|---|---|---:|')
    for i in p.ignored_items: print(f'| {i.item_id} | {esc(i.label)} | {esc(i.reason)} | {len(i.evidence_refs)} |')
    print('\n## Deferred Items\n\n| ID | Label | Reason | Suggested Next Step | Evidence |\n|---|---|---|---|---:|')
    for d in p.deferred_items: print(f'| {d.item_id} | {esc(d.label)} | {esc(d.reason)} | {esc(d.suggested_next_step)} | {len(d.evidence_refs)} |')
    print('\n## Evidence Preview\n\n| Anchor | Label | Snippet |\n|---|---|---|')
    seen=set()
    for x in res:
        if x.source_anchor_id in seen: continue
        seen.add(x.source_anchor_id); print(f'| {x.source_anchor_id} | {esc(x.label)} | {esc(x.preview_snippet)} |')
    print('\n## Boundary Statement\n')
    print('This is a hand-authored Session 1 Candidate Graph Preview gold fixture.\nIt is not extractor output.\nIt does not call an LLM.\nIt does not run the live planner.\nIt does not write graph memory.\nIt does not approve writes.\nIt does not execute graph queries.\nIt does not scan or mutate corpus files.\nIt does not connect `/plan`.\nIt does not connect Agent Interaction.\nIt does not promote facts or canon.\nIt does not change runtime behavior.')
if __name__=='__main__': main()
