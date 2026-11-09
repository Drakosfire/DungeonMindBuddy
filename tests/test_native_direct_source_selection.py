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


def direct_grant_case(dsn, *, second_selection=False, boundary=False, count=3):
    """Actual SDK selection; metadata grants do not claim that fake sources were read."""
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
    from tests.application_state.test_surface_native_decisions import sdk_case

    def candidates(case):
        authority = case.turn.graph_context_receipt.source_authority
        if not hasattr(case, 'grants'):
            case.grants = tuple(dict(event_id=uuid4(), source_artifact_id=f'artifact:{i}',
                source_revision_id=f'revision:{i}', content_sha256=f'{i:064x}') for i in range(count))
        rows = tuple(RetrievalCandidate(handle=native_direct_source_handle(authority,
            row['source_artifact_id'], row['source_revision_id'], row['content_sha256']),
            label=f'Source {i}', kind='Explicit admitted full-source read; metadata choice, not evidence')
            for i, row in enumerate(case.grants))
        if boundary:
            from hashlib import sha256
            from application_state.agent_conversation.native_corpus import native_corpus_search_handle
            search = RetrievalCandidate(handle=native_corpus_search_handle(sha256(case.turn.user_text.encode()).hexdigest()),
                label='Search source sections', kind='Source lexical navigation; not evidence or semantic completeness')
            return (rows[0], search, *rows[1:])
        return rows

    def settle(case):
        case.turn, _ = commit_grants(case)
        for row in case.grants:
            case.turn, _ = case.service.observe_native_direct_source(case.turn.world_id,
                case.turn.conversation_id, case.turn.turn_id,
                expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
                event_id=uuid4(), authorization_event_id=row['event_id'], read=lambda _: None)
    acquisitions = ((candidates, settle), (candidates, lambda _: None)) if second_selection else ((candidates, lambda _: None),)
    return sdk_case(dsn, native=True, acquisitions=acquisitions, include_final_decision=False)


def grant_snapshot(case):
    import psycopg
    with psycopg.connect(case.dsn) as conn:
        return conn.execute('SELECT revision,graph_context_execution FROM agent.turn WHERE turn_id=%s',
            (case.turn.turn_id,)).fetchone()


def commit_grants(case, grants=None, **overrides):
    return case.service.authorize_native_direct_sources(case.turn.world_id,
        case.turn.conversation_id, case.turn.turn_id,
        **(dict(expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            grants=case.grants if grants is None else grants) | overrides))


def test_direct_grants_commit_together_and_complete_replay_does_not_advance(application_state_dsn):
    case = direct_grant_case(application_state_dsn)
    before = case.turn
    case.turn, fresh = commit_grants(case)
    assert fresh and case.turn.revision == before.revision + 1
    appended = case.turn.graph_context_execution.events[len(before.graph_context_execution.events):]
    assert len(appended) == 3 and all(type(e) is NativeDirectSourceAuthorizedV1 for e in appended)
    assert [e.event_id for e in appended] == [row['event_id'] for row in case.grants]
    assert [e.sequence for e in appended] == list(range(appended[0].sequence, appended[0].sequence + 3))
    checkpoint = grant_snapshot(case)
    replay, fresh = commit_grants(case)
    assert not fresh and replay == case.turn and grant_snapshot(case) == checkpoint


@pytest.mark.parametrize('count', [1, 2, 9, 10])
def test_group_sizes_keep_individual_unavailable_observations(application_state_dsn, count):
    case = direct_grant_case(application_state_dsn, count=count)
    before = case.turn
    case.turn, fresh = commit_grants(case)
    assert fresh and case.turn.revision == before.revision + 1
    for row in case.grants:
        case.turn, fresh = case.service.observe_native_direct_source(case.turn.world_id,
            case.turn.conversation_id, case.turn.turn_id,
            expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            event_id=uuid4(), authorization_event_id=row['event_id'], read=lambda _: None)
        assert fresh
    # Grant batching removes only grant commits: every unavailable read still
    # has its own durable observation, without inventing text or recovery.
    assert case.turn.revision == before.revision + count + 1
    added = case.turn.graph_context_execution.events[len(before.graph_context_execution.events):]
    grants = [e for e in added if type(e) is NativeDirectSourceAuthorizedV1]
    observed = [e for e in added if type(e) is NativeDirectSourceObservedV1]
    assert len(grants) == len(observed) == count
    assert [e.authorization_event_id for e in observed] == [e.event_id for e in grants]
    assert all(e.catalog is None and e.failure_code for e in observed)


