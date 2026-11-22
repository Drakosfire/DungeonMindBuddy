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
    integration_misconfigured,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    StatblockDefinitionV1Input,
    ValidationResponseV1,
)
from apps.live_control_server.main import create_app
from apps.live_control_server.services import statblock_definition_validation as validation_service
from apps.live_control_server.services.statblock_definition_validation import (
    ValidateDefinitionBuddyRequestV1,
    associate_validation_digest,
    validate_definition,
)

FIXTURES = Path(__file__).parent / "fixtures" / "statblocks" / "v1"
SECRET = "test-internal-key"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _definition() -> StatblockDefinitionV1Input:
    return StatblockDefinitionV1Input.model_validate(
        _fixture("candidate-response.json")["definition"]
    )


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
        definition=_definition(),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.definition_digest == invalid["definition_digest"]
    assert result.validation_receipt is not None
    assert result.validation_receipt.status == "invalid"
    issues = result.validation_receipt.issues or []
    assert any(issue.severity == "error" for issue in issues)
    assert any(issue.severity == "warning" for issue in issues)


def test_validate_definition_service_maps_transport_failure() -> None:
    class FakeClient:
        def validate_definition(self, body):
            raise downstream_timeout()

    result = validate_definition(
        definition=_definition(),
        client=FakeClient(),  # type: ignore[arg-type]
    )
    assert result.outcome == "failure"
    assert result.failure_category == "downstream_timeout"
    assert result.validation_receipt is None


def test_variant_review_reports_transport_failure_without_private_details(caplog) -> None:
    from apps.live_control_server.services.conversation_variant_save import validate_variant_review

    class FakeClient:
        def validate_definition(self, body):
            raise StatblockIntegrationError(category="downstream_timeout", message="private detail")

    assert validate_variant_review(_definition(), client=FakeClient()) is None
    assert "category=downstream_timeout" in caplog.text
    assert "private detail" not in caplog.text


@pytest.mark.parametrize("add_local_target", [False, True])
def test_manual_rule_replacement_resolves_only_local_multiattack_targets(add_local_target) -> None:
    from application_state.agent_conversation.native_completion import _apply_statblock_rule_edits

    definition = _definition().model_dump(mode="json")
    original = definition["rule_elements"][0]
    original["automation_support"] = "manual"
    original["mechanic"] = {"kind": "human_adjudicated", "adjudication_tags": ["summon"]}
    replacement = {
        **original,
        "rules_text": "Three summoned creatures emerge from the floor.",
        "mechanic": {
            "kind": "multiattack",
            "sequences": [{"element_key": "minion", "count": 3, "choice_group": None}],
        },
    }
    additions = [{**original, "key": "minion"}] if add_local_target else []
    edited = _apply_statblock_rule_edits(
        definition, {"replace_rules": [replacement], "add_rules": additions}
    )["rule_elements"][0]
    assert edited["mechanic"] == (replacement if add_local_target else original)["mechanic"]
    assert edited["rules_text"] == replacement["rules_text"]
    assert definition["rule_elements"][0]["mechanic"]["kind"] == "human_adjudicated"


def test_validate_definition_service_maps_constructor_misconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production path constructs the client; misconfig must not become an unhandled 500."""

    def boom() -> DungeonMindStatblockV1Client:
        raise integration_misconfigured("statblock integration base_url is missing")

    monkeypatch.setattr(validation_service, "DungeonMindStatblockV1Client", boom)
    result = validate_definition(definition=_definition())
    assert result.outcome == "failure"
    assert result.failure_category == "integration_misconfigured"
    assert result.validation_receipt is None
    assert "base_url" in (result.failure_message or "")


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
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
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


def test_validate_definition_route_rejects_extra_definition_fields(monkeypatch) -> None:
    definition = _fixture("candidate-response.json")["definition"]
    definition = {**definition, "unexpected_top_level": True}
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    response = client.post(
        "/api/live/statblock-definitions:validate",
        json={"definition": definition},
    )
    assert response.status_code == 422


def test_buddy_request_forbids_untyped_definition_bags() -> None:
    with pytest.raises(Exception):
        ValidateDefinitionBuddyRequestV1.model_validate(
            {"definition": {"identity": {"name": "partial"}}}
        )


def test_client_exposes_validate_definition_for_sbw05a() -> None:
    assert hasattr(DungeonMindStatblockV1Client, "validate_definition")
