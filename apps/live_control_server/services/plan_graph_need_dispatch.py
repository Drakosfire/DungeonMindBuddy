"""One request-owned Plan Graph-need decision through the actual SDK gate."""
from hashlib import sha256
from time import perf_counter
import logging
from uuid import UUID, uuid4

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_plan_graph_need import (
    NativePlanGraphNeedInputV1, prepare_decision, validate_wire,
)
from application_state.agent_conversation.native_retrieval import NativePlanGraphNeedAuthorizedV1
from application_state.agent_conversation.native_writer import json_container_count
from application_state.agent_conversation.plan_authoring import strict_json
from .plan_jev_dispatch import decision_client


class PlanGraphNeedDispatch:
    """Dispatch once; actual SDK callbacks own authorization and result admission."""
    def __init__(self, adapter, *, dialogue):
        from application_state.agent_conversation.native_context import NativePlanGraphQueryPendingV1
        self.adapter = adapter
        if adapter.fence is None:
            raise ValueError('Graph-need dispatch requires the actual claimed Plan turn')
        turn = adapter.fence.turn
        context = turn.graph_context_receipt
        if type(context.native_query) is not NativePlanGraphQueryPendingV1:
            raise ValueError('Graph-need dispatch requires its pending Plan receipt')
        self.parent = NativePlanGraphNeedInputV1(
            pending_query_sha256=t.canonical_sha256(context.native_query),
            admission_sha256=t.canonical_sha256(context.assembled_input),
            question=turn.graph_context_execution.policy.action.intent.message,
            dialogue=tuple(dialogue), current_work=adapter.work.plan_markdown)
        self.prepared = self.authorization = self.selection = None
        self.call = None

    async def authorize(self, prepared):
        from .agent_turn_service import _require_fresh_execution_append
        if self.prepared is not None or self.adapter.failure is not None:
            return False
        a = self.adapter
        validate_wire(self.parent, prepared.body)
        turn = a.fence.turn
        execution = turn.graph_context_execution
        role = execution.policy.provider_roles.controller
        auth = NativePlanGraphNeedAuthorizedV1(event_id=uuid4(), sequence=len(execution.events),
            provider_attempt_id=UUID(prepared.attempt_id), decision_request_id=uuid4(),
            parent_request_sha256=self.parent.digest, parent_json=self.parent.model_dump_json(by_alias=True),
            envelope_sha256=prepared.body_sha256, serializer_version='typesafe-sdk-json-v1',
            provider=role.provider, model=role.model, api_mode=role.api_mode,
            tool_schema_sha256=sha256(b'[]').hexdigest(), input_accounting_kind='conservative_upper_bound',
            input_estimator=turn.graph_context_receipt.assembled_input.tokenizer_name,
            input_tokens=len(prepared.body) + 64 * (1 + json_container_count(strict_json(prepared.body.decode()))),
            output_token_reserve=turn.graph_context_receipt.assembled_input.output_token_reserve,
            included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
            included_graph_event_ids=[], included_source_read_event_ids=[])
        a.turn = _require_fresh_execution_append(a.fence.append('_authorize_plan_graph_need', 'authorization', auth,
            prepared_request=prepared.body))
        a.last_provider_attempt_id = auth.provider_attempt_id
        a._capture_prepared_prompt({'provider': role.provider, 'model': role.model, 'apiMode': role.api_mode,
            'payloadJson': prepared.body.decode(), 'payloadSha256': prepared.body_sha256,
            'payloadUtf8Bytes': len(prepared.body)}, auth)
        self.prepared, self.authorization = prepared, auth
        return True

    async def record(self, event):
        if self.prepared is None or event.request != self.prepared:
            return False
        transition = {'sending': 'sdk_entered', 'known_not_sent': 'known_not_sent',
            'response_received': 'response_received', 'outcome_unknown': 'outcome_unknown'}.get(event.outcome)
        if transition is None:
            return False
        acknowledged = self.adapter.record_lifecycle({'transition': transition, 'statusCode': event.http_status,
            'runtimeApiRequestId': f'generationengine:{self.prepared.attempt_id}'},
            **({'opening_authorization': self.authorization} if transition == 'sdk_entered' else {}))
        if acknowledged and transition == 'sdk_entered':
            self.call = {'provider': self.authorization.provider, 'requested_model': self.authorization.model,
                'runtime_api_request_id': f'generationengine:{self.prepared.attempt_id}',
                'status': 'error', 'usage': {'status': 'unavailable'}}
        return acknowledged

    def acknowledge(self, result):
        from .agent_turn_service import _require_fresh_execution_append
        if self.prepared is None or self.authorization is None or self.selection is not None:
            raise ValueError('Graph-need result requires one actual authorized SDK dispatch')
        a = self.adapter
        a.turn = _require_fresh_execution_append(a.fence.append('_record_plan_graph_need_result', 'sdk_result', result,
            event_id=uuid4()))
        self.selection = a.turn.graph_context_execution.events[-1]
        return self.selection

    async def run(self, *, transport=None, api_key=None):
        trace = getattr(self.adapter, 'trace', None)
        client = decision_client(authorize=self.authorize, record=self.record, transport=transport, api_key=api_key,
            on_dispatch=getattr(trace, 'mark_first_jev_dispatch', None))
        started = perf_counter()
        try:
            result = await client.decide(prepare_decision(self.parent))
            if self.call is not None:
                counts = {'input_tokens': result.observation.input_tokens, 'output_tokens': result.observation.output_tokens}
                usage = {'status': 'reported' if any(v is not None for v in counts.values()) else 'unavailable', **counts}
                if all(v is not None for v in counts.values()):
                    usage['total_tokens'] = sum(counts.values())
                self.call.update(status='ok', response_model=result.observation.response_model, usage=usage)
            return self.acknowledge(result)
        finally:
            if self.call is not None:
                self.call['duration_ms'] = (perf_counter() - started) * 1000
                if self.adapter.context_capture is not None:
                    self.adapter.context_capture.provider_usage([self.call])
            await client.aclose()


