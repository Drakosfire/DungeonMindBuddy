"""Parent-owned native Plan/Play Rules broker and mixed-output owner.

This adapter joins the native SDK capture to the durable Rules ledger. It is
constructed only by the trusted governed-turn parent; it is not a route flag.
"""
from __future__ import annotations

import json
from uuid import UUID, uuid4

from application_state.agent_conversation.rules_authority_completion import (
    NativeRulesMixedTurnResultV1,
)
from application_state.agent_conversation.rules_authority_events import (
    RulesNativeProviderOutcomeV1,
    RulesOutputRefV1,
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
    RulesProviderOutcomeV1,
    RulesQueryObservedV1,
    RulesToolAuthorizedV1,
    normalized_question,
)
from application_state.agent_conversation.rules_authority_policy import (
    LookupRulesArguments,
    RulesCapabilityV1,
    rules_capability,
    rules_submission_authorization_id,
)
from application_state.agent_conversation.rules_authority_types import (
    RulesScopeV1,
)
from application_state.agent_conversation.types import submitted_turn_intent_fingerprint_v2
from . import rules_lookup_broker as broker


def _provider_lookup_arguments(raw_arguments, scope, authorization):
    """Validate provider wire arguments against the durable authorized query."""
    from application_state.agent_conversation.rules_authority_input import _unique_object

    if not isinstance(raw_arguments, str):
        raise ValueError("Native Rules provider arguments are not JSON text")
    parsed = json.loads(
        raw_arguments,
        object_pairs_hook=_unique_object,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(
            f"invalid JSON constant: {value}"
        )),
    )
    arguments = LookupRulesArguments.model_validate(parsed)
    if (arguments.ruleset_id != scope.ruleset_id
            or normalized_question(arguments.question) != authorization.normalized_question):
        raise ValueError("Native Rules provider arguments differ from the authorized query")
    return arguments


def _captured_lookup_call(reply, call_id: str, arguments) -> str:
    """Require the parent IPC operation to match one exact captured SDK call."""
    if (reply is None or reply.status != "tool_calls" or not isinstance(call_id, str)
            or not call_id or len(call_id) > 128):
        raise ValueError("Rules call has no exact captured provider tool reply")
    calls = [item for item in reply.tool_calls if item.call_id == call_id]
    if len(calls) != 1 or calls[0].name != "lookup_rules":
        raise ValueError("Rules call ID does not match one captured lookup_rules call")
    from application_state.agent_conversation.rules_authority_input import _unique_object
    raw_args = json.loads(calls[0].arguments_json, object_pairs_hook=_unique_object)
    parsed = LookupRulesArguments.model_validate(arguments)
    if raw_args != parsed.model_dump(mode="json", by_alias=True):
        raise ValueError("Rules call arguments differ from the captured provider reply")
    return call_id


