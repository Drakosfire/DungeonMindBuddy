"""OpenRouter DeepSeek Chat Completions client for category graph passes.

Stage 4J Path B transport: json_object response mode, schema embedded in
instructions, local parse/validate, same-request retry on failure.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Mapping, Protocol

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
    _usage_from_response,
    parse_json_object,
)
from src.graph_memory.extraction.category_candidate_graph_schema import (
    schema_for_pass,
    schema_for_pass_spec,
)
from src.graph_memory.extraction.extraction_profile import ExtractionPassSpec

DEFAULT_DEEPSEEK_MODEL = "deepseek/deepseek-v4.1-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
JSON_OBJECT_MAX_ATTEMPTS_ENV = "DMB_JSON_OBJECT_MAX_ATTEMPTS"
DEFAULT_JSON_OBJECT_MAX_ATTEMPTS = 5


class _ChatCompletionsClient(Protocol):
    class completions:  # noqa: N801
        @staticmethod
        def create(**kwargs: Any) -> Any: ...


class DeepSeekCategoryGraphPassClient:
    """CategoryGraphPassClient via OpenRouter with DeepSeek provider pin."""

    def __init__(
        self,
        *,
        model_id: str | None = None,
        max_attempts: int | None = None,
        sdk_client: _ChatCompletionsClient | None = None,
        reasoning_disabled: bool = True,
    ) -> None:
        self._model_id = (model_id or DEFAULT_DEEPSEEK_MODEL).strip()
        self._max_attempts = max_attempts
        self._sdk_client = sdk_client
        self._reasoning_disabled = reasoning_disabled

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec: ExtractionPassSpec | None = None,
    ) -> dict[str, Any]:
        load_dungeonmindbuddy_dotenv()
        api_key = _resolve_openrouter_api_key()
        schema = (
            schema_for_pass_spec(pass_spec)
            if pass_spec is not None
            else schema_for_pass(pass_name)
        )
        schema_text = json.dumps(schema, indent=2, sort_keys=True)
        system_instructions = (
            f"{instructions.strip()}\n\n"
            "Respond with a single JSON object only. No markdown fences, no commentary.\n"
            f"The JSON object MUST conform to this schema:\n{schema_text}"
        )
        resolved_model = (model_id or self._model_id).strip() or self._model_id
        max_attempts = _resolve_max_attempts_override(self._max_attempts)
        client = self._sdk_client or _build_openrouter_client(api_key)
        extra_body = _openrouter_extra_body(reasoning_disabled=self._reasoning_disabled)

        last_error: Exception | None = None
        last_raw_text = ""
        total_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
        total_cost_usd = 0.0
        total_cost_info: dict[str, Any] = {}
        total_elapsed_ms = 0.0
        response_id = ""
        attempt_count = 0

        for attempt in range(1, max_attempts + 1):
            attempt_count = attempt
            t0 = time.perf_counter()
            try:
                response = client.chat.completions.create(
                    model=resolved_model,
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": user_content},
                    ],
                    response_format={"type": "json_object"},
                    extra_body=extra_body,
                )
            except Exception as exc:  # noqa: BLE001 — retry same request on transport errors
                last_error = exc
                total_elapsed_ms += round((time.perf_counter() - t0) * 1000.0, 2)
                if attempt >= max_attempts:
                    raise CategoryGraphExtractionError(
                        f"{pass_name} OpenRouter request failed after {max_attempts} attempts: {exc}",
                        pass_name=pass_name,
                    ) from exc
                continue

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            total_elapsed_ms += elapsed_ms
            response_id = str(getattr(response, "id", "") or response_id)
            choice = _first_choice(response)
            message = getattr(choice, "message", None)
            raw_text = ""
            if message is not None:
                raw_text = str(getattr(message, "content", "") or "").strip()
            last_raw_text = raw_text

            usage = _usage_from_response(response)
            for key in ("input_tokens", "output_tokens", "cached_tokens"):
                total_usage[key] = int(total_usage.get(key, 0) or 0) + int(
                    usage.get(key, 0) or 0
                )

            from src.agent.planner_pricing import usage_cost_usd

            cost_info = usage_cost_usd(
                model_id=resolved_model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cached_tokens=usage["cached_tokens"],
            )
            total_cost_usd += float(cost_info.get("total_usd") or 0.0)
            total_cost_info = cost_info

            if not raw_text:
                last_error = CategoryGraphExtractionError(
                    f"{pass_name} returned empty content",
                    pass_name=pass_name,
                )
                if attempt >= max_attempts:
                    raise last_error
                continue

            try:
                parsed = parse_json_object(raw_text)
                _validate_required_keys(parsed, schema)
            except (json.JSONDecodeError, CategoryGraphExtractionError, ValueError) as exc:
                last_error = exc
                if attempt >= max_attempts:
                    raise CategoryGraphExtractionError(
                        f"{pass_name} returned invalid JSON after {max_attempts} attempts: {exc}",
                        pass_name=pass_name,
                        raw_model_response=raw_text,
                    ) from exc
                continue

            result: dict[str, Any] = {
                "parsed": parsed,
                "raw_text": raw_text,
                "usage": total_usage,
                "cost_usd": round(total_cost_usd, 6),
                "cost_info": total_cost_info,
                "elapsed_ms": total_elapsed_ms,
                "response_id": response_id,
                "transport": "openrouter_chat_completions_json_object",
                "provider_pin": {"order": ["DeepSeek"], "allow_fallbacks": False},
                "json_object_attempts": attempt_count,
            }
            if self._reasoning_disabled:
                result["reasoning_disabled"] = True
            return result

        raise CategoryGraphExtractionError(
            f"{pass_name} failed after {max_attempts} attempts: {last_error}",
            pass_name=pass_name,
            raw_model_response=last_raw_text,
        )


def _resolve_openrouter_api_key() -> str:
    for env_name in ("OPENROUTER_API_KEY", "DUNGEONBUDDY_OPENROUTER"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    raise CategoryGraphExtractionError(
        "OpenRouter API key is not configured; set OPENROUTER_API_KEY or DUNGEONBUDDY_OPENROUTER."
    )


def _resolve_max_attempts_override(value: int | None) -> int:
    if value is not None and value > 0:
        return value
    raw = os.environ.get(JSON_OBJECT_MAX_ATTEMPTS_ENV, "").strip()
    if raw:
        try:
            parsed = int(raw)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return DEFAULT_JSON_OBJECT_MAX_ATTEMPTS


def _build_openrouter_client(api_key: str) -> Any:
    from openai import OpenAI

    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


def _openrouter_extra_body(*, reasoning_disabled: bool) -> dict[str, Any]:
    body: dict[str, Any] = {
        "provider": {"order": ["DeepSeek"], "allow_fallbacks": False},
    }
    if reasoning_disabled:
        body["reasoning"] = {"effort": "none", "enabled": False}
    return body


def _first_choice(response: Any) -> Any:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise CategoryGraphExtractionError("OpenRouter response carried no choices")
    return choices[0]


def _validate_required_keys(parsed: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    required = schema.get("required")
    if not isinstance(required, list):
        return
    missing = [key for key in required if key not in parsed]
    if missing:
        raise ValueError(f"missing required keys: {', '.join(str(k) for k in missing)}")


__all__ = [
    "DEFAULT_DEEPSEEK_MODEL",
    "DEFAULT_JSON_OBJECT_MAX_ATTEMPTS",
    "DeepSeekCategoryGraphPassClient",
    "JSON_OBJECT_MAX_ATTEMPTS_ENV",
    "OPENROUTER_BASE_URL",
]
