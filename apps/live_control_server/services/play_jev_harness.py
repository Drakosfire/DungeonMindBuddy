"""Play orchestration adopts native retrieval and the configured shared writer.

Run work remains immutable; this has no Plan destination or placement stage.
"""
import asyncio
import logging

from application_state.agent_conversation.rules_authority_policy import rules_capability
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from .agent_runtime import AgentRuntimeDescriptor
from .plan_jev_harness import PlanJevHarness
from .plan_jev_dispatch import request_budget
from .plan_jev_driver import PlanJevDriver
from .plan_jev_rules_runtime import PlanRulesRuntime
from .plan_jev_writer import PlanJevWriter


class PlayJevHarness(PlanJevHarness):
    descriptor=AgentRuntimeDescriptor('buddy-play-jev','generationengine','play-jev-one-writer','graph')

    def configured_budget(self,request):
        from .agent_turn_service import _governed_graph_turn
        if request.surface.surface_id!='play' or not _governed_graph_turn(request):
            raise ValueError('Play Jev requires the actual governed Run question')
        return request_budget()

    def execute(self,adapter,*,dialogue=(),retained_navigation=()):
        self.calls=[]
        rules=PlanRulesRuntime(adapter,rules_capability(graph=True))
        driver=writer=None
        failed=False
        try:
            driver=PlanJevDriver(adapter,dialogue=dialogue,rules=rules,retained_navigation=retained_navigation)
            proof=asyncio.run(driver.run(transport=self.decision_transport,api_key=self.decision_api_key))
            writer=PlanJevWriter(adapter,proof,rules)
            completed=asyncio.run(writer.run(transport=self.writer_transport,api_key=self.writer_api_key))
            adapter.turn=completed.envelope if isinstance(completed,MixedCompletedTurnV1) else completed
            return completed
        except BaseException:
            failed=True
            raise
        finally:
            self.calls=(driver.calls if driver is not None else [])+([writer.call] if writer is not None and writer.call is not None else [])
            self.output_limit_exceeded=writer.output_limit_exceeded if writer is not None else False
            if adapter.fence is not None:
                try:adapter.stop()
                except Exception:
                    if not failed:raise
                    logging.getLogger(__name__).exception('Play claim cleanup failed; preserving original failure')


def default_play_jev_runtime():
    return PlayJevHarness()
