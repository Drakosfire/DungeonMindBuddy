"""Buddy parent-owned Jev Harness: unique reads, one writer, no retry fallback."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from uuid import UUID

from generationengine import GenerationClient
from generationengine.types import (
    BinaryDecisionQuestion,
    ChoiceDecisionQuestion,
    DecisionRequest,
)
from generationengine.decision_dispatch import DecisionDispatchGate
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
from generationengine.providers.openai_text import OpenAITextProvider
from generationengine.text_dispatch import TextDispatchGate
from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.build_authoring import completion_for_proposal
from application_state.build_proposal.types import BuildProposalOrigin
from apps.live_control_server.models.build_document_proposal import (
    BuildDocumentProposalRequest,
)
from .agent_runtime import AgentRuntimeDescriptor
from . import build_document_proposal as proposal_owner
from . import build_jev_dispatch as decision_policy
from . import build_jev_writer as writer_policy
from .build_jev_driver import AcquisitionBinding, digest, sdk_answers
from .build_jev_transitions import (
    AcquisitionIntent, DecisionIntent, Disposition, FrontierDisposition, FRONTIER_POLICY,
)


@dataclass(frozen=True)
class ProposalWriterProjection:
    expected_json: str
    event_sequence: int
    prior_provider_attempt_id: str
    authoring: bool = True
    source_only: bool = False
    source_event_ids: tuple = ()

    def kwargs(self):
        return json.loads(self.expected_json)


class BuildJevHarness:
    descriptor = AgentRuntimeDescriptor(
        "buddy-jev", "generationengine", "jev-one-writer", "graph"
    )

    def __init__(self, *, decision_transport=None, writer_transport=None):
        self.decision_transport, self.writer_transport = (
            decision_transport,
            writer_transport,
        )

    def run_with_provider_authorization(self, *args, **kwargs):
        raise ValueError("Jev requires the trusted Buddy parent adapter")

    @staticmethod
    def budget(request):
        budget = decision_policy.request_budget()
        cap = request.build_write_capability
        from .build_initial_packet_codec import CODEC
        budget["buildJevActions"] = dict(
            phase_input_policy=decision_policy.PHASE_POLICY,
            frontier_policy=FRONTIER_POLICY,
            initial_packet_codec=CODEC,
            controller_input_policy=decision_policy.CONTINUATION_POLICY,
            driver_schema="dmb_build_jev_actions_v1",
            action_capability_sha256=digest(cap.model_dump(mode="json"))
            if cap
            else None,
            allowed_surface_operations=["answer_from_sources"]
            + (["propose_build_insertion"] if cap else []),
        )
        return budget

    def execute_response(self, adapter, *, owner, trace):
        from .agent_turn_service import (
            AgentTurnServiceError,
            _completed_turn_replay,
            _interrupt_policy_delivery,
        )
        from apps.live_control_server.models.agent_turn import (
            AgentBuildGraphTurnResponseV1,
        )

        span = trace.start_phase("runtime_dispatch")
        try:
            completed = self.execute(adapter)
        except Exception as exc:
            trace.complete_phase(span, status="error")
            if adapter.turn is not None and adapter.turn.status == "running":
                _interrupt_policy_delivery(adapter.service, adapter.turn)
            trace.finalize_and_log(
                status="error",
                model_calls=self.calls,
                observed_model_call_count=len(self.calls),
            )
            if isinstance(exc, AgentTurnServiceError):
                raise
            raise AgentTurnServiceError(
                "The Jev conversation could not complete safely. No request was replayed.",
                code="build_jev_delivery_failure",
                status_code=503,
            ) from exc
        trace.complete_phase(span)
        final_trace = trace.finalize_and_log(
            status="ok",
            model_calls=self.calls,
            observed_model_call_count=len(self.calls),
            hermes_fields={"conversation_context": "structured"},
        )
        response = _completed_turn_replay(adapter.request, owner=owner, turn=completed)
        payload = response.model_dump(mode="json", by_alias=True)
        payload["primary_work"]["revision_used"] = adapter.work.build_source.revision
        payload["answer"]["trace"] = final_trace
        payload["knowledge_context"]["delivery_replay"] = False
        return AgentBuildGraphTurnResponseV1.model_validate(payload)

    def execute(self, adapter):
        self.calls, self.timings, self._inflight = [], [], {}
        self.adapter = adapter
        driver = adapter.create_build_jev_driver(with_actions=True)
        adapter.build_frozen_history = driver._interaction["history"]
        adapter.build_history_for_inclusion = tuple(
            (UUID(item["turn_id"]), item["assistant"])
            for item in driver._interaction["history"]
        )
        try:
            asyncio.run(self._decide(adapter, driver))
            if driver.operation == "propose_build_insertion":
                return self._proposal(adapter, driver)
            while not isinstance(driver.step, Disposition):
                if isinstance(driver.step, DecisionIntent):
                    asyncio.run(self._decide(adapter, driver))
                elif isinstance(driver.step, AcquisitionIntent):
                    self._acquire(adapter, driver)
                else:
                    raise ValueError("Unsupported Jev step")
            terminal = driver.step
            if terminal.status == "refused":
                raise ValueError(f"Jev refused delivery: {terminal.reason}")
            adapter.build_retrieval_disposition = terminal.writer_summary() if isinstance(terminal, FrontierDisposition) else {
                "status": terminal.status,
                "reason": terminal.reason,
                "relevant_ids": list(terminal.relevant_ids),
            }
            graph, sources, sections = driver._material()
            if sources:
                staged = adapter.stage_build_source_writer(
                    graph_payloads=graph,
                    source_read_event_ids=sources,
                    section_read_ids=sections,
                )
            else:
                staged = adapter.stage_build_writer(
                    graph_payloads=graph, section_read_ids=sections
                )
            result = asyncio.run(self._write(adapter, staged))
            if (terminal.status in {"insufficient_evidence", "unresolved_conflict"}
                    or (isinstance(terminal, FrontierDisposition)
                        and terminal.coverage_status != "catalog_exhausted")):
                candidate = json.loads(result.text)
                if candidate.get("answer_context_status") in {
                    "source_grounded",
                    "graph_grounded",
                }:
                    raise ValueError(
                        "Writer claimed full support despite unresolved retrieval"
                    )
            return adapter.complete_build_writer(result)
        finally:
            adapter.stop()

    def _record_observation(self, observation, elapsed, phase, *, status="ok"):
        self.timings.append(dict(phase=phase, elapsed_ms=elapsed))
        known = all(
            type(observation.get(k)) is int for k in ("input_tokens", "output_tokens")
        )
        call = dict(
            provider=observation.get("provider"),
            requested_model=observation.get("resolved_model"),
            response_model=observation.get("response_model")
            or observation.get("resolved_model"),
            status=status,
            duration_ms=elapsed,
            api_duration=elapsed / 1000,
            usage={**observation, "status": "reported" if known else "unavailable"},
            inference_observation=observation,
        )
        index = self._inflight.pop(phase, None)
        if index is None:
            self.calls.append(call)
        else:
            self.calls[index] = call
        if self.adapter.context_capture:
            self.adapter.context_capture.provider_usage([call])

    def _entered(self, event, phase):
        if event.outcome == "sending":
            self._inflight[phase] = len(self.calls)
            self.calls.append(
                dict(
                    provider=event.request.provider,
                    requested_model=event.request.model,
                    status="error",
                    usage={"status": "unavailable"},
                    outcome="unknown",
                )
            )

    def _failed(self, exc, started, phase):
        if phase not in self._inflight:
            return  # A pre-dispatch veto is not an entered provider call.
        observation = getattr(exc, "observation", None)
        if observation is not None:
            observation = observation.model_dump(mode="json")
        else:
            row = self.calls[self._inflight[phase]]
            observation = dict(
                provider=row["provider"], resolved_model=row["requested_model"]
            )
        self._record_observation(
            observation, (time.perf_counter() - started) * 1000, phase, status="error"
        )

    def _observe(self, result, started, phase):
        self._record_observation(
            result.observation.model_dump(mode="json"),
            (time.perf_counter() - started) * 1000,
            phase,
        )

    async def _decide(self, adapter, driver):
        plan, intent = driver.stage(), driver.step

        async def authorize(prepared):
            return driver.authorize(prepared)

        async def record(event):
            acknowledged = adapter.record_prepared_build_decision(event)
            if acknowledged:
                self._entered(event, "controller")
            return acknowledged

        provider = TypeSafeDecisionProvider(
            dispatch_gate=DecisionDispatchGate(authorize, record),
            transport=self.decision_transport,
        )
        client = GenerationClient(decision_providers={"typesafe": provider})
        started = time.perf_counter()
        try:
            result = await client.decide(
                DecisionRequest(
                    provider=decision_policy.PROVIDER,
                    model=decision_policy.MODEL,
                    state=plan.state(),
                    questions=tuple(
                        BinaryDecisionQuestion(name=q.name, question=q.question)
                        if q.kind == "binary"
                        else ChoiceDecisionQuestion(
                            name=q.name, question=q.question, options=q.options
                        )
                        for q in intent.questions
                    ),
                    max_transport_retries=0,
                )
            )
            self._observe(result, started, "controller")
            driver.accept_decision(decision_policy.MODEL, sdk_answers(result))
        except Exception as exc:
            self._failed(exc, started, "controller")
            raise
        finally:
            await client.aclose()

    @staticmethod
    def _acquire(adapter, driver):
        bindings, graph_reads = {}, {}
        needed = set()
        for action in driver.step.actions:
            args = driver.action_arguments(action.id)
            if action.kind == "saved_build_section":
                event = json.loads(adapter.read_build_section(**args))
                bindings[action.id] = AcquisitionBinding(
                    section_read_id=event["read_id"]
                )
                continue
            payloads, tokens = [], set()
            while True:
                reply = adapter.broker_graph_operation(
                    {"toolName": "expand_graph_retrieval", "arguments": args}
                )
                if adapter.failure:
                    raise adapter.failure
                raw = json.loads(reply["resultJson"])
                if raw.get("schema") == "dmb_world_graph_retrieval_error_v1":
                    raise ValueError("Native selected observation read was refused")
                payloads.append(reply["resultJson"])
                token = raw.get("detailPageToken") or raw.get("nextPageToken")
                if not token:
                    break
                if token in tokens:
                    raise ValueError("Repeated Graph presentation page")
                tokens.add(token)
                args = {**args, "resultPageToken": token}
            exposures = adapter._tool_presentation().inclusion(
                "expand_graph_retrieval", payloads
            )
            anchors = {
                anchor["anchorId"]
                for exposure in exposures
                for anchor in json.loads(
                    adapter.operation_payloads[exposure.event_id]
                ).get("sourceAnchors", [])
            }
            needed.update(anchors)
            graph_reads[action.id] = tuple(payloads), anchors
        prior = {
            r.anchor_id
            for event in adapter._broker_execution().events
            if isinstance(event, ledger.ValidatedSourceReadEventV2)
            for r in event.receipts
        }
        missing = sorted(needed - prior)
        while missing:
            execution = adapter._broker_execution()
            remaining = execution.policy.max_source_read_chars - ledger.source_read_character_usage(
                execution.policy, execution.events)
            if remaining <= 0:
                raise ValueError("Source character allowance is exhausted")
            max_chars = min(execution.policy.max_chars_per_source_read, remaining)
            count = min(8, len(missing), remaining // max_chars)
            batch, missing = missing[:count], missing[count:]
            reply = adapter.broker_source_read(
                {
                    "toolName": "read_graph_source",
                    "arguments": {
                        "retrievalSessionId": adapter.bootstrap.retrieval_session.id,
                        "anchorIds": batch,
                        "maxChars": max_chars,
                    },
                }
            )
            if adapter.failure:
                raise adapter.failure
            if (
                json.loads(reply["resultJson"]).get("schema")
                == "dmb_world_graph_retrieval_error_v1"
            ):
                raise ValueError("Native source read was refused")
        for aid, (payloads, anchors) in graph_reads.items():
            events = tuple(
                str(e.event_id)
                for e in adapter._broker_execution().events
                if isinstance(e, ledger.ValidatedSourceReadEventV2)
                and any(r.anchor_id in anchors for r in e.receipts)
            )
            bindings[aid] = AcquisitionBinding(
                graph_payloads=payloads, source_event_ids=events
            )
        driver.accept_acquisition(bindings)

    async def _write(self, adapter, staged):
        async def authorize(prepared):
            return adapter.authorize_prepared_build_writer(prepared)

        async def record(event):
            acknowledged = adapter.record_prepared_build_writer(event)
            if acknowledged:
                self._entered(event, "writer")
            return acknowledged

        provider = OpenAITextProvider(
            dispatch_gate=TextDispatchGate(authorize, record),
            transport=self.writer_transport,
        )
        client = GenerationClient(text_providers={"openai": provider})
        started = time.perf_counter()
        try:
            result = await client.generate_text(writer_policy.text_request(staged))
            self._observe(result, started, "writer")
            return result
        except Exception as exc:
            self._failed(exc, started, "writer")
            raise
        finally:
            await client.aclose()

    def _proposal(self, adapter, driver):
        capability = adapter.request.build_write_capability
        if capability is None or len(adapter.request.message) > 4000:
            raise ValueError(
                "The selected proposal has no valid captured instruction/capability"
            )
        selection = driver.selection
        if (
            digest(capability.model_dump(mode="json")) != selection.capability_sha256
            or digest({"instruction": adapter.request.message})
            != selection.arguments_sha256
        ):
            raise ValueError("Captured capability or selected tool instruction changed")
        origin = BuildProposalOrigin(
            client_turn_id=UUID(adapter.request.turn_id),
            durable_turn_id=adapter.turn.turn_id,
            turn_attempt=adapter.turn.attempt,
            broker_operation_id=selection.broker_operation_id,
            arguments_sha256=selection.arguments_sha256,
        )
        request = BuildDocumentProposalRequest(
            **capability.model_dump(exclude={"instruction", "origin"}),
            instruction=adapter.request.message,
            origin=origin,
        )
        history = driver._interaction["history"]
        expected = proposal_owner.prepare_writer_request(
            request, frozen_history=history
        )
        adapter._build_writer_projection = ProposalWriterProjection(
            json.dumps(
                expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
            len(adapter._broker_execution().events),
            str(adapter.last_provider_attempt_id),
        )

        async def authorize(prepared):
            return adapter.authorize_prepared_build_writer(prepared)

        async def record(event):
            acknowledged = adapter.record_prepared_build_writer(event)
            if acknowledged:
                self._entered(event, "writer")
            return acknowledged

        started = time.perf_counter()
        try:
            action = asyncio.run(
                proposal_owner.compose_with_writer(
                    request,
                    TextDispatchGate(authorize, record),
                    transport=self.writer_transport,
                    frozen_history=history,
                )
            )
        except Exception as exc:
            self._failed(exc, started, "writer")
            raise
        if action.state != "proposed":
            raise ValueError("Proposal is unresolved; no regeneration or second writer")
        if (
            adapter.producing_provider_attempt_id
            != action.authorization.provider_attempt_id
        ):
            raise ValueError("Proposal result differs from acknowledged writer")
        if action.observation:
            self._record_observation(
                action.observation, (time.perf_counter() - started) * 1000, "writer"
            )
        completion = completion_for_proposal(action, adapter.turn.graph_context_receipt)
        if adapter.context_capture:
            adapter.context_capture.answer_draft(
                action.raw_response,
                producing_provider_attempt_id=action.authorization.provider_attempt_id,
            )
            adapter.context_capture.answer_context(ledger.BUILD_PROPOSAL_READY_TEXT)
        turn = adapter.stop()
        adapter.turn = adapter.service.complete_turn(
            ledger.TurnResult(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                assistant_text=ledger.BUILD_PROPOSAL_READY_TEXT,
                completion=completion,
                producing_provider_attempt_id=action.authorization.provider_attempt_id,
                claim_graph_event_ids={},
            )
        )
        return adapter.turn
