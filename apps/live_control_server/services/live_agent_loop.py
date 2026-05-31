from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.live_control_server.config import repo_root, session_dir
from apps.live_control_server.session_store import (
    append_events_and_jobs,
    load_session,
    refresh_current_state,
)
from src.live_play.classify_live_turn import classify_live_turn
from src.live_play.live_query_context import run_context_lookup_turn
from src.live_play.live_turn import LiveTurnResult, handle_live_turn


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_event_id() -> str:
    return f"evt-live-{uuid.uuid4().hex[:12]}"


def _should_route_context_lookup(text: str, event_type: str) -> bool:
    if event_type == "context_question":
        return True
    lowered = text.lower()
    if "?" not in lowered:
        return False
    return any(
        token in lowered
        for token in (
            "what ",
            "how ",
            "which ",
            "session ",
            "outcome",
            "prep",
            "context",
            "evidence",
            "ground",
            "canon",
        )
    )


def process_live_query(
    text: str,
    *,
    base: Path | None = None,
    root: Path | None = None,
    request_manifest_path: str | None = None,
) -> dict[str, Any]:
    session_base = base or session_dir()
    repo = root or repo_root()
    packet, _layout, _events, _jobs = load_session(session_base)

    classification = classify_live_turn(text)
    if _should_route_context_lookup(text, classification.event_type):
        context_result = run_context_lookup_turn(
            question=text,
            classification=classification,
            packet=packet,
            root=repo,
            session=int(packet["session"]),
            request_manifest_path=request_manifest_path,
        )
        return context_result.response

    result: LiveTurnResult = handle_live_turn(
        packet,
        text,
        root=repo,
        created_at=_utc_now_z(),
        event_id_factory=_new_event_id,
    )

    append_events_and_jobs(session_base, result.events_to_write, result.jobs_to_queue)
    refresh_current_state(session_base)

    return {
        "schema": "dmb_live_query_response_v1",
        "query_id": f"live-query-{uuid.uuid4().hex[:12]}",
        "session": int(packet["session"]),
        "mode": "live_turn",
        "status": "ok",
        "answer": result.answer,
        "classification": asdict(result.classification),
        "events_written": [event["id"] for event in result.events_to_write],
        "jobs_queued": [job["id"] for job in result.jobs_to_queue],
        "next_suggestions": result.next_suggestions,
        "diagnostics": result.diagnostics,
        "provenance": result.provenance,
        "citations": [],
        "context_packet": None,
        "warnings": [],
        "mutations": [],
    }
