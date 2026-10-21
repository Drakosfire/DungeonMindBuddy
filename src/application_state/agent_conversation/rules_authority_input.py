"""Internal exact prepared-request proof for Rules provider exposure.

A parent request observer supplies the same serialized envelope and provider
attempt used by Graph. Quoted text in arbitrary messages is not a tool result.
"""

from __future__ import annotations

from hashlib import sha256
import json

from .rules_authority_events import (
    RulesExecutionV1,
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
    RulesQueryObservedV1,
    RulesToolAuthorizedV1, RulesBuildToolAuthorizedV1,
    RulesBuildProviderAuthorizedV1, RulesBuildProviderIncludedV1,
    normalized_question,
    ref_map,
)
from .rules_authority_packet import _unique_object, verify_output_proof


def verify_prepared_input(
    execution: RulesExecutionV1,
    event: RulesProviderAuthorizedV1 | RulesProviderIncludedV1,
    prepared_request_json: str,
) -> None:
    """Verify matched call/output bytes and exact emitted source identity.

    This proof is ephemeral. Persist only the validated event under the owning
    claim lock. Neither the complete request nor a second source copy is saved.
    """
    if event.execution_id != execution.scope.execution_id:
        raise ValueError("Rules provider event belongs to another execution")
    if (
        sha256(prepared_request_json.encode("utf-8")).hexdigest()
        != event.request_envelope_sha256
    ):
        raise ValueError(
            "Rules producing envelope differs from actual serialized request"
        )
    body = json.loads(prepared_request_json, object_pairs_hook=_unique_object)
    if not isinstance(body, dict):
        raise ValueError("Rules prepared request is not an object")
    calls = {}
    outputs = {}

    def admit_call(call_id, name, arguments):
        if not isinstance(call_id, str) or not call_id or call_id in calls:
            raise ValueError("Ambiguous provider function call identity")
        calls[call_id] = (name, arguments)

    def admit_output(call_id, output):
        if not isinstance(call_id, str) or call_id not in calls or call_id in outputs:
            raise ValueError("Provider function output has no unique preceding call")
        outputs[call_id] = output

    if isinstance(body.get("input"), list) and "messages" not in body:
        for item in body["input"]:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "function_call":
                admit_call(item.get("call_id"), item.get("name"), item.get("arguments"))
            elif item.get("type") == "function_call_output":
                admit_output(item.get("call_id"), item.get("output"))
    elif isinstance(body.get("messages"), list) and "input" not in body:
        for message in body["messages"]:
            if not isinstance(message, dict):
                continue
            if message.get("role") == "assistant":
                tool_calls = message.get("tool_calls")
                if tool_calls is None:
                    tool_calls = []
                if not isinstance(tool_calls, list):
                    raise ValueError("Malformed provider tool calls")
                for call in tool_calls:
                    if (
                        not isinstance(call, dict)
                        or call.get("type") != "function"
                        or not isinstance(call.get("function"), dict)
                    ):
                        raise ValueError("Malformed provider function call")
                    function = call["function"]
                    admit_call(
                        call.get("id"), function.get("name"), function.get("arguments")
                    )
            elif message.get("role") == "tool":
                admit_output(message.get("tool_call_id"), message.get("content"))
    else:
        if not isinstance(event, (RulesBuildProviderAuthorizedV1, RulesBuildProviderIncludedV1)):
            raise ValueError("Unknown or ambiguous Rules provider input representation")
        from .rules_authority_build_input import verify_build_prepared_input
        verify_build_prepared_input(execution, event, body)
        return
    if isinstance(event, (RulesBuildProviderAuthorizedV1, RulesBuildProviderIncludedV1)):
        raise ValueError("Build Rules provider cannot use a synthetic function transcript")
    authorizations = {
        item.call_id: item
        for item in execution.events
        if isinstance(item, RulesToolAuthorizedV1)
    }
    observations = {
        item.call_id: item
        for item in execution.events
        if isinstance(item, RulesQueryObservedV1)
    }
    actual_outputs = {}
    actual_supports = {}
    for call_id, raw in outputs.items():
        name, arguments = calls[call_id]
        if name != "lookup_rules":
            continue
        auth = authorizations.get(call_id)
        observed = observations.get(call_id)
        if (
            auth is None
            or isinstance(auth, RulesBuildToolAuthorizedV1)
            or observed is None
            or not isinstance(arguments, str)
            or not isinstance(raw, str)
        ):
            raise ValueError(
                "Rules function output lacks a parent-produced lookup observation"
            )
        args = json.loads(arguments, object_pairs_hook=_unique_object)
        if (
            not isinstance(args, dict)
            or set(args) != {"question", "ruleset_id"}
            or not isinstance(args["question"], str)
            or not 1 <= len(args["question"]) <= 800
            or normalized_question(args["question"]) != auth.normalized_question
            or args["ruleset_id"] != execution.scope.ruleset_id
        ):
            raise ValueError(
                "Rules provider call differs from its frozen authorization"
            )
        verify_output_proof(execution.scope, observed, execution.supports, raw)
        actual_outputs[call_id] = observed.packet_sha256
        refs = ref_map(observed.support_refs)
        actual_supports.update({key: refs[key] for key in observed.emitted_support_ids})
    declared_outputs = {
        item.call_id: item.packet_sha256 for item in event.matched_outputs
    }
    if (
        len(declared_outputs) != len(event.matched_outputs)
        or declared_outputs != actual_outputs
    ):
        raise ValueError(
            "Rules provider output declarations differ from actual matched results"
        )
    declared_refs = (
        event.declared_support_refs
        if isinstance(event, RulesProviderAuthorizedV1)
        else event.support_refs
    )
    if ref_map(declared_refs) != actual_supports:
        raise ValueError(
            "Rules provider support declarations differ from actual exposed capsules"
        )
