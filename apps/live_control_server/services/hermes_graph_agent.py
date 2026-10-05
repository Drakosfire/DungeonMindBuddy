"""Embedded Hermes graph-agent turn runtime (PR010B Rung 3).

Constructs a lockdown ``AIAgent`` from a caller-supplied capability policy,
runs one ``run_conversation`` turn, and returns a typed internal result with
ordered safe tool-event summaries. No Live/legacy/subprocess fallback.

Process isolation
-----------------
This wrapper is **process-exclusive**, not generally server-safe. Hermes and
DungeonBuddy both ship a top-level ``agent`` package, and Hermes lazily
re-imports ``agent.*`` during ``run_conversation``. For the duration of a turn
this runtime therefore:

* prefers Hermes site-packages on ``sys.path`` and binds Hermes ``agent.*`` in
  ``sys.modules``;
* sets process-wide ``HERMES_HOME`` to an isolated per-turn temp profile while
  pinning Hermes' cached file-logger home to the reusable worker's private home.

A process-wide :data:`_RUNTIME_LOCK` serializes *these* turns against each
other. It cannot protect unrelated server threads that import modules or
consult ``HERMES_HOME`` concurrently. Do not represent this wrapper as a
multi-tenant in-process server runtime. Product hosting that needs concurrent
Hermes + DungeonBuddy agent imports must isolate processes (later work).
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from apps.live_control_server.services.agent_graph_policy import (
    GRAPH_SYSTEM_POLICY as _GRAPH_SYSTEM_POLICY,
    resolve_agent_graph_openai_inference as _resolve_hermes_openai_inference,
)
from apps.live_control_server.services.agent_turn_trace import (
    map_hermes_observer_to_model_call,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    PROCESS_ISOLATION_MODE,
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    HermesGraphToolEvent,
    ProcessIsolationMode,
    ToolEventState,
    deserialize_capability_policy,
    deserialize_hermes_graph_agent_turn_request,
    deserialize_hermes_graph_agent_turn_result,
    serialize_capability_policy,
    serialize_hermes_graph_agent_turn_request,
    serialize_hermes_graph_agent_turn_result,
)
from graph_memory.hermes_graph_plugin import (
    DECLARE_CONVERSATION_CONTEXT_TOOL_NAME,
    HERMES_GRAPH_READ_TOOL_NAMES,
    HermesCapabilityPolicy,
    HermesGraphScope,
    HermesPluginActivation,
    HermesToolCapabilityRule,
    default_graph_only_capability_policy,
    reset_active_capability_policy,
    reset_active_retrieval_session_id,
    reset_parent_graph_broker,
    reset_graph_root_override,
    set_active_capability_policy,
    set_active_retrieval_session_id,
    set_parent_graph_broker,
    get_parent_retrieval_session_packet,
    set_graph_root_override,
    validate_capability_policy_structure,
)
from graph_memory.interaction.forensic import (
    build_tool_forensic_event,
    forensic_enabled,
)
from graph_memory.interaction.session_hydrate import hydrate_session_from_packet
from graph_memory.interaction.session_store import get_session
from graph_memory.retrieval.models import (
    RETRIEVAL_ERROR_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA,
)

HermesGraphAgentStatus = Literal["ok", "error"]

_RUNTIME_LOCK = threading.RLock()
_WORKER_HOME_ENV = "DMB_HERMES_GRAPH_AGENT_WORKER_HOME"
_SESSION_PROFILES_ENV = "DMB_HERMES_GRAPH_AGENT_SESSION_PROFILES_ROOT"
_CONVERSATION_ONLY_SYSTEM_POLICY = (
    "You are DungeonBuddy's conversational assistant. Respond using only the "
    "conversation context and descriptive current-surface context provided. "
    "No graph retrieval is performed on this turn. Earlier conversation may "
    "contain historical graph-derived statements; they are not revalidated as "
    "current graph evidence. Do not claim a fresh lookup or current verification "
    "from those statements. Identify them as prior conversation and request an "
    "explicit graph-retrieval turn when current confirmation is needed. You have "
    "no graph tools or external action tools on this turn."
)

_MAX_FOCUS_KIND_CHARS = 64
_MAX_FOCUS_SESSION_ID_CHARS = 128
_MAX_BOUNDED_ID_CHARS = 256
_MAX_BOUNDED_ID_LIST = 32
_MAX_MATCHED_IDS = 64


@contextmanager
def hermes_import_namespace() -> Iterator[None]:
    """Prefer the locked Hermes ``agent`` package over DungeonBuddy ``src/agent``.

    See module docstring: process-exclusive, not generally server-safe.
    Callers that mutate this process-global state must already hold
    :data:`_RUNTIME_LOCK`.
    """
    saved_path = list(sys.path)
    saved_agent_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "agent" or name.startswith("agent.")
    }
    site_packages = [
        entry
        for entry in saved_path
        if entry.replace("\\", "/").rstrip("/").endswith("site-packages")
    ]
    try:
        for name in list(saved_agent_modules):
            del sys.modules[name]
        reordered = [*site_packages, *[p for p in saved_path if p not in site_packages]]
        sys.path[:] = reordered
        yield
    finally:
        sys.path[:] = saved_path
        for name in list(sys.modules):
            if name == "agent" or name.startswith("agent."):
                del sys.modules[name]
        sys.modules.update(saved_agent_modules)


def import_hermes_aiagent() -> Any:
    """Import ``AIAgent`` from the locked Hermes environment."""
    with _RUNTIME_LOCK:
        with hermes_import_namespace():
            module = importlib.import_module("run_agent")
            return module.AIAgent


def _initialize_worker_logger_home() -> None:
    """Cache Hermes' logger home from the host-owned worker profile once."""
    worker_home = os.environ.get(_WORKER_HOME_ENV)
    if not worker_home:
        return

    previous_home = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = worker_home
    try:
        with hermes_import_namespace():
            importlib.import_module("run_agent")
    finally:
        if previous_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = previous_home


def _derive_answer_scope(
    tool_events: Sequence[HermesGraphToolEvent],
) -> Literal["graph", "conversation_context"] | None:
    """Infer explicit answer scope from completed tool events only."""
    graph_called = False
    declare_completed = False
    for event in tool_events:
        if event.tool_name in HERMES_GRAPH_READ_TOOL_NAMES:
            graph_called = True
        if (
            event.tool_name == DECLARE_CONVERSATION_CONTEXT_TOOL_NAME
            and event.state == "completion"
        ):
            declare_completed = True
    if declare_completed and not graph_called:
        return "conversation_context"
    if graph_called:
        return "graph"
    return None


def _error_result(
    *,
    hermes_session_id: str,
    error_code: str,
    error_message: str,
    messages: list[dict[str, Any]] | None = None,
    tool_events: list[HermesGraphToolEvent] | None = None,
    model_calls: list[dict[str, Any]] | None = None,
    telemetry_warnings: list[str] | None = None,
) -> HermesGraphAgentTurnResult:
    return HermesGraphAgentTurnResult(
        status="error",
        final_response=None,
        messages=list(messages or []),
        hermes_session_id=hermes_session_id,
        tool_events=list(tool_events or []),
        error_code=error_code,
        error_message=error_message,
        process_isolation=PROCESS_ISOLATION_MODE,
        model_calls=list(model_calls or []),
        telemetry_warnings=list(telemetry_warnings or []),
    )


def _resolve_capability_policy(
    request: HermesGraphAgentTurnRequest,
) -> HermesCapabilityPolicy:
    if request.capability_policy is not None:
        return request.capability_policy
    if (
        request.world_id is None
        or request.campaign_id is None
        or request.scope_mode is None
    ):
        raise ValueError(
            "no-scope turns require an explicit conversation-only capability policy"
        )
    focus = (
        dict(request.focus)
        if request.focus is not None
        else {"kind": "none", "sessionId": None}
    )
    admissibility = request.admissibility if request.admissibility is not None else "gm"
    scope = HermesGraphScope(
        world_id=str(request.world_id).strip(),
        campaign_id=str(request.campaign_id).strip(),
        scope_mode=request.scope_mode,
        focus=focus,
        admissibility=str(admissibility),
        revision_pin=request.revision_pin,
    )
    return default_graph_only_capability_policy(scope)


