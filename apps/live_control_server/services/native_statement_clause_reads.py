"""Authenticated historical native source-clause opening, never current-head fallback."""

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.native_statement_answer import (
    NativeStatementCompletionV1,
)
from .native_statement_answer_context import build_frame
from .agent_source_passages import SourcePassageOpenError
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from apps.live_control_server.models.native_statement_answers import (
    NativeStatementClauseReadV1,
)


def open_clause(*, world_id, turn_id, citation_index, principal, service=None):
    if (
        isinstance(citation_index, bool)
        or not isinstance(citation_index, int)
        or citation_index < 0
    ):
        raise SourcePassageOpenError("native_clause_selector_invalid", 422)
    turn = (service or AgentConversationService()).inspect_turn(
        world_id=world_id, turn_id=turn_id
    )
    from application_state.agent_conversation import types as t
    if isinstance(turn,MixedCompletedTurnV1):
        if turn.base_projection.kind != 'approved':
            raise SourcePassageOpenError('native_clause_completion_unavailable',404)
        turn=turn.base_projection.turn
    if isinstance(turn.graph_context_receipt, (t.PlanNativeContextReceiptV1,t.SurfaceNativeContextReceiptV1)):
        return _open_plan_clause(turn, world_id, turn_id, citation_index, principal)
    if (
        turn.world_id != world_id
        or turn.turn_id != turn_id
        or turn.status != "completed"
        or not isinstance(turn.completion, NativeStatementCompletionV1)
    ):
        raise SourcePassageOpenError("native_clause_completion_unavailable", 404)
    if citation_index >= len(turn.completion.native_clause_citations):
        raise SourcePassageOpenError("native_clause_not_found", 404)
    citation = turn.completion.native_clause_citations[citation_index]
    receipt = turn.graph_context_receipt
    try:
        # Core reauthorizes at the original exact R, not the current World head.
        current = build_frame(receipt.selection, principal)
        if current != receipt.frame:
            raise ValueError(
                "Pinned native context no longer admits the original complete support"
            )
        support = next(
            s for s in current.supports if s.statement_id == citation.statement_id
        )
        if (
            support.source_artifact_id != citation.source_artifact_id
            or support.source_revision_id != citation.source_revision_id
            or support.source_body_sha256 != citation.body_sha256
            or support.clause_start_byte != citation.start_byte
            or support.clause_end_byte != citation.end_byte
            or support.clause_sha256 != citation.clause_sha256
        ):
            raise ValueError("Native citation differs from original source clause")
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration) as exc:
        raise SourcePassageOpenError(
            "native_clause_access_or_bytes_unavailable", 409
        ) from exc
    return NativeStatementClauseReadV1(
        world_id=world_id,
        turn_id=str(turn_id),
        citation_index=citation_index,
        citation=citation,
        content=support.clause_text,
    )


def _reopen_record(context, grant, identity, principal, *, assertion):
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2
    from .native_graph_reads import read_authored_reference, read_selected
    if isinstance(grant, BuildAuthoredReferenceAuthorizedV2):
        support = read_authored_reference(context, grant, principal)
        reads = support.assertion_reads if assertion else support.statement_reads
        return next(read for read in reads if
            (read.assertion.assertion_id if assertion else read.support.statement_id) == identity)
    ids = 'assertion_ids' if assertion else 'statement_ids'
    reopened, unavailable = read_selected(context, grant.model_copy(update={ids: (identity,)}), principal)
    if unavailable or len(reopened) != 1:
        raise ValueError('Pinned native record no longer admits the original support')
    return reopened[0]


def _open_plan_clause(turn, world_id, turn_id, citation_index, principal):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_plan_statements import NativePlanStatementReadAuthorizedV1
    from .native_graph_reads import reopen_context
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2
    if (turn.world_id != world_id or turn.turn_id != turn_id or turn.status != 'completed'
            or not isinstance(turn.completion, (t.SurfaceEvidenceCompletionV6,t.SurfaceNativeCompletionV1))):
        raise SourcePassageOpenError('native_clause_completion_unavailable', 404)
    if citation_index >= len(turn.completion.native_clause_citations):
        raise SourcePassageOpenError('native_clause_not_found', 404)
    citation = turn.completion.native_clause_citations[citation_index]
    try:
        receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
        from application_state.agent_conversation.native_plan_statements import selected_read_records
        original = next((event, read) for event, read in selected_read_records(execution)
            if read.support.statement_id == citation.statement_id)
        observed, read = original
        grant = next(e for e in execution.events if isinstance(e, (NativePlanStatementReadAuthorizedV1, BuildAuthoredReferenceAuthorizedV2))
            and e.event_id == observed.authorization_event_id)
        context = reopen_context(receipt.native_query, principal)
        reopened = _reopen_record(context, grant, citation.statement_id, principal, assertion=False)
        if reopened != read:
            raise ValueError('Pinned native clause no longer admits the original support')
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration) as exc:
        raise SourcePassageOpenError('native_clause_access_or_bytes_unavailable', 409) from exc
    return NativeStatementClauseReadV1(world_id=world_id, turn_id=str(turn_id),
        citation_index=citation_index, citation=citation, content=read.support.clause_text)


def open_assertion_source(*, world_id, turn_id, citation_index, principal, service=None):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1
    from .native_graph_reads import reopen_context
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2
    from apps.live_control_server.models.native_statement_answers import NativeAssertionSourceReadV1
    if isinstance(citation_index, bool) or not isinstance(citation_index, int) or citation_index < 0:
        raise SourcePassageOpenError('native_assertion_selector_invalid', 422)
    turn = (service or AgentConversationService()).inspect_turn(world_id=world_id, turn_id=turn_id)
    if isinstance(turn,MixedCompletedTurnV1):
        if turn.base_projection.kind != 'approved':
            raise SourcePassageOpenError('native_assertion_completion_unavailable',404)
        turn=turn.base_projection.turn
    if (turn.world_id != world_id or turn.turn_id != turn_id or turn.status != 'completed'
            or not isinstance(turn.completion, (t.SurfaceEvidenceCompletionV7,t.SurfaceNativeCompletionV1))):
        raise SourcePassageOpenError('native_assertion_completion_unavailable', 404)
    if citation_index >= len(turn.completion.native_assertion_citations):
        raise SourcePassageOpenError('native_assertion_citation_not_found', 404)
    citation = turn.completion.native_assertion_citations[citation_index]
    try:
        from application_state.agent_conversation.native_plan_assertions import selected_read_records
        observed, read = next((event, read) for event, read in selected_read_records(turn.graph_context_execution)
            if event.event_id == citation.read_event_id and read.assertion.assertion_id == citation.assertion_id)
        grant = next(e for e in turn.graph_context_execution.events
            if isinstance(e, (NativePlanAssertionReadAuthorizedV1, BuildAuthoredReferenceAuthorizedV2)) and e.event_id == observed.authorization_event_id)
        context = reopen_context(turn.graph_context_receipt.native_query, principal)
        reopened = _reopen_record(context, grant, citation.assertion_id, principal, assertion=True)
        if reopened != read:
            raise ValueError('Pinned assertion no longer admits its exact original support')
        span = next(s for s in read.spans if s.evidence_ref_id == citation.evidence_ref_id)
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration) as exc:
        raise SourcePassageOpenError('native_assertion_access_or_bytes_unavailable', 409) from exc
    return NativeAssertionSourceReadV1(world_id=world_id, turn_id=str(turn_id), citation_index=citation_index,
        citation=citation, content=span.text)
