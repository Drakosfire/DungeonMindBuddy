"""Parent navigator and real APP read ownership; synthetic source/access only."""
import json
from types import SimpleNamespace
from uuid import uuid4
from hashlib import sha256

import pytest
from application_state.agent_conversation import types as t
from application_state.source import service as sources
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.agent_turn_service import _ClaimFence
from apps.live_control_server.services.native_source_navigation import NativeSourceNavigator,NativeSourceUnavailable,BROWSE,READ
from apps.live_control_server.services.native_rules_capture import NativeToolReply
from tests.application_state.test_native_source_navigation_postgres import nav_case  # noqa:F401
from tests.test_native_source_activation import synthetic_access,TEXT
from tests.application_state.test_native_source_input_postgres import input_case,prepare,admit  # noqa:F401

_BOUND_AUTHORITY = NativeSourceNavigator._bound_authority
_ACCESS = NativeSourceNavigator._access


@pytest.fixture(autouse=True)
def synthetic_active_binding(monkeypatch):
    monkeypatch.setattr(NativeSourceNavigator, '_bound_authority',
        lambda self: self.adapter.fence.renewer._turn.graph_context_receipt.graph_authority)


@pytest.fixture
def parent(nav_case,monkeypatch):
    service,turn,_,pin=nav_case
    sources.persist_source_markdown(source_artifact_id=pin.source_artifact_id,source_domain='worldbuilding',
        world_id=turn.world_id,campaign_id=None,session_id=None,markdown=TEXT,lineage={})
    adapter=SimpleNamespace(service=service,fence=_ClaimFence(service,turn),turn=turn,context_capture=None)
    monkeypatch.setattr(NativeSourceNavigator,'_access',synthetic_access)
    owner=NativeSourceNavigator(adapter)
    yield owner,pin
    adapter.fence.renewer.stop_and_join()


