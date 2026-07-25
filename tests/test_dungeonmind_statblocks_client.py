from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    MAX_RESPONSE_BODY_BYTES,
    DungeonMindStatblockV1Client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.config import (
    INTERNAL_KEY_HEADER,
    StatblockIntegrationConfig,
    StatblockIntegrationConfigError,
    load_statblock_integration_config,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ExactRevisionResourceV1,
    HealthResponseV1,
    ReadinessResponseV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.readiness import (
    evaluate_statblock_integration_readiness,
    project_buddy_capabilities,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "statblocks" / "v1"
SECRET = "test-internal-key-not-for-production"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _config(**overrides: object) -> StatblockIntegrationConfig:
    payload = {
        "base_url": "https://statblocks.example.test",
        "internal_api_key": SECRET,
        "enabled": True,
        "timeout_seconds": 5.0,
    }
    payload.update(overrides)
    return StatblockIntegrationConfig(**payload)  # type: ignore[arg-type]


def _client(handler: httpx.MockTransport) -> DungeonMindStatblockV1Client:
    return DungeonMindStatblockV1Client(
        config=_config(),
        http_client=httpx.Client(transport=handler, follow_redirects=False),
    )


def test_config_disabled_does_not_require_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_ENABLED", "false")
    monkeypatch.delenv("DUNGEONMIND_STATBLOCKS_BASE_URL", raising=False)
    monkeypatch.delenv("DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY", raising=False)
    config = load_statblock_integration_config()
    assert config.enabled is False
    assert config.is_configured is False


def test_config_enabled_requires_base_url_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_ENABLED", "true")
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_BASE_URL", "https://example.test")
    monkeypatch.delenv("DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY", raising=False)
    with pytest.raises(StatblockIntegrationConfigError, match="base URL and internal API key"):
        load_statblock_integration_config()


def test_config_rejects_unknown_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_ENABLED", "maybe")
    with pytest.raises(StatblockIntegrationConfigError, match="ENABLED must be one of"):
        load_statblock_integration_config()


def test_config_rejects_nan_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_ENABLED", "false")
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS", "nan")
    with pytest.raises(StatblockIntegrationConfigError, match="finite value"):
        load_statblock_integration_config()


@pytest.mark.parametrize(
    "base_url",
    [
        "https://statblocks.example.test?foo=bar",
        "https://statblocks.example.test#frag",
        "https://statblocks.example.test?foo=bar#frag",
        "https://statblocks.example.test/;jsessionid=abc",
    ],
)
def test_config_rejects_base_url_query_fragment_or_params(
    monkeypatch: pytest.MonkeyPatch,
    base_url: str,
) -> None:
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_ENABLED", "true")
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_BASE_URL", base_url)
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY", SECRET)
    with pytest.raises(
        StatblockIntegrationConfigError,
        match="query, fragment, or URL parameters",
    ):
        load_statblock_integration_config()


def test_config_repr_redacts_internal_key() -> None:
    config = _config()
    rendered = repr(config)
    assert SECRET not in rendered
    assert "internal_api_key=***" in rendered


def test_disabled_readiness_makes_no_downstream_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_ENABLED", "0")
    readiness = evaluate_statblock_integration_readiness()
    assert readiness.configured is False
    assert readiness.available is False
    assert readiness.diagnostics == ["integration_disabled"]


def test_success_readiness_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get(INTERNAL_KEY_HEADER) == SECRET
        if request.url.path.endswith("/health/ready"):
            return httpx.Response(
                200,
                json={
                    "status": "ready",
                    "contract": "dungeonmind.dungeonbuddy-statblocks",
                    "generation_enabled": True,
                    "read_routes_enabled": True,
                    "errors": [],
                },
            )
        if request.url.path.endswith("/health"):
            return httpx.Response(
                200,
                json={
                    "status": "available",
                    "contract": "dungeonmind.dungeonbuddy-statblocks",
                    "contract_version": "1.0.0",
                    "capabilities": [
                        "candidate_generate",
                        "candidate_read",
                        "statblock_create",
                        "statblock_revision_read",
                    ],
                },
            )
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "missing"}})

    client = _client(httpx.MockTransport(handler))
    readiness = evaluate_statblock_integration_readiness(client=client)
    assert readiness.configured is True
    assert readiness.available is True
    assert readiness.downstream_status == "ready"
    assert readiness.contract == "dungeonmind.dungeonbuddy-statblocks"
    assert readiness.contract_version == "1.0.0"
    assert readiness.capabilities == ["generation", "read", "persistence"]


