"""Server-owned DungeonMind statblock v1 HTTP client."""
from __future__ import annotations

import json
from typing import Any, Protocol, TypeVar

import httpx

from apps.live_control_server.integrations.dungeonmind_statblocks.config import (
    API_PREFIX,
    INTERNAL_KEY_HEADER,
    StatblockIntegrationConfig,
    StatblockIntegrationConfigError,
    load_statblock_integration_config,
    validate_candidate_id,
    validate_revision_id,
    validate_statblock_id,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
    downstream_authentication_failed,
    downstream_conflict,
    downstream_invalid_request,
    downstream_not_found,
    downstream_rate_limited,
    downstream_timeout,
    downstream_unexpected,
    downstream_unavailable,
    downstream_validation_failed,
    integration_disabled,
    integration_misconfigured,
    redact_secret,
    redact_secret_in_value,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ErrorEnvelopeV1,
    ExactRevisionResourceV1,
    HealthResponseV1,
    ReadinessResponseV1,
    StrictModel,
)

# Health/readiness envelopes are tiny; exact-revision payloads include definition.
MAX_RESPONSE_BODY_BYTES = 1_048_576

ModelT = TypeVar("ModelT", bound=StrictModel)


class StatblockV1Client(Protocol):
    def get_health(self) -> HealthResponseV1: ...

    def get_readiness(self) -> ReadinessResponseV1: ...

    def get_exact_revision(
        self, statblock_id: str, revision_id: str
    ) -> ExactRevisionResourceV1: ...

    def generate_candidate(self, body: dict[str, Any]) -> dict[str, Any]: ...

    def get_candidate(self, candidate_id: str) -> dict[str, Any]: ...


