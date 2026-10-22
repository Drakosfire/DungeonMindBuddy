"""Real APP input-proof fences. Provider lifecycle here is synthetic, no sends."""
from hashlib import sha256
import json
from uuid import uuid4

import psycopg
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.play_graph_authority import play_source_frame,play_graph_execution_policy_digest
from application_state.agent_conversation.play_graph_input import NativePlayInputV2
from application_state.agent_conversation import play_graph_source_owner as owner
from application_state.errors import ApplicationStateValidationError,ApplicationStateConflictError,ApplicationStateNotFoundError
from application_state.agent_conversation.rules_authority_types import canonical_bytes
from tests.application_state.test_native_play_graph_postgres import make_submission
from tests.test_play_graph_context import seal_receipt
from tests.test_play_graph_authority import native_provider


def prepared_native(dsn,*,moment=True,edition=False,forged_moment=False):
    service,sub,frame=make_submission(edition=edition)
    if moment:
        with psycopg.connect(dsn) as conn:text=owner.read_native_play_current_moment(conn,sub.play_context_receipt)
        assert sub.play_context_receipt.scene_note not in text
        if forged_moment:text+=' Invented scene detail.'
        frame=play_source_frame((*frame.sources,t.PlaySourcePayloadV1(source_kind='current_moment',
            locator=t.play_source_locator(sub.play_context_receipt),text=text)))
    carrier=NativePlayInputV2(submission_id=sub.idempotency_key,message=sub.user_text,source_frame=frame)
    raw=json.dumps({'model':'synthetic','messages':[{'role':'user','content':canonical_bytes(carrier).decode()}],'tools':[]},ensure_ascii=False)
    digest=sha256(raw.encode()).hexdigest();wire=sub.graph_context_receipt.model_dump(mode='json',by_alias=True)
    wire.update(play_sources=frame.manifest.model_dump(mode='json',by_alias=True),play_source_frame_sha256=t.canonical_sha256(frame))
    wire['assembled_input']['assembled_input_sha256']=digest;r=seal_receipt(wire)
    e=sub.graph_context_execution.model_copy(update={'context_receipt_sha256':r.context_receipt_sha256,
        'execution_policy_sha256':play_graph_execution_policy_digest(r.context_receipt_sha256,sub.graph_context_execution.policy)})
    sub=sub.model_copy(update={'graph_context_receipt':r,'graph_context_execution':e})
    turn=service.accept_turn(sub);turn=service.claim_turn(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision).turn
    auth=native_provider(1).model_copy(update={'envelope_sha256':digest,'api_mode':'chat_completions'})
    return service,sub,turn,auth,raw


def append(service,sub,turn,auth,raw,**changes):
    kwargs=dict(world_id=sub.world_id,conversation_id=sub.conversation_id,turn_id=turn.turn_id,
        expected_revision=turn.revision,expected_attempt=turn.attempt,provider_attempt_event=auth,prepared_request_json=raw)
    kwargs.update(changes)
    return service.authorize_native_play_provider(**kwargs)


@pytest.mark.parametrize('edition',[False,True])
def test_source_and_authorization_commit_together_and_reopen_exactly(application_state_dsn,edition):
    service,sub,turn,auth,raw=prepared_native(application_state_dsn,edition=edition)
    updated,fresh=append(service,sub,turn,auth,raw)
    assert fresh and updated.revision==turn.revision+1
    assert [e.kind for e in updated.graph_context_execution.events]==['play_source_provider_inclusion_v1','provider_attempt_authorized_v3']
    assert updated.graph_context_execution.events[0].provider_attempt_id==auth.provider_attempt_id
    assert service.list_turns(sub.world_id,sub.conversation_id)[0]==updated


def test_note_only_needs_no_content_read_and_exact_replay_grants_no_send(application_state_dsn,monkeypatch):
    service,sub,turn,auth,raw=prepared_native(application_state_dsn,moment=False)
    monkeypatch.setattr(owner,'read_native_play_current_moment',lambda *args:pytest.fail('Unnecessary content read'))
    updated,fresh=append(service,sub,turn,auth,raw);assert fresh
    replay,fresh=append(service,sub,updated,auth,raw)
    assert not fresh and replay==updated