def test_capability_honesty_when_generation_disabled() -> None:
    projected = project_buddy_capabilities(
        downstream_capabilities=[
            "candidate_generate",
            "statblock_revision_read",
            "statblock_create",
        ],
        generation_enabled=False,
        read_routes_enabled=True,
    )
    assert projected == ["read", "persistence"]


def test_auth_failure_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"code": "unauthorized_internal_client", "message": "nope"}},
        )

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_authentication_failed"
    assert SECRET not in str(exc_info.value)
    assert SECRET not in repr(exc_info.value)


def test_injected_client_redirects_are_refused() -> None:
    seen_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        if request.url.host == "evil.example.test":
            return httpx.Response(
                200,
                json={
                    "status": "available",
                    "contract": "dungeonmind.dungeonbuddy-statblocks",
                    "contract_version": "1.0.0",
                    "capabilities": [],
                },
            )
        return httpx.Response(
            302,
            headers={"location": "https://evil.example.test/steal"},
        )

    # Injected client opts into redirects; adapter must still refuse.
    client = DungeonMindStatblockV1Client(
        config=_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        ),
    )
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_unexpected"
    assert "redirect refused" in exc_info.value.message
    assert seen_hosts == ["statblocks.example.test"]
    assert SECRET not in str(exc_info.value)


def test_readiness_503_not_ready_body_is_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={
                "status": "not_ready",
                "contract": "dungeonmind.dungeonbuddy-statblocks",
                "generation_enabled": False,
                "read_routes_enabled": False,
                "errors": ["firestore_disabled"],
            },
        )

    client = _client(httpx.MockTransport(handler))
    readiness = client.get_readiness()
    assert readiness.status == "not_ready"
    assert readiness.errors == ["firestore_disabled"]


def test_readiness_503_error_envelope_is_stable_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={
                "error": {
                    "code": "internal_service_misconfigured",
                    "message": "Internal service is misconfigured",
                }
            },
        )

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_readiness()
    assert exc_info.value.category == "downstream_unavailable"
    assert exc_info.value.error_code == "internal_service_misconfigured"
    assert exc_info.value.message == "Internal service is misconfigured"
    assert exc_info.value.status_code == 503


def test_downstream_error_text_redacts_internal_key() -> None:
    leaked = f"rejected key {SECRET}"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={
                "error": {
                    "code": "internal_service_misconfigured",
                    "message": leaked,
                    "details": {"echo": SECRET, SECRET: "present"},
                }
            },
        )

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_readiness()
    assert SECRET not in exc_info.value.message
    assert SECRET not in str(exc_info.value)
    assert SECRET not in repr(exc_info.value)
    assert SECRET not in json.dumps(exc_info.value.details)
    assert "***" in exc_info.value.message
    assert "***" in exc_info.value.details
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None

    readiness = evaluate_statblock_integration_readiness(client=client)
    dumped = json.dumps(readiness.model_dump(mode="json", by_alias=True))
    assert SECRET not in dumped
    assert readiness.downstream_status == "downstream_unavailable"


def test_transport_errors_do_not_retain_secret_bearing_causes() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client = _client(httpx.MockTransport(timeout_handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_timeout"
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None

    def bad_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=f'{{"leak":"{SECRET}"}}'.encode() + b"not-json")

    client = _client(httpx.MockTransport(bad_json))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_unexpected"
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None
    assert SECRET not in str(exc_info.value)

    def bad_schema(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "available",
                "contract": "evil.contract",
                "contract_version": "1.0.0",
                "capabilities": [],
                "leak": SECRET,
            },
        )

    client = _client(httpx.MockTransport(bad_schema))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_unexpected"
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None
    assert SECRET not in str(exc_info.value)


def test_redact_secret_in_value_redacts_dictionary_keys() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        redact_secret_in_value,
    )

    payload = {SECRET: {"nested": SECRET}, "ok": True}
    redacted = redact_secret_in_value(payload, SECRET)
    assert SECRET not in json.dumps(redacted)
    assert "***" in redacted
    assert redacted["***"]["nested"] == "***"


