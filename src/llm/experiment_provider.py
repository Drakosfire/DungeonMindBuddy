"""Experiment-only OpenAI vs OpenRouter client and request-option seam.

This module is disposable notebook plumbing for Stage 4I.2. It is not a
production model router. Secrets are checked for presence only; values are
never logged, hashed, or returned.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

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


def _chat_parse_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    payload = dict(kwargs)
    text_format = payload.pop("text_format", None)
    if text_format is None:
        raise ValueError("chat_completions transport requires text_format")
    incoming = payload.pop("input", None)
    payload["messages"] = _as_chat_messages(incoming)
    payload["response_format"] = text_format
    return payload


def structured_parse(
    api_client: DungeonMindApiClient, *, action: str, **kwargs: Any
) -> ApiCallResult:
    transport = extraction_transport()
    if transport == "chat_completions":
        return api_client.chat_completions_parse(action=action, **_chat_parse_kwargs(kwargs))
    return api_client.responses_parse(action=action, **kwargs)


async def structured_parse_async(
    api_client: DungeonMindApiClient, *, action: str, **kwargs: Any
) -> ApiCallResult:
    transport = extraction_transport()
    if transport == "chat_completions":
        return await api_client.chat_completions_parse_async(
            action=action, **_chat_parse_kwargs(kwargs)
        )
    return await api_client.responses_parse_async(action=action, **kwargs)
