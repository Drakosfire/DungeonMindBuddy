from __future__ import annotations

import json
import os
import shutil
import subprocess
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
from src.bootstrap_env import load_dungeonmindbuddy_dotenv

LIVE_QUERY_BACKENDS = frozenset({"live", "hermes"})
HERMES_CLI_MODE_ENV = "DUNGEONMIND_LIVE_HERMES_MODE"
HERMES_CLI_TIMEOUT_ENV = "DUNGEONMIND_LIVE_HERMES_TIMEOUT_SECONDS"
HERMES_CLI_MODEL_ENV = "DUNGEONMIND_LIVE_HERMES_MODEL"
HERMES_CLI_PROVIDER_ENV = "DUNGEONMIND_LIVE_HERMES_PROVIDER"
HERMES_CLI_BASE_URL_ENV = "DUNGEONMIND_LIVE_HERMES_BASE_URL"


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
    query_backend: str = "live",
) -> dict[str, Any]:
    session_base = base or session_dir()
    repo = root or repo_root()
    packet, _layout, _events, _jobs = load_session(session_base)

    if query_backend == "hermes":
        return _process_hermes_context_query(
            text,
            packet=packet,
            request_manifest_path=request_manifest_path,
        )
    if query_backend not in LIVE_QUERY_BACKENDS:
        raise ValueError(f"unsupported query backend: {query_backend}")

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