def test_malformed_5xx_fails_closed_as_unexpected() -> None:
    def non_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"<html>boom</html>")

    client = _client(httpx.MockTransport(non_json))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_unexpected"

    def invalid_envelope(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"not": "an-error-envelope"})

    client = _client(httpx.MockTransport(invalid_envelope))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_unexpected"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "status": "not_ready",
            "contract": "evil.contract",
            "generation_enabled": False,
            "read_routes_enabled": False,
            "errors": [],
        },
        {"status": "not_ready"},
        {"arbitrary": True},
    ],
)
def test_readiness_503_invalid_payload_fails_closed(payload: dict) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json=payload)

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_readiness()
    assert exc_info.value.category == "downstream_unexpected"


def test_injected_client_timeout_is_enforced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    # Injected client disables timeouts; adapter must still apply config timeout.
    client = DungeonMindStatblockV1Client(
        config=_config(timeout_seconds=0.05),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            timeout=None,
            follow_redirects=False,
        ),
    )
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_timeout"


def test_injected_client_request_carries_config_timeout() -> None:
    seen_timeouts: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_timeouts.append(request.extensions.get("timeout"))
        return httpx.Response(
            200,
            json={
                "status": "available",
                "contract": "dungeonmind.dungeonbuddy-statblocks",
                "contract_version": "1.0.0",
                "capabilities": [],
            },
        )

    client = DungeonMindStatblockV1Client(
        config=_config(timeout_seconds=7.5),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            timeout=None,
            follow_redirects=False,
        ),
    )
    client.get_health()
    assert len(seen_timeouts) == 1
    timeout = seen_timeouts[0]
    assert timeout is not None
    if isinstance(timeout, dict):
        assert timeout.get("read") == 7.5
    else:
        assert timeout.read == 7.5


def test_timeout_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_timeout"
    assert exc_info.value.retryable is True


def test_rate_limit_and_error_envelope_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"code": "rate_limited", "message": "slow down"}})

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_rate_limited"
    assert exc_info.value.error_code == "rate_limited"


def test_malformed_json_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"content-type": "text/plain"})

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_unexpected"


def test_health_rejects_wrong_contract_identity() -> None:
    with pytest.raises(Exception):
        HealthResponseV1.model_validate(
            {
                "status": "available",
                "contract": "other.service",
                "contract_version": "1.0.0",
                "capabilities": [],
            }
        )


def test_readiness_rejects_wrong_contract_identity() -> None:
    with pytest.raises(Exception):
        ReadinessResponseV1.model_validate(
            {
                "status": "ready",
                "contract": "dungeonmind.dungeonbuddy-statblocks",
                "generation_enabled": True,
                "read_routes_enabled": True,
                "errors": [],
            }
            | {"contract": "evil.contract"}
        )


def test_exact_revision_rejects_arbitrary_identity_fields() -> None:
    payload = _fixture("exact-revision-response.json")
    payload["statblock_id"] = "not-a-statblock-id"
    with pytest.raises(Exception):
        ExactRevisionResourceV1.model_validate(payload)

    payload = _fixture("exact-revision-response.json")
    payload["definition_digest"] = "md5:deadbeef"
    with pytest.raises(Exception):
        ExactRevisionResourceV1.model_validate(payload)

    payload = _fixture("exact-revision-response.json")
    payload["contract_version"] = "9.9.9"
    with pytest.raises(Exception):
        ExactRevisionResourceV1.model_validate(payload)


def test_exact_revision_rejects_non_published_path_ids() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_fixture("exact-revision-response.json"))

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_exact_revision("SB_UPPER", "rev_000002")
    assert exc_info.value.category == "downstream_invalid_request"


def test_exact_revision_fixture_retains_identity() -> None:
    payload = _fixture("exact-revision-response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get(INTERNAL_KEY_HEADER) == SECRET
        assert request.url.path.endswith("/statblocks/sb_000001/revisions/rev_000002")
        return httpx.Response(200, json=payload)

    client = _client(httpx.MockTransport(handler))
    revision = client.get_exact_revision("sb_000001", "rev_000002")
    assert revision.statblock_id == "sb_000001"
    assert revision.revision_id == "rev_000002"
    assert revision.definition_digest.startswith("sha256:")
    assert revision.contract == "dungeonmind.dungeonbuddy-statblocks"
    assert revision.contract_version == "1.0.0"


def test_oversized_response_body_rejected_before_parse() -> None:
    huge = b"{" + (b"a" * (MAX_RESPONSE_BODY_BYTES + 1)) + b"}"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=huge,
            headers={
                "content-type": "application/json",
                "content-length": str(len(huge)),
            },
        )

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_unexpected"
    assert "bounded body" in exc_info.value.message