def _prepare_isolated_hermes_home(
    home: Path,
    *,
    enabled_plugin_ids: Sequence[str],
    model: str,
    provider: str = "openai-api",
    base_url: str = "https://api.openai.com/v1",
) -> None:
    """Write an isolated Hermes profile that cannot inherit ~/.hermes Anthropic defaults."""
    home.mkdir(parents=True, exist_ok=True)
    config_path = home / "config.yaml"
    config = {
        "plugins": {
            "enabled": list(enabled_plugin_ids),
            "disabled": [],
        },
        # Pin product inference to OpenAI. Ambient Hermes CLI profiles often
        # default to anthropic/* + auto provider; that 404s when Buddy only
        # has OPENAI_API_KEY.
        "model": {
            "default": model,
            "provider": provider,
            "base_url": base_url,
        },
    }
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )


def _native_history_is_valid(history: Any) -> bool:
    if not isinstance(history, list) or not history:
        return False
    if any(
        not isinstance(message, Mapping)
        or message.get("role") not in {"user", "assistant", "tool"}
        or "content" not in message
        for message in history
    ):
        return False
    return (
        history[-1].get("role") == "assistant"
        and any(message.get("role") == "user" for message in history)
        and any(message.get("role") == "assistant" for message in history)
    )


def _load_native_hermes_history(
    *,
    session_id: str,
    state_db_path: Path,
) -> tuple[Any, list[dict[str, Any]] | None]:
    """Read one exact Hermes session without changing its profile."""
    if not state_db_path.is_file() or state_db_path.is_symlink():
        return None, None
    try:
        with hermes_import_namespace():
            hermes_state = importlib.import_module("hermes_state")
            session_db = hermes_state.SessionDB(db_path=state_db_path, read_only=True)
            try:
                session_row = session_db.get_session(session_id)
                history = session_db.get_messages_as_conversation(session_id)
            finally:
                session_db.close()
    except Exception:
        return None, None
    if not isinstance(session_row, Mapping) or not _native_history_is_valid(history):
        return None, None
    return hermes_state, [dict(message) for message in history]


def _remove_unbound_hermes_profile(profile_home: Path, profiles_root: Path) -> None:
    """Remove only a profile path contained directly in the dedicated root."""
    if profile_home.is_symlink():
        profile_home.unlink()
        return
    resolved_root = profiles_root.resolve()
    resolved_profile = profile_home.resolve()
    if resolved_profile.parent != resolved_root:
        raise ValueError("Hermes session profile escaped its isolated root")
    if resolved_profile.is_dir():
        shutil.rmtree(resolved_profile)
    elif resolved_profile.exists():
        resolved_profile.unlink()


def _persisted_turn_matches(
    session_db: Any,
    *,
    session_id: str,
    question: str,
    final_response: str | None,
) -> bool:
    try:
        history = session_db.get_messages_as_conversation(session_id)
    except Exception:
        return False
    if not _native_history_is_valid(history):
        return False
    last_user = next(
        (message for message in reversed(history) if message.get("role") == "user"),
        None,
    )
    last_assistant = history[-1]
    return (
        isinstance(last_user, Mapping)
        and str(last_user.get("content") or "").strip() == question
        and isinstance(final_response, str)
        and str(last_assistant.get("content") or "").strip() == final_response.strip()
    )


def _scope_block(
    policy: HermesCapabilityPolicy,
    *,
    retrieval_session_id: str | None = None,
    retrieval_session: Mapping[str, Any] | None = None,
) -> str:
    scope = policy.graph_scope
    if scope is None:
        raise ValueError("graph capability policy requires graph scope")
    payload: dict[str, Any] = {
        "worldId": scope.world_id,
        "campaignId": scope.campaign_id,
        "scopeMode": scope.scope_mode,
        "focus": dict(scope.focus),
        "admissibility": scope.admissibility,
        "revisionPin": scope.revision_pin,
        "enabledPluginIds": list(policy.enabled_plugin_ids),
        "enabledToolsets": list(policy.enabled_toolsets),
        "enabledToolNames": list(policy.enabled_tool_names),
        "processIsolation": PROCESS_ISOLATION_MODE,
        "retrievalSessionId": retrieval_session_id,
    }
    if retrieval_session is not None:
        initial_packet: dict[str, Any] = {
            "candidates": list(retrieval_session.get("candidates") or [])[:8],
            "claimLedger": list(retrieval_session.get("claim_ledger") or [])[:24],
            "intentHint": retrieval_session.get("intent_hint"),
            "availableExpansions": list(
                retrieval_session.get("available_expansions") or []
            ),
        }
        latest_recap_change = retrieval_session.get("latest_recap_change")
        if isinstance(latest_recap_change, Mapping):
            latest_packet = dict(latest_recap_change)
            excerpt = latest_packet.pop("admitted_recap_excerpt", None)
            initial_packet["latestRecapChange"] = latest_packet
            if isinstance(excerpt, str) and excerpt.strip():
                initial_packet["admittedRecapExcerpt"] = excerpt.strip()
        payload["initialClaimPacket"] = initial_packet
    return (
        "Turn capability policy (runtime-enforced; also required on tool calls):\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _build_ephemeral_system_prompt(
    policy: HermesCapabilityPolicy,
    request: HermesGraphAgentTurnRequest,
    *,
    retrieval_session_packet: Mapping[str, Any] | None,
) -> str:
    if policy.mode == "conversation_only":
        parts = [_CONVERSATION_ONLY_SYSTEM_POLICY]
        if request.surface_context_block:
            parts.append(request.surface_context_block)
        return "\n\n".join(parts)
    scope_part = _scope_block(
        policy,
        retrieval_session_id=request.retrieval_session_id,
        retrieval_session=retrieval_session_packet,
    )
    parts = [_GRAPH_SYSTEM_POLICY, scope_part]
    if request.surface_context_block:
        parts.append(request.surface_context_block)
    return "\n\n".join(parts)


