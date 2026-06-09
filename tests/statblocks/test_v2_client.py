from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from src.statblocks.v2_client import (
    INTERNAL_KEY_HEADER,
    DungeonMindServerStatBlockGeneratorClient,
    MockStatBlockGeneratorProvider,
    StatBlockGeneratorClientConfigError,
    StatBlockGeneratorHTTPError,
)
from src.statblocks.v2_contract import (
    StatBlockDraftRenderRequest,
    StatBlockDraftRequest,
    StatBlockDraftResponse,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SECRET = "super-secret-internal-key"


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _client_with_handler(
    handler: httpx.MockTransport,
) -> DungeonMindServerStatBlockGeneratorClient:
    return DungeonMindServerStatBlockGeneratorClient(
        base_url="https://statblocks.example.test/",
        internal_api_key=SECRET,
        http_client=httpx.Client(transport=handler),
    )


def test_health_calls_v2_health_with_internal_key() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["method"] = request.method
        seen["key"] = request.headers.get(INTERNAL_KEY_HEADER)
        return httpx.Response(
            200, json={"ok": True, "status": "ok", "service": "statblockgenerator"}
        )

    client = _client_with_handler(httpx.MockTransport(handler))

    health = client.health()

    assert health.ok is True
    assert seen == {
        "url": "https://statblocks.example.test/api/statblockgenerator/v2/health",
        "method": "GET",
        "key": SECRET,
    }


def test_generate_draft_posts_v2_generate_draft_with_internal_key() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["method"] = request.method
        seen["key"] = request.headers.get(INTERNAL_KEY_HEADER)
        seen["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200, json=_fixture("generated_draft_response.fixture.json")
        )

    client = _client_with_handler(httpx.MockTransport(handler))

    response = client.generate_draft(StatBlockDraftRequest(mode="generate_from_prompt"))

    assert response.success is True
    assert (
        seen["url"]
        == "https://statblocks.example.test/api/statblockgenerator/v2/generate-draft"
    )
    assert seen["method"] == "POST"
    assert seen["key"] == SECRET
    assert seen["json"]["mode"] == "generate_from_prompt"


def test_render_draft_posts_v2_render_draft_with_internal_key() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["method"] = request.method
        seen["key"] = request.headers.get(INTERNAL_KEY_HEADER)
        return httpx.Response(
            200, json=_fixture("rendered_draft_response.fixture.json")
        )

    client = _client_with_handler(httpx.MockTransport(handler))

    response = client.render_draft(
        StatBlockDraftRenderRequest(statblock={"name": "Clockwork Scout"})
    )

    assert response.success is True
    assert seen == {
        "url": "https://statblocks.example.test/api/statblockgenerator/v2/render-draft",
        "method": "POST",
        "key": SECRET,
    }


def test_missing_internal_key_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUNGEONBUDDY_INTERNAL_API_KEY", raising=False)

    with pytest.raises(
        StatBlockGeneratorClientConfigError, match="DUNGEONBUDDY_INTERNAL_API_KEY"
    ):
        DungeonMindServerStatBlockGeneratorClient(
            base_url="https://statblocks.example.test", internal_api_key=""
        )


@pytest.mark.parametrize("status_code", [401, 403, 501, 500])
def test_error_responses_preserve_v2_error_envelope_without_leaking_key(
    status_code: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={
                "success": False,
                "draft": None,
                "error": {
                    "code": f"http_{status_code}",
                    "message": "The producer rejected the request.",
                    "details": {"status": status_code},
                },
                "timestamp": "2026-06-09T12:30:00Z",
            },
        )

    client = _client_with_handler(httpx.MockTransport(handler))

    with pytest.raises(StatBlockGeneratorHTTPError) as exc_info:
        client.generate_draft(StatBlockDraftRequest(mode="generate_from_prompt"))

    exc = exc_info.value
    assert exc.status_code == status_code
    assert exc.response is not None
    assert exc.response.error is not None
    assert exc.response.error.code == f"http_{status_code}"
    assert "producer rejected" in str(exc)
    assert SECRET not in str(exc)


def test_malformed_server_error_becomes_meaningful_local_envelope_without_leaking_key() -> (
    None
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream failed")

    client = _client_with_handler(httpx.MockTransport(handler))

    with pytest.raises(StatBlockGeneratorHTTPError) as exc_info:
        client.render_draft(StatBlockDraftRenderRequest(statblock={"name": "Broken"}))

    exc = exc_info.value
    assert exc.response is not None
    assert exc.response.error is not None
    assert exc.response.error.code == "http_500"
    assert SECRET not in str(exc)


def test_mock_provider_records_requests_and_returns_stable_responses() -> None:
    provider = MockStatBlockGeneratorProvider()

    health = provider.health()
    generated = provider.generate_draft(
        StatBlockDraftRequest(mode="quick_reinforcement")
    )
    rendered = provider.render_draft(
        StatBlockDraftRenderRequest(statblock={"name": "Mock"})
    )

    assert health.status == "ok"
    assert health.contract == "command_board_draft_v2"
    assert health.generator_ready is True
    assert health.supports == ["generate-draft", "render-draft"]
    assert isinstance(generated, StatBlockDraftResponse)
    assert isinstance(rendered, StatBlockDraftResponse)
    assert generated.draft is not None
    assert rendered.draft is not None
    assert generated.draft.draft_id == "mock-generated-draft"
    assert rendered.draft.draft_id == "mock-rendered-draft"
    assert rendered.draft.provenance.mode == "render_existing"
    assert provider.generate_requests[0].mode == "quick_reinforcement"
    assert provider.render_requests[0].statblock == {"name": "Mock"}


def test_mock_provider_does_not_reuse_generate_response_for_render_unless_overridden() -> (
    None
):
    generate_response = StatBlockDraftResponse.model_validate(
        _fixture("generated_draft_response.fixture.json")
    )
    provider = MockStatBlockGeneratorProvider(generate_response=generate_response)

    generated = provider.generate_draft(
        StatBlockDraftRequest(mode="generate_from_prompt")
    )
    rendered = provider.render_draft(
        StatBlockDraftRenderRequest(statblock={"name": "Mock"})
    )

    assert generated.draft is not None
    assert rendered.draft is not None
    assert generated.draft.draft_id == "draft-generated-ember-wolf"
    assert rendered.draft.draft_id == "mock-rendered-draft"
    assert rendered.draft.provenance.mode == "render_existing"
