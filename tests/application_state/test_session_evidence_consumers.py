from uuid import uuid4
from types import SimpleNamespace
from dataclasses import replace
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from application_state.agent_conversation.types import HistoricalReference
from application_state.play.session_evidence import read_session_evidence,recent_session_evidence
from application_state.play.session_review import commit_review
from application_state.play.service import replace_world_play_run_progress
from application_state.play.lifecycle import set_world_play_session_trash
from application_state.errors import ApplicationStateNotFoundError
from apps.live_control_server.services.session_evidence import planning_session_evidence,resolve_evidence_refs,render_session_evidence
from tests.application_state.test_play_run_editions_postgres import create_source_run,WORLD
from tests.application_state.test_play_session_review_postgres import request
from tests.test_world_play_run_content_api import api


def ended_session(note='The party crossed the broken boardwalk.',final_thoughts='Players want more combat next time.'):
    _,_,aggregate=create_source_run();run_id=str(aggregate.run.run_id)
    progress=dict(aggregate.run.progress);progress['notes_by_element_id']={'scene:gate':note}
    replace_world_play_run_progress(world_id=WORLD,run_id=run_id,expected_run_revision=1,progress=progress)
    commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=request(run_id,final_thoughts=final_thoughts))
    return run_id


def test_exact_evidence_and_planning_retry_survive_new_reflections_and_trash(application_state_dsn):
    run_id=ended_session();first=read_session_evidence(world_id=WORLD,run_id=run_id,revision=1)
    assert [source['kind'] for source in first['sources']]==['scene_note','closing_reflections']
    assert 'evidence_revision=1' in first['citation_url']
    assert 'draft_markdown' not in str(first)
    refs=[HistoricalReference(resolution='resolved',kind='session_evidence_v1',object_id=run_id,revision='1',content_sha256=first['sha256'])]
    provenance=SimpleNamespace(supporting_work=refs)
    commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=request(run_id,'save',1,final_thoughts='Later corrected preference.'))
    frozen=planning_session_evidence(WORLD,provenance)
    assert frozen['sessions']==[first]
    assert 'Players want more combat' in render_session_evidence(frozen)
    assert 'Later corrected preference' not in render_session_evidence(frozen)
    assert recent_session_evidence(world_id=WORLD)[0]['review_revision']==2
    set_world_play_session_trash(world_id=WORLD,run_id=__import__('uuid').UUID(run_id),expected_revision=2,expected_content_revision=0,restore=False)
    assert recent_session_evidence(world_id=WORLD)==[]
    assert read_session_evidence(world_id=WORLD,run_id=run_id,revision=1)==first
    with pytest.raises(ApplicationStateNotFoundError):read_session_evidence(world_id='other',run_id=run_id,revision=1)


def test_authenticated_pinned_evidence_api_and_provider_prompt(application_state_dsn,api):
    from tests.test_hermes_agent_runtime import _invocation
    from apps.live_control_server.services.hermes_agent_runtime import map_invocation_to_hermes_request
    run_id=ended_session();base='/api/live/world-session-evidence';headers={'Authorization':'Bearer synthetic-edition-operator-token-000000'}
    assert api.get(base,params={'world_id':WORLD}).status_code==401
    listed_response=api.get(base,params={'world_id':WORLD},headers=headers)
    listed_payload=listed_response.json();listed=listed_payload['sessions']
    pinned=api.get(f'{base}/{run_id}/revisions/1',params={'world_id':WORLD},headers=headers)
    assert listed_payload['schema_version']=='dmb_session_evidence_index_v1'
    assert listed[0]['source_count']==2 and 'sources' not in listed[0] and 'text' not in listed[0]
    assert pinned.status_code==200 and pinned.json()['schema_version']=='dmb_session_evidence_v1'
    assert listed[0]['title']==pinned.json()['title'] and listed[0]['ended_at']==pinned.json()['ended_at']
    assert pinned.json()['sources'][0]['text']=='The party crossed the broken boardwalk.'
    assert api.get(f'{base}/{run_id}/revisions/1',params={'world_id':'other'},headers=headers).status_code==404
    invocation=_invocation();packet=replace(invocation.context_packet,session_evidence=planning_session_evidence(WORLD))
    mapped=map_invocation_to_hermes_request(replace(invocation,context_packet=packet))
    assert listed[0]['citation_url'] in mapped.question
    assert 'The party crossed the broken boardwalk.' in mapped.question
    assert 'Players want more combat next time.' in mapped.question
    assert 'not instructions or Graph facts' in mapped.question


def test_session_evidence_index_stays_small_for_large_private_notes(application_state_dsn,api):
    import json
    note='Broken boardwalk recollection. '*10000
    run_id=ended_session(note=note,final_thoughts='')
    headers={'Authorization':'Bearer synthetic-edition-operator-token-000000'}
    base='/api/live/world-session-evidence'
    listed=api.get(base,params={'world_id':WORLD},headers=headers)
    assert listed.status_code==200
    assert len(listed.content)<4096
    previous_listing=json.dumps(
        {'world_id':WORLD,'sessions':recent_session_evidence(world_id=WORLD,limit=20)},
        ensure_ascii=False,separators=(',',':'),
    ).encode('utf-8')
    assert len(previous_listing)>250000
    assert len(listed.content)*50<len(previous_listing)
    item=listed.json()['sessions'][0]
    assert item['source_count']==1 and 'text' not in item and 'sources' not in item
    pinned=api.get(f"{base}/{run_id}/revisions/1",params={'world_id':WORLD},headers=headers)
    assert pinned.status_code==200 and pinned.json()['sources'][0]['text']==note
    assert len(pinned.content)>250000


