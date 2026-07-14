"""Owning tests for PR010B Rung 3 embedded Hermes graph-agent turn."""

from __future__ import annotations

import ast
import importlib.metadata
import json
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from apps.live_control_server.services.hermes_graph_agent import (
    HermesGraphAgentTurnRequest,
    run_hermes_graph_agent_turn,
)
from apps.live_control_server.services.hermes_graph_read_tool_adapter import (
    hermes_graph_read_tool_definitions,
)
from apps.live_control_server.services.hermes_graph_read_tools import (
    HERMES_GRAPH_READ_TOOL_NAMES,
)
from graph_memory.hermes_graph_plugin import TOOLSET_NAME

PLUGIN_MODULE = (
    Path(__file__).resolve().parents[1] / "src" / "graph_memory" / "hermes_graph_plugin.py"
)
AGENT_MODULE = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "live_control_server"
    / "services"
    / "hermes_graph_agent.py"
)

ORDERED_TOOL_NAMES = (
    "search_campaign_graph",
    "get_campaign_object",
    "get_object_neighborhood",
    "get_object_evidence",
    "read_source_anchor",
)

LEGACY_TOOL_NAMES = (
    "dungeon_context_lookup",
    "dungeon_manifest_index",
    "dungeon_get_document",
    "dungeon_search",
    "dungeon_check_continuity",
)

FORBIDDEN_IMPORT_TOKENS = (
    "integrations.hermes.plugins.dungeonbuddy",
    "live_agent_loop",
    "manifest_context_query",
    "live_query_context",
    "subprocess",
)


def _collect_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            for alias in node.names:
                imported.add(f"{module}.{alias.name}" if module else alias.name)
    return imported


def test_hermes_aiagent_imports_from_locked_environment() -> None:
    from apps.live_control_server.services.hermes_graph_agent import (
        import_hermes_aiagent,
    )

    AIAgent = import_hermes_aiagent()
    assert AIAgent.__name__ == "AIAgent"


def test_entry_point_declares_dungeonbuddy_graph_plugin() -> None:
    eps = importlib.metadata.entry_points()
    if hasattr(eps, "select"):
        group = list(eps.select(group="hermes_agent.plugins"))
    else:
        group = [ep for ep in eps if getattr(ep, "group", None) == "hermes_agent.plugins"]
    matches = [ep for ep in group if ep.name == "dungeonbuddy_graph"]
    assert len(matches) == 1
    assert matches[0].value == "graph_memory.hermes_graph_plugin"


def _enable_graph_plugin(tmp_path: Path) -> Path:
    home = tmp_path / "hermes-home"
    home.mkdir()
    (home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": [TOOLSET_NAME], "disabled": []}}),
        encoding="utf-8",
    )
    return home


def test_plugin_discovery_registers_exact_five_graph_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = _enable_graph_plugin(tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))

    from hermes_cli import plugins as hermes_plugins
    from tools.registry import registry

    hermes_plugins.discover_plugins(force=True)
    loaded = hermes_plugins.get_plugin_manager()._plugins.get("dungeonbuddy_graph")
    assert loaded is not None
    assert loaded.enabled is True
    assert loaded.error is None

    entries, _ = registry._snapshot_state()
    graph_tools = [e for e in entries if e.toolset == TOOLSET_NAME]
    names = [e.name for e in graph_tools]
    assert names == list(ORDERED_TOOL_NAMES)
    assert set(names) == set(HERMES_GRAPH_READ_TOOL_NAMES)
    for legacy in LEGACY_TOOL_NAMES:
        assert legacy not in names


def test_plugin_schemas_match_rung2_catalog_function_schemas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = _enable_graph_plugin(tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))

    from hermes_cli import plugins as hermes_plugins
    from tools.registry import registry

    hermes_plugins.discover_plugins(force=True)
    catalog = {
        item["function"]["name"]: item["function"]
        for item in hermes_graph_read_tool_definitions()
    }
    entries, _ = registry._snapshot_state()
    for entry in entries:
        if entry.toolset != TOOLSET_NAME:
            continue
        assert entry.schema == catalog[entry.name]