class NativeRulesRuntime:
    """Durable lookup, exact provider inclusion, capture and atomic acceptance."""

    def __init__(self, adapter, capability: RulesCapabilityV1):
        from .agent_turn_service import _turn_idempotency_key

        cap = RulesCapabilityV1.model_validate(capability)
        if cap != rules_capability(graph=True) or adapter._is_build_turn():
            raise ValueError("Native Rules requires the exact Plan/Play Graph capability")
        if adapter.rules_runtime is not None or adapter.fence is None:
            raise ValueError("Native Rules requires one current claimed provider attempt")
        # Provider authorization has already admitted and claimed this logical
        # turn. Its persisted conversation is the authoritative parent scope;
        # do not perform a second lookup/create race while binding the tool.
        turn = adapter.turn
        if turn is None or turn.world_id != adapter.world_id:
            raise ValueError("Native Rules requires the current admitted World turn")
        if adapter.expected_conversation_id not in (None, turn.conversation_id):
            raise ValueError("Rules conversation changed before provider preparation")
        adapter.expected_conversation_id = turn.conversation_id
        self.adapter, self.capability = adapter, cap
        self.conversation_id = turn.conversation_id
        self.intent_sha = submitted_turn_intent_fingerprint_v2(adapter.submitted_intent)
        self.idempotency_key = _turn_idempotency_key(adapter.world_id, adapter.request.turn_id)
        self.authorization_id = rules_submission_authorization_id(
            world_id=adapter.world_id, conversation_id=self.conversation_id,
            idempotency_key=self.idempotency_key,
            submitted_intent_sha256=self.intent_sha, capability=cap,
        )
        self.record = None
        self.last_provider = None
        self.last_prepared_json = None
        self.last_reply = None
        self._seen_api_request_ids: set[str] = set()

    def _bind(self):
        a = self.adapter
        if a.fence is None:
            raise ValueError("Native Rules requires the actual current Turn claim")
        turn = a.fence.renewer._turn
        if (turn.world_id != a.world_id or turn.conversation_id != self.conversation_id
                or turn.idempotency_key != self.idempotency_key
                or turn.submitted_intent_fingerprint_v2 != self.intent_sha):
            raise ValueError("Native Rules scope differs from the locked logical submission")
        if self.record is None:
            cap = self.capability
            scope = RulesScopeV1(
                schema="dmb_rules_scope_v1", execution_id=uuid4(), world_id=turn.world_id,
                conversation_id=turn.conversation_id, turn_id=turn.turn_id,
                product_attempt=turn.attempt, ruleset_id=cap.ruleset_id,
                corpus_sha256=cap.corpus_sha256, authorization_id=self.authorization_id,
                capability_policy_sha256=cap.policy_sha256, budget=cap.budget,
            )
            self.record = a.service.begin_rules_execution(scope, expected_turn_revision=turn.revision)
        elif (self.record.execution.scope.turn_id != turn.turn_id
                or self.record.execution.scope.product_attempt != turn.attempt):
            raise ValueError("Native Rules execution crossed a product attempt")
        from application_state.agent_conversation.types import (
            PlanWorldGraphContextReceiptV1,
            PlanWorldGraphExecutionV3,
            PlayWorldGraphContextReceiptV1,
            PlayWorldGraphExecutionV1,
        )
        receipt, graph = turn.graph_context_receipt, turn.graph_context_execution
        if not (
            isinstance(receipt, PlanWorldGraphContextReceiptV1)
            and isinstance(graph, PlanWorldGraphExecutionV3)
            or isinstance(receipt, PlayWorldGraphContextReceiptV1)
            and isinstance(graph, PlayWorldGraphExecutionV1)
        ):
            raise ValueError("Native Rules requires the current native Plan or Play Graph pair")
        if receipt.context_receipt_sha256 != graph.context_receipt_sha256:
            raise ValueError("Native Rules Graph receipt and execution differ")
        return turn

    def _actual_lookup_material(self, body):
        """Derive exact prior lookup packets from this provider input."""
        calls, outputs = {}, {}
        if isinstance(body.get("input"), list) and "messages" not in body:
            for item in body["input"]:
                if not isinstance(item, dict):
                    continue
                kind, call_id = item.get("type"), item.get("call_id")
                if kind == "function_call":
                    if not isinstance(call_id, str) or not call_id or call_id in calls:
                        raise ValueError("Provider input has ambiguous function call IDs")
                    calls[call_id] = (item.get("name"), item.get("arguments"))
                elif kind == "function_call_output":
                    if call_id in outputs or not isinstance(call_id, str):
                        raise ValueError("Provider input has ambiguous function outputs")
                    outputs[call_id] = item.get("output")
        elif isinstance(body.get("messages"), list) and "input" not in body:
            for message in body["messages"]:
                if not isinstance(message, dict):
                    continue
                if message.get("role") == "assistant":
                    for call in message.get("tool_calls") or []:
                        if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                            raise ValueError("Provider input has malformed tool calls")
                        call_id = call.get("id")
                        if not isinstance(call_id, str) or not call_id or call_id in calls:
                            raise ValueError("Provider input has ambiguous tool call IDs")
                        calls[call_id] = (
                            call["function"].get("name"), call["function"].get("arguments")
                        )
                elif message.get("role") == "tool":
                    call_id = message.get("tool_call_id")
                    if not isinstance(call_id, str) or call_id in outputs:
                        raise ValueError("Provider input has ambiguous tool results")
                    outputs[call_id] = message.get("content")
        else:
            raise ValueError("Native Rules provider input has an unknown wire shape")

        from application_state.agent_conversation.rules_authority_runtime import _replay
        matched, support_by_id = [], {}
        for call_id, raw in outputs.items():
            call = calls.get(call_id)
            if call is None or call[0] != "lookup_rules":
                continue
            if not isinstance(raw, str):
                raise ValueError("Native Rules output is not text")
            auths = [e for e in self.record.execution.events
                     if isinstance(e, RulesToolAuthorizedV1) and e.call_id == call_id]
            observations = [e for e in self.record.execution.events
                            if isinstance(e, RulesQueryObservedV1) and e.call_id == call_id]
            if len(auths) != 1 or len(observations) != 1:
                raise ValueError("Native Rules output has no unique durable lookup")
            _provider_lookup_arguments(call[1], self.record.execution.scope, auths[0])
            expected = _replay(self.record.execution, auths[0], observations[0]).raw_output
            if raw != expected:
                raise ValueError("Native Rules output differs from its durable canonical packet")
            matched.append(RulesOutputRefV1(call_id=call_id,
                packet_sha256=observations[0].packet_sha256))
            emitted = set(observations[0].emitted_support_ids)
            support_by_id.update({ref.support_id: ref for ref in observations[0].support_refs
                                  if ref.support_id in emitted})
        return tuple(matched), tuple(support_by_id[key] for key in sorted(support_by_id, key=str))

    def authorize(self, view):
        a = self.adapter
        with a.fence.renewer._lock:
            self._bind()
            body = json.loads(view["payloadJson"])
            outputs, refs = self._actual_lookup_material(body)
            execution = self.record.execution
            attempt = a.last_provider_attempt_id
            if not isinstance(attempt, UUID):
                raise ValueError("Native Rules has no parent-authorized provider attempt")
            event = RulesProviderAuthorizedV1(
                kind="provider_authorized", event_id=uuid4(), sequence=len(execution.events),
                execution_id=execution.scope.execution_id, provider_attempt_id=attempt,
                request_envelope_sha256=view["payloadSha256"], matched_outputs=outputs,
                declared_support_refs=refs,
            )
            self.record = a.service.append_rules_provider_event(
                execution.scope, expected_turn_revision=a.fence.renewer._turn.revision,
                expected_ledger_revision=self.record.revision, event=event,
                prepared_request_json=view["payloadJson"],
            )
            included = RulesProviderIncludedV1(
                kind="provider_included", event_id=uuid4(),
                sequence=len(self.record.execution.events), execution_id=execution.scope.execution_id,
                provider_attempt_id=attempt, request_envelope_sha256=view["payloadSha256"],
                matched_outputs=outputs, support_refs=refs,
            )
            self.record = a.service.append_rules_provider_event(
                execution.scope, expected_turn_revision=a.fence.renewer._turn.revision,
                expected_ledger_revision=self.record.revision, event=included,
                prepared_request_json=view["payloadJson"],
            )
            self.last_provider = {**view, "providerAttemptId": str(attempt)}
            self.last_prepared_json = view["payloadJson"]
            self.last_reply = None
        return True

    def capture_reply(self, reply):
        """Seal every exact native result before acknowledging the child hook."""
        try:
            a = self.adapter
            view = self.last_provider
            if (view is None or reply.authorization_id != str(self.authorization_id)
                    or reply.request_sha256 != view["payloadSha256"]
                    or reply.provider != view["provider"] or reply.model != view["model"]
                    or reply.api_mode != view["apiMode"]
                    or reply.api_request_id in self._seen_api_request_ids):
                return False
            turn = self._bind()
            execution = self.record.execution
            sequence = len(execution.events)
            if reply.status == "answered":
                event = RulesNativeProviderOutcomeV1.from_capture(
                    reply, event_id=uuid4(), sequence=sequence,
                    execution_id=execution.scope.execution_id,
                    provider_attempt_id=a.last_provider_attempt_id,
                    request_envelope_sha256=view["payloadSha256"],
                )
            else:
                event = RulesProviderOutcomeV1(
                    kind="provider_outcome", event_id=uuid4(), sequence=sequence,
                    execution_id=execution.scope.execution_id,
                    provider_attempt_id=a.last_provider_attempt_id,
                    request_envelope_sha256=view["payloadSha256"], status=reply.status,
                )
            self.record = a.service.append_rules_provider_event(
                execution.scope, expected_turn_revision=turn.revision,
                expected_ledger_revision=self.record.revision, event=event,
            )
            self._seen_api_request_ids.add(reply.api_request_id)
            self.last_reply = reply
            return reply.status != "failed"
        except Exception:
            return False

    def outcome(self, transition):
        """Persist lifecycle outcomes the native SDK could not capture directly."""
        if self.record is None or transition == "sdk_entered":
            return
        a = self.adapter
        with a.fence.renewer._lock:
            events = self.record.execution.events
            authorizations = [
                event for event in events
                if isinstance(event, RulesProviderAuthorizedV1)
            ]
            if not authorizations or authorizations[-1].provider_attempt_id != a.last_provider_attempt_id:
                return
            auth = authorizations[-1]
            if any(
                isinstance(event, RulesProviderOutcomeV1)
                and event.provider_attempt_id == auth.provider_attempt_id
                for event in events
            ):
                return
            # The generic transport lifecycle cannot distinguish a final
            # answer from an intermediate tool-call response. Exact SDK reply
            # capture owns answered/tool_calls/failed; this records only
            # terminal states that did not yield a capturable reply.
            status = {
                "known_not_sent": "failed",
                "outcome_unknown": "unknown",
            }.get(transition)
            if status is None:
                return
            event = RulesProviderOutcomeV1(
                kind="provider_outcome", event_id=uuid4(),
                sequence=len(events), execution_id=self.record.execution.scope.execution_id,
                provider_attempt_id=auth.provider_attempt_id,
                request_envelope_sha256=auth.request_envelope_sha256,
                status=status,
            )
            self.record = a.service.append_rules_provider_event(
                self.record.execution.scope,
                expected_turn_revision=a.fence.renewer._turn.revision,
                expected_ledger_revision=self.record.revision,
                event=event,
            )

    def lookup(self, message):
        """Persist tool authorization, perform the bounded local read, then reply."""
        a = self.adapter
        arguments = LookupRulesArguments.model_validate(message.get("arguments"))
        call_id = _captured_lookup_call(
            self.last_reply, message.get("modelCallId"), arguments
        )
        with a.fence.renewer._lock:
            turn = self._bind()
            event = broker.prepare_authorization(self.record.execution, call_id, arguments)
            self.record = a.service.authorize_rules_lookup(
                self.record.execution.scope, expected_turn_revision=turn.revision,
                expected_ledger_revision=self.record.revision, event=event,
            )
            from application_state.agent_conversation.rules_authority_input import _unique_object
            # Reconstruct only supports actually present in the exact preceding input.
            body = json.loads(self.last_prepared_json, object_pairs_hook=_unique_object)
            present = self._actual_lookup_material(body)[1]
            delivery = a.service.execute_rules_lookup(
                self.record.execution.scope, expected_turn_revision=turn.revision,
                call_id=call_id,
                local_reader=lambda current: broker.prepare_lookup(
                    current, call_id, arguments, current_context_refs=present
                ),
            )
            self.record = delivery.record
            self.last_reply = None
            return {"resultJson": delivery.prepared.raw_output, "retrievalSession": None}

    def complete(self, turn, reply):
        if self.record is None:
            return None
        from application_state.agent_conversation.native_rules_output import (
            NativeRulesOutputProofV1,
            normalize_native_mixed_output,
        )
        from application_state.agent_conversation.types import TurnResult
        if (reply is None or reply.status != "answered" or self.last_provider is None
                or self.last_provider["providerAttemptId"] != str(self.adapter.producing_provider_attempt_id)):
            raise ValueError("Native Rules completion has no actual final provider reply")
        proof = NativeRulesOutputProofV1.from_capture(
            reply, prepared_request_json=self.last_prepared_json,
            rules_execution_id=self.record.execution.scope.execution_id,
            producing_provider_attempt_id=self.adapter.producing_provider_attempt_id,
        )
        # Reuse the turn-local immutable result bytes; no Graph reacquisition.
        auth = next(event for event in turn.graph_context_execution.events
            if getattr(event, "provider_attempt_id", None) == proof.producing_provider_attempt_id
            and hasattr(event, "included_graph_event_ids"))
        from application_state.agent_conversation.source_writer_output import strict_json
        candidate = strict_json(reply.text)
        if not isinstance(candidate, dict):
            raise ValueError("Native final answer is not an object")
        base = candidate.get("base_output") if candidate.get("schema") == "dmb_rules_mixed_answer_v1" else candidate
        if base is not None and not isinstance(base, dict):
            raise ValueError("Native base answer is not an object")
        segments = base.get("answer_segments", []) if base is not None else []
        if not isinstance(segments, list):
            raise ValueError("Native base segments are not a list")
        targets = {(item.get("target_kind"), item.get("target_id"))
            for item in segments if isinstance(item, dict) and item.get("kind") == "graph_claim"
            and item.get("target_kind") in {"assertion", "relationship"}
            and isinstance(item.get("target_id"), str)}
        operations = {event.event_id: event for event in turn.graph_context_execution.events
            if hasattr(event, "assertion_ids") and hasattr(event, "relationship_ids")}
        packets = {}
        for event_id in auth.included_graph_event_ids:
            event = operations.get(event_id)
            if event is None or not any(
                    target in (event.assertion_ids if kind == "assertion" else event.relationship_ids)
                    for kind, target in targets):
                continue
            raw = self.adapter.operation_payloads.get(event_id)
            if raw is not None:
                value = json.loads(raw)
                packets[event_id] = json.dumps({key: item for key, item in value.items()
                    if key not in {"retrievalSessionId", "addedClaimIds", "claimLedger"}},
                    ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        proof = proof.model_copy(update={"graph_packets": packets})
        if self.record.execution.budget_use.calls == 0:
            from application_state.agent_conversation.native_rules_output import normalize_unused_native_output
            completion, bindings, text = normalize_unused_native_output(
                turn, self.record.execution, proof)
            return self.adapter.service.complete_native_base_turn(TurnResult(
                world_id=turn.world_id, conversation_id=turn.conversation_id,
                turn_id=turn.turn_id, expected_revision=turn.revision,
                assistant_text=text, completion=completion,
                producing_provider_attempt_id=self.adapter.producing_provider_attempt_id,
                claim_graph_event_ids=bindings,
            ), output_proof=proof, expected_rules_revision=self.record.revision)
        normalized = normalize_native_mixed_output(
            turn, turn.graph_context_execution, self.record.execution, proof, reply,
            graph_support=self.adapter.build_claim_evidence.get(self.adapter.producing_provider_attempt_id),
        )
        base = None
        if normalized.base_completion is not None:
            base_text = "\n".join(item.text for item in normalized.base_completion.answer_segments)
            base = TurnResult(
                world_id=turn.world_id, conversation_id=turn.conversation_id,
                turn_id=turn.turn_id, expected_revision=turn.revision,
                assistant_text=base_text, completion=normalized.base_completion,
                producing_provider_attempt_id=self.adapter.producing_provider_attempt_id,
                claim_graph_event_ids=normalized.claim_graph_event_ids,
            )
        result = NativeRulesMixedTurnResultV1(
            schema="dmb_native_rules_mixed_turn_result_v1", scope=self.record.execution.scope,
            expected_turn_revision=turn.revision, expected_rules_revision=self.record.revision,
            assistant_text=normalized.assistant_text, composition=normalized.composition,
            producing_provider_attempt_id=self.adapter.producing_provider_attempt_id,
            base_result=base, output_proof=proof,
        )
        return self.adapter.service.complete_mixed_turn(result)