def captured(owner,name,args,*,call_id='call-1'):
    provider=next(e for e in reversed(owner.adapter.fence.turn.graph_context_execution.events)
        if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
    owner.adapter.rules_runtime=SimpleNamespace(last_provider={'providerAttemptId':str(provider.provider_attempt_id)},
        last_reply=SimpleNamespace(request_sha256=provider.envelope_sha256,status='tool_calls',api_request_id=str(uuid4()),
            tool_calls=[NativeToolReply(call_id=call_id,name=name,arguments_json=json.dumps(args),arguments_sha256=sha256(json.dumps(args).encode()).hexdigest())]))
    owner.adapter.native_source_reply=owner.adapter.rules_runtime.last_reply
    owner.adapter.native_source_provider_id=provider.provider_attempt_id


def test_siblings_and_repeat_read_share_one_physical_body(parent,monkeypatch):
    owner,_=parent
    from application_state.agent_conversation import native_source_catalog
    counts=[];original=native_source_catalog.sources.get_source_markdown
    def body(*a,**kw):counts.append(1);return original(*a,**kw)
    monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',body)
    handle=owner.offered()[0].handle
    catalog=owner.browse(handle)
    handles=[r['section_handle'] for r in catalog['sections']]
    first=owner.read(handles)
    assert len(counts)==1 and len(first['sections'])==2 and not first['partial']
    repeated=owner.read(handles)
    assert not repeated['sections'] and len(repeated['reused_section_handles'])==2 and len(counts)==1
    assert len({r.read_id for r in owner.reads.values()})==2
    owner.browse(handle)
    assert len(counts)==1


def test_plan_selection_guard_precedes_body_read(parent,monkeypatch):
    owner,_=parent
    if owner.adapter.turn.provenance.surface_id!='plan':pytest.skip('Plan selection boundary')
    from application_state.agent_conversation import native_source_catalog
    monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',lambda *a,**kw:pytest.fail('unselected IO'))
    with pytest.raises(NativeSourceUnavailable,match='not_selected'):owner.browse(owner.offered()[0].handle,plan=True)


def test_lost_material_is_explicit_and_never_reloads_body(parent,monkeypatch):
    owner,_=parent
    from application_state.agent_conversation import native_source_catalog
    owner.browse(owner.offered()[0].handle)
    owner.materials.clear()
    monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',lambda *a,**kw:pytest.fail('cache loss reread'))
    result=owner.read([next(iter(owner.sections))])
    assert result['partial'] and not result['sections']
    assert owner.read([next(iter(owner.sections))])['partial']
    assert any(row.kind.startswith('Unavailable exact source section') for row in owner.examined())


def test_only_matching_current_captured_play_call_can_browse(parent,monkeypatch):
    owner,pin=parent
    from application_state.agent_conversation import native_source_catalog
    args={'anchor_id':pin.anchor_id};captured(owner,BROWSE,args)
    if owner.adapter.turn.provenance.surface_id=='plan':
        with pytest.raises(NativeSourceUnavailable):owner.tool(BROWSE,args,call_id='call-1')
        return
    reply=owner.adapter.rules_runtime.last_reply
    reply.request_sha256='f'*64
    with pytest.raises(NativeSourceUnavailable):owner.tool(BROWSE,args,call_id='call-1')
    provider=next(e for e in reversed(owner.adapter.fence.turn.graph_context_execution.events) if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
    reply.request_sha256=provider.envelope_sha256
    with pytest.raises(NativeSourceUnavailable):owner.tool(BROWSE,{'anchor_id':'foreign'},call_id='call-1')
    result=owner.tool(BROWSE,args,call_id='call-1')
    monkeypatch.setattr(native_source_catalog.sources,'get_source_markdown',lambda *a,**kw:pytest.fail('IPC retry IO'))
    assert owner.tool(BROWSE,args,call_id='call-1')==result
    selected={'section_handles':[result['sections'][-1]['section_handle']]}
    captured(owner,READ,selected,call_id='read-1')
    exact=owner.tool(READ,selected,call_id='read-1')
    assert exact['sections'][0]['text']=='## Appendix A\r\nTree mechanics.\r\n'
    captured(owner,READ,selected,call_id='read-2')
    repeated=owner.tool(READ,selected,call_id='read-2')
    assert not repeated['sections'] and len(repeated['reused_section_handles'])==1


@pytest.mark.parametrize('nav_case',['play'],indirect=True)
@pytest.mark.parametrize('forward',[False,True])
def test_current_play_input_reuses_only_previously_exposed_literal(input_case,forward):
    service,_,_=input_case
    turn,auth,raw,proof=prepare(input_case)
    body=json.loads(raw);literal=json.loads(body['messages'][-1]['content'])['sections'][0]
    first={'schema':'dmb_native_source_section_result_v1','sections':[literal],'reused_section_handles':[],'partial':False}
    repeat={'schema':'dmb_native_source_section_result_v1','sections':[],'reused_section_handles':[literal['section_handle']],'partial':False}
    body['messages'][-1]['content']=json.dumps(repeat if forward else first)
    body['messages'] += [{'role':'assistant','tool_calls':[{'id':'repeat','type':'function','function':{'name':READ,'arguments':'{}'}}]},
        {'role':'tool','tool_call_id':'repeat','content':json.dumps(first if forward else repeat)}]
    raw=json.dumps(body);auth=auth.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest()})
    if forward:
        with pytest.raises((ValueError,ApplicationStateValidationError)):
            admit(service,turn,auth,raw,proof)
    else:
        updated,fresh=admit(service,turn,auth,raw,proof)
        assert fresh and updated.graph_context_execution.events[-1].selected_chars==len(literal['text'])


def test_refused_section_is_not_reoffered_or_reauthorized(parent,monkeypatch):
    owner,_=parent
    owner.browse(owner.offered()[0].handle)
    handle=next(iter(owner.sections));calls=[];original=owner._commit
    def commit(method,**fields):
        if method=='authorize_native_source_section':
            calls.append(method);raise ApplicationStateValidationError('source read budget exhausted')
        return original(method,**fields)
    monkeypatch.setattr(owner,'_commit',commit)
    assert owner.read([handle])['partial']
    assert owner.read([handle])['partial']
    assert len(calls)==1 and handle not in {c.handle for c in owner.offered()}