def test_client_exposes_candidate_operations_for_sbw03() -> None:
    assert hasattr(DungeonMindStatblockV1Client, "generate_candidate")
    assert hasattr(DungeonMindStatblockV1Client, "get_candidate")


def test_internal_key_absent_from_readiness_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/health/ready"):
            return httpx.Response(
                200,
                json={
                    "status": "ready",
                    "contract": "dungeonmind.dungeonbuddy-statblocks",
                    "generation_enabled": True,
                    "read_routes_enabled": True,
                    "errors": [],
                },
            )
        return httpx.Response(
            200,
            json={
                "status": "available",
                "contract": "dungeonmind.dungeonbuddy-statblocks",
                "contract_version": "1.0.0",
                "capabilities": ["candidate_generate"],
            },
        )

    client = _client(httpx.MockTransport(handler))
    readiness = evaluate_statblock_integration_readiness(client=client)
    dumped = readiness.model_dump(mode="json", by_alias=True)
    serialized = json.dumps(dumped)
    assert SECRET not in serialized
    assert "internal_api_key" not in serialized
    assert SECRET not in repr(client.config)


# --- SBW07a: create / exact-read adapter + fixture-backed terminal inventory ---


def test_client_exposes_create_statblock_for_sbw07a() -> None:
    assert hasattr(DungeonMindStatblockV1Client, "create_statblock")


def test_create_statblock_serializes_request_and_idempotency_key() -> None:
    # Request body is the Server-captured transcript leaf (dict). Full
    # CreateStatblockRequestV1 typing of structural HP/AC awaits contract sync.
    request = _fixture("create-request.json")
    captured: dict[str, object] = {}

    def handler(request_http: httpx.Request) -> httpx.Response:
        captured["method"] = request_http.method
        captured["path"] = request_http.url.path
        captured["body"] = json.loads(request_http.content.decode("utf-8"))
        assert request_http.headers.get(INTERNAL_KEY_HEADER) == SECRET
        return httpx.Response(200, json=_fixture("create-response.json"))

    client = _client(httpx.MockTransport(handler))
    result = client.create_statblock(request)
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/internal/dungeonbuddy/v1/statblocks"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["idempotency_key"] == "sbw07a-create-1"
    assert body["change_summary"]
    assert "definition" in body
    assert result.locator.provider == "dungeonmind"
    assert result.locator.statblock_id == "sb_000001"
    assert result.locator.revision_id == "rev_000002"
    assert result.locator.contract == "dungeonmind.dungeonbuddy-statblocks"
    assert result.locator.contract_version == "1.0.0"
    assert result.locator.definition_digest.startswith("sha256:")


def test_create_statblock_parses_six_field_locator() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_fixture("create-response.json"))

    result = _client(httpx.MockTransport(handler)).create_statblock(
        _fixture("create-request.json")
    )
    assert isinstance(result.locator, MechanicsLocatorV1)
    assert set(result.locator.model_dump().keys()) == {
        "provider",
        "statblock_id",
        "revision_id",
        "contract",
        "contract_version",
        "definition_digest",
    }
    assert "accepted_from_candidate_id" not in result.model_dump()
    assert "accepted_at" not in result.locator.model_dump()


def test_create_statblock_rejects_identity_mismatch() -> None:
    payload = _fixture("create-response.json")
    payload["statblock"]["statblock_id"] = "sb_other"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(StatblockIntegrationError) as exc_info:
        _client(httpx.MockTransport(handler)).create_statblock(
            _fixture("create-request.json")
        )
    assert exc_info.value.category == "downstream_unexpected"
    assert "statblock_id" in exc_info.value.message


