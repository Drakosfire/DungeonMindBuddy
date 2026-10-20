"""Exact parent-side witnesses for native Rules tool dispatch."""

import json
from types import SimpleNamespace

from apps.live_control_server.services.native_rules_capture import NativeToolReply
from apps.live_control_server.services.native_rules_runtime import (
    _captured_lookup_call,
    _provider_lookup_arguments,
)
from application_state.agent_conversation.rules_authority_policy import RULESET


class CapturedReply:
    status = "tool_calls"

    def __init__(self, *calls):
        self.tool_calls = calls


def call(call_id="call-1", name="lookup_rules", arguments=None):
    arguments = arguments or {"question": "Can a creature end its move here?", "ruleset_id": RULESET}
    return NativeToolReply(
        call_id=call_id,
        name=name,
        arguments_json=json.dumps(arguments, separators=(",", ":")),
        arguments_sha256="0" * 64,
    )


def arguments():
    return {"question": "Can a creature end its move here?", "ruleset_id": RULESET}


def test_parent_accepts_only_the_exact_captured_lookup_call():
    reply = CapturedReply(call())

    assert _captured_lookup_call(reply, "call-1", arguments()) == "call-1"


def test_parent_rejects_a_foreign_tool_call_id():
    reply = CapturedReply(call())

    try:
        _captured_lookup_call(reply, "forged-call", arguments())
    except ValueError as exc:
        assert "captured lookup_rules call" in str(exc)
    else:
        raise AssertionError("foreign call ID was accepted")


def test_parent_rejects_ambiguous_duplicate_call_identity():
    reply = CapturedReply(call(), call())

    try:
        _captured_lookup_call(reply, "call-1", arguments())
    except ValueError as exc:
        assert "captured lookup_rules call" in str(exc)
    else:
        raise AssertionError("duplicate captured call ID was accepted")


def test_parent_rejects_arguments_that_differ_from_the_captured_call():
    reply = CapturedReply(call())
    changed = {**arguments(), "question": "How fast can they travel?"}

    try:
        _captured_lookup_call(reply, "call-1", changed)
    except ValueError as exc:
        assert "differ from the captured provider reply" in str(exc)
    else:
        raise AssertionError("changed tool arguments were accepted")


def test_parent_rejects_duplicate_json_argument_keys():
    captured = NativeToolReply(
        call_id="call-1", name="lookup_rules",
        arguments_json='{"question":"first","question":"second","ruleset_id":"'
        + RULESET + '"}',
        arguments_sha256="0" * 64,
    )

    try:
        _captured_lookup_call(CapturedReply(captured), "call-1", arguments())
    except ValueError as exc:
        assert "duplicate JSON keys" in str(exc)
    else:
        raise AssertionError("duplicate argument key was accepted")


def test_provider_input_arguments_must_match_durable_authorized_query():
    question = arguments()["question"]
    scope = SimpleNamespace(ruleset_id=RULESET)
    authorization = SimpleNamespace(normalized_question=question.casefold())
    payload = json.dumps(arguments())

    assert _provider_lookup_arguments(payload, scope, authorization).question == question

    changed = json.dumps({**arguments(), "question": "How fast can they travel?"})
    try:
        _provider_lookup_arguments(changed, scope, authorization)
    except ValueError as exc:
        assert "differ from the authorized query" in str(exc)
    else:
        raise AssertionError("reused call ID with changed question was accepted")


def test_provider_input_rejects_duplicate_lookup_argument_keys():
    scope = SimpleNamespace(ruleset_id=RULESET)
    authorization = SimpleNamespace(
        normalized_question=arguments()["question"].casefold()
    )
    payload = '{"question":"Can a creature end its move here?",' \
        '"question":"How fast can they travel?","ruleset_id":"' + RULESET + '"}'

    try:
        _provider_lookup_arguments(payload, scope, authorization)
    except ValueError as exc:
        assert "duplicate JSON keys" in str(exc)
    else:
        raise AssertionError("duplicate provider argument key was accepted")
