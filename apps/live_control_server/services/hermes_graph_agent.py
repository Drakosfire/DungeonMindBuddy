"""Embedded Hermes graph-agent turn runtime (PR010B Rung 3).

Constructs a lockdown ``AIAgent`` from a caller-supplied capability policy,
runs one ``run_conversation`` turn, and returns a typed internal result with
ordered safe tool-event summaries. No Live/legacy/subprocess fallback.

Process-global Hermes import / ``HERMES_HOME`` mutation is serialized by an
explicit lock; temporary Hermes homes are deleted in ``finally``.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from graph_memory.hermes_graph_plugin import (
    HermesCapabilityPolicy,
    HermesGraphScope,
    HermesToolCapabilityRule,
    default_graph_only_capability_policy,
    reset_active_capability_policy,
    reset_graph_root_override,
    set_active_capability_policy,
    set_graph_root_override,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_ERROR_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA,
)

HermesGraphAgentStatus = Literal["ok", "error"]
ToolEventState = Literal["start", "completion", "error"]

_RUNTIME_LOCK = threading.RLock()

_GRAPH_SYSTEM_POLICY = """\
You are a campaign-prep assistant for DungeonMindBuddy.

Factual retrieval rules:
- Configured World Graph tools are the sole factual retrieval plane for this turn.
- Every graph tool call MUST use the supplied worldId, campaignId, focus,
  admissibility, and revisionPin from the turn scope below. The runtime also
  enforces that scope at dispatch.
- Source text is readable only through opaque anchorId values returned by graph tools.
- If the graph returns empty, partial, denied, truncated, or unavailable outcomes,
  preserve uncertainty or abstain. Do not invent lore and do not search elsewhere.
- Prior conversation messages resolve intent and pronouns only. They are not
  campaign truth and must not override fresh graph-tool results.

Forbidden:
- Manifest, corpus, Markdown, lexical, filesystem, web, terminal, continuity,
  ambient-memory, or any non-graph factual discovery path.
"""


@contextmanager
def hermes_import_namespace() -> Iterator[None]:
    """Prefer the locked Hermes ``agent`` package over DungeonBuddy ``src/agent``.

    Both projects ship a top-level ``agent`` package. Pytest and the live-control
    pythonpath put ``src`` first, which shadows Hermes. For the duration of a
    Hermes import/turn, site-packages must win and ``sys.modules['agent*']``
    must refer to Hermes modules. The previous modules and path order are
    restored afterward so DungeonBuddy code is unaffected.

    Callers that mutate this process-global state must already hold
    :data:`_RUNTIME_LOCK` (or accept that concurrent turns are unsafe).
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
        # Site-packages first, then the remainder (preserving relative order).
        reordered = [*site_packages, *[p for p in saved_path if p not in site_packages]]
        sys.path[:] = reordered
        yield
    finally:
        sys.path[:] = saved_path
        # Drop Hermes agent modules loaded during the turn.
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
    enabled_toolsets: Sequence[str],
) -> None:
    home.mkdir(parents=True, exist_ok=True)
    config_path = home / "config.yaml"
    config = {
        "plugins": {
            "enabled": list(enabled_toolsets),
            "disabled": [],
        }
    }
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )


