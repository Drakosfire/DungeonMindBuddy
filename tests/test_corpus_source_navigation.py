"""Actual Plan decision/APP/writer/citation path; no Graph donor and no providers."""
import asyncio
import json
from types import SimpleNamespace
import httpx2
import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.source import service as sources
from application_state.agent_conversation.rules_authority_policy import rules_capability
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
from apps.live_control_server.services import corpus_source_navigation, agent_native_source_sections
from tests.test_plan_jev_dispatch import plan_adapter  # noqa:F401
from tests.test_plan_jev_writer import WriterWire
from tests.test_corpus_source_inventory import registry, TEXT


class Decisions(httpx2.AsyncBaseTransport):
    def __init__(self, after_search=None, decline=False):self.calls=[];self.after_search=after_search;self.decline=decline
    async def handle_async_request(self, request):
        body=json.loads(request.content); phase=len(self.calls); self.calls.append(body)
        if phase==1 and self.after_search is not None:self.after_search()
        assert 'A sleeping fox' not in request.content.decode()
        assert 'corpus-search:' not in request.content.decode() and 'native-section:' not in request.content.decode()
        answers={}
        for name, question in body['questions'].items():
            choice='finish_retrieval'
            if name!='operation':
                row=body['state']['candidates'][int(name.split('_')[-1])]
                include=not self.decline and (phase==0 and row['kind'].startswith('Corpus lexical navigation')
                    or phase==1 and row['kind']=='Exact source section' and 'Accounts' in row['label'])
                choice='include' if include else 'exclude'
            answers[name]={'type':'choice','choice':choice,'confidence':1.0,
                'probabilities':{key:float(key==choice) for key in question['criteria']}}
        return httpx2.Response(200,request=request,json={'model':'jev-1.14.0','answers':answers,
            'usage':{'input_tokens':30,'output_tokens':5}})


@pytest.fixture
def corpus(plan_adapter, monkeypatch):
    services, artifact, revision=registry()
    sources.persist_source_markdown(source_artifact_id=artifact.source_artifact_id,source_domain='worldbuilding',
        world_id='native-park',campaign_id=None,session_id=None,markdown=TEXT,lineage={})
    monkeypatch.setattr(corpus_source_navigation,'direct_services_from_config',lambda _:services)
    monkeypatch.setattr(agent_native_source_sections,'direct_services_from_config',lambda _:services)
    monkeypatch.setattr(agent_native_source_sections,'resolve_managed_world_binding',lambda _:SimpleNamespace(
        managed_world_id='world:one',native_world_id='native-park',binding_version=1))
    return plan_adapter, services


def test_zero_graph_source_reaches_real_writer_completion_and_reopen(corpus, monkeypatch):
    adapter, services=corpus
    driver=PlanJevDriver(adapter)
    wire=Decisions()
    proof=asyncio.run(driver.run(transport=wire,api_key='synthetic-not-secret'))
    assert len(wire.calls)==3
    events=adapter.fence.turn.graph_context_execution.events
    assert not any(isinstance(e,t.ValidatedGraphOperationEventV3) for e in events)
    assert not any(isinstance(e,t.SourceScopeExtensionEventV3) for e in events)
    result=next(e for e in events if isinstance(e,t.CorpusSourceSearchObservedV1))
    assert result.coverage=='enumerated_membership_scanned' and len(result.matches)==1
    assert not driver.native_sources.materials
    writer=PlanJevWriter(adapter,proof,PlanRulesRuntime(adapter,rules_capability(graph=True)))
    frame=writer.projection.frame
    assert frame['opened_passages']==[] and frame['retrieval_results']==[]
    sections=frame['native_source_sections']['sections']
    assert len(sections)==1 and sections[0]['text']=='## Accounts\r\nA sleeping fox lies beneath the black arch.\r\n'
    assert 'source_view_sha256' not in json.dumps(frame) and 'query_terms' not in json.dumps(frame)
    payload={'schema':'dmb_surface_evidence_answer_v4','limitations':[],'requested_detail_gaps':[],
        'answer_segments':[{'kind':'native_source_claim','text':'A sleeping fox lies beneath the black arch.',
            'section_handles':[sections[0]['section_handle']]}]}
    completed=asyncio.run(writer.run(transport=WriterWire(adapter,json.dumps(payload)),api_key='synthetic-not-secret'))
    assert completed.status=='completed'
    reloaded=AgentConversationService().inspect_turn(world_id=completed.world_id,turn_id=completed.turn_id)
    assert reloaded.completion==completed.completion
    section_reads=[e for e in reloaded.graph_context_execution.events if isinstance(e,t.NativeSourceSectionObservedV2)]
    assert len(section_reads)==1 and section_reads[0].fresh_body_read_bytes==len(TEXT.encode())
    reopened=agent_native_source_sections.open_native_source_section(world_id=completed.world_id,
        turn_id=completed.turn_id,citation_index=0)
    assert reopened.content==sections[0]['text']
    # A later source edition must not rebind or erase this historical citation.
    repo=services.bundle.sources
    old=repo.get_revision('orphan:r1')
    repo.put_revision(old.model_copy(update={'source_revision_id':'orphan:r2','content_sha256':'b'*64}))
    artifact=repo.get_artifact('artifact:orphan')
    repo._artifacts['artifact:orphan']=artifact.model_copy(update={'current_revision_id':'orphan:r2'})
    sources.persist_source_markdown(source_artifact_id='artifact:orphan',source_domain='worldbuilding',
        world_id='native-park',campaign_id=None,session_id=None,markdown='# New edition\nNo fox.\n',lineage={})
    again=agent_native_source_sections.open_native_source_section(world_id=completed.world_id,
        turn_id=completed.turn_id,citation_index=0)
    assert again.content==reopened.content
    repo._artifacts['artifact:orphan']=artifact.model_copy(update={'visibility':None})
    monkeypatch.setattr(agent_native_source_sections,'get_source_markdown',
        lambda **kw:pytest.fail('revoked citation reached bytes'))
    with pytest.raises(Exception,match='source_section_access_unavailable'):
        agent_native_source_sections.open_native_source_section(world_id=completed.world_id,
            turn_id=completed.turn_id,citation_index=0)