def test_pdf_page_navigation_uses_query_term_matches_without_prose_preview():
    from apps.live_control_server.services.native_source_navigation import section_query_terms
    from application_state.agent_conversation.native_source_catalog import section_catalog
    text='# Source\n## PDF page 1\nTravel and villagers.\n## PDF page 16\nAppendix A: Grotesque Tree. Armor Class and Hit Points.\n'
    sections=section_catalog(text,source_artifact_id='synthetic',native_source_revision_id='revision',content_sha256=sha256(text.encode()).hexdigest())
    matches=section_query_terms(text,sections,'Find the Grotesque Tree armor class and hit points in Appendix A.')
    assert {'grotesque','tree','armor','class','hit','points','appendix'} <= set(matches[sections[-1].section_id])
    assert 'armor' not in matches[sections[1].section_id]
    assert all(' ' not in token for tokens in matches.values() for token in tokens)
    assert not {'the','and','in','a'} & {token for tokens in matches.values() for token in tokens}


@pytest.mark.parametrize('nav_case',['play'],indirect=True)
def test_rules_lookup_consumption_does_not_erase_sibling_source_capture(parent):
    owner,pin=parent;args={'anchor_id':pin.anchor_id};captured(owner,BROWSE,args)
    owner.adapter.rules_runtime.last_reply=None
    assert owner.tool(BROWSE,args,call_id='call-1')['schema']=='dmb_native_source_catalog_v1'


def test_graph_budget_retirement_preserves_independent_source_tools():
    from apps.live_control_server.services.hermes_graph_agent import _GraphOperationReservation
    owner=_GraphOperationReservation(0,lambda *a:None)
    tools=[{'function':{'name':name}} for name in ('expand_graph_retrieval',BROWSE,READ,'lookup_rules')]
    agent=SimpleNamespace(tools=tools);owner.agents=[agent]
    owner._retire_tools()
    assert {t['function']['name'] for t in agent.tools}=={BROWSE,READ,'lookup_rules'}
    owner.indeterminate=True;owner._retire_tools()
    assert [t['function']['name'] for t in agent.tools]==['lookup_rules']


@pytest.mark.parametrize('nav_case',['play'],indirect=True)
@pytest.mark.parametrize('duplicate_id',[False,True])
def test_same_arguments_match_exact_call_id_and_reads_remain_deduplicated(parent,duplicate_id):
    from dataclasses import replace
    owner,_=parent;owner.browse(owner.offered()[0].handle)
    args={'section_handles':[next(reversed(owner.sections))]};captured(owner,READ,args,call_id='read-1')
    reply=owner.adapter.native_source_reply;first=reply.tool_calls[0]
    reply.tool_calls.append(replace(first,call_id='read-1' if duplicate_id else 'read-2'))
    if duplicate_id:
        with pytest.raises(NativeSourceUnavailable):owner.tool(READ,args,call_id='read-1')
        assert not owner.reads
    else:
        literal=owner.tool(READ,args,call_id='read-1')
        repeat=owner.tool(READ,args,call_id='read-2')
        assert len(literal['sections'])==1 and not repeat['sections']
        assert repeat['reused_section_handles']==[literal['sections'][0]['section_handle']]
        assert len(owner.reads)==1


def test_native_progress_distinguishes_reads_from_available_sections(parent):
    owner,_=parent
    source_handle=owner.offered()[0].handle
    assert not owner.examined()
    owner.browse(source_handle)
    handles=list(owner.sections)
    assert len(handles)==2
    owner.read([handles[0]])
    outcomes={row.handle:row.kind for row in owner.examined()}
    assert outcomes[source_handle].startswith('Acquired source section catalog')
    assert outcomes[handles[0]].startswith('Acquired exact source section')
    assert handles[1] not in outcomes
    assert handles[1] in {row.handle for row in owner.offered()}
    assert handles[0] not in {row.handle for row in owner.offered()}


