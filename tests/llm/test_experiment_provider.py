from types import SimpleNamespace

from src.llm.experiment_provider import (
    OPENROUTER_BASE_URL,
    build_sync_openai_client,
    extraction_request_kwargs,
    openrouter_key_present,
    routing_identity_from_response,
    secret_present,
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
