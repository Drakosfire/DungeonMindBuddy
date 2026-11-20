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
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.services.graph_tool_transport import (
    GraphToolPageCache,
    PAGED_TOOLS,
    PAGE_BYTES,
    TransportScope,
)

from apps.live_control_server.services.hermes_graph_interaction_tools import (
    DECLARE_CONVERSATION_CONTEXT_TOOL_NAME,
    HERMES_GRAPH_INTERACTION_TOOL_NAMES,
    PROPOSE_BUILD_INSERTION,
    ORDERED_INTERACTION_TOOL_NAMES,
    ORDERED_MODEL_VISIBLE_TOOL_NAMES,
    QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
    READ_RELATED_RECAP_CONTEXT_TOOL_NAME,
    execute_hermes_graph_interaction_tool_json,
    hermes_model_visible_tool_definitions,
)

from application_state.agent_conversation.rules_authority_policy import (
    RulesCapabilityV1, LOOKUP_RULES, RULES_READ_POLICY_ID,
    WORLD_GRAPH_RULES_READ_POLICY_ID, LookupRulesArguments, rules_tool_definition,
)

TOOLSET_NAME = "dungeonbuddy_graph"

ToolEffect = Literal["read", "write"]

ORDERED_GRAPH_TOOL_NAMES: tuple[str, ...] = ORDERED_INTERACTION_TOOL_NAMES
HERMES_GRAPH_READ_TOOL_NAMES = HERMES_GRAPH_INTERACTION_TOOL_NAMES

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

_active_rules_call_id: ContextVar[str | None] = ContextVar("rules_model_call_id", default=None)


def set_active_rules_call_id(call_id: str | None) -> None:
    _active_rules_call_id.set(call_id if isinstance(call_id, str) and call_id.strip() and len(call_id) <= 128 else None)


def get_active_rules_call_id() -> str | None:
    return _active_rules_call_id.get()


_active_parent_graph_broker: ContextVar[Any | None] = ContextVar(
    "hermes_graph_plugin_parent_broker", default=None
)
_parent_graph_broker_required: ContextVar[bool] = ContextVar(
    "hermes_graph_plugin_parent_broker_required", default=False
)
_parent_retrieval_session_packet: ContextVar[Mapping[str, Any] | None] = ContextVar(
    "hermes_graph_plugin_parent_retrieval_packet", default=None
)


@dataclass(frozen=True, slots=True)
class HermesGraphScope:
    """Immutable authoritative graph scope for a turn."""

    world_id: str
    campaign_id: str
    focus: Mapping[str, Any]
    admissibility: str
    revision_pin: str | None = None
    scope_mode: Literal["campaign", "world"] = "campaign"


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
    require_rules_authority: bool = False
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
    graph_scope: HermesGraphScope | None
    tool_rules: tuple[HermesToolCapabilityRule, ...]
    plugin_activations: tuple[HermesPluginActivation, ...]
    mode: Literal["graph", "conversation_only", "rules", "graph_rules"] = "graph"
    rules_capability: RulesCapabilityV1 | None = None

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
    """Default policy: declare scope + expand + source-read over one shared session."""
    graph_names = tuple(
        name
        for name in ORDERED_GRAPH_TOOL_NAMES
        if name not in {
            QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
            READ_RELATED_RECAP_CONTEXT_TOOL_NAME,
        }
    )
    names = tuple(
        name for name in ORDERED_MODEL_VISIBLE_TOOL_NAMES
        if name not in {READ_RELATED_RECAP_CONTEXT_TOOL_NAME, PROPOSE_BUILD_INSERTION, "prepare_build_image",
            "search_retained_source_sections", "browse_native_source_sections", "read_native_source_sections"}
    )
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


def rules_capability_policy(capability: RulesCapabilityV1, *,
                            graph_policy: HermesCapabilityPolicy | None = None) -> HermesCapabilityPolicy:
    capability = RulesCapabilityV1.model_validate(capability)
    graph = graph_policy is not None
    if capability.policy_id != (WORLD_GRAPH_RULES_READ_POLICY_ID if graph else RULES_READ_POLICY_ID):
        raise ValueError("Rules capability mode differs from Graph admission")
    rule = HermesToolCapabilityRule(tool_name=LOOKUP_RULES, require_graph_scope=False,
        require_rules_authority=True, allowed_effects=frozenset({"read"}))
    if graph:
        if validate_capability_policy_structure(graph_policy) is not None or graph_policy.mode != "graph":
            raise ValueError("Rules composition requires a valid independent Graph policy")
        return replace(graph_policy, mode="graph_rules", rules_capability=capability,
            enabled_tool_names=(*graph_policy.enabled_tool_names, LOOKUP_RULES),
            tool_rules=(*graph_policy.tool_rules, rule))
    return HermesCapabilityPolicy(enabled_toolsets=(TOOLSET_NAME,), enabled_tool_names=(LOOKUP_RULES,),
        graph_scope=None, tool_rules=(rule,), mode="rules", rules_capability=capability,
        plugin_activations=(HermesPluginActivation(plugin_id=TOOLSET_NAME, toolsets=(TOOLSET_NAME,)),))


