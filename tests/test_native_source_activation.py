"""Ordinary Plan decisions → native appendix → actual captured writer; synthetic only."""
import asyncio
from hashlib import sha256
import json

import httpx2
import pytest

from application_state.agent_conversation import types as t
from application_state.source import service as sources
from apps.live_control_server.integrations.dungeonmind.source_origin import NativeSourceOrigin
from apps.live_control_server.services.native_source_navigation import NativeSourceNavigator
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
from application_state.agent_conversation.rules_authority_policy import rules_capability
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import fixture_reads
from tests.test_plan_jev_writer import WriterWire
from graph_memory.interaction.session import GraphReferent

TEXT = '# Synthetic adventure\r\nThe road.\r\n## Appendix A\r\nTree mechanics.\r\n'


def synthetic_access(owner,entry):
    """Stand in for separately tested real Core access; APP body storage is real."""
    turn = owner.adapter.fence.renewer._turn
    donor,pin,_ = entry
    authority = turn.graph_context_receipt.graph_authority
    digest = sha256(TEXT.encode()).hexdigest()
    scope = {'world_id':authority.native_world_id,'campaign_id':None,'admissibility':'gm',
        'scope_mode':'world_cross_campaign','focus':{'kind':'none','session_id':None}}
    identity = {'source_artifact_id':pin.source_artifact_id,'source_revision_id':pin.source_revision_id}
    anchor = ('dm-source-anchor:v1:'+pin.anchor_id[len('source-anchor:v1:'):]
        if pin.anchor_id.startswith('source-anchor:v1:') else pin.anchor_id)
    proof = {'schema':'dmb_native_source_origin_proof_v1','donor':donor.model_dump(mode='json'),
        'donor_sha256':t.canonical_sha256(donor.model_dump(mode='json')),'pin':pin.model_dump(mode='json'),
        'projection':scope|{'revision_pin':donor.graph_revision},
        'resolution':identity|{'evidence_ref_id':pin.evidence_ref_id,'anchor_id':anchor,'can_open_source':True,
            'snapshot':scope|{'revision_id':donor.graph_revision},
            'artifact':{'source_artifact_id':pin.source_artifact_id,'world_id':authority.native_world_id,
                'source_domain':'worldbuilding','status':'active','visibility':'gm',
                'lineage':{'source_name':'Synthetic adventure'}},
            'evidence':identity|{'evidence_ref_id':pin.evidence_ref_id,'source_domain':'worldbuilding'}},
        'revision':identity|{'content_sha256':digest}}
    return NativeSourceOrigin(donor.event_id,pin.source_artifact_id,pin.source_revision_id,digest,json.dumps(proof))


class SectionDecisions(httpx2.AsyncBaseTransport):
    def __init__(self):self.calls=[]
    async def handle_async_request(self,request):
        body=json.loads(request.content);phase=len(self.calls);self.calls.append(body)
        assert 'native-source:' not in request.content.decode() and 'native-section:' not in request.content.decode()
        candidates=body['state']['candidates'];answers={}
        for name,question in body['questions'].items():
            choice='finish_retrieval'
            if name!='operation':
                row=candidates[int(name.split('_')[-1])]
                include=(phase==0 and row['kind']=='World entity' and row['label']=='Park pond'
                    or phase==1 and row['kind'].startswith('Source navigation:')
                    or phase==2 and row['kind']=='Exact source section' and 'Appendix A' in row['label'])
                choice='include' if include else 'exclude'
            answers[name]={'type':'choice','choice':choice,'confidence':1.0,
                'probabilities':{key:float(key==choice) for key in question['criteria']}}
        return httpx2.Response(200,request=request,json={'model':'jev-1.14.0','answers':answers,
            'usage':{'input_tokens':30,'output_tokens':5}})


@pytest.mark.parametrize('overlap',[False,True])
@pytest.mark.parametrize('registered_build',[False,True])
def test_ordinary_plan_selects_appendix_and_persists_named_citation(plan_adapter,monkeypatch,overlap,registered_build):
    from application_state.agent_conversation import native_source_catalog
    sources.persist_source_markdown(source_artifact_id='artifact:park',source_domain='worldbuilding',
        world_id=plan_adapter.world_id,campaign_id=plan_adapter.world_id if registered_build else None,
        session_id=None,markdown=TEXT,lineage={'workspace_document_id':'synthetic-build','workspace_document_revision':2} if registered_build else {})
    def access(owner,entry):
        from dataclasses import replace
        origin=synthetic_access(owner,entry)
        if not registered_build:return origin
        proof=json.loads(origin.proof_json)
        proof['resolution']['artifact']['workspace_document_ref']={'document_id':'synthetic-build','revision':2}
        return replace(origin,proof_json=json.dumps(proof))
    monkeypatch.setattr(NativeSourceNavigator,'_access',access)
    counts=[];original=native_source_catalog.sources.get_source_markdown
    def body(*a,**kw):counts.append(1);return original(*a,**kw)
    monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',body)
    plan_adapter.bootstrap.retrieval_session.referents=[GraphReferent(id='pond',label='Park pond')]
    fixture_reads(plan_adapter,source_text='## Appendix A\r\nTree mechanics.\r\n' if overlap else None,source_lines=(3,4) if overlap else (1,1))
    rules=PlanRulesRuntime(plan_adapter,rules_capability(graph=True))
    driver=PlanJevDriver(plan_adapter)
    transport=SectionDecisions()
    proof=asyncio.run(driver.run(transport=transport,api_key='synthetic-not-secret'))
    assert len(transport.calls)==4 and len(counts)==1
    writer=PlanJevWriter(plan_adapter,proof,rules)
    assert len(writer.projection.frame['opened_passages']) == (0 if overlap else 1)
    assert len(writer.projection.source_event_ids) == (0 if overlap else 1)
    sections=writer.projection.frame['native_source_sections']['sections']
    assert len(sections)==1 and sections[0]['text']=='## Appendix A\r\nTree mechanics.\r\n'
    payload={'schema':'dmb_surface_evidence_answer_v3','limitations':[],'requested_detail_gaps':[],
        'answer_segments':[{'kind':'native_source_claim','text':'The appendix describes tree mechanics.',
            'section_handles':[sections[0]['section_handle']]}]}
    completed=asyncio.run(writer.run(transport=WriterWire(plan_adapter,json.dumps(payload)),api_key='synthetic-not-secret'))
    assert completed.status=='completed'
    assert completed.completion.native_source_citations[0].source_name=='Synthetic adventure'
    assert len(counts)==1


def test_registered_scope_predicate_does_not_relax_real_ownership():
    from application_state.agent_conversation.native_source_scope import source_scope_matches
    artifact={'source_domain':'worldbuilding','campaign_id':None,'session_id':None,
        'workspace_document_ref':{'document_id':'document','revision':2}}
    scope={'world_id':'managed','source_domain':'worldbuilding','campaign_id':'managed','session_id':None}
    assert source_scope_matches(scope,artifact,'managed')
    for changed in ({'world_id':'foreign'},{'campaign_id':'real-campaign'},{'session_id':'session'},
            {'source_domain':'session_recap'}):
        assert not source_scope_matches(scope|changed,artifact,'managed')
    for changed in ({'workspace_document_ref':None},{'workspace_document_ref':{}},
            {'campaign_id':'real-campaign'},{'session_id':'session'},{'source_domain':'session_recap'}):
        assert not source_scope_matches(scope,artifact|changed,'managed')
