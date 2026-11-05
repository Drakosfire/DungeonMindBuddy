"""One native host for exact author-selected reads on Build and Plan.

APP admits the human selection; DungeonMind owns membership, versions and bytes.
This adopts the former native Build branches, not the classic recovery executor.
"""
from uuid import uuid4
from application_state.agent_conversation.authored_graph_references import native_references, AuthoredSourceReferenceV1
from .native_graph_reads import read_authored_reference
from ..integrations.dungeonmind.native_corpus_source import read_authored_source


def capture_input(adapter):
    refs = native_references(adapter.fence.turn.graph_context_execution)
    if refs is not None and refs.references:
        adapter.turn, _ = adapter.fence.append('capture_native_authored_references', 'event_id', uuid4())


def acquire(adapter):
    from application_state.errors import ApplicationStateValidationError
    from .agent_turn_service import AgentTurnServiceError
    refs = native_references(adapter.fence.turn.graph_context_execution)
    for index, reference in enumerate(() if refs is None else refs.references):
        if isinstance(reference, AuthoredSourceReferenceV1):
            try:
                adapter.turn, _ = adapter.fence.append('observe_native_authored_source', 'event_id', uuid4(),
                    reference_index=index, materialize=lambda selected: read_authored_source(adapter.native_corpus_context, selected))
            except (ValueError, ApplicationStateValidationError) as exc:
                raise AgentTurnServiceError('The exact selected source or passage could not be read. Your request is retained; choose it again. No newer source was substituted.',
                    code='authored_source_unavailable', status_code=409, provider_dispatched=None) from exc
            continue
        adapter.turn, _ = adapter.fence.append('authorize_native_authored_reference', 'event_id', uuid4(), node_id=reference.node_id)
        grant = adapter.fence.turn.graph_context_execution.events[-1]
        adapter.turn, _ = adapter.fence.append('observe_native_authored_reference', 'event_id', uuid4(),
            authorization_event_id=grant.event_id, materialize=lambda admitted: read_authored_reference(
                adapter.native_query_context, admitted, adapter.native_query_context.principal))
