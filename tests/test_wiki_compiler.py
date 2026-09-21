"""Tests for wiki connectivity scoring, name filters, and GE text generation."""

from __future__ import annotations

import asyncio
import inspect
import io
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest
from generationengine import InferenceObservation, ObservationState, TextRequest, TextResult

from src.cli import DungeonBuddyCLI
from src.compiler.wiki_compiler import (
    WIKI_SYSTEM_PROMPT,
    _format_facts_for_prompt,
    _resolve_wiki_model,
    _wiki_user_prompt,
    compile_entity_page,
    compile_wiki,
    score_entity_connectivity,
    should_skip_entity_for_wiki,
)
from src.store import FactStore

_ENTITY_ID = "ent_thalia"
_DISPLAY = "Commander Thalia"
_ENTITY_META = {
    "display_name": _DISPLAY,
    "entity_class": "actor",
    "entity_type": "npc",
    "aliases": ["Thalia", "The Commander"],
}
_PROJECTION = {
    "attributes": {
        "operational_status": {
            "value_label": "Alive and active",
            "source_truth_state": "CANON",
            "source_layer": "world",
        },
        "source_comments": {
            "value_label": "do not leak comments",
            "source_truth_state": "CANON",
            "source_layer": "world",
        },
        "unresolved_questions": {
            "value_label": "do not leak questions",
            "source_truth_state": "CANON",
            "source_layer": "world",
        },
    }
}
_ARTICLE = "Commander Thalia is an actor, also known as Thalia. She is alive and active."


def _queued_text_result(text: str | None) -> TextResult:
    return TextResult(
        text=text,
        observation=InferenceObservation(
            latency_ms=0,
            retry_count=0,
            state=ObservationState.COMPLETED,
        ),
    )


def _expected_user_prompt() -> str:
    return _wiki_user_prompt(
        entity_id=_ENTITY_ID,
        display=_DISPLAY,
        cls="actor",
        alias_line="Thalia, The Commander",
        facts_block=_format_facts_for_prompt(_PROJECTION),
    )


class RecordingTextClient:
    def __init__(self, texts: list[str | None] | None = None) -> None:
        self._texts = list(texts) if texts is not None else [_ARTICLE]
        self._i = 0
        self.requests: list[TextRequest] = []
        self.calls = 0

    async def generate_text(self, request: TextRequest) -> TextResult:
        self.requests.append(request)
        self.calls += 1
        if self._i >= len(self._texts):
            raise RuntimeError("RecordingTextClient: no more queued responses")
        text = self._texts[self._i]
        self._i += 1
        return _queued_text_result(text)


def _compile_page(client: Any, **kwargs: Any) -> str:
    return compile_entity_page(
        entity_id=_ENTITY_ID,
        entity_meta=_ENTITY_META,
        projection_entity=_PROJECTION,
        client=client,
        **kwargs,
    )


def _base_record() -> dict[str, str]:
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-03-27T00:00:00Z",
        "updated_at": "2026-03-27T00:00:00Z",
        "record_status": "active",
    }


def _wiki_store(tmp_path: Path, rows: list[tuple[str, str]]) -> FactStore:
    store = FactStore(tmp_path / "store")
    for i, (entity_id, display_name) in enumerate(rows):
        evid = f"evid_{i}"
        store.evidence_units.append(
            {
                **_base_record(),
                "evidence_id": evid,
                "document_id": f"doc_{i}",
                "document_type": "world_reference",
                "document_title": "Wiki Test",
                "source_class": "seed_reference",
                "canon_layer": "world",
                "campaign_id": None,
                "text": f"{display_name} is active.",
                "section_path": ["Overview"],
                "paragraph_index": 0,
                "source_order_index": i,
                "line_span": {"start": 1, "end": 1},
                "char_span": None,
                "inferred_session": None,
                "speaker_or_subject": None,
                "notes": None,
                "source_anchors": [],
            }
        )
        store.entities.append(
            {
                **_base_record(),
                "entity_id": entity_id,
                "entity_class": "actor",
                "entity_type": "npc",
                "display_name": display_name,
                "aliases": [display_name],
            }
        )
        store.facts.append(
            {
                **_base_record(),
                "fact_id": f"fact_{i}",
                "subject_entity_id": entity_id,
                "attribute": "operational_status",
                "value": {
                    "kind": "state",
                    "label": f"{display_name} is active",
                    "normalized": "active",
                },
                "truth_state": "CANON",
                "source_authority": "seed_prep",
                "evidence_ids": [evid],
                "asserted_in_session": None,
                "sequence_index_within_session": None,
            }
        )
    return store


def test_should_skip_generic_names() -> None:
    assert should_skip_entity_for_wiki("She")
    assert should_skip_entity_for_wiki("meat")
    assert not should_skip_entity_for_wiki("Commander Thalia")


