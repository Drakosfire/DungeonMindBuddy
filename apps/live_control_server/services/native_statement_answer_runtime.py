"""One guarded GE writer for preloaded native context; no Graph/Rules impersonation."""

import asyncio
from time import perf_counter
from hashlib import sha256
from uuid import UUID, uuid4

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_statement_input import (
    NativeStatementContextReceiptV1,
    NativeStatementWriterPolicyV1,
    NativeStatementInputEventV1,
    canonical,
    digest,
    validate_request,
    native_input_tokens,
)
from application_state.agent_conversation.native_statement_answer import (
    INSTRUCTIONS,
    OUTPUT_SCHEMA,
    answer_text,
    normalize_output,
)
from .plan_jev_writer import PlanWriterProvider
from .native_statement_answer_context import build_frame


class NativeStatementWriter:
    def __init__(self, service, turn):
        from .agent_turn_service import _ClaimFence

        self.service = service
        self.fence = _ClaimFence(service, turn)
        self.prepared = None
        self.authorization = None
        self.model_calls = []

    @property
    def turn(self):
        return self.fence.turn

    def append(self, events):
        _, fresh = self.fence.append("append_native_statement_events", "events", events)
        if not fresh:
            raise ValueError("Native dispatch requires a newly persisted event")

    async def authorize(self, prepared):
        from generationengine.text_dispatch import PreparedTextDispatch

        if self.prepared is not None:
            return False
        policy = self.turn.graph_context_execution.policy
        if (
            not isinstance(prepared, PreparedTextDispatch)
            or (
                prepared.provider,
                prepared.model,
                prepared.api_mode,
                prepared.method,
                prepared.url,
            )
            != (
                policy.provider,
                policy.model,
                policy.api_mode,
                "POST",
                "https://api.openai.com/v1/responses",
            )
            or len(prepared.body) != prepared.body_size
            or sha256(prepared.body).hexdigest() != prepared.body_sha256
        ):
            raise ValueError("Native prepared transport identity differs")
        raw = prepared.body.decode()
        validate_request(self.turn.graph_context_receipt, policy, raw)
        sequence = len(self.turn.graph_context_execution.events)
        auth = t.ProviderAttemptAuthorizedEventV1(
            kind="provider_attempt_authorized",
            event_id=uuid4(),
            sequence=sequence,
            provider_attempt_id=UUID(prepared.attempt_id),
            envelope_sha256=prepared.body_sha256,
            serializer_version="openai-sdk-json-v1",
            provider=policy.provider,
            model=policy.model,
            api_mode=policy.api_mode,
            tool_schema_sha256=sha256(b"[]").hexdigest(),
            input_accounting_kind="conservative_upper_bound",
            input_estimator="utf8_json_bytes_plus_64_per_node_v1",
            input_tokens=native_input_tokens(raw),
            output_token_reserve=policy.output_token_reserve,
            included_assertion_ids=[],
            included_relationship_ids=[],
            included_evidence_ref_ids=[],
            included_graph_event_ids=[],
        )
        inclusion = NativeStatementInputEventV1(
            event_id=uuid4(),
            sequence=sequence + 1,
            provider_attempt_id=auth.provider_attempt_id,
            envelope_sha256=auth.envelope_sha256,
            prepared_request_json=raw,
        )
        self.append([auth, inclusion])
        self.prepared, self.authorization = prepared, auth
        return True

    async def lifecycle(self, event):
        if self.prepared is None or event.request != self.prepared:
            return False
        outcome = {
            "sending": "sdk_entered",
            "known_not_sent": "known_not_sent",
            "response_received": "response_received",
            "outcome_unknown": "outcome_unknown",
        }[event.outcome]
        self.append(
            [
                t.ProviderOutcomeEventV1(
                    kind="provider_outcome",
                    event_id=uuid4(),
                    sequence=len(self.turn.graph_context_execution.events),
                    provider_attempt_id=self.authorization.provider_attempt_id,
                    outcome=outcome,
                    status_code=event.http_status,
                )
            ]
        )
        return True

    async def run(self, *, transport=None):
        from generationengine import GenerationClient, TextRequest
        from generationengine.text_dispatch import TextDispatchGate

        receipt, policy = (
            self.turn.graph_context_receipt,
            self.turn.graph_context_execution.policy,
        )
        messages = [
            {
                "role": "user",
                "content": canonical(
                    {
                        "question": receipt.user_text,
                        "native_statement_context": receipt.frame.model_dump(
                            mode="json", by_alias=True
                        ),
                    }
                ),
            }
        ]
        provider = PlanWriterProvider(
            dispatch_gate=TextDispatchGate(self.authorize, self.lifecycle),
            transport=transport,
        )
        client = GenerationClient(text_providers={"openai": provider})
        started = perf_counter()
        result = await client.generate_structured(
            TextRequest(
                provider="openai",
                model=policy.model,
                user_prompt=canonical(messages),
                system_prompt=INSTRUCTIONS,
                temperature=None,
                reasoning_effort="none",
                max_output_tokens=policy.output_token_reserve,
                json_schema=OUTPUT_SCHEMA,
                schema_name="native_statement_answer",
                max_conformance_retries=0,
                max_transport_retries=0,
            )
        )
        observation = result.observation
        self.model_calls.append(
            {
                "provider": "openai",
                "model": policy.model,
                "requested_model": policy.model,
                "response_model": observation.response_model,
                "status": "ok",
                "duration_ms": (perf_counter() - started) * 1000,
                "usage": {
                    "status": "reported",
                    "input_tokens": observation.input_tokens,
                    "output_tokens": observation.output_tokens,
                },
            }
        )
        response = provider.actual_response
        if (
            response is None
            or response.status != "completed"
            or response.model != policy.model
        ):
            raise ValueError("Native writer lacks an exact completed SDK reply")
        selected = provider.consume_selected_text(response)
        if (
            result.text != selected
            or not selected
            or result.observation.state.value != "completed"
            or result.observation.retry_count != 0
            or result.observation.provider_attempt_count != 1
        ):
            raise ValueError(
                "Native writer output does not match its acknowledged SDK reply"
            )
        for item in response.output:
            if item.type == "reasoning":
                continue
            if (
                item.type != "message"
                or item.role != "assistant"
                or item.status != "completed"
                or any(part.type != "output_text" for part in item.content)
            ):
                raise ValueError(
                    "Native writer returned a tool, refusal or incomplete message"
                )
        self.append(
            [
                t.NativeStatementOutputCapturedV1(
                    event_id=uuid4(),
                    sequence=len(self.turn.graph_context_execution.events),
                    provider_attempt_id=self.authorization.provider_attempt_id,
                    envelope_sha256=self.authorization.envelope_sha256,
                    response_sha256=sha256(selected.encode()).hexdigest(),
                    raw_output_json=selected,
                )
            ]
        )
        completion = normalize_output(receipt, self.authorization, selected)
        _, renewal_error = self.fence.stop()
        if renewal_error is not None:
            raise renewal_error
        return self.service.complete_turn(
            t.CitedSourceTurnResult(
                world_id=self.turn.world_id,
                conversation_id=self.turn.conversation_id,
                turn_id=self.turn.turn_id,
                expected_revision=self.turn.revision,
                assistant_text=answer_text(completion),
                completion=completion,
                producing_provider_attempt_id=self.authorization.provider_attempt_id,
                claim_graph_event_ids={},
                writer_request_json=self.prepared.body.decode(),
                raw_provider_output_json=selected,
            )
        )