@pytest.mark.parametrize('change', ['retracted', 'unknown_visibility', 'foreign_world'])
def test_revoked_registry_access_never_reaches_selected_body(corpus, monkeypatch, change):
    from application_state.agent_conversation import native_source_catalog
    from dungeonmind.contracts.evidence import SourceStatus
    adapter, services=corpus
    repo=services.bundle.sources
    def revoke():
        artifact=repo.get_artifact('artifact:orphan')
        updates={'retracted':{'status':SourceStatus.RETRACTED},
            'unknown_visibility':{'visibility':None}, 'foreign_world':{'world_id':'foreign'}}[change]
        repo._artifacts[artifact.source_artifact_id]=artifact.model_copy(update=updates)
        monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',
            lambda *a,**kw:pytest.fail('revoked access reached APP bytes'))
    driver=PlanJevDriver(adapter)
    asyncio.run(driver.run(transport=Decisions(after_search=revoke),api_key='synthetic-not-secret'))
    assert not any(isinstance(e,t.NativeSourceSectionObservedV1) and e.outcome=='complete'
        for e in adapter.fence.turn.graph_context_execution.events)


@pytest.mark.parametrize('change', ['missing', 'hash', 'encoding', 'scope'])
def test_invalid_app_source_is_visible_partial_search_not_evidence(corpus, monkeypatch, change):
    from application_state.agent_conversation import native_source_catalog
    adapter,_=corpus
    original=native_source_catalog.sources.get_source_markdown
    if change=='scope':
        metadata=native_source_catalog.sources.get_source_artifact
        monkeypatch.setattr(native_source_catalog.sources,'get_source_artifact',
            lambda *a,**kw:metadata(*a,**kw)|{'world_id':'foreign'})
        monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',
            lambda *a,**kw:pytest.fail('foreign metadata reached body'))
    else:
        def invalid(*a,**kw):
            source=original(*a,**kw)
            if change=='missing':return None
            return source.model_copy(update={'markdown':'Unrelated tampered text'} if change=='hash' else {'encoding':'latin-1'})
        monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',invalid)
    driver=PlanJevDriver(adapter)
    asyncio.run(driver.run(transport=Decisions(),api_key='synthetic-not-secret'))
    results=[e for e in adapter.fence.turn.graph_context_execution.events if isinstance(e,t.CorpusSourceSearchObservedV1)]
    assert len(results)==1 and results[0].coverage=='partial' and not results[0].matches
    assert not driver.native_sources.sections
    assert not any(isinstance(e,t.NativeSourceSectionObservedV1) for e in adapter.fence.turn.graph_context_execution.events)


