from __future__ import annotations

import os
from typing import Protocol

import httpx

from src.statblocks.v2_contract import (
    ContractError,
    StatBlockDraftRenderRequest,
    StatBlockDraftRequest,
    StatBlockDraftResponse,
    StatBlockGeneratorHealth,
)

DEFAULT_DUNGEONMIND_SERVER_URL = "https://www.dungeonmind.net"
INTERNAL_KEY_HEADER = "X-DungeonBuddy-Internal-Key"
_DEFAULT_RENDER_RESPONSE = object()


class StatBlockGeneratorClientConfigError(ValueError):
    """Raised when the server-side statblock generator client is misconfigured."""


class StatBlockGeneratorProvider(Protocol):
    def health(self) -> StatBlockGeneratorHealth: ...

    def generate_draft(
        self, request: StatBlockDraftRequest
    ) -> StatBlockDraftResponse: ...

    def render_draft(
        self, request: StatBlockDraftRenderRequest
    ) -> StatBlockDraftResponse: ...


class StatBlockGeneratorHTTPError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response: StatBlockDraftResponse | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class DungeonMindServerStatBlockGeneratorClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        internal_api_key: str | None = None,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("DUNGEONMIND_SERVER_URL")
            or DEFAULT_DUNGEONMIND_SERVER_URL
        ).rstrip("/")
        self._internal_api_key = (
            internal_api_key
            if internal_api_key is not None
            else os.environ.get("DUNGEONBUDDY_INTERNAL_API_KEY")
        )
        if not self._internal_api_key:
            raise StatBlockGeneratorClientConfigError(
                "DUNGEONBUDDY_INTERNAL_API_KEY is required for the HTTP statblock generator provider"
            )
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "DungeonMindServerStatBlockGeneratorClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def health(self) -> StatBlockGeneratorHealth:
        response = self._request("GET", "/api/statblockgenerator/v2/health")
        if response.status_code >= 400:
            self._raise_http_error(response)
        return StatBlockGeneratorHealth.model_validate(response.json())

    def generate_draft(self, request: StatBlockDraftRequest) -> StatBlockDraftResponse:
        return self._post_draft_envelope(
            "/api/statblockgenerator/v2/generate-draft", request.model_dump(mode="json")
        )

    def render_draft(
        self, request: StatBlockDraftRenderRequest
    ) -> StatBlockDraftResponse:
        return self._post_draft_envelope(
            "/api/statblockgenerator/v2/render-draft", request.model_dump(mode="json")
        )

    def _post_draft_envelope(
        self, path: str, payload: dict[str, object]
    ) -> StatBlockDraftResponse:
        response = self._request("POST", path, json=payload)
        envelope = self._draft_response_from_http_response(response)
        if response.status_code >= 400:
            self._raise_http_error(response, envelope=envelope)
        return envelope

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        return self._client.request(
            method,
            f"{self.base_url}{path}",
            headers={INTERNAL_KEY_HEADER: self._internal_api_key or ""},
            **kwargs,
        )

    @staticmethod
    def _draft_response_from_http_response(
        response: httpx.Response,
    ) -> StatBlockDraftResponse:
        try:
            return StatBlockDraftResponse.model_validate(response.json())
        except Exception as exc:  # noqa: BLE001 - convert malformed remote failures into local envelope
            if response.status_code < 400:
                raise
            return StatBlockDraftResponse(
                success=False,
                draft=None,
                error=ContractError(
                    code=f"http_{response.status_code}",
                    message=f"StatBlockGenerator returned HTTP {response.status_code}",
                    details={"parse_error": exc.__class__.__name__},
                ),
            )

    @staticmethod
    def _raise_http_error(
        response: httpx.Response, *, envelope: StatBlockDraftResponse | None = None
    ) -> None:
        preserved = envelope
        if preserved is None:
            try:
                preserved = StatBlockDraftResponse.model_validate(response.json())
            except Exception:  # noqa: BLE001 - health may not return a draft envelope
                preserved = None
        if preserved is not None and preserved.error is not None:
            message = f"StatBlockGenerator HTTP {response.status_code}: {preserved.error.code}: {preserved.error.message}"
        else:
            message = f"StatBlockGenerator HTTP {response.status_code}"
        raise StatBlockGeneratorHTTPError(
            message, status_code=response.status_code, response=preserved
        )


class MockStatBlockGeneratorProvider:
    def __init__(
        self,
        *,
        health_response: StatBlockGeneratorHealth | None = None,
        generate_response: StatBlockDraftResponse | None = None,
        render_response: StatBlockDraftResponse
        | None
        | object = _DEFAULT_RENDER_RESPONSE,
    ) -> None:
        self.health_response = health_response or StatBlockGeneratorHealth(
            ok=True,
            status="ok",
            service="mock-statblock-generator",
            contract="command_board_draft_v2",
            generator_ready=True,
            openai_configured=False,
            supports=["generate-draft", "render-draft"],
        )
        self.generate_response = generate_response
        self.render_response = (
            None if render_response is _DEFAULT_RENDER_RESPONSE else render_response
        )
        self.generate_requests: list[StatBlockDraftRequest] = []
        self.render_requests: list[StatBlockDraftRenderRequest] = []

    def health(self) -> StatBlockGeneratorHealth:
        return self.health_response

    def generate_draft(self, request: StatBlockDraftRequest) -> StatBlockDraftResponse:
        self.generate_requests.append(request)
        if self.generate_response is None:
            return _mock_success_response("mock-generated-draft", mode=request.mode)
        return self.generate_response

    def render_draft(
        self, request: StatBlockDraftRenderRequest
    ) -> StatBlockDraftResponse:
        self.render_requests.append(request)
        if self.render_response is None:
            return _mock_success_response("mock-rendered-draft", mode=request.mode)
        return self.render_response


def statblock_generator_provider_from_env() -> StatBlockGeneratorProvider:
    provider = os.environ.get("STATBLOCK_GENERATOR_PROVIDER", "mock").strip().lower()
    if provider == "http":
        return DungeonMindServerStatBlockGeneratorClient()
    if provider == "mock":
        return MockStatBlockGeneratorProvider()
    raise StatBlockGeneratorClientConfigError(
        "STATBLOCK_GENERATOR_PROVIDER must be 'mock' or 'http'"
    )


def _mock_success_response(draft_id: str, *, mode: str) -> StatBlockDraftResponse:
    return StatBlockDraftResponse.model_validate(
        {
            "success": True,
            "draft": {
                "draft_id": draft_id,
                "lifecycle_state": "live_draft",
                "review_status": "needs_dm_review",
                "markdown": "## Mock Statblock\nA server-side mock statblock draft.",
                "statblock": {"name": "Mock Statblock"},
                "combat_defaults": {
                    "name": "Mock Statblock",
                    "armor_class": 12,
                    "hit_points": 7,
                    "passive_perception": 10,
                    "speed_summary": "30 ft.",
                    "senses_summary": "passive Perception 10",
                    "primary_actions": ["Mock Strike"],
                    "suggested_tactics": [
                        "Use as a deterministic server-side test double."
                    ],
                },
                "warnings": [],
                "provenance": {
                    "mode": mode,
                    "generator": "mock",
                    "source_refs": [],
                    "generation_info": {},
                },
            },
            "timestamp": "2026-06-09T00:00:00Z",
        }
    )