def _citations_from_context_packet(context_packet: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for row in list(context_packet.get("admitted_evidence") or []):
        citations.append(
            {
                "evidence_id": str(row.get("evidence_id") or ""),
                "path": str(row.get("path") or ""),
                "line_start": row.get("line_start") if isinstance(row.get("line_start"), int) else None,
                "line_end": row.get("line_end") if isinstance(row.get("line_end"), int) else None,
                "source_role": str(row.get("source_role") or ""),
                "authority": str(row.get("authority") or ""),
            }
        )
    return citations


def _process_hermes_context_query(
    text: str,
    *,
    packet: dict[str, Any],
    request_manifest_path: str | None,
) -> dict[str, Any]:
    if os.getenv(HERMES_CLI_MODE_ENV, "").strip().lower() == "cli":
        return _process_hermes_cli_query(
            text,
            packet=packet,
            request_manifest_path=request_manifest_path,
        )

    from integrations.hermes.plugins.dungeonbuddy import handle_dungeon_context_lookup

    params: dict[str, Any] = {
        "question": text,
        "question_id": f"hermes-live-query-{uuid.uuid4().hex[:12]}",
    }
    if request_manifest_path:
        params["manifest_path"] = request_manifest_path

    raw = handle_dungeon_context_lookup(params)
    data = json.loads(raw)
    if not data.get("success"):
        return {
            "schema": "dmb_live_query_response_v1",
            "query_id": params["question_id"],
            "session": int(packet["session"]),
            "mode": "hermes_context_lookup",
            "status": "error",
            "answer": str(data.get("error") or "Hermes context lookup failed."),
            "classification": {
                "latency_mode": "context_lookup",
                "event_type": "context_question",
                "intent": "hermes_context_lookup",
            },
            "events_written": [],
            "jobs_queued": [],
            "next_suggestions": [],
            "diagnostics": data,
            "provenance": {"mode": "hermes_context_lookup", "backend": "hermes"},
            "citations": [],
            "context_packet": None,
            "warnings": ["Hermes context lookup failed."],
            "mutations": [],
        }

    context_packet = dict(data.get("context_packet") or {})
    summary = dict(data.get("sufficiency_summary") or {})
    answerable = bool(summary.get("answerable_now"))
    answer = (
        "Hermes returned enough manifest-backed context. Review admitted evidence before final GM-facing synthesis."
        if answerable
        else "Hermes needs follow-up source reads before a grounded answer. Review suggested routes."
    )

    return {
        "schema": "dmb_live_query_response_v1",
        "query_id": str(data.get("question_id") or params["question_id"]),
        "session": int(packet["session"]),
        "mode": "hermes_context_lookup",
        "status": "ok",
        "answer": answer,
        "classification": {
            "latency_mode": "context_lookup",
            "event_type": "context_question",
            "intent": "hermes_context_lookup",
        },
        "events_written": [],
        "jobs_queued": [],
        "next_suggestions": list(summary.get("suggested_routes") or []),
        "diagnostics": {
            "hermes_tool": "dungeon_context_lookup",
            "sufficiency_summary": summary,
        },
        "provenance": {
            "mode": "hermes_context_lookup",
            "backend": "hermes",
            "manifest_path": data.get("manifest_path"),
        },
        "citations": _citations_from_context_packet(context_packet),
        "context_packet": context_packet,
        "warnings": [],
        "mutations": [],
    }


def _hermes_cli_timeout_seconds() -> int:
    raw = os.getenv(HERMES_CLI_TIMEOUT_ENV, "").strip()
    if not raw:
        return 180
    try:
        return max(1, int(raw))
    except ValueError:
        return 180


def _process_hermes_cli_query(
    text: str,
    *,
    packet: dict[str, Any],
    request_manifest_path: str | None,
) -> dict[str, Any]:
    query_id = f"hermes-cli-query-{uuid.uuid4().hex[:12]}"
    hermes_bin = shutil.which("hermes")
    if not hermes_bin:
        return _hermes_cli_error_response(
            query_id=query_id,
            packet=packet,
            error="hermes executable not found on PATH.",
            diagnostics={"backend": "hermes_cli"},
        )

    repo = repo_root()
    load_dungeonmindbuddy_dotenv()
    env = os.environ.copy()
    env.setdefault("HERMES_HOME", str(repo / ".hermes-runtime"))
    env.setdefault("DUNGEONBUDDY_REPO", str(repo))
    env.setdefault("DUNGEONBUDDY_CORPUS_ROOT", str(repo / "corpus"))
    env.setdefault("OPENROUTER_BASE_URL", os.getenv(HERMES_CLI_BASE_URL_ENV, "https://api.openai.com/v1"))

    provider = os.getenv(HERMES_CLI_PROVIDER_ENV, "custom").strip() or "custom"
    model = os.getenv(HERMES_CLI_MODEL_ENV, "gpt-5.4-mini").strip() or "gpt-5.4-mini"
    prompt = (
        "Use the DungeonBuddy corpus tools to answer the operator question. "
        "Keep the answer brief, grounded, and cite no raw corpus excerpts. "
        "Question: "
        f"{text}"
    )
    if request_manifest_path:
        prompt += f"\nUse manifest path if a DungeonBuddy tool asks for one: {request_manifest_path}"

    try:
        completed = subprocess.run(
            [
                hermes_bin,
                "--provider",
                provider,
                "--model",
                model,
                "--toolsets",
                "dungeonbuddy",
                "--oneshot",
                prompt,
            ],
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=_hermes_cli_timeout_seconds(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _hermes_cli_error_response(
            query_id=query_id,
            packet=packet,
            error="Hermes CLI query timed out.",
            diagnostics={"backend": "hermes_cli", "timeout_seconds": _hermes_cli_timeout_seconds()},
        )

    output = completed.stdout.strip()
    if completed.returncode != 0:
        return _hermes_cli_error_response(
            query_id=query_id,
            packet=packet,
            error=output or f"Hermes CLI exited with {completed.returncode}.",
            diagnostics={"backend": "hermes_cli", "returncode": completed.returncode},
        )

    return {
        "schema": "dmb_live_query_response_v1",
        "query_id": query_id,
        "session": int(packet["session"]),
        "mode": "hermes_cli_oneshot",
        "status": "ok",
        "answer": output,
        "classification": {
            "latency_mode": "context_lookup",
            "event_type": "context_question",
            "intent": "hermes_cli_oneshot",
        },
        "events_written": [],
        "jobs_queued": [],
        "next_suggestions": [],
        "diagnostics": {
            "hermes_toolset": "dungeonbuddy",
            "provider": provider,
            "model": model,
        },
        "provenance": {
            "mode": "hermes_cli_oneshot",
            "backend": "hermes",
            "runtime": "cli",
        },
        "citations": [],
        "context_packet": None,
        "warnings": ["Hermes CLI one-shot returned synthesized text without a context packet."],
        "mutations": [],
    }


def _hermes_cli_error_response(
    *,
    query_id: str,
    packet: dict[str, Any],
    error: str,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "dmb_live_query_response_v1",
        "query_id": query_id,
        "session": int(packet["session"]),
        "mode": "hermes_cli_oneshot",
        "status": "error",
        "answer": error,
        "classification": {
            "latency_mode": "context_lookup",
            "event_type": "context_question",
            "intent": "hermes_cli_oneshot",
        },
        "events_written": [],
        "jobs_queued": [],
        "next_suggestions": [],
        "diagnostics": diagnostics,
        "provenance": {
            "mode": "hermes_cli_oneshot",
            "backend": "hermes",
            "runtime": "cli",
        },
        "citations": [],
        "context_packet": None,
        "warnings": ["Hermes CLI query failed."],
        "mutations": [],
    }