def test_later_producer_reproves_exposure_without_repeating_immutable_content_read(application_state_dsn,monkeypatch):
    service,sub,turn,auth,raw=prepared_native(application_state_dsn)
    calls=[];original=owner.read_native_play_current_moment
    def counted(*args):calls.append(1);return original(*args)
    monkeypatch.setattr(owner,'read_native_play_current_moment',counted)
    turn,fresh=append(service,sub,turn,auth,raw);assert fresh and len(calls)==1
    for outcome in ('sdk_entered','response_received'):
        event=t.ProviderOutcomeEventV1(kind='provider_outcome',event_id=uuid4(),sequence=len(turn.graph_context_execution.events),
            provider_attempt_id=auth.provider_attempt_id,outcome=outcome)
        turn,_=service.record_provider_outcome(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,outcome=event)
    second=native_provider(len(turn.graph_context_execution.events)+1).model_copy(update={'envelope_sha256':auth.envelope_sha256,'api_mode':'chat_completions'})
    turn,fresh=append(service,sub,turn,second,raw)
    assert fresh and len(calls)==1
    included=[e for e in turn.graph_context_execution.events if isinstance(e,t.PlaySourceProviderInclusionV1)]
    assert [e.provider_attempt_id for e in included]==[auth.provider_attempt_id,second.provider_attempt_id]


@pytest.mark.parametrize('change',['body','missing','wrongtype','owner_body','stale','expired','world','conversation'])
def test_failed_proof_or_fence_persists_neither_event(application_state_dsn,change):
    service,sub,turn,auth,raw=prepared_native(application_state_dsn)
    kw={}
    if change=='body':raw+=' '
    if change=='missing':raw=None
    if change=='wrongtype':raw=b'{}'
    if change=='owner_body':
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE content.work_revision SET markdown=markdown||'Corruption' WHERE work_revision_id=%s",(sub.play_context_receipt.runbook_work_revision_id,))
    if change=='stale':kw['expected_revision']=turn.revision-1
    if change=='expired':
        with psycopg.connect(application_state_dsn) as conn:conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",(turn.turn_id,))
    if change=='world':kw['world_id']='foreign-world'
    if change=='conversation':kw['conversation_id']=uuid4()
    with pytest.raises((ApplicationStateValidationError,ApplicationStateConflictError,ApplicationStateNotFoundError)):
        append(service,sub,turn,auth,raw,**kw)
    with psycopg.connect(application_state_dsn) as conn:
        revision,execution=conn.execute('SELECT revision,graph_context_execution FROM agent.turn WHERE turn_id=%s',(turn.turn_id,)).fetchone()
    assert revision==turn.revision and execution['events']==[]


def test_failed_atomic_update_does_not_leave_a_source_witness(application_state_dsn,monkeypatch):
    service,sub,turn,auth,raw=prepared_native(application_state_dsn)
    from application_state.agent_conversation import repository
    original=repository.update_graph_execution
    def fail_after_write(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('Injected update failure')
    monkeypatch.setattr(repository,'update_graph_execution',fail_after_write)
    with pytest.raises(RuntimeError,match='Injected update failure'):append(service,sub,turn,auth,raw)
    stored=service.list_turns(sub.world_id,sub.conversation_id)[0]
    assert stored.revision==turn.revision and stored.graph_context_execution.events==[]


def test_replay_still_requires_the_exact_original_request_bytes(application_state_dsn):
    service,sub,turn,auth,raw=prepared_native(application_state_dsn,moment=False)
    updated,_=append(service,sub,turn,auth,raw)
    with pytest.raises(ApplicationStateValidationError,match='input snapshot'):
        append(service,sub,updated,auth,raw+' ')
    assert service.list_turns(sub.world_id,sub.conversation_id)[0]==updated


def test_canonical_receipt_and_input_do_not_replace_independent_source_owner(application_state_dsn):
    service,sub,turn,auth,raw=prepared_native(application_state_dsn,forged_moment=True)
    with pytest.raises(ApplicationStateValidationError,match='independent source owner'):
        append(service,sub,turn,auth,raw)
    stored=service.list_turns(sub.world_id,sub.conversation_id)[0]
    assert stored.revision==turn.revision and stored.graph_context_execution.events==[]


def test_concurrent_provider_admissions_leave_one_atomic_pair(application_state_dsn,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    service,sub,turn,auth,raw=prepared_native(application_state_dsn)
    other=native_provider(1).model_copy(update={'envelope_sha256':auth.envelope_sha256,'api_mode':'chat_completions'})
    calls=[];original=owner.read_native_play_current_moment;barrier=Barrier(2)
    def counted(*args):calls.append(1);return original(*args)
    monkeypatch.setattr(owner,'read_native_play_current_moment',counted)
    def attempt(event):
        barrier.wait(timeout=10)
        try:
            return append(service,sub,turn,event,raw)
        except ApplicationStateConflictError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,[auth,other]))
    assert sum(result is not None and result[1] for result in results)==1
    assert len(calls)==1
    saved=service.list_turns(sub.world_id,sub.conversation_id)[0]
    inclusion,authorization=saved.graph_context_execution.events
    assert inclusion.kind=='play_source_provider_inclusion_v1'
    assert authorization.kind=='provider_attempt_authorized_v3'
    assert inclusion.provider_attempt_id==authorization.provider_attempt_id
    assert saved.revision==turn.revision+1