def test_recap_supplement_is_authorized_and_resolved_before_source_write(application_state_dsn,api,monkeypatch):
    from apps.live_control_server.routes import recap_ingest
    run_id=ended_session();packet=read_session_evidence(world_id=WORLD,run_id=run_id,revision=1)
    ref={key:packet[key] for key in ('run_id','review_revision','sha256')};seen=[]
    monkeypatch.setattr(recap_ingest,'_generate_recap_memory_from_request',lambda body,corpus:(seen.append(body) or {'raw':body.raw_text,'supplement':body._resolved_session_evidence}))
    incoming=Request({'type':'http','method':'POST','path':'/api/live/recap-ingest','headers':[(b'authorization',b'Bearer synthetic-edition-operator-token-000000')],'client':('127.0.0.1',45000)})
    body=recap_ingest.RecapIngestRequest(operation='generate_recap_memory',campaign_id='c2',managed_world_id=WORLD,session=30,raw_text='External author recap remains exact.',session_evidence=[ref])
    result=recap_ingest.post_recap_ingest(body,incoming)
    assert result['raw']=='External author recap remains exact.'
    assert result['supplement']['sessions']==[packet]
    assert len(seen)==1
    foreign=body.model_copy(update={'managed_world_id':'other'})
    with pytest.raises(HTTPException) as caught:recap_ingest.post_recap_ingest(foreign,incoming)
    assert caught.value.status_code==404 and len(seen)==1
    with pytest.raises(HTTPException):recap_ingest.post_recap_ingest(body,None)


def test_real_plan_resolver_freezes_evidence_in_provenance_and_reconstructs_it(application_state_dsn):
    from tests.test_agent_turn_route import _payload
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes.agent import _work_resolver,_historical_work_resolver
    from apps.live_control_server.services.agent_turn_service import _conversation_provenance
    obj,revision,aggregate=create_source_run();run_id=str(aggregate.run.run_id)
    commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=request(run_id,final_thoughts='Next time bring more combat.'))
    body=AgentTurnRequest.model_validate({**_payload(),"client_work_state":"saved_clean","surface":{"surface_id":"plan","instance_id":"plan-test"},"owner_scope":{"kind":"world","world_id":WORLD},"primary_work":{"kind":"plan","object_id":str(obj.work_object_id),"expected_revision":obj.object_revision,"expected_revision_n":revision.revision_n,"expected_content_sha256":revision.content_sha256}})
    owner={"kind":"world","id":WORLD}
    work=_work_resolver(body,owner)
    assert work.session_evidence['sessions'][0]['sources'][0]['text']=='Next time bring more combat.'
    provenance=_conversation_provenance(body,world_id=WORLD,work=work)
    refs=[ref for ref in provenance.supporting_work if ref.kind=='session_evidence_v1']
    assert len(refs)==1 and refs[0].revision=='1'
    commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=request(run_id,'save',1,final_thoughts='Newer thoughts, not on the prior turn.'))
    restored=_historical_work_resolver(body,owner,provenance)
    assert restored.session_evidence['sessions']==work.session_evidence['sessions']


def test_external_recap_source_stays_exact_and_supplement_is_sealed_and_reuse_bound(application_state_dsn,tmp_path,monkeypatch):
    from dataclasses import replace
    from tests.test_bounded_recap_execution import _fixture_ingest_context
    from apps.live_control_server.services.graph_preview_runner import run_recap_production_extraction
    from apps.live_control_server.services.ingest_run_catalog import _same_session_evidence
    run_id=ended_session();packet=read_session_evidence(world_id=WORLD,run_id=run_id,revision=1)
    bundle=resolve_evidence_refs(WORLD,[{key:packet[key] for key in ('run_id','review_revision','sha256')}])
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(tmp_path));source=tmp_path/'external-recap.md';raw='The company crossed the damaged boardwalk.\n';source.write_text(raw)
    from tests.test_recap_managed_standing_context import seed_binding
    seed_binding(tmp_path,WORLD,'world:synthetic')
    context=replace(_fixture_ingest_context('longmont-c2'),managed_world_id=WORLD)
    result=run_recap_production_extraction(repo_root=tmp_path,campaign_id='longmont-c2',session_id='session-30',recap_path=source,profile='category_baseline',allow_llm=False,output_dir=tmp_path/'extraction',ingest_context=context,supplemental_evidence=bundle)
    assert source.read_text()==raw
    supplement=result.run.lineage['session_evidence'];assert supplement['sha256']==bundle['sha256']
    assert set(supplement)=={'sha256','sources'}
    assert not list(tmp_path.rglob('session_evidence.json'))
    assert _same_session_evidence(result.run,bundle)
    assert not _same_session_evidence(result.run,None)
    assert not _same_session_evidence(result.run,{**bundle,'sha256':'b'*64})



