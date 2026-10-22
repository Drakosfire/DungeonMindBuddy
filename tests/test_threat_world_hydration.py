"""Scope contract through the real HTTP parser, service and projection DTO."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from apps.live_control_server.routes import threat_query_hydration as route
from apps.live_control_server.services import threat_query_hydration as service
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
from graph_memory.projection.world_projection import WorldGraphProjection

TOKEN = "test-world-hydration-operator-token-1234"


def projection(scope="world", campaign="", revision="graph-a"):
    snapshot={"worldId":"native-world","campaignId":campaign,"revisionId":revision,"headRevisionId":revision,
              "isHead":True,"focus":{"kind":"none"},"admissibility":"gm","scopeMode":scope}
    return WorldGraphProjection.model_validate({"schema":"dmb_world_graph_projection_v1","snapshot":snapshot,
        "summary":{"nodeCount":1,"relationshipCount":0,"attributeCount":0,"evidenceCount":0,"sourceArtifactCount":0},
        "nodes":[{"nodeId":"npc:scout","label":"Scout","kind":"npc","role":"npc"}],
        "trustBoundary":{"canTrust":[],"cannotTrust":[]},
        "queryContext":{"snapshot":snapshot,"revisionId":revision,"queryText":"Scout","matchedNodeIds":["npc:scout"]}})


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE","local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT","development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",TOKEN)
    app=FastAPI();app.include_router(route.router)
    with TestClient(app,client=("127.0.0.1",50000),headers={"Authorization":f"Bearer {TOKEN}"}) as c:yield c


def request(**changes):
    return {"schema":"dmb_threat_query_hydration_request_v1","worldId":"native-world","campaignId":None,
            "scopeMode":"world","revisionPin":"graph-a","queryText":"Scout","focusNodeIds":["npc:scout"],**changes}


def test_world_null_scope_reaches_projection_and_returns_no_binding_honestly(client,monkeypatch):
    calls=[]
    def read(body,**kwargs):
        calls.append(body)
        assert body.world_id=="native-world" and body.campaign_id=="" and body.scope_mode=="world"
        assert body.revision_pin=="graph-a"
        return projection()
    monkeypatch.setattr(service,"project_world_graph",read)
    result=client.post('/api/live/threats/query-hydration',json=request())
    assert result.status_code==200,result.text
    body=result.json();assert body['campaignId'] is None and body['scopeMode']=='world'
    assert body['worldId']=='native-world' and body['revisionId']=='graph-a'
    assert body['hits'][0]['threat']['nodeId']=='npc:scout'
    assert body['hits'][0]['mechanicsDisposition']=='no_binding' and body['hits'][0]['bindings']==[]
    assert len(calls)==1


@pytest.mark.parametrize('scope,campaign', [('world','campaign-a'),('world',''),('campaign',None),('campaign','   ')])
def test_rejects_wrong_scope_campaign_before_native_read(client,monkeypatch,scope,campaign):
    monkeypatch.setattr(service,'project_world_graph',lambda *_a,**_kw:pytest.fail('invalid request reached native read'))
    assert client.post('/api/live/threats/query-hydration',json=request(scopeMode=scope,campaignId=campaign)).status_code==422


def test_campaign_scope_keeps_exact_nonblank_campaign(client,monkeypatch):
    monkeypatch.setattr(service,'project_world_graph',lambda body,**_kw:projection('campaign',body.campaign_id))
    result=client.post('/api/live/threats/query-hydration',json=request(scopeMode='campaign',campaignId='campaign-a'))
    assert result.status_code==200,result.text
    assert result.json()['campaignId']=='campaign-a'


@pytest.mark.parametrize('changes',[{'campaign':'foreign-campaign'},{'revision':'other-pin'},{'scope':'campaign'}])
def test_scope_echo_mismatch_never_grants_a_hit(client,monkeypatch,changes):
    monkeypatch.setattr(service,'project_world_graph',lambda *_a,**_kw:projection(**changes))
    result=client.post('/api/live/threats/query-hydration',json=request())
    assert result.status_code==500 and result.json()['diagnostics']==['projection_scope_mismatch']


def test_missing_revision_stays_not_found(client,monkeypatch):
    def read(*_a,**_kw):
        raise WorldGraphProjectionServiceError('Missing pinned revision',code='projection_revision_not_found',status_code=404)
    monkeypatch.setattr(service,'project_world_graph',read)
    result=client.post('/api/live/threats/query-hydration',json=request())
    assert result.status_code==404 and result.json()['resultLabel']=='threat_query_hydration_not_found'


@pytest.mark.parametrize('scope,campaign',[('world','campaign-a'),('campaign',None)])
def test_response_scope_cannot_assert_an_inconsistent_campaign(scope,campaign):
    from pydantic import ValidationError
    from apps.live_control_server.models.threat_query_hydration import ThreatQueryHydrationResponseV1
    with pytest.raises(ValidationError):
        ThreatQueryHydrationResponseV1(world_id='native-world',campaign_id=campaign,scope_mode=scope,
            revision_id='graph-a',query_text='Scout',result_label='threat_query_hydration_empty')
