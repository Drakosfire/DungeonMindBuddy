"""Actual selected SDK → APP grant → existing host/Core read → shared answer."""

from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.services.agent_turn_service import _ClaimFence
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.jev_retrieval_contract import (
    RetrievalCandidate,
)
from tests.application_state.test_surface_native_decisions import sdk_case
from tests.test_surface_native_execution import execution
from tests.test_surface_native_writer import (
    published_lane as published_lane,
    published_case,
)
from tests.test_native_plan_statements import query
from tests.application_state.test_native_plan_statements import native_read_admission_probes as native_read_admission_probes
from tests.test_native_corpus_source_access import lane as lane
from application_state.errors import (
    ApplicationStateValidationError,
    ApplicationStateConflictError,
)


@contextmanager
def host(case, *, query_context=None, source_context=None):
    fence = _ClaimFence(case.service, case.turn)
    adapter = SimpleNamespace(
        fence=fence,
        service=case.service,
        world_id=case.turn.world_id,
        bootstrap=None,
        request=SimpleNamespace(
            message=case.turn.user_text, surface=SimpleNamespace(surface_id="plan")
        ),
        native_query=case.turn.graph_context_receipt.native_query,
        native_query_context=query_context,
        native_corpus_context=source_context,
        context_capture=None,
        _broker_execution=lambda: fence.turn.graph_context_execution,
    )
    try:
        yield adapter
    finally:
        case.turn, error = fence.stop()
        assert error is None


def record_candidates(case):
    from application_state.agent_conversation.native_plan_assertions import object_selection_handle
    q = case.turn.graph_context_receipt.native_query
    return [RetrievalCandidate(handle=object_selection_handle(q, m.entity_id),
        label=m.label, kind="Native Graph object") for m in q.object_matches]


def test_actual_driver_selected_native_support_reads_use_shared_claim(
    application_state_dsn, published_lane, monkeypatch, native_read_admission_probes
):
    context, record = published_case("plan", published_lane)
    record = execution(context.context_receipt_sha256, record.policy)
    query_context, result = query(published_lane, scope_mode="world")
    assert context.native_query == result

    def acquire(case):
        with host(case, query_context=query_context) as adapter:
            driver = PlanJevDriver(adapter)
            driver._read_native("statement", [m.statement_id for m in result.matches])
            driver._read_native(
                "assertion", [m.assertion_id for m in result.assertion_matches]
            )
            assert driver._native_object_examined()

    case = sdk_case(
        application_state_dsn,
        context_record=(context, record),
        acquisitions=((record_candidates, acquire),),
    )
    assert any(
        type(e) is t.NativePlanStatementReadObservedV1
        for e in case.turn.graph_context_execution.events
    )
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadObservedV2
    assert any(
        type(e) is NativePlanAssertionReadObservedV2
        for e in case.turn.graph_context_execution.events
    )
    assert (
        AgentConversationService().inspect_turn(
            world_id=case.turn.world_id, turn_id=case.turn.turn_id
        )
        == case.turn
    )

    from tests.application_state.test_surface_native_completion import (
        completed_input,
        finish,
    )

    def rows(writer):
        return [
            dict(
                kind="native_statement_report",
                text="A reported that B fled, with uncertainty.",
                statement_handles=[
                    writer.frame["native_statements"]["statements"][0][
                        "statement_handle"
                    ]
                ],
            ),
            dict(
                kind="native_assertion_claim",
                text="The Graph preserves a provisional speculative belief.",
                assertion_handles=[
                    r["assertion_handle"]
                    for r in writer.frame["native_assertions"]["assertions"]
                ],
            ),
        ]

    writer = completed_input(application_state_dsn, acquired=case, answer_rows=rows)
    from apps.live_control_server.services import native_graph_reads

    monkeypatch.setattr(
        native_graph_reads,
        "read_selected",
        lambda *_: pytest.fail("Late read reached Core"),
    )

    def reject_late_read():
        before = writer.turn
        with host(writer, query_context=query_context) as adapter:
            with pytest.raises(
                (ApplicationStateValidationError, ApplicationStateConflictError)
            ):
                PlanJevDriver(adapter)._read_native(
                    "statement", [result.matches[0].statement_id]
                )
        assert writer.turn == before

    reject_late_read()  # writer has already consumed the exact read prefix
    completed = finish(writer)
    writer.turn = completed
    reject_late_read()  # completed turns cannot grant new acquisition
    assert completed.completion.native_clause_citations
    assert completed.completion.native_assertion_citations
    assert all(
        c.read_revision_id == result.authority.revision_id
        for c in completed.completion.native_assertion_citations
    )
    assert (
        AgentConversationService().inspect_turn(
            world_id=completed.world_id, turn_id=completed.turn_id
        )
        == completed
    )
    assert finish(writer) == completed and len(writer.writer_calls) == 1