@pytest.mark.parametrize('mutation', ['duplicate_id', 'duplicate_source', 'foreign', 'reordered', 'partial_replay', 'stale'])
def test_direct_grant_batch_rejects_atomically(application_state_dsn, mutation):
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    case = direct_grant_case(application_state_dsn)
    if mutation == 'partial_replay':
        case.turn, fresh = commit_grants(case, case.grants[:1])
        assert fresh
    grants = [dict(row) for row in case.grants]
    extra = {}
    if mutation == 'duplicate_id':
        grants[1]['event_id'] = grants[0]['event_id']
    elif mutation == 'duplicate_source':
        grants[1] = dict(grants[0], event_id=grants[1]['event_id'])
    elif mutation == 'foreign':
        grants[-1]['source_artifact_id'] = 'artifact:foreign'
    elif mutation == 'reordered':
        grants.reverse()
    elif mutation == 'stale':
        extra['expected_revision'] = case.turn.revision - 1
    before = grant_snapshot(case)
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        commit_grants(case, tuple(grants), **extra)
    assert grant_snapshot(case) == before


def test_direct_grant_batch_rolls_back_if_durable_return_fails(application_state_dsn, monkeypatch):
    from application_state.agent_conversation import repository as repo
    from application_state.errors import ApplicationStateIntegrityError
    case = direct_grant_case(application_state_dsn)
    before = grant_snapshot(case)
    original = repo.update_graph_execution
    attempted = []

    def rejected_return(*args, **kwargs):
        result = original(*args, **kwargs)
        assert result is not None
        attempted.append(True)
        raise ApplicationStateIntegrityError('Injected durable return rejection')

    monkeypatch.setattr(repo, 'update_graph_execution', rejected_return)
    with pytest.raises(ApplicationStateIntegrityError, match='durable return rejection'):
        commit_grants(case)
    assert attempted and grant_snapshot(case) == before


@pytest.mark.parametrize('mutation', ['changed_content', 'another_controller', 'stale_attempt', 'expired'])
def test_direct_grant_replay_and_claim_fences(application_state_dsn, mutation):
    import psycopg
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    case = direct_grant_case(application_state_dsn, second_selection=mutation == 'another_controller')
    if mutation == 'changed_content':
        case.turn, _ = commit_grants(case)
    grants = tuple(dict(row) for row in case.grants)
    extra = {}
    if mutation == 'changed_content':
        grants[-1]['content_sha256'] = 'f' * 64
    elif mutation == 'stale_attempt':
        extra['expected_attempt'] = case.turn.attempt + 1
    elif mutation == 'expired':
        with psycopg.connect(case.dsn) as conn:
            conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (case.turn.turn_id,))
    before = grant_snapshot(case)
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        commit_grants(case, grants, **extra)
    assert grant_snapshot(case) == before


@pytest.mark.parametrize('mutation', ['empty', 'list', 'mixed', 'duplicate'])
def test_native_batch_materializer_has_closed_event_family(application_state_dsn, mutation, monkeypatch):
    from application_state.agent_conversation import native_reads
    from application_state.agent_conversation.native_reads import authorize_direct_sources_locked
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    case = direct_grant_case(application_state_dsn)
    before = grant_snapshot(case)

    def produce(turn, *, grants):
        grants = authorize_direct_sources_locked(turn, grants=grants)
        if mutation == 'empty': return ()
        if mutation == 'list': return list(grants)
        if mutation == 'mixed': return (grants[0], turn.graph_context_execution.events[0])
        return (grants[0], grants[0].model_copy(update={'sequence': grants[0].sequence + 1}))

    monkeypatch.setattr(native_reads, 'authorize_direct_sources_locked', produce)
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        case.service.authorize_native_direct_sources(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            grants=case.grants)
    assert grant_snapshot(case) == before


