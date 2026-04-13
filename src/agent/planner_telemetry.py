"""Structured logging for OpenAI Responses planner calls (tokens, latency, I/O previews)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger("dmb.planner")


def planner_log_full_io() -> bool:
    return os.environ.get("PLANNER_LOG_FULL_IO", "").strip().lower() in ("1", "true", "yes")


def text_sig(text: str) -> dict[str, Any]:
    raw = text.encode("utf-8", errors="replace")
    return {
        "chars": len(text),
        "bytes": len(raw),
        "sha256_16": hashlib.sha256(raw).hexdigest()[:16],
    }


def clip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + f"\n...[truncated, total_chars={len(text)}]...\n" + text[-half :]


def maybe_full_text(text: str, *, short_preview: int = 2400) -> str:
    """Full body when ``PLANNER_LOG_FULL_IO``; else short preview for large strings."""
    if planner_log_full_io():
        return clip_text(text, 200_000)
    if len(text) <= short_preview:
        return text
    return clip_text(text, 1200)


def usage_dict_from_response(response: Any) -> dict[str, int]:
    u = getattr(response, "usage", None)
    if not u:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0}
    details = getattr(u, "input_tokens_details", None)
    cached = int(getattr(details, "cached_tokens", 0) or 0) if details is not None else 0
    return {
        "input_tokens": int(getattr(u, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(u, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(u, "total_tokens", 0) or 0),
        "cached_tokens": cached,
    }


def response_extras(response: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for attr in (
        "status",
        "error",
        "temperature",
        "top_p",
        "service_tier",
        "incomplete_details",
        "background",
        "billing",
    ):
        if not hasattr(response, attr):
            continue
        v = getattr(response, attr)
        if v is None:
            continue
        try:
            json.dumps(v)
            out[attr] = v
        except (TypeError, ValueError):
            out[attr] = repr(v)[:800]
    items = getattr(response, "output", None) or []
    try:
        out["output_item_types"] = [getattr(x, "type", type(x).__name__) for x in items]
    except (TypeError, ValueError):
        out["output_item_types"] = []
    return out


def summarize_tool_inputs(tool_inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for t in tool_inputs:
        if not isinstance(t, dict):
            rows.append({"non_dict": str(t)[:300]})
            continue
        out = t.get("output", "")
        oc = len(out) if isinstance(out, str) else None
        rows.append(
            {
                "type": t.get("type"),
                "call_id": t.get("call_id"),
                "output_chars": oc,
                "output_text": maybe_full_text(out) if isinstance(out, str) else None,
            }
        )
    return rows


def log_telemetry(payload: dict[str, Any]) -> None:
    """One JSON line per event under logger ``dmb.planner``."""
    logger.info("[dmb.planner.telemetry] %s", json.dumps(payload, ensure_ascii=False, default=str))