def execute(
    request,
    *,
    service,
    principal,
    owner,
    work,
    submitted_intent,
    existing_turn,
    trace,
    transport=None,
):
    from . import agent_turn_service as turns

    if service is None or principal is None or not principal.subject:
        raise turns.AgentTurnServiceError(
            "Native question requires authenticated durable conversation.",
            code="native_statement_auth_required",
            status_code=403,
            provider_dispatched=False,
        )
    if work is not None:
        basis = work.content_basis
        locator = request.primary_work
        if (
            locator is None
            or basis is None
            or work.world_id != request.owner_scope.world_id
            or basis.world_id != request.owner_scope.world_id
            or basis.document_id != locator.object_id
            or basis.object_revision != locator.expected_revision
            or basis.revision_n != locator.expected_revision_n
            or basis.content_sha256 != locator.expected_content_sha256
            or work.changed_since_expected
        ):
            raise turns.AgentTurnServiceError(
                "Native question Plan basis changed.",
                code="native_statement_plan_changed",
                status_code=409,
                provider_dispatched=False,
            )
    if existing_turn is None:
        try:
            frame = build_frame(request.native_statement_selection, principal)
            provenance = turns._conversation_provenance(
                request, world_id=frame.managed_world_id, work=work
            )
            provenance = provenance.model_copy(
                update={
                    "supporting_work": [
                        *provenance.supporting_work,
                        t.HistoricalReference(
                            resolution="resolved",
                            kind="native_statement_context_v1",
                            object_id=frame.subject_id,
                            revision=frame.revision_id,
                            content_sha256=digest(frame),
                        ),
                    ]
                }
            )
            payload = {
                "schema": "dmb_native_statement_context_receipt_v1",
                "selection": request.native_statement_selection.model_dump(
                    mode="json", by_alias=True
                ),
                "frame": frame.model_dump(mode="json", by_alias=True),
                "user_text": request.message,
                "provenance_sha256": digest(provenance),
            }
            receipt = NativeStatementContextReceiptV1.model_validate(
                payload | {"context_receipt_sha256": digest(payload)}
            )
            budget = turns._policy_request_budget()
            policy = NativeStatementWriterPolicyV1(
                model=budget["model"],
                output_token_reserve=budget["outputReserveTokens"],
                context_limit_tokens=budget["contextLimitTokens"],
            )
            execution = t.NativeStatementExecutionV1(
                context_receipt_sha256=receipt.context_receipt_sha256,
                policy=policy,
                execution_policy_sha256=digest(policy),
                events=[],
            )
            existing_turn = turns._accept_world_turn(
                service,
                request,
                world_id=frame.managed_world_id,
                provenance=provenance,
                submitted_intent=submitted_intent,
                graph_context_receipt=receipt,
                graph_context_execution=execution,
            )
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise turns.AgentTurnServiceError(
                "Native statement context is unavailable or differs from selection.",
                code="native_statement_context_unavailable",
                status_code=409,
                provider_dispatched=False,
            ) from exc
    if not isinstance(
        existing_turn.graph_context_execution, t.NativeStatementExecutionV1
    ):
        raise turns.AgentTurnServiceError(
            "Original turn has no matching native capability.",
            code="native_statement_context_changed",
            status_code=409,
            provider_dispatched=False,
        )
    # Never dispatch again after any prior authorization, including an unknown outcome.
    if existing_turn.graph_context_execution.events:
        raise turns.AgentTurnServiceError(
            "The original native writer attempt already entered execution; inspect its recorded outcome.",
            code="native_statement_attempt_retained",
            status_code=409,
            provider_dispatched=False,
        )
    claim = service.claim_turn(
        existing_turn.world_id,
        existing_turn.conversation_id,
        existing_turn.turn_id,
        expected_revision=existing_turn.revision,
        lease_seconds=120,
    )
    if claim.disposition == "completed":
        return turns._completed_turn_replay(
            request, owner=owner, turn=claim.turn, trace_builder=trace
        )
    if claim.disposition == "pending":
        raise turns.AgentTurnServiceError(
            "Native question is already running.",
            code="turn_already_running",
            status_code=409,
        )
    trace.bind_durable_turn(claim.turn)
    writer = NativeStatementWriter(service, claim.turn)
    try:
        completed = asyncio.run(writer.run(transport=transport))
    except Exception as exc:
        writer.fence.stop()
        try:
            service.fail_turn(
                t.TurnFailure(
                    world_id=writer.turn.world_id,
                    conversation_id=writer.turn.conversation_id,
                    turn_id=writer.turn.turn_id,
                    expected_revision=writer.turn.revision,
                    failure_code="native_statement_writer_interrupted",
                ),
                interrupted=True,
            )
        except Exception as persist_exc:
            raise turns.AgentTurnServiceError(
                "Native writer outcome could not be durably confirmed.",
                code="turn_persistence_indeterminate",
                status_code=503,
            ) from persist_exc
        raise turns.AgentTurnServiceError(
            "Native writer stopped; its original attempt remains recorded.",
            code="native_statement_writer_interrupted",
            status_code=502,
        ) from exc
    return turns._completed_turn_replay(
        request,
        owner=owner,
        turn=completed,
        trace_builder=trace,
        native_model_calls=writer.model_calls,
    )
