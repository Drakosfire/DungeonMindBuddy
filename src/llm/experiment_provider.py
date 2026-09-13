"""Experiment-only OpenAI vs OpenRouter client and request-option seam.

This module is disposable notebook plumbing for Stage 4I.2. It is not a
production model router. Secrets are checked for presence only; values are
never logged, hashed, or returned.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from pydantic import ValidationError

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.llm.api_client import ApiCallResult, DungeonMindApiClient

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER = "https://github.com/Drakosfire/DungeonMindBuddy"
OPENROUTER_TITLE = "DungeonMindBuddy"
OPENROUTER_DISABLED_EFFORTS = {"none", "off", "disabled"}
DEEPSEEK_FLASH_SLUG = "deepseek/deepseek-v4.1-flash"


def extraction_provider(environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    value = str(env.get("DMB_EXTRACTION_PROVIDER") or "openai").strip().lower()
    if value not in {"openai", "openrouter"}:
        raise ValueError(f"unsupported extraction provider: {value}")
    return value


def extraction_transport(environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    value = str(env.get("DMB_EXTRACTION_TRANSPORT") or "responses").strip().lower()
    if value not in {"responses", "chat_completions"}:
        raise ValueError(f"unsupported extraction transport: {value}")
    return value


def secret_present(name: str, environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return bool(str(env.get(name) or "").strip())


def openrouter_key_present(environ: dict[str, str] | None = None) -> bool:
    return secret_present("DUNGEONBUDDY_OPENROUTER", environ)


def openai_key_present(environ: dict[str, str] | None = None) -> bool:
    return secret_present("OPENAI_API_KEY", environ)


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def extraction_request_kwargs(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    kwargs: dict[str, Any] = {}
    provider = extraction_provider(env)
    tier = str(env.get("DMB_OPENAI_SERVICE_TIER") or "").strip().lower()
    if tier == "flex":
        kwargs["service_tier"] = "flex"
    effort = str(env.get("DMB_OPENAI_REASONING_EFFORT") or "").strip()
    if effort:
        if provider == "openrouter" and effort.lower() in OPENROUTER_DISABLED_EFFORTS:
            kwargs["reasoning"] = {"enabled": False}
        else:
            kwargs["reasoning"] = {"effort": effort}
    if provider == "openrouter":
        pin = str(env.get("DMB_OPENROUTER_PROVIDER_PIN") or "").strip()
        allow_fallbacks = _truthy(str(env.get("DMB_OPENROUTER_ALLOW_FALLBACKS") or "0"))
        provider_block: dict[str, Any] = {
            "allow_fallbacks": allow_fallbacks,
            "require_parameters": True,
        }
        if pin:
            provider_block["order"] = [pin]
        kwargs["extra_body"] = {"provider": provider_block}
    return kwargs


def _openrouter_headers() -> dict[str, str]:
    return {
        "HTTP-Referer": OPENROUTER_REFERER,
        "X-Title": OPENROUTER_TITLE,
    }


def build_sync_openai_client(
    *, api_key: str | None = None, environ: dict[str, str] | None = None
) -> Any:
    from openai import OpenAI

    env = environ if environ is not None else os.environ
    if extraction_provider(env) == "openrouter":
        key = str(env.get("DUNGEONBUDDY_OPENROUTER") or "").strip()
        if not key:
            raise RuntimeError("DUNGEONBUDDY_OPENROUTER is required for OpenRouter extraction")
        return OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=key,
            default_headers=_openrouter_headers(),
        )
    if api_key:
        return OpenAI(api_key=api_key)
    return OpenAI()


def build_async_openai_client(
    *, api_key: str | None = None, environ: dict[str, str] | None = None
) -> Any:
    from openai import AsyncOpenAI

    env = environ if environ is not None else os.environ
    if extraction_provider(env) == "openrouter":
        key = str(env.get("DUNGEONBUDDY_OPENROUTER") or "").strip()
        if not key:
            raise RuntimeError("DUNGEONBUDDY_OPENROUTER is required for OpenRouter extraction")
        return AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=key,
            default_headers=_openrouter_headers(),
        )
    if api_key:
        return AsyncOpenAI(api_key=api_key)
    return AsyncOpenAI()


def _git_common_env_path(repo_root: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    git_common = Path(result.stdout.strip())
    if not git_common.is_absolute():
        git_common = (repo_root / git_common).resolve()
    env_path = git_common.parent / ".env"
    return env_path if env_path.is_file() else None


def ensure_experiment_secrets(repo_root: Path, environ: dict[str, str]) -> None:
    """Load OpenAI and OpenRouter keys into *environ* without echoing values."""
    load_dungeonmindbuddy_dotenv(override=False)
    common_env = _git_common_env_path(repo_root)
    if common_env is not None:
        load_dotenv(common_env, override=False)
    for name in ("OPENAI_API_KEY", "DUNGEONBUDDY_OPENROUTER"):
        current = str(environ.get(name) or "").strip()
        if current:
            continue
        loaded = str(os.environ.get(name) or "").strip()
        if loaded:
            environ[name] = loaded
            if name not in os.environ or not str(os.environ.get(name) or "").strip():
                os.environ[name] = loaded


JSON_OBJECT_SCHEMA_INSTRUCTION = (
    "Return JSON. Your output MUST be a single JSON object that validates against "
    "this JSON Schema. Every object must include every required field. "
    "Rows with decision=exclude still require display_name.\n"
)


class ParsedChatResponse:
    """Proxy so local Pydantic results look like Responses output_parsed."""

    def __init__(
        self,
        raw: Any,
        parsed: Any,
        *,
        json_object_attempts: int = 1,
        json_object_retry_errors: list[dict[str, Any]] | None = None,
        json_object_retry_input_tokens: int = 0,
        json_object_retry_output_tokens: int = 0,
        json_object_retry_cost_usd: float = 0.0,
    ) -> None:
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "output_parsed", parsed)
        object.__setattr__(self, "json_object_attempts", json_object_attempts)
        object.__setattr__(self, "json_object_retry_errors", json_object_retry_errors or [])
        object.__setattr__(self, "json_object_retry_input_tokens", json_object_retry_input_tokens)
        object.__setattr__(self, "json_object_retry_output_tokens", json_object_retry_output_tokens)
        object.__setattr__(self, "json_object_retry_cost_usd", json_object_retry_cost_usd)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)


def json_object_max_attempts(environ: dict[str, str] | None = None) -> int:
    env = environ if environ is not None else os.environ
    value = int(str(env.get("DMB_JSON_OBJECT_MAX_ATTEMPTS") or "5").strip())
    if value < 1:
        raise ValueError("DMB_JSON_OBJECT_MAX_ATTEMPTS must be >= 1")
    return value


def classify_json_object_error(exc: BaseException) -> dict[str, Any]:
    """Record parse failures without storing model text or corpus."""
    if isinstance(exc, json.JSONDecodeError):
        return {
            "class": "JSONDecodeError",
            "lineno": exc.lineno,
            "colno": exc.colno,
            "pos": exc.pos,
        }
    if isinstance(exc, ValidationError):
        fields = []
        for err in exc.errors()[:20]:
            loc = ".".join(str(part) for part in (err.get("loc") or ()))
            fields.append({"type": err.get("type"), "loc": loc})
        return {
            "class": "ValidationError",
            "error_count": exc.error_count(),
            "fields": fields,
        }
    if isinstance(exc, ValueError):
        return {"class": "ValueError", "kind": str(exc)[:80]}
    return {"class": type(exc).__name__}


def json_object_retry_usage(response: Any) -> dict[str, Any]:
    attempts = getattr(response, "json_object_attempts", None)
    if attempts is None:
        return {}
    payload: dict[str, Any] = {
        "json_object_attempts": int(attempts),
        "json_object_retries": max(0, int(attempts) - 1),
        "json_object_retry_errors": list(getattr(response, "json_object_retry_errors", []) or []),
    }
    extra_in = int(getattr(response, "json_object_retry_input_tokens", 0) or 0)
    extra_out = int(getattr(response, "json_object_retry_output_tokens", 0) or 0)
    extra_cost = float(getattr(response, "json_object_retry_cost_usd", 0.0) or 0.0)
    if extra_in:
        payload["json_object_retry_input_tokens"] = extra_in
    if extra_out:
        payload["json_object_retry_output_tokens"] = extra_out
    if extra_cost:
        payload["json_object_retry_cost_usd"] = extra_cost
    return payload


def _chat_token_counts(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    if isinstance(usage, dict):
        raw_in = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        raw_out = usage.get("completion_tokens", usage.get("output_tokens", 0))
    else:
        raw_in = getattr(usage, "prompt_tokens", None)
        if raw_in is None:
            raw_in = getattr(usage, "input_tokens", 0)
        raw_out = getattr(usage, "completion_tokens", None)
        if raw_out is None:
            raw_out = getattr(usage, "output_tokens", 0)
    return int(raw_in or 0), int(raw_out or 0)


def _as_chat_messages(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("structured parse input must be a list of role/content messages")
    messages: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("structured parse input items must be mappings")
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or content is None:
            raise ValueError("structured parse input items require role and content")
        messages.append({"role": role, "content": content})
    return messages


def _message_content(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("chat completion returned no choices")
    message = getattr(choices[0], "message", None)
    content = None if message is None else getattr(message, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("chat completion returned empty content")
    return content


def load_json_object(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def attach_json_schema_instruction(messages: list[dict[str, Any]], text_format: Any) -> list[dict[str, Any]]:
    schema_text = json.dumps(text_format.model_json_schema(), indent=2, sort_keys=True)
    instruction = f"{JSON_OBJECT_SCHEMA_INSTRUCTION}{schema_text}"
    attached = False
    out: list[dict[str, Any]] = []
    for message in messages:
        if not attached and message.get("role") == "system":
            out.append(
                {
                    "role": "system",
                    "content": f"{message['content']}\n\n{instruction}",
                }
            )
            attached = True
            continue
        out.append(dict(message))
    if not attached:
        out.insert(0, {"role": "system", "content": instruction})
    return out


def chat_json_object_kwargs(kwargs: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    """Map a Responses-style parse call onto DeepSeek Chat Completions json_object."""
    payload = dict(kwargs)
    text_format = payload.pop("text_format", None)
    if text_format is None:
        raise ValueError("chat_completions transport requires text_format")
    incoming = payload.pop("input", None)
    extra = dict(payload.pop("extra_body", {}) or {})
    reasoning = payload.pop("reasoning", None)
    if reasoning is not None:
        extra["reasoning"] = reasoning
    payload.pop("service_tier", None)
    payload["messages"] = attach_json_schema_instruction(_as_chat_messages(incoming), text_format)
    payload["response_format"] = {"type": "json_object"}
    if extra:
        payload["extra_body"] = extra
    return payload, text_format


def parsed_output_from_response(response: Any) -> Any:
    parsed = getattr(response, "output_parsed", None)
    if parsed is not None:
        return parsed
    choices = getattr(response, "choices", None)
    if not choices:
        return None
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        return None
    parsed = getattr(message, "parsed", None)
    if parsed is not None:
        return parsed
    content = getattr(message, "content", None)
    return content


def routing_identity_from_response(response: Any) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    for key in ("id", "model", "provider", "system_fingerprint"):
        value = getattr(response, key, None)
        if isinstance(value, (str, int, float, bool)):
            identity[key] = value
        elif value is not None and not callable(value):
            identity[key] = str(value)
    metadata = getattr(response, "metadata", None)
    if isinstance(metadata, dict):
        for key in ("provider", "endpoint", "model"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip() and key not in identity:
                identity[key] = value
    return identity


def provider_cost_usd_from_response(response: Any) -> float | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        raw = usage.get("cost", usage.get("total_cost"))
    else:
        raw = getattr(usage, "cost", None)
        if raw is None:
            raw = getattr(usage, "total_cost", None)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parsed_chat_result(
    call: ApiCallResult,
    *,
    text_format: Any,
    json_object_attempts: int = 1,
    json_object_retry_errors: list[dict[str, Any]] | None = None,
    json_object_retry_input_tokens: int = 0,
    json_object_retry_output_tokens: int = 0,
    json_object_retry_cost_usd: float = 0.0,
    elapsed_ms: float | None = None,
) -> ApiCallResult:
    parsed = text_format.model_validate(load_json_object(_message_content(call.response)))
    return ApiCallResult(
        action=call.action,
        elapsed_ms=call.elapsed_ms if elapsed_ms is None else elapsed_ms,
        response=ParsedChatResponse(
            call.response,
            parsed,
            json_object_attempts=json_object_attempts,
            json_object_retry_errors=json_object_retry_errors,
            json_object_retry_input_tokens=json_object_retry_input_tokens,
            json_object_retry_output_tokens=json_object_retry_output_tokens,
            json_object_retry_cost_usd=json_object_retry_cost_usd,
        ),
    )


def _retryable_json_object_error(exc: BaseException) -> bool:
    return isinstance(exc, (json.JSONDecodeError, ValidationError, ValueError))


def structured_parse(
    api_client: DungeonMindApiClient, *, action: str, **kwargs: Any
) -> ApiCallResult:
    transport = extraction_transport()
    if transport == "chat_completions":
        payload, text_format = chat_json_object_kwargs(kwargs)
        max_attempts = json_object_max_attempts()
        errors: list[dict[str, Any]] = []
        retry_in = 0
        retry_out = 0
        retry_cost = 0.0
        elapsed = 0.0
        last_exc: BaseException | None = None
        for attempt in range(1, max_attempts + 1):
            call = api_client.chat_completions_create(action=action, **payload)
            elapsed += call.elapsed_ms
            try:
                return _parsed_chat_result(
                    call,
                    text_format=text_format,
                    json_object_attempts=attempt,
                    json_object_retry_errors=errors,
                    json_object_retry_input_tokens=retry_in,
                    json_object_retry_output_tokens=retry_out,
                    json_object_retry_cost_usd=retry_cost,
                    elapsed_ms=elapsed,
                )
            except Exception as exc:
                if not _retryable_json_object_error(exc) or attempt >= max_attempts:
                    raise
                errors.append(classify_json_object_error(exc))
                inn, out = _chat_token_counts(call.response)
                retry_in += inn
                retry_out += out
                cost = provider_cost_usd_from_response(call.response)
                if cost is not None:
                    retry_cost += cost
                last_exc = exc
        raise last_exc if last_exc is not None else RuntimeError("json_object retry exhausted")
    return api_client.responses_parse(action=action, **kwargs)


async def structured_parse_async(
    api_client: DungeonMindApiClient, *, action: str, **kwargs: Any
) -> ApiCallResult:
    transport = extraction_transport()
    if transport == "chat_completions":
        payload, text_format = chat_json_object_kwargs(kwargs)
        max_attempts = json_object_max_attempts()
        errors: list[dict[str, Any]] = []
        retry_in = 0
        retry_out = 0
        retry_cost = 0.0
        elapsed = 0.0
        last_exc: BaseException | None = None
        for attempt in range(1, max_attempts + 1):
            call = await api_client.chat_completions_create_async(action=action, **payload)
            elapsed += call.elapsed_ms
            try:
                return _parsed_chat_result(
                    call,
                    text_format=text_format,
                    json_object_attempts=attempt,
                    json_object_retry_errors=errors,
                    json_object_retry_input_tokens=retry_in,
                    json_object_retry_output_tokens=retry_out,
                    json_object_retry_cost_usd=retry_cost,
                    elapsed_ms=elapsed,
                )
            except Exception as exc:
                if not _retryable_json_object_error(exc) or attempt >= max_attempts:
                    raise
                errors.append(classify_json_object_error(exc))
                inn, out = _chat_token_counts(call.response)
                retry_in += inn
                retry_out += out
                cost = provider_cost_usd_from_response(call.response)
                if cost is not None:
                    retry_cost += cost
                last_exc = exc
        raise last_exc if last_exc is not None else RuntimeError("json_object retry exhausted")
    return await api_client.responses_parse_async(action=action, **kwargs)