def default_conversation_only_capability_policy() -> HermesCapabilityPolicy:
    """No World authority and no tools: a plain conversational model turn."""
    return HermesCapabilityPolicy(
        enabled_toolsets=(),
        enabled_tool_names=(),
        graph_scope=None,
        tool_rules=(),
        plugin_activations=(),
        mode="conversation_only",
    )


def parent_brokered_graph_expansion_policy(
    scope: HermesGraphScope,
) -> HermesCapabilityPolicy:
    """Expose only parent-brokered expansion for metadata-only Plan grounding."""
    policy = default_graph_only_capability_policy(scope)
    names = ("expand_graph_retrieval",)
    rules = tuple(policy.rule_for(name) for name in names)
    if any(rule is None for rule in rules):
        raise ValueError("Graph interaction rule is not present in the plugin catalog")
    return replace(
        policy,
        enabled_tool_names=names,
        tool_rules=rules,
    )


def parent_brokered_graph_source_policy(scope: HermesGraphScope) -> HermesCapabilityPolicy:
    """Expose parent-brokered expansion and source reading for a V2 Plan turn."""
    policy = default_graph_only_capability_policy(scope)
    names = ("expand_graph_retrieval", "read_graph_source")
    rules = tuple(policy.rule_for(name) for name in names)
    if any(rule is None for rule in rules):
        raise ValueError("Graph interaction rule is not present in the plugin catalog")
    return replace(policy, enabled_tool_names=names, tool_rules=rules)


def set_active_retrieval_session_id(session_id: str | None) -> Any:
    return _active_retrieval_session_id.set(session_id)


def reset_active_retrieval_session_id(token: Any) -> None:
    _active_retrieval_session_id.reset(token)


def set_parent_graph_broker(broker: Any | None, *, required: bool) -> tuple[Any, Any, Any]:
    return (
        _active_parent_graph_broker.set(broker),
        _parent_graph_broker_required.set(required),
        _parent_retrieval_session_packet.set(None),
    )


def reset_parent_graph_broker(tokens: tuple[Any, Any]) -> None:
    broker_token, required_token, packet_token = tokens
    _parent_retrieval_session_packet.reset(packet_token)
    _active_parent_graph_broker.reset(broker_token)
    _parent_graph_broker_required.reset(required_token)


def get_parent_retrieval_session_packet() -> Mapping[str, Any] | None:
    return _parent_retrieval_session_packet.get()


def get_active_retrieval_session_id() -> str | None:
    return _active_retrieval_session_id.get()


def validate_capability_policy_structure(
    policy: HermesCapabilityPolicy,
) -> str | None:
    """Fail-closed structural checks before Hermes agent construction.

    Returns an error code string, or ``None`` when the policy is well-formed.
    """
    if policy.mode == "conversation_only":
        if (
            policy.graph_scope is not None
            or policy.rules_capability is not None
            or policy.plugin_activations
            or policy.enabled_toolsets
            or policy.enabled_tool_names
            or policy.tool_rules
        ):
            return "hermes_conversation_policy_has_capabilities"
        return None
    if policy.mode not in {"graph", "rules", "graph_rules"}:
        return "hermes_capability_policy_mode_invalid"
    if (policy.mode in {"graph", "graph_rules"}) != (policy.graph_scope is not None):
        return "hermes_capability_policy_graph_scope_required"
    rules_enabled = policy.mode in {"rules", "graph_rules"}
    if rules_enabled != (policy.rules_capability is not None):
        return "hermes_capability_policy_rules_authority_required"
    if rules_enabled:
        try:
            cap = RulesCapabilityV1.model_validate(policy.rules_capability)
        except ValueError:
            return "hermes_capability_policy_rules_authority_invalid"
        expected = WORLD_GRAPH_RULES_READ_POLICY_ID if policy.mode == "graph_rules" else RULES_READ_POLICY_ID
        if cap.policy_id != expected or LOOKUP_RULES not in policy.enabled_tool_names:
            return "hermes_capability_policy_rules_authority_invalid"
    if policy.mode == "rules" and policy.enabled_tool_names != (LOOKUP_RULES,):
        return "hermes_rules_policy_has_foreign_tools"
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
        if type(rule.require_graph_scope) is not bool or type(rule.require_rules_authority) is not bool:
            return "hermes_capability_policy_invalid_authority_flags"
        if rule.tool_name == LOOKUP_RULES:
            if (not rules_enabled or not rule.require_rules_authority or rule.require_graph_scope
                    or rule.allowed_effects != frozenset({"read"}) or rule.toolset != TOOLSET_NAME):
                return "hermes_capability_policy_rules_rule_invalid"
        elif rule.require_rules_authority:
            return "hermes_capability_policy_rules_rule_invalid"
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
    _graph_page_cache.set(GraphToolPageCache() if policy is not None else None)
    return _active_capability_policy.set(policy)