def _scope_block(policy: HermesCapabilityPolicy) -> str:
    scope = policy.graph_scope
    payload = {
        "worldId": scope.world_id,
        "campaignId": scope.campaign_id,
        "focus": dict(scope.focus),
        "admissibility": scope.admissibility,
        "revisionPin": scope.revision_pin,
        "enabledToolsets": list(policy.enabled_toolsets),
        "enabledToolNames": list(policy.enabled_tool_names),
    }
    return (
        "Turn capability policy (runtime-enforced; also required on tool calls):\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _safe_ids_from_args(args: Mapping[str, Any]) -> dict[str, Any]:
    bounded: dict[str, Any] = {}
    for key in (
        "nodeId",
        "seedNodeIds",
        "anchorId",
        "queryText",
        "maxDepth",
        "maxChars",
    ):
        if key in args:
            bounded[key] = args[key]
    target = args.get("target")
    if isinstance(target, Mapping):
        bounded["target"] = {
            "kind": target.get("kind"),
            "id": target.get("id"),
        }
    return bounded


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
        summary["matched_node_ids"] = [str(x) for x in matched]
    relationships = parsed.get("relationships") or []
    if isinstance(relationships, list):
        ids: list[str] = []
        for rel in relationships:
            if not isinstance(rel, Mapping):
                continue
            # PR010A serializes ``edgeId`` (not ``id``).
            edge_id = rel.get("edgeId")
            if edge_id is None:
                edge_id = rel.get("id")
            if edge_id is not None:
                ids.append(str(edge_id))
        summary["relationship_ids"] = ids
    # Source-anchor *read* results expose top-level ``anchorId`` and do not
    # populate ``sourceAnchors``. Check that first so an empty list cannot
    # shadow the top-level field.
    if parsed.get("anchorId"):
        summary["source_anchor_ids"] = [str(parsed["anchorId"])]
    else:
        anchors = parsed.get("sourceAnchors") or []
        if isinstance(anchors, list):
            summary["source_anchor_ids"] = [
                str(a.get("anchorId") or a.get("id"))
                for a in anchors
                if isinstance(a, Mapping) and (a.get("anchorId") or a.get("id"))
            ]
    diagnostics = parsed.get("diagnostics") or []
    if isinstance(diagnostics, list):
        summary["diagnostic_codes"] = [
            str(d.get("code"))
            for d in diagnostics
            if isinstance(d, Mapping) and d.get("code")
        ]
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


class _ToolEventCollector:
    def __init__(self) -> None:
        self.events: list[HermesGraphToolEvent] = []
        self._starts: dict[str, float] = {}

    def on_start(
        self,
        tool_call_id: Any,
        tool_name: str,
        args: dict[str, Any] | None = None,
        *_unused: Any,
        **_kwargs: Any,
    ) -> None:
        del tool_call_id, _unused
        started = time.perf_counter()
        args = args if isinstance(args, dict) else {}
        event_index = len(self.events)
        self._starts[str(event_index)] = started
        self.events.append(
            HermesGraphToolEvent(
                tool_name=str(tool_name),
                state="start",
                world_id=str(args["worldId"]) if args.get("worldId") is not None else None,
                campaign_id=(
                    str(args["campaignId"]) if args.get("campaignId") is not None else None
                ),
                focus=dict(args["focus"]) if isinstance(args.get("focus"), Mapping) else None,
                admissibility=(
                    str(args["admissibility"])
                    if args.get("admissibility") is not None
                    else None
                ),
                revision_pin=(
                    str(args["revisionPin"]) if args.get("revisionPin") is not None else None
                ),
                bounded_ids=_safe_ids_from_args(args),
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
        del tool_call_id, _unused
        args = args if isinstance(args, dict) else {}
        # Pair with the most recent start for this tool name when possible.
        started = None
        for idx in range(len(self.events) - 1, -1, -1):
            event = self.events[idx]
            if event.tool_name == str(tool_name) and event.state == "start":
                started = self._starts.get(str(idx))
                break
        duration_ms = (
            (time.perf_counter() - started) * 1000.0 if started is not None else None
        )
        summary = _summarize_tool_result(result)
        state: ToolEventState = "error" if summary["is_error"] else "completion"
        self.events.append(
            HermesGraphToolEvent(
                tool_name=str(tool_name),
                state=state,
                duration_ms=duration_ms,
                world_id=str(args["worldId"]) if args.get("worldId") is not None else None,
                campaign_id=(
                    str(args["campaignId"]) if args.get("campaignId") is not None else None
                ),
                focus=dict(args["focus"]) if isinstance(args.get("focus"), Mapping) else None,
                admissibility=(
                    str(args["admissibility"])
                    if args.get("admissibility") is not None
                    else None
                ),
                revision_pin=(
                    str(args["revisionPin"]) if args.get("revisionPin") is not None else None
                ),
                bounded_ids=_safe_ids_from_args(args),
                retrieval_schema=summary["retrieval_schema"],
                outcome=summary["outcome"],
                matched_node_ids=summary["matched_node_ids"],
                relationship_ids=summary["relationship_ids"],
                source_anchor_ids=summary["source_anchor_ids"],
                diagnostic_codes=summary["diagnostic_codes"],
            )
        )


def run_hermes_graph_agent_turn(
    request: HermesGraphAgentTurnRequest,
    *,
    agent_factory: Any | None = None,
) -> HermesGraphAgentTurnResult:
    """Run one lockdown Hermes graph-agent turn and return a typed result."""
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
    hermes_home = Path(tempfile.mkdtemp(prefix="dmb-hermes-graph-home-"))
    previous_home = os.environ.get("HERMES_HOME")
    root_token = set_graph_root_override(request.root)
    policy_token = set_active_capability_policy(policy)
    collector = _ToolEventCollector()

    with _RUNTIME_LOCK:
        try:
            _prepare_isolated_hermes_home(
                hermes_home,
                enabled_toolsets=policy.enabled_toolsets,
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
                # Keep Hermes's agent package preferred for the duration of the turn.
                with hermes_import_namespace():
                    agent = factory(
                        quiet_mode=True,
                        skip_memory=True,
                        skip_context_files=True,
                        enabled_toolsets=list(policy.enabled_toolsets),
                        session_id=session_id,
                        tool_start_callback=collector.on_start,
                        tool_complete_callback=collector.on_complete,
                        ephemeral_system_prompt=(
                            f"{_GRAPH_SYSTEM_POLICY}\n\n{_scope_block(policy)}"
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

            return HermesGraphAgentTurnResult(
                status="ok",
                final_response=final_response,
                messages=[
                    dict(m) if isinstance(m, Mapping) else {"value": m} for m in messages
                ],
                hermes_session_id=str(raw.get("session_id") or session_id),
                tool_events=list(collector.events),
            )
        except Exception:
            return _error_result(
                hermes_session_id=session_id,
                error_code="hermes_graph_agent_error",
                error_message="Hermes graph-agent runtime failed unexpectedly.",
                tool_events=collector.events,
            )
        finally:
            reset_active_capability_policy(policy_token)
            reset_graph_root_override(root_token)
            if previous_home is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = previous_home
            shutil.rmtree(hermes_home, ignore_errors=True)


__all__ = [
    "HermesCapabilityPolicy",
    "HermesGraphAgentTurnRequest",
    "HermesGraphAgentTurnResult",
    "HermesGraphScope",
    "HermesGraphToolEvent",
    "HermesToolCapabilityRule",
    "hermes_import_namespace",
    "import_hermes_aiagent",
    "run_hermes_graph_agent_turn",
]
