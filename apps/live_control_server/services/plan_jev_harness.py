"""Plan parent orchestration: semantic decisions, unique reads, one writer."""
import asyncio
import json

from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from .agent_runtime import AgentRuntimeDescriptor
from .plan_jev_dispatch import PlanJevDispatch, request_budget
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

    def execute(self, adapter, *, dialogue=(), retained_navigation=()):
        from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
        from .agent_turn_service import AgentTurnServiceError
        self.calls = []
        page_title = next((line[2:].strip() for line in adapter.work.plan_markdown.splitlines() if line.startswith('# ') and line[2:].strip()), 'Current Plan')
        semantic = PlanJevDispatch.requested_work(adapter, page_title=page_title, dialogue=dialogue)
        rules = PlanRulesRuntime(adapter, rules_capability(graph=True))
        driver = writer = None
        try:
            selected, _ = asyncio.run(semantic.run(transport=self.decision_transport, api_key=self.decision_api_key))
            if selected == 'different_destination':
                raise AgentTurnServiceError('This request needs another page or object. The request is retained; choose that destination before generating.',
                    code='plan_authoring_destination_unavailable', status_code=409)
            if selected == 'write_current_page':
                capture = adapter.request.plan_authoring_capture
                if capture is None:
                    raise AgentTurnServiceError('The requested Plan writing has no captured page location. The request is retained; select a location on the Plan and try again.',
                        code='plan_authoring_target_unavailable', status_code=409)
                try:
                    action, _ = adapter.service.reserve_plan_authoring_action(capture=capture,
                        turn_id=adapter.fence.turn.turn_id, expected_revision=adapter.fence.turn.revision)
                except (ApplicationStateConflictError, ApplicationStateValidationError) as exc:
                    raise AgentTurnServiceError('The Plan or conversation changed before writing could start. The request is retained; review the current page location before trying again.',
                        code='plan_authoring_target_changed', status_code=409) from exc
                rules.authoring = (action, capture)
            driver = PlanJevDriver(adapter, dialogue=dialogue, rules=rules, retained_navigation=retained_navigation)
            proof = asyncio.run(driver.run(transport=self.decision_transport, api_key=self.decision_api_key))
            writer = PlanJevWriter(adapter, proof, rules)
            completed = asyncio.run(writer.run(transport=self.writer_transport, api_key=self.writer_api_key))
            adapter.turn = completed.envelope if isinstance(completed, MixedCompletedTurnV1) else completed
            return completed
        except BaseException as exc:
            if writer is not None and writer.target_changed:
                raise AgentTurnServiceError('The Plan or conversation changed during preparation, before writing was sent. The request is retained; review the current page location before trying again.',
                    code='plan_authoring_target_changed', status_code=409) from exc
            raise
        finally:
            self.calls = ([semantic.call] if semantic.call is not None else []) + (driver.calls if driver is not None else []) + ([writer.call] if writer is not None and writer.call is not None else [])
            self.output_limit_exceeded = writer.output_limit_exceeded if writer is not None else False
            if adapter.fence is not None:
                adapter.stop()

    def execute_response(self, adapter, *, owner, trace, dialogue=(), retained_navigation=()):
        from .agent_turn_service import AgentTurnServiceError, _completed_turn_replay, _interrupt_policy_delivery
        span=trace.start_phase('runtime_dispatch')
        try:
            completed=self.execute(adapter,dialogue=dialogue,retained_navigation=retained_navigation)
        except BaseException as exc:
            trace.complete_phase(span,status='error')
            if adapter.fence is not None:
                current=adapter.fence.turn
                if current.status=='running': _interrupt_policy_delivery(adapter.service,current,
                    output_limit_exceeded=self.output_limit_exceeded,
                    failure_code_override=exc.code if isinstance(exc,AgentTurnServiceError) and exc.code in {
                        "plan_authoring_target_unavailable", "plan_authoring_target_changed", "plan_authoring_destination_unavailable"} else None)
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
        # The durable projection deliberately omits live work on a replay. A
        # fresh response must carry the committed basis resolved for this turn.
        payload['primary_work']['content_basis']=adapter.work.content_basis.model_dump(mode='json')
        if payload.get('plan_context') is not None: payload['plan_context']['delivery_replay']=False
        if payload.get('rules_context') is not None:
            for key in ('base_context','unclaimed_context'):
                if payload['rules_context'].get(key) is not None: payload['rules_context'][key]['delivery_replay']=False
        return type(response).model_validate_json(json.dumps(payload))


def default_plan_jev_runtime():
    """Ordinary governed Plan factory; the parent owns dispatch authorization."""
    return PlanJevHarness()
