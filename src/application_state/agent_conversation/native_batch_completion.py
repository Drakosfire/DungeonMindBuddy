"""APP-owned fulfillment of a controller's explicit prospective read plan.

This proves only the selected batch's successful reads, never answer sufficiency
or completeness of unselected World knowledge. It performs no IO or model call.
"""
from . import types as t
from .native_retrieval import NativeRetrievalSelectedV2, NativeReadBatchConcludedV1


def selected_read_closure(receipt, execution, selection_event_id, *, before_sequence=None):
    from .native_corpus import (
        initial_source_discovery_enabled, NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1,
        NativeDirectSourceAuthorizedV1, native_direct_source_handle, native_body_handle,
        native_full_document_handle, selected_batch_covering_reads,
    )
    from .native_plan_assertions import (
        NativeGraphQueryV4, NativePlanAssertionReadAuthorizedV1,
        NativePlanAssertionReadObservedV1, object_record_ids, object_selection_handle,
    )
    from .native_plan_statements import NativePlanStatementReadAuthorizedV1, NativePlanStatementReadObservedV1
    if not initial_source_discovery_enabled(execution):
        return None
    events = execution.events if before_sequence is None else execution.events[:before_sequence]
    selections = [e for e in events if isinstance(e, t.PlanJevRetrievalSelectionV1)]
    selection = selections[-1] if selections else None
    if (type(selection) is not NativeRetrievalSelectedV2 or selection.event_id != selection_event_id
            or selection.operation != 'select_candidates'
            or selection.post_read_plan != 'finish_if_selected_reads_succeed'):
        return None
    before, after = events[:selection.sequence], events[selection.sequence + 1:]
    if any(isinstance(e, (t.ProviderAttemptAuthorizedEventV1, NativeReadBatchConcludedV1)) for e in after):
        return None
    handles = tuple(selection.selected_handles)
    supported = ('native-object:', 'native-direct-source:', 'native-body:', 'native-full-document:')
    if not handles or any(not h.startswith(supported) for h in handles):
        return None  # Metadata/discovery/Rules/unknown choices still require review.
    reads = set()
    object_handles = tuple(h for h in handles if h.startswith('native-object:'))
    if object_handles:
        query = receipt.native_query
        if not isinstance(query, NativeGraphQueryV4):
            return None
        known = {object_selection_handle(query, m.entity_id) for m in query.object_matches}
        if not set(object_handles) <= known:
            return None
        expected_by_family = []
        for grant_type, observed_type, ids_field, assertion in (
            (NativePlanStatementReadAuthorizedV1, NativePlanStatementReadObservedV1, 'statement_ids', False),
            (NativePlanAssertionReadAuthorizedV1, NativePlanAssertionReadObservedV1, 'assertion_ids', True),
        ):
            attempted = {i for e in before if isinstance(e, grant_type) for i in getattr(e, ids_field)}
            expected = set(object_record_ids(query, object_handles, assertion=assertion, attempted=attempted))
            expected_by_family.append((assertion, attempted))
            fulfilled = set()
            for grant in after:
                if not isinstance(grant, grant_type):
                    continue
                if grant.provider_attempt_id != selection.controller_attempt_id or grant.query_sha256 != query.sha256:
                    return None
                observed = [e for e in after if isinstance(e, observed_type) and e.authorization_event_id == grant.event_id]
                if len(observed) != 1 or observed[0].status != 'complete':
                    return None
                fulfilled.update(getattr(grant, ids_field))
                reads.add(observed[0].event_id)
            if expected != fulfilled:
                return None
        for handle in object_handles:
            if not any(object_record_ids(query, (handle,), assertion=assertion, attempted=attempted)
                    for assertion, attempted in expected_by_family):
                return None  # An empty or already attempted target is not a new successful read.
    grants = [e for e in after if isinstance(e, (NativeBodyReadAuthorizedV1, NativeDirectSourceAuthorizedV1))]
    for handle in handles:
        if handle.startswith('native-object:'):
            continue
        matched = []
        for grant in grants:
            if grant.provider_attempt_id != selection.controller_attempt_id:
                return None
            if isinstance(grant, NativeDirectSourceAuthorizedV1):
                key = native_direct_source_handle(grant.authority, grant.source_artifact_id,
                    grant.source_revision_id, grant.content_sha256)
            else:
                key = (native_full_document_handle(grant.catalog_sha256) if grant.retrieval_kind == 'full_document'
                    else native_body_handle(grant.catalog_sha256, grant.section_id))
            if key == handle:
                matched.append(grant)
        if not matched and handle.startswith('native-body:'):
            covering = selected_batch_covering_reads(execution, selection, handle, before_sequence=before_sequence)
            if not covering:
                return None
            reads.update(covering)
            continue
        if len(matched) != 1:
            return None
        observations = [e for e in after if isinstance(e, NativeBodyReadObservedV1)
            and e.authorization_event_id == matched[0].event_id]
        if len(observations) != 1 or observations[0].excerpt is None:
            return None
        reads.add(observations[0].event_id)
    # No unused/pending read grant may be hidden by a successful subset.
    observed_grants = {e.authorization_event_id for e in after if isinstance(e,
        (NativeBodyReadObservedV1, NativePlanStatementReadObservedV1, NativePlanAssertionReadObservedV1))}
    if any(e.event_id not in observed_grants for e in after if isinstance(e,
            (NativeBodyReadAuthorizedV1, NativeDirectSourceAuthorizedV1,
             NativePlanStatementReadAuthorizedV1, NativePlanAssertionReadAuthorizedV1))):
        return None
    return tuple(sorted(reads, key=str)) if reads else None


def conclude_selected_batch(turn, *, event_id, selection_event_id):
    from .native_retrieval import owner
    receipt, execution = owner(turn)
    prior = next((e for e in execution.events if e.event_id == event_id), None)
    if prior is not None:
        if type(prior) is not NativeReadBatchConcludedV1 or prior.selection_event_id != selection_event_id:
            raise ValueError('Read-batch conclusion replay changed identity')
        return prior
    reads = selected_read_closure(receipt, execution, selection_event_id)
    if reads is None:
        raise ValueError('Selected read batch has no proven prospective completion')
    return NativeReadBatchConcludedV1(event_id=event_id, sequence=len(execution.events),
        selection_event_id=selection_event_id, read_event_ids=reads)