def test_plugin_handlers_route_to_rung2_json_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = _enable_graph_plugin(tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))

    from hermes_cli import plugins as hermes_plugins
    from tools.registry import registry

    hermes_plugins.discover_plugins(force=True)

    calls: list[tuple[str, dict[str, Any]]] = []

    def _fake_execute(tool_name: str, arguments: Any, *, root: Any = None) -> str:
        del root
        calls.append((tool_name, dict(arguments)))
        return json.dumps(
            {
                "schema": "dmb_world_graph_retrieval_result_v1",
                "operation": "search",
                "outcome": "empty",
                "matchedNodeIds": [],
            }
        )

    monkeypatch.setattr(
        "graph_memory.hermes_graph_plugin.execute_hermes_graph_read_tool_json",
        _fake_execute,
    )

    entries, _ = registry._snapshot_state()
    by_name = {e.name: e for e in entries if e.toolset == TOOLSET_NAME}
    payload = {
        "schema": "dmb_world_graph_search_request_v1",
        "worldId": "world:eldyrwild",
        "campaignId": "campaign:c1",
        "queryText": "Tripod",
    }
    result = by_name["search_campaign_graph"].handler(payload)
    assert isinstance(result, str)
    assert calls == [("search_campaign_graph", payload)]
    assert json.loads(result)["outcome"] == "empty"


class _FakeAgent:
    last_init: dict[str, Any] | None = None
    last_run: dict[str, Any] | None = None

    def __init__(self, **kwargs: Any) -> None:
        type(self).last_init = dict(kwargs)
        self.session_id = kwargs.get("session_id")
        self._start = kwargs.get("tool_start_callback")
        self._complete = kwargs.get("tool_complete_callback")

    def run_conversation(
        self,
        user_message: str,
        system_message: str = None,
        conversation_history: list[dict[str, Any]] | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        del system_message
        type(self).last_run = {
            "user_message": user_message,
            "conversation_history": conversation_history,
        }
        if self._start and self._complete:
            args = {
                "schema": "dmb_world_graph_search_request_v1",
                "worldId": "world:eldyrwild",
                "campaignId": "campaign:c1",
                "queryText": "Tripod",
                "focus": {"kind": "none", "sessionId": None},
                "admissibility": "gm",
                "revisionPin": None,
            }
            tool_json = json.dumps(
                {
                    "schema": "dmb_world_graph_retrieval_result_v1",
                    "operation": "search",
                    "outcome": "partial",
                    "matchedNodeIds": ["threat:tripod-null-calf"],
                    "relationships": [{"id": "rel:1"}],
                    "sourceAnchors": [{"anchorId": "source-anchor:v1:abc"}],
                    "diagnostics": [{"code": "coverage_gap"}],
                    "content": "/secret/path should never appear in events",
                }
            )
            self._start("call-1", "search_campaign_graph", args)
            self._complete("call-1", "search_campaign_graph", args, tool_json)
        return {
            "final_response": "Tripod is at the North Gate.",
            "messages": [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": "Tripod is at the North Gate."},
            ],
            "session_id": self.session_id,
        }


def test_agent_receives_exact_lockdown_configuration(tmp_path: Path) -> None:
    _FakeAgent.last_init = None
    result = run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="What do we know about Tripod?",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            session_id="sess-test-1",
            root=tmp_path,
        ),
        agent_factory=_FakeAgent,
    )
    assert result.status == "ok"
    init = _FakeAgent.last_init or {}
    assert init.get("quiet_mode") is True
    assert init.get("skip_memory") is True
    assert init.get("skip_context_files") is True
    assert init.get("enabled_toolsets") == [TOOLSET_NAME]
    assert init.get("fallback_model") is None
    assert "disabled_toolsets" not in init or init.get("disabled_toolsets") in (None, [])


def test_turn_passes_history_and_captures_messages(tmp_path: Path) -> None:
    history = [{"role": "user", "content": "Remember: it means Tripod."}]
    result = run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="What is it connected to?",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            conversation_history=history,
            session_id="sess-hist",
            root=tmp_path,
        ),
        agent_factory=_FakeAgent,
    )
    assert result.status == "ok"
    assert _FakeAgent.last_run is not None
    assert _FakeAgent.last_run["conversation_history"] == history
    assert result.final_response == "Tripod is at the North Gate."
    assert result.messages[0]["role"] == "user"
    assert result.hermes_session_id == "sess-hist"


def test_tool_events_preserve_order_and_redact_unsafe_content(tmp_path: Path) -> None:
    result = run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="Find Tripod",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            session_id="sess-events",
            root=tmp_path,
        ),
        agent_factory=_FakeAgent,
    )
    assert result.status == "ok"
    assert [e.state for e in result.tool_events] == ["start", "completion"]
    assert result.tool_events[0].tool_name == "search_campaign_graph"
    completion = result.tool_events[1]
    assert completion.outcome == "partial"
    assert completion.matched_node_ids == ["threat:tripod-null-calf"]
    assert completion.relationship_ids == ["rel:1"]
    assert completion.source_anchor_ids == ["source-anchor:v1:abc"]
    assert completion.diagnostic_codes == ["coverage_gap"]
    dumped = json.dumps(
        [
            {
                "tool": e.tool_name,
                "state": e.state,
                "ids": e.bounded_ids,
                "anchors": e.source_anchor_ids,
            }
            for e in result.tool_events
        ]
    )
    assert "/secret/path" not in dumped
    assert "should never appear" not in dumped