def _clip_str(value: Any, *, max_chars: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def _bounded_focus(focus: Any) -> dict[str, Any] | None:
    if not isinstance(focus, Mapping):
        return None
    bounded: dict[str, Any] = {}
    if "kind" in focus:
        kind = _clip_str(focus.get("kind"), max_chars=_MAX_FOCUS_KIND_CHARS)
        if kind is not None:
            bounded["kind"] = kind
    if "sessionId" in focus and focus.get("sessionId") is not None:
        session_id = _clip_str(
            focus.get("sessionId"),
            max_chars=_MAX_FOCUS_SESSION_ID_CHARS,
        )
        if session_id is not None:
            bounded["sessionId"] = session_id
    return bounded or None


def _safe_ids_from_args(args: Mapping[str, Any]) -> dict[str, Any]:
    """Bounded, non-prompt identifiers for tool-event telemetry."""
    bounded: dict[str, Any] = {}
    query_text = args.get("queryText")
    if isinstance(query_text, str):
        bounded["queryTextChars"] = len(query_text)
        bounded["queryTextSha25616"] = hashlib.sha256(
            query_text.encode("utf-8", errors="replace")
        ).hexdigest()[:16]
    for key in ("nodeId", "anchorId"):
        if key in args and args[key] is not None:
            clipped = _clip_str(args[key], max_chars=_MAX_BOUNDED_ID_CHARS)
            if clipped is not None:
                bounded[key] = clipped
    seed_ids = args.get("seedNodeIds")
    if isinstance(seed_ids, list):
        bounded["seedNodeIds"] = [
            clipped
            for item in seed_ids[:_MAX_BOUNDED_ID_LIST]
            if (clipped := _clip_str(item, max_chars=_MAX_BOUNDED_ID_CHARS)) is not None
        ]
        if len(seed_ids) > _MAX_BOUNDED_ID_LIST:
            bounded["seedNodeIdsTruncated"] = True
    for key in ("maxDepth", "maxChars"):
        if key in args and isinstance(args[key], (int, float)):
            bounded[key] = args[key]
    target = args.get("target")
    if isinstance(target, Mapping):
        bounded["target"] = {
            "kind": _clip_str(target.get("kind"), max_chars=_MAX_FOCUS_KIND_CHARS),
            "id": _clip_str(target.get("id"), max_chars=_MAX_BOUNDED_ID_CHARS),
        }
    return bounded


def _cap_id_list(values: list[str]) -> list[str]:
    if len(values) <= _MAX_MATCHED_IDS:
        return values
    return values[:_MAX_MATCHED_IDS]


def _summarize_tool_result(raw: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "retrieval_schema": None,
        "outcome": None,
        "matched_node_ids": [],
        "relationship_ids": [],
        "source_anchor_ids": [],
        "diagnostic_codes": [],
        "is_error": False,
    }
    if not isinstance(raw, str):
        return summary
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return summary
    if not isinstance(parsed, dict):
        return summary
    summary["retrieval_schema"] = parsed.get("schema")
    summary["outcome"] = parsed.get("outcome")
    matched = parsed.get("matchedNodeIds") or []
    if isinstance(matched, list):
        summary["matched_node_ids"] = _cap_id_list([str(x) for x in matched])
    relationships = parsed.get("relationships") or []
    if isinstance(relationships, list):
        ids: list[str] = []
        for rel in relationships:
            if not isinstance(rel, Mapping):
                continue
            edge_id = rel.get("edgeId")
            if edge_id is None:
                edge_id = rel.get("id")
            if edge_id is not None:
                ids.append(str(edge_id))
        summary["relationship_ids"] = _cap_id_list(ids)
    if parsed.get("anchorId"):
        summary["source_anchor_ids"] = [str(parsed["anchorId"])]
    else:
        anchors = parsed.get("sourceAnchors") or []
        if isinstance(anchors, list):
            summary["source_anchor_ids"] = _cap_id_list(
                [
                    str(a.get("anchorId") or a.get("id"))
                    for a in anchors
                    if isinstance(a, Mapping) and (a.get("anchorId") or a.get("id"))
                ]
            )
    diagnostics = parsed.get("diagnostics") or []
    if isinstance(diagnostics, list):
        summary["diagnostic_codes"] = [
            str(d.get("code"))
            for d in diagnostics
            if isinstance(d, Mapping) and d.get("code")
        ][:_MAX_MATCHED_IDS]
    if parsed.get("code") and not summary["outcome"]:
        summary["diagnostic_codes"] = list(
            dict.fromkeys([*summary["diagnostic_codes"], str(parsed["code"])])
        )
    schema = summary["retrieval_schema"]
    summary["is_error"] = bool(
        schema == RETRIEVAL_ERROR_SCHEMA
        or (
            parsed.get("code")
            and schema != RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA
            and summary["outcome"] is None
        )
    )
    return summary


def _tool_names_from_definitions(definitions: Sequence[Mapping[str, Any]]) -> list[str]:
    names: list[str] = []
    for item in definitions:
        function = item.get("function") if isinstance(item, Mapping) else None
        if not isinstance(function, Mapping):
            continue
        name = function.get("name")
        if isinstance(name, str) and name:
            names.append(name)
    return names


def _validate_model_visible_surface(
    visible_names: Sequence[str],
    policy: HermesCapabilityPolicy,
) -> str | None:
    """Ensure Hermes model-visible tools match the capability policy exactly."""
    visible = list(visible_names)
    if len(visible) != len(set(visible)):
        return "hermes_tool_surface_duplicate"
    expected = set(policy.enabled_tool_names)
    actual = set(visible)
    if actual != expected:
        return "hermes_tool_surface_mismatch"
    for name in visible:
        rule = policy.rule_for(name)
        if rule is None:
            return "hermes_tool_rule_missing"
        if not rule.allowed_effects:
            return "hermes_capability_policy_empty_effects"
    return None


def _safe_mode_enabled() -> bool:
    value = (os.environ.get("HERMES_SAFE_MODE") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _hermes_builtin_toolset_names() -> frozenset[str]:
    """Return statically defined Hermes built-in toolset names."""
    from toolsets import TOOLSETS

    return frozenset(TOOLSETS.keys())


def _reject_unsupported_builtin_toolsets(
    policy: HermesCapabilityPolicy,
) -> str | None:
    """Built-in Hermes toolsets are not rediscovered by plugin sweeps yet."""
    builtins = _hermes_builtin_toolset_names()
    if any(name in builtins for name in policy.enabled_toolsets):
        return "hermes_builtin_toolset_unsupported"
    return None


def _rediscoverable_plugin_toolsets(
    policy: HermesCapabilityPolicy,
) -> frozenset[str]:
    """Toolsets owned by activated plugins that this wrapper will rediscover."""
    builtins = _hermes_builtin_toolset_names()
    return frozenset(
        toolset
        for activation in policy.plugin_activations
        for toolset in activation.toolsets
        if toolset not in builtins
    )


def _purge_stale_rediscoverable_plugin_tools(
    registry: Any,
    policy: HermesCapabilityPolicy,
) -> None:
    """Remove stale registry entries only for plugin toolsets we will rediscover.

    Built-in Hermes toolsets are never purged here (and are rejected earlier).
    """
    rediscoverable = _rediscoverable_plugin_toolsets(policy)
    if not rediscoverable:
        return
    entries, _ = registry._snapshot_state()
    for entry in entries:
        if entry.toolset in rediscoverable:
            registry.deregister(entry.name)


def _find_loaded_plugin(manager: Any, plugin_id: str) -> Any | None:
    """Locate a loaded plugin by registry key or manifest name."""
    loaded = manager._plugins.get(plugin_id)
    if loaded is not None:
        return loaded
    for key, plugin in manager._plugins.items():
        manifest = getattr(plugin, "manifest", None)
        name = getattr(manifest, "name", None) if manifest is not None else None
        if key == plugin_id or name == plugin_id:
            return plugin
    return None


def _verify_enabled_plugin_discovery(
    hermes_plugins: Any,
    policy: HermesCapabilityPolicy,
) -> str | None:
    """Prove each activated plugin loaded, then check its attributed tools.

    Lookup uses :attr:`HermesPluginActivation.plugin_id`. Expected tools are
    the union of policy rules for that activation's toolsets — never a
    comparison of every policy tool against a single plugin.
    """
    if _safe_mode_enabled():
        return "hermes_plugin_discovery_skipped"

    manager = hermes_plugins.get_plugin_manager()
    builtins = _hermes_builtin_toolset_names()
    for activation in policy.plugin_activations:
        # Built-in toolsets are rejected earlier; skip any residual activation.
        if not any(toolset not in builtins for toolset in activation.toolsets):
            continue
        loaded = _find_loaded_plugin(manager, activation.plugin_id)
        if loaded is None:
            return "hermes_plugin_not_loaded"
        if not bool(getattr(loaded, "enabled", False)):
            return "hermes_plugin_disabled"
        if getattr(loaded, "error", None):
            return "hermes_plugin_load_error"
        expected = set(policy.expected_tool_names_for_plugin(activation.plugin_id))
        registered = set(getattr(loaded, "tools_registered", []) or [])
        if expected and not expected.issubset(registered):
            return "hermes_plugin_registration_incomplete"
    return None


def _pre_tool_call_policy_hook(
    policy: HermesCapabilityPolicy,
) -> Callable[..., Any]:
    """Hermes-wide pre-dispatch allowlist for every tool name.

    Effect metadata beyond nonempty ``allowed_effects`` is enforced in the
    graph plugin handlers for this rung (see ``HermesToolCapabilityRule``).
    """

    def _hook(
        tool_name: str,
        args: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> dict[str, str] | None:
        del args
        name = str(tool_name)
        if name not in policy.enabled_tool_names:
            return {
                "action": "block",
                "message": (
                    f"Tool {name!r} is not permitted by the active capability policy."
                ),
            }
        rule = policy.rule_for(name)
        if rule is None:
            return {
                "action": "block",
                "message": f"Tool {name!r} has no capability rule.",
            }
        if not rule.allowed_effects:
            return {
                "action": "block",
                "message": f"Tool {name!r} has no permitted effects.",
            }
        return None

    return _hook


class _ToolEventCollector:
    def __init__(self, policy: HermesCapabilityPolicy) -> None:
        self.events: list[HermesGraphToolEvent] = []
        self.forensic_events: list[dict[str, Any]] = []
        self._starts_by_call_id: dict[str, float] = {}
        self._scope = policy.graph_scope

    def _authoritative_scope_fields(self) -> dict[str, Any]:
        scope = self._scope
        if scope is None:
            return {
                "world_id": None,
                "campaign_id": None,
                "focus": None,
                "admissibility": None,
                "revision_pin": None,
            }
        return {
            "world_id": str(scope.world_id),
            "campaign_id": str(scope.campaign_id),
            "focus": _bounded_focus(scope.focus),
            "admissibility": str(scope.admissibility),
            "revision_pin": (
                None if scope.revision_pin is None else str(scope.revision_pin)
            ),
        }

    def on_start(
        self,
        tool_call_id: Any,
        tool_name: str,
        args: dict[str, Any] | None = None,
        *_unused: Any,
        **_kwargs: Any,
    ) -> None:
        del _unused
        started = time.perf_counter()
        call_key = (
            str(tool_call_id)
            if tool_call_id is not None
            else f"anon:{len(self.events)}:{tool_name}"
        )
        self._starts_by_call_id[call_key] = started
        args = args if isinstance(args, dict) else {}
        scope_fields = self._authoritative_scope_fields()
        call_id = (
            str(tool_call_id)
            if tool_call_id is not None
            else f"anon:{len(self.events)}"
        )
        self.events.append(
            HermesGraphToolEvent(
                tool_name=str(tool_name),
                state="start",
                world_id=scope_fields["world_id"],
                campaign_id=scope_fields["campaign_id"],
                focus=scope_fields["focus"],
                admissibility=scope_fields["admissibility"],
                revision_pin=scope_fields["revision_pin"],
                bounded_ids=_safe_ids_from_args(args),
            )
        )
        if forensic_enabled():
            self.forensic_events.append(
                build_tool_forensic_event(
                    call_id=call_id,
                    tool=str(tool_name),
                    state="start",
                )
            )

    def on_complete(
        self,
        tool_call_id: Any,
        tool_name: str,
        args: dict[str, Any] | None = None,
        result: Any = None,
        *_unused: Any,
        **_kwargs: Any,
    ) -> None:
        del _unused
        args = args if isinstance(args, dict) else {}
        call_key = str(tool_call_id) if tool_call_id is not None else None
        started = (
            self._starts_by_call_id.pop(call_key, None)
            if call_key is not None
            else None
        )
        duration_ms = (
            (time.perf_counter() - started) * 1000.0 if started is not None else None
        )
        summary = _summarize_tool_result(result)
        state: ToolEventState = "error" if summary["is_error"] else "completion"
        scope_fields = self._authoritative_scope_fields()
        self.events.append(
            HermesGraphToolEvent(
                tool_name=str(tool_name),
                state=state,
                duration_ms=duration_ms,
                world_id=scope_fields["world_id"],
                campaign_id=scope_fields["campaign_id"],
                focus=scope_fields["focus"],
                admissibility=scope_fields["admissibility"],
                revision_pin=scope_fields["revision_pin"],
                bounded_ids=_safe_ids_from_args(args),
                retrieval_schema=summary["retrieval_schema"],
                outcome=summary["outcome"],
                matched_node_ids=summary["matched_node_ids"],
                relationship_ids=summary["relationship_ids"],
                source_anchor_ids=summary["source_anchor_ids"],
                diagnostic_codes=summary["diagnostic_codes"],
            )
        )
        if forensic_enabled():
            self.forensic_events.append(
                build_tool_forensic_event(
                    call_id=call_key,
                    tool=str(tool_name),
                    state=state,
                    raw_result=result,
                    outcome=summary["outcome"],
                    result_schema=summary["retrieval_schema"],
                    diagnostic_codes=summary["diagnostic_codes"],
                )
            )


class _ApiObserverCollector:
    """Fail-open Hermes request-scoped API observer for exactly one turn."""

    def __init__(
        self,
        *,
        on_model_call: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self.model_calls: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self._pending: dict[str, dict[str, Any]] = {}
        self._runtime_api_mode: str | None = None
        self._on_model_call = on_model_call
        self._callbacks: dict[str, Callable[..., Any]] = {
            "pre_api_request": self.on_pre_api_request,
            "post_api_request": self.on_post_api_request,
            "api_request_error": self.on_api_request_error,
        }
        self._registered: list[tuple[Any, str, Callable[..., Any]]] = []

    def _note(self, warning: str) -> None:
        text = str(warning or "").strip()
        if text and text not in self.warnings:
            self.warnings.append(text)

    def _request_key(self, payload: Mapping[str, Any]) -> str:
        request_id = str(payload.get("api_request_id") or "").strip()
        if request_id:
            return request_id
        return f"anon:{len(self.model_calls)}:{len(self._pending)}"

    def _merge_pending(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        key = self._request_key(payload)
        merged = dict(self._pending.pop(key, {}))
        merged.update(dict(payload))
        return merged

    def _record(self, payload: Mapping[str, Any], *, status: str) -> None:
        call = map_hermes_observer_to_model_call(
            payload,
            status=status,  # type: ignore[arg-type]
            sequence=len(self.model_calls) + 1,
        )
        if call.get("api_mode") is None:
            call["api_mode"] = self._runtime_api_mode
        self.model_calls.append(call)
        if self._on_model_call is None:
            return
        try:
            self._on_model_call(call)
        except Exception:
            self._note("observer_telemetry_emit_failed")

    def capture_runtime_api_mode(self, agent: Any) -> None:
        """Use Hermes' resolved agent mode, never infer it from routing policy."""
        try:
            runtime_mode = getattr(agent, "api_mode", None)
        except Exception:
            return
        if not isinstance(runtime_mode, str):
            return
        runtime_mode = runtime_mode.strip()
        if runtime_mode:
            self._runtime_api_mode = runtime_mode[:_MAX_BOUNDED_ID_CHARS]

    def on_pre_api_request(self, **kwargs: Any) -> None:
        try:
            key = self._request_key(kwargs)
            self._pending[key] = dict(kwargs)
        except Exception:
            self._note("observer_payload_malformed")

    def on_post_api_request(self, **kwargs: Any) -> None:
        try:
            self._record(self._merge_pending(kwargs), status="ok")
        except Exception:
            self._note("observer_payload_malformed")

    def on_api_request_error(self, **kwargs: Any) -> None:
        try:
            self._record(self._merge_pending(kwargs), status="error")
        except Exception:
            self._note("observer_payload_malformed")

    def discard_pre_dispatch_veto(self, api_request_id: str) -> None:
        """Do not report an observed pre-hook as an inference call when vetoed."""
        key = str(api_request_id or "").strip()
        if key:
            self._pending.pop(key, None)

    def _flush_pending(self) -> None:
        for payload in self._pending.values():
            try:
                self._record(payload, status="error")
                self._note("observer_api_request_incomplete")
            except Exception:
                self._note("observer_payload_malformed")
        self._pending.clear()

    def finish(self) -> tuple[list[dict[str, Any]], list[str]]:
        self._flush_pending()
        return list(self.model_calls), list(self.warnings)

    def register(self, plugin_manager: Any) -> None:
        hooks = getattr(plugin_manager, "_hooks", None)
        if not isinstance(hooks, dict):
            self._note("observer_hooks_unavailable")
            return
        for name, callback in self._callbacks.items():
            hooks.setdefault(name, []).append(callback)
            self._registered.append((plugin_manager, name, callback))

    def unregister(self) -> None:
        for plugin_manager, name, callback in self._registered:
            hooks = getattr(plugin_manager, "_hooks", None)
            if not isinstance(hooks, dict):
                continue
            registered = hooks.get(name) or []
            try:
                registered.remove(callback)
            except ValueError:
                self._note("observer_hook_already_removed")
        self._registered.clear()
        self._flush_pending()


def _request_budget_guard(
    policy: Mapping[str, Any],
    *,
    on_provider_authorization: Callable[[Any], bool] | None = None,
    on_provider_lifecycle: Callable[[Mapping[str, Any]], bool] | None = None,
) -> Callable[[Any], bool]:
    """Build the strict local request-envelope guard for one resolved model."""
    expected_provider = str(policy["provider"])
    expected_model = str(policy["model"])
    expected_mode = str(policy["apiMode"])
    expected_estimator = str(policy["estimator"])
    context_limit = int(policy["contextLimitTokens"])
    output_reserve = int(policy["outputReserveTokens"])

    protocol_by_provider = {
        "openai-api": frozenset({"codex_responses", "chat_completions"}),
    }

    authorization_sequence = 0
    agent_ref: list[Any] = []

    def allow(view: Any) -> bool:
        nonlocal authorization_sequence
        if (
            view.provider != expected_provider
            or view.model != expected_model
            or view.api_mode != expected_mode
            or expected_mode not in protocol_by_provider.get(expected_provider, ())
            or expected_estimator != "utf8_json_bytes_plus_64_per_node_v1"
        ):
            return False
        try:
            payload = json.loads(view.payload_json)
        except (TypeError, ValueError):
            return False
        if not isinstance(payload, dict) or payload.get("model") != expected_model:
            return False
        def count_nodes(value: Any) -> int:
            if isinstance(value, dict):
                return 1 + sum(count_nodes(item) for item in value.values())
            if isinstance(value, list):
                return 1 + sum(count_nodes(item) for item in value)
            return 0

        def text_content(value: Any, *, allowed_types: frozenset[str]) -> bool:
            if isinstance(value, str):
                return True
            return isinstance(value, list) and all(
                isinstance(part, dict)
                and set(part) == {"type", "text"}
                and isinstance(part.get("type"), str)
                and part.get("type") in allowed_types
                and isinstance(part.get("text"), str)
                for part in value
            )

        def optional_string(item: Mapping[str, Any], key: str, *, nonempty: bool = False) -> bool:
            if key not in item:
                return True
            value = item[key]
            return isinstance(value, str) and (not nonempty or bool(value.strip()))

        def valid_tool_choice(value: Any, *, responses: bool) -> bool:
            if isinstance(value, str):
                return value in {"auto", "none", "required"}
            if not isinstance(value, dict):
                return False
            if responses:
                return (
                    set(value) == {"type", "name"}
                    and value.get("type") == "function"
                    and isinstance(value.get("name"), str)
                    and bool(value["name"].strip())
                )
            return (
                set(value) == {"type", "function"}
                and value.get("type") == "function"
                and isinstance(value.get("function"), dict)
                and set(value["function"]) == {"name"}
                and isinstance(value["function"].get("name"), str)
                and bool(value["function"]["name"].strip())
            )

        def valid_function_tool(tool: Any, *, responses: bool) -> bool:
            if not isinstance(tool, dict):
                return False
            if responses:
                return (
                    set(tool) <= {"type", "name", "description", "parameters", "strict"}
                    and tool.get("type") == "function"
                    and isinstance(tool.get("name"), str)
                    and isinstance(tool.get("parameters"), dict)
                    and ("description" not in tool or isinstance(tool["description"], str))
                    and ("strict" not in tool or isinstance(tool["strict"], bool))
                )
            if set(tool) != {"type", "function"} or tool.get("type") != "function":
                return False
            function = tool.get("function")
            return (
                isinstance(function, dict)
                and set(function) <= {"name", "description", "parameters", "strict"}
                and isinstance(function.get("name"), str)
                and isinstance(function.get("parameters"), dict)
                and ("description" not in function or isinstance(function["description"], str))
                and ("strict" not in function or isinstance(function["strict"], bool))
            )

        def valid_responses_input(inputs: Any) -> bool:
            if isinstance(inputs, str):
                return True
            if not isinstance(inputs, list):
                return False
            for item in inputs:
                if not isinstance(item, dict):
                    return False
                kind = item.get("type", "message")
                if kind == "message":
                    if set(item) - {"type", "role", "content", "status", "id", "phase"}:
                        return False
                    if not isinstance(item.get("role"), str) or item.get("role") not in {"system", "developer", "user", "assistant"}:
                        return False
                    if not text_content(item.get("content"), allowed_types=frozenset({"input_text", "output_text"})):
                        return False
                    if "status" in item and (
                        not isinstance(item["status"], str)
                        or item["status"] not in {"completed", "incomplete", "in_progress"}
                    ):
                        return False
                    if "id" in item and (
                        not isinstance(item["id"], str)
                        or not item["id"].strip()
                        or len(item["id"].strip()) > 64
                    ):
                        return False
                    if "phase" in item and (
                        not isinstance(item["phase"], str)
                        or item["phase"] not in {
                            "analysis",
                            "commentary",
                            "final_answer",
                            "final",
                        }
                    ):
                        return False
                elif kind == "function_call":
                    if set(item) - {"type", "call_id", "name", "arguments", "id", "status"}:
                        return False
                    if not all(
                        isinstance(item.get(key), str)
                        for key in ("call_id", "name", "arguments")
                    ) or not item["call_id"].strip() or not item["name"].strip():
                        return False
                    if "id" in item and (
                        not isinstance(item["id"], str)
                        or not item["id"].strip()
                        or len(item["id"].strip()) > 64
                    ):
                        return False
                    if "status" in item and (
                        not isinstance(item["status"], str)
                        or item["status"] not in {"in_progress", "completed"}
                    ):
                        return False
                elif kind == "function_call_output":
                    if set(item) - {"type", "call_id", "output"}:
                        return False
                    if (
                        not isinstance(item.get("call_id"), str)
                        or not item["call_id"].strip()
                        or not text_content(
                            item.get("output"),
                            allowed_types=frozenset({"input_text", "output_text"}),
                        )
                    ):
                        return False
                else:
                    return False
            return True

        def valid_chat_messages(messages: Any) -> bool:
            if not isinstance(messages, list):
                return False
            for item in messages:
                if not isinstance(item, dict):
                    return False
                role = item.get("role")
                if not isinstance(role, str):
                    return False
                if role in {"system", "developer", "user"}:
                    if set(item) - {"role", "content", "name"} or not text_content(
                        item.get("content"), allowed_types=frozenset({"text"})
                    ) or not optional_string(item, "name", nonempty=True):
                        return False
                elif role == "assistant":
                    if set(item) - {"role", "content", "name", "tool_calls", "refusal"}:
                        return False
                    if "content" in item and not text_content(
                        item["content"], allowed_types=frozenset({"text"})
                    ):
                        return False
                    if not optional_string(item, "name", nonempty=True) or not optional_string(item, "refusal"):
                        return False
                    calls = item.get("tool_calls", [])
                    if not isinstance(calls, list):
                        return False
                    for call in calls:
                        if (
                            not isinstance(call, dict)
                            or set(call) != {"id", "type", "function"}
                            or call.get("type") != "function"
                            or not isinstance(call.get("id"), str)
                            or not call["id"].strip()
                        ):
                            return False
                        function = call.get("function")
                        if (
                            not isinstance(function, dict)
                            or set(function) != {"name", "arguments"}
                            or not isinstance(function.get("name"), str)
                            or not function["name"].strip()
                            or not isinstance(function.get("arguments"), str)
                        ):
                            return False
                elif role == "tool":
                    if set(item) - {"role", "content", "tool_call_id"} or not isinstance(
                        item.get("tool_call_id"), str
                    ) or not item["tool_call_id"].strip() or not isinstance(item.get("content"), str):
                        return False
                else:
                    return False
            return True

        if expected_mode == "codex_responses":
            allowed_root = {
                "model", "input", "instructions", "tools", "tool_choice",
                "parallel_tool_calls", "max_output_tokens", "stream", "store",
                "include", "reasoning", "prompt_cache_key",
            }
            if set(payload) - allowed_root:
                return False
            inputs = payload.get("input")
            actual_output = payload.get("max_output_tokens")
            if not valid_responses_input(inputs):
                return False
            if "instructions" in payload and not isinstance(payload["instructions"], str):
                return False
            if "include" in payload and (
                not isinstance(payload["include"], list)
                or payload["include"] != []
            ):
                return False
            if "reasoning" in payload and (
                not isinstance(payload["reasoning"], dict)
                or set(payload["reasoning"]) - {"effort", "summary"}
                or (
                    "effort" in payload["reasoning"]
                    and (
                        not isinstance(payload["reasoning"]["effort"], str)
                        or payload["reasoning"]["effort"] not in {"minimal", "low", "medium", "high", "xhigh"}
                    )
                )
                or (
                    "summary" in payload["reasoning"]
                    and (
                        not isinstance(payload["reasoning"]["summary"], str)
                        or payload["reasoning"]["summary"] not in {"auto", "concise", "detailed"}
                    )
                )
            ):
                return False
            if payload.get("store", False) is not False:
                return False
            for key in ("stream", "parallel_tool_calls"):
                if key in payload and not isinstance(payload[key], bool):
                    return False
            if "prompt_cache_key" in payload and (
                not isinstance(payload["prompt_cache_key"], str)
                or not payload["prompt_cache_key"].strip()
            ):
                return False
            if "tool_choice" in payload and not valid_tool_choice(payload["tool_choice"], responses=True):
                return False
            tools = payload.get("tools", [])
            if not isinstance(tools, list) or not all(
                valid_function_tool(tool, responses=True) for tool in tools
            ):
                return False
        else:
            allowed_root = {
                "model", "messages", "tools", "tool_choice", "parallel_tool_calls",
                "max_tokens", "max_completion_tokens", "temperature", "top_p",
                "stop", "stream", "reasoning_effort", "seed",
            }
            if set(payload) - allowed_root:
                return False
            messages = payload.get("messages")
            if "max_completion_tokens" in payload and "max_tokens" in payload:
                return False
            actual_output = payload.get("max_completion_tokens", payload.get("max_tokens"))
            if not valid_chat_messages(messages):
                return False
            tools = payload.get("tools", [])
            if not isinstance(tools, list) or not all(
                valid_function_tool(tool, responses=False) for tool in tools
            ):
                return False
            if "tool_choice" in payload and not valid_tool_choice(payload["tool_choice"], responses=False):
                return False
        for key in ("stream", "parallel_tool_calls"):
            if key in payload and not isinstance(payload[key], bool):
                return False
        for key in ("temperature", "top_p"):
            if key in payload and (
                isinstance(payload[key], bool)
                or not isinstance(payload[key], (int, float))
                or not (0 <= payload[key] <= 2)
            ):
                return False
        if "reasoning_effort" in payload and (
            not isinstance(payload["reasoning_effort"], str)
            or payload["reasoning_effort"] not in {"minimal", "low", "medium", "high", "xhigh"}
        ):
            return False
        if "seed" in payload and (isinstance(payload["seed"], bool) or not isinstance(payload["seed"], int)):
            return False
        if "stop" in payload and not (
            isinstance(payload["stop"], str)
            or isinstance(payload["stop"], list) and all(isinstance(value, str) for value in payload["stop"])
        ):
            return False
        if count_nodes(payload) > 100_000:
            return False
        if (
            isinstance(actual_output, bool)
            or not isinstance(actual_output, int)
            or actual_output <= 0
            or actual_output > output_reserve
        ):
            return False
        # Full canonical request JSON includes instructions/input/messages and
        # tool schemas. Treat each UTF-8 byte as a conservative content-token
        # ceiling and reserve additional protocol framing per input/tool item.
        # This is explicitly an upper-bound guard, not an exact token count.
        input_upper_bound = view.payload_utf8_bytes + 64 * (1 + count_nodes(payload))
        if input_upper_bound + output_reserve > context_limit:
            return False
        if on_provider_authorization is None:
            return True
        try:
            authorized = on_provider_authorization(view) is True
        except Exception:
            return False
        if authorized:
            authorization_sequence += 1
            if agent_ref:
                agent_ref[0]._api_request_budget_authorization_sequence = authorization_sequence
        return authorized

    allow.bind_agent = agent_ref  # type: ignore[attr-defined]
    allow.provider_lifecycle = on_provider_lifecycle  # type: ignore[attr-defined]

    return allow


def run_hermes_graph_agent_turn(
    request: HermesGraphAgentTurnRequest,
    *,
    agent_factory: Any | None = None,
    on_model_call: Callable[[Mapping[str, Any]], None] | None = None,
    on_worker_phase: Callable[[Mapping[str, Any]], None] | None = None,
    on_provider_authorization: Callable[[Any], bool] | None = None,
    on_provider_lifecycle: Callable[[Mapping[str, Any]], bool] | None = None,
    on_parent_graph_operation: Callable[
        [str, Mapping[str, Any]], tuple[str, Mapping[str, Any] | None]
    ] | None = None,
) -> HermesGraphAgentTurnResult:
    """Run one lockdown Hermes graph-agent turn and return a typed result.

    Isolation mode is always :data:`PROCESS_ISOLATION_MODE` (process-exclusive).
    """
    session_id = (request.session_id or "").strip() or str(uuid.uuid4())
    phase_group_id = uuid.uuid4().hex
    phase_sequence = 0

    @contextmanager
    def timed_worker_phase(name: str) -> Iterator[Callable[[], None]]:
        nonlocal phase_sequence
        started_mono = time.monotonic()
        phase_sequence += 1
        sequence = phase_sequence
        status = "error"

        def mark_success() -> None:
            nonlocal status
            status = "ok"

        try:
            yield mark_success
        finally:
            if on_worker_phase is not None and sequence <= 8:
                duration_ms = max(0, round((time.monotonic() - started_mono) * 1000))
                completed_at = datetime.now(UTC)
                span = {
                    "span_id": f"{phase_group_id}:{sequence}",
                    "parent_span_id": None,
                    "kind": "phase",
                    "name": name,
                    "status": status,
                    "started_at": datetime.fromtimestamp(
                        completed_at.timestamp() - duration_ms / 1000, UTC
                    ).isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "duration_ms": duration_ms,
                    "attributes": {"host_phase_group_id": phase_group_id},
                }
                try:
                    on_worker_phase(span)
                except Exception:
                    # Timing is observational and never changes the turn result.
                    pass

    if not str(request.question or "").strip():
        return _error_result(
            hermes_session_id=session_id,
            error_code="invalid_request",
            error_message="Hermes graph-agent turn requires a non-empty question.",
        )
    if (
        request.provider_authorization_required
        and (request.request_budget is None or on_provider_authorization is None)
    ):
        return _error_result(
            hermes_session_id=session_id,
            error_code="request_budget_guard_invalid",
            error_message="This turn requires a parent authorization and valid request budget.",
        )
    if request.parent_graph_broker_required and (
        on_parent_graph_operation is None or not request.provider_authorization_required
    ):
        return _error_result(
            hermes_session_id=session_id,
            error_code="parent_graph_broker_unavailable",
            error_message="This turn requires a parent Graph-operation broker.",
        )
    try:
        policy = _resolve_capability_policy(request)
    except ValueError:
        return _error_result(
            hermes_session_id=session_id,
            error_code="invalid_request",
            error_message="Hermes turn requires a valid graph scope or explicit conversation-only policy.",
        )
    if policy.mode == "conversation_only":
        if (
            request.world_id is not None
            or request.campaign_id is not None
            or request.scope_mode is not None
            or request.focus is not None
            or request.admissibility is not None
            or request.revision_pin is not None
            or request.retrieval_session_id is not None
            or request.retrieval_session is not None
        ):
            return _error_result(
                hermes_session_id=session_id,
                error_code="invalid_request",
                error_message="Conversation-only turns cannot carry graph scope or retrieval.",
            )
    elif (
        policy.mode != "graph"
        or not str(request.world_id or "").strip()
        or request.scope_mode not in {"campaign", "world"}
        or (
            request.scope_mode == "campaign"
            and not str(request.campaign_id or "").strip()
        )
    ):
        return _error_result(
            hermes_session_id=session_id,
            error_code="invalid_request",
            error_message="Graph turns require valid worldId, campaignId and scopeMode.",
        )
    structure_error = validate_capability_policy_structure(policy)
    if structure_error is not None:
        return _error_result(
            hermes_session_id=session_id,
            error_code=structure_error,
            error_message="Hermes capability policy failed structural validation.",
        )

    inference = _resolve_hermes_openai_inference(
        # Injected factories are unit-test doubles; production path requires a key.
        require_api_key=agent_factory is None,
    )
    if isinstance(inference, str):
        return _error_result(
            hermes_session_id=session_id,
            error_code=inference,
            error_message=(
                "Hermes graph turns require OPENAI_API_KEY (DungeonBuddy product "
                "path). Ambient Anthropic/OpenRouter Hermes CLI config is not used."
            ),
        )
    provider, model, base_url = inference

    retrieval_session_packet: dict[str, Any] | None = None
    if request.retrieval_session is not None:
        retrieval_session_packet = dict(request.retrieval_session)
        if (
            request.retrieval_session_id
            and "retrieval_session_id" not in retrieval_session_packet
        ):
            retrieval_session_packet["retrieval_session_id"] = (
                request.retrieval_session_id
            )
        if request.parent_graph_broker_required:
            if retrieval_session_packet.get("retrieval_session_id") != request.retrieval_session_id:
                return _error_result(
                    hermes_session_id=session_id,
                    error_code="retrieval_session_hydrate_error",
                    error_message="Parent Graph session identity is invalid.",
                )
        else:
            try:
                hydrate_session_from_packet(retrieval_session_packet)
            except Exception:
                return _error_result(
                    hermes_session_id=session_id,
                    error_code="retrieval_session_hydrate_error",
                    error_message="Hermes could not hydrate the shared retrieval session.",
                )

    with _RUNTIME_LOCK:
        # Persistent native profiles belong to saved Plan work only. Other
        # surfaces keep their existing per-turn Hermes home behavior.
        profiles_root_raw = os.environ.get(_SESSION_PROFILES_ENV)
        test_only_ephemeral_profile = (
            agent_factory is not None and not profiles_root_raw
        )
        # This is a typed server decision carried over runtime IPC. Rendered
        # surface prose is descriptive and never grants persistence.
        plan_continuity_turn = request.plan_continuity_turn
        if (
            plan_continuity_turn
            and not profiles_root_raw
            and not test_only_ephemeral_profile
        ):
            return _error_result(
                hermes_session_id=session_id,
                error_code="hermes_continuity_unavailable",
                error_message="The isolated Hermes conversation profile is unavailable.",
            )

        persistent_profile = plan_continuity_turn and not test_only_ephemeral_profile
        profile_created_for_new_session = False
        profile_turn_persisted = False
        session_db: Any | None = None
        hermes_state: Any | None = None
        previous_default_db_path: Any = None
        restored_history: list[dict[str, Any]] | None = None
        if persistent_profile:
            profiles_root = Path(str(profiles_root_raw)).expanduser().resolve()
            profile_home = (
                profiles_root / hashlib.sha256(session_id.encode("utf-8")).hexdigest()
            )
            state_db_path = profile_home / "state.db"
            continuing_session = bool(request.session_id and request.session_id.strip())
            try:
                if profile_home.is_symlink():
                    raise ValueError("Hermes profile path is a symbolic link")
                if continuing_session:
                    hermes_state, restored_history = _load_native_hermes_history(
                        session_id=session_id,
                        state_db_path=state_db_path,
                    )
                    if hermes_state is None or restored_history is None:
                        return _error_result(
                            hermes_session_id=session_id,
                            error_code="hermes_continuity_unavailable",
                            error_message=(
                                "Saved conversation continuity is unavailable. "
                                "Start a new conversation."
                            ),
                        )
                else:
                    profiles_root.mkdir(parents=True, exist_ok=True)
                    if profile_home.exists():
                        raise ValueError("New Hermes session profile already exists")
                    profile_home.mkdir()
                    profile_created_for_new_session = True
                    with hermes_import_namespace():
                        hermes_state = importlib.import_module("hermes_state")
                if hermes_state is None:
                    with hermes_import_namespace():
                        hermes_state = importlib.import_module("hermes_state")
                resolved_root = profiles_root.resolve()
                if profile_home.resolve().parent != resolved_root:
                    raise ValueError("Hermes profile escaped its isolated root")
                _prepare_isolated_hermes_home(
                    profile_home,
                    enabled_plugin_ids=policy.enabled_plugin_ids,
                    model=model,
                    provider=provider,
                    base_url=base_url,
                )
                previous_default_db_path = hermes_state.DEFAULT_DB_PATH
                hermes_state.DEFAULT_DB_PATH = state_db_path
                session_db = hermes_state.SessionDB(
                    db_path=state_db_path,
                    read_only=False,
                )
            except Exception:
                if session_db is not None:
                    try:
                        session_db.close()
                    except Exception:
                        pass
                if hermes_state is not None and previous_default_db_path is not None:
                    hermes_state.DEFAULT_DB_PATH = previous_default_db_path
                if profile_created_for_new_session:
                    try:
                        _remove_unbound_hermes_profile(profile_home, profiles_root)
                    except Exception:
                        pass
                return _error_result(
                    hermes_session_id=session_id,
                    error_code="hermes_continuity_unavailable",
                    error_message=(
                        "Saved conversation continuity is unavailable. "
                        "Start a new conversation."
                    ),
                )
            hermes_home = profile_home
        else:
            hermes_home = Path(tempfile.mkdtemp(prefix="dmb-hermes-graph-home-"))

        # Capture and mutate process-global env only while holding the lock so
        # concurrent turns cannot restore a sibling's profile or DB path.
        previous_home = os.environ.get("HERMES_HOME")
        root_token = set_graph_root_override(request.root)
        policy_token = set_active_capability_policy(policy)
        session_token = set_active_retrieval_session_id(request.retrieval_session_id)
        parent_broker_token = set_parent_graph_broker(
            on_parent_graph_operation,
            required=request.parent_graph_broker_required,
        )
        collector = _ToolEventCollector(policy)
        api_observer = _ApiObserverCollector(on_model_call=on_model_call)
        pre_tool_hook: Callable[..., Any] | None = None
        plugin_manager: Any | None = None
        whitelist_installed = False

        def observed_error(**kwargs: Any) -> HermesGraphAgentTurnResult:
            calls, warnings = api_observer.finish()
            kwargs.setdefault("model_calls", calls)
            kwargs.setdefault("telemetry_warnings", warnings)
            return _error_result(**kwargs)

        try:
            with timed_worker_phase(
                "rung3_bootstrap_logger_home_setup"
            ) as home_setup_succeeded:
                try:
                    _initialize_worker_logger_home()
                except Exception:
                    return observed_error(
                        hermes_session_id=session_id,
                        error_code="hermes_import_error",
                        error_message=(
                            "Hermes AIAgent could not be imported from the locked environment."
                        ),
                    )
                if not persistent_profile:
                    _prepare_isolated_hermes_home(
                        hermes_home,
                        enabled_plugin_ids=policy.enabled_plugin_ids,
                        model=model,
                        provider=provider,
                        base_url=base_url,
                    )
                os.environ["HERMES_HOME"] = str(hermes_home)
                home_setup_succeeded()

            factory = agent_factory
            if factory is None:
                try:
                    with timed_worker_phase(
                        "rung3_cached_agent_factory_lookup"
                    ) as lookup_succeeded:
                        with hermes_import_namespace():
                            module = importlib.import_module("run_agent")
                            factory = module.AIAgent
                        lookup_succeeded()
                except Exception:
                    return observed_error(
                        hermes_session_id=session_id,
                        error_code="hermes_import_error",
                        error_message=(
                            "Hermes AIAgent could not be imported from the locked environment."
                        ),
                    )

            try:
                with hermes_import_namespace():
                    from hermes_cli import plugins as hermes_plugins
                    from model_tools import get_tool_definitions
                    from tools.registry import registry

                    builtin_error = _reject_unsupported_builtin_toolsets(policy)
                    if builtin_error is not None:
                        return observed_error(
                            hermes_session_id=session_id,
                            error_code=builtin_error,
                            error_message=(
                                "Capability policy enables a Hermes built-in "
                                "toolset that this wrapper does not rediscover; "
                                "refuse rather than silently deregister "
                                "built-in tools."
                            ),
                        )

                    with timed_worker_phase(
                        "rung3_plugin_discovery"
                    ) as discovery_succeeded:
                        # Drop stale entries only for plugin toolsets we rediscover.
                        _purge_stale_rediscoverable_plugin_tools(registry, policy)

                        hermes_plugins.discover_plugins(force=True)

                        discovery_error = _verify_enabled_plugin_discovery(
                            hermes_plugins,
                            policy,
                        )
                        if discovery_error is not None:
                            return observed_error(
                                hermes_session_id=session_id,
                                error_code=discovery_error,
                                error_message=(
                                    "One or more enabled plugin toolsets were not "
                                    "successfully loaded during the current discovery sweep."
                                ),
                            )

                        visible_defs = get_tool_definitions(
                            enabled_toolsets=list(policy.enabled_toolsets),
                            quiet_mode=True,
                        )
                        if request.parent_graph_broker_required:
                            visible_defs = [
                                definition
                                for definition in visible_defs
                                if (
                                    names := _tool_names_from_definitions([definition])
                                )
                                and set(names).issubset(policy.enabled_tool_names)
                            ]
                        visible_names = _tool_names_from_definitions(visible_defs)
                        surface_error = _validate_model_visible_surface(
                            visible_names,
                            policy,
                        )
                        if surface_error is not None:
                            return observed_error(
                                hermes_session_id=session_id,
                                error_code=surface_error,
                                error_message=(
                                    "Hermes model-visible tool surface does not match "
                                    "the capability policy."
                                ),
                            )
                        discovery_succeeded()

                    hermes_plugins.set_thread_tool_whitelist(
                        set(policy.enabled_tool_names),
                        deny_msg_fmt=(
                            "Tool '{tool_name}' denied: not in capability policy whitelist"
                        ),
                    )
                    whitelist_installed = True
                    pre_tool_hook = _pre_tool_call_policy_hook(policy)
                    plugin_manager = hermes_plugins.get_plugin_manager()
                    plugin_manager._hooks.setdefault("pre_tool_call", []).append(
                        pre_tool_hook
                    )
                    api_observer.register(plugin_manager)

                    with timed_worker_phase(
                        "rung3_agent_construction"
                    ) as agent_construction_succeeded:
                        agent = factory(
                            quiet_mode=True,
                            skip_memory=True,
                            skip_context_files=True,
                            enabled_toolsets=list(policy.enabled_toolsets),
                            session_id=session_id,
                            provider=provider,
                            model=model,
                            base_url=base_url,
                            **(
                                {"max_tokens": request.request_budget["outputReserveTokens"]}
                                if request.request_budget is not None
                                else {}
                            ),
                            **(
                                {"session_db": session_db}
                                if session_db is not None
                                else {}
                            ),
                            tool_start_callback=collector.on_start,
                            tool_complete_callback=collector.on_complete,
                            ephemeral_system_prompt=_build_ephemeral_system_prompt(
                                policy,
                                request,
                                retrieval_session_packet=retrieval_session_packet,
                            ),
                        )
                        if request.request_budget is not None:
                            agent.api_request_budget_guard = _request_budget_guard(
                                request.request_budget,
                                on_provider_authorization=(
                                    (
                                        on_provider_authorization
                                        or (lambda _view: False)
                                    )
                                    if request.provider_authorization_required
                                    else (lambda _view: True)
                                ),
                                on_provider_lifecycle=(
                                    on_provider_lifecycle
                                    if request.provider_authorization_required
                                    else None
                                ),
                            )
                            agent.api_request_budget_guard.bind_agent.append(agent)
                            lifecycle_callback = agent.api_request_budget_guard.provider_lifecycle
                            agent.api_provider_lifecycle_callback = (
                                lambda transition: lifecycle_callback({
                                    "authorizationSequence": getattr(
                                        agent,
                                        "_api_request_budget_authorization_sequence",
                                        0,
                                    ),
                                    "transition": transition,
                                }) is True
                                if lifecycle_callback is not None
                                else None
                            )
                        api_observer.capture_runtime_api_mode(agent)

                        agent_tools = getattr(agent, "tools", None)
                        if isinstance(agent_tools, list):
                            if request.parent_graph_broker_required:
                                agent_tools = [
                                    definition
                                    for definition in agent_tools
                                    if (
                                        names := _tool_names_from_definitions([definition])
                                    )
                                    and set(names).issubset(policy.enabled_tool_names)
                                ]
                                agent.tools = agent_tools
                            agent_visible = _tool_names_from_definitions(agent_tools)
                            agent_surface_error = _validate_model_visible_surface(
                                agent_visible,
                                policy,
                            )
                            if agent_surface_error is not None:
                                return observed_error(
                                    hermes_session_id=session_id,
                                    error_code=agent_surface_error,
                                    error_message=(
                                        "AIAgent model-visible tools do not match the "
                                        "capability policy."
                                    ),
                                )
                        agent_construction_succeeded()

                    history = (
                        restored_history
                        if persistent_profile and request.session_id
                        else (
                            None
                            if persistent_profile
                            else (
                                [dict(item) for item in request.conversation_history]
                                if request.conversation_history
                                else None
                            )
                        )
                    )
                    try:
                        with timed_worker_phase(
                            "rung3_provider_conversation"
                        ) as provider_conversation_succeeded:
                            raw = agent.run_conversation(
                                user_message=str(request.question).strip(),
                                conversation_history=history,
                            )
                            provider_conversation_succeeded()
                    except Exception:
                        return observed_error(
                            hermes_session_id=session_id,
                            error_code="hermes_turn_error",
                            error_message="Hermes graph-agent turn failed.",
                            tool_events=collector.events,
                        )
            except Exception:
                return observed_error(
                    hermes_session_id=session_id,
                    error_code="hermes_agent_init_error",
                    error_message="Hermes graph-agent construction failed.",
                    tool_events=collector.events,
                )

            with timed_worker_phase(
                "rung3_response_normalization_projection"
            ) as response_normalization_succeeded:
                if not isinstance(raw, Mapping):
                    return observed_error(
                        hermes_session_id=session_id,
                        error_code="hermes_malformed_response",
                        error_message="Hermes returned a malformed turn response.",
                        tool_events=collector.events,
                    )

                messages = raw.get("messages")
                if messages is None:
                    messages = []
                if not isinstance(messages, list):
                    return observed_error(
                        hermes_session_id=session_id,
                        error_code="hermes_malformed_response",
                        error_message="Hermes returned a malformed messages payload.",
                        tool_events=collector.events,
                    )

                request_budget_failure_codes = {
                    "request_budget_exceeded",
                    "request_budget_guard_invalid",
                    "request_budget_guard_error",
                    "provider_lifecycle_unavailable",
                }
                if raw.get("failure_reason") == "request_budget_veto" and raw.get(
                    "failure_code"
                ) in request_budget_failure_codes:
                    request_id = raw.get("api_request_id")
                    api_observer.discard_pre_dispatch_veto(
                        request_id if isinstance(request_id, str) else ""
                    )
                    failure_code = str(raw["failure_code"])
                    prior_calls, prior_warnings = api_observer.finish()
                    prior_attempts = bool(prior_calls)
                    return _error_result(
                        hermes_session_id=session_id,
                        error_code=failure_code,
                        error_message=(
                            "The current provider request was denied before dispatch by "
                            "the local request-budget guard."
                            if not prior_attempts
                            else "The current provider request was denied before dispatch; "
                            "one or more earlier provider attempts occurred."
                        ),
                        messages=[dict(item) for item in messages if isinstance(item, Mapping)],
                        tool_events=collector.events,
                        model_calls=prior_calls,
                        telemetry_warnings=prior_warnings,
                    )

                final_response = raw.get("final_response")
                if final_response is not None and not isinstance(final_response, str):
                    final_response = str(final_response)
                returned_session_id = str(raw.get("session_id") or session_id)
                if persistent_profile and returned_session_id != session_id:
                    return observed_error(
                        hermes_session_id=session_id,
                        error_code="hermes_continuity_unavailable",
                        error_message=(
                            "Hermes changed the isolated conversation identity. "
                            "Start a new conversation."
                        ),
                        tool_events=collector.events,
                    )
                if persistent_profile and not _persisted_turn_matches(
                    session_db,
                    session_id=session_id,
                    question=str(request.question).strip(),
                    final_response=final_response,
                ):
                    return observed_error(
                        hermes_session_id=session_id,
                        error_code="hermes_continuity_unavailable",
                        error_message=(
                            "Hermes did not persist this turn to its isolated conversation. "
                            "Start a new conversation."
                        ),
                        tool_events=collector.events,
                    )
                parent_packet = get_parent_retrieval_session_packet()
                hydrated = (
                    get_session(request.retrieval_session_id)
                    if request.retrieval_session_id
                    and not request.parent_graph_broker_required
                    else None
                )
                model_calls, telemetry_warnings = api_observer.finish()
                if persistent_profile:
                    profile_turn_persisted = True
                result = HermesGraphAgentTurnResult(
                    status="ok",
                    final_response=final_response,
                    messages=[
                        dict(m) if isinstance(m, Mapping) else {"value": m}
                        for m in messages
                    ],
                    hermes_session_id=returned_session_id,
                    tool_events=list(collector.events),
                    process_isolation=PROCESS_ISOLATION_MODE,
                    retrieval_session_id=request.retrieval_session_id,
                    retrieval_session=(
                        dict(parent_packet)
                        if isinstance(parent_packet, Mapping)
                        else hydrated.project_for_hermes()
                        if hydrated is not None
                        else retrieval_session_packet
                    ),
                    answer_scope=_derive_answer_scope(collector.events),
                    model_calls=model_calls,
                    telemetry_warnings=telemetry_warnings,
                )
                response_normalization_succeeded()
                return result
        except Exception:
            return observed_error(
                hermes_session_id=session_id,
                error_code="hermes_graph_agent_error",
                error_message="Hermes graph-agent runtime failed unexpectedly.",
                tool_events=collector.events,
            )
        finally:
            api_observer.unregister()
            reset_active_retrieval_session_id(session_token)
            reset_parent_graph_broker(parent_broker_token)
            if plugin_manager is not None and pre_tool_hook is not None:
                hooks = plugin_manager._hooks.get("pre_tool_call") or []
                try:
                    hooks.remove(pre_tool_hook)
                except ValueError:
                    pass
            if whitelist_installed:
                try:
                    with hermes_import_namespace():
                        from hermes_cli import plugins as hermes_plugins

                        hermes_plugins.clear_thread_tool_whitelist()
                except Exception:
                    pass
            reset_active_capability_policy(policy_token)
            reset_graph_root_override(root_token)
            if previous_home is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = previous_home
            if session_db is not None:
                try:
                    session_db.close()
                except Exception:
                    pass
            if hermes_state is not None and previous_default_db_path is not None:
                hermes_state.DEFAULT_DB_PATH = previous_default_db_path
            if (
                persistent_profile
                and profile_created_for_new_session
                and not profile_turn_persisted
            ):
                try:
                    _remove_unbound_hermes_profile(profile_home, profiles_root)
                except Exception:
                    pass
            elif not persistent_profile:
                shutil.rmtree(hermes_home, ignore_errors=True)


__all__ = [
    "PROCESS_ISOLATION_MODE",
    "HermesCapabilityPolicy",
    "HermesGraphAgentTurnRequest",
    "HermesGraphAgentTurnResult",
    "HermesGraphScope",
    "HermesGraphToolEvent",
    "HermesPluginActivation",
    "HermesToolCapabilityRule",
    "ProcessIsolationMode",
    "ToolEventState",
    "deserialize_capability_policy",
    "deserialize_hermes_graph_agent_turn_request",
    "deserialize_hermes_graph_agent_turn_result",
    "hermes_import_namespace",
    "import_hermes_aiagent",
    "run_hermes_graph_agent_turn",
    "serialize_capability_policy",
    "serialize_hermes_graph_agent_turn_request",
    "serialize_hermes_graph_agent_turn_result",
]
