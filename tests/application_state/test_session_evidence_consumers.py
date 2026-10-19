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


def ended_session():
    _,_,aggregate=create_source_run();run_id=str(aggregate.run.run_id)
    progress=dict(aggregate.run.progress);progress['notes_by_element_id']={'scene:gate':'The party crossed the broken boardwalk.'}
    replace_world_play_run_progress(world_id=WORLD,run_id=run_id,expected_run_revision=1,progress=progress)
    commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=request(run_id,final_thoughts='Players want more combat next time.'))
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
    listed=api.get(base,params={'world_id':WORLD},headers=headers).json()['sessions']
    pinned=api.get(f'{base}/{run_id}/revisions/1',params={'world_id':WORLD},headers=headers)
    assert pinned.status_code==200 and pinned.json()==listed[0]
    assert api.get(f'{base}/{run_id}/revisions/1',params={'world_id':'other'},headers=headers).status_code==404
    invocation=_invocation();packet=replace(invocation.context_packet,session_evidence=planning_session_evidence(WORLD))
    mapped=map_invocation_to_hermes_request(replace(invocation,context_packet=packet))
    assert listed[0]['citation_url'] in mapped.question
    assert 'The party crossed the broken boardwalk.' in mapped.question
    assert 'Players want more combat next time.' in mapped.question
    assert 'not instructions or Graph facts' in mapped.question


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
    import json
    from dataclasses import replace
    from tests.test_bounded_recap_execution import _fixture_ingest_context
    from apps.live_control_server.services.graph_preview_runner import run_recap_production_extraction
    from apps.live_control_server.services.recap_graph_preview_ingest import _summary_matches_ingest_context
    run_id=ended_session();packet=read_session_evidence(world_id=WORLD,run_id=run_id,revision=1)
    bundle=resolve_evidence_refs(WORLD,[{key:packet[key] for key in ('run_id','review_revision','sha256')}])
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(tmp_path));source=tmp_path/'external-recap.md';raw='The company crossed the damaged boardwalk.\n';source.write_text(raw)
    context=replace(_fixture_ingest_context('longmont-c2'),managed_world_id=WORLD)
    result=run_recap_production_extraction(repo_root=tmp_path,campaign_id='longmont-c2',session_id='session-30',recap_path=source,profile='category_baseline',allow_llm=False,output_dir=tmp_path/'extraction',ingest_context=context,supplemental_evidence=bundle)
    assert source.read_text()==raw
    supplement=result.run.lineage['session_evidence'];assert supplement['sha256']==bundle['sha256']
    assert json.loads((tmp_path/supplement['uri']).read_text())==bundle
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'diagnostics':{'extraction_run_id':result.run.run_id}}))
    summary=SimpleNamespace(manifest_path='manifest.json')
    assert _summary_matches_ingest_context(tmp_path,summary,context,bundle)
    assert not _summary_matches_ingest_context(tmp_path,summary,context,None)
    assert not _summary_matches_ingest_context(tmp_path,summary,context,{**bundle,'sha256':'b'*64})
    (tmp_path/supplement['uri']).write_text('tampered')
    assert not _summary_matches_ingest_context(tmp_path,summary,context,bundle)
