"""Centralized wrapper for OpenAI API calls used by DungeonMindBuddy."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApiCallResult:
    """Raw response plus lightweight request metadata."""

    action: str
    elapsed_ms: float
    response: Any


class DungeonMindApiClient:
    """
    Thin central client for API calls.

    This wrapper intentionally stays lightweight so existing modules can migrate one
    call-site at a time while still gaining a shared interception point for retries,
    tracing, and policy enforcement.
    """

    def __init__(self, raw_client: Any):
        self._raw_client = raw_client

    @classmethod
    def wrap(cls, client_or_wrapper: Any) -> "DungeonMindApiClient":
        if isinstance(client_or_wrapper, cls):
            return client_or_wrapper
        return cls(client_or_wrapper)

    @property
    def raw_client(self) -> Any:
        return self._raw_client

    def responses_create(self, *, action: str, **kwargs: Any) -> ApiCallResult:
        t0 = time.perf_counter()
        response = self._raw_client.responses.create(**kwargs)
        return ApiCallResult(
            action=action,
            elapsed_ms=(time.perf_counter() - t0) * 1000.0,
            response=response,
        )

    def responses_parse(self, *, action: str, **kwargs: Any) -> ApiCallResult:
        t0 = time.perf_counter()
        response = self._raw_client.responses.parse(**kwargs)
        return ApiCallResult(
            action=action,
            elapsed_ms=(time.perf_counter() - t0) * 1000.0,
            response=response,
        )

    async def responses_parse_async(self, *, action: str, **kwargs: Any) -> ApiCallResult:
        t0 = time.perf_counter()
        response = await self._raw_client.responses.parse(**kwargs)
        return ApiCallResult(
            action=action,
            elapsed_ms=(time.perf_counter() - t0) * 1000.0,
            response=response,
        )

    def chat_completions_create(self, *, action: str, **kwargs: Any) -> ApiCallResult:
        t0 = time.perf_counter()
        response = self._raw_client.chat.completions.create(**kwargs)
        return ApiCallResult(
            action=action,
            elapsed_ms=(time.perf_counter() - t0) * 1000.0,
            response=response,
        )

    async def chat_completions_create_async(self, *, action: str, **kwargs: Any) -> ApiCallResult:
        t0 = time.perf_counter()
        response = await self._raw_client.chat.completions.create(**kwargs)
        return ApiCallResult(
            action=action,
            elapsed_ms=(time.perf_counter() - t0) * 1000.0,
            response=response,
        )