@pytest.mark.parametrize("outcome", ("empty", "partial", "denied", "unavailable"))
def test_graph_miss_outcomes_do_not_trigger_alternate_retrieval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    class _OutcomeAgent(_FakeAgent):
        def run_conversation(self, user_message: str, **kwargs: Any) -> dict[str, Any]:
            if self._complete:
                args = {
                    "worldId": "world:eldyrwild",
                    "campaignId": "campaign:c1",
                    "queryText": "missing",
                }
                self._start("c1", "search_campaign_graph", args)
                self._complete(
                    "c1",
                    "search_campaign_graph",
                    args,
                    json.dumps(
                        {
                            "schema": "dmb_world_graph_retrieval_result_v1",
                            "operation": "search",
                            "outcome": outcome,
                            "matchedNodeIds": [],
                        }
                    ),
                )
            return {
                "final_response": f"Graph outcome was {outcome}.",
                "messages": [],
                "session_id": self.session_id,
            }

    invoked: list[str] = []

    def _track(name: str) -> Any:
        def _spy(*_a: Any, **_k: Any) -> Any:
            invoked.append(name)
            raise AssertionError(f"forbidden retrieval {name}")

        return _spy

    for forbidden in (
        "manifest_context_query",
        "live_query_context",
        "subprocess",
    ):
        monkeypatch.setattr(
            f"apps.live_control_server.services.hermes_graph_agent.{forbidden}",
            _track(forbidden),
            raising=False,
        )

    result = run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="Is this in the graph?",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            root=tmp_path,
        ),
        agent_factory=_OutcomeAgent,
    )
    assert result.status == "ok"
    assert result.tool_events[-1].outcome == outcome
    assert invoked == []


def test_provider_failure_returns_typed_error_without_fallback(tmp_path: Path) -> None:
    class _BoomAgent(_FakeAgent):
        def run_conversation(self, *_a: Any, **_k: Any) -> dict[str, Any]:
            raise RuntimeError("/secret/provider OPENAI_KEY=sk-leak")

    result = run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="Anything?",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            root=tmp_path,
        ),
        agent_factory=_BoomAgent,
    )
    assert result.status == "error"
    assert result.error_code == "hermes_turn_error"
    assert result.error_message is not None
    assert "/secret/provider" not in result.error_message
    assert "sk-leak" not in result.error_message
    assert result.final_response is None


def test_model_visible_toolsets_only_dungeonbuddy_graph(tmp_path: Path) -> None:
    run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="q",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            root=tmp_path,
        ),
        agent_factory=_FakeAgent,
    )
    init = _FakeAgent.last_init or {}
    assert init["enabled_toolsets"] == [TOOLSET_NAME]
    for legacy in LEGACY_TOOL_NAMES:
        assert legacy not in init["enabled_toolsets"]


def test_no_subprocess_or_direct_openai_loop_in_production_modules() -> None:
    for path in (PLUGIN_MODULE, AGENT_MODULE):
        imported = _collect_imports(path)
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_IMPORT_TOKENS:
            assert token not in imported
            assert not any(
                token == name or name.startswith(f"{token}.") for name in imported
            )
        assert "openai" not in imported
        assert "OpenAI(" not in source
        assert "import subprocess" not in source
        assert "from subprocess" not in source
        assert "Popen(" not in source
        assert "--oneshot" not in source


def test_isolated_hermes_home_does_not_mutate_user_global_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = tmp_path / "user-global"
    sentinel.mkdir()
    config = sentinel / "config.yaml"
    config.write_text("plugins:\n  enabled: []\n", encoding="utf-8")
    before = config.read_text(encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(sentinel))

    # The runtime must replace HERMES_HOME with an isolated temp home and
    # restore the previous value afterward.
    result = run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="q",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            root=tmp_path / "graph",
        ),
        agent_factory=_FakeAgent,
    )
    assert result.status == "ok"
    assert config.read_text(encoding="utf-8") == before
    assert os.environ.get("HERMES_HOME") == str(sentinel)
