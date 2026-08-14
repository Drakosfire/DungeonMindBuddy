"""Packaged Hermes plugin: graph interaction and answer-scope tools.

Registers expand_graph_retrieval + read_graph_source and the explicit
conversation-context declaration under toolset ``dungeonbuddy_graph``. Kernel
search/object/neighborhood/evidence/source-read primitives remain internal.
Capability policy injects authoritative scope and the active retrieval session
ID only for graph interaction tools.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.services.hermes_graph_interaction_tools import (
    DECLARE_CONVERSATION_CONTEXT_TOOL_NAME,
    HERMES_GRAPH_INTERACTION_TOOL_NAMES,
    ORDERED_INTERACTION_TOOL_NAMES,
    ORDERED_MODEL_VISIBLE_TOOL_NAMES,
    QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
    execute_hermes_graph_interaction_tool_json,
    hermes_model_visible_tool_definitions,
)
from apps.live_control_server.services.canvas_block_proposal import (
    CANVAS_BLOCK_PROPOSAL_SCHEMA,
    PROPOSE_CANVAS_BLOCK_TOOL_NAME,
)

TOOLSET_NAME = "dungeonbuddy_graph"

ToolEffect = Literal["read", "write"]

ORDERED_GRAPH_TOOL_NAMES: tuple[str, ...] = ORDERED_INTERACTION_TOOL_NAMES
HERMES_GRAPH_READ_TOOL_NAMES = frozenset(
    name
    for name in HERMES_GRAPH_INTERACTION_TOOL_NAMES
    if name != PROPOSE_CANVAS_BLOCK_TOOL_NAME
)
HERMES_GRAPH_SESSION_TOOL_NAMES = frozenset(
    {
        "expand_graph_retrieval",
        "read_graph_source",
    }
)

# Optional process-local graph root override for tests / embedded callers.
# Not part of the model-visible tool arguments.
_graph_root_override: ContextVar[Path | None] = ContextVar(
    "hermes_graph_plugin_root",
    default=None,
)

# Active capability policy for the current embedded turn (process ContextVar).
_active_capability_policy: ContextVar["HermesCapabilityPolicy | None"] = ContextVar(
    "hermes_graph_plugin_capability_policy",
    default=None,
)

# Active GraphRetrievalSession id for the current embedded turn.
_active_retrieval_session_id: ContextVar[str | None] = ContextVar(
    "hermes_graph_plugin_retrieval_session_id",
    default=None,
)

# Active Canvas work object for propose_canvas_block inject (not model-authored).
_active_canvas_work_object: ContextVar["HermesCanvasWorkObject | None"] = ContextVar(
    "hermes_graph_plugin_canvas_work_object",
    default=None,
)

# Turn-local mutation bucket filled by propose_canvas_block successes.
_pending_canvas_mutations: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "hermes_graph_plugin_pending_canvas_mutations",
    default=None,
)


@dataclass(frozen=True, slots=True)
class HermesGraphScope:
    """Immutable authoritative graph scope for a turn."""

    world_id: str
    campaign_id: str
    focus: Mapping[str, Any]
    admissibility: str
    revision_pin: str | None = None


@dataclass(frozen=True, slots=True)
class HermesCanvasWorkObject:
    """Published Canvas identity for propose_canvas_block (server-injected)."""

    document_id: str
    surface_id: str
    expected_content_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class HermesPluginActivation:
    """Binds a Hermes plugin registry identity to one or more model toolsets.

    ``plugin_id`` is written to ``plugins.enabled`` and used to look up the
    loaded plugin (path-derived key or manifest name). ``toolsets`` are the
    names passed to ``AIAgent(enabled_toolsets=...)`` and used when attributing
    tools via :class:`HermesToolCapabilityRule.toolset`. These namespaces are
    intentionally independent — a plugin may register tools under a toolset
    that differs from its plugin key / manifest name.
    """

    plugin_id: str
    toolsets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HermesToolCapabilityRule:
    """Per-tool constraints within a capability policy.

    ``allowed_effects`` is enforced by the graph plugin handlers for this
    rung (every graph handler dispatches as ``read``). Hermes-wide effect
    classification for arbitrary non-graph tools is **not** implemented yet;
    do not treat this field as a complete cross-toolset write/read gate until
    a later rung associates authoritative effect metadata with every
    model-visible tool.

    ``toolset`` identifies which Hermes toolset owns the tool so discovery
    verification and stale-registry purge stay toolset-scoped.
    """

    tool_name: str
    toolset: str = TOOLSET_NAME
    require_graph_scope: bool = True
    allowed_effects: frozenset[ToolEffect] = field(
        default_factory=lambda: frozenset({"read"})
    )


@dataclass(frozen=True, slots=True)
class HermesCapabilityPolicy:
    """Caller-supplied capability boundary for an embedded Hermes turn.

    The default factory is graph-only / five-tool / read-only. Callers may
    enable additional **plugins** via :attr:`plugin_activations` (Hermes
    ``plugins.enabled`` identities) and expose their toolsets via
    :attr:`enabled_toolsets`. Hermes built-in toolsets (terminal, web, …)
    are not supported by this wrapper yet and must be rejected explicitly
    rather than silently deregistered.
    """

    enabled_toolsets: tuple[str, ...]
    enabled_tool_names: tuple[str, ...]
    graph_scope: HermesGraphScope
    tool_rules: tuple[HermesToolCapabilityRule, ...]
    plugin_activations: tuple[HermesPluginActivation, ...]

    @property
    def enabled_plugin_ids(self) -> tuple[str, ...]:
        return tuple(activation.plugin_id for activation in self.plugin_activations)

    def rule_for(self, tool_name: str) -> HermesToolCapabilityRule | None:
        for rule in self.tool_rules:
            if rule.tool_name == tool_name:
                return rule
        return None

    def tool_names_for_toolset(self, toolset: str) -> tuple[str, ...]:
        return tuple(
            rule.tool_name for rule in self.tool_rules if rule.toolset == toolset
        )

    def toolsets_for_plugin(self, plugin_id: str) -> tuple[str, ...]:
        for activation in self.plugin_activations:
            if activation.plugin_id == plugin_id:
                return activation.toolsets
        return ()

    def expected_tool_names_for_plugin(self, plugin_id: str) -> tuple[str, ...]:
        names: list[str] = []
        for toolset in self.toolsets_for_plugin(plugin_id):
            names.extend(self.tool_names_for_toolset(toolset))
        return tuple(names)


def default_graph_only_capability_policy(
    scope: HermesGraphScope,
) -> HermesCapabilityPolicy:
    """Default policy: declare scope + expand + source-read + Threat + canvas propose."""
    graph_names = tuple(
        name
        for name in ORDERED_GRAPH_TOOL_NAMES
        if name
        not in {
            QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
            PROPOSE_CANVAS_BLOCK_TOOL_NAME,
        }
    )
    names = tuple(ORDERED_MODEL_VISIBLE_TOOL_NAMES)
    return HermesCapabilityPolicy(
        enabled_toolsets=(TOOLSET_NAME,),
        enabled_tool_names=names,
        graph_scope=scope,
        plugin_activations=(
            HermesPluginActivation(
                plugin_id=TOOLSET_NAME,
                toolsets=(TOOLSET_NAME,),
            ),
        ),
        tool_rules=(
            HermesToolCapabilityRule(
                tool_name=DECLARE_CONVERSATION_CONTEXT_TOOL_NAME,
                toolset=TOOLSET_NAME,
                require_graph_scope=False,
                allowed_effects=frozenset({"read"}),
            ),
            HermesToolCapabilityRule(
                tool_name=QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
                toolset=TOOLSET_NAME,
                # Exact Threat hydration requires authoritative turn scope inject.
                require_graph_scope=True,
                allowed_effects=frozenset({"read"}),
            ),
            HermesToolCapabilityRule(
                tool_name=PROPOSE_CANVAS_BLOCK_TOOL_NAME,
                toolset=TOOLSET_NAME,
                # Canvas documentId inject is separate from graph scope.
                require_graph_scope=False,
                allowed_effects=frozenset({"write"}),
            ),
            *(
                HermesToolCapabilityRule(
                    tool_name=name,
                    toolset=TOOLSET_NAME,
                    # Session tools bind via retrievalSessionId; scope is validated
                    # against the hydrated session rather than request body fields.
                    require_graph_scope=False,
                    allowed_effects=frozenset({"read"}),
                )
                for name in graph_names
            ),
        ),
    )


def set_active_retrieval_session_id(session_id: str | None) -> Any:
    return _active_retrieval_session_id.set(session_id)


def reset_active_retrieval_session_id(token: Any) -> None:
    _active_retrieval_session_id.reset(token)


def get_active_retrieval_session_id() -> str | None:
    return _active_retrieval_session_id.get()


def set_active_canvas_work_object(work: HermesCanvasWorkObject | None) -> Any:
    return _active_canvas_work_object.set(work)


def reset_active_canvas_work_object(token: Any) -> None:
    _active_canvas_work_object.reset(token)


def get_active_canvas_work_object() -> HermesCanvasWorkObject | None:
    return _active_canvas_work_object.get()


def begin_pending_canvas_mutations() -> Any:
    return _pending_canvas_mutations.set([])


def reset_pending_canvas_mutations(token: Any) -> None:
    _pending_canvas_mutations.reset(token)


def record_pending_canvas_mutation(proposal: Mapping[str, Any]) -> None:
    bucket = _pending_canvas_mutations.get()
    if bucket is None:
        return
    if str(proposal.get("schema") or "") != CANVAS_BLOCK_PROPOSAL_SCHEMA:
        return
    bucket.append(dict(proposal))


def take_pending_canvas_mutations() -> list[dict[str, Any]]:
    bucket = _pending_canvas_mutations.get()
    if not bucket:
        return []
    return [dict(item) for item in bucket]


def validate_capability_policy_structure(
    policy: HermesCapabilityPolicy,
) -> str | None:
    """Fail-closed structural checks before Hermes agent construction.

    Returns an error code string, or ``None`` when the policy is well-formed.
    """
    if not policy.plugin_activations:
        return "hermes_capability_policy_empty_plugin_activations"
    if not policy.enabled_toolsets:
        return "hermes_capability_policy_empty_toolsets"
    if not policy.enabled_tool_names:
        return "hermes_capability_policy_empty_tools"
    plugin_ids = [activation.plugin_id for activation in policy.plugin_activations]
    if len(plugin_ids) != len(set(plugin_ids)):
        return "hermes_capability_policy_duplicate_plugin_ids"
    if any(not activation.plugin_id.strip() for activation in policy.plugin_activations):
        return "hermes_capability_policy_empty_plugin_id"
    activation_toolsets: list[str] = []
    for activation in policy.plugin_activations:
        if not activation.toolsets:
            return "hermes_capability_policy_empty_plugin_toolsets"
        activation_toolsets.extend(activation.toolsets)
    if len(activation_toolsets) != len(set(activation_toolsets)):
        return "hermes_capability_policy_duplicate_plugin_toolsets"
    if set(activation_toolsets) != set(policy.enabled_toolsets):
        return "hermes_capability_policy_plugin_toolset_mismatch"
    names = list(policy.enabled_tool_names)
    if len(names) != len(set(names)):
        return "hermes_capability_policy_duplicate_tool_names"
    rule_names = [rule.tool_name for rule in policy.tool_rules]
    if len(rule_names) != len(set(rule_names)):
        return "hermes_capability_policy_duplicate_tool_rules"
    if set(rule_names) != set(names):
        return "hermes_capability_policy_rule_name_mismatch"
    if len(policy.tool_rules) != len(names):
        return "hermes_capability_policy_rule_count_mismatch"
    enabled_toolsets = set(policy.enabled_toolsets)
    for rule in policy.tool_rules:
        if rule.toolset not in enabled_toolsets:
            return "hermes_capability_policy_rule_toolset_mismatch"
        if not rule.allowed_effects:
            return "hermes_capability_policy_empty_effects"
        if rule.require_graph_scope and "read" not in rule.allowed_effects:
            return "hermes_capability_policy_graph_read_required"
    return None


def set_graph_root_override(root: Path | None) -> Any:
    """Set the ContextVar token for an optional World Graph root override."""
    return _graph_root_override.set(root)


def reset_graph_root_override(token: Any) -> None:
    """Reset the ContextVar token from :func:`set_graph_root_override`."""
    _graph_root_override.reset(token)


def set_active_capability_policy(policy: HermesCapabilityPolicy | None) -> Any:
    """Bind the active capability policy for the current turn."""
    return _active_capability_policy.set(policy)


def reset_active_capability_policy(token: Any) -> None:
    """Reset the capability-policy ContextVar token."""
    _active_capability_policy.reset(token)


def get_active_capability_policy() -> HermesCapabilityPolicy | None:
    """Return the active capability policy, if any."""
    return _active_capability_policy.get()


def _policy_denied_error(*, code: str, message: str) -> str:
    return json.dumps(
        {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "code": code,
            "message": message,
            "statusCode": 403,
            "diagnostics": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def apply_capability_policy_to_arguments(
    tool_name: str,
    args: Mapping[str, Any] | None,
    *,
    policy: HermesCapabilityPolicy | None = None,
    effect: ToolEffect = "read",
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate/inject scope from the active (or supplied) capability policy.

    Returns ``(payload, None)`` on success or ``(None, error_json)`` on denial.
    """
    active = policy if policy is not None else _active_capability_policy.get()
    if active is None:
        return None, _policy_denied_error(
            code="hermes_capability_policy_missing",
            message="No active Hermes capability policy for this tool dispatch.",
        )

    if tool_name not in active.enabled_tool_names:
        return None, _policy_denied_error(
            code="hermes_tool_not_permitted",
            message=f"Tool {tool_name!r} is not permitted by the capability policy.",
        )

    rule = active.rule_for(tool_name)
    if rule is None:
        return None, _policy_denied_error(
            code="hermes_tool_rule_missing",
            message=f"Tool {tool_name!r} has no capability rule.",
        )

    if effect not in rule.allowed_effects:
        return None, _policy_denied_error(
            code="hermes_tool_effect_denied",
            message=f"Effect {effect!r} is not permitted for tool {tool_name!r}.",
        )

    payload = dict(args) if isinstance(args, Mapping) else {}
    if rule.require_graph_scope:
        scope = active.graph_scope
        # Authoritative inject — model-supplied scope cannot override the turn.
        payload["worldId"] = scope.world_id
        payload["campaignId"] = scope.campaign_id
        payload["focus"] = dict(scope.focus)
        payload["admissibility"] = scope.admissibility
        payload["revisionPin"] = scope.revision_pin
    if tool_name == PROPOSE_CANVAS_BLOCK_TOOL_NAME:
        canvas = _active_canvas_work_object.get()
        # Authoritative inject — model cannot invent document identity.
        payload["documentId"] = canvas.document_id if canvas else ""
        payload["surfaceId"] = canvas.surface_id if canvas else ""
        payload["expectedContentSha256"] = (
            canvas.expected_content_sha256 if canvas else None
        )
        payload.pop("document_id", None)
        payload.pop("surface_id", None)
        payload.pop("expected_content_sha256", None)
    session_id = _active_retrieval_session_id.get()
    if session_id and tool_name in HERMES_GRAPH_SESSION_TOOL_NAMES:
        # Authoritative session inject — model cannot retarget another session.
        # Wire form is camelCase (aliases on Expand/Read request models).
        payload["retrievalSessionId"] = session_id
        payload.pop("retrieval_session_id", None)
    return payload, None


