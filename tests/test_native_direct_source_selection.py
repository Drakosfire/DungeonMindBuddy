"""Direct source choices reuse Core admission and native body writer/citation owners."""
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from dungeonmind.application.vnext import list_admitted_native_text_sources
from apps.live_control_server.integrations.dungeonmind import native_corpus_source as core
from application_state.agent_conversation.native_corpus import (
    NativeDirectSourceAuthorizedV1, NativeDirectSourceObservedV1,
    NativeBodySearchAuthorizedV1, acquired_body_catalogs,
    validate_native_body_events, native_direct_source_handle,
)
from tests.test_native_corpus_source_access import lane as lane, admit, GM, BODY


def prepared(lane):
    return core.prepare_native_source_context(managed_world_id=lane.bound.managed_world_id,
        principal=GM, repository=lane.repo, resolve_identity=lambda _: lane.bound)


def target(context):
    item = list_admitted_native_text_sources(context.access).sources[0]
    return dict(source_artifact_id=item.source_artifact.source_artifact_id,
        source_revision_id=item.source_revision.source_revision_id,
        content_sha256=item.source_revision.content_sha256)


def test_metadata_does_not_open_bodies_and_direct_read_refreshes_exact_source(lane, monkeypatch):
    admit(lane)
    context = prepared(lane)
    selection = target(context)
    admit(lane, 'later', body='# Elsewhere\nNot the requested source.\n')
    opened = []
    actual = core.open_admitted_native_text
    def read(access, evidence):
        opened.append((access.source_view.epoch, evidence))
        return actual(access, evidence)
    monkeypatch.setattr(core, 'open_admitted_native_text', read)
    assert target(context) == selection and not opened
    catalog, excerpt = core.read_direct_native_source(context, authority=context.authority, **selection)
    assert excerpt.text == BODY and len(opened) == 1
    assert catalog.authority.acquisition_epoch > context.authority.acquisition_epoch
    assert catalog.authority.revision_id == context.authority.revision_id
    assert catalog.source.campaign_scope == catalog.source.session_scope == 'unestablished'


@pytest.mark.parametrize('changed', [dict(source_artifact_id='foreign'),
    dict(source_revision_id='foreign'), dict(content_sha256='0'*64)])
def test_unadmitted_or_changed_source_refuses_before_body_read(lane, monkeypatch, changed):
    admit(lane)
    context = prepared(lane)
    selection = target(context) | changed
    monkeypatch.setattr(core, 'open_admitted_native_text', lambda *_: pytest.fail('unadmitted body read'))
    with pytest.raises(ValueError, match='original admitted catalogue'):
        core.read_direct_native_source(context, authority=context.authority, **selection)


def test_changed_world_binding_refuses_before_body_read(lane, monkeypatch):
    admit(lane)
    context = prepared(lane)
    selection = target(context)
    lane.bound = SimpleNamespace(**(vars(lane.bound) | {'binding_version':2}))
    monkeypatch.setattr(core, 'open_admitted_native_text', lambda *_: pytest.fail('foreign binding body read'))
    with pytest.raises(ValueError, match='authority changed'):
        core.read_direct_native_source(context, authority=context.authority, **selection)


