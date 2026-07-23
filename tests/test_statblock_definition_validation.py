from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.config import (
    INTERNAL_KEY_HEADER,
    StatblockIntegrationConfig,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
    downstream_timeout,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    ValidationResponseV1,
)
from apps.live_control_server.main import create_app
from apps.live_control_server.services import statblock_definition_validation as validation_service
from apps.live_control_server.services.statblock_definition_validation import (
    associate_validation_digest,
    validate_definition,
)

FIXTURES = Path(__file__).parent / "fixtures" / "statblocks" / "v1"
SECRET = "test-internal-key"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _client(transport: httpx.MockTransport) -> DungeonMindStatblockV1Client:
    return DungeonMindStatblockV1Client(
        config=StatblockIntegrationConfig(
            enabled=True,
            base_url="https://statblocks.test",
            internal_api_key=SECRET,
            timeout_seconds=5.0,
        ),
        http_client=httpx.Client(transport=transport, timeout=5.0),
    )


def test_validate_definition_client_binds_matching_digest() -> None:
    payload = _fixture("validate-response.json")
    definition = _fixture("candidate-response.json")["definition"]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/statblock-definitions:validate")
        assert request.headers.get(INTERNAL_KEY_HEADER) == SECRET
        body = json.loads(request.content.decode("utf-8"))
        assert body["definition"]["identity"]["name"] == "Ironhide Brute"
        return httpx.Response(200, json=payload)

    client = _client(httpx.MockTransport(handler))
    response = client.validate_definition({"definition": definition})
    assert response.definition_digest == payload["definition_digest"]
    assert (
        response.validation_receipt.definition_digest == response.definition_digest
    )
    assert associate_validation_digest(response) == response.definition_digest


def test_validate_definition_client_rejects_digest_mismatch() -> None:
    payload = _fixture("validate-response.json")
    payload["definition_digest"] = "sha256:" + ("a" * 64)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(StatblockIntegrationError) as exc_info:
        client.validate_definition(
            {"definition": _fixture("candidate-response.json")["definition"]}
        )
    assert exc_info.value.category == "downstream_unexpected"


def test_validate_definition_service_maps_invalid_receipt_as_success() -> None:
    """Server validation errors are HTTP 200 with issues, not Buddy transport failure."""
    invalid = _fixture("validate-response-invalid.json")

    class FakeClient:
        def validate_definition(self, body):
            return ValidationResponseV1.model_validate(invalid)

    result = validate_definition(
        definition=_fixture("candidate-response.json")["definition"],
        client=FakeClient(),  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.definition_digest == invalid["definition_digest"]
    assert result.validation_receipt is not None
    assert result.validation_receipt["status"] == "invalid"
    issues = result.validation_receipt["issues"]
    assert any(issue["severity"] == "error" for issue in issues)
    assert any(issue["severity"] == "warning" for issue in issues)


def test_validate_definition_service_maps_transport_failure() -> None:
    class FakeClient:
        def validate_definition(self, body):
            raise downstream_timeout()

    result = validate_definition(
        definition=_fixture("candidate-response.json")["definition"],
        client=FakeClient(),  # type: ignore[arg-type]
    )
    assert result.outcome == "failure"
    assert result.failure_category == "downstream_timeout"
    assert result.validation_receipt is None


def test_validate_definition_route(monkeypatch) -> None:
    invalid = _fixture("validate-response-invalid.json")

    class FakeClient:
        def validate_definition(self, body):
            return ValidationResponseV1.model_validate(invalid)

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        validation_service,
        "DungeonMindStatblockV1Client",
        lambda: FakeClient(),
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/live/statblock-definitions:validate",
        json={"definition": _fixture("candidate-response.json")["definition"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "dmb_statblock_definition_validation_v1"
    assert body["outcome"] == "success"
    assert body["definition_digest"] == invalid["definition_digest"]
    assert body["validation_receipt"]["status"] == "invalid"


def test_client_exposes_validate_definition_for_sbw05a() -> None:
    assert hasattr(DungeonMindStatblockV1Client, "validate_definition")
