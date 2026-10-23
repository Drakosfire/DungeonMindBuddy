"""Trusted Build parent for Rules capability; no route/registry activation.

The Graph parent still proves each complete prepared request. This owner binds
its Rules projection to the actual moving claim and seals it before SDK entry.
"""
from __future__ import annotations

from hashlib import sha256
import json
from uuid import UUID, uuid4

from application_state.agent_conversation.rules_authority_build_input import RulesBuildProjectionV1, RulesBuildOperationV1
from application_state.agent_conversation.rules_authority_completion import BuildRulesMixedTurnResultV1, RulesCitedSourceTurnResultV1
from application_state.agent_conversation.rules_authority_events import (
    RulesBuildProviderAuthorizedV1, RulesBuildProviderIncludedV1,
    RulesProviderAuthorizedV1, RulesProviderOutcomeV1, RulesOutputRefV1,
)
from application_state.agent_conversation.rules_authority_output import POLICY, BuildRulesOutputProofV1, parse_answer
from application_state.agent_conversation.rules_authority_policy import RulesCapabilityV1, rules_capability, rules_submission_authorization_id
from application_state.agent_conversation.rules_authority_types import RulesScopeV1
from application_state.agent_conversation.types import submitted_turn_intent_fingerprint_v2
from . import rules_lookup_broker as broker

QUERY_CHOICE = "rules_query"


