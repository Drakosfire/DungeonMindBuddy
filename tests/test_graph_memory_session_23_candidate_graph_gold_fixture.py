import json, subprocess, sys
from pathlib import Path
from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import *
from src.graph_memory.candidate_graph_preview import COMMITTED_ACTIONS
from evals.graph_memory_layer.session_23_recap_ingest_fixture import load_expected_normalized_recap, load_raw_recap


def test_manifest():
    p=gold_manifest_path(); assert p.exists(); m=load_gold_manifest(); validate_gold_manifest(m)
    assert m['schema']==GOLD_MANIFEST_SCHEMA and m['version']==GOLD_MANIFEST_VERSION
    assert m['fixture_id']==GOLD_FIXTURE_ID and m['campaign_id']=='longmont-c2' and m['session']==23
    assert m['input_mode']=='explicit_fixture_dependency'
    assert m['source_fixture_id']=='graph-memory:session-23-recap-ingest:v0'
    for k in ('source_manifest_path','source_span_seed_refs_path','candidate_graph_gold_path'):
        assert not Path(m[k]).is_absolute() and '..' not in Path(m[k]).parts
    assert m['candidate_graph_gold_path']==GOLD_GRAPH_PATH
    assert all(v is False for k,v in m['diagnostics'].items() if k!='manual_gold_fixture')


def test_parse_schema_and_shape():
    assert gold_graph_path().exists(); p=parse_gold_candidate_graph(); r=validate_gold_candidate_graph(); assert not r.issues
    assert p.schema=='dmb_candidate_graph_preview_v0' and p.version=='0.1' and p.status=='preview'
    assert p.campaign_id=='longmont-c2' and p.session_id=='session-23'
    assert len(p.nodes)>=18 and len(p.edges)>=16 and len(p.beats)>=8 and len(p.proposed_writes)>=10
    assert len(p.ignored_items)>=2 and len(p.deferred_items)>=4
    assert sum(n.node_type in {'thread','mystery'} and n.node_id.startswith('node:thread') for n in p.nodes)>=3
    assert sum(n.node_type=='unknown_important' for n in p.nodes)>=4
    labels=' '.join(n.label.lower() for n in p.nodes)
    for term in ['heroes / party','edge refugees','mireward guard','mireward townspeople','first meat wave','mireward reach','edge','north gate','inn','south gate']:
        assert term in labels


def test_integrity_and_evidence():
    p=parse_gold_candidate_graph(); node_ids={n.node_id for n in p.nodes}
    assert len(node_ids)==len(p.nodes); assert len({e.edge_id for e in p.edges})==len(p.edges)
    assert len({b.beat_id for b in p.beats})==len(p.beats); assert len({w.write_id for w in p.proposed_writes})==len(p.proposed_writes)
    assert len({i.item_id for i in p.ignored_items}|{d.item_id for d in p.deferred_items})==len(p.ignored_items)+len(p.deferred_items)
    assert all(e.from_node_id in node_ids and e.to_node_id in node_ids for e in p.edges)
    assert all(n in node_ids for b in p.beats for n in b.involved_node_ids+b.unresolved_thread_node_ids)
    targets=node_ids|{e.edge_id for e in p.edges}|{b.beat_id for b in p.beats}|{i.item_id for i in p.ignored_items}|{d.item_id for d in p.deferred_items}
    assert all(w.target_id in targets for w in p.proposed_writes)
    orders=[b.order for b in p.beats]; assert orders==sorted(orders) and len(set(orders))==len(orders) and min(orders)>0
    refs=collect_gold_evidence_refs(p); assert refs and all(refs)
    assert all(getattr(o,'evidence_refs') for seq in (p.nodes,p.edges,p.beats,p.proposed_writes,p.ignored_items,p.deferred_items) for o in seq)
    anchors=valid_source_anchor_ids(); assert all(r.source_artifact_id==SOURCE_ARTIFACT_ID and r.source_ref_id==SOURCE_REF_ID and r.source_anchor_id in anchors for r in refs)
    resolved=resolve_gold_evidence_refs(); assert len(resolved)==len(refs); assert all(not r.warnings for r in resolved)
    validate_high_risk_evidence_audit(p)
    assert all(r.can_open_source and r.can_highlight_span for r in resolved)
    assert all(r.preview_snippet.strip() and not r.preview_snippet.strip().startswith('#') for r in resolved)
    text=json.dumps(load_gold_candidate_graph_dict()); assert load_expected_normalized_recap() not in text and load_raw_recap() not in text


def test_semantics_content_and_boundaries():
    p=parse_gold_candidate_graph();
    assert all(n.semantic_state.lifecycle_state!='promoted' for n in p.nodes)
    assert all(e.semantic_state.lifecycle_state!='promoted' for e in p.edges)
    assert all(w.status=='pending' for w in p.proposed_writes)
    assert all(getattr(o,'proposed_action','create') not in COMMITTED_ACTIONS for o in list(p.nodes)+list(p.edges)+list(p.beats))
    d=p.diagnostics; assert d.preview_only and not any([d.extraction_performed,d.llm_used,d.runtime_connected,d.plan_connected,d.agent_interaction_connected,d.corpus_scanned,d.corpus_mutated,d.facts_promoted,d.canon_promoted])
    text=json.dumps(load_gold_candidate_graph_dict(), ensure_ascii=False).lower()
    for term in ['heroes / party','lysandra','lysandro','orik tane','brin holloway','stafl','ephanna','karsemine','bonogo','thrin','baergrom','caelynn','ogonob','mireward reach','edge','north gate','south gate','edge refugees','first meat wave','tripod meat monsters','flying meatwings','hunger of hadar','commanding shout','hunter’s mark','lightning bolt cliffhanger']:
        assert term.lower() in text
    for forbidden in ['llm_response','extraction_output','runtime_payload','plan_payload','agent_interaction_payload','query_execution','corpus_mutation','graph_write_result','"approved"','"promoted"','/workspace/']:
        assert forbidden not in text
    assert 'questionable company' not in text and 'second wave' not in text and 'thread-monster-second-wave' not in text


def test_cli_report_and_validator():
    v=subprocess.run([sys.executable,'-m','evals.graph_memory_layer.validate_session_23_candidate_graph_gold_fixture'],text=True,capture_output=True,check=True)
    assert 'session 23 candidate graph gold fixture: ready' in v.stdout
    r=subprocess.run([sys.executable,'-m','evals.graph_memory_layer.report_session_23_candidate_graph_gold_fixture'],text=True,capture_output=True,check=True)
    assert '## Session Outline' in r.stdout and '## Evidence Preview' in r.stdout
    assert 'This is a hand-authored Session 23 Candidate Graph Preview gold fixture.' in r.stdout