def test_navigation_omits_only_document_wide_terms_and_keeps_single_section_hints():
    from apps.live_control_server.services.native_source_navigation import section_query_terms
    from application_state.agent_conversation.native_source_catalog import section_catalog
    text='# Source\nshared\n## Rules\nshared armor\n## Tree\nshared tree armor\n'
    sections=section_catalog(text,source_artifact_id='synthetic',native_source_revision_id='revision',content_sha256=sha256(text.encode()).hexdigest())
    hints=section_query_terms(text,sections,'shared armor tree')
    assert all('shared' not in terms for terms in hints.values())
    assert hints[sections[-1].section_id]==['tree','armor']
    single='# Rules\nshared armor\n'
    sections=section_catalog(single,source_artifact_id='synthetic',native_source_revision_id='revision',content_sha256=sha256(single.encode()).hexdigest())
    assert set(section_query_terms(single,sections,'shared armor')[sections[0].section_id])=={'shared','armor'}


@pytest.mark.parametrize(('producer_key', 'native_key'), [('recap','recap'), ('recap','session_recap'), ('session_recap','session_recap'), ('dungeonbuddy.recap','dungeonbuddy.recap')])
@pytest.mark.parametrize('owner_world', ['managed', 'native'])
@pytest.mark.parametrize('named', [False, True])
def test_recap_catalog_read_and_citation_share_frozen_registered_name(nav_case, monkeypatch, named, owner_world, producer_key, native_key):  # noqa: F811
    from dataclasses import replace
    from application_state.agent_conversation.native_source_input import project_sections
    from application_state.agent_conversation.native_source_answer import NativeSectionSupport, citation
    service, turn, _, pin = nav_case
    sources.persist_source_markdown(source_artifact_id=pin.source_artifact_id, source_domain=producer_key,
        world_id=turn.world_id if owner_world == 'managed' else turn.graph_context_receipt.graph_authority.native_world_id, campaign_id='campaign:synthetic', session_id='session-29', markdown=TEXT, lineage={})
    adapter = SimpleNamespace(service=service, fence=_ClaimFence(service, turn), turn=turn, context_capture=None)
    owner = NativeSourceNavigator(adapter)
    def access(self, entry):
        origin = synthetic_access(self, entry)
        proof = json.loads(origin.proof_json)
        proof['resolution']['artifact'].update(source_domain_key=native_key, source_domain='session_recap', campaign_id='campaign:synthetic',
            session_id='session-29', lineage={'source_name':'Custom recap title'} if named else {})
        proof['resolution']['evidence']['source_domain'] = 'session_recap'
        return replace(origin, proof_json=json.dumps(proof))
    monkeypatch.setattr(NativeSourceNavigator, '_access', access)
    expected = 'Custom recap title' if named else 'Session 29 recap'
    try:
        handle = owner.offered()[0].handle
        catalog = owner.browse(handle)
        assert catalog['source_name'] == expected
        # Navigation labels never supply citation names; the frozen origin proof does.
        donor, source_pin, _ = owner.sources[handle]
        owner.sources[handle] = donor, source_pin, 'Misleading navigation label'
        result = owner.read([catalog['sections'][-1]['section_handle']])
        assert not result['partial'] and result['sections'][0]['source_name'] == expected
        execution = owner.adapter.fence.turn.graph_context_execution
        projected = project_sections(execution)
        assert projected['sections'][0] == result['sections'][0]
        read = next(iter(owner.reads.values()))
        support = NativeSectionSupport(projected['sections'][0]['section_handle'], read, projected['sections'][0]['source_name'])
        assert citation(support, index=0, text='Exact supported statement', producer=uuid4(), envelope_sha256='a'*64).source_name == expected
    finally:
        adapter.fence.renewer.stop_and_join()


