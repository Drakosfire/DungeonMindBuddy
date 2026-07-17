"""Non-secret forensic envelope for Hermes graph dogfood instrumentation."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any

from graph_memory.interaction.schema_constants import FORENSIC_ENVELOPE_SCHEMA

FORENSIC_ENV_FLAG = "DMB_HERMES_GRAPH_FORENSIC"
MAX_RAW_RESULT_CHARS = 4000
MAX_DIAGNOSTICS = 32


def forensic_enabled() -> bool:
    value = (os.environ.get(FORENSIC_ENV_FLAG) or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _clip(text: str, *, max_chars: int = MAX_RAW_RESULT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def extract_anchor_states(raw_result: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_result, str):
        return []
    try:
        parsed = json.loads(raw_result)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, Mapping):
        return []
    anchors = parsed.get("sourceAnchors") or []
    if not isinstance(anchors, list):
        # Source-read result shape.
        anchor_id = parsed.get("anchorId")
        if isinstance(anchor_id, str) and anchor_id:
            return [
                {
                    "anchor_id": anchor_id,
                    "readable": parsed.get("outcome") in {"enough", "partial", "truncated"},
                    "opened": parsed.get("content") is not None,
                    "locator_kind": parsed.get("locatorKind"),
                }
            ]
        return []
    states: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        anchor_id = anchor.get("anchorId") or anchor.get("id")
        if not isinstance(anchor_id, str) or not anchor_id:
            continue
        states.append(
            {
                "anchor_id": anchor_id,
                "readable": bool(anchor.get("readable") is True),
                "opened": False,
                "locator_kind": anchor.get("locatorKind"),
            }
        )
    return states[:MAX_DIAGNOSTICS]


def extract_claim_ids(raw_result: Any) -> list[str]:
    if not isinstance(raw_result, str):
        return []
    try:
        parsed = json.loads(raw_result)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, Mapping):
        return []
    ids: list[str] = []
    for attribute in parsed.get("attributes") or []:
        if isinstance(attribute, Mapping) and attribute.get("assertionId"):
            ids.append(str(attribute["assertionId"]))
    for rel in parsed.get("relationships") or []:
        if isinstance(rel, Mapping) and rel.get("edgeId"):
            ids.append(str(rel["edgeId"]))
    for node in parsed.get("nodes") or []:
        if isinstance(node, Mapping) and node.get("nodeId"):
            ids.append(f"identity:{node['nodeId']}")
    return list(dict.fromkeys(ids))[:MAX_DIAGNOSTICS]


def summarize_raw_result_for_forensic(raw_result: Any) -> dict[str, Any]:
    if not isinstance(raw_result, str):
        return {
            "result_type": type(raw_result).__name__,
            "parseable_json": False,
            "result_schema": None,
            "outcome": None,
            "byte_length": 0,
            "preview": None,
        }
    preview = _clip(raw_result)
    try:
        parsed = json.loads(raw_result)
        parseable = isinstance(parsed, Mapping)
        schema = parsed.get("schema") if parseable else None
        outcome = parsed.get("outcome") if parseable else None
    except json.JSONDecodeError:
        parseable = False
        schema = None
        outcome = None
    return {
        "result_type": "str",
        "parseable_json": parseable,
        "result_schema": schema,
        "outcome": outcome,
        "byte_length": len(raw_result.encode("utf-8", errors="replace")),
        "preview": preview if forensic_enabled() else None,
    }


def build_tool_forensic_event(
    *,
    call_id: str | None,
    tool: str,
    state: str,
    raw_result: Any = None,
    outcome: str | None = None,
    result_schema: str | None = None,
    diagnostic_codes: Sequence[str] | None = None,
) -> dict[str, Any]:
    anchor_states = extract_anchor_states(raw_result) if state == "completion" else []
    claim_ids = extract_claim_ids(raw_result) if state == "completion" else []
    raw_summary = summarize_raw_result_for_forensic(raw_result)
    return {
        "call_id": call_id,
        "tool": tool,
        "state": state,
        "result_schema": result_schema or raw_summary.get("result_schema"),
        "outcome": outcome or raw_summary.get("outcome"),
        "claim_ids": claim_ids,
        "anchor_states": anchor_states,
        "diagnostics": list(diagnostic_codes or [])[:MAX_DIAGNOSTICS],
        "raw_result": raw_summary,
    }


def classify_runtime_branch(
    *,
    tool_events: Sequence[Mapping[str, Any]],
    acceptance_state: str,
) -> str:
    """Narrow the canned-abstention forensic branch."""
    completions = [e for e in tool_events if e.get("state") == "completion"]
    starts = [e for e in tool_events if e.get("state") == "start"]
    if not starts and not completions:
        return "no_tool"
    if starts and not completions:
        return "no_completion"
    has_anchors = any(
        (e.get("source_anchor_ids") or e.get("sourceAnchorIds") or e.get("anchor_states"))
        for e in completions
    )
    if not has_anchors:
        return "no_anchors"
    malformed = any(
        (e.get("raw_result") or {}).get("parseable_json") is False for e in completions
    )
    if malformed:
        return "malformed_completion"
    return f"accepted_{acceptance_state}"


def build_forensic_envelope(
    *,
    retrieval_session_id: str | None,
    preflight_candidate_ids: Sequence[str],
    agent_seed_ids: Sequence[str],
    tool_events: Sequence[Mapping[str, Any]],
    acceptance: Mapping[str, Any],
) -> dict[str, Any]:
    state = str(acceptance.get("state") or "unknown")
    return {
        "schema": FORENSIC_ENVELOPE_SCHEMA,
        "retrieval_session_id": retrieval_session_id,
        "preflight_candidate_ids": list(preflight_candidate_ids),
        "agent_seed_ids": list(agent_seed_ids),
        "tool_events": list(tool_events),
        "acceptance": dict(acceptance),
        "runtime_branch": classify_runtime_branch(
            tool_events=tool_events,
            acceptance_state=state,
        ),
    }


__all__ = [
    "FORENSIC_ENV_FLAG",
    "build_forensic_envelope",
    "build_tool_forensic_event",
    "classify_runtime_branch",
    "extract_anchor_states",
    "extract_claim_ids",
    "forensic_enabled",
    "summarize_raw_result_for_forensic",
]
