"""Packaged Hermes plugin: graph-only World Graph read tools (PR010B Rung 3).

Registers exactly five tools under toolset ``dungeonbuddy_graph``, deriving each
schema from the Rung 2 catalog and routing every handler to the Rung 2 JSON
adapter. Active capability policy is enforced at dispatch (scope inject /
allowlist), not only in model-facing prose. No legacy retrieval path.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.services.hermes_graph_read_tool_adapter import (
    execute_hermes_graph_read_tool_json,
    hermes_graph_read_tool_definitions,
)
from apps.live_control_server.services.hermes_graph_read_tools import (
    HERMES_GRAPH_READ_TOOL_NAMES,
)

TOOLSET_NAME = "dungeonbuddy_graph"

ToolEffect = Literal["read", "write"]

ORDERED_GRAPH_TOOL_NAMES: tuple[str, ...] = (
    "search_campaign_graph",
    "get_campaign_object",
    "get_object_neighborhood",
    "get_object_evidence",
    "read_source_anchor",
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


@dataclass(frozen=True, slots=True)
class HermesGraphScope:
    """Immutable authoritative graph scope for a turn."""

    world_id: str
    campaign_id: str
    focus: Mapping[str, Any]
    admissibility: str
    revision_pin: str | None = None


@dataclass(frozen=True, slots=True)
class HermesToolCapabilityRule:
    """Per-tool constraints within a capability policy."""

    tool_name: str
    require_graph_scope: bool = True
    allowed_effects: frozenset[ToolEffect] = field(
        default_factory=lambda: frozenset({"read"})
    )


@dataclass(frozen=True, slots=True)
class HermesCapabilityPolicy:
    """Caller-supplied capability boundary for an embedded Hermes turn.

    PR #352 configures this as graph-only / five-tool / read-only. Future
    non-graph tools may appear here with their own scope rules; the runtime
    must not hard-code “exactly five forever” outside of the default factory.
    """

    enabled_toolsets: tuple[str, ...]
    enabled_tool_names: tuple[str, ...]
    graph_scope: HermesGraphScope
    tool_rules: tuple[HermesToolCapabilityRule, ...]

    def rule_for(self, tool_name: str) -> HermesToolCapabilityRule | None:
        for rule in self.tool_rules:
            if rule.tool_name == tool_name:
                return rule
        return None


def default_graph_only_capability_policy(
    scope: HermesGraphScope,
) -> HermesCapabilityPolicy:
    """Default PR010B Rung 3 policy: five graph reads, graph scope required."""
    names = tuple(ORDERED_GRAPH_TOOL_NAMES)
    return HermesCapabilityPolicy(
        enabled_toolsets=(TOOLSET_NAME,),
        enabled_tool_names=names,
        graph_scope=scope,
        tool_rules=tuple(
            HermesToolCapabilityRule(
                tool_name=name,
                require_graph_scope=True,
                allowed_effects=frozenset({"read"}),
            )
            for name in names
        ),
    )


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
    return payload, None


def _handler_for(tool_name: str):
    def _handler(args: dict, **kwargs: Any) -> str:
        del kwargs
        try:
            payload, denied = apply_capability_policy_to_arguments(tool_name, args)
            if denied is not None:
                return denied
            assert payload is not None
            return execute_hermes_graph_read_tool_json(
                tool_name,
                payload,
                root=_graph_root_override.get(),
            )
        except Exception:
            # Adapter already fail-closes; this is a last line of defense so
            # Hermes never sees a raised exception from a graph tool.
            return (
                '{"schema":"dmb_world_graph_retrieval_error_v1",'
                '"code":"hermes_graph_read_tool_adapter_error",'
                '"message":"Hermes graph-read tool adapter failed unexpectedly.",'
                '"statusCode":500,'
                '"diagnostics":[]}'
            )

    _handler.__name__ = f"handle_{tool_name}"
    _handler.__qualname__ = f"handle_{tool_name}"
    return _handler


def register(ctx: Any) -> None:
    """Register the five PR010A graph-read tools with Hermes."""
    definitions = hermes_graph_read_tool_definitions()
    names = [item["function"]["name"] for item in definitions]
    if set(names) != set(HERMES_GRAPH_READ_TOOL_NAMES) or len(names) != len(
        HERMES_GRAPH_READ_TOOL_NAMES
    ):
        raise RuntimeError(
            "Rung 2 catalog names drifted from HERMES_GRAPH_READ_TOOL_NAMES"
        )
    if tuple(names) != ORDERED_GRAPH_TOOL_NAMES:
        raise RuntimeError("Rung 2 catalog order drifted from ORDERED_GRAPH_TOOL_NAMES")

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
    "ORDERED_GRAPH_TOOL_NAMES",
    "TOOLSET_NAME",
    "HermesCapabilityPolicy",
    "HermesGraphScope",
    "HermesToolCapabilityRule",
    "ToolEffect",
    "apply_capability_policy_to_arguments",
    "default_graph_only_capability_policy",
    "get_active_capability_policy",
    "register",
    "reset_active_capability_policy",
    "reset_graph_root_override",
    "set_active_capability_policy",
    "set_graph_root_override",
]
