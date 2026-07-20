"""Bounded JSON wire contract for Hermes graph-agent host IPC (PR353).

Types and strict serialize/deserialize helpers shared by the Rung 3 runtime
(re-exported) and the process-isolated host (sole import surface for the parent).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from graph_memory.hermes_graph_plugin import (
    HermesCapabilityPolicy,
    HermesGraphScope,
    HermesPluginActivation,
    HermesToolCapabilityRule,
)

HermesGraphAgentStatus = Literal["ok", "error"]
HermesAnswerScope = Literal["graph", "conversation_context"]
ToolEventState = Literal["start", "completion", "error"]
ProcessIsolationMode = Literal["process_exclusive"]

PROCESS_ISOLATION_MODE: ProcessIsolationMode = "process_exclusive"

MAX_WIRE_BYTES = 262144
MAX_QUESTION_CHARS = 8000
MAX_ID_CHARS = 256
MAX_SESSION_ID_CHARS = 256
MAX_HISTORY_MESSAGES = 32
MAX_MESSAGE_CHARS = 8000
MAX_FOCUS_KEYS = 8
MAX_FOCUS_VALUE_CHARS = 256
ALLOWED_FOCUS_KEYS = frozenset({"kind", "sessionId", "campaignId"})
MAX_ROOT_CHARS = 1024
MAX_POLICY_TOOLSETS = 16
MAX_POLICY_TOOL_NAMES = 64
MAX_PLUGIN_ACTIVATIONS = 16
MAX_TOOLSETS_PER_ACTIVATION = 16
MAX_TOOL_RULES = 64
MAX_ALLOWED_EFFECTS = 4
MAX_RESULT_MESSAGES = 64
MAX_TOOL_EVENTS = 128
MAX_BOUNDED_ID_MAP_KEYS = 32
MAX_ID_LIST = 64
MAX_DIAGNOSTIC_CODES = 32
MAX_FINAL_RESPONSE_CHARS = 32000
MAX_ERROR_MESSAGE_CHARS = 4000
ALLOWED_EFFECTS = frozenset({"read", "write"})

_REQUEST_ALLOWED_KEYS = frozenset(
    {
        "question",
        "worldId",
        "campaignId",
        "focus",
        "admissibility",
        "revisionPin",
        "conversationHistory",
        "sessionId",
        "root",
        "capabilityPolicy",
        "retrievalSessionId",
        "retrievalSession",
    }
)
_REQUEST_FORBIDDEN_KEYS = frozenset(
    {"agentFactory", "agent_factory", "callable", "importTarget", "env"}
)
_POLICY_ALLOWED_KEYS = frozenset(
    {
        "enabledToolsets",
        "enabledToolNames",
        "graphScope",
        "pluginActivations",
        "toolRules",
    }
)
_SCOPE_ALLOWED_KEYS = frozenset(
    {"worldId", "campaignId", "focus", "admissibility", "revisionPin"}
)
_ACTIVATION_ALLOWED_KEYS = frozenset({"pluginId", "toolsets"})
_RULE_ALLOWED_KEYS = frozenset(
    {"toolName", "toolset", "requireGraphScope", "allowedEffects"}
)
_RESULT_ALLOWED_KEYS = frozenset(
    {
        "status",
        "finalResponse",
        "messages",
        "hermesSessionId",
        "toolEvents",
        "errorCode",
        "errorMessage",
        "processIsolation",
        "retrievalSessionId",
        "retrievalSession",
        "answerScope",
    }
)
_TOOL_EVENT_ALLOWED_KEYS = frozenset(
    {
        "toolName",
        "state",
        "durationMs",
        "worldId",
        "campaignId",
        "focus",
        "admissibility",
        "revisionPin",
        "boundedIds",
        "retrievalSchema",
        "outcome",
        "matchedNodeIds",
        "relationshipIds",
        "sourceAnchorIds",
        "diagnosticCodes",
    }
)


@dataclass(frozen=True, slots=True)
class HermesGraphToolEvent:
    tool_name: str
    state: ToolEventState
    duration_ms: float | None = None
    world_id: str | None = None
    campaign_id: str | None = None
    focus: dict[str, Any] | None = None
    admissibility: str | None = None
    revision_pin: str | None = None
    bounded_ids: dict[str, Any] = field(default_factory=dict)
    retrieval_schema: str | None = None
    outcome: str | None = None
    matched_node_ids: list[str] = field(default_factory=list)
    relationship_ids: list[str] = field(default_factory=list)
    source_anchor_ids: list[str] = field(default_factory=list)
    diagnostic_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class HermesGraphAgentTurnResult:
    status: HermesGraphAgentStatus
    final_response: str | None
    messages: list[dict[str, Any]]
    hermes_session_id: str
    tool_events: list[HermesGraphToolEvent]
    error_code: str | None = None
    error_message: str | None = None
    process_isolation: ProcessIsolationMode = PROCESS_ISOLATION_MODE
    retrieval_session_id: str | None = None
    retrieval_session: dict[str, Any] | None = None
    answer_scope: HermesAnswerScope | None = None


@dataclass(frozen=True, slots=True)
class HermesGraphAgentTurnRequest:
    question: str
    world_id: str
    campaign_id: str
    focus: Mapping[str, Any] | None = None
    admissibility: str | None = None
    revision_pin: str | None = None
    conversation_history: Sequence[Mapping[str, Any]] | None = None
    session_id: str | None = None
    root: Path | None = None
    capability_policy: HermesCapabilityPolicy | None = None
    retrieval_session_id: str | None = None
    retrieval_session: Mapping[str, Any] | None = None


def _reject_unknown_keys(payload: Mapping[str, Any], allowed: frozenset[str], *, label: str) -> None:
    unknown = set(payload.keys()) - allowed
    if unknown:
        raise ValueError(f"{label} contains unknown keys: {sorted(unknown)}")


def _require_str(value: Any, *, label: str, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if len(value) > max_chars:
        raise ValueError(f"{label} exceeds max length {max_chars}")
    return value


def _optional_str(value: Any, *, label: str, max_chars: int) -> str | None:
    if value is None:
        return None
    return _require_str(value, label=label, max_chars=max_chars)


def _clip_str(value: str, *, max_chars: int) -> str:
    if len(value) > max_chars:
        return value[:max_chars]
    return value


def _validate_root_path(value: Any, *, on_deserialize: bool) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("root must be a string path or null")
    if "\x00" in value:
        raise ValueError("root must not contain NUL")
    if len(value) > MAX_ROOT_CHARS:
        raise ValueError(f"root exceeds max length {MAX_ROOT_CHARS}")
    if ".." in Path(value).parts:
        raise ValueError("root must not contain .. path segments")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("root must be an absolute path")
    return path


def _serialize_focus(focus: Mapping[str, Any] | None) -> dict[str, str | None] | None:
    if focus is None:
        return None
    if len(focus) > MAX_FOCUS_KEYS:
        raise ValueError(f"focus exceeds max keys {MAX_FOCUS_KEYS}")
    unknown = set(focus.keys()) - ALLOWED_FOCUS_KEYS
    if unknown:
        raise ValueError(f"focus contains unsupported keys: {sorted(unknown)}")
    bounded: dict[str, str | None] = {}
    for key in ALLOWED_FOCUS_KEYS:
        if key not in focus:
            continue
        raw = focus[key]
        if raw is None:
            bounded[key] = None
        elif isinstance(raw, str):
            if len(raw) > MAX_FOCUS_VALUE_CHARS:
                raise ValueError(f"focus.{key} exceeds max length {MAX_FOCUS_VALUE_CHARS}")
            bounded[key] = raw
        else:
            raise ValueError(f"focus.{key} must be a string or null")
    return bounded or None


def _deserialize_focus(focus: Any) -> dict[str, str | None] | None:
    if focus is None:
        return None
    if not isinstance(focus, Mapping):
        raise ValueError("focus must be a mapping or null")
    return _serialize_focus(dict(focus))


def _require_nonempty_str(value: Any, *, label: str, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{label} must be a non-empty string")
    if len(trimmed) > max_chars:
        raise ValueError(f"{label} exceeds max length {max_chars}")
    return trimmed


def _validate_history_pairs(items: Sequence[Mapping[str, Any]]) -> None:
    if len(items) % 2 != 0:
        raise ValueError("conversationHistory must contain complete user/assistant pairs")
    for index, item in enumerate(items):
        expected_role = "user" if index % 2 == 0 else "assistant"
        role = item.get("role")
        if role not in {"user", "assistant"}:
            raise ValueError("conversationHistory role must be user or assistant")
        if role != expected_role:
            raise ValueError(
                "conversationHistory messages must alternate user then assistant"
            )
        _require_nonempty_str(
            item.get("content"),
            label="conversationHistory.content",
            max_chars=MAX_MESSAGE_CHARS,
        )


def _serialize_history(
    history: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, str]] | None:
    if history is None:
        return None
    items = list(history)
    if len(items) > MAX_HISTORY_MESSAGES:
        raise ValueError(f"conversationHistory exceeds max messages {MAX_HISTORY_MESSAGES}")
    bounded: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ValueError("conversationHistory entries must be mappings")
        _reject_unknown_keys(item, frozenset({"role", "content"}), label="conversationHistory entry")
        role = _require_str(
            item.get("role"),
            label="conversationHistory.role",
            max_chars=MAX_ID_CHARS,
        )
        if role not in {"user", "assistant"}:
            raise ValueError("conversationHistory role must be user or assistant")
        content = _require_nonempty_str(
            item.get("content"),
            label="conversationHistory.content",
            max_chars=MAX_MESSAGE_CHARS,
        )
        bounded.append({"role": role, "content": _clip_str(content, max_chars=MAX_MESSAGE_CHARS)})
    _validate_history_pairs(bounded)
    return bounded


def _deserialize_history(history: Any) -> list[dict[str, str]] | None:
    if history is None:
        return None
    if not isinstance(history, list):
        raise ValueError("conversationHistory must be a list or null")
    return _serialize_history(history)


def encode_json_wire(obj: Any) -> bytes:
    """Encode a JSON object to bounded UTF-8 wire bytes."""
    try:
        text = json.dumps(
            obj,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("wire payload is not JSON-serializable") from exc
    raw = text.encode("utf-8")
    if len(raw) > MAX_WIRE_BYTES:
        raise ValueError(f"wire payload exceeds max bytes {MAX_WIRE_BYTES}")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("wire payload must encode a JSON object")
    return raw


def decode_json_wire(raw: bytes | bytearray | memoryview | str) -> dict[str, Any]:
    """Decode bounded UTF-8 wire bytes to a JSON object."""
    if isinstance(raw, (bytes, bytearray, memoryview)):
        text = bytes(raw).decode("utf-8")
    elif isinstance(raw, str):
        text = raw
    else:
        raise ValueError("wire payload must be bytes or str")
    if len(text.encode("utf-8")) > MAX_WIRE_BYTES:
        raise ValueError(f"wire payload exceeds max bytes {MAX_WIRE_BYTES}")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("wire payload must be a JSON object")
    return parsed


def serialize_capability_policy(policy: HermesCapabilityPolicy) -> dict[str, Any]:
    """Serialize a capability policy to a bounded JSON-compatible dict."""
    toolsets = list(policy.enabled_toolsets)
    tool_names = list(policy.enabled_tool_names)
    if len(toolsets) > MAX_POLICY_TOOLSETS:
        raise ValueError(f"enabledToolsets exceeds max {MAX_POLICY_TOOLSETS}")
    if len(tool_names) > MAX_POLICY_TOOL_NAMES:
        raise ValueError(f"enabledToolNames exceeds max {MAX_POLICY_TOOL_NAMES}")
    activations = list(policy.plugin_activations)
    rules = list(policy.tool_rules)
    if len(activations) > MAX_PLUGIN_ACTIVATIONS:
        raise ValueError(f"pluginActivations exceeds max {MAX_PLUGIN_ACTIVATIONS}")
    if len(rules) > MAX_TOOL_RULES:
        raise ValueError(f"toolRules exceeds max {MAX_TOOL_RULES}")
    return {
        "enabledToolsets": [_require_str(item, label="toolset", max_chars=MAX_ID_CHARS) for item in toolsets],
        "enabledToolNames": [
            _require_str(item, label="toolName", max_chars=MAX_ID_CHARS) for item in tool_names
        ],
        "graphScope": {
            "worldId": _require_str(
                policy.graph_scope.world_id,
                label="worldId",
                max_chars=MAX_ID_CHARS,
            ),
            "campaignId": _require_str(
                policy.graph_scope.campaign_id,
                label="campaignId",
                max_chars=MAX_ID_CHARS,
            ),
            "focus": _serialize_focus(policy.graph_scope.focus),
            "admissibility": _require_str(
                policy.graph_scope.admissibility,
                label="admissibility",
                max_chars=MAX_ID_CHARS,
            ),
            "revisionPin": _optional_str(
                policy.graph_scope.revision_pin,
                label="revisionPin",
                max_chars=MAX_ID_CHARS,
            ),
        },
        "pluginActivations": [
            _serialize_plugin_activation(activation) for activation in activations
        ],
        "toolRules": [
            {
                "toolName": _require_str(rule.tool_name, label="toolName", max_chars=MAX_ID_CHARS),
                "toolset": _require_str(rule.toolset, label="toolset", max_chars=MAX_ID_CHARS),
                "requireGraphScope": bool(rule.require_graph_scope),
                "allowedEffects": sorted(
                    _serialize_allowed_effects(rule.allowed_effects)
                ),
            }
            for rule in rules
        ],
    }


def _serialize_plugin_activation(activation: HermesPluginActivation) -> dict[str, Any]:
    toolsets = list(activation.toolsets)
    if len(toolsets) > MAX_TOOLSETS_PER_ACTIVATION:
        raise ValueError(
            f"plugin activation toolsets exceed max {MAX_TOOLSETS_PER_ACTIVATION}"
        )
    return {
        "pluginId": _require_str(
            activation.plugin_id,
            label="pluginId",
            max_chars=MAX_ID_CHARS,
        ),
        "toolsets": [
            _require_str(toolset, label="activation.toolset", max_chars=MAX_ID_CHARS)
            for toolset in toolsets
        ],
    }


def _serialize_allowed_effects(effects: frozenset[str] | set[str]) -> list[str]:
    items = list(effects)
    if len(items) > MAX_ALLOWED_EFFECTS:
        raise ValueError(f"allowedEffects exceeds max {MAX_ALLOWED_EFFECTS}")
    serialized: list[str] = []
    for effect in items:
        effect_str = _require_str(effect, label="allowedEffect", max_chars=MAX_ID_CHARS)
        if effect_str not in ALLOWED_EFFECTS:
            raise ValueError(f"unsupported tool effect: {effect_str!r}")
        serialized.append(effect_str)
    return serialized


def deserialize_capability_policy(payload: Mapping[str, Any]) -> HermesCapabilityPolicy:
    """Rebuild a capability policy from :func:`serialize_capability_policy` output."""
    if not isinstance(payload, Mapping):
        raise ValueError("capability policy payload must be a mapping")
    _reject_unknown_keys(payload, _POLICY_ALLOWED_KEYS, label="capability policy")
    scope_raw = payload.get("graphScope")
    if not isinstance(scope_raw, Mapping):
        raise ValueError("capability policy graphScope must be a mapping")
    _reject_unknown_keys(scope_raw, _SCOPE_ALLOWED_KEYS, label="graphScope")
    toolsets_raw = payload.get("enabledToolsets")
    names_raw = payload.get("enabledToolNames")
    if not isinstance(toolsets_raw, list) or not isinstance(names_raw, list):
        raise ValueError("capability policy toolsets/names must be lists")
    if len(toolsets_raw) > MAX_POLICY_TOOLSETS:
        raise ValueError(f"enabledToolsets exceeds max {MAX_POLICY_TOOLSETS}")
    if len(names_raw) > MAX_POLICY_TOOL_NAMES:
        raise ValueError(f"enabledToolNames exceeds max {MAX_POLICY_TOOL_NAMES}")
    activations_raw = payload.get("pluginActivations")
    rules_raw = payload.get("toolRules")
    if not isinstance(activations_raw, list):
        raise ValueError("capability policy pluginActivations must be a list")
    if not isinstance(rules_raw, list):
        raise ValueError("capability policy toolRules must be a list")
    if len(activations_raw) > MAX_PLUGIN_ACTIVATIONS:
        raise ValueError(f"pluginActivations exceeds max {MAX_PLUGIN_ACTIVATIONS}")
    if len(rules_raw) > MAX_TOOL_RULES:
        raise ValueError(f"toolRules exceeds max {MAX_TOOL_RULES}")

    activations: list[HermesPluginActivation] = []
    for item in activations_raw:
        if not isinstance(item, Mapping):
            raise ValueError("plugin activation must be a mapping")
        _reject_unknown_keys(item, _ACTIVATION_ALLOWED_KEYS, label="plugin activation")
        toolsets = item.get("toolsets")
        if not isinstance(toolsets, list):
            raise ValueError("plugin activation toolsets must be a list")
        if len(toolsets) > MAX_TOOLSETS_PER_ACTIVATION:
            raise ValueError(
                f"plugin activation toolsets exceeds max {MAX_TOOLSETS_PER_ACTIVATION}"
            )
        plugin_id = _require_str(item.get("pluginId"), label="pluginId", max_chars=MAX_ID_CHARS)
        if not plugin_id.strip():
            raise ValueError("plugin activation pluginId must be a non-empty string")
        activations.append(
            HermesPluginActivation(
                plugin_id=plugin_id.strip(),
                toolsets=tuple(
                    _require_str(toolset, label="activation.toolset", max_chars=MAX_ID_CHARS)
                    for toolset in toolsets
                ),
            )
        )

    rules: list[HermesToolCapabilityRule] = []
    for item in rules_raw:
        if not isinstance(item, Mapping):
            raise ValueError("tool rule must be a mapping")
        _reject_unknown_keys(item, _RULE_ALLOWED_KEYS, label="tool rule")
        effects_raw = item.get("allowedEffects")
        if not isinstance(effects_raw, list):
            raise ValueError("tool rule allowedEffects must be a list")
        if len(effects_raw) > MAX_ALLOWED_EFFECTS:
            raise ValueError(f"allowedEffects exceeds max {MAX_ALLOWED_EFFECTS}")
        effects: set[str] = set()
        for effect in effects_raw:
            effect_str = _require_str(effect, label="allowedEffect", max_chars=MAX_ID_CHARS)
            if effect_str not in ALLOWED_EFFECTS:
                raise ValueError(f"unsupported tool effect: {effect_str!r}")
            effects.add(effect_str)
        rules.append(
            HermesToolCapabilityRule(
                tool_name=_require_str(item.get("toolName"), label="toolName", max_chars=MAX_ID_CHARS),
                toolset=_require_str(item.get("toolset"), label="toolset", max_chars=MAX_ID_CHARS),
                require_graph_scope=bool(item.get("requireGraphScope", True)),
                allowed_effects=frozenset(effects),  # type: ignore[arg-type]
            )
        )

    focus = _deserialize_focus(scope_raw.get("focus"))
    return HermesCapabilityPolicy(
        enabled_toolsets=tuple(
            _require_str(item, label="toolset", max_chars=MAX_ID_CHARS) for item in toolsets_raw
        ),
        enabled_tool_names=tuple(
            _require_str(item, label="toolName", max_chars=MAX_ID_CHARS) for item in names_raw
        ),
        graph_scope=HermesGraphScope(
            world_id=_require_str(scope_raw.get("worldId"), label="worldId", max_chars=MAX_ID_CHARS).strip(),
            campaign_id=_require_str(
                scope_raw.get("campaignId"),
                label="campaignId",
                max_chars=MAX_ID_CHARS,
            ).strip(),
            focus=focus or {},
            admissibility=_require_str(
                scope_raw.get("admissibility") or "gm",
                label="admissibility",
                max_chars=MAX_ID_CHARS,
            ),
            revision_pin=_optional_str(
                scope_raw.get("revisionPin"),
                label="revisionPin",
                max_chars=MAX_ID_CHARS,
            ),
        ),
        plugin_activations=tuple(activations),
        tool_rules=tuple(rules),
    )


def serialize_hermes_graph_agent_turn_request(
    request: HermesGraphAgentTurnRequest,
) -> dict[str, Any]:
    """Serialize a Rung 3 turn request for host IPC (no callables)."""
    question = _require_str(request.question, label="question", max_chars=MAX_QUESTION_CHARS)
    world_id = _require_str(request.world_id, label="worldId", max_chars=MAX_ID_CHARS)
    campaign_id = _require_str(request.campaign_id, label="campaignId", max_chars=MAX_ID_CHARS)
    root = request.root
    root_str = None if root is None else str(Path(root))
    if root_str is not None:
        _validate_root_path(root_str, on_deserialize=False)
    focus = None if request.focus is None else _serialize_focus(request.focus)
    policy_payload = (
        None
        if request.capability_policy is None
        else serialize_capability_policy(request.capability_policy)
    )
    retrieval_session = None
    if request.retrieval_session is not None:
        if not isinstance(request.retrieval_session, Mapping):
            raise ValueError("retrievalSession must be a mapping or null")
        # Bound by wire encoder MAX_WIRE_BYTES; keep as JSON-safe mapping.
        retrieval_session = dict(request.retrieval_session)
    return {
        "question": question,
        "worldId": world_id,
        "campaignId": campaign_id,
        "focus": focus,
        "admissibility": _optional_str(
            request.admissibility,
            label="admissibility",
            max_chars=MAX_ID_CHARS,
        ),
        "revisionPin": _optional_str(
            request.revision_pin,
            label="revisionPin",
            max_chars=MAX_ID_CHARS,
        ),
        "conversationHistory": _serialize_history(request.conversation_history),
        "sessionId": _optional_str(
            request.session_id,
            label="sessionId",
            max_chars=MAX_SESSION_ID_CHARS,
        ),
        "root": root_str,
        "capabilityPolicy": policy_payload,
        "retrievalSessionId": _optional_str(
            request.retrieval_session_id,
            label="retrievalSessionId",
            max_chars=MAX_SESSION_ID_CHARS,
        ),
        "retrievalSession": retrieval_session,
    }


def deserialize_hermes_graph_agent_turn_request(
    payload: Mapping[str, Any],
) -> HermesGraphAgentTurnRequest:
    """Rebuild a Rung 3 turn request from host IPC payload."""
    if not isinstance(payload, Mapping):
        raise ValueError("turn request payload must be a mapping")
    if any(key in payload for key in _REQUEST_FORBIDDEN_KEYS):
        raise ValueError("turn request payload contains forbidden fields")
    _reject_unknown_keys(payload, _REQUEST_ALLOWED_KEYS, label="turn request")
    root = _validate_root_path(payload.get("root"), on_deserialize=True)
    policy_raw = payload.get("capabilityPolicy")
    policy = None if policy_raw is None else deserialize_capability_policy(policy_raw)
    history = _deserialize_history(payload.get("conversationHistory"))
    focus = _deserialize_focus(payload.get("focus"))
    retrieval_session_raw = payload.get("retrievalSession")
    if retrieval_session_raw is not None and not isinstance(retrieval_session_raw, Mapping):
        raise ValueError("retrievalSession must be a mapping or null")
    return HermesGraphAgentTurnRequest(
        question=_require_str(payload.get("question") or "", label="question", max_chars=MAX_QUESTION_CHARS),
        world_id=_require_str(payload.get("worldId") or "", label="worldId", max_chars=MAX_ID_CHARS),
        campaign_id=_require_str(payload.get("campaignId") or "", label="campaignId", max_chars=MAX_ID_CHARS),
        focus=focus,
        admissibility=_optional_str(
            payload.get("admissibility"),
            label="admissibility",
            max_chars=MAX_ID_CHARS,
        ),
        revision_pin=_optional_str(
            payload.get("revisionPin"),
            label="revisionPin",
            max_chars=MAX_ID_CHARS,
        ),
        conversation_history=history,
        session_id=_optional_str(
            payload.get("sessionId"),
            label="sessionId",
            max_chars=MAX_SESSION_ID_CHARS,
        ),
        root=root,
        capability_policy=policy,
        retrieval_session_id=_optional_str(
            payload.get("retrievalSessionId"),
            label="retrievalSessionId",
            max_chars=MAX_SESSION_ID_CHARS,
        ),
        retrieval_session=None if retrieval_session_raw is None else dict(retrieval_session_raw),
    )


def _serialize_bounded_id_map(value: Mapping[str, Any]) -> dict[str, Any]:
    if len(value) > MAX_BOUNDED_ID_MAP_KEYS:
        raise ValueError(f"boundedIds exceeds max keys {MAX_BOUNDED_ID_MAP_KEYS}")
    bounded: dict[str, Any] = {}
    for key, item in value.items():
        key_str = _require_str(key, label="boundedIds key", max_chars=MAX_ID_CHARS)
        if isinstance(item, str):
            bounded[key_str] = _clip_str(item, max_chars=MAX_ID_CHARS)
        elif isinstance(item, bool):
            bounded[key_str] = item
        elif isinstance(item, (int, float)):
            bounded[key_str] = item
        elif isinstance(item, list):
            if len(item) > MAX_ID_LIST:
                raise ValueError(f"boundedIds list exceeds max items {MAX_ID_LIST}")
            bounded[key_str] = [
                _clip_str(str(entry), max_chars=MAX_ID_CHARS) for entry in item
            ]
        elif isinstance(item, Mapping):
            if len(item) > MAX_BOUNDED_ID_MAP_KEYS:
                raise ValueError(
                    f"boundedIds nested map exceeds max keys {MAX_BOUNDED_ID_MAP_KEYS}"
                )
            nested: dict[str, Any] = {}
            for nested_key, nested_value in item.items():
                nested[str(nested_key)] = (
                    None
                    if nested_value is None
                    else _clip_str(str(nested_value), max_chars=MAX_ID_CHARS)
                )
            bounded[key_str] = nested
        elif item is None:
            bounded[key_str] = None
        else:
            raise ValueError("boundedIds values must be JSON-safe scalars or lists")
    return bounded


def _serialize_id_list(values: Sequence[Any], *, label: str) -> list[str]:
    items = list(values)
    max_items = MAX_DIAGNOSTIC_CODES if label == "diagnosticCodes" else MAX_ID_LIST
    if len(items) > max_items:
        raise ValueError(f"{label} exceeds max items {max_items}")
    return [_clip_str(str(item), max_chars=MAX_ID_CHARS) for item in items]


def _serialize_tool_event(event: HermesGraphToolEvent) -> dict[str, Any]:
    return {
        "toolName": _clip_str(event.tool_name, max_chars=MAX_ID_CHARS),
        "state": event.state,
        "durationMs": event.duration_ms,
        "worldId": (
            None
            if event.world_id is None
            else _clip_str(event.world_id, max_chars=MAX_ID_CHARS)
        ),
        "campaignId": (
            None
            if event.campaign_id is None
            else _clip_str(event.campaign_id, max_chars=MAX_ID_CHARS)
        ),
        "focus": _serialize_focus(event.focus) if event.focus is not None else None,
        "admissibility": (
            None
            if event.admissibility is None
            else _clip_str(event.admissibility, max_chars=MAX_ID_CHARS)
        ),
        "revisionPin": (
            None
            if event.revision_pin is None
            else _clip_str(event.revision_pin, max_chars=MAX_ID_CHARS)
        ),
        "boundedIds": _serialize_bounded_id_map(event.bounded_ids),
        "retrievalSchema": (
            None
            if event.retrieval_schema is None
            else _clip_str(event.retrieval_schema, max_chars=MAX_ID_CHARS)
        ),
        "outcome": (
            None if event.outcome is None else _clip_str(event.outcome, max_chars=MAX_ID_CHARS)
        ),
        "matchedNodeIds": _serialize_id_list(event.matched_node_ids, label="matchedNodeIds"),
        "relationshipIds": _serialize_id_list(event.relationship_ids, label="relationshipIds"),
        "sourceAnchorIds": _serialize_id_list(event.source_anchor_ids, label="sourceAnchorIds"),
        "diagnosticCodes": _serialize_id_list(
            event.diagnostic_codes,
            label="diagnosticCodes",
        ),
    }


def serialize_hermes_graph_agent_turn_result(
    result: HermesGraphAgentTurnResult,
) -> dict[str, Any]:
    """Serialize a Rung 3 turn result for host IPC.

    Hermes transcripts may contain tool_calls / tool-role messages that are not
    safe {role, content} records. The host wire intentionally omits ``messages``;
    PR354 consumes ``finalResponse`` and bounded ``toolEvents`` only.
    """
    if len(result.tool_events) > MAX_TOOL_EVENTS:
        raise ValueError(f"toolEvents exceeds max {MAX_TOOL_EVENTS}")
    final_response = result.final_response
    if final_response is not None:
        final_response = _clip_str(final_response, max_chars=MAX_FINAL_RESPONSE_CHARS)
    error_message = result.error_message
    if error_message is not None:
        error_message = _clip_str(error_message, max_chars=MAX_ERROR_MESSAGE_CHARS)
    retrieval_session = None
    if result.retrieval_session is not None:
        if not isinstance(result.retrieval_session, Mapping):
            raise ValueError("retrievalSession must be a mapping or null")
        retrieval_session = dict(result.retrieval_session)
    return {
        "status": result.status,
        "finalResponse": final_response,
        # Host IPC omits Hermes transcript; keep the key for schema stability.
        "messages": [],
        "hermesSessionId": _clip_str(result.hermes_session_id, max_chars=MAX_SESSION_ID_CHARS),
        "toolEvents": [_serialize_tool_event(event) for event in result.tool_events],
        "errorCode": (
            None
            if result.error_code is None
            else _clip_str(result.error_code, max_chars=MAX_ID_CHARS)
        ),
        "errorMessage": error_message,
        "processIsolation": result.process_isolation,
        "retrievalSessionId": (
            None
            if result.retrieval_session_id is None
            else _clip_str(result.retrieval_session_id, max_chars=MAX_SESSION_ID_CHARS)
        ),
        "retrievalSession": retrieval_session,
        "answerScope": result.answer_scope,
    }


def _deserialize_tool_event(item: Mapping[str, Any]) -> HermesGraphToolEvent:
    _reject_unknown_keys(item, _TOOL_EVENT_ALLOWED_KEYS, label="tool event")
    state = item.get("state")
    if state not in {"start", "completion", "error"}:
        raise ValueError("tool event state must be start, completion, or error")
    focus_raw = item.get("focus")
    focus = None if focus_raw is None else _deserialize_focus(focus_raw)
    bounded_raw = item.get("boundedIds") or {}
    if not isinstance(bounded_raw, Mapping):
        raise ValueError("boundedIds must be a mapping")
    if len(bounded_raw) > MAX_BOUNDED_ID_MAP_KEYS:
        raise ValueError(f"boundedIds exceeds max keys {MAX_BOUNDED_ID_MAP_KEYS}")
    return HermesGraphToolEvent(
        tool_name=_require_str(item.get("toolName") or "", label="toolName", max_chars=MAX_ID_CHARS),
        state=state,  # type: ignore[arg-type]
        duration_ms=(
            None if item.get("durationMs") is None else float(item.get("durationMs"))
        ),
        world_id=_optional_str(item.get("worldId"), label="worldId", max_chars=MAX_ID_CHARS),
        campaign_id=_optional_str(item.get("campaignId"), label="campaignId", max_chars=MAX_ID_CHARS),
        focus=focus,
        admissibility=_optional_str(
            item.get("admissibility"),
            label="admissibility",
            max_chars=MAX_ID_CHARS,
        ),
        revision_pin=_optional_str(
            item.get("revisionPin"),
            label="revisionPin",
            max_chars=MAX_ID_CHARS,
        ),
        bounded_ids=dict(_serialize_bounded_id_map(bounded_raw)),
        retrieval_schema=_optional_str(
            item.get("retrievalSchema"),
            label="retrievalSchema",
            max_chars=MAX_ID_CHARS,
        ),
        outcome=_optional_str(item.get("outcome"), label="outcome", max_chars=MAX_ID_CHARS),
        matched_node_ids=_serialize_id_list(
            item.get("matchedNodeIds") or [],
            label="matchedNodeIds",
        ),
        relationship_ids=_serialize_id_list(
            item.get("relationshipIds") or [],
            label="relationshipIds",
        ),
        source_anchor_ids=_serialize_id_list(
            item.get("sourceAnchorIds") or [],
            label="sourceAnchorIds",
        ),
        diagnostic_codes=_serialize_id_list(
            item.get("diagnosticCodes") or [],
            label="diagnosticCodes",
        ),
    )


def deserialize_hermes_graph_agent_turn_result(
    payload: Mapping[str, Any],
) -> HermesGraphAgentTurnResult:
    """Rebuild a Rung 3 turn result from host IPC payload."""
    if not isinstance(payload, Mapping):
        raise ValueError("turn result payload must be a mapping")
    _reject_unknown_keys(payload, _RESULT_ALLOWED_KEYS, label="turn result")
    status = payload.get("status")
    if status not in {"ok", "error"}:
        raise ValueError("result status must be ok or error")
    messages_raw = payload.get("messages") or []
    if not isinstance(messages_raw, list):
        raise ValueError("messages must be a list")
    if len(messages_raw) > MAX_RESULT_MESSAGES:
        raise ValueError(f"messages exceeds max {MAX_RESULT_MESSAGES}")
    messages: list[dict[str, str]] = []
    for item in messages_raw:
        if not isinstance(item, Mapping):
            raise ValueError("messages entries must be mappings")
        _reject_unknown_keys(item, frozenset({"role", "content"}), label="message")
        messages.append(
            {
                "role": _require_str(item.get("role"), label="message.role", max_chars=MAX_ID_CHARS),
                "content": _require_str(
                    item.get("content"),
                    label="message.content",
                    max_chars=MAX_MESSAGE_CHARS,
                ),
            }
        )
    events_raw = payload.get("toolEvents") or []
    if not isinstance(events_raw, list):
        raise ValueError("toolEvents must be a list")
    if len(events_raw) > MAX_TOOL_EVENTS:
        raise ValueError(f"toolEvents exceeds max {MAX_TOOL_EVENTS}")
    events = [_deserialize_tool_event(item) for item in events_raw if isinstance(item, Mapping)]
    if len(events) != len(events_raw):
        raise ValueError("toolEvents entries must be mappings")
    final_response = payload.get("finalResponse")
    if final_response is not None:
        final_response = _require_str(
            final_response,
            label="finalResponse",
            max_chars=MAX_FINAL_RESPONSE_CHARS,
        )
    error_message = payload.get("errorMessage")
    if error_message is not None:
        error_message = _require_str(
            error_message,
            label="errorMessage",
            max_chars=MAX_ERROR_MESSAGE_CHARS,
        )
    process_isolation = payload.get("processIsolation")
    if process_isolation not in {None, PROCESS_ISOLATION_MODE}:
        raise ValueError("processIsolation must be process_exclusive")
    retrieval_session_raw = payload.get("retrievalSession")
    if retrieval_session_raw is not None and not isinstance(retrieval_session_raw, Mapping):
        raise ValueError("retrievalSession must be a mapping or null")
    answer_scope_raw = payload.get("answerScope")
    if answer_scope_raw is not None and answer_scope_raw not in {
        "graph",
        "conversation_context",
    }:
        raise ValueError("answerScope must be graph, conversation_context, or null")
    return HermesGraphAgentTurnResult(
        status=status,  # type: ignore[arg-type]
        final_response=final_response,
        messages=messages,
        hermes_session_id=_require_str(
            payload.get("hermesSessionId") or "",
            label="hermesSessionId",
            max_chars=MAX_SESSION_ID_CHARS,
        ),
        tool_events=events,
        error_code=_optional_str(payload.get("errorCode"), label="errorCode", max_chars=MAX_ID_CHARS),
        error_message=error_message,
        process_isolation=PROCESS_ISOLATION_MODE,
        retrieval_session_id=_optional_str(
            payload.get("retrievalSessionId"),
            label="retrievalSessionId",
            max_chars=MAX_SESSION_ID_CHARS,
        ),
        retrieval_session=None if retrieval_session_raw is None else dict(retrieval_session_raw),
        answer_scope=answer_scope_raw,  # type: ignore[arg-type]
    )


def encode_turn_request_wire(request: HermesGraphAgentTurnRequest) -> bytes:
    return encode_json_wire(serialize_hermes_graph_agent_turn_request(request))


def decode_turn_request_wire(raw: bytes | bytearray | memoryview | str) -> HermesGraphAgentTurnRequest:
    return deserialize_hermes_graph_agent_turn_request(decode_json_wire(raw))


def encode_turn_result_wire(result: HermesGraphAgentTurnResult) -> bytes:
    return encode_json_wire(serialize_hermes_graph_agent_turn_result(result))


def decode_turn_result_wire(raw: bytes | bytearray | memoryview | str) -> HermesGraphAgentTurnResult:
    return deserialize_hermes_graph_agent_turn_result(decode_json_wire(raw))


__all__ = [
    "ALLOWED_EFFECTS",
    "ALLOWED_FOCUS_KEYS",
    "HermesGraphAgentTurnRequest",
    "HermesGraphAgentTurnResult",
    "HermesGraphToolEvent",
    "HermesAnswerScope",
    "PROCESS_ISOLATION_MODE",
    "decode_json_wire",
    "decode_turn_request_wire",
    "decode_turn_result_wire",
    "deserialize_capability_policy",
    "deserialize_hermes_graph_agent_turn_request",
    "deserialize_hermes_graph_agent_turn_result",
    "encode_json_wire",
    "encode_turn_request_wire",
    "encode_turn_result_wire",
    "serialize_capability_policy",
    "serialize_hermes_graph_agent_turn_request",
    "serialize_hermes_graph_agent_turn_result",
]
