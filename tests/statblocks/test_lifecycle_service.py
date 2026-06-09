from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.statblocks.lifecycle_artifact import StatblockBreadcrumb
from src.statblocks.lifecycle_commands import (
    STATBLOCK_DRAFT_GENERATE,
    STATBLOCK_DRAFT_RENDER,
    STATBLOCK_GENERATOR_HEALTH,
)
from src.statblocks.lifecycle_service import (
    StatblockLifecycleCommandRequest,
    StatblockLifecycleService,
)
from src.statblocks.v2_client import MockStatBlockGeneratorProvider, StatBlockGeneratorHTTPError
from src.statblocks.v2_contract import (
    ContractError,
    StatBlockDraftResponse,
    StatBlockGeneratorHealth,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SECRET = "buddy-secret-should-not-leak"


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _response_fixture(name: str = "generated_draft_response.fixture.json") -> StatBlockDraftResponse:
    return StatBlockDraftResponse.model_validate(_fixture(name))


def test_health_command_calls_provider_health_and_returns_ok() -> None:
    provider = MockStatBlockGeneratorProvider(
        health_response=StatBlockGeneratorHealth(status="ok", service="unit-test")
    )
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(command_type=STATBLOCK_GENERATOR_HEALTH)
    )

    assert result.status == "ok"
    assert result.health is not None
    assert result.health.service == "unit-test"
    assert result.response is None
    assert result.artifact is None


def test_generate_command_validates_payload_and_calls_provider_generate() -> None:
    provider = MockStatBlockGeneratorProvider()
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_GENERATE,
            payload=_fixture("generate_draft_request.fixture.json"),
        )
    )

    assert result.status == "ok"
    assert result.response is not None
    assert result.response.success is True
    assert provider.generate_requests[0].request_id == "buddy-smoke-generate-ember-wolf"
    assert provider.generate_requests[0].mode == "generate_from_prompt"


def test_render_command_validates_payload_and_calls_provider_render() -> None:
    provider = MockStatBlockGeneratorProvider()
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_RENDER,
            payload=_fixture("render_draft_request.fixture.json"),
        )
    )

    assert result.status == "ok"
    assert result.response is not None
    assert result.response.success is True
    assert provider.render_requests[0].request_id == "buddy-smoke-render-clockwork-scout"
    assert provider.render_requests[0].statblock["name"] == "Clockwork Scout"


def test_successful_generate_maps_to_artifact_when_requested() -> None:
    provider = MockStatBlockGeneratorProvider(generate_response=_response_fixture())
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_GENERATE,
            payload=_fixture("generate_draft_request.fixture.json"),
            requested_by="planning_task",
        )
    )

    assert result.status == "ok"
    assert result.response is not None
    assert result.artifact is not None
    assert result.artifact.draft_id == "draft-generated-ember-wolf"
    assert result.artifact.title == "Ember Wolf"
    assert result.artifact.created_by == "planning_task"


def test_successful_render_maps_to_artifact_when_requested() -> None:
    provider = MockStatBlockGeneratorProvider(
        render_response=_response_fixture("rendered_draft_response.fixture.json")
    )
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_RENDER,
            payload=_fixture("render_draft_request.fixture.json"),
            requested_by="human",
        )
    )

    assert result.status == "ok"
    assert result.response is not None
    assert result.artifact is not None
    assert result.artifact.draft_id == "draft-rendered-clockwork-scout"
    assert result.artifact.created_by == "human"


def test_as_artifact_false_returns_response_without_artifact() -> None:
    provider = MockStatBlockGeneratorProvider(generate_response=_response_fixture())
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_GENERATE,
            payload=_fixture("generate_draft_request.fixture.json"),
            as_artifact=False,
        )
    )

    assert result.status == "ok"
    assert result.response is not None
    assert result.artifact is None
    assert result.diagnostics == ["artifact mapping skipped because as_artifact is false"]


def test_breadcrumbs_are_passed_through_to_artifact() -> None:
    breadcrumb = StatblockBreadcrumb(
        label="Smoke Test", source="pytest", target="statblock-workbench"
    )
    provider = MockStatBlockGeneratorProvider(generate_response=_response_fixture())
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_GENERATE,
            payload=_fixture("generate_draft_request.fixture.json"),
            breadcrumbs=[breadcrumb],
        )
    )

    assert result.artifact is not None
    assert result.artifact.breadcrumbs == [breadcrumb]


def test_unknown_requested_by_conservatively_maps_to_agent() -> None:
    provider = MockStatBlockGeneratorProvider(generate_response=_response_fixture())
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_GENERATE,
            payload=_fixture("generate_draft_request.fixture.json"),
            requested_by="untrusted-caller",
        )
    )

    assert result.artifact is not None
    assert result.artifact.created_by == "agent"


def test_unsupported_command_returns_structured_result_without_calling_provider() -> None:
    provider = MockStatBlockGeneratorProvider()
    service = StatblockLifecycleService(provider)

    result = service.execute(
        StatblockLifecycleCommandRequest(command_type="statblock.draft.store")
    )

    assert result.status == "unsupported"
    assert result.error is not None
    assert result.error.code == "unsupported_command"
    assert provider.generate_requests == []
    assert provider.render_requests == []


def test_http_error_with_preserved_v2_envelope_returns_safe_command_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", SECRET)
    response = StatBlockDraftResponse(
        success=False,
        error=ContractError(
            code="producer_failed",
            message="Producer rejected the draft request.",
            details={"safe": True},
        ),
    )

    class FailingProvider(MockStatBlockGeneratorProvider):
        def generate_draft(self, request):  # type: ignore[no-untyped-def]
            raise StatBlockGeneratorHTTPError(
                f"HTTP 500 failed with {SECRET}", status_code=500, response=response
            )

    result = StatblockLifecycleService(FailingProvider()).execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_GENERATE,
            payload=_fixture("generate_draft_request.fixture.json"),
        )
    )

    dumped = result.model_dump_json()
    assert result.status == "error"
    assert result.response == response
    assert result.error is not None
    assert result.error.code == "producer_failed"
    assert SECRET not in dumped


def test_http_error_without_envelope_redacts_known_fake_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", SECRET)

    class FailingProvider(MockStatBlockGeneratorProvider):
        def render_draft(self, request):  # type: ignore[no-untyped-def]
            raise StatBlockGeneratorHTTPError(
                f"HTTP 401 unauthorized for {SECRET}", status_code=401
            )

    result = StatblockLifecycleService(FailingProvider()).execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_RENDER,
            payload=_fixture("render_draft_request.fixture.json"),
        )
    )

    dumped = result.model_dump_json()
    assert result.status == "error"
    assert result.error is not None
    assert result.error.code == "http_error"
    assert "[redacted]" in dumped
    assert SECRET not in dumped


def test_validation_error_returns_safe_command_error_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", SECRET)
    payload = {"request_id": SECRET, "mode": "render_existing"}

    result = StatblockLifecycleService(MockStatBlockGeneratorProvider()).execute(
        StatblockLifecycleCommandRequest(
            command_type=STATBLOCK_DRAFT_RENDER,
            payload=payload,
        )
    )

    dumped = result.model_dump_json()
    assert result.status == "error"
    assert result.error is not None
    assert result.error.code == "invalid_payload"
    assert result.error.details == {"error_count": 1}
    assert SECRET not in dumped
