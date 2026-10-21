"""Claim-fenced native Rules delivery without Graph admission or tool authority."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_tool_definition
from application_state.agent_conversation.source_writer_output import strict_json
from .native_rules_runtime import NativeRulesRuntime


class RulesOnlyRuntime:
    def __init__(self, *, service, request, submitted_intent, renewer, budget):
        turn = renewer.current_turn()
        if (request.graph_request.mode != "none" or request.surface.surface_id not in {"plan", "play"}
                or turn.graph_context_receipt is not None or turn.graph_context_execution is not None):
            raise ValueError("Rules-only requires native Plan/Play and no Graph scope")
        self.service, self.request, self.submitted_intent = service, request, submitted_intent
        self.turn, self.world_id = turn, turn.world_id
        self.expected_conversation_id = turn.conversation_id
        self.fence = SimpleNamespace(renewer=renewer)
        self.budget = budget
        self.last_provider_attempt_id = self.producing_provider_attempt_id = None
        self.build_claim_evidence = {}
        self.failure = None
        self.rules_runtime = None
        self.context_capture = None
        self.rules_runtime = NativeRulesRuntime(self, rules_capability(graph=False))
        self._entered = self._received = self._captured = False

    def _is_build_turn(self):
        return False

    def invocation(self, invocation):
        capability = self.rules_runtime.capability
        if invocation.context_packet.world_scope is not None or invocation.context_packet.retrieval_session is not None:
            raise ValueError("Rules-only cannot inherit Graph input authority")
        return replace(invocation, context_packet=replace(invocation.context_packet, rules_capability=capability),
            capability_policy=replace(invocation.capability_policy, policy_id=capability.policy_id))

    def authorize(self, view):
        from .agent_turn_service import _json_node_count
        try:
            if self.failure is not None or self.fence.renewer._error is not None:
                return False
            if self.last_provider_attempt_id is not None and (not self._received or not self._captured):
                raise ValueError("Previous provider outcome remains indeterminate")
            if self.rules_runtime.last_reply is not None and self.rules_runtime.last_reply.status == "answered":
                raise ValueError("A final Rules-only answer cannot dispatch again")
            if any(view.get(key) != self.budget[key] for key in ("provider", "model", "apiMode")):
                raise ValueError("Rules-only provider differs from the configured budget")
            raw = view["payloadJson"].encode("utf-8")
            if (len(raw) != view["payloadUtf8Bytes"] or sha256(raw).hexdigest() != view["payloadSha256"]
                    or len(raw) > self.budget["maxProviderRequestBytes"]):
                raise ValueError("Rules-only provider bytes differ from their commitment")
            body = strict_json(view["payloadJson"])
            if not isinstance(body, dict) or body.get("model") != self.budget["model"]:
                raise ValueError("Rules-only provider body must use the configured model")
            estimate = len(raw) + 64 * (1 + _json_node_count(body))
            if estimate + self.budget["outputReserveTokens"] > self.budget["contextLimitTokens"]:
                raise ValueError("Rules-only provider envelope exceeds its context budget")
            output_limit = body.get("max_output_tokens", body.get("max_completion_tokens", body.get("max_tokens")))
            if type(output_limit) is not int or not 1 <= output_limit <= self.budget["outputReserveTokens"]:
                raise ValueError("Rules-only provider output reserve is not bounded")
            tools = body.get("tools", [])
            if not isinstance(tools,list) or len(tools) > 1:
                raise ValueError("Rules-only provider tool inventory differs from its capability")
            expected = rules_tool_definition()["function"]
            for tool in tools:
                function = tool.get("function",tool) if isinstance(tool,dict) else {}
                if (function.get("name") != expected["name"] or function.get("parameters") != expected["parameters"]):
                    raise ValueError("Rules-only provider exposes a foreign tool contract")
            items = body.get("input", []) if isinstance(body.get("input"), list) else []
            for item in (*items, *body.get("messages", [])):
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "function_call" and item.get("name") != "lookup_rules":
                    raise ValueError("Rules-only input includes a foreign function call")
                for call in item.get("tool_calls", []):
                    if call.get("function", {}).get("name") != "lookup_rules":
                        raise ValueError("Rules-only input includes a foreign tool call")
            self.last_provider_attempt_id = uuid4()
            accepted = self.rules_runtime.authorize(view)
            self._entered = self._received = self._captured = False
            return accepted
        except Exception as exc:
            self.failure = exc
            return False

    def capture_native_provider_reply(self, reply):
        if self.failure is not None or not self._entered or not self._received:
            return False
        accepted = self.rules_runtime.capture_reply(replace(reply,
            authorization_id=str(self.rules_runtime.authorization_id)))
        if not accepted:
            self.failure = ValueError("Rules-only provider reply was not durably captured")
        else:
            self._captured = True
            if reply.status == "answered":
                self.producing_provider_attempt_id = self.last_provider_attempt_id
        return accepted

    def record_lifecycle(self, lifecycle):
        try:
            if self.failure is not None or self.last_provider_attempt_id is None:
                return False
            transition = lifecycle.get("transition")
            if transition == "sdk_entered":
                if self._entered:
                    raise ValueError("Rules-only SDK entry was already acknowledged")
                self._entered = True
            elif transition == "response_received":
                # The SDK acknowledges receipt before its post_api_request hook
                # publishes the parsed reply. Capture remains a separate required gate.
                if not self._entered or self._received:
                    raise ValueError("Rules-only response has no unique entered request")
                self._received = True
            elif transition in {"known_not_sent", "outcome_unknown"}:
                self.rules_runtime.outcome(transition)
                self.failure = ValueError("Rules-only provider delivery did not complete")
            else:
                raise ValueError("Unknown Rules-only provider lifecycle")
            return True
        except Exception as exc:
            self.failure = exc
            return False

    def broker_operation(self, message):
        if self.failure is not None or not self._received or message.get("toolName") != "lookup_rules":
            raise ValueError("Rules-only has no authority for this tool operation")
        return self.rules_runtime.lookup(message)

    def complete(self, turn):
        if (self.failure is not None or not self._received or self.producing_provider_attempt_id is None):
            raise ValueError("Rules-only final response is not acknowledged")
        return self.rules_runtime.complete(turn, self.rules_runtime.last_reply)