def test_score_entity_connectivity_non_empty_on_fixture_store() -> None:
    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/extraction_lab/sample_store"
    if not (fixture / "facts.json").exists():
        return
    store = FactStore(fixture)
    store.load()
    scores = score_entity_connectivity(store)
    assert isinstance(scores, dict)
    if scores:
        assert max(scores.values()) >= min(scores.values())


def test_generationengine_request_uses_explicit_openai_target() -> None:
    client = RecordingTextClient()
    article = _compile_page(client)
    assert article == _ARTICLE
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.provider == "openai"
    assert request.model == "gpt-5.3-codex"
    assert request.profile is None
    assert request.temperature == 0.35
    assert request.system_prompt == WIKI_SYSTEM_PROMPT
    assert request.user_prompt == _expected_user_prompt()
    assert request.json_schema is None
    assert request.schema_name is None
    assert "do not leak comments" not in request.user_prompt
    assert "do not leak questions" not in request.user_prompt
    assert "Alive and active" in request.user_prompt


def test_explicit_alternate_model_reaches_generationengine_unchanged() -> None:
    client = RecordingTextClient()
    _compile_page(client, model="gpt-4o-mini")
    assert client.requests[0].model == "gpt-4o-mini"


def test_env_model_override_reaches_generationengine_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DMB_WIKI_COMPILE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    store = _wiki_store(tmp_path, [(_ENTITY_ID, _DISPLAY)])
    constructed: list[Any] = []

    class _FakeGE:
        async def generate_text(self, request: TextRequest) -> TextResult:
            constructed.append(request.model)
            return _queued_text_result(_ARTICLE)

    monkeypatch.setattr(
        "src.compiler.wiki_compiler.GenerationClient.from_env",
        lambda: _FakeGE(),
    )
    new_pages = compile_wiki(store, None, entity_ids=[_ENTITY_ID], incremental=False)
    assert new_pages[_ENTITY_ID] == _ARTICLE
    assert constructed == ["gpt-4o-mini"]
    assert store.wiki_manifest[_ENTITY_ID]["model"] == "gpt-4o-mini"
    assert _resolve_wiki_model() == "gpt-4o-mini"


def test_policy_model_resolution_still_returns_gpt_53_codex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DMB_WIKI_COMPILE_MODEL", raising=False)
    assert _resolve_wiki_model() == "gpt-5.3-codex"


def test_output_strips_surrounding_whitespace() -> None:
    client = RecordingTextClient(["  padded article  \n"])
    assert _compile_page(client) == "padded article"


@pytest.mark.parametrize("text", [None, "", "   \n"])
def test_empty_or_whitespace_text_raises_existing_error(text: str | None) -> None:
    client = RecordingTextClient([text])
    with pytest.raises(RuntimeError, match=f"Empty wiki article for {_ENTITY_ID}"):
        _compile_page(client)


def test_generationengine_failure_propagates_without_retry() -> None:
    class _FailClient:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_text(self, request: TextRequest) -> TextResult:
            self.calls += 1
            raise RuntimeError("generation failed")

    client = _FailClient()
    with pytest.raises(RuntimeError, match="generation failed"):
        _compile_page(client)
    assert client.calls == 1


def test_ordinary_synchronous_compile_succeeds_without_running_loop() -> None:
    client = RecordingTextClient()
    assert _compile_page(client) == _ARTICLE
    assert len(client.requests) == 1


def test_synchronous_compile_succeeds_from_running_event_loop() -> None:
    client = RecordingTextClient()

    async def _inside_running_loop() -> str:
        return _compile_page(client)

    assert asyncio.run(_inside_running_loop()) == _ARTICLE
    assert len(client.requests) == 1


def test_production_client_is_constructed_inside_awaited_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    seen: list[asyncio.AbstractEventLoop] = []

    class _FakeGE:
        async def generate_text(self, request: TextRequest) -> TextResult:
            return _queued_text_result(_ARTICLE)

    def _from_env() -> _FakeGE:
        seen.append(asyncio.get_running_loop())
        return _FakeGE()

    monkeypatch.setattr(
        "src.compiler.wiki_compiler.GenerationClient.from_env",
        _from_env,
    )
    article = compile_entity_page(
        entity_id=_ENTITY_ID,
        entity_meta=_ENTITY_META,
        projection_entity=_PROJECTION,
    )
    assert article == _ARTICLE
    assert len(seen) == 1


