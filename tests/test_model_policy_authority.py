"""E1B fitness: active runtime model-policy authority stays inside Buddy."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "apps", ROOT / "src")
ALLOWED_POLICY_PATH_FILES = {
    (ROOT / "src" / "model_policy.py").resolve(),
}

# Literal path construction / file name that would reintroduce cross-repo discovery.
_PATH_CONSTRUCTION = re.compile(
    r"""(?:parents\[\d+\]|Path\([^)]*\)|\w+)\s*/\s*["']MODEL_POLICY\.json["']"""
    r"""|["']MODEL_POLICY\.json["']"""
)


def test_buddy_model_policy_path_is_inside_repo() -> None:
    from src.model_policy import buddy_model_policy_path, buddy_repo_root

    policy = buddy_model_policy_path().resolve()
    root = buddy_repo_root().resolve()
    assert policy.is_relative_to(root)
    assert policy.name == "MODEL_POLICY.json"
    assert policy.is_file()


def test_active_runtime_does_not_construct_external_model_policy_paths() -> None:
    """Active apps/src code may only construct MODEL_POLICY.json via src.model_policy."""
    offenders: list[str] = []
    for scan_root in SCAN_ROOTS:
        for path in scan_root.rglob("*.py"):
            if path.resolve() in ALLOWED_POLICY_PATH_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            for match in _PATH_CONSTRUCTION.finditer(text):
                # Allow narrative mentions in comments/docstrings that do not construct paths.
                line_start = text.rfind("\n", 0, match.start()) + 1
                line = text[line_start : text.find("\n", match.start())]
                stripped = line.lstrip()
                if stripped.startswith("#") or '"""' in line or "'''" in line:
                    # Still forbid path construction inside comments.
                    if "parents[" in line or " / " in line or '.parent /' in line:
                        offenders.append(f"{path.relative_to(ROOT)}: {stripped}")
                    continue
                offenders.append(f"{path.relative_to(ROOT)}: {stripped}")
    assert offenders == [], (
        "Active apps/src code must load policy via src.model_policy; "
        f"found forbidden MODEL_POLICY.json path usage in: {offenders}"
    )


def test_active_consumer_model_parity_with_e1b_baseline(monkeypatch) -> None:
    """Preserve Phase-0 effective models after localizing policy authority."""
    monkeypatch.delenv("DUNGEONMIND_HERMES_GRAPH_MODEL", raising=False)
    monkeypatch.delenv("LIVE_TURN_CLASSIFIER_MODEL", raising=False)
    monkeypatch.delenv("NPC_INTENT_CLASSIFIER_MODEL", raising=False)
    monkeypatch.delenv("DMB_WIKI_COMPILE_MODEL", raising=False)

    from apps.live_control_server.services.agent_graph_policy import (
        resolve_agent_graph_openai_inference,
    )
    from src.agent.document_planner import _resolve_document_planner_model
    from src.agent.planner import _resolve_planner_model
    from src.agent.synthesis import _resolve_model
    from src.compiler.wiki_compiler import _resolve_wiki_model
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        resolve_category_graph_model,
    )
    from src.ingestion.entity_extractor import _load_fast_smart_model_id
    from src.ingestion.fact_extractor import _load_model_id as load_fact_model
    from src.ingestion.frontmatter_inference import _load_model_id as load_frontmatter_model
    from src.live_play.classify_live_turn import _resolve_classifier_model
    from src.live_play.live_query_context import _live_query_model
    from src.npc_statblock_pipeline.canonical_intent import _resolve_intent_classifier_model

    monkeypatch.setattr(
        "src.bootstrap_env.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )
    provider, model, base_url = resolve_agent_graph_openai_inference(require_api_key=False)
    assert (provider, model, base_url) == (
        "openai-api",
        "gpt-5.3-codex",
        "https://api.openai.com/v1",
    )
    assert _resolve_model(None) == "gpt-5.3-chat-latest"
    assert _resolve_document_planner_model(None) == "gpt-5.4-nano"
    assert _resolve_planner_model(None) == "gpt-5.4-mini"
    assert _resolve_classifier_model(None) == "gpt-5.3-codex"
    assert _resolve_intent_classifier_model(None) == "gpt-5.3-codex"
    assert resolve_category_graph_model(None) == "gpt-5.4-mini"
    assert _resolve_wiki_model() == "gpt-5.3-codex"
    assert load_frontmatter_model() == "gpt-5.3-codex"
    assert load_fact_model() == "gpt-5.3-codex"
    assert _load_fast_smart_model_id() == "gpt-5.3-codex"
    assert _live_query_model(ROOT) == "gpt-5.3-chat-latest"


def _point_policy_at(monkeypatch, path: Path) -> None:
    monkeypatch.setattr("src.model_policy.buddy_model_policy_path", lambda: path)


def test_missing_policy_returns_empty_dict_in_both_modes(tmp_path, monkeypatch) -> None:
    from src.model_policy import load_buddy_model_policy

    _point_policy_at(monkeypatch, tmp_path / "MODEL_POLICY.json")
    assert load_buddy_model_policy() == {}
    assert load_buddy_model_policy(strict=True) == {}


def test_malformed_policy_strict_raises_tolerant_returns_empty(tmp_path, monkeypatch) -> None:
    from src.model_policy import load_buddy_model_policy

    path = tmp_path / "MODEL_POLICY.json"
    path.write_text("{not-json", encoding="utf-8")
    _point_policy_at(monkeypatch, path)
    with pytest.raises(json.JSONDecodeError):
        load_buddy_model_policy(strict=True)
    assert load_buddy_model_policy(strict=False) == {}


def test_unreadable_policy_strict_raises_tolerant_returns_empty(tmp_path, monkeypatch) -> None:
    from src.model_policy import load_buddy_model_policy

    path = tmp_path / "MODEL_POLICY.json"
    path.write_text("{}", encoding="utf-8")
    _point_policy_at(monkeypatch, path)
    original_read_text = Path.read_text

    def _read_text(self, *args, **kwargs):
        if Path(self).resolve() == path.resolve():
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _read_text)
    with pytest.raises(OSError):
        load_buddy_model_policy(strict=True)
    assert load_buddy_model_policy(strict=False) == {}


