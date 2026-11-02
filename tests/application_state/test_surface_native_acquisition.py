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
from application_state.agent_conversation.native_plan_statements import selection_handle
from application_state.agent_conversation.native_plan_assertions import (
    selection_handle as assertion_handle,
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
    q = case.turn.graph_context_receipt.native_query
    return [
        RetrievalCandidate(
            handle=selection_handle(q, m),
            label=m.label,
            kind="Qualified source statement",
        )
        for m in q.matches
    ] + [
        RetrievalCandidate(
            handle=assertion_handle(q, m),
            label=m.label,
            kind="Reviewed Graph assertion",
        )
        for m in q.assertion_matches
    ]


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
            assert driver._native_statement_examined()
            assert driver._native_assertion_examined()

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

    def selected(case):
        return [
            c
            for c in record_candidates(case)
            if c.handle.startswith("native-statement:")
        ]

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
            driver._native_statement_examined()

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
            driver._read_native(
                "assertion", [m.assertion_id for m in result.assertion_matches]
            )
            assert driver.gaps == ["native_assertion_support_unavailable"]
            assert all(
                "unavailable" in c.kind for c in driver._native_assertion_examined()
            )

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
