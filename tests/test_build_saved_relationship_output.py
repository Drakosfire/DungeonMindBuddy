"""Resolved review grammar and exact shared saved-page support, without repair."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

from jsonschema import Draft202012Validator,ValidationError as SchemaError
import pytest
from application_state.agent_conversation import relationship_review as review
from application_state.agent_conversation import build_intentional_response as intentional
from application_state.agent_conversation.build_primary_context import POLICY,ROLE,SCHEMA,packet_rows
from application_state.agent_conversation.build_draft_context import POLICY as DRAFT_POLICY
from application_state.agent_conversation.source_writer_output import validate_writer_format
from tests.test_build_related_pages import build_case


def packet(*,current=True):
    text='Mara and Oren exchange bell repairs for lantern fittings.'
    return {'schema':SCHEMA,'user_question':'Review their trade relationship.',
        'source_writer_output_policy':'cited_facts_host_limitations_v1',
        'requested_detail_gap_policy':'exact_question_phrase_selected_excerpts_v1',
        'working_draft_context':{'policy':DRAFT_POLICY,'record_id':str(uuid4()),'draft_markdown':text},
        'collaboration_output_policy':'typed_author_review_collaboration_v1',
        'connected_page_review_policy':'typed_connected_page_review_v1',
        review.KEY:review.POLICY,
        'artifact_under_edit':{'policy':POLICY,'role':ROLE,'sections':[{'read_id':str(uuid4()),'line_start':1,'line_end':1,'text_ref':'working_draft_context'}] if current else []},
        'response_contract':intentional.resolve('review_relationship',intentional.Capabilities(('answer_from_sources',),('relationship',),False,None))}


def answer(collaboration):
    return {'answer_context_status':'discussion','answer_segments':[{'kind':'discussion','text':'Review the trade connection.'}],
        'limitations':[],'requested_detail_gaps':[],'collaboration':collaboration}


def relationship(p):
    row,=packet_rows(p)
    return {'kind':'relationship','read_id':row['read_id'],'quote':row['text'],
        'source':{'label':'Mara','kind':'npc'},'target':{'label':'Oren','kind':'npc'},
        'predicate':'works_with','label':'Reciprocal trade','context':'A trade arrangement, not a played event.'}


def test_new_grammar_closes_the_observed_schema_normalizer_mismatch_without_changing_history():
    old=packet();historical=intentional.output_schema(old);new={**old,review.OUTPUT_KEY:review.OUTPUT_POLICY}
    schema=intentional.output_schema(new)
    fmt={'type':'json_schema','name':intentional.FORMAT+review.OUTPUT_SUFFIX,'strict':True,'schema':schema}
    validate_writer_format(fmt,new)
    wrong=[{'kind':'questions','questions':[{'text':'Can you acquire the saved page?'}]},
        {'kind':'plan','steps':[{'text':'Discuss trade.','kind':'discuss'}]},
        {'kind':'connected_page','title':'Other shop','read_id':str(uuid4()),'quote':'Other text','person_label':None,'relationships':[],'instructions':'Develop it.'}]
    for value in wrong:
        raw=answer(value)
        if value['kind']!='connected_page':Draft202012Validator(historical).validate(raw)
        with pytest.raises(SchemaError):Draft202012Validator(schema).validate(raw)
        with pytest.raises(ValueError,match='Typed object differs'):intentional.normalize(json.dumps(raw),new)
    assert intentional.output_schema(old)==historical
    validate_writer_format({**fmt,'name':intentional.FORMAT,'schema':historical},old)
    for bad_fmt,bad_packet in [(fmt,old),({**fmt,'name':intentional.FORMAT},new),({**fmt,'schema':historical},new)]:
        with pytest.raises(ValueError):validate_writer_format(bad_fmt,bad_packet)
    for mutation in ['unknown','wrong_work','wrong_profile','barrier']:
        bad=deepcopy(new)
        if mutation=='unknown':bad[review.OUTPUT_KEY]='unknown'
        elif mutation=='wrong_work':bad['response_contract']=intentional.resolve('discuss',intentional.Capabilities(('answer_from_sources',),('relationship',),False,None))
        elif mutation=='wrong_profile':bad.pop(review.KEY)
        else:bad['response_contract']=intentional.resolve('review_relationship',intentional.Capabilities(('answer_from_sources',),(),False,None))
        with pytest.raises(ValueError):validate_writer_format(fmt,bad)


def test_current_saved_alias_and_absent_support_keep_their_actual_authority():
    p=packet();p[review.OUTPUT_KEY]=review.OUTPUT_POLICY
    raw=answer(relationship(p));Draft202012Validator(intentional.output_schema(p)).validate(raw)
    assert intentional.normalize(json.dumps(raw),p)['collaboration']==raw['collaboration']
    foreign=deepcopy(raw);foreign['collaboration']['read_id']=str(uuid4())
    with pytest.raises(ValueError,match='unread current saved'):intentional.normalize(json.dumps(foreign),p)
    foreign['collaboration']['read_id']=raw['collaboration']['read_id'];foreign['collaboration']['quote']='Unseen source text'
    with pytest.raises(ValueError,match='exact quote'):intentional.normalize(json.dumps(foreign),p)
    absent=packet(current=False);absent[review.OUTPUT_KEY]=review.OUTPUT_POLICY
    assert intentional.output_schema(absent)['properties']['collaboration']['anyOf']==[{'type':'null'}]
    no_support=answer(None);no_support['answer_segments'][0]['text']='The current saved passage was not acquired; the review is still pending.'
    Draft202012Validator(intentional.output_schema(absent)).validate(no_support)
    assert intentional.normalize(json.dumps(no_support),absent)['collaboration'] is None


@pytest.mark.parametrize('aliased',[False,True])
@pytest.mark.parametrize('selected',[False,True])
def test_guarded_sdk_app_retains_aliased_current_relationship_and_exact_composite_format(build_case,monkeypatch,tmp_path,aliased,selected):
    from tests import test_build_related_pages as cases
    if aliased:
        original=cases.world_case;snapshot=cases.BuildDraftSnapshotV1;body=[]
        def world_case(*args,**kwargs):
            result=original(*args,**kwargs);body.append(result[0][0].markdown);return result
        def exact_snapshot(**kwargs):
            return snapshot(**{**kwargs,'draft_markdown':body[0],'draft_sha256':sha256(body[0].encode()).hexdigest()})
        monkeypatch.setattr(cases,'world_case',world_case);monkeypatch.setattr(cases,'BuildDraftSnapshotV1',exact_snapshot)
    turn,service,*rest=cases.completed.__wrapped__(build_case,monkeypatch,tmp_path,SimpleNamespace(param='relationship_review_cap' if selected else 'relationship_review'))
    writer=rest[-2];wire=json.loads(writer.calls[0].content);p=json.loads(wire['input'])
    assert p[review.OUTPUT_KEY]==review.OUTPUT_POLICY
    assert ('text_ref' in p['artifact_under_edit']['sections'][0])==aliased
    assert wire['text']['format']['name'].endswith('_quotes_v3'+review.OUTPUT_SUFFIX)
    assert len(wire['text']['format']['name'])<=64
    assert ('plan_output_contract' in p)==selected
    assert wire['text']['format']['schema']['properties']['collaboration']['anyOf']==[{'$ref':'#/$defs/ProposedRelationship'},{'type':'null'}]
    assert 'shared carrier does not revoke' in wire['instructions']
    validate_writer_format(wire['text']['format'],p)
    assert service.inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id)==turn
    assert turn.completion.collaboration.model_dump(mode='json')==writer.collaboration
    foreign=deepcopy(writer.collaboration);foreign['read_id']=p['related_authored_pages']['pages'][0]['read_id']
    with pytest.raises(ValueError,match='unread current saved'):intentional.normalize(json.dumps(answer(foreign)),p)