def _effect_for_tool(tool_name: str, rule: HermesToolCapabilityRule) -> ToolEffect:
    if "write" in rule.allowed_effects and "read" not in rule.allowed_effects:
        return "write"
    if tool_name == PROPOSE_CANVAS_BLOCK_TOOL_NAME and "write" in rule.allowed_effects:
        return "write"
    return "read"


def _handler_for(tool_name: str):
    def _handler(args: dict, **kwargs: Any) -> str:
        del kwargs
        try:
            active = _active_capability_policy.get()
            rule = active.rule_for(tool_name) if active is not None else None
            effect: ToolEffect = (
                _effect_for_tool(tool_name, rule) if rule is not None else "read"
            )
            payload, denied = apply_capability_policy_to_arguments(
                tool_name,
                args,
                effect=effect,
            )
            if denied is not None:
                return denied
            assert payload is not None
            result_json = execute_hermes_graph_interaction_tool_json(
                tool_name,
                payload,
                root=_graph_root_override.get(),
            )
            if tool_name == PROPOSE_CANVAS_BLOCK_TOOL_NAME:
                try:
                    parsed = json.loads(result_json)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    record_pending_canvas_mutation(parsed)
            return result_json
        except Exception:
            # Adapter already fail-closes; this is a last line of defense so
            # Hermes never sees a raised exception from a graph tool.
            return (
                '{"schema":"dmb_world_graph_retrieval_error_v1",'
                '"code":"hermes_graph_interaction_tool_error",'
                '"message":"Hermes graph interaction tool failed unexpectedly.",'
                '"statusCode":500,'
                '"diagnostics":[]}'
            )

    _handler.__name__ = f"handle_{tool_name}"
    _handler.__qualname__ = f"handle_{tool_name}"
    return _handler