def direct_case(surface, lane, *, advance=False):
    from tests.test_surface_native_writer import body_case
    from tests.test_surface_native_execution import execution
    context, record, read = body_case(surface, lane, full=True)
    search_index = next(i for i,e in enumerate(record.events) if isinstance(e, NativeBodySearchAuthorizedV1))
    catalog = acquired_body_catalogs(record)[read.excerpt.catalog_sha256]
    handle = native_direct_source_handle(context.source_authority, catalog.source.artifact.source_artifact_id,
        catalog.source.revision.source_revision_id, catalog.source.revision.content_sha256)
    events = list(record.events[:search_index])
    events[-1] = events[-1].model_copy(update={'selected_handles':(handle,)})
    grant = NativeDirectSourceAuthorizedV1(event_id=uuid4(), sequence=len(events),
        provider_attempt_id=events[-1].controller_attempt_id, authority=context.source_authority,
        source_artifact_id=catalog.source.artifact.source_artifact_id,
        source_revision_id=catalog.source.revision.source_revision_id, content_sha256=catalog.source.revision.content_sha256)
    events.append(grant)
    excerpt = read.excerpt
    if advance:
        source_context=prepared(lane)
        admit(lane,'later-epoch',body='# Later source\nUnrelated.\n')
        catalog,excerpt=core.read_direct_native_source(source_context,authority=context.source_authority,
            source_artifact_id=grant.source_artifact_id,source_revision_id=grant.source_revision_id,
            content_sha256=grant.content_sha256)
        assert catalog.authority.acquisition_epoch > grant.authority.acquisition_epoch
    observed = NativeDirectSourceObservedV1(event_id=uuid4(), sequence=len(events),
        authorization_event_id=grant.event_id, catalog=catalog, excerpt=excerpt, failure_code=None)
    events.append(observed)
    # Reuse the existing acknowledged finish and Build work-selection fixtures.
    tail = record.events[read.sequence+1:]
    offset = len(events)
    events.extend(e.model_copy(update={'sequence':offset+i}) for i,e in enumerate(tail))
    return context, execution(context.context_receipt_sha256, record.policy, events), grant, observed


@pytest.mark.parametrize('surface',['build','plan'])
@pytest.mark.parametrize('advance',[False,True])
def test_actual_sdk_shared_input_closes_direct_source_and_existing_citations(lane,surface,advance):
    from tests.test_surface_native_writer import work_submission, actual_sdk_request, authorize
    from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
    context, record, grant, observed = direct_case(surface,lane,advance=advance)
    frame = model_frame(context,record)
    work = work_submission(context,record)
    raw = asyncio.run(actual_sdk_request(frame,work_frame=model_work_frame(context,record,**work)))
    stored, auth = authorize(context,record,raw,frame)
    supports = verify_input_records(context,stored,auth,raw,**work)
    assert len(supports.body_excerpts)==1
    assert supports.body_excerpts[0].read == observed
    assert auth.native_read_event_ids == (observed.event_id,)
    assert not any(isinstance(e,NativeBodySearchAuthorizedV1) for e in stored.events)
    assert type(stored).model_validate_json(stored.model_dump_json(by_alias=True)) == stored


@pytest.mark.parametrize('surface',['build','plan'])
def test_direct_grants_close_pending_reads_and_reject_changed_selection(lane,surface):
    _, execution, grant, observed = direct_case(surface,lane)
    validate_native_body_events(execution)
    with pytest.raises(ValueError, match='unresolved native body read'):
        validate_native_body_events(execution.model_copy(update={'events':[
            e for e in execution.events if e.event_id != observed.event_id]}))
    changed = grant.model_copy(update={'content_sha256':'0'*64})
    with pytest.raises(ValueError, match='controller selection'):
        validate_native_body_events(execution.model_copy(update={'events':[
            changed if e.event_id == grant.event_id else e for e in execution.events]}))
    wrong = observed.model_copy(update={'authorization_event_id':uuid4()})
    with pytest.raises(ValueError, match='current unique authorization'):
        validate_native_body_events(execution.model_copy(update={'events':[
            wrong if e.event_id == observed.event_id else e for e in execution.events]}))


@pytest.fixture
def publication_lane(application_state_dsn,tmp_path,monkeypatch):
    from tests.test_source_statements import make_lane
    return make_lane(tmp_path,monkeypatch,narrow=True)