def test_native_read_operation_rejects_generic_callback():
    from application_state.agent_conversation.native_reads import _NativeReadOperation
    with pytest.raises(ValueError, match='existing closed producer'):
        _NativeReadOperation(lambda turn: pytest.fail('Generic producer ran'), {})


def test_direct_source_callback_cannot_mutate_retained_grant(application_state_dsn):
    case = direct_grant_case(application_state_dsn, count=1)
    case.turn, _ = commit_grants(case)
    grant = case.grants[0]
    def unavailable(authority):
        # Check alias isolation independently of the model's frozen attribute
        # guard: a retained Python reference still has mutable model storage.
        authority.__dict__['source_revision_id'] = 'changed callback argument'
        return None
    updated, fresh = case.service.observe_native_direct_source(
        case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
        expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
        event_id=uuid4(), authorization_event_id=grant['event_id'], read=unavailable)
    assert fresh
    retained = next(e for e in updated.graph_context_execution.events if e.event_id == grant['event_id'])
    assert retained.source_revision_id == grant['source_revision_id']
    assert updated.graph_context_execution.events[-1].failure_code == 'native_body_unavailable'


def test_ordinary_multiple_direct_sources_are_granted_before_each_read(publication_lane, tmp_path, monkeypatch):
    from tests.test_surface_native_build_ordinary import _fresh_case
    from application_state.agent_conversation.plan_jev_decision import current_selection
    from application_state.agent_conversation import AgentConversationService
    adapters, calls, reads = [], [], []
    original_grant = AgentConversationService.authorize_native_direct_sources
    original_read = core.read_direct_native_source

    def grant(service, *args, **kwargs):
        result = original_grant(service, *args, **kwargs)
        calls.append(len(kwargs['grants']))
        return result

    def read(context, **kwargs):
        a = adapters[-1]
        turn = a.service.inspect_turn(world_id=a.world_id, turn_id=a.fence.renewer._turn.turn_id)
        selected = current_selection(turn)
        grants = [e for e in turn.graph_context_execution.events if type(e) is NativeDirectSourceAuthorizedV1
            and e.provider_attempt_id == selected.controller_attempt_id]
        assert len(grants) > 1
        observations = [e for e in turn.graph_context_execution.events if type(e) is NativeDirectSourceObservedV1
            and e.authorization_event_id in {g.event_id for g in grants}]
        assert not observations or max(g.sequence for g in grants) < min(e.sequence for e in observations)
        trace = a.service.list_context_trace_attempts(world_id=a.world_id, turn_id=turn.turn_id)[-1]
        activity = [e for e in trace.observations if e.kind == 'context_decision' and e.policy_version == 'native_source_document_read_progress_v2']
        assert activity[-1].action == 'expanded'
        reads.append((kwargs['source_artifact_id'], kwargs['source_revision_id']))
        return original_read(context, **kwargs)

    monkeypatch.setattr(AgentConversationService, 'authorize_native_direct_sources', grant)
    monkeypatch.setattr(core, 'read_direct_native_source', read)
    case = _fresh_case(publication_lane, tmp_path, monkeypatch, None, False, False, False,
        native_body='direct_support', direct_source=True,
        native_source_text='# Additional source\nSeparate source evidence.\n',
        before_provider=lambda adapter, _: adapters.append(adapter))
    events = case.turn.graph_context_execution.events
    granted = [e for e in events if type(e) is NativeDirectSourceAuthorizedV1]
    observed = [e for e in events if type(e) is NativeDirectSourceObservedV1]
    assert len(calls) == 1 and calls[0] == len(granted) == len(observed) == len(reads) > 1
    assert reads == [(g.source_artifact_id, g.source_revision_id) for g in granted]
    assert case.turn.status == 'completed' and case.turn.completion.native_body_citations



def test_direct_grant_batch_cannot_cross_selected_search(application_state_dsn):
    from application_state.errors import ApplicationStateValidationError
    case = direct_grant_case(application_state_dsn, boundary=True)
    before = grant_snapshot(case)
    with pytest.raises(ApplicationStateValidationError, match='not consecutive'):
        commit_grants(case)
    assert grant_snapshot(case) == before