class DungeonMindStatblockV1Client:
    """Authenticated transport for DungeonMindServer statblock v1 routes."""

    def __init__(
        self,
        *,
        config: StatblockIntegrationConfig | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        config_error: str | None = None
        try:
            self._config = config if config is not None else load_statblock_integration_config()
        except StatblockIntegrationConfigError as exc:
            config_error = str(exc)
        if config_error is not None:
            # Raise outside the except block so no secret-bearing cause/context is retained.
            raise integration_misconfigured(config_error)
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=self._config.timeout_seconds,
            follow_redirects=False,
        )

    @property
    def config(self) -> StatblockIntegrationConfig:
        return self._config

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get_health(self) -> HealthResponseV1:
        payload = self._request_json("GET", f"{API_PREFIX}/statblocks/health")
        return self._parse_model(HealthResponseV1, payload)

    def get_readiness(self) -> ReadinessResponseV1:
        status, body = self._request_bytes(
            "GET",
            f"{API_PREFIX}/statblocks/health/ready",
        )
        if status == 200:
            payload = self._decode_json(body, status_code=status)
            return self._parse_model(ReadinessResponseV1, payload)
        if status == 503:
            # Server may return a legitimate not_ready readiness body or an
            # ErrorEnvelopeV1 (auth/config). Invalid shapes fail closed.
            payload = self._decode_json(body, status_code=status)
            try:
                return ReadinessResponseV1.model_validate(payload)
            except Exception:
                pass
            envelope: ErrorEnvelopeV1 | None
            try:
                envelope = ErrorEnvelopeV1.model_validate(payload)
            except Exception:
                envelope = None
            if envelope is None:
                raise downstream_unexpected(
                    "downstream response failed schema validation",
                    status_code=status,
                )
            raise downstream_unavailable(
                self._public_text(envelope.error.message),
                status_code=status,
                error_code=self._public_text(envelope.error.code),
                details=self._public_details(envelope.error.details or {}),
            )
        raise self._map_error_response(status, body)

    def get_exact_revision(
        self, statblock_id: str, revision_id: str
    ) -> ExactRevisionResourceV1:
        invalid_id: str | None = None
        safe_statblock_id = ""
        safe_revision_id = ""
        try:
            safe_statblock_id = validate_statblock_id(statblock_id)
            safe_revision_id = validate_revision_id(revision_id)
        except ValueError as exc:
            invalid_id = str(exc)
        if invalid_id is not None:
            raise downstream_invalid_request(invalid_id)
        payload = self._request_json(
            "GET",
            f"{API_PREFIX}/statblocks/{safe_statblock_id}/revisions/{safe_revision_id}",
        )
        revision = self._parse_model(ExactRevisionResourceV1, payload)
        if (
            revision.statblock_id != safe_statblock_id
            or revision.revision_id != safe_revision_id
        ):
            raise downstream_unexpected(
                "exact revision response identity does not match request"
            )
        return revision

    def generate_candidate(self, body: dict[str, Any]) -> dict[str, Any]:
        """SBW03: POST candidate generation; transport returns the Server JSON object."""
        payload = self._request_json(
            "POST",
            f"{API_PREFIX}/statblock-candidates:generate",
            json_body=body,
        )
        if not isinstance(payload, dict):
            raise downstream_unexpected("generate candidate response must be an object")
        return payload

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        """SBW03: GET candidate by published `cand_*` identity."""
        try:
            safe_candidate_id = validate_candidate_id(candidate_id)
        except ValueError as exc:
            raise downstream_invalid_request(str(exc)) from exc
        payload = self._request_json(
            "GET",
            f"{API_PREFIX}/statblock-candidates/{safe_candidate_id}",
        )
        if not isinstance(payload, dict):
            raise downstream_unexpected("candidate response must be an object")
        return payload

    def _ensure_ready(self) -> None:
        if not self._config.enabled:
            raise integration_disabled()
        if not self._config.is_configured:
            raise integration_misconfigured(
                "DungeonMind statblock integration is not fully configured"
            )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        allow_statuses: set[int] | None = None,
    ) -> Any:
        status, body = self._request_bytes(method, path, json_body=json_body)
        allowed = allow_statuses or {200}
        if status in allowed:
            return self._decode_json(body, status_code=status)
        raise self._map_error_response(status, body)

    def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> tuple[int, bytes]:
        self._ensure_ready()
        url = f"{self._config.base_url}{path}"
        headers = {INTERNAL_KEY_HEADER: self._config.internal_api_key}
        mapped_error: StatblockIntegrationError | None = None
        try:
            # Enforce timeout and no-redirect per request so injected clients
            # cannot override the integration's transport bounds.
            with self._client.stream(
                method,
                url,
                headers=headers,
                json=json_body,
                timeout=self._config.timeout_seconds,
                follow_redirects=False,
            ) as response:
                if 300 <= response.status_code < 400:
                    response.close()
                    raise downstream_unexpected(
                        "downstream redirect refused",
                        status_code=response.status_code,
                    )
                body = self._read_bounded_body(response)
                return response.status_code, body
        except StatblockIntegrationError:
            raise
        except httpx.TimeoutException:
            # httpx exceptions retain the request (including auth headers).
            mapped_error = downstream_timeout()
        except httpx.HTTPError as exc:
            mapped_error = downstream_unavailable(
                self._public_text(str(exc) or "transport error") or "transport error"
            )
        # Raise outside except blocks so __cause__/__context__ stay empty.
        assert mapped_error is not None
        raise mapped_error

    def _read_bounded_body(self, response: httpx.Response) -> bytes:
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = -1
            if declared > MAX_RESPONSE_BODY_BYTES:
                response.close()
                raise downstream_unexpected(
                    "downstream response exceeds bounded body limit",
                    status_code=response.status_code,
                )

        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > MAX_RESPONSE_BODY_BYTES:
                response.close()
                raise downstream_unexpected(
                    "downstream response exceeds bounded body limit",
                    status_code=response.status_code,
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def _decode_json(self, body: bytes, *, status_code: int) -> Any:
        try:
            return json.loads(body)
        except ValueError:
            # Decode errors retain the raw document; raise outside that context.
            pass
        raise downstream_unexpected(
            "downstream response is not JSON",
            status_code=status_code,
        )

    def _parse_model(self, model_type: type[ModelT], payload: Any) -> ModelT:
        try:
            return model_type.model_validate(payload)
        except Exception:
            # Validation errors retain the rejected payload; raise outside that context.
            pass
        raise downstream_unexpected(
            "downstream response failed schema validation"
        )

    def _map_error_response(
        self, status: int, body: bytes
    ) -> StatblockIntegrationError:
        if status in {401, 403}:
            return downstream_authentication_failed(status_code=status)
        if status == 404:
            code, message, details = self._safe_error_parts(body)
            return downstream_not_found(
                message or "not found", status_code=status, error_code=code
            )
        if status == 409:
            code, message, details = self._safe_error_parts(body)
            return downstream_conflict(
                message or "conflict",
                status_code=status,
                error_code=code,
                details=details,
            )
        if status == 422:
            code, message, details = self._safe_error_parts(body)
            return downstream_validation_failed(
                message or "validation failed",
                status_code=status,
                error_code=code,
                details=details,
            )
        if status == 429:
            return downstream_rate_limited(status_code=status)
        if status == 400:
            code, message, details = self._safe_error_parts(body)
            return downstream_invalid_request(
                message or "invalid request",
                status_code=status,
                error_code=code,
                details=details,
            )
        if status >= 500:
            code, message, details = self._safe_error_parts(body)
            if code is not None:
                return downstream_unavailable(
                    message or f"downstream HTTP {status}",
                    status_code=status,
                    error_code=code,
                    details=details,
                )
            return downstream_unexpected(
                "downstream response failed schema validation",
                status_code=status,
            )
        return downstream_unexpected(
            f"unexpected downstream HTTP {status}",
            status_code=status,
        )

    def _public_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        return redact_secret(value, self._config.internal_api_key)

    def _public_details(self, details: dict[str, Any]) -> dict[str, Any]:
        redacted = redact_secret_in_value(details, self._config.internal_api_key)
        return redacted if isinstance(redacted, dict) else {}

    def _safe_error_parts(
        self, body: bytes
    ) -> tuple[str | None, str | None, dict[str, Any]]:
        # Only structured ErrorEnvelopeV1 fields are preserved; raw body text
        # is never reflected into exceptions (secret / unbounded-content risk).
        try:
            payload = json.loads(body)
        except ValueError:
            return None, None, {}
        try:
            envelope = ErrorEnvelopeV1.model_validate(payload)
        except Exception:
            return None, None, {}
        return (
            self._public_text(envelope.error.code),
            self._public_text(envelope.error.message),
            self._public_details(envelope.error.details or {}),
        )


def build_statblock_v1_client(
    *,
    http_client: httpx.Client | None = None,
) -> DungeonMindStatblockV1Client:
    return DungeonMindStatblockV1Client(http_client=http_client)
