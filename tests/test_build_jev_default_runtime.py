"""Ordinary HTTP default uses startup-prepared offline accounting and real APP."""

import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as ledger
from apps.live_control_server.routes import agent
from apps.live_control_server.services import build_jev_runtime as prepared
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    WriterWire,
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.fixture
def verified_asset():
    configured = os.environ.get("DMB_TEST_JEV_TOKENIZER_FILE", "")
    if not configured:
        pytest.skip(
            "Public verified offline o200k asset must be configured for conformance/startup acceptance"
        )
    return Path(configured)


def test_missing_and_corrupt_preparation_never_downloads_or_falls_back(
    monkeypatch, tmp_path
):
    import tiktoken.load

    monkeypatch.setattr(
        tiktoken.load,
        "read_file",
        lambda *_: pytest.fail("network/cache loader called"),
    )
    monkeypatch.delenv(prepared.ASSET_ENV, raising=False)
    missing = prepared.prepare_default_build_runtime()
    assert missing.unavailable_reason == "tokenizer_asset_unconfigured"
    with pytest.raises(prepared.BuildJevRuntimeUnavailable):
        missing.create()
    monkeypatch.setenv(prepared.ASSET_ENV, str(tmp_path / "absent"))
    assert (
        prepared.prepare_default_build_runtime().unavailable_reason
        == "tokenizer_asset_unreadable"
    )
    bad = tmp_path / "wrong-asset"
    bad.write_bytes(b"not a tokenizer")
    monkeypatch.setenv(prepared.ASSET_ENV, str(bad))
    assert (
        prepared.prepare_default_build_runtime().unavailable_reason
        == "tokenizer_asset_digest"
    )
    monkeypatch.setenv(prepared.ASSET_ENV, "relative-asset")
    assert (
        prepared.prepare_default_build_runtime().unavailable_reason
        == "tokenizer_asset_path"
    )


def test_verified_loader_matches_upstream_unicode_and_markdown_without_fetch(
    monkeypatch, verified_asset
):
    import tiktoken
    import tiktoken.load
    import tiktoken_ext.openai_public as upstream

    data = verified_asset.read_bytes()
    ranks = {
        base64.b64decode(token): int(rank)
        for token, rank in (line.split() for line in data.splitlines())
    }

    def public_asset(url, expected_hash):
        assert (
            url.endswith("/o200k_base.tiktoken")
            and expected_hash == prepared.ASSET_SHA256
        )
        return ranks

    monkeypatch.setattr(upstream, "load_tiktoken_bpe", public_asset)
    monkeypatch.setattr(
        tiktoken.load,
        "read_file",
        lambda *_: pytest.fail("network/cache loader called"),
    )
    reference = tiktoken.Encoding(**upstream.o200k_base())
    counter = prepared.load_offline_accounting(verified_asset)
    texts = [
        "",
        "🐐 café 中文 العربية Ελληνικά",
        "<|endoftext|> <|endofprompt|>",
        "| NPC | Job |\n| --- | --- |\n| Pippa | Brewer |",
        json.dumps({"nested": {"sources": ["a\nb", "emoji 🐐"]}}, ensure_ascii=False),
        "\u0301a\u0301\r\n\t ",
        "9876543210 " * 500,
        ("Source facts and qualifications.\n" * 4000),
    ]
    assert counter.descriptor["guaranteed_upper_bound"] is False
    for text in texts:
        assert counter.count_tokens(text) == len(
            reference.encode(text, disallowed_special=())
        )
    # Prepared count/factory construction has no subsequent asset/cache access.
    monkeypatch.setattr(
        Path, "open", lambda *_args, **_kwargs: pytest.fail("request-time file read")
    )
    factory = prepared.PreparedBuildJevRuntime(
        accounting=counter, unavailable_reason=None
    )
    assert factory.create().accounting is counter
    assert counter.estimate({"question": texts[1]}) > 4096


@pytest.mark.parametrize(
    "reason", ["tokenizer_asset_unconfigured", "tokenizer_asset_digest"]
)
def test_unavailable_default_refuses_before_acceptance_or_provider(
    build_case, monkeypatch, tmp_path, reason
):
    case, reads = ordinary_case(build_case, monkeypatch)
    factory = prepared.PreparedBuildJevRuntime(unavailable_reason=reason)
    with pytest.raises(Exception) as rejected:
        execute(case, tmp_path, None, build_runtime_factory=factory)
    assert rejected.value.code == "build_jev_runtime_unavailable"
    assert rejected.value.provider_dispatched is False
    assert reads == {"graph": 0, "source": 0}
    service = AgentConversationService()
    pointer = service.get_world_pointer("elderwyld")
    assert (
        pointer.active_conversation_id is None
        or service.list_turns("elderwyld", pointer.active_conversation_id) == []
    )