def reset_active_capability_policy(token: Any) -> None:
    """Reset the capability-policy ContextVar token."""
    _active_capability_policy.reset(token)
    _graph_page_cache.set(None)


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
    if tool_name == LOOKUP_RULES:
        if (validate_capability_policy_structure(active) is not None
                or not rule.require_rules_authority or active.rules_capability is None):
            return None, _policy_denied_error(code="rules_authority_required", message="Rules authority is unavailable.")
        try:
            payload = LookupRulesArguments.model_validate(payload).model_dump(mode="json")
        except ValueError:
            return None, _policy_denied_error(code="rules_arguments_invalid", message="Invalid rules lookup arguments.")
    if rule.require_graph_scope:
        scope = active.graph_scope
        # Authoritative inject — model-supplied scope cannot override the turn.
        payload["worldId"] = scope.world_id
        payload["campaignId"] = scope.campaign_id
        payload["scopeMode"] = scope.scope_mode
        payload["focus"] = dict(scope.focus)
        payload["admissibility"] = scope.admissibility
        payload["revisionPin"] = scope.revision_pin
    session_id = _active_retrieval_session_id.get()
    if session_id and tool_name in HERMES_GRAPH_INTERACTION_TOOL_NAMES:
        # Authoritative session inject — model cannot retarget another session.
        # Wire form is camelCase (aliases on Expand/Read request models).
        payload["retrievalSessionId"] = session_id
        payload.pop("retrieval_session_id", None)
    return payload, None


_graph_page_cache: ContextVar[GraphToolPageCache | None] = ContextVar(
    "graph_page_cache", default=None
)


