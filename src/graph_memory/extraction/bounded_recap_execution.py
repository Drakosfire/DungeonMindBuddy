"""Recap pass budgets and metadata receipts; GenerationEngine owns inference IO."""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass
from functools import partial
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.graph_memory.extraction._recap_inference_worker import (
    _execute_in_owned_process, _WorkerStartFailure,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)
from src.graph_memory.extraction.category_candidate_graph_schema import (
    category_pass_text_format,
    category_pass_text_format_for_spec,
)

DEEPSEEK_MODEL = "deepseek/deepseek-v4.1-flash"


class NonObjectResponseError(ValueError):
    """A completed JSON response was not the object required by a pass."""


def _safe_validation_path(path, schema: dict[str, Any]) -> list[str | int]:
    """Retain schema-known path labels, never arbitrary response field names."""
    allowed = {
        "properties", "items", "type", "required", "additionalProperties",
        "enum", "minLength", "minimum", "maximum", "pattern", "anyOf",
        "oneOf", "allOf",
    }

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                allowed.update(properties)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(schema)
    return [
        segment if isinstance(segment, int) or segment in allowed else "<unknown>"
        for segment in list(path)[:16]
    ]


@dataclass(frozen=True)
class RecapExecutionLimits:
    provider: str = "openai"
    model: str = "gpt-6-luna"
    max_calls: int = 8
    per_call_deadline_ms: int = 60_000
    run_deadline_ms: int = 480_000
    max_output_tokens: int = 8192

    def __post_init__(self) -> None:
        if (self.provider, self.model) not in {
            ("openai", "gpt-6-luna"),
            ("openrouter", DEEPSEEK_MODEL),
        }:
            raise ValueError("unsupported bounded recap provider/model selection")
        for name, ceiling in (
            ("max_calls", 8),
            ("per_call_deadline_ms", 60_000),
            ("run_deadline_ms", 480_000),
            ("max_output_tokens", 8192),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} must be 1..{ceiling}")


def _default_engine_for(provider: str):
    from generationengine import GenerationClient

    if provider == "openrouter":
        from generationengine.providers.openrouter_text import OpenRouterTextProvider

        load_dungeonmindbuddy_dotenv(override=False)
        key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
            "DUNGEONBUDDY_OPENROUTER"
        )
        if not key or not key.strip():
            raise CategoryGraphExtractionError(
                "OpenRouter credential is unavailable for bounded recap extraction"
            )
        return GenerationClient(
            text_providers={"openrouter": OpenRouterTextProvider(api_key=key.strip())}
        )
    return GenerationClient()