def test_create_statblock_rejects_malformed_success_without_inventing_locator() -> None:
    payload = _fixture("create-response.json")
    del payload["revision"]["definition_digest"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(StatblockIntegrationError) as exc_info:
        _client(httpx.MockTransport(handler)).create_statblock(
            _fixture("create-request.json")
        )
    assert exc_info.value.category == "downstream_unexpected"
    assert "schema validation" in exc_info.value.message


def test_create_same_key_same_body_replay_returns_identical_locator() -> None:
    """Replay recorded Server first/second responses (not an unconditional mock)."""
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        same_mechanics_locator,
    )

    transcript = _fixture("server_transcripts/same_key_same_body_replay.json")
    request_body = transcript["request"]["json"]
    recorded = [
        transcript["first_response"],
        transcript["second_response"],
    ]
    # Server fact: recorded responses share exact identity fields.
    for field in (
        ("statblock", "statblock_id"),
        ("revision", "revision_id"),
        ("revision", "definition_digest"),
        ("revision", "contract"),
        ("revision", "contract_version"),
    ):
        left = recorded[0]["json"]
        right = recorded[1]["json"]
        cur_l, cur_r = left, right
        for key in field:
            cur_l = cur_l[key]
            cur_r = cur_r[key]
        assert cur_l == cur_r

    call_idx = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body == request_body
        assert body["idempotency_key"] == request_body["idempotency_key"]
        idx = call_idx["n"]
        call_idx["n"] += 1
        entry = recorded[idx]
        return httpx.Response(entry["status"], json=entry["json"])

    client = _client(httpx.MockTransport(handler))
    first = client.create_statblock(request_body)
    second = client.create_statblock(request_body)
    assert call_idx["n"] == 2
    assert same_mechanics_locator(first.locator, second.locator)
    assert first.locator.statblock_id == second.locator.statblock_id == "sb_000001"
    assert first.locator.revision_id == second.locator.revision_id == "rev_000002"
    assert first.locator.definition_digest == second.locator.definition_digest


def test_create_changed_body_conflict_is_not_terminal() -> None:
    """Conflict response comes from Server transcript for same key + changed body."""
    from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
        is_changed_body_idempotency_conflict,
        is_fixture_proven_terminal_non_begin,
    )

    transcript = _fixture("server_transcripts/same_key_changed_body_conflict.json")
    original_req = transcript["original_request"]["json"]
    changed_req = transcript["changed_request"]["json"]
    assert original_req["idempotency_key"] == changed_req["idempotency_key"]
    assert original_req["change_summary"] != changed_req["change_summary"]
    assert transcript["conflict_response"]["status"] == 409
    assert transcript["conflict_response"]["json"]["error"]["code"] == "idempotency_conflict"

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        if body == original_req:
            entry = transcript["original_response"]
            return httpx.Response(entry["status"], json=entry["json"])
        if body == changed_req:
            entry = transcript["conflict_response"]
            return httpx.Response(entry["status"], json=entry["json"])
        raise AssertionError("request body does not match Server transcript")

    client = _client(httpx.MockTransport(handler))
    original = client.create_statblock(original_req)
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.create_statblock(changed_req)
    error = exc_info.value
    assert error.category == "downstream_conflict"
    assert error.error_code == "idempotency_conflict"
    assert error.status_code == 409
    assert is_changed_body_idempotency_conflict(error)
    assert is_fixture_proven_terminal_non_begin(error) is False
    assert original.locator.statblock_id == transcript["original_response"]["json"]["statblock"]["statblock_id"]


def test_create_to_exact_read_identity_match() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        locator_from_exact_revision,
        same_mechanics_locator,
    )

    transcript = _fixture("server_transcripts/create_to_exact_read.json")
    create_body = transcript["create_response"]["json"]
    read_body = transcript["exact_read_response"]["json"]
    observed_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed_paths.append(request.url.path)
        if request.method == "POST" and request.url.path.endswith("/statblocks"):
            return httpx.Response(200, json=create_body)
        if request.method == "GET" and "/revisions/" in request.url.path:
            assert request.url.path == transcript["exact_read_request"]["path"]
            return httpx.Response(
                transcript["exact_read_response"]["status"], json=read_body
            )
        raise AssertionError(f"unexpected request {request.method} {request.url.path}")

    client = _client(httpx.MockTransport(handler))
    created = client.create_statblock(_fixture("create-request.json"))
    revision = client.get_exact_revision(
        created.locator.statblock_id, created.locator.revision_id
    )
    read_locator = locator_from_exact_revision(revision)
    assert same_mechanics_locator(created.locator, read_locator)
    assert revision.statblock_id == created.locator.statblock_id
    assert revision.revision_id == created.locator.revision_id
    assert revision.definition_digest == created.locator.definition_digest
    assert revision.contract == created.locator.contract
    assert revision.contract_version == created.locator.contract_version
    assert observed_paths == [
        "/api/internal/dungeonbuddy/v1/statblocks",
        transcript["exact_read_request"]["path"],
    ]
    assert not any("latest" in path for path in observed_paths)
    assert not any("corpus" in path for path in observed_paths)