@pytest.mark.parametrize("full", [False, True])
def test_actual_source_navigator_and_shared_writer_deliver_exact_corpus_citation(
    application_state_dsn, lane, full
):
    from tests.test_surface_native_writer import body_case
    from tests.test_native_corpus_source_access import GM
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import (
        prepare_native_source_context,
    )
    from tests.application_state.test_surface_native_completion import (
        completed_input,
        finish,
    )

    context, record, _ = body_case("plan", lane, full=full)
    record = execution(context.context_receipt_sha256, record.policy)
    source_context = prepare_native_source_context(
        managed_world_id="managed",
        principal=GM,
        repository=lane.repo,
        resolve_identity=lambda _: lane.bound,
    )
    assert source_context.authority == context.source_authority

    def offered(case):
        with host(case, source_context=source_context) as adapter:
            driver = PlanJevDriver(adapter)
            return driver.native_sources.offered()

    def extent(case):
        prefix = "native-full-document:" if full else "native-body:"
        return tuple(row for row in offered(case) if row.handle.startswith(prefix))[:1]

    def acquire(case):
        from application_state.agent_conversation.plan_jev_decision import (
            current_selection,
        )

        with host(case, source_context=source_context) as adapter:
            driver = PlanJevDriver(adapter)
            driver.native_sources.select(current_selection(case.turn).selected_handles)
            assert driver.native_sources.examined()

    case = sdk_case(
        application_state_dsn,
        context_record=(context, record),
        acquisitions=((offered, acquire), (extent, acquire)),
    )

    def rows(writer):
        return [
            dict(
                kind="native_body_claim",
                text="The check revealed an origin beyond this plane.",
                excerpt_handles=[
                    row["excerpt_handle"]
                    for row in writer.frame["native_body_evidence"]["excerpts"]
                ],
            )
        ]

    writer = completed_input(application_state_dsn, acquired=case, answer_rows=rows)
    completed = finish(writer)
    (citation,) = completed.completion.native_body_citations
    assert citation.selector_policy == (
        "native_full_document_v1" if full else "markdown_sections_v1"
    )
    assert ("Unselected private context." in writer.prepared.body.decode()) == full
    assert completed.completion.native_assertion_citations == []
    assert (
        AgentConversationService().inspect_turn(
            world_id=completed.world_id, turn_id=completed.turn_id
        )
        == completed
    )
    assert finish(writer) == completed and len(writer.writer_calls) == 1


@pytest.mark.parametrize("invalid", ["foreign", "unselected", "stale"])
def test_rejected_selected_read_never_reaches_core(
    application_state_dsn, published_lane, monkeypatch, invalid
):
    from apps.live_control_server.services import native_graph_reads

    context, record = published_case("plan", published_lane)
    record = execution(context.context_receipt_sha256, record.policy)
    query_context, result = query(published_lane, scope_mode="world")
    monkeypatch.setattr(
        native_graph_reads,
        "read_selected",
        lambda *_: pytest.fail("Rejected grant reached Core"),
    )

    class RejectedReadProbeComplete(Exception):
        pass

    def selected(case):
        if invalid == "unselected":
            return [RetrievalCandidate(handle="other-navigation", label="Unrelated navigation", kind="navigation")]
        return record_candidates(case)

    def acquire(case):
        before = case.turn
        with host(case, query_context=query_context) as adapter:
            driver = PlanJevDriver(adapter)
            with pytest.raises(
                (ApplicationStateValidationError, ApplicationStateConflictError)
            ):
                if invalid == "stale":
                    case.service.authorize_native_read(
                        before.world_id,
                        before.conversation_id,
                        before.turn_id,
                        expected_revision=before.revision - 1,
                        expected_attempt=before.attempt,
                        event_id=uuid4(),
                        record_kind="statement",
                        record_ids=(result.matches[0].statement_id,),
                    )
                else:
                    driver._read_native(
                        "assertion" if invalid == "unselected" else "statement",
                        [
                            result.assertion_matches[0].assertion_id
                            if invalid == "unselected"
                            else "foreign"
                        ],
                    )
        assert case.turn == before
        assert (
            case.service.inspect_turn(world_id=before.world_id, turn_id=before.turn_id)
            == before
        )

        # Stop at the rejected read. An actually selected object deliberately
        # remains unacquired; the next provider must not bypass that obligation.
        raise RejectedReadProbeComplete

    with pytest.raises(RejectedReadProbeComplete):
        sdk_case(
            application_state_dsn,
            context_record=(context, record),
            acquisitions=((selected, acquire),),
        )


