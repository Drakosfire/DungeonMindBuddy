"""Compact Plan wire addresses, never new source authority or source matching."""
import re

from .rules_authority_types import canonical_sha256

FRAME_SCHEMA = 'dmb_plan_jev_writer_frame_v4'


def _scope(turn):
    return canonical_sha256(dict(world_id=turn.world_id,
        conversation_id=str(turn.conversation_id),turn_id=str(turn.turn_id),
        submission_id=str(turn.idempotency_key),attempt=turn.attempt,
        context_receipt_sha256=turn.graph_context_execution.context_receipt_sha256))[:12]


def source_selector(turn, event, receipt_index=0):
    from . import types as t
    events = turn.graph_context_execution.events
    if (type(receipt_index) is not int or receipt_index < 0
            or event.sequence >= len(events) or events[event.sequence] != event):
        raise ValueError('Plan source selector lacks its exact current event')
    if isinstance(event,t.SOURCE_PASSAGE_EVENTS):
        from .surface_source_answer import eligible
        if receipt_index >= len(event.receipts) or not eligible(event.receipts[receipt_index]):
            raise ValueError('Plan source selector lacks an eligible receipt')
        prefix='p'
    elif isinstance(event,t.NativeSourceSectionObservedV1) and event.outcome=='complete' and receipt_index==0:
        # This typed event owns exactly one descriptor/text, never a section batch.
        prefix='n'
    else:
        raise ValueError('Plan source selector lacks a successful source read')
    return f'{prefix}-{_scope(turn)}-{event.sequence}-{receipt_index}'


def resolve_selector(turn, authorization, selector, prefix):
    """Resolve only a literal current-frame row; callers enforce row membership.

    A decodable address alone is not an output capability. Only the producing
    supports reconstructed from actual frozen rows may reach the answer parser.
    """
    from . import types as t
    if not isinstance(authorization,t.PlanJevWriterAuthorizedV1) or prefix not in {'p','n'}:
        raise ValueError('Plan selectors require their own exact writer')
    match=re.fullmatch(r'([pn])-([0-9a-f]{12})-(0|[1-9][0-9]*)-(0|[1-9][0-9]*)',selector) if isinstance(selector,str) else None
    if match is None or match[1]!=prefix or match[2]!=_scope(turn):
        raise ValueError('Plan source selector has wrong kind, scope or shape')
    sequence,index=int(match[3]),int(match[4])
    events=turn.graph_context_execution.events
    if sequence >= len(events):raise ValueError('Plan source selector event is unavailable')
    event=events[sequence]
    if source_selector(turn,event,index)!=selector:
        raise ValueError('Plan source selector changed its exact address')
    if prefix=='p':
        if not isinstance(event,t.SOURCE_PASSAGE_EVENTS) or event.event_id not in t.included_passage_event_ids(authorization):
            raise ValueError('Plan source selector lacks authorized passage inclusion')
        return event,event.receipts[index]
    if not isinstance(event,t.NativeSourceSectionObservedV1):
        raise ValueError('Plan section selector lacks its exact section event')
    return event,event
