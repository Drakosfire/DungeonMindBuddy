"""Provider-specific IPC retains integrity and non-provider size boundaries."""
import hashlib
import json

import pytest

from apps.live_control_server.services.hermes_graph_agent_contract import (
    MAX_WIRE_BYTES, decode_json_wire, decode_worker_wire,
    encode_json_wire, encode_provider_authorization_wire, provider_request_byte_limit,
    _serialize_request_budget,
)
from tests.test_hermes_graph_agent_host import _synthetic_request_budget


def frame(payload):
    raw = payload.encode()
    return dict(type="provider_authorization_request", requestId="r", authorizationId="r:1",
                view=dict(provider="openai-api", model="gpt-6-luna", apiMode="codex_responses",
                          baseUrl=None, payloadJson=payload, payloadSha256=hashlib.sha256(raw).hexdigest(),
                          payloadUtf8Bytes=len(raw)))


@pytest.mark.parametrize("text", ["x" * 300_000, '\\"' * 100_000, "é🐐" * 50_000, "\t\n" * 150_000])
def test_large_frame_roundtrip_with_json_escaping(text):
    payload = json.dumps({"input": text}, ensure_ascii=False)
    message = frame(payload)
    with pytest.raises(ValueError):
        encode_json_wire(message)
    raw = encode_provider_authorization_wire(message, body_limit=1_050_000)
    assert len(raw) > MAX_WIRE_BYTES
    with pytest.raises(ValueError):
        decode_json_wire(raw)
    assert decode_worker_wire(raw, body_limit=1_050_000) == message


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_exact_body_byte_boundary(delta):
    message = frame('"' + "x" * (300_000 + delta - 2) + '"')
    if delta > 0:
        with pytest.raises(ValueError, match="provider_request_bytes_exceeded"):
            encode_provider_authorization_wire(message, body_limit=300_000)
        raw = json.dumps(message).encode()
        with pytest.raises(ValueError, match="provider_request_bytes_exceeded"):
            decode_worker_wire(raw, body_limit=300_000)
    else:
        assert decode_worker_wire(encode_provider_authorization_wire(message, body_limit=300_000), body_limit=300_000) == message


@pytest.mark.parametrize("key,value", [("payloadUtf8Bytes", True), ("payloadUtf8Bytes", 1), ("payloadSha256", "0" * 64)])
def test_forged_integrity_rejected_before_authorization(key, value):
    message = frame('"safe"')
    message["view"][key] = value
    with pytest.raises(ValueError, match="integrity"):
        decode_worker_wire(json.dumps(message), body_limit=300_000)


def test_non_provider_messages_keep_old_ceiling():
    for kind in ["result", "telemetry", "graph_operation_request", "provider_lifecycle_request"]:
        with pytest.raises(ValueError, match="non-provider"):
            decode_worker_wire(json.dumps(dict(type=kind, text="x" * MAX_WIRE_BYTES)), body_limit=1_050_000)


def test_budget_frozen_and_old_shape_preserved():
    budget = _synthetic_request_budget()
    assert provider_request_byte_limit(budget) == 256_000
    assert "maxProviderRequestBytes" not in _serialize_request_budget(budget)
    assert _serialize_request_budget({**budget, "maxProviderRequestBytes": 1_050_000})["maxProviderRequestBytes"] == 1_050_000
    for invalid in [True, None, "1050000", 0, 1_050_001]:
        with pytest.raises(ValueError):
            _serialize_request_budget({**budget, "maxProviderRequestBytes": invalid})


def test_maximum_control_escaping_is_bounded_without_changing_raw_payload():
    # Transport integrity handles arbitrary text; provider JSON validity remains
    # the parent's existing authorization responsibility.
    message = frame("\x00" * 300_000)
    raw = encode_provider_authorization_wire(message, body_limit=300_000)
    assert len(raw) > 6 * 300_000
    assert decode_worker_wire(raw, body_limit=300_000) == message
    with pytest.raises(ValueError, match="frame_bytes_exceeded"):
        decode_worker_wire(b" " * (6 * 300_000 + 65_537), body_limit=300_000)