def test_strict_consumers_fall_back_when_policy_missing_and_raise_when_malformed(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("DMB_WIKI_COMPILE_MODEL", raising=False)

    from src.agent.synthesis import _resolve_model
    from src.compiler.wiki_compiler import _resolve_wiki_model
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        resolve_category_graph_model,
    )
    from src.ingestion.entity_extractor import _load_fast_smart_model_id
    from src.ingestion.fact_extractor import _load_model_id as load_fact_model
    from src.ingestion.frontmatter_inference import _load_model_id as load_frontmatter_model

    missing = tmp_path / "missing" / "MODEL_POLICY.json"
    _point_policy_at(monkeypatch, missing)
    assert _resolve_model(None) == "gpt-5.3-chat-latest"
    assert _resolve_wiki_model() == "gpt-5.4-nano"
    assert load_frontmatter_model() == "gpt-5.3-chat-latest"
    assert load_fact_model() == "fast_smart"
    assert _load_fast_smart_model_id() == "fast_smart"
    assert resolve_category_graph_model(None) == "gpt-5.4-mini"

    malformed = tmp_path / "MODEL_POLICY.json"
    malformed.write_text("{not-json", encoding="utf-8")
    _point_policy_at(monkeypatch, malformed)
    with pytest.raises(json.JSONDecodeError):
        _resolve_model(None)
    with pytest.raises(json.JSONDecodeError):
        _resolve_wiki_model()
    with pytest.raises(json.JSONDecodeError):
        load_frontmatter_model()
    with pytest.raises(json.JSONDecodeError):
        load_fact_model()
    with pytest.raises(json.JSONDecodeError):
        _load_fast_smart_model_id()
    with pytest.raises(json.JSONDecodeError):
        resolve_category_graph_model(None)


def test_tolerant_consumers_fall_back_when_policy_missing_or_malformed(
    tmp_path, monkeypatch
) -> None:
    from apps.live_control_server.services.agent_graph_policy import (
        resolve_agent_graph_openai_inference,
    )
    from src.agent.document_planner import DEFAULT_MODEL, _resolve_document_planner_model
    from src.agent.planner import _resolve_planner_model
    from src.live_play.classify_live_turn import _resolve_classifier_model
    from src.live_play.live_query_context import _live_query_model
    from src.npc_statblock_pipeline.canonical_intent import _resolve_intent_classifier_model

    monkeypatch.setattr("src.bootstrap_env.load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.delenv("DUNGEONMIND_HERMES_GRAPH_MODEL", raising=False)
    monkeypatch.delenv("LIVE_TURN_CLASSIFIER_MODEL", raising=False)
    monkeypatch.delenv("NPC_INTENT_CLASSIFIER_MODEL", raising=False)

    def _assert_tolerant_fallbacks() -> None:
        provider, model, base_url = resolve_agent_graph_openai_inference(
            require_api_key=False
        )
        assert (provider, model, base_url) == (
            "openai-api",
            "gpt-5.4-mini",
            "https://api.openai.com/v1",
        )
        assert _resolve_document_planner_model(None) == DEFAULT_MODEL
        assert _resolve_planner_model(None) == "gpt-5.4-mini"
        assert _resolve_classifier_model(None) == "gpt-4o-mini"
        assert _resolve_intent_classifier_model(None) == "gpt-4o-mini"
        assert _live_query_model(ROOT) == "gpt-5.3-chat-latest"

    _point_policy_at(monkeypatch, tmp_path / "missing" / "MODEL_POLICY.json")
    _assert_tolerant_fallbacks()

    malformed = tmp_path / "MODEL_POLICY.json"
    malformed.write_text("{not-json", encoding="utf-8")
    _point_policy_at(monkeypatch, malformed)
    _assert_tolerant_fallbacks()
