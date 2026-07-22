"""Typed error taxonomy for DungeonMind statblock v1 transport."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StatblockIntegrationError(Exception):
    """Stable internal transport failure categories."""

    category: str
    message: str
    status_code: int | None = None
    error_code: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


def integration_disabled(message: str = "DungeonMind statblock integration is disabled") -> StatblockIntegrationError:
    return StatblockIntegrationError(category="integration_disabled", message=message)


def integration_misconfigured(message: str) -> StatblockIntegrationError:
    return StatblockIntegrationError(category="integration_misconfigured", message=message)


def downstream_unavailable(
    message: str = "DungeonMind statblock service unavailable",
    *,
    status_code: int | None = None,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_unavailable",
        message=message,
        status_code=status_code,
        error_code=error_code,
        details=details or {},
        retryable=True,
    )


def downstream_authentication_failed(
    message: str = "DungeonMind statblock authentication failed",
    *,
    status_code: int | None = None,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_authentication_failed",
        message=message,
        status_code=status_code,
    )


def downstream_timeout(message: str = "DungeonMind statblock request timed out") -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_timeout",
        message=message,
        retryable=True,
    )


def downstream_rate_limited(
    message: str = "DungeonMind statblock rate limited",
    *,
    status_code: int = 429,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_rate_limited",
        message=message,
        status_code=status_code,
        retryable=True,
    )


def downstream_invalid_request(
    message: str,
    *,
    status_code: int = 400,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_invalid_request",
        message=message,
        status_code=status_code,
        error_code=error_code,
        details=details or {},
    )


def downstream_validation_failed(
    message: str,
    *,
    status_code: int = 422,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_validation_failed",
        message=message,
        status_code=status_code,
        error_code=error_code,
        details=details or {},
    )


def downstream_not_found(
    message: str = "DungeonMind statblock resource not found",
    *,
    status_code: int = 404,
    error_code: str | None = None,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_not_found",
        message=message,
        status_code=status_code,
        error_code=error_code,
    )


def downstream_conflict(
    message: str,
    *,
    status_code: int = 409,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_conflict",
        message=message,
        status_code=status_code,
        error_code=error_code,
        details=details or {},
    )


def downstream_unexpected(
    message: str = "Unexpected DungeonMind statblock response",
    *,
    status_code: int | None = None,
) -> StatblockIntegrationError:
    return StatblockIntegrationError(
        category="downstream_unexpected",
        message=message,
        status_code=status_code,
    )