def test_changed_native_binding_keeps_unresolved_grant_and_cannot_retry(
    application_state_dsn, published_lane
):
    context, record = published_case("plan", published_lane)
    record = execution(context.context_receipt_sha256, record.policy)
    query_context, result = query(published_lane, scope_mode="world")
    query_context = replace(query_context, resolve_binding=lambda _: object())
    cases = []

    def acquire(case):
        cases.append(case)
        with host(case, query_context=query_context) as adapter:
            driver = PlanJevDriver(adapter)
            with pytest.raises(ValueError, match="binding changed"):
                driver._read_native("statement", [result.matches[0].statement_id])
            with pytest.raises(ValueError, match="cannot be reacquired"):
                driver._read_native("statement", [result.matches[0].statement_id])
            # No follow-up decision or writer may launder an unsettled grant.
            driver._native_object_examined()

    with pytest.raises(ValueError, match="must settle"):
        sdk_case(
            application_state_dsn,
            context_record=(context, record),
            acquisitions=((record_candidates, acquire),),
        )
    (case,) = cases
    events = case.turn.graph_context_execution.events
    assert sum(type(e) is t.NativePlanStatementReadAuthorizedV1 for e in events) == 1
    assert not any(type(e) is t.NativePlanStatementReadObservedV1 for e in events)
    assert case.turn.status == "running" and case.turn.completion is None
    assert (
        case.service.inspect_turn(
            world_id=case.turn.world_id, turn_id=case.turn.turn_id
        )
        == case.turn
    )


def test_unavailable_assertion_settles_as_gap_without_fabricated_evidence(
    application_state_dsn, published_lane, monkeypatch
):
    from apps.live_control_server.services import native_graph_reads
    from tests.application_state.test_surface_native_completion import (
        completed_input,
        finish,
    )

    context, record = published_case("plan", published_lane)
    record = execution(context.context_receipt_sha256, record.policy)
    query_context, result = query(published_lane, scope_mode="world")
    monkeypatch.setattr(
        native_graph_reads,
        "open_admitted_native_text",
        lambda *_: SimpleNamespace(status="unavailable"),
    )

    def acquire(case):
        with host(case, query_context=query_context) as adapter:
            driver = PlanJevDriver(adapter)
            if result.matches:
                driver._read_native("statement", [m.statement_id for m in result.matches])
            driver._read_native(
                "assertion", [m.assertion_id for m in result.assertion_matches]
            )
            assert "native_assertion_support_unavailable" in driver.gaps
            from application_state.agent_conversation.native_plan_assertions import object_record_ids
            affected = [c for c in driver._native_object_examined()
                if object_record_ids(result, (c.handle,), assertion=True)]
            assert affected and all(
                ": partial;" in c.kind or ": unavailable;" in c.kind for c in affected
            )  # Other objects can retain readable qualified statements without assertions.

    case = sdk_case(
        application_state_dsn,
        context_record=(context, record),
        acquisitions=((record_candidates, acquire),),
    )
    observed = [
        e
        for e in case.turn.graph_context_execution.events
        if type(e) is t.NativePlanAssertionReadObservedV1
    ]
    assert (
        len(observed) == 1 and observed[0].status == "partial" and not observed[0].reads
    )
    assert set(observed[0].unavailable_assertion_ids) == {
        m.assertion_id for m in result.assertion_matches
    }
    writer = completed_input(
        application_state_dsn, acquired=case, answer_rows=lambda _: []
    )
    assert not writer.frame["native_assertions"]["assertions"]
    completed = finish(writer)
    assert not completed.completion.native_assertion_citations
    assert completed.completion.answer_context_status == "insufficient_evidence"
    assert any(
        type(s) is t.SurfaceLimitationV1 and s.code == "partial_retrieval"
        for s in completed.completion.answer_segments
    )
    assert (
        case.service.inspect_turn(
            world_id=completed.world_id, turn_id=completed.turn_id
        )
        == completed
    )


@pytest.mark.parametrize('mixed', [False, True])
@pytest.mark.parametrize('question,scoped', [('What did the check reveal in session 8?',True),
    ('What did the check reveal?',False), ('What did the check reveal in session 99?',False)])
