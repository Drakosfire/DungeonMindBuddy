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
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.get_health()
    assert exc_info.value.category == "downstream_timeout"
    assert exc_info.value.retryable is True


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
        client.get_exact_revision("SB_UPPER", "rev_fixture1")
    assert exc_info.value.category == "downstream_invalid_request"


def test_exact_revision_fixture_retains_identity() -> None:
    payload = _fixture("exact-revision-response.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get(INTERNAL_KEY_HEADER) == SECRET
        assert request.url.path.endswith("/statblocks/sb_fixture1/revisions/rev_fixture1")
        return httpx.Response(200, json=payload)

    client = _client(httpx.MockTransport(handler))
    revision = client.get_exact_revision("sb_fixture1", "rev_fixture1")
    assert revision.statblock_id == "sb_fixture1"
    assert revision.revision_id == "rev_fixture1"
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


def test_client_exposes_only_sbw01_operations() -> None:
    assert not hasattr(DungeonMindStatblockV1Client, "generate_candidate")
    assert not hasattr(DungeonMindStatblockV1Client, "get_candidate")


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
