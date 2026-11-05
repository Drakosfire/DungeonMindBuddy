import hashlib
import pytest
from src.graph_memory.extraction.name_review import review_names,apply_review

CAT={'entities':[{'entity_id':'a','names':['Maraline']},{'entity_id':'b','names':['Berenwald']}], 'native_pin':{'revision_id':'r1'}}
SCOPE={'managed_world_id':'m','native_world_id':'n','binding_version':1,'campaign_id':'c'}


def test_generic_transposition_and_missing_letter_review_requires_all_decisions():
    text='Mara spent time with Marlaine and Berenwld. Maraline stayed.'
    review=review_names(text,CAT,SCOPE)
    assert [s['surface'] for s in review['suggestions']]==['Marlaine','Berenwld']
    assert review['exact_mention_count']==1
    with pytest.raises(ValueError,match='Review possible'):apply_review(text,review,None)
    with pytest.raises(ValueError,match='every'):apply_review(text,review,{'review_id':review['review_id'],'decisions':[]})
    receipt={'review_id':review['review_id'],'decisions':[{'id':s['id'],'replacement':s['options'][0]} for s in review['suggestions']]}
    corrected,record=apply_review(text,review,receipt)
    assert corrected=='Mara spent time with Maraline and Berenwald. Maraline stayed.'
    assert record['review']['source_sha256']==hashlib.sha256(text.encode()).hexdigest()
    assert record['corrected_sha256']==hashlib.sha256(corrected.encode()).hexdigest()


def test_stale_catalog_source_scope_and_arbitrary_replacement_rejected():
    text='Berenwld waits.'
    review=review_names(text,CAT,SCOPE)
    receipt={'review_id':review['review_id'],'decisions':[{'id':review['suggestions'][0]['id'],'replacement':'An invented name'}]}
    with pytest.raises(ValueError,match='outside'):apply_review(text,review,receipt)
    for changed in [review_names(text+'!',CAT,SCOPE),review_names(text,{**CAT,'native_pin':{'revision_id':'r2'}},SCOPE),review_names(text,CAT,{**SCOPE,'campaign_id':'other'})]:
        with pytest.raises(ValueError,match='stale'):apply_review(text,changed,receipt)
    receipt['decisions'][0]['replacement']=None
    corrected,record=apply_review(text,review,receipt)
    assert corrected==text and record['applied_edits']==[]


def test_ambiguous_names_never_become_automatic_correction_targets():
    cat={'entities':[{'entity_id':'a','names':['Marlena']},{'entity_id':'b','names':['Marlena']}],'ambiguous_names':['marlena']}
    assert review_names('Marlna waits.',cat,SCOPE)['suggestions']==[]


@pytest.mark.parametrize("replacement", ["Berenwald", None])
def test_corrections_and_original_are_database_retained_before_owned_extraction(tmp_path,monkeypatch,application_state_dsn,replacement):
    from graph_memory.ingestion.native_recap_source import SourceScope
    from apps.live_control_server.services import recap_graph_preview_ingest as host,recap_name_review as names
    from apps.live_control_server.services.source_artifact_registry import load_registered_source_artifact_text
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(tmp_path))
    monkeypatch.setattr(names.known_character_context,'read_known_character_catalog',lambda *a:{**CAT,'native_pin':{'native_world_id':'n','binding_version':1}})
    scope=SourceScope(**SCOPE)
    text='Berenwld waits.'
    review=names.prepare_name_review(text,scope,session_id="session-1")[2]
    calls=[]
    def run(**kwargs):
        calls.append(kwargs)
        record=kwargs['name_review_record']
        assert load_registered_source_artifact_text(tmp_path,record['original_source_artifact_id'])[1]==text+'\n'
        assert load_registered_source_artifact_text(tmp_path,kwargs['source_artifact_id'])[1]==('Berenwald waits.\n' if replacement else 'Berenwld waits.\n')
        assert record['decisions'][0]['replacement']==replacement
        assert bool(record['applied_edits']) == bool(replacement)
        return type('Result',(),{'run':object()})()
    monkeypatch.setattr(host,'run_recap_production_extraction',run)
    monkeypatch.setattr(host,'reusable_recap_extraction',lambda **kw:pytest.fail('Explicit decisions must not disappear through historical reuse'))
    monkeypatch.setattr(host,'project_recap_extraction_run',lambda **kw:{'status':'candidate_validation_ready'})
    args=dict(repo_root=tmp_path,campaign_id='c',session=1,recap_text=text,force_graph_run=False,ingest_context=scope)
    with pytest.raises(ValueError,match='Review possible'):host.extract_recap(**args)
    assert calls==[]
    receipt={'review_id':review['review_id'],'decisions':[{'id':review['suggestions'][0]['id'],'replacement':replacement}]}
    host.extract_recap(**args,name_review=receipt)
    assert len(calls)==1


def test_http_name_review_authenticates_before_identity_read(monkeypatch):
    from fastapi import FastAPI,HTTPException
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import recap_ingest as route
    from apps.live_control_server.services import hosted_auth,recap_name_review as names
    monkeypatch.setattr(hosted_auth,'deployment_environment',lambda:'local')
    monkeypatch.setattr(hosted_auth,'auth_mode',lambda:hosted_auth.LOCAL_MODE)
    monkeypatch.setattr(names,'prepare_name_review',lambda *a,**kw:pytest.fail('unauthenticated identity read'))
    def denied(*a):raise HTTPException(status_code=403,detail='Denied')
    monkeypatch.setattr(route,'_native_source_actor',denied)
    app=FastAPI();app.include_router(route.router)
    with TestClient(app) as client:
        r=client.post('/api/live/recap-name-review',json={'operation':'generate_recap_memory','campaign_id':'c','managed_world_id':'m','session':1,'raw_text':'Berenwld waits.'})
    assert r.status_code==403