def test_unselected_or_repeated_search_never_dispatches_native_reads(corpus, monkeypatch):
    adapter,_=corpus
    driver=PlanJevDriver(adapter)
    asyncio.run(driver.run(transport=Decisions(),api_key='synthetic-not-secret'))
    monkeypatch.setattr(corpus_source_navigation,'collect_source_view',lambda *a,**kw:pytest.fail('repeated scan'))
    with pytest.raises(ValueError,match='not_selected'):driver.native_sources.corpus.search(plan=True)


@pytest.mark.parametrize('field', ['query_sha256', 'query_terms', 'attempt', 'native_world_id', 'binding_version', 'action_handle'])
def test_wrong_search_submission_cannot_be_appended(corpus, field):
    from uuid import uuid4
    adapter,_=corpus
    asyncio.run(PlanJevDriver(adapter).run(transport=Decisions(),api_key='synthetic-not-secret'))
    turn=adapter.fence.turn
    event=next(e for e in turn.graph_context_execution.events if isinstance(e,t.CorpusSourceSearchAuthorizedV1))
    value={'query_sha256':'f'*64,'query_terms':['forged'],'attempt':turn.attempt+1,
        'native_world_id':'foreign','binding_version':99,'action_handle':'forged'}[field]
    forged=event.model_copy(update={field:value,'event_id':uuid4(),'search_id':uuid4(),'sequence':len(turn.graph_context_execution.events)})
    with pytest.raises(ValueError):adapter.service.authorize_corpus_source_search(turn.world_id,
        turn.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,authorization=forged)
    assert adapter.service.inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id).revision==turn.revision


def test_corpus_tool_is_not_advertised_by_unbrokered_graph_policy():
    from graph_memory.hermes_graph_plugin import default_graph_only_capability_policy
    from graph_memory.hermes_graph_plugin import HermesGraphScope
    policy=default_graph_only_capability_policy(HermesGraphScope(world_id='world',campaign_id='',focus={'kind':'none'},admissibility='gm',revision_pin='rev',scope_mode='world'))
    assert 'search_retained_source_sections' not in policy.enabled_tool_names


def test_declined_corpus_offer_does_not_authorize_scan(corpus, monkeypatch):
    adapter,_=corpus
    driver=PlanJevDriver(adapter)
    asyncio.run(driver.run(transport=Decisions(decline=True),api_key='synthetic-not-secret'))
    monkeypatch.setattr(corpus_source_navigation,'collect_source_view',lambda *a,**kw:pytest.fail('unselected scan'))
    with pytest.raises(ValueError,match='not_selected'):driver.native_sources.corpus.search(plan=True)


