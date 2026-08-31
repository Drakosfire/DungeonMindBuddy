"""A4/E1B: neutral graph-Agent policy ownership, Buddy-local model authority."""

from __future__ import annotations

import ast
from pathlib import Path

from apps.live_control_server.services import hermes_graph_agent as hermes_mod
from apps.live_control_server.services.agent_graph_policy import (
    GRAPH_SYSTEM_POLICY,
    resolve_agent_graph_openai_inference,
)
from src.model_policy import buddy_model_policy_path, buddy_repo_root, load_buddy_model_policy

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "apps/live_control_server/services"
CAMPAIGN_PREP = "You are a campaign-prep assistant for DungeonMindBuddy."


def _imported_names(path: Path, module: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "") == module:
            for alias in node.names:
                names.add(alias.name)
    return names


def test_agent_graph_policy_is_single_canonical_source() -> None:
    policy_src = (SERVICES / "agent_graph_policy.py").read_text(encoding="utf-8")
    hermes_src = (SERVICES / "hermes_graph_agent.py").read_text(encoding="utf-8")
    pai_src = (SERVICES / "pydantic_ai_agent_runtime.py").read_text(encoding="utf-8")
    assert "GRAPH_SYSTEM_POLICY =" in policy_src
    assert CAMPAIGN_PREP in policy_src
    assert CAMPAIGN_PREP not in hermes_src
    assert CAMPAIGN_PREP not in pai_src
    assert "def resolve_agent_graph_openai_inference" in policy_src
    assert "def _resolve_hermes_openai_inference" not in hermes_src
    assert "def _resolve_hermes_openai_inference" not in pai_src


def test_accepted_policy_clauses_moved_verbatim() -> None:
    assert GRAPH_SYSTEM_POLICY.startswith(CAMPAIGN_PREP)
    assert "call declare_conversation_context exactly once" in GRAPH_SYSTEM_POLICY
    assert "latest-recap change question" in GRAPH_SYSTEM_POLICY
    assert "name the campaign and session provenance" in GRAPH_SYSTEM_POLICY
    assert "Use read_graph_source only for quotation" in GRAPH_SYSTEM_POLICY
    assert "Do not use report scaffolding" in GRAPH_SYSTEM_POLICY
    assert "Manifest, corpus, Markdown" in GRAPH_SYSTEM_POLICY
    assert "or “Hermes answer.”" in GRAPH_SYSTEM_POLICY


def test_hermes_aliases_are_the_neutral_objects() -> None:
    assert hermes_mod._GRAPH_SYSTEM_POLICY is GRAPH_SYSTEM_POLICY
    assert (
        hermes_mod._resolve_hermes_openai_inference
        is resolve_agent_graph_openai_inference
    )


def test_pydantic_ai_does_not_import_policy_from_hermes() -> None:
    names = _imported_names(
        SERVICES / "pydantic_ai_agent_runtime.py",
        "apps.live_control_server.services.hermes_graph_agent",
    )
    assert "_GRAPH_SYSTEM_POLICY" not in names
    assert "_resolve_hermes_openai_inference" not in names
    assert names == {"_safe_ids_from_args", "_summarize_tool_result"}
    policy_names = _imported_names(
        SERVICES / "pydantic_ai_agent_runtime.py",
        "apps.live_control_server.services.agent_graph_policy",
    )
    assert policy_names == {"GRAPH_SYSTEM_POLICY", "resolve_agent_graph_openai_inference"}


def test_resolver_missing_key_and_require_flag(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.bootstrap_env.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DUNGEONMIND_HERMES_GRAPH_MODEL", raising=False)
    assert (
        resolve_agent_graph_openai_inference(require_api_key=True)
        == "hermes_openai_credentials_missing"
    )
    provider, model, base_url = resolve_agent_graph_openai_inference(
        require_api_key=False
    )
    assert provider == "openai-api"
    assert base_url == "https://api.openai.com/v1"
    assert model == "gpt-5.3-codex"


def test_resolver_env_override_and_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.bootstrap_env.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    monkeypatch.setenv("DUNGEONMIND_HERMES_GRAPH_MODEL", "gpt-test-override")
    provider, model, base_url = resolve_agent_graph_openai_inference(
        require_api_key=True
    )
    assert provider == "openai-api"
    assert model == "gpt-test-override"
    assert base_url == "https://api.openai.com/v1"


def test_resolver_uses_buddy_owned_policy_not_parent_workspace(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.bootstrap_env.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )
    monkeypatch.delenv("DUNGEONMIND_HERMES_GRAPH_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")

    src = (SERVICES / "agent_graph_policy.py").read_text(encoding="utf-8")
    assert 'actions.get("hermes_graph_agent")' in src
    assert "default_text_generation" in src
    assert "DUNGEONMIND_HERMES_GRAPH_MODEL" in src
    assert '"openai-api"' in src
    assert "https://api.openai.com/v1" in src
    assert "load_buddy_model_policy" in src
    assert "parents[4]" not in src

    policy_path = buddy_model_policy_path()
    assert policy_path.is_file()
    assert policy_path.resolve().is_relative_to(buddy_repo_root().resolve())
    policy = load_buddy_model_policy()
    actions = policy.get("actions") if isinstance(policy.get("actions"), dict) else {}
    models = policy.get("models") if isinstance(policy.get("models"), dict) else {}
    assert "default_text_generation" in actions
    assert models.get(actions["default_text_generation"]) == "gpt-5.3-codex"

    provider, model, base_url = resolve_agent_graph_openai_inference(require_api_key=True)
    assert provider == "openai-api"
    assert model == "gpt-5.3-codex"
    assert base_url == "https://api.openai.com/v1"
