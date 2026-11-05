import hashlib
from src.graph_memory.extraction.known_character_bindings import bind_characters, candidate_bindings, ensure_name_anchors, identity_prompt


def catalog(*entities):
    return {'entities': [{'entity_id': eid, 'label': names[0], 'names': names} for eid, names in entities], 'native_pin': {'revision_id': 'rev-1'}}


def test_literal_case_alias_boundaries_and_no_invented_presence():
    text = 'Mara meets M. Vale. MARA leaves; Marabelle stays.'
    c = bind_characters(catalog(('e1', ['Mara', 'M. Vale']), ('e2', ['Absent'])), [{'source_span_ref_id':'s1','text':text}], hashlib.sha256(text.encode()).hexdigest())
    assert [m['surface'] for m in c['mentions']] == ['Mara','M. Vale','MARA']
    assert [e['entity_id'] for e in c['entities']] == ['e1']
    assert all(text[m['start_offset']:m['end_offset']] == m['surface'] for m in c['mentions'])
    assert 'Absent' not in identity_prompt(c)


def test_conflicting_names_fail_closed_and_duplicate_candidates_remain_unbound():
    c=bind_characters(catalog(('e1',['Mara']),('e2',['Mara'])),[{'source_span_ref_id':'s','text':'Mara waits'}],'x')
    assert c['mentions']==[] and c['ambiguous_surfaces']==['Mara']
    c=bind_characters(catalog(('e1',['Mara'])),[{'source_span_ref_id':'s','text':'Mara waits'}],'x')
    nodes=[{'node_id':i,'label':'Mara','node_type':'character'} for i in ['a','b']]
    assert candidate_bindings(nodes,c)=={}
    assert len(ensure_name_anchors({'observation_nodes':nodes},c)['observation_nodes'])==2


def test_missing_character_endpoint_has_name_evidence_and_no_imported_description():
    c=bind_characters(catalog(('e1',['Mara'])),[{'source_span_ref_id':'s','text':'Mara waits. Mara smiles.'}],'x')
    payload={'observation_nodes':[]}
    result=ensure_name_anchors(payload,c)
    assert payload=={'observation_nodes':[]}
    n=result['observation_nodes'][0]
    assert n['description'] is None and n['evidence_refs']==[{'source_span_ref_id':'s','anchor_quotes':['Mara']}]
    assert candidate_bindings(result['observation_nodes'],c)=={'e1':n['node_id']}


def test_ambiguous_name_stays_blocked_when_other_owner_has_no_unique_mention():
    c=bind_characters(catalog(('e1',['Mara Vale','Mara']),('e2',['Mara'])),[{'source_span_ref_id':'s','text':'Mara Vale waits. Mara departs.'}],'x')
    assert c['entities'][0]['names']==['Mara Vale']
    assert c['entities'][0]['label']=='Mara Vale'
    assert candidate_bindings([{'node_id':'n','label':'Mara','node_type':'character'}],c)=={}
    assert '"Mara"' not in identity_prompt(c)


def test_unmentioned_historical_names_never_reach_actor_prompt_or_candidate_linking():
    c=bind_characters(catalog(('e1',['Mara','A Different Historical Name'])),[{'source_span_ref_id':'s','text':'Mara waits.'}],'x')
    assert c['entities'][0]['names']==['Mara']
    assert 'Historical' not in identity_prompt(c)
    assert candidate_bindings([{'node_id':'n','label':'A Different Historical Name','node_type':'character'}],c)=={}
    assert candidate_bindings([{'node_id':'n','label':'Mara','node_type':'creature'}],c)=={'e1':'n'}