def test_current_native_play_captured_search_reads_registry_section(application_state_dsn, monkeypatch):
    from uuid import uuid4
    from application_state.agent_conversation.play_graph_authority import play_graph_execution_policy_digest
    from application_state.agent_conversation.corpus_source_search import terms
    from tests.application_state.test_native_play_input_postgres import prepared_native, append
    from tests.test_native_source_navigation_runtime import captured
    from apps.live_control_server.services.agent_turn_service import _ClaimFence
    from apps.live_control_server.services import native_source_navigation
    original=AgentConversationService.accept_turn
    def accept(service, sub):
        execution=sub.graph_context_execution
        policy=t.PlayCorpusSourceSectionsPolicyV1.model_validate(execution.policy.model_dump(mode='json',by_alias=True)|{
            'native_source_section_policy':'exact_native_source_sections_v1','corpus_source_policy':'registered_corpus_sections_v1'})
        execution=t.PlayWorldGraphExecutionV1.model_validate(execution.model_dump(mode='json',by_alias=True)|{
            'policy':policy.model_dump(mode='json',by_alias=True),
            'execution_policy_sha256':play_graph_execution_policy_digest(execution.context_receipt_sha256,policy)})
        return original(service,sub.model_copy(update={'graph_context_execution':execution}))
    monkeypatch.setattr(AgentConversationService,'accept_turn',accept)
    service,sub,turn,provider,raw=prepared_native(application_state_dsn,moment=False)
    turn,_=append(service,sub,turn,provider,raw)
    for status in ('sdk_entered','response_received'):
        event=t.ProviderOutcomeEventV1(kind='provider_outcome',event_id=uuid4(),sequence=len(turn.graph_context_execution.events),
            provider_attempt_id=provider.provider_attempt_id,outcome=status)
        turn,_=service.record_provider_outcome(turn.world_id,turn.conversation_id,turn.turn_id,
            expected_revision=turn.revision,expected_attempt=turn.attempt,outcome=event)
    authority=turn.graph_context_receipt.graph_authority
    text='# Workshop\n## Selected account\n'+' '.join(terms(turn.user_text))+'.\n'
    services,artifact,_=registry(world=authority.native_world_id,text=text)
    sources.persist_source_markdown(source_artifact_id=artifact.source_artifact_id,source_domain='worldbuilding',
        world_id=authority.native_world_id,campaign_id=None,session_id=None,markdown=text,lineage={})
    monkeypatch.setattr(corpus_source_navigation,'direct_services_from_config',lambda _:services)
    monkeypatch.setattr(native_source_navigation,'resolve_managed_world_binding',lambda _:SimpleNamespace(
        managed_world_id=turn.world_id,native_world_id=authority.native_world_id,binding_version=authority.binding_version))
    adapter=SimpleNamespace(service=service,fence=_ClaimFence(service,turn),turn=turn,context_capture=None)
    owner=native_source_navigation.NativeSourceNavigator(adapter)
    try:
        captured(owner,native_source_navigation.SEARCH,{})
        result=owner.tool(native_source_navigation.SEARCH,{},call_id='call-1')
        assert result['coverage']=='enumerated_membership_scanned' and len(result['sections'])==1
        # A fresh Play worker receives the next captured call without a prior offer/collect.
        owner=native_source_navigation.NativeSourceNavigator(adapter)
        monkeypatch.setattr(corpus_source_navigation,'collect_source_view',lambda *a,**kw:pytest.fail('repeated query scanned native sources'))
        captured(owner,native_source_navigation.SEARCH,{},call_id='repeat-search')
        reused=owner.tool(native_source_navigation.SEARCH,{},call_id='repeat-search')
        assert reused['reused_search'] and not reused['sections']
        assert reused['reused_section_handles']==[result['sections'][0]['section_handle']]
        chosen={'section_handles':[result['sections'][0]['section_handle']]}
        captured(owner,native_source_navigation.READ,chosen,call_id='read')
        read=owner.tool(native_source_navigation.READ,chosen,call_id='read')
        assert read['sections'][0]['text']=='## Selected account\n'+' '.join(terms(turn.user_text))+'.\n'
        assert not any(isinstance(e,t.ValidatedGraphOperationEventV3) for e in adapter.fence.turn.graph_context_execution.events)
    finally:adapter.fence.renewer.stop_and_join()


def test_fresh_navigator_recovers_matched_section_without_rescanning(corpus, monkeypatch):
    from apps.live_control_server.services.native_source_navigation import NativeSourceNavigator
    adapter, _ = corpus
    driver = PlanJevDriver(adapter)
    def restart():
        monkeypatch.setattr(corpus_source_navigation, 'collect_source_view',
                            lambda *a, **kw: pytest.fail('recovery repeated native scan'))
        replacement = NativeSourceNavigator(adapter)
        adapter._native_source_navigator = replacement
        driver.native_sources = replacement
        replacement.collect()
        assert replacement.corpus.observation is not None
        assert len(replacement.sections) == 1
        assert not replacement.materials
    proof = asyncio.run(driver.run(transport=Decisions(after_search=restart), api_key='synthetic-not-secret'))
    execution = adapter.fence.turn.graph_context_execution
    assert len([e for e in execution.events if isinstance(e, t.CorpusSourceSearchAuthorizedV1)]) == 1
    reads = [e for e in execution.events if isinstance(e, t.NativeSourceSectionObservedV2)]
    assert len(reads) == 1 and reads[0].outcome == 'complete'
    assert reads[0].fresh_body_read_bytes == len(TEXT.encode())
    writer = PlanJevWriter(adapter, proof, PlanRulesRuntime(adapter, rules_capability(graph=True)))
    assert 'A sleeping fox' in writer.projection.frame['native_source_sections']['sections'][0]['text']
    again = NativeSourceNavigator(adapter)
    again.collect()
    assert again.reads and again.attempted_sections == set(again.reads)
    assert not again.offered()


