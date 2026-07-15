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
* sets process-wide ``HERMES_HOME`` to an isolated temp profile.

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
from pathlib import Path
from typing import Any, Literal

import yaml

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
    HermesCapabilityPolicy,
    HermesGraphScope,
    HermesPluginActivation,
    HermesToolCapabilityRule,
    default_graph_only_capability_policy,
    reset_active_capability_policy,
    reset_active_retrieval_session_id,
    reset_graph_root_override,
    set_active_capability_policy,
    set_active_retrieval_session_id,
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

_MAX_FOCUS_KIND_CHARS = 64
_MAX_FOCUS_SESSION_ID_CHARS = 128
_MAX_BOUNDED_ID_CHARS = 256
_MAX_BOUNDED_ID_LIST = 32
_MAX_MATCHED_IDS = 64

_GRAPH_SYSTEM_POLICY = """\
You are a campaign-prep assistant for DungeonMindBuddy.

Factual retrieval rules:
- A shared GraphRetrievalSession is already opened for this turn with deterministic
  candidates and accepted graph claims. Prefer those claims; expand only when needed.
- Use expand_graph_retrieval for object/neighborhood/compare/path/timeline/support/coverage.
- Use read_graph_source only for quotation, exact detail, conflict checks, or when
  claim policy requires source verification. Accepted graph claims may be stated as
  graph-grounded facts without a source read.
- Always pass the retrievalSessionId supplied for this turn. Scope/revision are
  server-enforced.
- If coverage is partial or anchors are unreadable, answer with the known graph
  facts and name the gap. Do not invent lore and do not search Markdown/corpus.
- For a latest-recap change question, use the server-provided latest-recap
  comparison context. Name the admitted recap and comparison boundary, disclose
  memory lag when the recap is not in the graph head, and distinguish no-change
  from unknown or retrieval failure. The context is metadata, not recap prose.
- Prior conversation messages resolve intent and pronouns only. They are not
  campaign truth.

Forbidden:
- Manifest, corpus, Markdown, lexical, filesystem, web, terminal, continuity,
  ambient-memory, or any non-graph factual discovery path.
"""


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


def _error_result(
    *,
    hermes_session_id: str,
    error_code: str,
    error_message: str,
    messages: list[dict[str, Any]] | None = None,
    tool_events: list[HermesGraphToolEvent] | None = None,
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
    )


def _resolve_capability_policy(
    request: HermesGraphAgentTurnRequest,
) -> HermesCapabilityPolicy:
    if request.capability_policy is not None:
        return request.capability_policy
    focus = (
        dict(request.focus)
        if request.focus is not None
        else {"kind": "none", "sessionId": None}
    )
    admissibility = request.admissibility if request.admissibility is not None else "gm"
    scope = HermesGraphScope(
        world_id=str(request.world_id).strip(),
        campaign_id=str(request.campaign_id).strip(),
        focus=focus,
        admissibility=str(admissibility),
        revision_pin=request.revision_pin,
    )
    return default_graph_only_capability_policy(scope)


def _prepare_isolated_hermes_home(
    home: Path,
    *,
    enabled_plugin_ids: Sequence[str],
) -> None:
    home.mkdir(parents=True, exist_ok=True)
    config_path = home / "config.yaml"
    config = {
        "plugins": {
            "enabled": list(enabled_plugin_ids),
            "disabled": [],
        }
    }
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )


def _scope_block(
    policy: HermesCapabilityPolicy,
    *,
    retrieval_session_id: str | None = None,
    retrieval_session: Mapping[str, Any] | None = None,
) -> str:
    scope = policy.graph_scope
    payload: dict[str, Any] = {
        "worldId": scope.world_id,
        "campaignId": scope.campaign_id,
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
            initial_packet["latestRecapChange"] = dict(latest_recap_change)
        payload["initialClaimPacket"] = initial_packet
    return (
        "Turn capability policy (runtime-enforced; also required on tool calls):\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


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
            str(tool_call_id) if tool_call_id is not None else f"anon:{len(self.events)}"
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
            self._starts_by_call_id.pop(call_key, None) if call_key is not None else None
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


def run_hermes_graph_agent_turn(
    request: HermesGraphAgentTurnRequest,
    *,
    agent_factory: Any | None = None,
) -> HermesGraphAgentTurnResult:
    """Run one lockdown Hermes graph-agent turn and return a typed result.

    Isolation mode is always :data:`PROCESS_ISOLATION_MODE` (process-exclusive).
    """
    session_id = (request.session_id or "").strip() or str(uuid.uuid4())

    if not str(request.question or "").strip():
        return _error_result(
            hermes_session_id=session_id,
            error_code="invalid_request",
            error_message="Hermes graph-agent turn requires a non-empty question.",
        )
    if not str(request.world_id or "").strip() or not str(request.campaign_id or "").strip():
        return _error_result(
            hermes_session_id=session_id,
            error_code="invalid_request",
            error_message="Hermes graph-agent turn requires worldId and campaignId.",
        )

    policy = _resolve_capability_policy(request)
    structure_error = validate_capability_policy_structure(policy)
    if structure_error is not None:
        return _error_result(
            hermes_session_id=session_id,
            error_code=structure_error,
            error_message="Hermes capability policy failed structural validation.",
        )

    retrieval_session_packet: dict[str, Any] | None = None
    if request.retrieval_session is not None:
        retrieval_session_packet = dict(request.retrieval_session)
        if request.retrieval_session_id and "retrieval_session_id" not in retrieval_session_packet:
            retrieval_session_packet["retrieval_session_id"] = request.retrieval_session_id
        try:
            hydrate_session_from_packet(retrieval_session_packet)
        except Exception:
            return _error_result(
                hermes_session_id=session_id,
                error_code="retrieval_session_hydrate_error",
                error_message="Hermes could not hydrate the shared retrieval session.",
            )

    with _RUNTIME_LOCK:
        # Capture and mutate process-global env only while holding the lock so
        # concurrent turns cannot restore a sibling's deleted temp home.
        hermes_home = Path(tempfile.mkdtemp(prefix="dmb-hermes-graph-home-"))
        previous_home = os.environ.get("HERMES_HOME")
        root_token = set_graph_root_override(request.root)
        policy_token = set_active_capability_policy(policy)
        session_token = set_active_retrieval_session_id(request.retrieval_session_id)
        collector = _ToolEventCollector(policy)
        pre_tool_hook: Callable[..., Any] | None = None
        plugin_manager: Any | None = None
        whitelist_installed = False
        try:
            _prepare_isolated_hermes_home(
                hermes_home,
                enabled_plugin_ids=policy.enabled_plugin_ids,
            )
            os.environ["HERMES_HOME"] = str(hermes_home)

            factory = agent_factory
            if factory is None:
                try:
                    with hermes_import_namespace():
                        module = importlib.import_module("run_agent")
                        factory = module.AIAgent
                except Exception:
                    return _error_result(
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
                        return _error_result(
                            hermes_session_id=session_id,
                            error_code=builtin_error,
                            error_message=(
                                "Capability policy enables a Hermes built-in "
                                "toolset that this wrapper does not rediscover; "
                                "refuse rather than silently deregister "
                                "built-in tools."
                            ),
                        )

                    # Drop stale entries only for plugin toolsets we rediscover.
                    _purge_stale_rediscoverable_plugin_tools(registry, policy)

                    hermes_plugins.discover_plugins(force=True)

                    discovery_error = _verify_enabled_plugin_discovery(
                        hermes_plugins,
                        policy,
                    )
                    if discovery_error is not None:
                        return _error_result(
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
                    visible_names = _tool_names_from_definitions(visible_defs)
                    surface_error = _validate_model_visible_surface(
                        visible_names,
                        policy,
                    )
                    if surface_error is not None:
                        return _error_result(
                            hermes_session_id=session_id,
                            error_code=surface_error,
                            error_message=(
                                "Hermes model-visible tool surface does not match "
                                "the capability policy."
                            ),
                        )

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

                    agent = factory(
                        quiet_mode=True,
                        skip_memory=True,
                        skip_context_files=True,
                        enabled_toolsets=list(policy.enabled_toolsets),
                        session_id=session_id,
                        tool_start_callback=collector.on_start,
                        tool_complete_callback=collector.on_complete,
                        ephemeral_system_prompt=(
                            f"{_GRAPH_SYSTEM_POLICY}\n\n"
                            f"{_scope_block(policy, retrieval_session_id=request.retrieval_session_id, retrieval_session=retrieval_session_packet)}"
                        ),
                    )

                    agent_tools = getattr(agent, "tools", None)
                    if isinstance(agent_tools, list):
                        agent_visible = _tool_names_from_definitions(agent_tools)
                        agent_surface_error = _validate_model_visible_surface(
                            agent_visible,
                            policy,
                        )
                        if agent_surface_error is not None:
                            return _error_result(
                                hermes_session_id=session_id,
                                error_code=agent_surface_error,
                                error_message=(
                                    "AIAgent model-visible tools do not match the "
                                    "capability policy."
                                ),
                            )

                    history = (
                        [dict(item) for item in request.conversation_history]
                        if request.conversation_history
                        else None
                    )
                    try:
                        raw = agent.run_conversation(
                            user_message=str(request.question).strip(),
                            conversation_history=history,
                        )
                    except Exception:
                        return _error_result(
                            hermes_session_id=session_id,
                            error_code="hermes_turn_error",
                            error_message="Hermes graph-agent turn failed.",
                            tool_events=collector.events,
                        )
            except Exception:
                return _error_result(
                    hermes_session_id=session_id,
                    error_code="hermes_agent_init_error",
                    error_message="Hermes graph-agent construction failed.",
                    tool_events=collector.events,
                )

            if not isinstance(raw, Mapping):
                return _error_result(
                    hermes_session_id=session_id,
                    error_code="hermes_malformed_response",
                    error_message="Hermes returned a malformed turn response.",
                    tool_events=collector.events,
                )

            messages = raw.get("messages")
            if messages is None:
                messages = []
            if not isinstance(messages, list):
                return _error_result(
                    hermes_session_id=session_id,
                    error_code="hermes_malformed_response",
                    error_message="Hermes returned a malformed messages payload.",
                    tool_events=collector.events,
                )

            final_response = raw.get("final_response")
            if final_response is not None and not isinstance(final_response, str):
                final_response = str(final_response)

            hydrated = (
                get_session(request.retrieval_session_id)
                if request.retrieval_session_id
                else None
            )
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response=final_response,
                messages=[
                    dict(m) if isinstance(m, Mapping) else {"value": m} for m in messages
                ],
                hermes_session_id=str(raw.get("session_id") or session_id),
                tool_events=list(collector.events),
                process_isolation=PROCESS_ISOLATION_MODE,
                retrieval_session_id=request.retrieval_session_id,
                retrieval_session=(
                    hydrated.project_for_hermes() if hydrated is not None else retrieval_session_packet
                ),
            )
        except Exception:
            return _error_result(
                hermes_session_id=session_id,
                error_code="hermes_graph_agent_error",
                error_message="Hermes graph-agent runtime failed unexpectedly.",
                tool_events=collector.events,
            )
        finally:
            reset_active_retrieval_session_id(session_token)
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
