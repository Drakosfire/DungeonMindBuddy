"""Exact pinned-hook message capture primitives; no SDK sends or APP acceptance."""

from hashlib import sha256
from types import SimpleNamespace as S
import json

import pytest

from apps.live_control_server.services.native_rules_capture import (
    NativeProviderReply,
    NativeReplyCapture,
    decode_native_reply_wire,
    encode_native_reply_wire,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    decode_worker_wire,
)


def view():
    return S(
        provider="openai-api",
        model="gpt-6-luna",
        api_mode="chat_completions",
        payload_sha256="a" * 64,
    )


def capture(callback=None):
    received = []

    def ack(reply):
        received.append(reply)
        return True

    collector = NativeReplyCapture(callback or ack)
    manager = S(_hooks={})
    assert collector.register(manager)
    assert collector.bind(view(), authorization_id="auth:1", api_request_id="api:1")
    return collector, manager, received


def post(collector, text='{"answer":"exact"}', calls=None, finish="stop", **changes):
    payload = dict(
        api_request_id="api:1",
        model="gpt-6-luna",
        api_mode="chat_completions",
        finish_reason=finish,
        assistant_message=S(role="assistant", content=text, tool_calls=calls),
        response={"assistant_message": {"content": "SANITIZED/TRUNCATED"}},
    )
    payload.update(changes)
    return collector.on_post_api_request(**payload)


def tool(identity="call_real", args='{"ruleset_id":"srd","question":"Space 🦉?"}'):
    return S(
        id=identity, type="function", function=S(name="lookup_rules", arguments=args)
    )


def test_uncapped_sdk_message_not_sanitized_hook_response_is_captured_exactly():
    collector, _, replies = capture()
    text = "🦉" * 40000
    assert post(collector, text)
    reply = replies[0]
    assert reply.text == text and reply.text_utf8_bytes == 160000
    assert reply.text_sha256 == sha256(text.encode()).hexdigest()
    assert reply.request_sha256 == "a" * 64 and reply.authorization_id == "auth:1"
    assert reply.status == "answered" and collector.pending is None


