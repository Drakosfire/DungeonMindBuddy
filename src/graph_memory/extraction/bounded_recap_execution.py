"""Recap pass budgets and metadata receipts; GenerationEngine owns inference IO."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from typing import Any

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)
from src.graph_memory.extraction.category_candidate_graph_schema import (
    category_pass_text_format,
    category_pass_text_format_for_spec,
)


@dataclass(frozen=True)
class RecapExecutionLimits:
    model: str = "gpt-6-luna"
    max_calls: int = 8
    per_call_deadline_ms: int = 60_000
    run_deadline_ms: int = 480_000
    max_output_tokens: int = 8192

    def __post_init__(self) -> None:
        if self.model != "gpt-6-luna":
            raise ValueError("bounded recap extraction requires gpt-6-luna")
        for name, ceiling in (
            ("max_calls", 8),
            ("per_call_deadline_ms", 60_000),
            ("run_deadline_ms", 480_000),
            ("max_output_tokens", 8192),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} must be 1..{ceiling}")


class BoundedRecapPassClient:
    def __init__(
        self, limits: RecapExecutionLimits, *, engine_factory=None, clock=time.monotonic
    ):
        from generationengine import GenerationClient
        from generationengine.types import TextRequest

        self.limits = limits
        self._engine_factory = engine_factory or GenerationClient
        self._request_type = TextRequest
        self._clock = clock
        self._started = clock()
        self.calls: list[dict[str, Any]] = []
        self._stopped = False

    def ledger(self) -> dict[str, Any]:
        return {
            "schema": "dmb_bounded_recap_execution_v1",
            "limits": asdict(self.limits),
            "calls": self.calls,
            "stopped": self._stopped,
        }

    def run_pass(
        self, pass_name, *, model_id, instructions, user_content, pass_spec=None
    ):
        from generationengine.types import GenerationEngineError

        remaining = self.limits.run_deadline_ms - int(
            (self._clock() - self._started) * 1000
        )
        if (
            self._stopped
            or model_id != self.limits.model
            or len(self.calls) >= self.limits.max_calls
            or remaining <= 0
        ):
            self._stopped = True
            raise CategoryGraphExtractionError(
                "bounded recap execution stopped before inference", pass_name=pass_name
            )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            self._stopped = True
            raise CategoryGraphExtractionError(
                "bounded recap execution requires a synchronous worker",
                pass_name=pass_name,
            )
        fmt = (
            category_pass_text_format_for_spec(pass_spec)
            if pass_spec
            else category_pass_text_format(pass_name)
        )["format"]
        request = self._request_type(
            user_prompt=user_content,
            system_prompt=instructions,
            provider="openai",
            model=self.limits.model,
            temperature=None,
            json_schema=fmt["schema"],
            schema_name=fmt["name"],
            max_transport_retries=0,
            max_output_tokens=self.limits.max_output_tokens,
            deadline_ms=min(remaining, self.limits.per_call_deadline_ms),
        )
        entry = {
            "ordinal": len(self.calls) + 1,
            "pass_name": pass_name,
            "model": self.limits.model,
            "deadline_ms": request.deadline_ms,
            "max_output_tokens": request.max_output_tokens,
            "observation": None,
        }
        self.calls.append(entry)

        async def execute():
            engine = self._engine_factory()
            try:
                # Native schema format, consumer parsing; no GE conformance repair call.
                return await engine.generate_text(request)
            finally:
                await engine.aclose()

        try:
            result = asyncio.run(execute())
            observation = result.observation.model_dump(mode="json")
            entry["observation"] = observation
            if (
                observation["state"] != "completed"
                or observation["retry_count"] != 0
                or observation["conformance_retry_count"] != 0
            ):
                raise CategoryGraphExtractionError(
                    "inference did not complete within one attempt", pass_name=pass_name
                )
            parsed = json.loads(result.text or "")
            if not isinstance(parsed, dict):
                raise ValueError("expected JSON object")
        except GenerationEngineError as exc:
            entry["observation"] = exc.observation.model_dump(mode="json")
            self._stopped = True
            raise CategoryGraphExtractionError(
                "bounded inference failed: " + exc.failure.code.value,
                pass_name=pass_name,
            ) from None
        except Exception as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            raise CategoryGraphExtractionError(
                "bounded extraction pass failed", pass_name=pass_name
            ) from None
        return {
            "parsed": parsed,
            "raw_text": result.text,
            "usage": {
                "input_tokens": observation["input_tokens"],
                "output_tokens": observation["output_tokens"],
                "cached_tokens": observation["cached_input_tokens"],
            },
            "cost_usd": observation["cost_usd"],
            "elapsed_ms": observation["latency_ms"],
            "response_id": observation["provider_response_id"],
        }