def test_mid_group_read_failure_retains_grants_and_prior_observation(publication_lane, tmp_path, monkeypatch):
    from tests.test_surface_native_build_ordinary import _fresh_case
    from application_state.agent_conversation.native_execution import NativeWriterAuthorizedV1
    original = core.read_direct_native_source
    adapters, reads = [], []

    def failing_read(*args, **kwargs):
        reads.append(kwargs['source_artifact_id'])
        if len(reads) == 2:
            raise RuntimeError('Injected second source read failure')
        return original(*args, **kwargs)

    monkeypatch.setattr(core, 'read_direct_native_source', failing_read)
    with pytest.raises(AssertionError):  # Existing ordinary fixture requires HTTP200.
        _fresh_case(publication_lane, tmp_path, monkeypatch, None, False, False, False,
            native_body='direct_support', direct_source=True,
            native_source_text='# Additional source\nSeparate source evidence.\n',
            before_provider=lambda adapter, _: adapters.append(adapter))
    a = adapters[-1]
    turn = a.service.inspect_turn(world_id=a.world_id, turn_id=a.turn.turn_id)
    events = turn.graph_context_execution.events
    grants = [e for e in events if type(e) is NativeDirectSourceAuthorizedV1]
    observed = [e for e in events if type(e) is NativeDirectSourceObservedV1]
    assert len(reads) == 2 and len(grants) > 1 and len(observed) == 1
    assert observed[0].authorization_event_id == grants[0].event_id
    assert not any(type(e) is NativeWriterAuthorizedV1 for e in events)
    assert turn.status == 'interrupted' and turn.completion is None


@pytest.mark.parametrize('component', ['graph_context_receipt', 'graph_context_execution'])
def test_source_callback_mutated_locked_receipt_rejects_before_write(application_state_dsn, monkeypatch, component):
    from application_state.agent_conversation import repository as repo
    from application_state.errors import ApplicationStateValidationError

    case = direct_grant_case(application_state_dsn)
    case.turn, _ = commit_grants(case)
    before = grant_snapshot(case)
    locked = []
    writes = []
    original_lock = repo.lock_turn
    original_update = repo.update_graph_execution

    def lock(*args, **kwargs):
        turn = original_lock(*args, **kwargs)
        locked.append(turn)
        return turn

    def update(*args, **kwargs):
        writes.append(True)
        return original_update(*args, **kwargs)

    def read(_authorization):
        assert locked and locked[-1] is not None
        object.__setattr__(getattr(locked[-1], component),
            'context_receipt_sha256', '0' * 64)
        return None

    monkeypatch.setattr(repo, 'lock_turn', lock)
    monkeypatch.setattr(repo, 'update_graph_execution', update)
    with pytest.raises(ApplicationStateValidationError):
        case.service.observe_native_direct_source(case.turn.world_id,
            case.turn.conversation_id, case.turn.turn_id,
            expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            event_id=uuid4(), authorization_event_id=case.grants[0]['event_id'], read=read)
    assert not writes
    assert grant_snapshot(case) == before


@pytest.mark.parametrize('component', ['graph_context_receipt', 'graph_context_execution'])
def test_persisted_native_corruption_is_rejected_before_source_io(application_state_dsn, component):
    import psycopg
    from psycopg import sql
    from application_state.errors import ApplicationStateIntegrityError

    case = direct_grant_case(application_state_dsn)
    case.turn, _ = commit_grants(case)
    path = (['provenance_sha256'] if component == 'graph_context_receipt'
            else ['policy', 'source_authority_sha256'])
    with psycopg.connect(case.dsn) as conn:
        conn.execute(sql.SQL("UPDATE agent.turn SET {}=jsonb_set({}, %s::text[], %s::jsonb) "
            "WHERE turn_id=%s").format(sql.Identifier(component), sql.Identifier(component)),
            (path, '"' + '0' * 64 + '"', case.turn.turn_id))
    corrupted = grant_snapshot(case)
    reads = []
    with pytest.raises(ApplicationStateIntegrityError):
        case.service.observe_native_direct_source(case.turn.world_id,
            case.turn.conversation_id, case.turn.turn_id,
            expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            event_id=uuid4(), authorization_event_id=case.grants[0]['event_id'],
            read=lambda _: reads.append(True))
    assert not reads
    assert grant_snapshot(case) == corrupted
