"""Plan parent orchestration: semantic decisions, unique reads, one writer."""
import asyncio
import json

from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from .agent_runtime import AgentRuntimeDescriptor
from .plan_jev_dispatch import request_budget
from .plan_jev_driver import PlanJevDriver
from .plan_jev_rules_runtime import PlanRulesRuntime
from .plan_jev_writer import PlanJevWriter


class PlanJevHarness:
    descriptor = AgentRuntimeDescriptor('buddy-plan-jev','generationengine','plan-jev-one-writer','graph')

    def __init__(self, *, decision_transport=None, writer_transport=None, decision_api_key=None, writer_api_key=None):
        self.decision_transport, self.writer_transport = decision_transport, writer_transport
        self.decision_api_key, self.writer_api_key = decision_api_key, writer_api_key
        self.calls = []
        self.output_limit_exceeded = False

    def configured_budget(self, request):
        if request.surface.surface_id != 'plan' or request.plan_context_policy is None:
            raise ValueError('Plan Jev requires a governed Plan question')
        return request_budget()

    def run_with_provider_authorization(self, *args, **kwargs):
        raise ValueError('Plan Jev requires its trusted parent orchestration')

    def execute(self, adapter, *, dialogue=()):
        self.calls=[]
        rules=PlanRulesRuntime(adapter,rules_capability(graph=True))
        driver=PlanJevDriver(adapter,dialogue=dialogue,rules=rules)
        writer=None
        try:
            proof=asyncio.run(driver.run(transport=self.decision_transport,api_key=self.decision_api_key))
            writer=PlanJevWriter(adapter,proof,rules)
            completed=asyncio.run(writer.run(transport=self.writer_transport,api_key=self.writer_api_key))
            adapter.turn=completed.envelope if isinstance(completed,MixedCompletedTurnV1) else completed
            return completed
        finally:
            self.calls=[*driver.calls,*([writer.call] if writer is not None and writer.call is not None else [])]
            self.output_limit_exceeded=writer.output_limit_exceeded if writer is not None else False
            if adapter.fence is not None:
                adapter.stop()

    def execute_response(self, adapter, *, owner, trace, dialogue=()):
        from .agent_turn_service import AgentTurnServiceError, _completed_turn_replay, _interrupt_policy_delivery
        span=trace.start_phase('runtime_dispatch')
        try:
            completed=self.execute(adapter,dialogue=dialogue)
        except BaseException as exc:
            trace.complete_phase(span,status='error')
            if adapter.fence is not None:
                current=adapter.fence.turn
                if current.status=='running': _interrupt_policy_delivery(adapter.service,current,
                    output_limit_exceeded=self.output_limit_exceeded)
            trace.finalize_and_log(status='error',model_calls=self.calls,observed_model_call_count=len(self.calls))
            if isinstance(exc,AgentTurnServiceError): raise
            raise AgentTurnServiceError('The Plan reply could not complete safely. No request was replayed.',
                code='plan_jev_delivery_failure',status_code=503) from exc
        trace.complete_phase(span)
        final=trace.finalize_and_log(status='ok',model_calls=self.calls,observed_model_call_count=len(self.calls),
            hermes_fields={'conversation_context':'structured'})
        response=_completed_turn_replay(adapter.request,owner=owner,turn=completed)
        payload=response.model_dump(mode='json',by_alias=True)
        payload['answer']['trace']=final
        if payload.get('plan_context') is not None: payload['plan_context']['delivery_replay']=False
        if payload.get('rules_context') is not None:
            for key in ('base_context','unclaimed_context'):
                if payload['rules_context'].get(key) is not None: payload['rules_context'][key]['delivery_replay']=False
        return type(response).model_validate_json(json.dumps(payload))