def test_actual_http_default_freezes_prepared_policy_completes_and_replays(
    build_case, monkeypatch, tmp_path, verified_asset
):
    case, reads = ordinary_case(build_case, monkeypatch)
    _, request, bootstrap = case
    decisions, writer = DecisionWire(), WriterWire()
    monkeypatch.setenv(prepared.ASSET_ENV, str(verified_asset))
    monkeypatch.setattr(
        prepared,
        "BuildJevHarness",
        lambda **kwargs: BuildJevHarness(
            decision_transport=decisions, writer_transport=writer, **kwargs
        ),
    )
    monkeypatch.setattr(
        agent,
        "enforce_native_graph_gm",
        lambda _: SimpleNamespace(subject="synthetic-operator"),
    )
    monkeypatch.setattr(agent, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "session_dir", lambda: tmp_path / "http-pointers")
    monkeypatch.setattr(
        agent,
        "_owner_resolver",
        lambda _: {"kind": "world", "id": "elderwyld", "name": "Elderwyld"},
    )
    monkeypatch.setattr(
        agent, "_plan_context_resolver", lambda *args, **kwargs: bootstrap
    )
    from apps.live_control_server.main import create_app

    app = create_app()
    with TestClient(app) as client:
        factory = app.state.build_jev_runtime_factory
        assert factory.accounting is not None
        app.state.agent_conversation_service = AgentConversationService()
        assert getattr(app.state, "agent_turn_runtime", None) is None
        monkeypatch.setattr(
            prepared,
            "load_offline_accounting",
            lambda *_: pytest.fail("request-time loader"),
        )
        response = client.post(
            "/api/live/agent/turn", json=request.model_dump(mode="json", by_alias=True)
        )
        assert response.status_code == 200, response.text
        assert reads == {"graph": 1, "source": 1} and len(writer.calls) == 1
        service = AgentConversationService()
        turn = service.list_turns(
            "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
        )[0]
        assert turn.status == "completed"
        policy = turn.graph_context_execution.policy
        assert isinstance(policy, ledger.BuildCitedSourceActionControllerWriterPolicyV1)
        assert (
            policy.controller_continuation_accounting.model_dump()
            == factory.accounting.descriptor
        )
        assert policy.writer_context_budget.context_limit_tokens == 128000
        assert turn.graph_context_receipt.assembled_input.context_window_limit == 64000
        assert turn.completion.source_citations
        # Durable completed replay must not need a newly available runtime/asset.
        app.state.build_jev_runtime_factory = prepared.PreparedBuildJevRuntime()
        replay = client.post(
            "/api/live/agent/turn", json=request.model_dump(mode="json", by_alias=True)
        )
        assert replay.status_code == 200 and len(writer.calls) == 1
        assert replay.json()["answer"]["text"] == response.json()["answer"]["text"]
    assert app.state.build_jev_runtime_factory is None


def test_lifespan_factory_is_per_app_and_does_not_reuse_another_apps_capability(
    monkeypatch, verified_asset
):
    from apps.live_control_server.main import create_app

    first, second = create_app(), create_app()
    monkeypatch.setenv(prepared.ASSET_ENV, str(verified_asset))
    with TestClient(first):
        good = first.state.build_jev_runtime_factory
        assert good.accounting is not None
        monkeypatch.delenv(prepared.ASSET_ENV)
        with TestClient(second):
            bad = second.state.build_jev_runtime_factory
            assert bad is not good and bad.accounting is None
            with pytest.raises(prepared.BuildJevRuntimeUnavailable):
                bad.create()
            assert good.create().accounting is good.accounting
    assert (
        first.state.build_jev_runtime_factory
        is second.state.build_jev_runtime_factory
        is None
    )


@pytest.mark.parametrize("corrupt", [False, True])
def test_http_unavailable_capability_keeps_health_but_accepts_no_turn(
    build_case, monkeypatch, tmp_path, corrupt
):
    case, reads = ordinary_case(build_case, monkeypatch)
    _, request, bootstrap = case
    if corrupt:
        asset = tmp_path / "corrupt-tokenizer"
        asset.write_bytes(b"invalid")
        monkeypatch.setenv(prepared.ASSET_ENV, str(asset))
    else:
        monkeypatch.delenv(prepared.ASSET_ENV, raising=False)
    monkeypatch.setattr(
        agent,
        "enforce_native_graph_gm",
        lambda _: SimpleNamespace(subject="synthetic-operator"),
    )
    monkeypatch.setattr(agent, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "session_dir", lambda: tmp_path / "http-pointers")
    monkeypatch.setattr(
        agent,
        "_owner_resolver",
        lambda _: {"kind": "world", "id": "elderwyld", "name": "Elderwyld"},
    )
    monkeypatch.setattr(
        agent, "_plan_context_resolver", lambda *args, **kwargs: bootstrap
    )
    monkeypatch.setattr(
        prepared,
        "BuildJevHarness",
        lambda **_: pytest.fail("provider runtime constructed"),
    )
    from apps.live_control_server.main import create_app

    app = create_app()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post(
            "/api/live/agent/turn", json=request.model_dump(mode="json", by_alias=True)
        )
        assert response.status_code == 503
        assert (
            "offline tokenizer" in response.text
            and "corrupt-tokenizer" not in response.text
        )
    service = AgentConversationService()
    pointer = service.get_world_pointer("elderwyld")
    assert (
        pointer.active_conversation_id is None
        or service.list_turns("elderwyld", pointer.active_conversation_id) == []
    )
    assert reads == {"graph": 0, "source": 0}


def test_wrong_tokenizer_version_is_unavailable_before_asset_read(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(prepared, "version", lambda _: "0.13.0")
    monkeypatch.setenv(prepared.ASSET_ENV, str(tmp_path / "not-read"))
    factory = prepared.prepare_default_build_runtime()
    assert factory.unavailable_reason == "tokenizer_dependency_version"
    with pytest.raises(prepared.BuildJevRuntimeUnavailable):
        factory.create()