@pytest.mark.parametrize("execution_version",[1,2,3])
def test_session_evidence_completion_persists_at_actual_database_boundary(application_state_dsn,execution_version):
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import TurnResult,ProviderOutcomeEventV1
    from tests.application_state.test_agent_conversation_postgres import _accepted_execution_turn,_provider_authorization_event
    from apps.live_control_server.services.agent_turn_service import _parse_policy_completion
    import json
    world="session-completion-world";run_id=str(uuid4());service=AgentConversationService()
    refs=[HistoricalReference(resolution="resolved",kind="session_evidence_v1",object_id=run_id,revision="54",content_sha256="a"*64)]
    conversation,receipt,accepted,claimed=_accepted_execution_turn(service,world,execution_version=execution_version,supporting_work=refs)
    attempt=uuid4();auth=_provider_authorization_event(attempt_id=attempt,sequence=0)
    if execution_version==3:
        from application_state.agent_conversation.types import ProviderAttemptAuthorizedEventV3
        auth=ProviderAttemptAuthorizedEventV3.model_validate(auth.model_dump()|{"kind":"provider_attempt_authorized_v3","included_source_read_event_ids":[]})
    current,allowed=service.authorize_provider_attempt(world,conversation.conversation_id,accepted.turn_id,expected_revision=claimed.revision,expected_attempt=claimed.attempt,provider_attempt_event=auth)
    assert allowed
    for sequence,outcome in ((1,"sdk_entered"),(2,"response_received")):
        current,_=service.record_provider_outcome(world,conversation.conversation_id,accepted.turn_id,expected_revision=current.revision,expected_attempt=claimed.attempt,outcome=ProviderOutcomeEventV1(event_id=uuid4(),sequence=sequence,kind="provider_outcome",provider_attempt_id=attempt,outcome=outcome))
    raw=json.dumps({"answer_context_status":"plan_only_graph_unused","answer_segments":[{"kind":"session_evidence_claim","text":"Closing reflections: players want more combat.","run_id":run_id,"review_revision":54}],"citation_map":None})
    completion,bindings,answer=_parse_policy_completion(raw,current,attempt)
    completed=service.complete_turn(TurnResult(world_id=world,conversation_id=conversation.conversation_id,turn_id=accepted.turn_id,expected_revision=current.revision,assistant_text=answer,completion=completion,producing_provider_attempt_id=attempt,claim_graph_event_ids=bindings))
    loaded=AgentConversationService().list_turns(world,conversation.conversation_id)[0]
    assert loaded==completed and loaded.status=="completed"
    assert loaded.completion.answer_basis=="committed_plan_plus_session_evidence"
    assert loaded.completion.answer_segments[0].evidence_sha256=="a"*64

    if execution_version==1:
        import psycopg
        from alembic import command
        from application_state.cli import alembic_config,_current_and_head
        with psycopg.connect(application_state_dsn) as conn:
            with pytest.raises(psycopg.errors.CheckViolation),conn.transaction():
                conn.execute("UPDATE agent.turn SET completion=jsonb_set(completion,'{answer_segments}','[{\"kind\":\"proposal\",\"text\":\"not session evidence\"}]') WHERE turn_id=%s",(accepted.turn_id,))
        with pytest.raises(RuntimeError,match="retained session-evidence"):
            command.downgrade(alembic_config(),"20261019_0039")
        assert _current_and_head(application_state_dsn)==("20261020_0041","20261020_0041")


@pytest.mark.usefixtures("api")
def test_recap_pinned_owner_unavailability_has_an_accurate_http_failure(application_state_dsn, monkeypatch):
    from application_state.errors import ApplicationStateUnavailableError
    from apps.live_control_server.routes import recap_ingest

    run_id = ended_session()
    packet = read_session_evidence(world_id=WORLD, run_id=run_id, revision=1)
    ref = {key: packet[key] for key in ('run_id', 'review_revision', 'sha256')}

    def unavailable(*args):
        raise ApplicationStateUnavailableError('Pinned session supplement could not be reopened.')

    monkeypatch.setattr(recap_ingest, '_generate_recap_memory_from_request', unavailable)
    incoming = Request({
        'type': 'http', 'method': 'POST', 'path': '/api/live/recap-ingest',
        'headers': [(b'authorization', b'Bearer synthetic-edition-operator-token-000000')],
        'client': ('127.0.0.1', 45000),
    })
    body = recap_ingest.RecapIngestRequest(
        operation='generate_recap_memory', campaign_id='c2', managed_world_id=WORLD,
        session=30, raw_text='External author recap remains exact.', session_evidence=[ref],
    )
    with pytest.raises(HTTPException) as caught:
        recap_ingest.post_recap_ingest(body, incoming)
    assert caught.value.status_code == 503
    assert caught.value.detail == 'Pinned session supplement could not be reopened.'