@pytest.mark.parametrize('omit_navigation', [False, True])
def test_durable_search_match_must_belong_to_recorded_scan(corpus, omit_navigation):
    from application_state.agent_conversation.corpus_source_search import validate_events
    adapter, _ = corpus
    asyncio.run(PlanJevDriver(adapter).run(transport=Decisions(), api_key='synthetic-not-secret'))
    execution = adapter.fence.turn.graph_context_execution
    events = [e.model_copy(update={'catalog_event_ids': []})
              if isinstance(e, t.CorpusSourceSearchObservedV1) else e for e in execution.events
              if not (omit_navigation and isinstance(e, t.NativeSourceNavigationAuthorizedV2))]
    with pytest.raises(ValueError, match='omits an acquired|not navigation'):
        validate_events(SimpleNamespace(policy=execution.policy, events=events,
            context_receipt_sha256=execution.context_receipt_sha256,
            execution_policy_sha256=execution.execution_policy_sha256))


def test_registry_section_requires_earlier_exact_matched_result(corpus):
    from application_state.agent_conversation.native_source_sections import validate_section_events
    adapter, _ = corpus
    asyncio.run(PlanJevDriver(adapter).run(transport=Decisions(), api_key='synthetic-not-secret'))
    execution = adapter.fence.turn.graph_context_execution
    events = [e.model_copy(update={'matches': []})
              if isinstance(e, t.CorpusSourceSearchObservedV1) else e for e in execution.events]
    with pytest.raises(ValueError, match='not an earlier recorded corpus search match'):
        validate_section_events(SimpleNamespace(policy=execution.policy, events=events,
            context_receipt_sha256=execution.context_receipt_sha256,
            execution_policy_sha256=execution.execution_policy_sha256))


@pytest.mark.parametrize('recover', [False, True])
def test_unequal_term_frequencies_commit_canonical_matches_and_keep_rank(corpus, monkeypatch, recover):
    from apps.live_control_server.services.native_source_navigation import NativeSourceNavigator
    from application_state.agent_conversation.corpus_source_search import validate_events
    adapter, _ = corpus
    text = TEXT.replace('Unrelated blue flowers.', 'An unrelated arch.')
    services, artifact, _ = registry(text=text)
    sources.persist_source_markdown(source_artifact_id=artifact.source_artifact_id, source_domain='worldbuilding',
        world_id='native-park', campaign_id=None, session_id=None, markdown=text, lineage={})
    monkeypatch.setattr(corpus_source_navigation, 'direct_services_from_config', lambda _: services)
    driver = PlanJevDriver(adapter)
    original_search = driver.native_sources.corpus.search
    def observed_search(**kwargs):
        result = original_search(**kwargs)
        assert any(row['matched_query_terms'] == ['beneath', 'black', 'arch'] for row in result['sections'])
        return result
    monkeypatch.setattr(driver.native_sources.corpus, 'search', observed_search)
    def after_search():
        before = dict(driver.native_sources.query_matches)
        assert ['beneath', 'black', 'arch'] in before.values()
        if recover:
            monkeypatch.setattr(corpus_source_navigation, 'collect_source_view',
                                lambda *a, **kw: pytest.fail('recovery repeated scan'))
            replacement = NativeSourceNavigator(adapter)
            driver.native_sources = adapter._native_source_navigator = replacement
            replacement.collect()
            assert replacement.query_matches == before
    proof = asyncio.run(driver.run(transport=Decisions(after_search=after_search), api_key='synthetic-not-secret'))
    execution = adapter.fence.turn.graph_context_execution
    observed = next(e for e in execution.events if isinstance(e, t.CorpusSourceSearchObservedV1))
    assert observed.coverage == 'enumerated_membership_scanned'
    assert any(h.matched_terms == ['arch', 'beneath', 'black'] for h in observed.matches)
    assert all(h.matched_terms == sorted(set(h.matched_terms)) for h in observed.matches)
    writer = PlanJevWriter(adapter, proof, PlanRulesRuntime(adapter, rules_capability(graph=True)))
    selected = writer.projection.frame['native_source_sections']['sections']
    assert len(selected) == 1 and 'A sleeping fox' in selected[0]['text']
    assert any(isinstance(e, t.NativeSourceSectionObservedV2) and e.outcome == 'complete' for e in execution.events)
    forged = observed.model_copy(update={'matches': [h.model_copy(update={'matched_terms': list(reversed(h.matched_terms))})
        if len(h.matched_terms) > 1 else h for h in observed.matches]})
    fake = SimpleNamespace(policy=execution.policy,
        events=[forged if e.event_id == observed.event_id else e for e in execution.events],
        context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256)
    with pytest.raises(ValueError, match='not navigation'):
        validate_events(fake)