def _handler_for(tool_name: str):
    def _handler(args: dict, **kwargs: Any) -> str:
        del kwargs
        try:
            payload, denied = apply_capability_policy_to_arguments(tool_name, args,
                effect="write" if tool_name in {PROPOSE_BUILD_INSERTION, "prepare_build_image"} else "read")
            if denied is not None:
                return denied
            assert payload is not None
            if tool_name == LOOKUP_RULES:
                broker = _active_parent_graph_broker.get()
                if not _parent_graph_broker_required.get() or not callable(broker):
                    return _policy_denied_error(code="rules_broker_unavailable", message="No authorized parent Rules broker is available.")
                call_id = get_active_rules_call_id()
                if call_id is None:
                    return _policy_denied_error(code="rules_call_identity_required", message="Rules lookup has no actual model call identity.")
                raw, _ = broker(tool_name, payload)
                from application_state.agent_conversation.rules_authority_packet import RulesPacketV1, RulesBudgetDiagnosticV1
                from application_state.agent_conversation.rules_authority_events import normalized_question
                if len(raw.encode("utf-8")) > 65536:
                    raise ValueError("Rules packet exceeds its transport budget")
                data = json.loads(raw)
                if data.get("schema") == "dmb_rules_budget_diagnostic_v1":
                    packet = RulesBudgetDiagnosticV1.model_validate_json(raw)
                    if packet.call_id != call_id or len(raw.encode()) > 1024:
                        raise ValueError("Rules diagnostic differs from current call")
                else:
                    packet = RulesPacketV1.model_validate_json(raw)
                    cap = get_active_capability_policy().rules_capability
                    if (packet.call_id != call_id or packet.corpus_sha256 != cap.corpus_sha256
                            or packet.ruleset_id != cap.ruleset_id
                            or packet.normalized_question != normalized_question(payload["question"])):
                        raise ValueError("Rules packet differs from admitted source/query/call")
                return raw
            if tool_name in {"search_retained_source_sections","browse_native_source_sections","read_native_source_sections"}:
                broker = _active_parent_graph_broker.get()
                if not _parent_graph_broker_required.get() or not callable(broker):
                    return _policy_denied_error(code="native_source_broker_required",message="Native source sections require the current parent owner.")
                if get_active_rules_call_id() is None:
                    return _policy_denied_error(code="native_source_call_identity_required",message="Source navigation has no actual model call identity.")
                return broker(tool_name,payload)[0]
            if tool_name in {PROPOSE_BUILD_INSERTION, "prepare_build_image"}:
                broker = _active_parent_graph_broker.get()
                if not _parent_graph_broker_required.get() or not callable(broker):
                    return _policy_denied_error(code="build_insertion_broker_unavailable", message="No parent authoring capability is available.")
                return broker(tool_name, payload)[0]
            if _parent_graph_broker_required.get():
                if tool_name not in PAGED_TOOLS:
                    return _policy_denied_error(code="plan_graph_tool_not_permitted",
                        message="Only parent-brokered Graph interactions are permitted.")
                broker = _active_parent_graph_broker.get()
                if not callable(broker):
                    return _policy_denied_error(code="plan_graph_broker_unavailable",
                        message="Parent Graph-operation broker is unavailable.")
                result_json, retrieval_packet = broker(tool_name, payload)
                if isinstance(retrieval_packet, Mapping):
                    _parent_retrieval_session_packet.set(dict(retrieval_packet))
                # Parent owns pagination and delivered evidence membership.
                return result_json
            cache = _graph_page_cache.get()
            policy = get_active_capability_policy()
            scope = None
            if tool_name in PAGED_TOOLS and cache is not None and policy is not None:
                session_id = get_active_retrieval_session_id()
                graph_scope = policy.graph_scope
                if session_id and graph_scope is not None:
                    scope = TransportScope(
                        session_id, graph_scope.world_id, graph_scope.revision_pin
                    )
                    packet = get_parent_retrieval_session_packet()
                    if packet is not None:
                        snapshot = packet.get("snapshot", {})
                        if (
                            packet.get("retrieval_session_id") != session_id
                            or snapshot.get("world_id", snapshot.get("worldId"))
                            != scope.world_id
                            or snapshot.get("revision_id", snapshot.get("revisionId"))
                            != scope.revision_id
                        ):
                            return _policy_denied_error(
                                code="graph_page_scope_conflict",
                                message="Frozen Graph packet differs from active scope.",
                            )
                    page = cache.continuation(tool_name, payload, scope)
                    if page is not None:
                        return page
                elif "resultPageToken" in payload:
                    return _policy_denied_error(
                        code="graph_page_scope_unavailable",
                        message="Active Graph scope unavailable.",
                    )
            if "resultPageToken" in payload and scope is None:
                return _policy_denied_error(
                    code="graph_page_scope_unavailable",
                    message="Active Graph scope unavailable.",
                )
            clean_payload = {k: v for k, v in payload.items() if k != "resultPageToken"}
            result_json = execute_hermes_graph_interaction_tool_json(
                tool_name, clean_payload, root=_graph_root_override.get()
            )
            if scope is not None and cache is not None:
                return cache.present(tool_name, payload, scope, result_json)
            if tool_name in PAGED_TOOLS and len(result_json.encode()) > PAGE_BYTES:
                return _policy_denied_error(
                    code="graph_page_scope_unavailable",
                    message="Active Graph scope required for this oversized result.",
                )
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
    graph_names = [
        name for name in names if name in HERMES_GRAPH_INTERACTION_TOOL_NAMES
    ]
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

    policy = get_active_capability_policy()
    if policy is not None and policy.rules_capability is not None:
        if validate_capability_policy_structure(policy) is not None:
            raise ValueError("Invalid Rules capability at plugin registration")
        definitions.append(rules_tool_definition())

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
    "ORDERED_GRAPH_TOOL_NAMES",
    "ORDERED_MODEL_VISIBLE_TOOL_NAMES",
    "TOOLSET_NAME",
    "HermesCapabilityPolicy",
    "HermesGraphScope",
    "HermesPluginActivation",
    "HermesToolCapabilityRule",
    "ToolEffect",
    "apply_capability_policy_to_arguments",
    "default_conversation_only_capability_policy",
    "default_graph_only_capability_policy",
    "parent_brokered_graph_expansion_policy",
    "parent_brokered_graph_source_policy",
    "get_active_capability_policy",
    "get_active_retrieval_session_id",
    "register",
    "reset_active_capability_policy",
    "reset_active_retrieval_session_id",
    "reset_graph_root_override",
    "set_active_capability_policy",
    "set_active_retrieval_session_id",
    "set_graph_root_override",
    "validate_capability_policy_structure",
]
