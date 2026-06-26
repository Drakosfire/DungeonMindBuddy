import json, subprocess, sys, re
from pathlib import Path
from src.graph_memory.candidate_graph_preview import *
ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'evals/graph_memory_layer/examples/candidate_graph_preview_minimal.json'
SRC=ROOT/'evals/graph_memory_layer/examples/source_span_resolver_fixture.json'

def load(): return json.loads(FIX.read_text())
def preview(): return candidate_graph_preview_from_dict(load())
def all_refs(p):
    out=[]
    for seq in (p.nodes,p.edges,p.beats,p.proposed_writes,p.ignored_items,p.deferred_items):
        for o in seq: out.extend(o.evidence_refs)
    return out

def test_evidence_ref_round_trip_anchor_quote_fields():
    data = {
        "source_ref_id": "source-ref:normalized_recap_markdown:dogfood",
        "source_artifact_id": "source-artifact:normalized_recap_markdown:dogfood",
        "source_span_ref_id": "spref:session-22:p004",
        "anchor_quotes": ["Grobnok"],
        "anchor_quote_matches": [
            {
                "quote": "Grobnok",
                "char_start": 10,
                "char_end": 17,
                "match_text": "Grobnok",
            }
        ],
        "can_open_source": True,
        "can_highlight_span": True,
    }
    ref = evidence_ref_from_dict(data)
    assert ref.source_span_ref_id == "spref:session-22:p004"
    assert ref.anchor_quotes == ("Grobnok",)
    assert len(ref.anchor_quote_matches) == 1
    assert evidence_ref_from_dict(evidence_ref_to_dict(ref)) == ref

def test_cli_and_fixture_shape():
    assert subprocess.run([sys.executable,'-m','evals.graph_memory_layer.validate_candidate_graph_preview_ir'],cwd=ROOT).returncode==0
    assert subprocess.run([sys.executable,'-m','evals.graph_memory_layer.report_candidate_graph_preview_ir'],cwd=ROOT,stdout=subprocess.PIPE,text=True).returncode==0
    d=load(); assert d['schema']==CANDIDATE_GRAPH_PREVIEW_SCHEMA; assert d['version']==CANDIDATE_GRAPH_PREVIEW_VERSION; assert d['status']=='preview'
    assert len(d['nodes'])>=5 and len(d['edges'])>=4 and len(d['beats'])>=3
    assert d['proposed_writes'] and d['ignored_items'] and d['deferred_items']

def test_object_model_round_trip_tuples():
    p=preview(); d=candidate_graph_preview_to_dict(p); p2=candidate_graph_preview_from_dict(d)
    assert isinstance(p2.nodes, tuple) and isinstance(p2.nodes[0].evidence_refs, tuple)
    assert p2 == p
    assert semantic_state_from_dict(semantic_state_to_dict(p.nodes[0].semantic_state)) == p.nodes[0].semantic_state
    assert evidence_ref_from_dict(evidence_ref_to_dict(p.nodes[0].evidence_refs[0])) == p.nodes[0].evidence_refs[0]

def test_graph_integrity_and_validation_report():
    p=preview(); r=validate_candidate_graph_preview(p); assert r.issue_counts == {}; assert r.issues == ()
    node_ids={n.node_id for n in p.nodes}; assert len(node_ids)==len(p.nodes); assert len({e.edge_id for e in p.edges})==len(p.edges)
    assert all(e.from_node_id in node_ids and e.to_node_id in node_ids for e in p.edges)
    assert all(set(b.involved_node_ids).issubset(node_ids) and set(b.unresolved_thread_node_ids).issubset(node_ids) for b in p.beats)
    targets=node_ids|{e.edge_id for e in p.edges}|{b.beat_id for b in p.beats}|{i.item_id for i in p.ignored_items}|{d.item_id for d in p.deferred_items}
    assert all(w.target_id in targets for w in p.proposed_writes)
    assert len({i.item_id for i in p.ignored_items}|{d.item_id for d in p.deferred_items}) == len(p.ignored_items)+len(p.deferred_items)

def test_evidence_resolves_and_is_inspectable():
    p=preview(); src=json.loads(SRC.read_text())
    valid={(r['source_ref_id'],r['source_artifact_id'],r.get('source_anchor_id')) for r in src['source_span_refs'] if not r['source_ref_id'].startswith('source-ref:missing') and r.get('start_line',1)<90}
    assert all(o.evidence_refs for seq in (p.nodes,p.edges,p.beats,p.proposed_writes) for o in seq)
    for r in all_refs(p):
        assert (r.source_ref_id,r.source_artifact_id,r.source_anchor_id) in valid
        assert r.can_open_source
        if r.evidence_role == 'source_evidence': assert r.can_highlight_span

def test_semantic_state_preview_only():
    p=preview(); assert p.status=='preview'; assert any(n.node_type=='unknown_important' for n in p.nodes); assert any(n.node_type in {'warning','clue'} for n in p.nodes); assert any(n.node_type=='thread' for n in p.nodes)
    for obj in list(p.nodes)+list(p.edges):
        s=obj.semantic_state; assert s.canon_state in CANON_STATES; assert s.lifecycle_state in LIFECYCLE_STATES and s.lifecycle_state != 'promoted'; assert s.evidence_role in EVIDENCE_ROLES; assert s.authority_state in AUTHORITY_STATES; assert s.visibility_state in VISIBILITY_STATES
    assert all(w.status!='approved' and w.status=='pending' for w in p.proposed_writes)
    assert 'fact' in p.ignored_items[0].reason and 'canon' in p.deferred_items[0].warnings[0]

def test_safety_and_diagnostics():
    raw=FIX.read_text(); src=json.loads(SRC.read_text())
    for art in src['text_artifacts']: assert art['text'] not in raw
    assert not re.search(r'(^|[\s"])(/[A-Za-z0-9_.-]+){2,}', raw)
    for token in ['_normalized/','_breadcrumbed/','.records_meta.jsonl','corpus_impact','adapter_payload','/plan','Agent Interaction payload','runtime_ui','query_payload','extraction_prompt','llm_prompt','fact_promotion','canon_promotion']:
        assert token not in raw
    d=preview().diagnostics; assert d.preview_only is True
    assert not any([d.extraction_performed,d.llm_used,d.runtime_connected,d.plan_connected,d.agent_interaction_connected,d.corpus_scanned,d.corpus_mutated,d.facts_promoted,d.canon_promoted])
