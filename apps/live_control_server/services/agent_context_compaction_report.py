"""Bounded Hermes compaction observations, not source/citation authority."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.services.agent_conversation_context import (
    ROUTE_MARKER, ConversationContext, _question,
)


class _ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VisibleMessage(_ReportModel):
    item_id: str
    role: Literal["user", "assistant"]
    text: str


class PriorSourceCandidate(_ReportModel):
    """Observed prior bytes identified by digest; APP must verify provenance."""

    item_id: str
    anchor_id: str
    evidence_ref_id: str | None = None
    source_artifact_id: str | None = None
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    returned_chars: int = Field(ge=1)


class CompactionDecision(_ReportModel):
    item_id: str
    action: Literal["pruned", "compacted", "retained"]
    reason_code: Literal["route_preserved", "superseded", "question_relevance"]


class ContextCompactionReport(_ReportModel):
    schema_version: Literal["dmb_context_compaction_report_v1"] = "dmb_context_compaction_report_v1"
    policy_version: Literal["conversation_routes_v1"] = "conversation_routes_v1"
    before_visible: list[VisibleMessage] = Field(max_length=512)
    after_visible: list[VisibleMessage] = Field(max_length=512)
    prior_sources: list[PriorSourceCandidate] = Field(max_length=512)
    routes: dict[str, list[dict[str, str]]]
    decisions: list[CompactionDecision] = Field(max_length=512)
    before_chars: int = Field(ge=0)
    after_chars: int = Field(ge=0)


def compaction_report(history: Sequence[Mapping[str, Any]], compacted: ConversationContext) -> ContextCompactionReport:
    """Project the actual deterministic compactor's inputs/output without prompts.

    Source prose is never copied into this transport. Its hash is only a lookup
    candidate for an earlier exact APP snapshot, not a verified historical ref.
    Oversized reports fail explicitly rather than silently dropping context.
    """
    def visible(messages: Sequence[Mapping[str, Any]]) -> list[VisibleMessage]:
        rows = []
        for index, message in enumerate(messages):
            role, content = message.get("role"), message.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str) or not content:
                continue
            if content.startswith(ROUTE_MARKER) or message.get("tool_calls"):
                continue
            rows.append(VisibleMessage(item_id=f"message:{index}", role=role,
                                       text=_question(content) if role == "user" else content))
        return rows

    sources = []
    def source(result: Any, item_id: str) -> None:
        if not isinstance(result, dict):
            return
        if result.get("schema") == "dmb_read_graph_source_batch_v1":
            for index, read in enumerate(result.get("reads", [])):
                source(read, f"{item_id}:read:{index}")
            return
        text, anchor = result.get("content"), result.get("anchorId")
        if (result.get("schema") != "dmb_world_graph_source_anchor_read_v1"
                or result.get("outcome") not in {"enough", "partial", "truncated"}
                or not isinstance(text, str) or not text or not isinstance(anchor, str) or not anchor):
            return
        sources.append(PriorSourceCandidate(
            item_id=item_id, anchor_id=anchor,
            evidence_ref_id=result.get("evidenceRefId"), source_artifact_id=result.get("sourceArtifactId"),
            content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), returned_chars=len(text),
        ))

    for index, message in enumerate(history):
        if message.get("role") != "tool" or not isinstance(message.get("content"), str):
            continue
        try:
            source(json.loads(message["content"]), f"message:{index}")
        except json.JSONDecodeError:
            continue
    actions = {"prune": "pruned", "compact": "compacted", "retain": "retained"}
    reasons = {
        "previous_tool_output_replaced_by_recoverable_routes": "route_preserved",
        "previous_tool_calls_are_not_current_turn_admission": "superseded",
        "current_turn_supplies_plan_basis": "superseded",
        "visible_conversation_knowledge": "question_relevance",
    }
    report = ContextCompactionReport(
        before_visible=visible(history), after_visible=visible(compacted.messages), prior_sources=sources,
        routes=compacted.routes, before_chars=compacted.before_chars, after_chars=compacted.after_chars,
        decisions=[CompactionDecision(item_id=f"message:{item['message_index']}",
                                     action=actions[item["action"]], reason_code=reasons[item["reason"]])
                   for item in compacted.decisions],
    )
    if len(report.model_dump_json().encode("utf-8")) > 1_048_576:
        raise ValueError("context compaction report exceeds its explicit 1 MiB transport limit")
    return report