def test_actual_tool_call_ids_and_argument_bytes_are_preserved():
    collector, _, replies = capture()
    call = tool()
    assert post(collector, None, [call], "tool_calls")
    actual = replies[0].tool_calls[0]
    assert (
        actual.call_id == call.id and actual.arguments_json == call.function.arguments
    )
    canonical = json.dumps(
        json.loads(call.function.arguments),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert actual.arguments_sha256 == sha256(canonical).hexdigest()


@pytest.mark.parametrize(
    "change",
    [
        "request",
        "mode",
        "model",
        "role",
        "text_type",
        "oversize",
        "malformed_calls",
        "duplicate",
        "arguments",
        "nonfinite",
        "invalid_unicode",
    ],
)
def test_malformed_or_foreign_reply_vetoes_without_partial_capture(change):
    collector, _, replies = capture()
    kw = {}
    if change == "request":
        kw["api_request_id"] = "foreign"
    if change == "mode":
        kw["api_mode"] = "legacy"
    if change == "model":
        kw["model"] = "other"
    if change == "role":
        kw["assistant_message"] = S(role="user", content="forged", tool_calls=None)
    if change == "text_type":
        kw["text"] = {}
    if change == "oversize":
        kw["text"] = "x" * 262145
    if change == "malformed_calls":
        kw["calls"] = False
    if change == "duplicate":
        kw.update(text=None, calls=[tool(), tool()], finish="tool_calls")
    if change == "arguments":
        kw.update(text=None, calls=[tool(args='{"x":1,"x":2}')], finish="tool_calls")
    if change == "nonfinite":
        kw.update(text=None, calls=[tool(args='{"x":NaN}')], finish="tool_calls")
    if change == "invalid_unicode":
        kw["text"] = chr(0xD800)
    assert not post(collector, **kw)
    assert (
        collector.failure
        and collector.last is None
        and collector.pending is None
        and replies == []
    )
    assert not collector.bind(view(), authorization_id="auth:2", api_request_id="api:2")


@pytest.mark.parametrize("finish", ["length", "content_filter", None])
def test_incomplete_response_is_observed_but_never_usable_as_an_answer(finish):
    collector, _, replies = capture()
    assert post(collector, '{"partial":', finish=finish)
    assert (
        replies[0].status == "failed"
        and collector.failure == "provider_output_incomplete"
    )


@pytest.mark.parametrize("raises", [False, True])
def test_unacknowledged_parent_callback_is_fail_closed_even_when_sdk_swallows_hooks(
    raises,
):
    def callback(_reply):
        if raises:
            raise RuntimeError("private persistence failure")
        return False

    collector, _, _ = capture(callback)
    assert not post(collector)
    assert collector.failure and collector.last is None


def test_next_request_retires_prior_body_and_close_unregisters_all_owned_state():
    collector, manager, _ = capture()
    assert post(collector)
    assert collector.last is not None
    assert collector.bind(view(), authorization_id="auth:2", api_request_id="api:2")
    assert collector.last is None
    assert post(collector, "next", api_request_id="api:2")
    collector.close()
    assert manager._hooks["post_api_request"] == []
    assert (
        collector.pending is None
        and collector.last is None
        and collector.on_reply is None
    )
    assert not collector.register(manager)


def test_missing_hook_or_unresolved_capture_prevents_binding():
    collector = NativeReplyCapture(lambda _: True)
    assert not collector.register(S())
    assert not collector.bind(view(), authorization_id="auth:1", api_request_id="api:1")
    ready, _, _ = capture()
    assert not ready.bind(view(), authorization_id="auth:2", api_request_id="api:2")


def test_capture_metadata_is_bounded_to_the_native_provider_allowance():
    collector, _, _ = capture(lambda _: True)
    for number in range(1, 65):
        if number > 1:
            assert collector.bind(
                view(),
                authorization_id=f"auth:{number}",
                api_request_id=f"api:{number}",
            )
        assert post(collector, "short", api_request_id=f"api:{number}")
    assert not collector.bind(
        view(), authorization_id="auth:65", api_request_id="api:65"
    )
    assert collector.failure


def test_reusing_an_earlier_provider_tool_call_identity_is_rejected():
    collector, _, replies = capture()
    assert post(collector, None, [tool()], "tool_calls")
    assert collector.bind(view(), authorization_id="auth:2", api_request_id="api:2")
    assert not post(collector, None, [tool()], "tool_calls", api_request_id="api:2")
    assert collector.failure and len(replies) == 1


def test_native_reply_wire_has_a_purpose_bound_and_round_trips_large_exact_text():
    text = '\\"\n🦉' * 30000
    encoded = text.encode("utf-8")
    reply = NativeProviderReply(
        "auth:1",
        "api:1",
        "openai-api",
        "gpt-6-luna",
        "chat_completions",
        "a" * 64,
        "stop",
        "answered",
        text,
        sha256(encoded).hexdigest(),
        len(encoded),
        (),
    )
    frame = encode_native_reply_wire(reply)
    assert len(frame) > 262144
    decoded = decode_native_reply_wire(frame)
    assert decoded == reply
    assert decode_worker_wire(frame, body_limit=262144)["text"] == text


def test_native_reply_wire_rejects_digest_tampering_and_unknown_fields():
    reply = NativeProviderReply(
        "auth:1",
        "api:1",
        "openai-api",
        "gpt-6-luna",
        "chat_completions",
        "a" * 64,
        "stop",
        "answered",
        "answer",
        sha256(b"answer").hexdigest(),
        6,
        (),
    )
    import json

    payload = json.loads(encode_native_reply_wire(reply))
    payload["textSha256"] = "b" * 64
    with pytest.raises(ValueError):
        decode_native_reply_wire(json.dumps(payload))
    payload["textSha256"] = sha256(b"answer").hexdigest()
    payload["extra"] = True
    with pytest.raises(ValueError):
        decode_native_reply_wire(json.dumps(payload))