def test_native_scope_expands_through_actual_sdk_reload_and_exact_core_read(
    application_state_dsn, lane, monkeypatch, mixed, question, scoped
):
    from tests.test_surface_native_writer import body_case, BODY
    from tests.test_native_corpus_source_access import GM, admit
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context
    from apps.live_control_server.services import native_source_display
    from application_state.agent_conversation.native_retrieval import NativeRetrievalSelectedV1
    from application_state.agent_conversation.native_corpus import NativeBodyReadObservedV1

    admit(lane, 'second', body=BODY)
    context, record, _ = body_case('plan', lane)
    record = execution(context.context_receipt_sha256, record.policy)
    source_context = prepare_native_source_context(managed_world_id='managed', principal=GM,
        repository=lane.repo, resolve_identity=lambda _:lane.bound)
    assert source_context.authority == context.source_authority
    def labels(items, world_id):
        return [dict(label='Session '+('8' if item.origin.object_id == 'first' else '9'),
            kind='recap', status='available', origin_matches_current_metadata=True,
            campaign_id='longmont-c1', session_id='session-'+('8' if item.origin.object_id == 'first' else '9'))
            for item in items]
    monkeypatch.setattr(native_source_display, 'source_display_metadata', labels)
    retained = {'expansion':None}
    search_first = scoped and not mixed
    original_head = lane.repo.get_head('world:test')

    def narrow(case):
        with host(case, source_context=source_context) as adapter:
            nav = PlanJevDriver(adapter).native_sources
            rows = nav.offered()
            expansions = [row for row in rows if row.handle.startswith('native-corpus-expand:')]
            assert len(expansions) == int(scoped)
            direct = [row for row in rows if row.handle.startswith('native-direct-source:')]
            assert len(direct) == (1 if scoped else 2)
            if search_first:
                sections = [row for row in rows if row.handle.startswith('native-body:')]
                assert sections and all('Session 8' in row.label for row in sections)
            selected = next(row for row in direct if 'Session 8' in row.label)
            retained['outside_artifact'] = next(pair[0] for pair,display in nav._source_display.items() if display.get('session_id')=='session-9')
            retained['expansion'] = expansions[0].handle if expansions else None
            return (expansions[0], selected) if scoped and mixed else tuple(expansions) if scoped else (selected,)

    def apply(case):
        with host(case, source_context=source_context) as adapter:
            driver = PlanJevDriver(adapter)
            step = case.steps[-1]
            selected = SimpleNamespace(operation=step.selection.operation,
                selected_handles=tuple(step.selection.selected_handles))
            dispatch = SimpleNamespace(parent=step.parent, authorization=step.auth, selection=selected)
            driver.current = dispatch
            if search_first and retained['expansion'] in selected.selected_handles:
                # Parent/selection are already durable. Naming can disappear on
                # reload without revoking this acknowledged navigation choice.
                monkeypatch.setattr(native_source_display, 'source_display_metadata',
                    lambda items,_:[dict(status='unavailable',kind='recap',label=None,
                        campaign_id=None,session_id=None,origin_matches_current_metadata=None) for item in items])
                driver = PlanJevDriver(adapter)
                driver.current = dispatch
            before = tuple(adapter.fence.turn.graph_context_execution.events)
            if retained['expansion'] in selected.selected_handles:
                for parent in (step.parent.model_copy(update={'request_id':uuid4()}),
                        step.parent.model_copy(update={'candidates':()})):
                    with pytest.raises(ValueError):
                        driver.native_sources.expand_selected(retained['expansion'],parent=parent)
                actual_turn=adapter.fence.renewer._turn
                try:
                    adapter.fence.renewer._turn=actual_turn.model_copy(update={'attempt':actual_turn.attempt+1})
                    with pytest.raises(ValueError):
                        driver.native_sources.expand_selected(retained['expansion'],parent=step.parent)
                finally:
                    adapter.fence.renewer._turn=actual_turn
                assert tuple(adapter.fence.turn.graph_context_execution.events)==before
            driver.apply(dispatch)
            after = tuple(adapter.fence.turn.graph_context_execution.events)
            if scoped and not mixed and retained['expansion'] in selected.selected_handles:
                assert after == before  # Expansion alone grants/reads nothing.
                monkeypatch.setattr(native_source_display, 'source_display_metadata', labels)
            elif any(handle.startswith('native-corpus-search:') for handle in selected.selected_handles):
                assert not any(isinstance(event,NativeBodyReadObservedV1) for event in after[len(before):])
            else:
                reads = [event for event in after[len(before):] if isinstance(event, NativeBodyReadObservedV1)]
                assert len(reads) == 1 and reads[0].excerpt is not None
            with pytest.raises(ValueError):
                driver.native_sources.expand_selected((retained['expansion'] or 'native-corpus-expand:')+'forged', parent=step.parent)
            if retained['expansion'] and retained['expansion'] not in selected.selected_handles:
                with pytest.raises(ValueError):
                    driver.native_sources.expand_selected(retained['expansion'], parent=step.parent)
            assert any(type(event) is NativeRetrievalSelectedV1 for event in after)

    def broader(case):
        case.turn = AgentConversationService().inspect_turn(world_id=case.turn.world_id, turn_id=case.turn.turn_id)
        with host(case, source_context=source_context) as adapter:
            nav = PlanJevDriver(adapter).native_sources
            rows = nav.offered()
            assert all(not row.handle.startswith('native-corpus-expand:') for row in rows)
            direct = [row for row in rows if row.handle.startswith('native-direct-source:')]
            assert len(direct) == (1 if mixed or not scoped else 2)
            if search_first:
                # Original source IDs/catalog pins survive unavailable names.
                unseen_pair = next(pair for pair,display in nav._source_display.items()
                    if pair[0] == retained['outside_artifact'])
                _,catalog_search,_,_ = nav._events()
                catalog = next(c for c in catalog_search.catalogs
                    if c.source.artifact.source_artifact_id == unseen_pair[0])
                return tuple(row for row in rows if row.handle.startswith('native-body:'+catalog.catalog_sha256+':'))
            return tuple(row for row in direct if 'Session 9' in row.label)

    def search(case):
        with host(case, source_context=source_context) as adapter:
            return tuple(row for row in PlanJevDriver(adapter).native_sources.offered()
                if row.handle.startswith('native-corpus-search:'))

    acquisitions = (((search,apply),) if search_first else ()) + ((narrow,apply),(broader,apply))
    case = sdk_case(application_state_dsn, context_record=(context,record), native=True,
        question=question, acquisitions=acquisitions)
    from tests.application_state.test_surface_native_completion import completed_input, finish
    def answer(writer):
        return [dict(kind='native_body_claim', text='The check revealed an origin beyond this plane.',
            excerpt_handles=[row['excerpt_handle'] for row in writer.frame['native_body_evidence']['excerpts']])]
    writer = completed_input(application_state_dsn, acquired=case, answer_rows=answer)
    completed = finish(writer)
    assert completed.completion.native_body_citations
    assert all(c.selector_policy == ('markdown_sections_v1' if search_first else 'native_full_document_v1')
        for c in completed.completion.native_body_citations)

    assert lane.repo.get_head('world:test') == original_head


