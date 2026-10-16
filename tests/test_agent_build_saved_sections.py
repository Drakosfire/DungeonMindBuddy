"""Saved-source admission at actual APP persistence boundary, no live providers."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4
import json

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.build_section import exact_saved_section
from application_state.errors import ApplicationStateError
from apps.live_control_server.services import agent_turn_service as owner
from tests.test_agent_build_jev_controller_exposure import _start, build_case as _build_case
from tests.test_agent_build_jev_single_writer import stage, prepared


@pytest.fixture
def build_case(tmp_path,monkeypatch,application_state_dsn):
    return _build_case.__wrapped__(tmp_path,monkeypatch,application_state_dsn)


def fresh(adapter):
    return AgentConversationService().list_turns(adapter.turn.world_id,adapter.turn.conversation_id)[0]


def authorization(adapter,**changes):
    return t.BuildSectionReadAuthorizationV1(kind='build_section_read_authorized_v1',event_id=uuid4(),
        sequence=len(adapter._broker_execution().events),read_id=uuid4(),source_basis=adapter.fence.turn.graph_context_receipt.source_basis,
        source_class='saved_authored_source_not_played_truth',line_start=1,line_end=2,max_chars=12000).model_copy(update=changes)


def append_authorization(adapter,event):
    turn=adapter.fence.turn
    return AgentConversationService().authorize_build_section_read(turn.world_id,turn.conversation_id,turn.turn_id,
        expected_revision=turn.revision,expected_attempt=turn.attempt,authorization=event)


def read_receipt(auth,body,**changes):
    text=exact_saved_section(body,auth.source_basis.content_sha256,auth.line_start,auth.line_end)
    return t.ValidatedBuildSectionReadV1(kind='validated_build_section_read_v1',event_id=uuid4(),
        sequence=auth.sequence+1,read_id=auth.read_id,source_basis=auth.source_basis,source_class=auth.source_class,
        line_start=auth.line_start,line_end=auth.line_end,text=text,excerpt_sha256=sha256(text.encode()).hexdigest()).model_copy(update=changes)


def append_receipt(turn,event,body):
    return AgentConversationService().record_validated_build_section(turn.world_id,turn.conversation_id,turn.turn_id,
        expected_revision=turn.revision,expected_attempt=turn.attempt,receipt=event,source_markdown=body)


def test_actual_controller_authorizes_exact_section_then_fresh_reload(build_case,monkeypatch):
    adapter,calls,_=_start(build_case,monkeypatch)
    body=adapter.work.build_source.markdown
    result=json.loads(adapter.read_build_section(line_start=1,line_end=2))
    expected=''.join(body.splitlines(keepends=True)[:2])
    assert result['text']==expected and result['excerpt_sha256']==sha256(expected.encode()).hexdigest()
    assert result['source_class']=='saved_authored_source_not_played_truth'
    assert 'anchor_id' not in result and 'source_artifact_id' not in result
    turn=fresh(adapter)
    auth,receipt=turn.graph_context_execution.events[-2:]
    assert isinstance(auth,t.BuildSectionReadAuthorizationV1) and isinstance(receipt,t.ValidatedBuildSectionReadV1)
    assert auth.read_id==receipt.read_id and auth.source_basis==turn.graph_context_receipt.source_basis
    assert receipt==t.ValidatedBuildSectionReadV1.model_validate(result)
    assert calls=={'graph':0,'source':0}
    # Old immutable excerpt survives local work changing; no source re-read at history reload.
    adapter.work=replace(adapter.work,build_source=replace(adapter.work.build_source,markdown='different current workspace'))
    assert fresh(adapter).graph_context_execution.events[-1].text==expected


@pytest.mark.parametrize('body',['# Néra\r\n雪 and 🐐\r\nLast line', '# Title\n\n  café\n', 'one\rtwo\rthree'])
def test_unicode_and_original_line_endings_are_preserved(body):
    digest=sha256(body.encode()).hexdigest()
    assert exact_saved_section(body,digest,1,2)==''.join(body.splitlines(keepends=True)[:2])


@pytest.mark.parametrize('start,end',[(0,1),(2,1),(True,2),(1,9999)])
def test_invalid_range_does_not_expose_passage(build_case,monkeypatch,start,end):
    adapter,_,_=_start(build_case,monkeypatch)
    before=len(adapter.turn.graph_context_execution.events)
    with pytest.raises((ValueError,ApplicationStateError)):
        adapter.read_build_section(line_start=start,line_end=end)
    turn=fresh(adapter)
    assert not any(isinstance(e,t.ValidatedBuildSectionReadV1) for e in turn.graph_context_execution.events[before:])


def test_corrupt_complete_body_leaves_unresolved_authorization_and_blocks_provider(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch)
    adapter.work=replace(adapter.work,build_source=replace(adapter.work.build_source,markdown='Corrupt source'))
    with pytest.raises(ValueError):
        adapter.read_build_section(line_start=1,line_end=1)
    turn=fresh(adapter)
    assert isinstance(turn.graph_context_execution.events[-1],t.BuildSectionReadAuthorizationV1)
    original=next(e for e in turn.graph_context_execution.events if owner._is_provider_authorization(e))
    provider=original.model_copy(update={'event_id':uuid4(),'provider_attempt_id':uuid4(),
        'sequence':len(turn.graph_context_execution.events)})
    with pytest.raises(ApplicationStateError):
        AgentConversationService().authorize_provider_attempt_v2(turn.world_id,turn.conversation_id,turn.turn_id,
            expected_revision=turn.revision,expected_attempt=turn.attempt,provider_attempt_event=provider)
    assert fresh(adapter).completion is None


@pytest.mark.parametrize('field,value',[('world_id','foreign'),('document_id','foreign'),('registry_revision',99),
    ('content_sha256','f'*64),('visibility','player_safe')])
def test_app_rejects_authorization_outside_frozen_basis(build_case,monkeypatch,field,value):
    adapter,_,_=_start(build_case,monkeypatch)
    event=authorization(adapter)
    event=event.model_copy(update={'source_basis':event.source_basis.model_copy(update={field:value})})
    with pytest.raises(ApplicationStateError):
        append_authorization(adapter,event)
    assert not isinstance(fresh(adapter).graph_context_execution.events[-1],t.BuildSectionReadAuthorizationV1)


@pytest.mark.parametrize('fault',['forged_text','wrong_body','missing_body','wrong_range','foreign_id'])
def test_app_verifies_complete_body_not_caller_passage_hash(build_case,monkeypatch,fault):
    adapter,_,_=_start(build_case,monkeypatch)
    auth=authorization(adapter)
    turn,_=append_authorization(adapter,auth)
    body=adapter.work.build_source.markdown
    receipt=read_receipt(auth,body)
    if fault=='forged_text':
        text='## Forged\r\nNot in the immutable document.\r\n'
        receipt=receipt.model_copy(update={'text':text,'excerpt_sha256':sha256(text.encode()).hexdigest()})
    elif fault=='wrong_body':
        body='Different full body'
    elif fault=='missing_body':
        body=None
    elif fault=='wrong_range':
        receipt=receipt.model_copy(update={'line_start':2,'line_end':3})
    else:
        receipt=receipt.model_copy(update={'read_id':uuid4()})
    with pytest.raises(ApplicationStateError):
        append_receipt(turn,receipt,body)
    loaded=AgentConversationService().list_turns(turn.world_id,turn.conversation_id)[0]
    assert loaded.graph_context_execution.events[-1]==auth


def test_stale_claim_and_concurrent_receipt_cas(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch)
    auth=authorization(adapter)
    turn,_=append_authorization(adapter,auth)
    body=adapter.work.build_source.markdown
    receipt=read_receipt(auth,body)
    def attempt(_):
        try:
            return append_receipt(turn,receipt,body)
        except ApplicationStateError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(attempt,range(2)))
    assert sum(value is not None for value in outcomes)==1
    loaded=AgentConversationService().list_turns(turn.world_id,turn.conversation_id)[0]
    assert sum(isinstance(e,t.ValidatedBuildSectionReadV1) for e in loaded.graph_context_execution.events)==1
    with pytest.raises(ApplicationStateError):
        append_receipt(turn,receipt,body)


def test_second_receipt_for_same_read_and_tampered_reload_refuse(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch)
    adapter.read_build_section(line_start=1,line_end=2)
    turn=fresh(adapter)
    receipt=turn.graph_context_execution.events[-1]
    duplicate=receipt.model_copy(update={'event_id':uuid4(),'sequence':len(turn.graph_context_execution.events)})
    with pytest.raises(ApplicationStateError):
        append_receipt(turn,duplicate,adapter.work.build_source.markdown)
    data=turn.model_dump(mode='json',by_alias=True)
    data['graph_context_execution']['events'][-1]['text']='Changed text'
    with pytest.raises(ValueError):
        t.Turn.model_validate(data)
    data=turn.model_dump(mode='json',by_alias=True)
    data['graph_context_execution']['events'][-1]['source_basis']['visibility']='player_safe'
    with pytest.raises(ValueError):
        t.Turn.model_validate(data)


def test_post_writer_read_refuses_before_passage(build_case,monkeypatch):
    adapter,staged,_,_=stage(build_case,monkeypatch)
    assert adapter.authorize_prepared_build_writer(prepared(staged))
    before=len(adapter.turn.graph_context_execution.events)
    with pytest.raises(ApplicationStateError):
        adapter.read_build_section(line_start=1,line_end=2)
    assert len(fresh(adapter).graph_context_execution.events)==before


@pytest.mark.parametrize('state',['pending','unknown','known_not_sent'])
def test_unresolved_or_unsent_controller_cannot_authorize_section(build_case,monkeypatch,state):
    from tests.test_agent_build_jev_dispatch import _adapter, _prepared, _invoke, Wire
    adapter,initial=_adapter(build_case)
    if state=='unknown':
        from generationengine import GenerationEngineError
        with pytest.raises(GenerationEngineError):
            _invoke(adapter,initial,Wire(adapter,timeout=True),[])
    else:
        from generationengine.decision_dispatch import DecisionDispatchEvent
        view=_prepared(initial)
        assert adapter.authorize_prepared_build_decision(view)
        if state=='known_not_sent':
            assert adapter.record_prepared_build_decision(DecisionDispatchEvent(view,'known_not_sent'))
    before=len(adapter.turn.graph_context_execution.events)
    with pytest.raises(ApplicationStateError):
        adapter.read_build_section(line_start=1,line_end=2)
    assert len(fresh(adapter).graph_context_execution.events)==before


def test_app_enforces_authorized_text_size_and_trace_cannot_replace_proof(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch)
    auth=authorization(adapter,max_chars=2)
    turn,_=append_authorization(adapter,auth)
    body=adapter.work.build_source.markdown
    receipt=read_receipt(auth,body)
    with pytest.raises(ApplicationStateError):
        append_receipt(turn,receipt,body)
    # Trace presence is not authority for a forged/missing immutable body.
    with pytest.raises(ApplicationStateError):
        append_receipt(turn,receipt,None)


def test_read_authority_does_not_depend_on_trace_collector(build_case,monkeypatch):
    adapter,_,_=_start(build_case,monkeypatch)
    adapter.context_capture=None
    result=json.loads(adapter.read_build_section(line_start=2,line_end=2))
    assert result['text']==adapter.work.build_source.markdown.splitlines(keepends=True)[1]
    assert isinstance(fresh(adapter).graph_context_execution.events[-1],t.ValidatedBuildSectionReadV1)


def test_app_enforces_smaller_frozen_policy_and_accepts_equality(build_case,monkeypatch):
    original=owner._freeze_policy_receipt
    limit=len(exact_saved_section(build_case[0].markdown,build_case[0].content_sha256,1,2))
    def freeze(*args,**kwargs):
        receipt,execution,membership=original(*args,**kwargs)
        policy=execution.policy.model_copy(update={'max_chars_per_source_read':limit})
        execution=execution.model_copy(update={'policy':policy,
            'execution_policy_sha256':t.graph_execution_policy_digest_v3(receipt.context_receipt_sha256,policy)})
        return receipt,type(execution).model_validate(execution.model_dump(mode='json',by_alias=True)),membership
    monkeypatch.setattr(owner,'_freeze_policy_receipt',freeze)
    adapter,_,_=_start(build_case,monkeypatch)
    assert fresh(adapter).graph_context_execution.policy.max_chars_per_source_read==limit
    with pytest.raises(ApplicationStateError):
        append_authorization(adapter,authorization(adapter,max_chars=limit+1))
    auth=authorization(adapter,max_chars=limit)
    turn,_=append_authorization(adapter,auth)
    body=adapter.work.build_source.markdown
    receipt=read_receipt(auth,body)
    completed,created=append_receipt(turn,receipt,body)
    assert created and completed.graph_context_execution.events[-1].text==receipt.text