def settle_graph_need(adapter, observed, *, prepare_graph):
    """Close or run one pinned query after its actual decision has settled.

    The supplied Graph owner must refresh current access before acquisition.
    Once a start is durable, an uncertain result is never silently repeated.
    """
    from .agent_turn_service import AgentTurnServiceError, _require_fresh_execution_append
    if observed.choice == 'uncertain':
        raise AgentTurnServiceError('The Graph requirement could not be determined safely.',
            code='plan_graph_need_uncertain', status_code=503, provider_dispatched=True)
    if observed.choice == 'no_graph':
        adapter.turn = _require_fresh_execution_append(adapter.fence.commit('_transition_plan_graph_need',
            action='close', event_id=uuid4()))
        adapter.native_query_context = adapter.native_query = None
        return
    if observed.choice != 'require_graph' or not callable(prepare_graph):
        raise ValueError('Graph acquisition requires the exact authorized decision and owner')
    adapter.turn = _require_fresh_execution_append(adapter.fence.commit('_transition_plan_graph_need',
        action='authorize', event_id=uuid4()))
    adapter.turn = _require_fresh_execution_append(adapter.fence.commit('_transition_plan_graph_need',
        action='start', event_id=uuid4()))
    try:
        context, query = prepare_graph()
        if context is not None and context.query != query:
            raise ValueError('Graph owner returned a different context and query')
    except Exception:
        # The owner may have entered Core before it failed. Retain uncertainty;
        # never silently repeat a potentially completed acquisition. If the
        # failure append also fails, preserve the original acquisition exception.
        try:
            adapter.turn = _require_fresh_execution_append(adapter.fence.commit('_transition_plan_graph_need',
                action='fail', event_id=uuid4(), reason='uncertain_owner_result'))
        except Exception:
            logging.getLogger(__name__).exception('Could not retain uncertain Plan Graph failure')
        raise
    adapter.turn = _require_fresh_execution_append(adapter.fence.commit('_transition_plan_graph_need',
        action='settle', event_id=uuid4(), query=query))
    adapter.native_query_context, adapter.native_query = context, query