def test_native_expansion_fence_rejects_older_reader_without_row_rewrite(application_state_dsn, monkeypatch):
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError
    from importlib import import_module
    cli.assert_at_head(dsn=application_state_dsn)
    monkeypatch.setattr(cli, '_alembic_head', lambda:'20261106_0121')
    with pytest.raises(ApplicationStateMigrationError):
        cli.assert_at_head(dsn=application_state_dsn)
    fence = import_module('application_state.migrations.versions.20261107_0122_native_candidate_expansion')
    assert fence.upgrade() is None
    with pytest.raises(RuntimeError, match='Older readers'):
        fence.downgrade()


def test_native_graph_objects_survive_source_scope_and_share_exact_expansion_batch(
    application_state_dsn, published_lane, monkeypatch
):
    import json
    from hashlib import sha256
    from tests.test_source_statements import GM, NOW
    from tests.test_surface_native_context import seal
    from application_state.agent_conversation.native_corpus import NativeBodyReadObservedV1
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context
    from apps.live_control_server.services import native_source_display
    from dungeonmind.application.vnext import publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_custom_predicate_profile, GM_LABEL
    from application_state.agent_conversation.plan_jev_decision import current_selection

    world = published_lane.world.world_id
    for name in ('session-8','session-9'):
        body = '# Recap\n\nB fled.\n'
        publish_native_text_source_evidence(repository=published_lane.repo,
            domain_contract=dungeonbuddy_world_domain_contract(), semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
            request=NativeTextSourceAdmissionV1(space_id=world,admission_id=name,
                expected_parent_revision_id=published_lane.repo.get_head(world).head_revision_id,
                created_at=NOW,body_text=body,expected_body_sha256=sha256(body.encode()).hexdigest(),
                source_classification='dungeonbuddy.source:session_recap',authority='primary',
                visibility={'kind':'labels_any','labels':[GM_LABEL]},
                origin={'namespace':'test.scope','object_id':name,'revision_id':'1'},
                spans=[dict(client_ref='support',evidence_role='support',start_byte=0,end_byte=len(body.encode()),
                    expected_slice_sha256=sha256(body.encode()).hexdigest())]))
    binding = SimpleNamespace(managed_world_id=world,native_world_id=world,binding_version=1,provisioning_id='scope-fixture')
    source_context = prepare_native_source_context(managed_world_id=world,principal=GM,
        repository=published_lane.repo,resolve_identity=lambda _:binding)
    graph_context, graph_query = query(published_lane,text='What did B do in session 8?',scope_mode='world')
    context, record = published_case('plan',published_lane)
    wire = context.model_dump(mode='json',by_alias=True)
    wire['source_authority'] = source_context.authority.model_dump(mode='json')
    wire['native_query'] = graph_query.model_dump(mode='json',by_alias=True)
    context = type(context).model_validate_json(json.dumps(seal(wire)))
    policy = record.policy.model_copy(update={
        'action':record.policy.action.model_copy(update={'intent':record.policy.action.intent.model_copy(update={'message':graph_query.question})}),
        'source_authority_sha256':t.canonical_sha256(context.source_authority),'native_query_sha256':t.canonical_sha256(graph_query)})
    record = execution(context.context_receipt_sha256,policy)
    def labels(items, _):
        return [dict(label=item.origin.object_id,kind='recap' if item.origin.namespace=='test.scope' else 'worldbuilding',
            status='available',origin_matches_current_metadata=True,campaign_id='c1',
            session_id=item.origin.object_id if item.origin.namespace=='test.scope' else None) for item in items]
    monkeypatch.setattr(native_source_display,'source_display_metadata',labels)
    graph_handles = set()
    def select(case):
        with host(case,query_context=graph_context,source_context=source_context) as adapter:
            driver = PlanJevDriver(adapter)
            rows = driver.offered()
            objects = driver._native_object_candidates()
            assert objects and {row.handle for row in objects} <= {row.handle for row in rows}
            graph_handles.update(row.handle for row in objects)
            expansion = next(row for row in rows if row.handle.startswith('native-corpus-expand:'))
            return (expansion,objects[0])
    def apply(case):
        with host(case,query_context=graph_context,source_context=source_context) as adapter:
            adapter.broker_graph_operation=lambda *_:pytest.fail('Native scope expansion reached classic Graph broker')
            driver = PlanJevDriver(adapter)
            step = case.steps[-1]
            selection = current_selection(case.turn)
            before = tuple(adapter.fence.turn.graph_context_execution.events)
            for handle in selection.selected_handles:
                if handle.startswith('native-corpus-expand:'):
                    driver.native_sources.expand_selected(handle,parent=step.parent)
                    assert tuple(adapter.fence.turn.graph_context_execution.events)==before
            dispatch = SimpleNamespace(parent=step.parent,authorization=step.auth,
                selection=SimpleNamespace(operation=selection.operation,selected_handles=tuple(selection.selected_handles)))
            driver.current=dispatch
            driver.apply(dispatch)
            added=adapter.fence.turn.graph_context_execution.events[len(before):]
            if set(selection.selected_handles)&graph_handles:
                assert any(isinstance(event,(t.NativePlanStatementReadObservedV1,t.NativePlanAssertionReadObservedV1)) for event in added)
                assert not any(isinstance(event,NativeBodyReadObservedV1) for event in added)
            else:
                assert any(isinstance(event,NativeBodyReadObservedV1) and event.excerpt is not None for event in added)
    def wider(case):
        case.turn=AgentConversationService().inspect_turn(world_id=world,turn_id=case.turn.turn_id)
        with host(case,query_context=graph_context,source_context=source_context) as adapter:
            return tuple(row for row in PlanJevDriver(adapter).offered()
                if row.handle.startswith('native-direct-source:') and 'session-9' in row.label)
    original_head=published_lane.repo.get_head(world)
    case=sdk_case(application_state_dsn,context_record=(context,record),native=True,
        acquisitions=((select,apply),(wider,apply)))
    assert any(isinstance(event,NativeBodyReadObservedV1) for event in case.turn.graph_context_execution.events)
    assert published_lane.repo.get_head(world)==original_head


