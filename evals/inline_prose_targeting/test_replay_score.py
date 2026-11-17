"""Scorer controls, not model samples. No held-out answers are used here."""
from copy import deepcopy
import hashlib
import json
import pytest
from evals.inline_prose_targeting.replay_score import score


def fixture():
    inputs={'schema':'prose_routing_inputs_v1','split':'dev','cases':[
        {'id':str(i),'request':'Synthetic request','choices':[{'alias':'choice1'},{'alias':'choice2'}]} for i in range(5)]}
    raw=(json.dumps(inputs)+'\n').encode(); digest=hashlib.sha256(raw).hexdigest()
    answers=[]
    for i,(disposition,targets) in enumerate([('target',['choice1']),('clarify',[]),('discuss',[]),('target',[]),('target',['choice1','choice2'])]):
        answers.append({'id':str(i),'fixture_id':'private','disposition':disposition,'target_available':bool(targets),
            'acceptable_aliases':targets,'snapshot_sha256':'a'*64,'host_bindings':{'choice1':'host1','choice2':'host2'}})
    manifest={'schema':'prose_routing_answers_v1','split':'dev','source_sha':'b'*40,'inputs_sha256':digest,'cases':answers}
    replay={'schema':'prose_routing_replay_v1','inputs_sha256':digest,'provenance':'scripted','decisions':[]}
    return raw,manifest,replay


def test_known_control_keeps_capability_miss_separate_and_accepts_equivalent_boundary():
    raw,manifest,replay=fixture()
    decisions=[{'alias':'choice1'},{'clarify':True},{'discuss':True},{'clarify':True},{'alias':'choice2'}]
    replay['decisions']=[{'id':str(i),'decision':d} for i,d in enumerate(decisions)]
    result=score(raw,manifest,replay)
    assert result['counts']['correct_target']==2
    assert result['counts']['capability_miss']==1
    assert result['counts']['valid_miss']==1
    assert result['counts']['unnecessary_clarification']==0
    assert result['clarification']=={'required':1,'correct':1,'overuse':0}
    assert result['intentional_non_edit']=={'required':1,'correct':1}
    assert not result['hard_failure'] and not result['ordinary_routing_qualified']
    assert result['transactions']=='not run' and result['save_reopen']=='not run'


@pytest.mark.parametrize('case,decision,outcome',[
    ('0',{'alias':'choice2'},'wrong_target_nomination'),
    ('0',{'alias':'foreign'},'invalid_alias'),
    ('1',{'alias':'choice1'},'wrong_target_nomination'),
    ('2',{'alias':'choice1'},'wrong_target_nomination'),
    ('3',{'alias':'choice1'},'wrong_target_nomination'),
])
def test_wrong_or_unknown_target_is_hard_failure_even_when_other_cases_missing(case,decision,outcome):
    raw,manifest,replay=fixture();replay['decisions']=[{'id':case,'decision':decision}]
    result=score(raw,manifest,replay)
    assert result['hard_failure'] and result['counts'][outcome]==1
    assert result['coverage']['missing']==4


def test_clarification_overuse_and_intentional_non_edit_are_not_conflated():
    raw,manifest,replay=fixture()
    replay['decisions']=[{'id':'0','decision':{'clarify':True}}, {'id':'1','decision':{'discuss':True}}, {'id':'2','decision':{'clarify':True}}]
    result=score(raw,manifest,replay)
    assert result['counts']['unnecessary_clarification']==2
    assert result['counts']['missed_clarification']==1
    assert result['counts']['missed_intentional_non_edit']==1
    assert result['counts']['correct_intentional_non_edit']==0


def test_missing_decisions_are_unscored_not_success():
    raw,manifest,replay=fixture();result=score(raw,manifest,replay)
    assert result['coverage']=={'total':5,'supplied':0,'missing':5}
    assert all(row['outcome']=='unscored' for row in result['cases'])
    assert result['counts']['correct_target']==0


@pytest.mark.parametrize('bad',[{'alias':'choice1','clarify':True},{'clarify':False},{'discuss':1},{'alias':1},{'offset':42},{}])
def test_malformed_decisions_reject_without_scoring(bad):
    raw,manifest,replay=fixture();replay['decisions']=[{'id':'0','decision':bad}]
    with pytest.raises(ValueError):score(raw,manifest,replay)


@pytest.mark.parametrize('change',['digest','split','unknown','duplicate','extra','missing-answer','unknown-answer-alias'])
def test_mismatched_or_ambiguous_protocol_rejects(change):
    raw,manifest,replay=fixture()
    if change=='digest': replay['inputs_sha256']='0'*64
    if change=='split': manifest['split']='holdout'
    if change=='unknown': replay['decisions']=[{'id':'unknown','decision':{'discuss':True}}]
    if change=='duplicate': replay['decisions']=[{'id':'0','decision':{'discuss':True}}]*2
    if change=='extra': replay['auto_apply']=True
    if change=='missing-answer':manifest['cases'].pop()
    if change=='unknown-answer-alias':manifest['cases'][0]['acceptable_aliases']=['foreign']
    with pytest.raises(ValueError):score(raw,manifest,replay)


def test_input_bytes_bound_and_inputs_not_mutated():
    raw,manifest,replay=fixture();before=deepcopy((manifest,replay))
    with pytest.raises(ValueError):score(raw+b' ',manifest,replay)
    score(raw,manifest,replay)
    assert before==(manifest,replay)


@pytest.mark.parametrize('raw', [
    '{"alias":"wrong","alias":"choice1"}',
    '{"decision":{"alias":"wrong","alias":"choice1"}}',
    '{"cases":[],"cases":[]}',
])
def test_duplicate_json_keys_reject_before_reducing_supplied_response(raw):
    from evals.inline_prose_targeting.replay_score import decode_json
    with pytest.raises(ValueError, match='Duplicate JSON'):
        decode_json(raw)


def test_cli_duplicate_decision_key_never_writes_a_score(tmp_path):
    import subprocess, sys
    raw, manifest, replay = fixture()
    (tmp_path/'inputs').write_bytes(raw)
    (tmp_path/'manifest').write_text(json.dumps(manifest))
    replay['decisions']=[{'id':'0','decision':{'alias':'choice1'}}]
    encoded=json.dumps(replay).replace('{"alias": "choice1"}', '{"alias":"wrong","alias":"choice1"}')
    (tmp_path/'replay').write_text(encoded)
    result=subprocess.run([sys.executable,'-m','evals.inline_prose_targeting.replay_score',
        '--inputs',str(tmp_path/'inputs'),'--manifest',str(tmp_path/'manifest'),
        '--decisions',str(tmp_path/'replay'),'--output',str(tmp_path/'score')],capture_output=True)
    assert result.returncode != 0 and b'Duplicate JSON' in result.stderr
    assert not (tmp_path/'score').exists()
