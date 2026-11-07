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
    application_state_dsn, published_lane, monkeypatch
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
    assert any(
        type(e) is t.NativePlanAssertionReadObservedV1
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
            before = tuple(adapter.fence.turn.graph_context_execution.events)
            driver.apply(dispatch)
            after = tuple(adapter.fence.turn.graph_context_execution.events)
            if scoped and not mixed and retained['expansion'] in selected.selected_handles:
                assert after == before  # Expansion alone grants/reads nothing.
            elif any(handle.startswith('native-corpus-search:') for handle in selected.selected_handles):
                assert not any(isinstance(event,NativeBodyReadObservedV1) for event in after[len(before):])
            else:
                reads = [event for event in after[len(before):] if isinstance(event, NativeBodyReadObservedV1)]
                assert len(reads) == 1 and reads[0].excerpt is not None
            with pytest.raises(ValueError):
                driver.native_sources.expand_selected((retained['expansion'] or 'native-corpus-expand:')+'forged')
            if retained['expansion'] and retained['expansion'] not in selected.selected_handles:
                with pytest.raises(ValueError):
                    driver.native_sources.expand_selected(retained['expansion'])
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
                return tuple(row for row in rows if row.handle.startswith('native-body:') and 'Session 9' in row.label)
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