class RulesBuildRuntime:
    def __init__(self, adapter, capability: RulesCapabilityV1):
        from .agent_turn_service import _active_or_create_conversation, _turn_idempotency_key
        capability = RulesCapabilityV1.model_validate(capability)
        if capability != rules_capability(graph=True) or not adapter._is_build_turn():
            raise ValueError("Build Rules requires its exact Graph+Rules capability")
        if adapter.fence is not None or getattr(adapter, "_build_jev_driver", None) is not None:
            raise ValueError("Rules capability must be frozen before first preparation")
        if (adapter.budget.get("buildJevActions") or {}).get("source_writer_output_policy") != "cited_facts_host_limitations_v1":
            raise ValueError("Build Rules requires the current cited writer profile")
        active = _active_or_create_conversation(adapter.service, world_id=adapter.world_id, turn_id=adapter.request.turn_id)
        expected = adapter.expected_conversation_id
        if expected is not None and expected != active.conversation_id:
            raise ValueError("Rules conversation changed before first preparation")
        if adapter.turn is not None and adapter.turn.conversation_id != active.conversation_id:
            raise ValueError("Rules retry differs from the current conversation")
        adapter.expected_conversation_id = active.conversation_id
        self.adapter, self.capability = adapter, capability
        self.conversation_id = active.conversation_id
        self.intent_sha = submitted_turn_intent_fingerprint_v2(adapter.submitted_intent)
        self.idempotency_key = _turn_idempotency_key(adapter.world_id, adapter.request.turn_id)
        self.authorization_id = rules_submission_authorization_id(world_id=adapter.world_id,
            conversation_id=self.conversation_id, idempotency_key=self.idempotency_key,
            submitted_intent_sha256=self.intent_sha, capability=capability)
        self.record = None
        self.active = True
        self.outputs = []
        self._selection = None
        question = adapter.request.message
        self.offers = (question,) if 0 < len(question) <= 800 and question.strip() else tuple(
            part for part in question.split("\n\n") if 0 < len(part) <= 800 and part.strip())[:4]

    def _bind(self):
        a = self.adapter
        if a.fence is None:
            raise ValueError("Rules requires the actual current Turn claim")
        turn = a.fence.renewer._turn
        if (turn.world_id != a.world_id or turn.conversation_id != self.conversation_id
                or turn.idempotency_key != self.idempotency_key or turn.submitted_intent_fingerprint_v2 != self.intent_sha):
            raise ValueError("Rules actual locked Turn differs from its logical submission")
        if self.record is None:
            cap = self.capability
            scope = RulesScopeV1(schema="dmb_rules_scope_v1", execution_id=uuid4(), world_id=turn.world_id,
                conversation_id=turn.conversation_id, turn_id=turn.turn_id, product_attempt=turn.attempt,
                ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256,
                authorization_id=self.authorization_id, capability_policy_sha256=cap.policy_sha256, budget=cap.budget)
            self.record = a.service.begin_rules_execution(scope, expected_turn_revision=turn.revision)
        elif (self.record.execution.scope.turn_id != turn.turn_id or self.record.execution.scope.product_attempt != turn.attempt):
            raise ValueError("Rules execution cannot move to another product attempt")

    def _projection(self, carrier, role, request_id):
        execution = self.record.execution if self.record else None
        previous = [e for e in execution.events if isinstance(e, RulesProviderAuthorizedV1)] if execution else []
        if role == "controller" and execution and execution.budget_use.provider_requests >= 63:
            raise ValueError("Rules provider limit reserves the final writer slot")
        if role == "writer" and execution and execution.budget_use.provider_requests >= 64:
            raise ValueError("Rules final writer allowance is exhausted")
        return RulesBuildProjectionV1(schema="dmb_build_rules_projection_v1", authorization_id=self.authorization_id,
            rules_event_sequence=len(execution.events) if execution else 0, role=role, carrier_schema=carrier,
            request_id=request_id, prior_provider_attempt_id=previous[-1].provider_attempt_id if previous else None,
            operations=tuple(RulesBuildOperationV1(operation_id=o.observation.call_id, packet_json=o.raw_output)
                for o in self.outputs) if role == "writer" else ())

    def controller_state(self, state, request_id):
        if not self.active:
            return state
        projection = self._projection(state["schema"], "controller", request_id)
        return {**state, "rules_projection": projection.model_dump(mode="json", by_alias=True),
            "rules_capability": self.capability.model_dump(mode="json", by_alias=True),
            "rules_lookup_offers": {f"query:{i}": question for i, question in enumerate(self.offers)}}

    def select(self, *, request_id, vote, operation):
        """Called only after the actual current typed driver response is accepted."""
        import math
        options = {"none", *(f"query:{i}" for i in range(len(self.offers)))}
        selected, scores = vote.get("selected"), vote.get("probabilities")
        if (vote.get("kind") != "choice" or selected not in options or not isinstance(scores, dict)
                or set(scores) != options or any(type(v) not in {int, float} or not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values())
                or abs(sum(scores.values()) - 1) > .02
                or (selected != "none" and scores[selected] < .9)):
            raise ValueError("Rules query choice is unresolved or uncalibrated")
        if operation != "answer_from_sources":
            self.retire_unused()
            return
        if selected == "none":
            # Abstention grants no lookup or support authority. Only an actual
            # positive query needs the calibrated authorization threshold.
            return
        index = int(selected.split(":")[1])
        a = self.adapter
        auth = next(e for e in self.record.execution.events if isinstance(e, RulesBuildProviderAuthorizedV1)
            and e.provider_attempt_id == a.last_provider_attempt_id)
        if auth.request_id != request_id or auth.role != "controller":
            raise ValueError("Rules selection differs from the actual controller request")
        self._selection = (auth, index, broker.LookupRulesArguments(question=self.offers[index], ruleset_id=self.capability.ruleset_id))

    def lookup_selected(self):
        if self._selection is None:
            return
        auth, index, arguments = self._selection
        self._selection = None
        a = self.adapter
        with a.fence.renewer._lock:
            self._bind()
            turn = a.fence.renewer._turn
            authorization = broker.prepare_build_authorization(self.record.execution, arguments,
                origin_provider_attempt_id=auth.provider_attempt_id,
                origin_request_envelope_sha256=auth.request_envelope_sha256,
                decision_request_id=auth.request_id, operation_index=index)
            self.record = a.service.authorize_rules_lookup(self.record.execution.scope,
                expected_turn_revision=turn.revision, expected_ledger_revision=self.record.revision, event=authorization)
            delivery = a.service.execute_rules_lookup(self.record.execution.scope, expected_turn_revision=turn.revision,
                call_id=authorization.call_id, local_reader=lambda current: broker.prepare_lookup(current, authorization.call_id, arguments))
            self.record = delivery.record
            self.outputs.append(delivery.prepared)

    def retire_unused(self):
        if self.record and self.record.execution.budget_use.calls:
            raise ValueError("Used Rules capability cannot fall back to ordinary completion")
        self.active = False

    def stage_writer(self, staged):
        from .build_jev_writer import with_rules_output
        if not self.active:
            return staged
        if self.record is None or not self.record.execution.budget_use.calls:
            self.retire_unused()
            return staged
        request_id = "rules-writer:" + sha256(staged.input_json.encode()).hexdigest()
        projection = self._projection(json.loads(staged.input_json)["schema"], "writer", request_id)
        return with_rules_output(staged, projection, self._writer_refs())

    def _writer_refs(self):
        refs = {}
        for output in self.outputs:
            emitted = set(output.observation.emitted_support_ids)
            refs.update({r.support_id: r for r in output.observation.support_refs if r.support_id in emitted})
        return tuple(refs.values())

    def authorize(self, view):
        if not self.active:
            return
        body = json.loads(view["payloadJson"])
        writing = getattr(self.adapter, "_active_build_writer_projection", None) is not None
        carrier = json.loads(body["input"]) if writing else body["state"]
        # This existing selector has no Rules capability or source bodies. Its
        # independently verified full request remains under the Graph owner.
        if not writing and carrier.get("writer_selection_policy") == "source_unit_selection_event_closure_v1":
            if "rules_projection" in carrier or "rules_capability" in carrier:
                raise ValueError("Source-unit selector cannot advertise Rules")
            return
        a = self.adapter
        with a.fence.renewer._lock:
            self._bind()
            projection = RulesBuildProjectionV1.model_validate_json(json.dumps(carrier["rules_projection"]))
            expected = self._projection(carrier["schema"], "writer" if writing else "controller", projection.request_id)
            if projection != expected:
                raise ValueError("Actual Rules projection differs from fresh parent records")
            if not writing and (carrier.get("rules_capability") != self.capability.model_dump(mode="json", by_alias=True)
                    or carrier.get("rules_lookup_offers") != {f"query:{i}": question for i, question in enumerate(self.offers)}):
                raise ValueError("Actual controller Rules capability or offered queries differ")
            execution = self.record.execution
            outputs = tuple(RulesOutputRefV1(call_id=o.observation.call_id, packet_sha256=o.observation.packet_sha256)
                for o in self.outputs) if writing else ()
            event = RulesBuildProviderAuthorizedV1(kind="build_provider_authorized", event_id=uuid4(),
                sequence=len(execution.events), execution_id=execution.scope.execution_id,
                provider_attempt_id=UUID(view["providerAttemptId"]), request_envelope_sha256=view["payloadSha256"],
                matched_outputs=outputs, declared_support_refs=self._writer_refs() if writing else (),
                role=projection.role, carrier_schema=projection.carrier_schema, request_id=projection.request_id,
                prior_provider_attempt_id=projection.prior_provider_attempt_id)
            self._append(event, view["payloadJson"])
            included = RulesBuildProviderIncludedV1(kind="build_provider_included", event_id=uuid4(),
                sequence=len(self.record.execution.events), execution_id=execution.scope.execution_id,
                provider_attempt_id=event.provider_attempt_id, request_envelope_sha256=event.request_envelope_sha256,
                matched_outputs=event.matched_outputs, support_refs=event.declared_support_refs,
                role=event.role, carrier_schema=event.carrier_schema, request_id=event.request_id,
                prior_provider_attempt_id=event.prior_provider_attempt_id)
            self._append(included, view["payloadJson"])

    def _append(self, event, raw=None):
        a = self.adapter
        self.record = a.service.append_rules_provider_event(self.record.execution.scope,
            expected_turn_revision=a.fence.renewer._turn.revision, expected_ledger_revision=self.record.revision,
            event=event, prepared_request_json=raw)

    def outcome(self, transition):
        if not self.active or self.record is None or transition == "sdk_entered":
            return
        a = self.adapter
        with a.fence.renewer._lock:
            authorizations = [e for e in self.record.execution.events if isinstance(e, RulesProviderAuthorizedV1)]
            if not authorizations or authorizations[-1].provider_attempt_id != a.last_provider_attempt_id:
                return  # The source-unit selector carried no Rules capability.
            auth = authorizations[-1]
            status = {"response_received": "answered", "known_not_sent": "failed", "outcome_unknown": "unknown"}[transition]
            self._append(RulesProviderOutcomeV1(kind="provider_outcome", event_id=uuid4(),
                sequence=len(self.record.execution.events), execution_id=self.record.execution.scope.execution_id,
                provider_attempt_id=auth.provider_attempt_id, request_envelope_sha256=auth.request_envelope_sha256, status=status))

    def complete(self, raw):
        from application_state.agent_conversation import source_writer_output as base_writer
        from application_state.agent_conversation import types as t
        a = self.adapter
        with a.fence.renewer._lock:
            self._bind()
        auth = [e for e in self.record.execution.events if isinstance(e, RulesBuildProviderAuthorizedV1)][-1]
        outcomes = [e for e in self.record.execution.events if isinstance(e, RulesProviderOutcomeV1)
            and e.provider_attempt_id == auth.provider_attempt_id]
        if auth.role != "writer" or auth.provider_attempt_id != a.producing_provider_attempt_id or len(outcomes) != 1 or outcomes[0].status != "answered":
            raise ValueError("Rules output lacks the actual acknowledged writer")
        item_id = f"unvalidated-rules-answer:{auth.provider_attempt_id}:{self.record.execution.scope.execution_id}"
        existing = [m for o in a.context_capture.trace.observations if o.kind == "context_snapshot"
            for m in o.materials if m.item_id == item_id]
        if existing:
            if len(existing) != 1 or existing[0].text != raw:
                raise ValueError("Rules output capture identity already differs")
        else:
            a.context_capture.observe({"kind": "context_snapshot", "stage": "after", "materials": [
                {"item_id": item_id, "role": "assistant", "state": "model_context", "text": raw}]})
        answer = parse_answer(raw)
        turn = a.fence.turn
        proof = BuildRulesOutputProofV1(policy=POLICY,
            prepared_request_json=a._prepared_build_writer.body.decode(), raw_output_json=raw)
        base_result, segments = None, ()
        if answer.base_output is not None:
            graph_auth = next(e for e in turn.graph_context_execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
                and e.provider_attempt_id == auth.provider_attempt_id)
            packet = json.loads(json.loads(proof.prepared_request_json)["input"])
            completion, bindings = base_writer.reconstruct(json.dumps(answer.base_output), packet, turn, graph_auth)
            segments = tuple(s.text for s in completion.answer_segments)
            base_result = RulesCitedSourceTurnResultV1(world_id=turn.world_id, conversation_id=turn.conversation_id,
                turn_id=turn.turn_id, expected_revision=turn.revision, assistant_text="\n".join(segments), completion=completion,
                producing_provider_attempt_id=auth.provider_attempt_id, claim_graph_event_ids={}, build_section_bindings=bindings,
                writer_request_json=proof.prepared_request_json, raw_provider_output_json=raw,
                rules_execution_id=self.record.execution.scope.execution_id, rules_output_policy=POLICY)
        composition = answer.composition(supplied_refs=self._writer_refs(), base_segments=segments,
            base_disposition="approved" if base_result else "unclaimed")
        text = composition.render(segments)
        a.context_capture.answer_context(text)
        turn = a.stop()
        if base_result is not None:
            base_result = base_result.model_copy(update={"expected_revision": turn.revision})
        a.turn = a.service.complete_mixed_turn(BuildRulesMixedTurnResultV1(schema="dmb_build_rules_mixed_turn_result_v1",
            scope=self.record.execution.scope, expected_turn_revision=turn.revision, expected_rules_revision=self.record.revision,
            assistant_text=text, composition=composition, producing_provider_attempt_id=auth.provider_attempt_id,
            base_result=base_result, output_proof=proof))
        return a.turn