def register(ctx: Any) -> None:
    """Register model-visible graph + answer-scope tools with Hermes."""
    definitions = hermes_model_visible_tool_definitions()
    names = [item["function"]["name"] for item in definitions]
    if tuple(names) != ORDERED_MODEL_VISIBLE_TOOL_NAMES:
        raise RuntimeError(
            "Model-visible catalog order drifted from ORDERED_MODEL_VISIBLE_TOOL_NAMES"
        )
    graph_names = [name for name in names if name in HERMES_GRAPH_INTERACTION_TOOL_NAMES]
    if set(graph_names) != set(HERMES_GRAPH_INTERACTION_TOOL_NAMES) or len(
        graph_names
    ) != len(HERMES_GRAPH_INTERACTION_TOOL_NAMES):
        raise RuntimeError(
            "Interaction catalog names drifted from HERMES_GRAPH_INTERACTION_TOOL_NAMES"
        )
    if tuple(graph_names) != ORDERED_GRAPH_TOOL_NAMES:
        raise RuntimeError(
            "Interaction catalog order drifted from ORDERED_GRAPH_TOOL_NAMES"
        )

    for item in definitions:
        function_schema = copy.deepcopy(item["function"])
        name = function_schema["name"]
        description = str(function_schema.get("description") or "")
        ctx.register_tool(
            name=name,
            toolset=TOOLSET_NAME,
            schema=function_schema,
            handler=_handler_for(name),
            description=description,
        )


__all__ = [
    "DECLARE_CONVERSATION_CONTEXT_TOOL_NAME",
    "HERMES_GRAPH_READ_TOOL_NAMES",
    "ORDERED_GRAPH_TOOL_NAMES",
    "ORDERED_MODEL_VISIBLE_TOOL_NAMES",
    "TOOLSET_NAME",
    "HermesCapabilityPolicy",
    "HermesCanvasWorkObject",
    "HermesGraphScope",
    "HermesPluginActivation",
    "HermesToolCapabilityRule",
    "ToolEffect",
    "apply_capability_policy_to_arguments",
    "begin_pending_canvas_mutations",
    "default_graph_only_capability_policy",
    "get_active_capability_policy",
    "get_active_canvas_work_object",
    "get_active_retrieval_session_id",
    "record_pending_canvas_mutation",
    "register",
    "reset_active_capability_policy",
    "reset_active_canvas_work_object",
    "reset_active_retrieval_session_id",
    "reset_graph_root_override",
    "reset_pending_canvas_mutations",
    "set_active_capability_policy",
    "set_active_canvas_work_object",
    "set_active_retrieval_session_id",
    "set_graph_root_override",
    "take_pending_canvas_mutations",
    "validate_capability_policy_structure",
]