def test_unnamed_nonrecap_catalog_refuses_before_body_io(parent, monkeypatch):
    from dataclasses import replace
    from application_state.agent_conversation import native_source_catalog
    owner, _ = parent
    def access(self, entry):
        origin = synthetic_access(self, entry)
        proof = json.loads(origin.proof_json)
        proof['resolution']['artifact']['lineage'] = {}
        return replace(origin, proof_json=json.dumps(proof))
    monkeypatch.setattr(NativeSourceNavigator, '_access', access)
    monkeypatch.setattr(native_source_catalog.sources, 'get_source_markdown',
        lambda *a, **kw: pytest.fail('Nameless navigation must not load source body'))
    with pytest.raises(NativeSourceUnavailable, match='source_navigation_unavailable'):
        owner.browse(owner.offered()[0].handle)
    assert not owner.catalogs and not owner.materials


@pytest.mark.parametrize('scope', ['missing', 'foreign', 'unowned'])
def test_unowned_catalog_is_not_offered_or_opened_and_metadata_is_reused(nav_case, monkeypatch, scope):  # noqa: F811
    service, turn, _, pin = nav_case
    if scope != 'missing':
        sources.persist_source_markdown(source_artifact_id=pin.source_artifact_id, source_domain='worldbuilding',
            world_id='other-world' if scope == 'foreign' else None, campaign_id=None,
            session_id=None, markdown=TEXT, lineage={})
    capture = SimpleNamespace(observations=[], observe=lambda row: capture.observations.append(row))
    adapter = SimpleNamespace(service=service, fence=_ClaimFence(service, turn), turn=turn, context_capture=capture)
    owner = NativeSourceNavigator(adapter)
    calls = []
    query = sources.owned_source_artifacts
    def metadata(**fields):
        calls.append(fields)
        return query(**fields)
    monkeypatch.setattr(sources, 'owned_source_artifacts', metadata)
    monkeypatch.setattr(owner, '_access', lambda *a: pytest.fail('Ineligible route must not call native origin'))
    try:
        assert not owner.offered()
        assert not owner.offered()
        assert len(calls) == 2
        assert calls[1] == dict(source_artifact_ids=[pin.source_artifact_id], world_id=turn.graph_context_receipt.graph_authority.native_world_id)
        assert calls[0] == dict(source_artifact_ids=[pin.source_artifact_id], world_id=turn.world_id)
        assert all(row.kind.startswith('Unavailable source section catalog') for row in owner.examined())
        # A metadata exclusion is not a failed selected body read.
        assert not capture.observations
        with pytest.raises(NativeSourceUnavailable):
            owner.browse(next(iter(owner.sources)))
        assert len(calls) == 2 and not owner.catalogs
        if turn.provenance.surface_id == 'play':
            args = {'anchor_id': pin.anchor_id}
            captured(owner, BROWSE, args)
            with pytest.raises(NativeSourceUnavailable):
                owner.tool(BROWSE, args, call_id='call-1')
            assert len(calls) == 2 and not owner.catalogs
    finally:
        adapter.fence.renewer.stop_and_join()


def test_positive_metadata_preflight_does_not_bypass_later_body_ownership(parent, monkeypatch):
    from application_state.source import repository
    owner, _ = parent
    handle = owner.offered()[0].handle
    assert handle not in owner.attempted_sources
    query = repository.get_source_artifact
    def changed(conn, identity, **kwargs):
        row = query(conn, identity, **kwargs)
        return row | {'world_id':'different-world'}
    monkeypatch.setattr(repository, 'get_source_artifact', changed)
    from application_state.agent_conversation import native_source_catalog
    monkeypatch.setattr(native_source_catalog.sources, 'get_source_markdown',
        lambda *a, **kw: pytest.fail('Ownership drift must refuse before body IO'))
    with pytest.raises(NativeSourceUnavailable):
        owner.browse(handle)
    assert owner.catalogs[handle].failure_code == 'source_scope_mismatch'
    assert not owner.sections