@pytest.mark.parametrize('judgment',['direct_support','qualification_or_conflict','uncertain','irrelevant'])
def test_ordinary_build_direct_source_selection_delivers_and_reopens(publication_lane,tmp_path,monkeypatch,judgment):
    # This fixture uses the ordinary authenticated HTTP/default factory and real
    # APP persistence. It has its own published assertion/source fixture owner.
    from tests.test_surface_native_build_ordinary import _fresh_case
    monkeypatch.setattr(core,'capture_native_sources',lambda **_:pytest.fail('Direct lookup scanned the corpus'))
    case = _fresh_case(publication_lane,tmp_path,monkeypatch,None,False,False,False,
        native_body=judgment,direct_source=True)
    events = case.turn.graph_context_execution.events
    assert any(isinstance(e,NativeDirectSourceObservedV1) for e in events)
    assert not any(isinstance(e,NativeBodySearchAuthorizedV1) for e in events)
    citations=case.turn.completion.native_body_citations
    assert bool(citations) == (judgment != 'irrelevant')
    for index,citation in enumerate(citations):
        opened=case.client.get(f'/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/native-body-excerpts/{index}')
        assert opened.status_code==200 and opened.json()['content']


@pytest.mark.parametrize('outcome',['unavailable','integrity','binding'])
def test_direct_read_preserves_core_failures_and_rechecks_binding_after_io(lane,monkeypatch,outcome):
    from dungeonmind.application.vnext.errors import NativeTextSourceAccessIntegrityError
    admit(lane)
    context=prepared(lane)
    selection=target(context)
    actual=core.open_admitted_native_text
    def read(access, evidence):
        if outcome=='unavailable':
            return SimpleNamespace(status='unavailable')
        if outcome=='integrity':
            raise NativeTextSourceAccessIntegrityError('synthetic integrity failure')
        result=actual(access,evidence)
        lane.bound=SimpleNamespace(**(vars(lane.bound)|{'binding_version':2}))
        return result
    monkeypatch.setattr(core,'open_admitted_native_text',read)
    if outcome=='unavailable':
        assert core.read_direct_native_source(context,authority=context.authority,**selection) is None
    else:
        with pytest.raises(NativeTextSourceAccessIntegrityError if outcome=='integrity' else ValueError):
            core.read_direct_native_source(context,authority=context.authority,**selection)


def test_direct_source_catalogue_is_available_after_scan_without_duplicate_full_document_actions(lane):
    from tests.test_native_reference_navigation import navigation
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
    nav,catalog,_=navigation(lane)
    # Exercise the shared owner gate using its real source authority and native
    # event inventory; only presentation is inspected, no fake body grant occurs.
    from tests.test_surface_native_execution import component
    context,_=component('plan',unavailable=True)
    nav.adapter.fence.turn.graph_context_receipt=context.model_copy(update={
        'source_authority':nav.adapter.native_corpus_context.authority})
    assert type(nav.adapter.fence.turn.graph_context_receipt) is SurfaceNativeContextReceiptV1
    offered=nav.offered()
    assert any(c.kind=='Explicit admitted full-source read; metadata choice, not evidence' for c in offered)
    assert not any(c.kind=='Explicit full-document read' for c in offered)
    assert any(c.kind=='Exact source section' for c in offered)


def test_ordinary_mixed_direct_and_search_selection_settles_without_duplicate_read(publication_lane,tmp_path,monkeypatch):
    from tests.test_surface_native_build_ordinary import _fresh_case
    from application_state.agent_conversation.native_corpus import acquired_body_reads
    case=_fresh_case(publication_lane,tmp_path,monkeypatch,None,False,False,False,
        native_body='direct_support',direct_source='mixed')
    execution=case.turn.graph_context_execution
    reads=acquired_body_reads(execution)
    assert any(isinstance(e,NativeBodySearchAuthorizedV1) for e in execution.events)
    assert reads and all(isinstance(e,NativeDirectSourceObservedV1) for e in reads)
    pairs=[(r.catalog.source.artifact.source_artifact_id,r.catalog.source.revision.source_revision_id) for r in reads]
    assert len(pairs)==len(set(pairs))
    assert case.turn.status=='completed'