@pytest.mark.parametrize('keyword,corrupt_focus', [('origin',None),('private',None),('unicorn',None),(None,None),
    ('origin','label'),('origin','handle'),('origin','duplicate')])
def test_keyword_first_view_reloads_and_broad_recovery_reads_excluded_source_section(
    application_state_dsn, lane, monkeypatch, keyword, corrupt_focus
):
    from tests.test_surface_native_writer import body_case
    from tests.test_native_corpus_source_access import GM
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context
    from application_state.agent_conversation.native_source_keywords import KEYWORD_KIND, RETAINED_KEYWORD_KIND
    from generationengine import GenerationEngineError
    import json
    from application_state.agent_conversation.native_corpus import NativeBodyReadObservedV1
    from application_state.agent_conversation.native_retrieval import NativeRetrievalSelectedV1
    context, record, _ = body_case('plan', lane)
    record = execution(context.context_receipt_sha256, record.policy)
    source_context = prepare_native_source_context(managed_world_id='managed', principal=GM,
        repository=lane.repo, resolve_identity=lambda _:lane.bound)
    original_head = lane.repo.get_head('world:test')
    retained = {}

    def search_and_hint(case):
        retained['case'] = case
        with host(case, source_context=source_context) as adapter:
            nav = PlanJevDriver(adapter).native_sources
            rows = nav.offered()
            selected = [row for row in rows if row.handle.startswith('native-corpus-search:')]
            assert len(selected) == 1
            hints = [row for row in rows if row.kind == KEYWORD_KIND]
            assert hints
            if keyword:
                chosen = next(row for row in hints if row.label == repr(keyword))
                retained['hint'] = chosen.handle
                selected.append(chosen)
            return selected

    def apply(case):
        with host(case, source_context=source_context) as adapter:
            driver = PlanJevDriver(adapter)
            step = case.steps[-1]
            dispatch = SimpleNamespace(parent=step.parent, authorization=step.auth,
                selection=SimpleNamespace(operation=step.selection.operation,
                    selected_handles=tuple(step.selection.selected_handles)))
            driver.current = dispatch
            before = tuple(adapter.fence.turn.graph_context_execution.events)
            if retained.get('hint') in dispatch.selection.selected_handles:
                for parent in (step.parent.model_copy(update={'request_id':uuid4()}),
                        step.parent.model_copy(update={'candidates':()})):
                    with pytest.raises(ValueError):
                        driver.native_sources.accept_keyword_selection(retained['hint'], parent=parent)
                actual = adapter.fence.renewer._turn
                try:
                    adapter.fence.renewer._turn = actual.model_copy(update={'attempt':actual.attempt+1})
                    with pytest.raises(ValueError):
                        driver.native_sources.accept_keyword_selection(retained['hint'], parent=step.parent)
                finally:
                    adapter.fence.renewer._turn = actual
                assert tuple(adapter.fence.turn.graph_context_execution.events) == before
            driver.apply(dispatch)
            if any(h.startswith('native-corpus-expand:') for h in dispatch.selection.selected_handles):
                assert tuple(adapter.fence.turn.graph_context_execution.events) == before
            if any(h.startswith('native-corpus-search:') for h in dispatch.selection.selected_handles):
                assert not any(isinstance(e, NativeBodyReadObservedV1)
                    for e in adapter.fence.turn.graph_context_execution.events[len(before):])

    def narrowed(case):
        case.turn = AgentConversationService().inspect_turn(world_id=case.turn.world_id, turn_id=case.turn.turn_id)
        with host(case, source_context=source_context) as adapter:
            nav = PlanJevDriver(adapter).native_sources
            rows = nav.offered()
            assert not any(row.kind == KEYWORD_KIND for row in rows)
            sections = [row for row in rows if row.handle.startswith('native-body:')]
            expand = [row for row in rows if row.handle.startswith('native-corpus-expand:')]
            focused = keyword in {'origin','private'}
            assert len(sections) == (1 if focused else 2)
            assert len(expand) == int(focused)
            # Full-source access survives even when sections are prioritized.
            assert any(row.handle.startswith('native-direct-source:') for row in rows)
            return expand if focused else sections

    def recovered(case):
        case.turn = AgentConversationService().inspect_turn(world_id=case.turn.world_id, turn_id=case.turn.turn_id)
        with host(case, source_context=source_context) as adapter:
            rows = PlanJevDriver(adapter).native_sources.offered()
            assert not any(row.handle.startswith('native-corpus-expand:') for row in rows)
            sections = [row for row in rows if row.handle.startswith('native-body:')]
            if keyword in {'origin','private'}:
                assert len(sections) == 2
                return sections
            assert not sections  # Already acquired when no positive keyword existed.
            return ()

    def examined(case):
        with host(case, source_context=source_context) as adapter:
            rows = list(PlanJevDriver(adapter).native_sources.examined())
            focus = [row for row in rows if row.kind == RETAINED_KEYWORD_KIND]
            if focus and corrupt_focus:
                if corrupt_focus == 'duplicate':
                    rows.append(focus[0])
                else:
                    changes = {'label':'private'} if corrupt_focus == 'label' else {'handle':'native-corpus-keyword:'+'0'*64}
                    rows = [row.model_copy(update=changes) if row is focus[0] else row for row in rows]
            return rows

    def execute():
        return sdk_case(application_state_dsn, context_record=(context,record), native=True,
            question='Find origin and private unicorn', examined=examined,
            acquisitions=((search_and_hint,apply),(narrowed,apply)) +
                (((recovered,apply),) if keyword in {'origin','private'} else ()))
    if corrupt_focus:
        from application_state.agent_conversation import native_retrieval
        verify=native_retrieval.verify_input
        def capture_admission(*args,**kwargs):
            try:return verify(*args,**kwargs)
            except ValueError as error:
                retained['admission_error']=str(error)
                raise
        monkeypatch.setattr(native_retrieval,'verify_input',capture_admission)
        with pytest.raises((GenerationEngineError,ValueError)) as caught:
            execute()
        errors=[];error=caught.value
        while error is not None:
            errors.append(str(error));error=error.__cause__
        # The generic fixture's known-not-sent callback can fail after rejected
        # authorization. Assert the actual owning boundary, not that wrapper.
        errors.append(retained.get('admission_error',''))
        assert any('keyword focus' in error.lower() for error in errors), errors
        case=retained['case']
        stored=case.service.inspect_turn(world_id=case.turn.world_id,turn_id=case.turn.turn_id)
        assert not any(isinstance(e,NativeBodyReadObservedV1) for e in stored.graph_context_execution.events)
        assert lane.repo.get_head('world:test') == original_head
        return
    case = execute()
    seen_focus=False
    for step,sent in zip(case.steps,case.sent):
        if step.semantic:continue
        wire=json.loads(sent.content);focus=[c for c in step.parent.examined_candidates if c.kind==RETAINED_KEYWORD_KIND]
        assert len(wire['questions']) == len(step.parent.candidates)+1
        assert all(c['kind'] != RETAINED_KEYWORD_KIND for c in wire['state'].get('examined_subjects',[]))
        if focus:
            seen_focus=True
            assert wire['state']['selected_content_keywords'] == [keyword]
        else:
            assert 'selected_content_keywords' not in wire['state']
    assert seen_focus == (keyword in {'origin','private'})
    selections = [e for e in case.turn.graph_context_execution.events if type(e) is NativeRetrievalSelectedV1]
    assert all(e.operation != 'select_candidates' or any(not h.startswith('native-corpus-keyword:')
        for h in e.selected_handles) for e in selections)
    from tests.application_state.test_surface_native_completion import completed_input, finish
    def answer(writer):
        return [dict(kind='native_body_claim', text='The check revealed an origin beyond this plane.',
            excerpt_handles=[row['excerpt_handle'] for row in writer.frame['native_body_evidence']['excerpts']])]
    writer=completed_input(application_state_dsn, acquired=case, answer_rows=answer)
    assert 'selected_content_keywords' not in json.dumps(writer.frame)
    completed = finish(writer)
    assert completed.completion.native_body_citations
    assert lane.repo.get_head('world:test') == original_head