def test_negative_offer_cache_is_not_shared_with_a_new_navigation_owner(nav_case, monkeypatch):  # noqa: F811
    service, turn, _, pin = nav_case
    adapter = SimpleNamespace(service=service, fence=_ClaimFence(service, turn), turn=turn, context_capture=None)
    owner = NativeSourceNavigator(adapter)
    try:
        assert not owner.offered()
        sources.persist_source_markdown(source_artifact_id=pin.source_artifact_id, source_domain='worldbuilding',
            world_id=turn.world_id, campaign_id=None, session_id=None, markdown=TEXT, lineage={})
        assert not owner.offered()
        fresh = NativeSourceNavigator(adapter)
        assert len(fresh.offered()) == 1
    finally:
        adapter.fence.renewer.stop_and_join()


def test_newly_discovered_sources_share_one_metadata_batch(parent, monkeypatch):
    owner, _ = parent
    calls = []
    query = sources.owned_source_artifacts
    def metadata(**fields):
        calls.append(fields)
        return query(**fields)
    monkeypatch.setattr(sources, 'owned_source_artifacts', metadata)
    assert len(owner.offered()) == 1
    a = owner.adapter
    turn = a.fence.turn
    execution, receipt = turn.graph_context_execution, turn.graph_context_receipt
    prior = next(e for e in execution.events if isinstance(e, t.ValidatedGraphOperationEventV3))
    pins = [t.GraphSourceScopeAnchorV2(anchor_id=f'source-anchor:v1:new-{i}', evidence_ref_id=f'evidence:new-{i}',
        source_artifact_id=f'source:new-{i}', source_revision_id=f'native-revision:new-{i}') for i in range(2)]
    for pin in pins:
        sources.persist_source_markdown(source_artifact_id=pin.source_artifact_id, source_domain='worldbuilding',
            world_id=turn.world_id, campaign_id=None, session_id=None, markdown=TEXT, lineage={})
    donor = prior.model_copy(update={'event_id':uuid4(), 'sequence':len(execution.events), 'operation_id':uuid4(),
        'evidence_ref_ids':[pin.evidence_ref_id for pin in pins], 'returned_source_pins':pins})
    turn, _ = a.service.append_validated_graph_operation(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, operation_event=donor)
    execution = turn.graph_context_execution
    scope, authority = execution.policy.source_read_scope, receipt.graph_authority
    extension = t.SourceScopeExtensionEventV3(kind='source_scope_extension_v3', event_id=uuid4(),
        sequence=len(execution.events), origin_graph_event_id=donor.event_id,
        context_receipt_sha256=execution.context_receipt_sha256, execution_policy_sha256=execution.execution_policy_sha256,
        world_id=turn.world_id, native_world_id=authority.native_world_id, binding_version=authority.binding_version,
        campaign_id=None, graph_revision=scope.graph_revision, retrieval_session_id=scope.retrieval_session_id, pins=pins)
    turn, _ = a.service.extend_source_scope(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, extension=extension)
    a.fence.renewer._turn = turn
    a.turn = turn
    assert len(owner.offered()) == 3
    assert len(owner.offered()) == 3
    assert len(calls) == 4
    assert set(calls[2]['source_artifact_ids']) == {pin.source_artifact_id for pin in pins}