def test_ordinary_batch_full_read_fulfills_selected_sections_without_false_failure(publication_lane,tmp_path,monkeypatch):
    from tests.test_surface_native_build_ordinary import _fresh_case
    from application_state.agent_conversation.native_corpus import acquired_body_reads
    case = _fresh_case(publication_lane,tmp_path,monkeypatch,None,False,False,False,
        native_body='direct_support',direct_source='covered-batch')
    execution = case.turn.graph_context_execution
    selections = [e for e in execution.events if e.kind == 'native_retrieval_selected_v1']
    assert any(any(h.startswith('native-direct-source:') for h in s.selected_handles)
        and any(h.startswith('native-body:') for h in s.selected_handles) for s in selections)
    reads = acquired_body_reads(execution)
    assert reads and all(isinstance(e,NativeDirectSourceObservedV1) for e in reads)
    trace, = case.service.list_context_trace_attempts(world_id=case.world,turn_id=case.turn.turn_id)
    assert not any(e.kind == 'failure' for e in trace.observations)
    assert case.turn.status == 'completed' and case.turn.completion.native_body_citations
    # Reconstruct the actual running prefix after this batch and before the next
    # controller, without changing stored test records or admitting new evidence.
    from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
    from application_state.agent_conversation import types as t
    batch = next(s for s in selections if any(h.startswith('native-body:') for h in s.selected_handles))
    stop = next(e.sequence for e in execution.events if e.sequence > batch.sequence
        and isinstance(e,t.ProviderAttemptAuthorizedEventV1))
    prefix = execution.model_copy(update={'events':execution.events[:stop]})
    turn = case.turn.model_copy(update={'status':'running','graph_context_execution':prefix})
    nav = NativeBodyNavigation(SimpleNamespace(fence=SimpleNamespace(turn=turn),
        native_corpus_context=case.writer.adapter.native_corpus_context))
    handle = next(h for h in batch.selected_handles if h.startswith('native-body:'))
    assert nav._fulfilled_in_current_selection(handle)
    assert nav.select([handle])['body_text_exposed'] is False
    acquired = nav._acquired_extents()
    # No completed read, a read from an earlier decision, or an incomplete
    # interval cannot replace this section's acknowledged acquisition.
    for replacement in ((), tuple((read.model_copy(update={'sequence':batch.sequence-1}),catalog)
            for read,catalog in acquired), tuple((read.model_copy(update={'excerpt':read.excerpt.model_copy(update={
                'section':read.excerpt.section.model_copy(update={'byte_end':0})})}),catalog)
            for read,catalog in acquired)):
        with monkeypatch.context() as patch:
            patch.setattr(nav,'_acquired_extents',lambda:replacement)
            assert not nav._fulfilled_in_current_selection(handle)
    # Identical bytes in a distinct source, revision or digest are not fulfillment.
    for field in ('source_artifact_id','source_revision_id','content_sha256'):
        altered=[]
        for read,catalog in acquired:
            source=catalog.source
            key='artifact_json' if field=='source_artifact_id' else 'revision_json'
            import json
            value=json.loads(getattr(source,key))
            value[field]='0'*64 if field=='content_sha256' else 'foreign'
            altered.append((read,catalog.model_copy(update={'source':source.model_copy(update={key:json.dumps(value)})})))
        with monkeypatch.context() as patch:
            patch.setattr(nav,'_acquired_extents',lambda:tuple(altered))
            assert not nav._fulfilled_in_current_selection(handle)
    with monkeypatch.context() as patch:
        unselected=batch.model_copy(update={'selected_handles':tuple(h for h in batch.selected_handles if h!=handle)})
        patch.setattr('application_state.agent_conversation.plan_jev_decision.current_selection',lambda _:unselected)
        assert not nav._fulfilled_in_current_selection(handle)