def test_keyword_reader_fence_has_no_row_rewrite(application_state_dsn, monkeypatch):
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError
    from importlib import import_module
    cli.assert_at_head(dsn=application_state_dsn)
    monkeypatch.setattr(cli, '_alembic_head', lambda:'20261107_0122')
    with pytest.raises(ApplicationStateMigrationError):
        cli.assert_at_head(dsn=application_state_dsn)
    fence = import_module('application_state.migrations.versions.20261107_0123_native_keyword_choices')
    assert fence.upgrade() is None
    with pytest.raises(RuntimeError, match='Older readers'):
        fence.downgrade()


def test_actual_sdk_keyword_only_vote_finishes_without_source_acquisition(application_state_dsn, lane):
    from tests.test_surface_native_writer import body_case
    from tests.test_native_corpus_source_access import GM
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context
    from application_state.agent_conversation.native_source_keywords import KEYWORD_KIND
    from application_state.agent_conversation.native_corpus import NativeBodySearchAuthorizedV1, NativeBodyReadAuthorizedV1
    context, record, _ = body_case('plan', lane)
    record = execution(context.context_receipt_sha256, record.policy)
    source_context = prepare_native_source_context(managed_world_id='managed', principal=GM,
        repository=lane.repo, resolve_identity=lambda _:lane.bound)
    def hints(case):
        with host(case, source_context=source_context) as adapter:
            return tuple(row for row in PlanJevDriver(adapter).native_sources.offered() if row.kind == KEYWORD_KIND)
    def finish_without_read(case):
        with host(case, source_context=source_context) as adapter:
            driver = PlanJevDriver(adapter)
            step = case.steps[-1]
            assert step.selection.operation == 'finish_retrieval' and not step.selection.selected_handles
            dispatch = SimpleNamespace(parent=step.parent, authorization=step.auth,
                selection=SimpleNamespace(operation=step.selection.operation, selected_handles=()))
            driver.current = dispatch
            before = tuple(adapter.fence.turn.graph_context_execution.events)
            driver.apply(dispatch)
            assert driver.finished  # The ordinary driver's while loop stops here.
            assert tuple(adapter.fence.turn.graph_context_execution.events) == before
            assert driver.offered() == ()
    case = sdk_case(application_state_dsn, context_record=(context,record), native=True,
        question='Find an origin', acquisitions=((hints,finish_without_read),), include_final_decision=False)
    assert not any(isinstance(e,(NativeBodySearchAuthorizedV1,NativeBodyReadAuthorizedV1))
        for e in case.turn.graph_context_execution.events)


