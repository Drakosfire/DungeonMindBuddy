"""PydanticAI adapter for the DungeonBuddy AgentRuntime port.

A3 challenger experiment: translates ``AgentRuntimeInvocation`` onto a
PydanticAI Agent loop and maps the result back. Does not resolve World scope,
create retrieval sessions, validate grounding, or finalize A0 traces.
Production code must not instantiate this adapter automatically.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pydantic_ai import Agent, Tool
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import Model
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.usage import RequestUsage

from apps.live_control_server.services.agent_runtime import (
    UNSUPPORTED_CAPABILITY_POLICY,
    WORLD_GRAPH_READ_POLICY_ID,
    AgentRuntimeDescriptor,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
    AgentRuntimeToolEvent,
)
from apps.live_control_server.services.agent_turn_trace import (
    estimate_model_call_cost,
    new_call_id,
    utc_now_z,
)
from apps.live_control_server.services.hermes_graph_agent import (
    _resolve_hermes_openai_inference,
    _safe_ids_from_args,
    _summarize_tool_result,
)
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    DECLARE_CONVERSATION_CONTEXT_TOOL_NAME,
    ORDERED_INTERACTION_TOOL_NAMES,
    ORDERED_MODEL_VISIBLE_TOOL_NAMES,
    QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME,
    execute_hermes_graph_interaction_tool_json,
    hermes_model_visible_tool_definitions,
)

PYDANTIC_AI_RUNTIME_DESCRIPTOR = AgentRuntimeDescriptor(
    runtime_id="pydantic_ai",
    trace_backend="pydantic_ai",
    trace_runtime="in_process",
    trace_mode="pydantic_ai_graph_agent",
)

PROVIDER_ERROR = "pydantic_ai_provider_error"
RUN_ERROR = "pydantic_ai_run_error"
CREDENTIALS_MISSING = "pydantic_ai_openai_credentials_missing"
GRAPH_SESSION_TOOLS = frozenset({"expand_graph_retrieval", "read_graph_source"})
MODEL_CALL_SCHEMA = "dmb_agent_model_call_v1"

ModelFactory = Callable[[str], Model]
ToolExecutor = Callable[..., str]


def map_pydantic_ai_usage(usage: RequestUsage | None) -> dict[str, Any]:
    """Map PydanticAI RequestUsage onto A0 fields without double-counting cache.

    PydanticAI ``input_tokens`` already includes cached input. Cache-read tokens
    are a subset, not an extra prompt bucket.
    """
    if usage is None or not usage.has_values():
        return {"status": "unavailable"}
    input_tokens = int(usage.input_tokens)
    cache_read = int(usage.cache_read_tokens)
    cache_write = int(usage.cache_write_tokens)
    output_tokens = int(usage.output_tokens)
    mapped: dict[str, Any] = {
        "status": "reported",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cached_input_tokens": cache_read,
        "cache_write_input_tokens": cache_write,
        "uncached_input_tokens": max(0, input_tokens - cache_read - cache_write),
    }
    details = usage.details or {}
    reasoning = details.get("reasoning_tokens")
    if isinstance(reasoning, int):
        mapped["reasoning_tokens"] = reasoning
    return mapped


def pydantic_ai_model_visible_tools() -> list[Tool[None]]:
    """Translate existing DMB JSON tool definitions. Used by tests for schema equality."""
    return [
        Tool.from_schema(
            function=_unused_schema_probe,
            name=str(item["function"]["name"]),
            description=str(item["function"].get("description") or ""),
            json_schema=dict(item["function"]["parameters"]),
        )
        for item in hermes_model_visible_tool_definitions()
    ]


def _unused_schema_probe(**_kwargs: Any) -> str:
    return "{}"


def model_visible_tool_names() -> tuple[str, ...]:
    return tuple(tool.name for tool in pydantic_ai_model_visible_tools())


def model_visible_json_schemas() -> dict[str, dict[str, Any]]:
    return {
        str(item["function"]["name"]): dict(item["function"]["parameters"])
        for item in hermes_model_visible_tool_definitions()
    }


def map_conversation_history(
    history: Sequence[Mapping[str, str]] | None,
) -> list[ModelRequest | ModelResponse]:
    messages: list[ModelRequest | ModelResponse] = []
    if not history:
        return messages
    for item in history:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "")
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


def inject_authoritative_tool_args(
    tool_name: str,
    model_args: Mapping[str, Any],
    invocation: AgentRuntimeInvocation,
) -> dict[str, Any]:
    args = dict(model_args)
    scope = invocation.context_packet.world_scope
    retrieval = invocation.context_packet.retrieval_session
    if tool_name == QUERY_THREAT_MECHANICS_HYDRATION_TOOL_NAME:
        args["worldId"] = scope.world_id
        args["campaignId"] = scope.campaign_id
        args["revisionPin"] = scope.revision_id
        args.pop("world_id", None)
        args.pop("campaign_id", None)
        args.pop("revision_pin", None)
    if tool_name in GRAPH_SESSION_TOOLS and retrieval is not None:
        args["retrievalSessionId"] = retrieval.session_id
        args.pop("retrieval_session_id", None)
    return args


def derive_answer_scope(events: Sequence[AgentRuntimeToolEvent]) -> str | None:
    graph_called = False
    declare_completed = False
    interaction = frozenset(ORDERED_INTERACTION_TOOL_NAMES)
    for event in events:
        if event.tool_name in interaction:
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


def _scope_instructions(invocation: AgentRuntimeInvocation) -> str:
    scope = invocation.context_packet.world_scope
    retrieval = invocation.context_packet.retrieval_session
    payload: dict[str, Any] = {
        "worldId": scope.world_id,
        "campaignId": scope.campaign_id,
        "focus": dict(scope.focus),
        "admissibility": scope.admissibility,
        "revisionPin": scope.revision_id,
        "enabledToolNames": list(ORDERED_MODEL_VISIBLE_TOOL_NAMES),
        "retrievalSessionId": None if retrieval is None else retrieval.session_id,
    }
    if retrieval is not None:
        packet = retrieval.packet
        initial: dict[str, Any] = {
            "candidates": list(packet.get("candidates") or [])[:8],
            "claimLedger": list(packet.get("claim_ledger") or [])[:24],
            "intentHint": packet.get("intent_hint"),
            "availableExpansions": list(packet.get("available_expansions") or []),
        }
        latest = packet.get("latest_recap_change")
        if isinstance(latest, Mapping):
            latest_packet = dict(latest)
            excerpt = latest_packet.pop("admitted_recap_excerpt", None)
            initial["latestRecapChange"] = latest_packet
            if isinstance(excerpt, str) and excerpt.strip():
                initial["admittedRecapExcerpt"] = excerpt.strip()
        payload["initialClaimPacket"] = initial
    return (
        "DungeonBuddy World Graph Agent. Answer only from enabled graph tools "
        "or an explicit conversation-context declaration. Server injects "
        "world/campaign/revision/retrievalSessionId; do not override them. "
        "This runtime is in-process PydanticAI, not a process-isolated Hermes worker.\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _a0_provider_label(system: str) -> str:
    if system in {"openai", "openai-api", "openai-chat"}:
        return "openai-api"
    return system


def _unsupported_policy_result(policy_id: str) -> AgentRuntimeResult:
    return AgentRuntimeResult(
        status="error",
        error_code=UNSUPPORTED_CAPABILITY_POLICY,
        error_message=(
            f"Unsupported Agent capability policy {policy_id!r}; "
            f"expected {WORLD_GRAPH_READ_POLICY_ID!r}."
        ),
        runtime_metadata={"process_isolation": "in_process"},
    )


class _TurnCollector:
    def __init__(self, invocation: AgentRuntimeInvocation) -> None:
        self.invocation = invocation
        self.model_calls: list[dict[str, Any]] = []
        self.tool_events: list[AgentRuntimeToolEvent] = []
        self.warnings: list[str] = []

    def _scope_attributes(self, args: Mapping[str, Any]) -> dict[str, Any]:
        scope = self.invocation.context_packet.world_scope
        return {
            "world_id": scope.world_id,
            "campaign_id": scope.campaign_id,
            "focus": dict(scope.focus),
            "admissibility": scope.admissibility,
            "revision_pin": scope.revision_id,
            "bounded_ids": _safe_ids_from_args(dict(args)),
        }

    def emit_start(self, tool_name: str, args: Mapping[str, Any]) -> None:
        self.tool_events.append(
            AgentRuntimeToolEvent(
                tool_name=tool_name,
                state="start",
                attributes=self._scope_attributes(args),
            )
        )

    def emit_finish(
        self,
        tool_name: str,
        args: Mapping[str, Any],
        *,
        duration_ms: float,
        raw_result: str,
        forced_error: bool = False,
    ) -> None:
        summary = _summarize_tool_result(raw_result)
        state = "error" if forced_error or summary["is_error"] else "completion"
        attributes = self._scope_attributes(args)
        attributes.update(
            {
                "retrieval_schema": summary["retrieval_schema"],
                "outcome": summary["outcome"],
                "matched_node_ids": list(summary["matched_node_ids"]),
                "relationship_ids": list(summary["relationship_ids"]),
                "source_anchor_ids": list(summary["source_anchor_ids"]),
                "diagnostic_codes": list(summary["diagnostic_codes"]),
            }
        )
        self.tool_events.append(
            AgentRuntimeToolEvent(
                tool_name=tool_name,
                state=state,
                duration_ms=duration_ms,
                attributes=attributes,
            )
        )

    def record_model_call(
        self,
        *,
        status: str,
        started_at: str,
        duration_ms: float,
        requested_model: str,
        response_model: str | None,
        usage: RequestUsage | None,
        provider: str,
        error_type: str | None = None,
        message_count: int | None = None,
        finish_reason: str | None = None,
        runtime_api_request_id: str | None = None,
    ) -> None:
        mapped_usage = map_pydantic_ai_usage(usage if status == "ok" else None)
        cost = estimate_model_call_cost(
            model=response_model or requested_model,
            usage=mapped_usage,
        )
        if status != "ok":
            mapped_usage = {"status": "unavailable"}
            cost = {"status": "unavailable"}
        sequence = len(self.model_calls) + 1
        call: dict[str, Any] = {
            "schema": MODEL_CALL_SCHEMA,
            "call_id": new_call_id(),
            "sequence": sequence,
            "status": status,
            "provider": provider,
            "requested_model": requested_model,
            "response_model": response_model,
            "started_at": started_at,
            "completed_at": utc_now_z(),
            "duration_ms": max(0, int(duration_ms)),
            "request_summary": {},
            "usage": mapped_usage,
            "cost": cost,
        }
        if message_count is not None:
            call["request_summary"]["message_count"] = message_count
        if finish_reason:
            call["finish_reason"] = finish_reason
        if runtime_api_request_id:
            call["runtime_api_request_id"] = runtime_api_request_id
        if error_type:
            call["error_type"] = error_type
        self.model_calls.append(call)


class ObservingModel(WrapperModel):
    """Record every ``Model.request`` as one A0 model-call observation."""

    def __init__(self, wrapped: Model, collector: _TurnCollector) -> None:
        super().__init__(wrapped)
        self._collector = collector

    async def request(
        self,
        messages: list[Any],
        model_settings: Any,
        model_request_parameters: Any,
    ) -> ModelResponse:
        started_at = utc_now_z()
        t0 = time.perf_counter()
        provider = _a0_provider_label(self.system)
        try:
            response = await super().request(
                messages, model_settings, model_request_parameters
            )
        except Exception as exc:
            self._collector.record_model_call(
                status="error",
                started_at=started_at,
                duration_ms=(time.perf_counter() - t0) * 1000.0,
                requested_model=self.model_name,
                response_model=None,
                usage=None,
                provider=provider,
                error_type=type(exc).__name__,
                message_count=len(messages),
            )
            raise
        self._collector.record_model_call(
            status="ok",
            started_at=started_at,
            duration_ms=(time.perf_counter() - t0) * 1000.0,
            requested_model=self.model_name,
            response_model=response.model_name or self.model_name,
            usage=response.usage,
            provider=provider,
            message_count=len(messages),
            finish_reason=None if response.finish_reason is None else str(response.finish_reason),
            runtime_api_request_id=response.provider_response_id,
        )
        return response


def _default_openai_model(model_id: str) -> Model:
    from pydantic_ai.models.openai import OpenAIModel

    return OpenAIModel(model_id, provider="openai")


def _make_tool(
    *,
    definition: Mapping[str, Any],
    invocation: AgentRuntimeInvocation,
    collector: _TurnCollector,
    executor: ToolExecutor,
    root: Any,
) -> Tool[None]:
    function = definition["function"]
    tool_name = str(function["name"])

    def handler(**kwargs: Any) -> str:
        collector.emit_start(tool_name, kwargs)
        t0 = time.perf_counter()
        args = inject_authoritative_tool_args(tool_name, kwargs, invocation)
        try:
            raw = executor(tool_name, args, root=root)
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            payload = json.dumps(
                {
                    "schema": "dmb_world_graph_retrieval_error_v1",
                    "code": "pydantic_ai_tool_error",
                    "message": f"PydanticAI graph tool failed: {exc}",
                    "statusCode": 500,
                    "diagnostics": [],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            collector.emit_finish(
                tool_name,
                args,
                duration_ms=duration_ms,
                raw_result=payload,
                forced_error=True,
            )
            return payload
        if not isinstance(raw, str):
            raw = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        duration_ms = (time.perf_counter() - t0) * 1000.0
        collector.emit_finish(tool_name, args, duration_ms=duration_ms, raw_result=raw)
        return raw

    handler.__name__ = f"pydantic_ai_{tool_name}"
    handler.__qualname__ = handler.__name__
    return Tool.from_schema(
        function=handler,
        name=tool_name,
        description=str(function.get("description") or ""),
        json_schema=dict(function["parameters"]),
    )


class PydanticAIAgentRuntimeAdapter:
    """In-process PydanticAI implementation of ``AgentRuntime``."""

    def __init__(
        self,
        *,
        model_factory: ModelFactory | None = None,
        tool_executor: ToolExecutor | None = None,
        resolved_model_id: str | None = None,
    ) -> None:
        self.descriptor: AgentRuntimeDescriptor = PYDANTIC_AI_RUNTIME_DESCRIPTOR
        self._model_factory = model_factory
        self._tool_executor = tool_executor or execute_hermes_graph_interaction_tool_json
        self._resolved_model_id = resolved_model_id

    def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
        policy_id = invocation.capability_policy.policy_id
        if policy_id != WORLD_GRAPH_READ_POLICY_ID:
            return _unsupported_policy_result(policy_id)

        if self._model_factory is None:
            resolved = _resolve_hermes_openai_inference(require_api_key=True)
            if isinstance(resolved, str):
                return AgentRuntimeResult(
                    status="error",
                    error_code=CREDENTIALS_MISSING,
                    error_message="OpenAI credentials are missing for the PydanticAI challenger.",
                    runtime_metadata={"process_isolation": "in_process"},
                )
            _provider, model_id, _base_url = resolved
            wrapped = _default_openai_model(model_id)
        else:
            model_id = self._resolved_model_id or "gpt-5.4-mini"
            wrapped = self._model_factory(model_id)

        collector = _TurnCollector(invocation)
        observing = ObservingModel(wrapped, collector)
        root = invocation.run_options.execution_root
        tools = [
            _make_tool(
                definition=definition,
                invocation=invocation,
                collector=collector,
                executor=self._tool_executor,
                root=root,
            )
            for definition in hermes_model_visible_tool_definitions()
        ]
        agent = Agent(
            model=observing,
            tools=tools,
            instructions=_scope_instructions(invocation),
            builtin_tools=(),
            retries=0,
            name="dmb-pydantic-ai-graph-agent",
        )
        history = map_conversation_history(invocation.conversation_history)
        try:
            run_result = agent.run_sync(
                invocation.message,
                message_history=history,
            )
        except Exception as exc:
            return AgentRuntimeResult(
                status="error",
                error_code=PROVIDER_ERROR if collector.model_calls else RUN_ERROR,
                error_message=str(exc) or type(exc).__name__,
                runtime_session_id=None,
                answer_scope=derive_answer_scope(collector.tool_events),
                tool_events=list(collector.tool_events),
                model_calls=list(collector.model_calls),
                telemetry_warnings=list(collector.warnings),
                observed_model_call_count=len(collector.model_calls),
                context_updates=_context_updates(invocation),
                runtime_metadata={"process_isolation": "in_process"},
            )

        output = run_result.output
        final_text = output if isinstance(output, str) else str(output)
        return AgentRuntimeResult(
            status="ok",
            final_text=final_text,
            runtime_session_id=None,
            answer_scope=derive_answer_scope(collector.tool_events),
            tool_events=list(collector.tool_events),
            model_calls=list(collector.model_calls),
            telemetry_warnings=list(collector.warnings),
            observed_model_call_count=len(collector.model_calls),
            context_updates=_context_updates(invocation),
            runtime_metadata={"process_isolation": "in_process"},
        )


def _context_updates(invocation: AgentRuntimeInvocation) -> dict[str, Any]:
    retrieval = invocation.context_packet.retrieval_session
    if retrieval is None:
        return {}
    return {"retrieval_session_id": retrieval.session_id}


def default_pydantic_ai_agent_runtime() -> PydanticAIAgentRuntimeAdapter:
    """Explicit factory for tests/local injection. Production must not call this."""
    return PydanticAIAgentRuntimeAdapter()