class BoundedRecapPassClient:
    def __init__(
        self, limits: RecapExecutionLimits, *, engine_factory=None, clock=time.monotonic
    ):
        from generationengine.types import TextRequest

        self.limits = limits
        self._engine_factory = engine_factory or partial(_default_engine_for, limits.provider)
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
        from generationengine.types import TextResult

        wall_started = time.monotonic()

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
        deepseek = self.limits.provider == "openrouter"
        route = None
        system_prompt = instructions
        if deepseek:
            from generationengine.types import ProviderRoute

            route = ProviderRoute(order=("DeepSeek",), allow_fallbacks=False)
            system_prompt = (
                f"{instructions}\n\nThe JSON object MUST conform to this schema:\n"
                + json.dumps(fmt["schema"], sort_keys=True, separators=(",", ":"))
            )
        request_kwargs: dict[str, Any] = {
            "user_prompt": user_content,
            "system_prompt": system_prompt,
            "provider": self.limits.provider,
            "model": self.limits.model,
            "temperature": None,
            "max_transport_retries": 0,
            "max_output_tokens": self.limits.max_output_tokens,
            "deadline_ms": min(remaining, self.limits.per_call_deadline_ms),
        }
        if deepseek:
            request_kwargs.update(
                provider_route=route,
                reasoning_effort="none",
                json_object=True,
            )
        else:
            request_kwargs.update(json_schema=fmt["schema"], schema_name=fmt["name"])
        request = self._request_type(**request_kwargs)
        entry = {
            "ordinal": len(self.calls) + 1,
            "pass_name": pass_name,
            "requested_provider": self.limits.provider,
            "model": self.limits.model,
            "requested_route": (
                {"order": list(route.order), "allow_fallbacks": route.allow_fallbacks}
                if route is not None
                else None
            ),
            "deadline_ms": request.deadline_ms,
            "max_output_tokens": request.max_output_tokens,
            "observation": None,
        }
        self.calls.append(entry)
        result = None
        try:
            outcome = _execute_in_owned_process(
                self._engine_factory, request.model_dump(mode="json"),
                deadline=wall_started + request.deadline_ms / 1000,
            )
            entry["wall_clock_ms"] = int((time.monotonic() - wall_started) * 1000)
            entry["worker_cleanup"] = "terminated" if outcome.terminated else "reaped"
            if outcome.terminated:
                self._stopped = True
            receipt = outcome.receipt
            if receipt is None:
                entry["external_outcome"] = "unknown"
                raise CategoryGraphExtractionError(
                    "bounded inference outcome unknown: worker ended without receipt",
                    pass_name=pass_name,
                )
            if receipt["kind"] == "provider_failure":
                entry["observation"] = receipt["observation"]
                raise CategoryGraphExtractionError(
                    "bounded inference failed: " + receipt["failure_code"],
                    pass_name=pass_name,
                )
            if receipt["kind"] == "worker_failure":
                entry["external_outcome"] = "unknown"
                entry["consumer_failure"] = receipt["error_type"]
                raise CategoryGraphExtractionError(
                    "bounded inference outcome unknown: worker failed without GE receipt",
                    pass_name=pass_name,
                )
            result = TextResult.model_validate(receipt["result"])
            observation = result.observation.model_dump(mode="json")
            entry["observation"] = observation
            if (
                observation["state"] != "completed"
                or observation["retry_count"] != 0
                or observation["conformance_retry_count"] != 0
                or observation.get("transport_retry_count") not in (None, 0)
                or (
                    deepseek
                    and (
                        observation.get("provider") != "openrouter"
                        or observation.get("requested_model") != self.limits.model
                        or observation.get("resolved_model") != self.limits.model
                        or observation.get("provider_attempt_count") != 1
                        or observation.get("response_model") != self.limits.model
                    )
                )
            ):
                raise CategoryGraphExtractionError(
                    "inference did not complete within one attempt", pass_name=pass_name,
                    raw_model_response=result.text,
                )
        except CategoryGraphExtractionError:
            self._stopped = True
            raise
        except Exception as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            if isinstance(exc, _WorkerStartFailure):
                entry["external_outcome"] = "not_started"
            raise CategoryGraphExtractionError(
                "bounded extraction pass failed", pass_name=pass_name,
                raw_model_response=result.text if result is not None else None,
            ) from None
        try:
            parsed = json.loads(result.text or "")
            if not isinstance(parsed, dict):
                raise NonObjectResponseError("expected JSON object")
            if deepseek:
                validate_json_schema(parsed, fmt["schema"])
        except (json.JSONDecodeError, NonObjectResponseError, JsonSchemaValidationError) as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            entry["validation_failure"] = {
                "kind": (
                    "schema" if isinstance(exc, JsonSchemaValidationError)
                    else "invalid_json" if isinstance(exc, json.JSONDecodeError)
                    else "non_object"
                ),
                "validator": (
                    exc.validator
                    if isinstance(exc, JsonSchemaValidationError)
                    and exc.validator in {
                        "type", "required", "additionalProperties", "enum", "minLength",
                        "minimum", "maximum", "pattern", "anyOf", "oneOf", "allOf",
                    }
                    else None
                ),
                "instance_path": (
                    _safe_validation_path(exc.path, fmt["schema"])
                    if isinstance(exc, JsonSchemaValidationError) else []
                ),
                "schema_path": (
                    _safe_validation_path(exc.schema_path, fmt["schema"])
                    if isinstance(exc, JsonSchemaValidationError) else []
                ),
            }
            raise CategoryGraphExtractionError(
                "bounded extraction pass failed", pass_name=pass_name,
                raw_model_response=result.text,
            ) from None
        except Exception as exc:
            self._stopped = True
            entry["consumer_failure"] = type(exc).__name__
            raise CategoryGraphExtractionError(
                "bounded extraction pass failed", pass_name=pass_name,
                raw_model_response=result.text,
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