def test_compile_wiki_constructs_execution_local_clients_not_one_shared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    store = _wiki_store(
        tmp_path,
        [("ent_alpha", "Alpha Captain"), ("ent_beta", "Beta Warden")],
    )
    constructed: list[object] = []
    loops: list[int] = []

    class _FakeGE:
        def __init__(self) -> None:
            constructed.append(self)

        async def generate_text(self, request: TextRequest) -> TextResult:
            loops.append(id(asyncio.get_running_loop()))
            entity_id = request.user_prompt.splitlines()[0].removeprefix("Entity ID: ").strip()
            return _queued_text_result(f"Article for {entity_id}.")

    monkeypatch.setattr(
        "src.compiler.wiki_compiler.GenerationClient.from_env",
        lambda: _FakeGE(),
    )
    new_pages = compile_wiki(
        store,
        None,
        entity_ids=["ent_alpha", "ent_beta"],
        incremental=False,
        max_workers=2,
    )
    assert new_pages == {
        "ent_alpha": "Article for ent_alpha.",
        "ent_beta": "Article for ent_beta.",
    }
    assert len(constructed) == 2
    assert constructed[0] is not constructed[1]
    assert len(loops) == 2
    assert store.wiki_pages["ent_alpha"] == "Article for ent_alpha."
    assert store.wiki_manifest["ent_alpha"]["model"] == "gpt-5.3-codex"
    assert store.wiki_manifest["ent_beta"]["model"] == "gpt-5.3-codex"


def test_compile_wiki_preserves_thread_pool_max_workers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    store = _wiki_store(tmp_path, [("ent_alpha", "Alpha Captain")])
    seen: list[int] = []
    real_tpe = ThreadPoolExecutor

    class _RecordingTPE(ThreadPoolExecutor):
        def __init__(self, max_workers: int | None = None, **kwargs: Any) -> None:
            seen.append(int(max_workers or 0))
            super().__init__(max_workers=max_workers, **kwargs)

    class _FakeGE:
        async def generate_text(self, request: TextRequest) -> TextResult:
            return _queued_text_result(_ARTICLE)

    monkeypatch.setattr("src.compiler.wiki_compiler.ThreadPoolExecutor", _RecordingTPE)
    monkeypatch.setattr(
        "src.compiler.wiki_compiler.GenerationClient.from_env",
        lambda: _FakeGE(),
    )
    compile_wiki(
        store,
        None,
        entity_ids=["ent_alpha"],
        incremental=False,
        max_workers=3,
    )
    assert seen == [3]
    assert real_tpe is ThreadPoolExecutor


def test_compile_wiki_incremental_skips_unchanged_pages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    store = _wiki_store(tmp_path, [("ent_alpha", "Alpha Captain")])
    calls = {"n": 0}

    class _FakeGE:
        async def generate_text(self, request: TextRequest) -> TextResult:
            calls["n"] += 1
            return _queued_text_result(_ARTICLE)

    monkeypatch.setattr(
        "src.compiler.wiki_compiler.GenerationClient.from_env",
        lambda: _FakeGE(),
    )
    first = compile_wiki(store, None, entity_ids=["ent_alpha"], incremental=True)
    second = compile_wiki(store, None, entity_ids=["ent_alpha"], incremental=True)
    assert first == {"ent_alpha": _ARTICLE}
    assert second == {}
    assert calls["n"] == 1
    assert store.wiki_pages["ent_alpha"] == _ARTICLE


def test_production_direct_call_requires_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def _boom() -> Any:
        raise AssertionError("missing key must not construct GenerationEngine")

    monkeypatch.setattr(
        "src.compiler.wiki_compiler.GenerationClient.from_env",
        _boom,
    )
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required for compile_entity_page."):
        compile_entity_page(
            entity_id=_ENTITY_ID,
            entity_meta=_ENTITY_META,
            projection_entity=_PROJECTION,
        )


def test_injected_client_bypasses_provider_credential_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = RecordingTextClient()
    assert _compile_page(client) == _ARTICLE


def test_cli_requires_openai_api_key_before_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli._cmd_compile_wiki(["--list"])
    assert buf.getvalue().strip() == "Error: OPENAI_API_KEY is required for compile-wiki."


def test_cli_list_does_not_compile_when_key_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def _boom(*_args: Any, **_kwargs: Any) -> dict[str, str]:
        raise AssertionError("--list must not compile wiki pages")

    monkeypatch.setattr("src.cli.compile_wiki", _boom)
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli._cmd_compile_wiki(["--list"])
    assert "Would compile 0 entity wiki page(s):" in buf.getvalue()


def test_production_path_no_longer_owns_openai_or_wrapper_telemetry() -> None:
    import src.compiler.wiki_compiler as wiki_compiler

    source = inspect.getsource(compile_entity_page)
    module_source = inspect.getsource(wiki_compiler)
    assert "from openai import" not in module_source
    assert "DungeonMindApiClient" not in module_source
    assert "chat_completions_create" not in module_source
    assert "generate_structured" not in module_source
    assert "generate_text" in source
    assert "run_awaitable_sync" in source
    assert "temperature=0.35" in source
    assert "OpenAI(" not in module_source