@pytest.mark.parametrize('drift', ['managed', 'native', 'version'])
def test_changed_active_binding_refuses_before_metadata_and_catalog_body(parent, monkeypatch, drift):
    from apps.live_control_server.services import native_source_navigation as runtime
    from application_state.agent_conversation import native_source_catalog
    owner, _ = parent
    authority = owner.adapter.fence.turn.graph_context_receipt.graph_authority
    binding = SimpleNamespace(managed_world_id=authority.managed_world_id,
        native_world_id=authority.native_world_id, binding_version=authority.binding_version)
    monkeypatch.setattr(NativeSourceNavigator, '_bound_authority', _BOUND_AUTHORITY)
    monkeypatch.setattr(NativeSourceNavigator, '_access', _ACCESS)
    monkeypatch.setattr(runtime, 'resolve_managed_world_binding', lambda world: binding)
    monkeypatch.setattr(runtime, 'direct_services_from_config', lambda world: None)
    monkeypatch.setattr(runtime, 'verify_native_source_origin',
        lambda services, **kw: synthetic_access(owner, (kw['donor'], kw['pin'], 'Synthetic adventure')))
    handle = owner.offered()[0].handle
    setattr(binding, {'managed':'managed_world_id','native':'native_world_id','version':'binding_version'}[drift],
        authority.binding_version + 1 if drift == 'version' else 'unrelated-world')
    monkeypatch.setattr(native_source_catalog.sources, 'get_source_markdown',
        lambda *a, **kw: pytest.fail('Stale active binding must refuse before source body IO'))
    with pytest.raises(NativeSourceUnavailable):
        owner.browse(handle)
    assert not owner.catalogs
    fresh = NativeSourceNavigator(owner.adapter)
    monkeypatch.setattr(sources, 'owned_source_artifacts',
        lambda **kw: pytest.fail('Stale binding must refuse even metadata preflight'))
    with pytest.raises(NativeSourceUnavailable):
        fresh.offered()


@pytest.mark.parametrize('changed', [dict(world_id='unrelated'), dict(source_domain='worldbuilding'),
    dict(campaign_id='other-campaign'), dict(session_id='session-other')])
def test_native_recap_scope_mismatch_refuses_before_body(nav_case, monkeypatch, changed):
    from dataclasses import replace
    from application_state.agent_conversation import native_source_catalog
    service, turn, _, pin = nav_case
    authority = turn.graph_context_receipt.graph_authority
    scope = dict(world_id=authority.native_world_id, source_domain='session_recap',
        campaign_id='campaign:synthetic', session_id='session-29') | changed
    sources.persist_source_markdown(source_artifact_id=pin.source_artifact_id, markdown=TEXT, lineage={}, **scope)
    adapter = SimpleNamespace(service=service, fence=_ClaimFence(service, turn), turn=turn, context_capture=None)
    owner = NativeSourceNavigator(adapter)
    def access(self, entry):
        origin = synthetic_access(self, entry)
        proof = json.loads(origin.proof_json)
        proof['resolution']['artifact'].update(source_domain='session_recap', source_domain_key='session_recap',
            campaign_id='campaign:synthetic', session_id='session-29')
        proof['resolution']['evidence']['source_domain'] = 'session_recap'
        return replace(origin, proof_json=json.dumps(proof))
    monkeypatch.setattr(NativeSourceNavigator, '_access', access)
    monkeypatch.setattr(native_source_catalog.sources, 'get_source_markdown',
        lambda *a, **kw: pytest.fail('Scope mismatch must refuse before body IO'))
    try:
        offered = owner.offered()
        if changed.get('world_id'):
            assert not offered
        else:
            with pytest.raises(NativeSourceUnavailable):
                owner.browse(offered[0].handle)
            assert owner.catalogs[offered[0].handle].failure_code == 'source_scope_mismatch'
    finally:
        adapter.fence.renewer.stop_and_join()


def test_binding_change_after_navigation_authorization_prevents_materialization(parent, monkeypatch):
    owner, _ = parent
    handle = owner.offered()[0].handle
    authority = owner.adapter.fence.turn.graph_context_receipt.graph_authority
    authorized = False
    original = owner._commit
    def commit(method, **fields):
        nonlocal authorized
        result = original(method, **fields)
        if method == 'authorize_native_source_navigation':
            authorized = True
        return result
    def binding():
        if authorized:
            raise NativeSourceUnavailable('source_navigation_unavailable')
        return authority
    monkeypatch.setattr(owner, '_commit', commit)
    monkeypatch.setattr(owner, '_bound_authority', binding)
    from application_state.agent_conversation import native_source_catalog
    monkeypatch.setattr(native_source_catalog.sources, 'get_source_markdown',
        lambda *a, **kw: pytest.fail('Binding drift after authorization must not load body'))
    with pytest.raises(NativeSourceUnavailable):
        owner.browse(handle)
    assert authorized and not owner.catalogs and not owner.materials
