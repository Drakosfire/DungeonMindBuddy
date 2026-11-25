"""Exact prepared source ownership for the distinct pending Build protocol.

These are historical identity/binding checks. Actual current principal, claim,
selected read and public Core access checks remain with locked read admission.
"""
from . import types as ledger
from .build_source_free import effective_pending_source
from .native_context import BuildPendingContextReceiptV1


def prepared_pending_source(receipt, execution):
    if type(receipt) is not BuildPendingContextReceiptV1:
        raise ValueError('Prepared pending source requires its actual Build receipt')
    source = effective_pending_source(receipt, execution)
    if source is None:
        raise ValueError('Pending observation has no admitted native source settlement')
    return source


def pending_native_owner(turn):
    """Reconstruct actual stored work before returning its prepared source owner."""
    from .native_execution import BuildPendingExecutionV1, BuildPendingExecutionPolicyV1, NativeBuildActionV1
    if (type(turn) is not ledger.Turn or turn.status != 'running'
            or type(turn.graph_context_receipt) is not BuildPendingContextReceiptV1
            or type(turn.graph_context_execution) is not BuildPendingExecutionV1
            or type(turn.graph_context_execution.policy) is not BuildPendingExecutionPolicyV1
            or type(turn.graph_context_execution.policy.action) is not NativeBuildActionV1):
        raise ValueError('Pending native retrieval requires its actual running Build owner')
    current = ledger.Turn.model_validate_json(turn.model_dump_json(by_alias=True))
    receipt, execution = current.graph_context_receipt, current.graph_context_execution
    prepared_pending_source(receipt, execution)
    return receipt, execution


def read_selection(turn):
    """Use the actual pending controller; preserve existing legacy delegates."""
    if type(turn.graph_context_receipt) is BuildPendingContextReceiptV1:
        from .native_retrieval import current_selection
    else:
        from .plan_jev_decision import current_selection
    return current_selection(turn)


def read_source_authority(receipt, execution):
    """Resolve the prepared pending source; legacy owners keep their own fields."""
    if type(receipt) is BuildPendingContextReceiptV1:
        return prepared_pending_source(receipt, execution)[0]
    return receipt.source_authority
