from types import SimpleNamespace
import json

from pydantic import BaseModel, ValidationError
import pytest

from src.llm.api_client import DungeonMindApiClient
from src.llm.experiment_provider import (
    OPENROUTER_BASE_URL,
    build_sync_openai_client,
    chat_json_object_kwargs,
    extraction_request_kwargs,
    json_object_retry_usage,
    openrouter_key_present,
    routing_identity_from_response,
    secret_present,
    structured_parse,
)


def test_openrouter_pin_and_no_fallback(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_PROVIDER", "openrouter")
    monkeypatch.setenv("DMB_OPENROUTER_PROVIDER_PIN", "DeepSeek")
    monkeypatch.setenv("DMB_OPENROUTER_ALLOW_FALLBACKS", "0")
    monkeypatch.setenv("DMB_OPENAI_REASONING_EFFORT", "high")
    kwargs = extraction_request_kwargs()
    assert kwargs["reasoning"] == {"effort": "high"}
    assert kwargs["extra_body"] == {
        "provider": {
            "order": ["DeepSeek"],
            "allow_fallbacks": False,
            "require_parameters": True,
        }
    }
    assert "service_tier" not in kwargs


def test_openrouter_none_disables_reasoning(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_PROVIDER", "openrouter")
    monkeypatch.setenv("DMB_OPENAI_REASONING_EFFORT", "none")
    kwargs = extraction_request_kwargs()
    assert kwargs["reasoning"] == {"enabled": False}


def test_luna_flex_and_standard_differ_only_in_service_tier(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_PROVIDER", "openai")
    monkeypatch.setenv("DMB_OPENAI_REASONING_EFFORT", "medium")
    monkeypatch.setenv("DMB_OPENAI_SERVICE_TIER", "flex")
    flex = extraction_request_kwargs()
    monkeypatch.setenv("DMB_OPENAI_SERVICE_TIER", "standard")
    standard = extraction_request_kwargs()
    assert flex == {
        "service_tier": "flex",
        "reasoning": {"effort": "medium"},
    }
    assert standard == {"reasoning": {"effort": "medium"}}
    assert set(flex) - set(standard) == {"service_tier"}


def test_openrouter_key_presence_does_not_return_secret() -> None:
    env = {"DUNGEONBUDDY_OPENROUTER": "super-secret-openrouter-key"}
    present = openrouter_key_present(env)
    assert present is True
    assert secret_present("DUNGEONBUDDY_OPENROUTER", env) is True
    assert present is not env["DUNGEONBUDDY_OPENROUTER"]


def test_openrouter_client_uses_openrouter_base_url(monkeypatch) -> None:
    captured: dict = {}

    class _Fake:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("DMB_EXTRACTION_PROVIDER", "openrouter")
    monkeypatch.setenv("DUNGEONBUDDY_OPENROUTER", "super-secret-openrouter-key")
    monkeypatch.setattr("openai.OpenAI", _Fake)
    client = build_sync_openai_client()
    assert isinstance(client, _Fake)
    assert captured["base_url"] == OPENROUTER_BASE_URL
    assert captured["api_key"] == "super-secret-openrouter-key"


def test_routing_identity_captures_provider_without_inventing_it() -> None:
    present = SimpleNamespace(id="gen_1", model="deepseek/deepseek-v4.1-flash", provider="DeepSeek")
    identity = routing_identity_from_response(present)
    assert identity["provider"] == "DeepSeek"
    assert identity["model"] == "deepseek/deepseek-v4.1-flash"
    missing = SimpleNamespace(id="gen_2", model="deepseek/deepseek-v4.1-flash")
    assert "provider" not in routing_identity_from_response(missing)


class _Probe(BaseModel):
    ok: bool
    note: str


def test_chat_json_object_uses_deepseek_chat_contract(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_PROVIDER", "openrouter")
    monkeypatch.setenv("DMB_OPENROUTER_PROVIDER_PIN", "DeepSeek")
    monkeypatch.setenv("DMB_OPENROUTER_ALLOW_FALLBACKS", "0")
    monkeypatch.setenv("DMB_OPENAI_REASONING_EFFORT", "none")
    payload, text_format = chat_json_object_kwargs(
        {
            "model": "deepseek/deepseek-v4.1-flash",
            "input": [
                {"role": "system", "content": "Extract entities."},
                {"role": "user", "content": "none"},
            ],
            "text_format": _Probe,
            **extraction_request_kwargs(),
        }
    )
    assert text_format is _Probe
    assert payload["response_format"] == {"type": "json_object"}
    assert "reasoning" not in payload
    assert payload["extra_body"]["reasoning"] == {"enabled": False}
    assert payload["extra_body"]["provider"]["order"] == ["DeepSeek"]
    assert payload["extra_body"]["provider"]["allow_fallbacks"] is False
    system = payload["messages"][0]["content"]
    assert "JSON" in system
    assert "display_name" in system
    assert '"ok"' in system


def test_structured_parse_chat_json_object_validates_locally(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_TRANSPORT", "chat_completions")
    monkeypatch.setenv("DMB_JSON_OBJECT_MAX_ATTEMPTS", "1")
    captured: dict = {}

    class _Completions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                provider="DeepSeek",
                model="deepseek/deepseek-v4.1-flash",
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"ok": true, "note": "ping"}', parsed=None)
                    )
                ],
                usage=SimpleNamespace(cost=0.0),
            )

    class _Chat:
        completions = _Completions()

    class _Raw:
        chat = _Chat()

    result = structured_parse(
        DungeonMindApiClient.wrap(_Raw()),
        action="probe",
        model="deepseek/deepseek-v4.1-flash",
        input=[{"role": "user", "content": "ping"}],
        text_format=_Probe,
    )
    assert captured["response_format"] == {"type": "json_object"}
    assert result.response.output_parsed == _Probe(ok=True, note="ping")
    assert result.response.provider == "DeepSeek"

    class _Bad:
        @staticmethod
        def create(**kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content='{"ok": true}', parsed=None))
                ]
            )

    class _BadChat:
        completions = _Bad()

    class _BadRaw:
        chat = _BadChat()

    with pytest.raises(ValidationError):
        structured_parse(
            DungeonMindApiClient.wrap(_BadRaw()),
            action="probe",
            model="deepseek/deepseek-v4.1-flash",
            input=[{"role": "user", "content": "ping"}],
            text_format=_Probe,
        )


