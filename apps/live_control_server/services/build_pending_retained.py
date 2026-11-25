"""Host entry into the existing retained conversation capture owner."""
from uuid import uuid4
from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
from application_state.agent_conversation.build_source_free import pending_retained_work


def admit_pending_conversation(adapter):
    if type(adapter._broker_receipt()) is not BuildPendingContextReceiptV1:
        return False
    execution = adapter._broker_execution()
    if pending_retained_work(execution) is None:
        return False
    prior = [event for event in execution.events if type(event) is ledger.BuildPriorBodyEvidenceAdmittedV3]
    if len(prior) > 1 or not callable(adapter.pending_build_access) or adapter.fence is None:
        raise ValueError('Pending conversation requires one current App claim and retained owner')
    turn, fresh = adapter.fence.commit('admit_pending_build_prior_body_evidence',
        event_id=prior[0].event_id if prior else uuid4(), authorize_current_access=adapter.pending_build_access)
    if fresh is not (not prior):
        raise ValueError('Pending retained capture has an indeterminate disposition')
    adapter.turn = turn
    return True