def test_create_transport_and_auth_uncertainty_remain_non_terminal() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
        is_fixture_proven_terminal_non_begin,
    )

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(StatblockIntegrationError) as timeout_info:
        _client(httpx.MockTransport(timeout_handler)).create_statblock(
            _fixture("create-request.json")
        )
    assert timeout_info.value.category == "downstream_timeout"
    assert is_fixture_proven_terminal_non_begin(timeout_info.value) is False

    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"code": "unauthorized", "message": "missing key"}},
        )

    with pytest.raises(StatblockIntegrationError) as auth_info:
        _client(httpx.MockTransport(auth_handler)).create_statblock(
            _fixture("create-request.json")
        )
    assert auth_info.value.category == "downstream_authentication_failed"
    assert is_fixture_proven_terminal_non_begin(auth_info.value) is False


def test_create_persistence_validation_failed_is_terminal_candidate() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
        TERMINAL_NON_BEGIN_SPECS,
        is_fixture_proven_terminal_non_begin,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422, json=_fixture("create-persistence-validation-failed.json")
        )

    with pytest.raises(StatblockIntegrationError) as exc_info:
        _client(httpx.MockTransport(handler)).create_statblock(
            _fixture("create-request.json")
        )
    error = exc_info.value
    assert error.category == "downstream_validation_failed"
    assert error.error_code == "validation_failed"
    assert error.status_code == 422
    assert error.details.get("is_persistence_ready") is False
    assert is_fixture_proven_terminal_non_begin(error) is True
    assert any(
        spec.server_error_code == "validation_failed" for spec in TERMINAL_NON_BEGIN_SPECS
    )


def test_create_invalid_request_is_terminal_candidate() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
        is_fixture_proven_terminal_non_begin,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json=_fixture("create-invalid-request.json"))

    with pytest.raises(StatblockIntegrationError) as exc_info:
        _client(httpx.MockTransport(handler)).create_statblock(
            _fixture("create-request.json")
        )
    error = exc_info.value
    assert error.error_code == "invalid_request"
    assert error.status_code == 422
    assert is_fixture_proven_terminal_non_begin(error) is True


def test_create_terminal_inventory_does_not_infer_from_status_alone() -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
        CREATE_OUTCOME_INVENTORY,
        is_fixture_proven_terminal_non_begin,
        is_persistence_validation_terminal_non_begin,
    )
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        StatblockIntegrationError,
    )

    # Same HTTP status as a terminal fixture, but unrecognized code → non-terminal.
    unknown = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="unknown",
        status_code=422,
        error_code="some_unproven_code",
    )
    assert is_fixture_proven_terminal_non_begin(unknown) is False
    # Status alone with no code → non-terminal.
    status_only = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="no code",
        status_code=422,
        error_code=None,
    )
    assert is_fixture_proven_terminal_non_begin(status_only) is False

    # validation_failed without is_persistence_ready proof → non-terminal.
    missing_ready = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="Definition is not persistence-ready",
        status_code=422,
        error_code="validation_failed",
        details={},
    )
    assert is_persistence_validation_terminal_non_begin(missing_ready) is False
    assert is_fixture_proven_terminal_non_begin(missing_ready) is False

    contradictory = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="Definition is not persistence-ready",
        status_code=422,
        error_code="validation_failed",
        details={"is_persistence_ready": True},
    )
    assert is_persistence_validation_terminal_non_begin(contradictory) is False
    assert is_fixture_proven_terminal_non_begin(contradictory) is False

    malformed = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="Definition is not persistence-ready",
        status_code=422,
        error_code="validation_failed",
        details={"is_persistence_ready": "false"},
    )
    assert is_persistence_validation_terminal_non_begin(malformed) is False
    assert is_fixture_proven_terminal_non_begin(malformed) is False

    proven = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="Definition is not persistence-ready",
        status_code=422,
        error_code="validation_failed",
        details={"is_persistence_ready": False},
    )
    assert is_persistence_validation_terminal_non_begin(proven) is True
    assert is_fixture_proven_terminal_non_begin(proven) is True

    assert all(spec.proof for spec in CREATE_OUTCOME_INVENTORY)
    assert all(
        spec.fixture_kind == "server"
        for spec in CREATE_OUTCOME_INVENTORY
        if spec.terminal_non_begin == "yes"
    )