def test_explicit_acquired_source_is_not_replaced_by_keyword_classification(lane):
    from tests.test_surface_native_writer import body_case
    from application_state.agent_conversation.native_writer import model_frame
    from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
    context, record, read = body_case('plan', lane)
    turn = SimpleNamespace(user_text='What did that source say?', graph_context_receipt=context,
        graph_context_execution=record)
    from tests.test_native_corpus_source_access import GM
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context
    source_context = prepare_native_source_context(managed_world_id='managed', principal=GM,
        repository=lane.repo, resolve_identity=lambda _:lane.bound)
    nav = NativeBodyNavigation(SimpleNamespace(fence=SimpleNamespace(turn=turn), native_corpus_context=source_context))
    before = model_frame(context, record)
    assert before['native_body_evidence']['excerpts']
    assert nav._keyword_offers() == ()
    assert model_frame(context, record) == before


def test_retained_keyword_focus_reader_fence_has_no_row_rewrite(application_state_dsn, monkeypatch):
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError
    from importlib import import_module
    cli.assert_at_head(dsn=application_state_dsn)
    monkeypatch.setattr(cli,'_alembic_head',lambda:'20261107_0123')
    with pytest.raises(ApplicationStateMigrationError):cli.assert_at_head(dsn=application_state_dsn)
    fence=import_module('application_state.migrations.versions.20261107_0124_native_keyword_focus')
    assert fence.upgrade() is None
    with pytest.raises(RuntimeError,match='Older readers'):fence.downgrade()