def test_json_object_retries_until_valid_json(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_TRANSPORT", "chat_completions")
    monkeypatch.setenv("DMB_JSON_OBJECT_MAX_ATTEMPTS", "5")
    contents = ['{"ok": true', '{"ok": true, "note": "ok"}']

    class _Completions:
        def create(self, **kwargs):
            return SimpleNamespace(
                provider="DeepSeek",
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=contents.pop(0), parsed=None))
                ],
                usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2, cost=0.001),
            )

    class _Chat:
        completions = _Completions()

    class _Raw:
        chat = _Chat()

    result = structured_parse(
        DungeonMindApiClient.wrap(_Raw()),
        action="probe",
        model="deepseek/deepseek-v4.1-flash",
        input=[{"role": "user", "content": "ping"}],
        text_format=_Probe,
    )
    assert result.response.output_parsed == _Probe(ok=True, note="ok")
    assert result.response.json_object_attempts == 2
    assert result.response.json_object_retry_errors[0]["class"] == "JSONDecodeError"
    assert json_object_retry_usage(result.response)["json_object_retries"] == 1


def test_json_object_retry_usage_keeps_zero_retries() -> None:
    response = SimpleNamespace(
        json_object_attempts=1,
        json_object_retry_errors=[],
    )
    usage = json_object_retry_usage(response)
    assert usage["json_object_attempts"] == 1
    assert usage["json_object_retries"] == 0


def test_json_object_retry_exhaustion_keeps_last_error(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_TRANSPORT", "chat_completions")
    monkeypatch.setenv("DMB_JSON_OBJECT_MAX_ATTEMPTS", "2")
    calls = {"n": 0}

    class _Completions:
        def create(self, **kwargs):
            calls["n"] += 1
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="{bad", parsed=None))]
            )

    class _Chat:
        completions = _Completions()

    class _Raw:
        chat = _Chat()

    with pytest.raises(json.JSONDecodeError):
        structured_parse(
            DungeonMindApiClient.wrap(_Raw()),
            action="probe",
            model="deepseek/deepseek-v4.1-flash",
            input=[{"role": "user", "content": "ping"}],
            text_format=_Probe,
        )
    assert calls["n"] == 2
