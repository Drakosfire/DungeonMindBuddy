"""Frozen provider output binds current saved source before any authoring review."""
import copy
import json
from uuid import uuid4
import pytest
from pydantic import ValidationError
from generationengine.utils.schema_utils import make_schema_strict
from application_state.agent_conversation.build_draft_answer import normalize, output_schema
from application_state.agent_conversation.source_writer_output import validate_writer_format
from application_state.agent_conversation.relationship_review import FORMAT, KEY, POLICY
from tests.test_typed_collaboration import packet, answer


def fixture():
    p=packet()
    rid=str(uuid4())
    p.update(schema='dmb_build_primary_context_writer_v1',connected_page_review_policy='typed_connected_page_review_v1',source_quote_binding_policy='exact_source_quote_binding_v1',relationship_review_policy=POLICY,artifact_under_edit={'policy':'exact_acquired_primary_work_context_v1','role':'authored_page_under_edit_not_world_or_played_truth','sections':[{'read_id':rid,'line_start':1,'line_end':1,'text':'Rowan worked with Mara temporarily in the past.'}]})
    proposal={'kind':'relationship','read_id':rid,'quote':'Rowan worked with Mara temporarily in the past.','source':{'label':'Rowan','kind':'npc'},'target':{'label':'Mara','kind':'npc'},'predicate':'works_with','label':'worked together temporarily','context':'Past temporary work; no current employment or played events.'}
    return p,proposal


def test_strict_provider_schema_and_exact_saved_quote_survive_projection():
    p,proposal=fixture()
    schema=output_schema(p)
    assert make_schema_strict(schema)==schema
    assert schema['$defs']['ProposedRelationship']['properties']['read_id']['enum']==[proposal['read_id']]
    validate_writer_format({'type':'json_schema','name':FORMAT,'strict':True,'schema':schema},p)
    assert normalize(json.dumps(answer(proposal)),p)['collaboration']==proposal


@pytest.mark.parametrize('patch',[{'read_id':str(uuid4())},{'quote':'Unsaved invention'},{'source':{'label':'Rowan','kind':'npc','node_id':'invented'}},{'context':'  '},{'published':True}])
def test_rejects_unread_or_unsupported_model_authority(patch):
    p,proposal=fixture()
    with pytest.raises(ValueError):normalize(json.dumps(answer({**proposal,**patch})),p)


def test_duplicate_quote_and_related_page_cannot_substitute_for_primary_saved_read():
    p,proposal=fixture()
    p['artifact_under_edit']['sections'][0]['text']*=2
    with pytest.raises(ValueError,match='one exact quote'):normalize(json.dumps(answer(proposal)),p)
    p['artifact_under_edit']['sections']=[]
    p['related_authored_pages']={'pages':[{'read_id':proposal['read_id'],'markdown':proposal['quote']}]}
    with pytest.raises(ValueError):normalize(json.dumps(answer(proposal)),p)
    assert 'ProposedRelationship' not in output_schema({k:v for k,v in p.items() if k!='related_authored_pages'})['$defs']


def test_historical_writer_and_schema_do_not_gain_relationship_authority():
    p,proposal=fixture()
    old=copy.deepcopy(p);old.pop(KEY)
    assert 'ProposedRelationship' not in output_schema(old)['$defs']
    with pytest.raises(ValidationError):normalize(json.dumps(answer(proposal)),old)
    for name,body in [('build_working_draft_answer_v4',p),(FORMAT,old)]:
        with pytest.raises(ValueError):validate_writer_format({'type':'json_schema','name':name,'strict':True,'schema':output_schema(body)},body)
