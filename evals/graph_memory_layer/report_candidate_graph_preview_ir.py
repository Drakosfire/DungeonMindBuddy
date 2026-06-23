from __future__ import annotations
import json
from pathlib import Path
from src.graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict, validate_candidate_graph_preview
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'evals/graph_memory_layer/examples/candidate_graph_preview_minimal.json'
def main():
    p=candidate_graph_preview_from_dict(json.loads(FIXTURE.read_text())); r=validate_candidate_graph_preview(p)
    refs=[]
    for seq in (p.nodes,p.edges,p.beats,p.proposed_writes,p.ignored_items,p.deferred_items):
        for o in seq: refs.extend(o.evidence_refs)
    print('# Candidate Graph Preview IR Report\n\n## Summary\n')
    print('| Metric | Count |\n|---|---:|')
    for k,v in [('Nodes',len(p.nodes)),('Edges',len(p.edges)),('Session beats',len(p.beats)),('Proposed writes',len(p.proposed_writes)),('Ignored items',len(p.ignored_items)),('Deferred items',len(p.deferred_items)),('Evidence refs',len(refs)),('Openable evidence refs',sum(x.can_open_source for x in refs)),('Highlightable evidence refs',sum(x.can_highlight_span for x in refs)),('Issues',len(r.issues))]: print(f'| {k} | {v} |')
    print('\n## Nodes\n\n| ID | Label | Type | Action | Confidence | Evidence |\n|---|---|---|---|---|---:|')
    for n in p.nodes: print(f'| {n.node_id} | {n.label} | {n.node_type} | {n.proposed_action} | {n.confidence} | {len(n.evidence_refs)} |')
    print('\n## Edges\n\n| ID | From | Label | To | Type | Evidence |\n|---|---|---|---|---|---:|')
    for e in p.edges: print(f'| {e.edge_id} | {e.from_node_id} | {e.label} | {e.to_node_id} | {e.relationship_type} | {len(e.evidence_refs)} |')
    print('\n## Session Beats\n\n| Order | Title | Involved Nodes | Evidence |\n|---:|---|---|---:|')
    for b in p.beats: print(f'| {b.order} | {b.title} | {", ".join(b.involved_node_ids)} | {len(b.evidence_refs)} |')
    print('\n## Proposed Writes\n\n| ID | Type | Target | Status | Evidence |\n|---|---|---|---|---:|')
    for w in p.proposed_writes: print(f'| {w.write_id} | {w.write_type} | {w.target_id} | {w.status} | {len(w.evidence_refs)} |')
    print('\n## Ignored / Deferred\n\n| Kind | ID | Label | Reason | Evidence |\n|---|---|---|---|---:|')
    for i in p.ignored_items: print(f'| Ignored | {i.item_id} | {i.label} | {i.reason} | {len(i.evidence_refs)} |')
    for d in p.deferred_items: print(f'| Deferred | {d.item_id} | {d.label} | {d.reason} | {len(d.evidence_refs)} |')
    print('\n## Boundary Statement\n\nThis is a preview-only Candidate Graph Preview IR fixture.\nIt does not extract entities.\nIt does not infer relationships from source text.\nIt does not write graph memory.\nIt does not approve writes.\nIt does not promote facts or canon.\nIt does not connect `/plan`.\nIt does not connect Agent Interaction.\nIt does not change runtime behavior.')
if __name__=='__main__': main()
