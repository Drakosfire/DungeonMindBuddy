from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
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


def _new_trace_id(prefix: str = "agent-trace") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _new_agent_thread_id() -> str:
    return f"agent-thread-{uuid.uuid4().hex[:12]}"


def _new_turn_id() -> str:
    return f"agent-turn-{uuid.uuid4().hex[:12]}"


def _with_conversation_fields(
    response: dict[str, Any],
    *,
    agent_thread_id: str | None,
    turn_id: str | None,
    hermes_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response["agent_thread_id"] = agent_thread_id
    response["turn_id"] = turn_id
    response["hermes_session"] = hermes_session
    return response


def _estimate_token_count(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // 4)


def _usage_unavailable() -> dict[str, Any]:
    return {
        "available": False,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }


def _usage_from_fields(
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> dict[str, Any]:
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return _usage_unavailable()
    computed_total = total_tokens
    if computed_total is None and input_tokens is not None and output_tokens is not None:
        computed_total = input_tokens + output_tokens
    return {
        "available": True,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": computed_total,
    }


def _context_summary_from_packet(
    context_packet: dict[str, Any] | None,
    *,
    manifest_path: str | None = None,
    sufficiency_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet = context_packet or {}
    summary = sufficiency_summary or {}
    admitted = list(packet.get("admitted_evidence") or [])
    rejected = list(packet.get("rejected_evidence") or [])
    admitted_excerpt_chars = sum(len(str(row.get("text_excerpt") or "")) for row in admitted if isinstance(row, dict))
    rejected_excerpt_chars = sum(
        len(str((row.get("evidence") or {}).get("text_excerpt") or ""))
        for row in rejected
        if isinstance(row, dict) and isinstance(row.get("evidence"), dict)
    )
    return {
        "admitted_count": len(admitted),
        "rejected_count": len(rejected),
        "admitted_excerpt_char_count": admitted_excerpt_chars,
        "admitted_excerpt_token_estimate": _estimate_token_count("x" * admitted_excerpt_chars),
        "rejected_excerpt_char_count": rejected_excerpt_chars,
        "rejected_excerpt_token_estimate": _estimate_token_count("x" * rejected_excerpt_chars),
        "total_excerpt_char_count": admitted_excerpt_chars + rejected_excerpt_chars,
        "total_excerpt_token_estimate": _estimate_token_count("x" * (admitted_excerpt_chars + rejected_excerpt_chars)),
        "context_payload_kind": "manifest_evidence_excerpts",
        "manifest_path": manifest_path,
        "answerable_now": summary.get("answerable_now"),
        "intent_class": packet.get("intent_class"),
        "suggested_route_count": len(list(summary.get("suggested_routes") or [])),
        "verdict": summary.get("verdict"),
    }


def _safe_command_summary(argv: list[str]) -> str:
    parts: list[str] = []
    for index, token in enumerate(argv):
        if token == "--oneshot" and index + 1 < len(argv):
            parts.append("--oneshot")
            parts.append(f"<prompt {len(argv[index + 1])} chars>")
            break
        parts.append(token)
    return " ".join(parts)


def _prompt_context_from_packet(context_packet: dict[str, Any], *, max_evidence: int = 8) -> str:
    admitted = [row for row in list(context_packet.get("admitted_evidence") or []) if isinstance(row, dict)]
    if not admitted:
        return "No admitted evidence excerpts were retrieved by the preflight context lookup."

    blocks: list[str] = []
    for index, row in enumerate(admitted[:max_evidence], start=1):
        excerpt = str(row.get("text_excerpt") or "").strip()
        if not excerpt:
            continue
        path = str(row.get("path") or "")
        source_role = str(row.get("source_role") or "")
        authority = str(row.get("authority") or "")
        line_start = row.get("line_start")
        line_end = row.get("line_end")
        locator = f"lines {line_start}-{line_end}" if isinstance(line_start, int) and isinstance(line_end, int) else "line unknown"
        blocks.append(
            "\n".join(
                [
                    f"[Evidence {index}] {source_role} / {authority} / {locator}",
                    f"Path: {path}",
                    f"Excerpt: {excerpt}",
                ]
            )
        )

    if not blocks:
        return "No admitted evidence excerpts were retrieved by the preflight context lookup."
    return "\n\n".join(blocks)


def _extract_usage_from_session_blob(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("usage", "token_usage", "metrics"):
        candidate = data.get(key)
        if isinstance(candidate, dict):
            input_tokens = candidate.get("input_tokens") or candidate.get("prompt_tokens")
            output_tokens = candidate.get("output_tokens") or candidate.get("completion_tokens")
            total_tokens = candidate.get("total_tokens")
            if any(value is not None for value in (input_tokens, output_tokens, total_tokens)):
                return _usage_from_fields(
                    input_tokens=int(input_tokens) if input_tokens is not None else None,
                    output_tokens=int(output_tokens) if output_tokens is not None else None,
                    total_tokens=int(total_tokens) if total_tokens is not None else None,
                )
    return _usage_unavailable()


def _collect_hermes_home_artifacts(hermes_home: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    artifact_refs: list[dict[str, Any]] = []
    warnings: list[str] = []
    usage = _usage_unavailable()
    if not hermes_home.is_dir():
        warnings.append(f"Hermes home not found: {hermes_home}")
        return artifact_refs, usage, warnings

    sessions_dir = hermes_home / "sessions"
    if sessions_dir.is_dir():
        session_files = sorted(
            [path for path in sessions_dir.iterdir() if path.is_file()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if session_files:
            latest = session_files[0]
            artifact_refs.append(
                {
                    "kind": "hermes_session",
                    "path": str(latest),
                    "label": latest.name,
                }
            )
            try:
                session_blob = json.loads(latest.read_text(encoding="utf-8"))
                if isinstance(session_blob, dict):
                    usage = _extract_usage_from_session_blob(session_blob)
                    for step in list(session_blob.get("tool_calls") or session_blob.get("steps") or [])[:12]:
                        if isinstance(step, dict):
                            artifact_refs.append(
                                {
                                    "kind": "hermes_step",
                                    "path": str(latest),
                                    "label": str(step.get("name") or step.get("tool") or "step"),
                                }
                            )
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                warnings.append("Unable to parse latest Hermes session artifact for usage metadata.")
        else:
            warnings.append("No Hermes session artifacts found under sessions/.")
    else:
        warnings.append("Hermes sessions directory missing; artifact pointers unavailable.")

    logs_dir = hermes_home / "logs"
    if logs_dir.is_dir():
        log_files = sorted(
            [path for path in logs_dir.iterdir() if path.is_file()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if log_files:
            artifact_refs.append(
                {
                    "kind": "hermes_log",
                    "path": str(log_files[0]),
                    "label": log_files[0].name,
                }
            )

    return artifact_refs, usage, warnings


def _build_agent_trace(
    *,
    trace_id: str,
    runtime: str,
    backend: str,
    mode: str,
    status: str,
    started_at: str,
    completed_at: str,
    elapsed_ms: int,
    provider: str | None = None,
    model: str | None = None,
    toolset: str | None = None,
    command_summary: str | None = None,
    prompt_preview: str | None = None,
    prompt_char_count: int | None = None,
    prompt_token_estimate: int | None = None,
    usage: dict[str, Any] | None = None,
    steps: list[dict[str, Any]] | None = None,
    context_summary: dict[str, Any] | None = None,
    artifact_refs: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "runtime": runtime,
        "backend": backend,
        "mode": mode,
        "provider": provider,
        "model": model,
        "started_at": started_at,
        "completed_at": completed_at,
        "elapsed_ms": elapsed_ms,
        "status": status,
        "toolset": toolset,
        "command_summary": command_summary,
        "prompt_preview": prompt_preview,
        "prompt_char_count": prompt_char_count,
        "prompt_token_estimate": prompt_token_estimate,
        "usage": usage or _usage_unavailable(),
        "steps": list(steps or []),
        "context_summary": context_summary or {},
        "artifact_refs": list(artifact_refs or []),
        "warnings": list(warnings or []),
    }


def _hermes_in_process_steps(summary: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        {
            "name": "dungeon_context_lookup",
            "summary": "Hermes in-process DungeonBuddy context lookup",
        }
    ]
    for route in list(summary.get("suggested_routes") or [])[:6]:
        steps.append({"name": "suggested_route", "summary": str(route)})
    return steps


def _run_dungeon_context_lookup_for_cli(
    text: str,
    *,
    question_id: str,
    request_manifest_path: str | None,
) -> dict[str, Any]:
    from integrations.hermes.plugins.dungeonbuddy import handle_dungeon_context_lookup

    params: dict[str, Any] = {"question": text, "question_id": question_id}
    if request_manifest_path:
        params["manifest_path"] = request_manifest_path
    return json.loads(handle_dungeon_context_lookup(params))


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
    agent_thread_id: str | None = None,
    hermes_session_id: str | None = None,
    trace_requested: bool | None = None,
) -> dict[str, Any]:
    session_base = base or session_dir()
    resolved_agent_thread_id = agent_thread_id or _new_agent_thread_id()
    resolved_turn_id = _new_turn_id()
    repo = root or repo_root()
    packet, _layout, _events, _jobs = load_session(session_base)

    if query_backend == "hermes":
        return run_hermes_conversation(
            text,
            packet=packet,
            request_manifest_path=request_manifest_path,
            agent_thread_id=resolved_agent_thread_id,
            turn_id=resolved_turn_id,
            hermes_session_id=hermes_session_id,
            trace_requested=trace_requested,
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
        return _with_conversation_fields(
            context_result.response,
            agent_thread_id=resolved_agent_thread_id,
            turn_id=resolved_turn_id,
        )

    result: LiveTurnResult = handle_live_turn(
        packet,
        text,
        root=repo,
        created_at=_utc_now_z(),
        event_id_factory=_new_event_id,
    )

    append_events_and_jobs(session_base, result.events_to_write, result.jobs_to_queue)
    refresh_current_state(session_base)

    response = {
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
    return _with_conversation_fields(response, agent_thread_id=resolved_agent_thread_id, turn_id=resolved_turn_id)


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


def run_hermes_conversation(
    text: str,
    *,
    packet: dict[str, Any],
    request_manifest_path: str | None,
    agent_thread_id: str | None,
    turn_id: str | None,
    hermes_session_id: str | None = None,
    trace_requested: bool | None = None,
) -> dict[str, Any]:
    response = _process_hermes_context_query(
        text,
        packet=packet,
        request_manifest_path=request_manifest_path,
        hermes_session_id=hermes_session_id,
    )
    hermes_session = None
    if hermes_session_id:
        hermes_session = {
            "sessionId": hermes_session_id,
            "title": None,
            "runtime": (
                response.get("agent_trace", {}).get("runtime", "unknown")
                if isinstance(response.get("agent_trace"), dict)
                else "unknown"
            ),
            "createdAt": None,
            "updatedAt": _utc_now_z(),
        }
    return _with_conversation_fields(response, agent_thread_id=agent_thread_id, turn_id=turn_id, hermes_session=hermes_session)


def _process_hermes_context_query(
    text: str,
    *,
    packet: dict[str, Any],
    request_manifest_path: str | None,
    hermes_session_id: str | None = None,
) -> dict[str, Any]:
    if os.getenv(HERMES_CLI_MODE_ENV, "").strip().lower() == "cli":
        return _process_hermes_cli_query(
            text,
            packet=packet,
            request_manifest_path=request_manifest_path,
            hermes_session_id=hermes_session_id,
        )

    from integrations.hermes.plugins.dungeonbuddy import handle_dungeon_context_lookup

    trace_id = _new_trace_id("hermes-trace")
    started_at = _utc_now_z()
    started_mono = time.monotonic()

    params: dict[str, Any] = {
        "question": text,
        "question_id": f"hermes-live-query-{uuid.uuid4().hex[:12]}",
    }
    if request_manifest_path:
        params["manifest_path"] = request_manifest_path

    raw = handle_dungeon_context_lookup(params)
    data = json.loads(raw)
    completed_at = _utc_now_z()
    elapsed_ms = int((time.monotonic() - started_mono) * 1000)

    if not data.get("success"):
        agent_trace = _build_agent_trace(
            trace_id=trace_id,
            runtime="in_process",
            backend="hermes",
            mode="hermes_context_lookup",
            status="error",
            started_at=started_at,
            completed_at=completed_at,
            elapsed_ms=elapsed_ms,
            toolset="dungeonbuddy",
            prompt_char_count=len(text),
            prompt_token_estimate=_estimate_token_count(text),
            steps=[{"name": "dungeon_context_lookup", "summary": "Lookup failed"}],
            context_summary=_context_summary_from_packet(
                None,
                manifest_path=str(data.get("manifest_path") or request_manifest_path or "") or None,
            ),
            warnings=["Hermes context lookup failed."],
        )
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
            "agent_trace": agent_trace,
        }

    context_packet = dict(data.get("context_packet") or {})
    summary = dict(data.get("sufficiency_summary") or {})
    answerable = bool(summary.get("answerable_now"))
    answer = (
        "Hermes returned enough manifest-backed context. Review admitted evidence before final GM-facing synthesis."
        if answerable
        else "Hermes needs follow-up source reads before a grounded answer. Review suggested routes."
    )
    manifest_path = str(data.get("manifest_path") or request_manifest_path or "") or None
    agent_trace = _build_agent_trace(
        trace_id=trace_id,
        runtime="in_process",
        backend="hermes",
        mode="hermes_context_lookup",
        status="ok",
        started_at=started_at,
        completed_at=completed_at,
        elapsed_ms=elapsed_ms,
        toolset="dungeonbuddy",
        prompt_char_count=len(text),
        prompt_token_estimate=_estimate_token_count(text),
        steps=_hermes_in_process_steps(summary),
        context_summary=_context_summary_from_packet(
            context_packet,
            manifest_path=manifest_path,
            sufficiency_summary=summary,
        ),
        artifact_refs=[
            {
                "kind": "manifest_path",
                "path": manifest_path or "",
                "label": "request manifest",
            }
        ] if manifest_path else [],
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
        "agent_trace": agent_trace,
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
    hermes_session_id: str | None = None,
) -> dict[str, Any]:
    query_id = f"hermes-cli-query-{uuid.uuid4().hex[:12]}"
    trace_id = _new_trace_id("hermes-cli-trace")
    started_at = _utc_now_z()
    started_mono = time.monotonic()
    hermes_bin = shutil.which("hermes")
    if not hermes_bin:
        return _hermes_cli_error_response(
            query_id=query_id,
            packet=packet,
            error="hermes executable not found on PATH.",
            diagnostics={"backend": "hermes_cli"},
            trace_id=trace_id,
            started_at=started_at,
            elapsed_ms=int((time.monotonic() - started_mono) * 1000),
        )

    repo = repo_root()
    load_dungeonmindbuddy_dotenv()
    env = os.environ.copy()
    hermes_home = Path(env.get("HERMES_HOME", str(repo / ".hermes-runtime")))
    env.setdefault("HERMES_HOME", str(hermes_home))
    env.setdefault("DUNGEONBUDDY_REPO", str(repo))
    env.setdefault("DUNGEONBUDDY_CORPUS_ROOT", str(repo / "corpus"))
    env.setdefault("OPENROUTER_BASE_URL", os.getenv(HERMES_CLI_BASE_URL_ENV, "https://api.openai.com/v1"))

    provider = os.getenv(HERMES_CLI_PROVIDER_ENV, "custom").strip() or "custom"
    model = os.getenv(HERMES_CLI_MODEL_ENV, "gpt-5.4-mini").strip() or "gpt-5.4-mini"

    lookup_started_mono = time.monotonic()
    lookup_data = _run_dungeon_context_lookup_for_cli(
        text,
        question_id=f"{query_id}-context",
        request_manifest_path=request_manifest_path,
    )
    lookup_elapsed_ms = int((time.monotonic() - lookup_started_mono) * 1000)
    context_packet = dict(lookup_data.get("context_packet") or {}) if lookup_data.get("success") else {}
    sufficiency_summary = dict(lookup_data.get("sufficiency_summary") or {}) if lookup_data.get("success") else {}
    manifest_path = str(lookup_data.get("manifest_path") or request_manifest_path or "") or None
    context_summary = _context_summary_from_packet(
        context_packet,
        manifest_path=manifest_path,
        sufficiency_summary=sufficiency_summary,
    )
    prompt_context = _prompt_context_from_packet(context_packet)

    resume_warnings: list[str] = []
    if hermes_session_id:
        resume_warnings.append(
            "Hermes CLI resume was requested, but non-interactive resume mechanics are not verified in this build; using one-shot fallback without --resume."
        )

    prompt = (
        "Use the DungeonBuddy corpus tools to answer the operator question. "
        "Keep the answer brief, grounded, and cite no raw corpus excerpts. "
        "The live-control server has already run dungeon_context_lookup; use the retrieved "
        "evidence excerpts below first. If the excerpts are insufficient, say what is missing "
        "or call DungeonBuddy tools for more context rather than guessing. "
        "Question: "
        f"{text}\n\nRetrieved evidence excerpts:\n{prompt_context}"
    )
    if request_manifest_path:
        prompt += f"\nUse manifest path if a DungeonBuddy tool asks for one: {request_manifest_path}"

    argv = [
        hermes_bin,
        "--provider",
        provider,
        "--model",
        model,
        "--toolsets",
        "dungeonbuddy",
        "--oneshot",
        prompt,
    ]
    command_summary = _safe_command_summary(argv)

    try:
        completed = subprocess.run(
            argv,
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
            trace_id=trace_id,
            started_at=started_at,
            elapsed_ms=int((time.monotonic() - started_mono) * 1000),
            provider=provider,
            model=model,
            command_summary=command_summary,
            prompt_char_count=len(prompt),
        )

    completed_at = _utc_now_z()
    elapsed_ms = int((time.monotonic() - started_mono) * 1000)
    output = completed.stdout.strip()
    artifact_refs, usage, artifact_warnings = _collect_hermes_home_artifacts(hermes_home)

    if completed.returncode != 0:
        return _hermes_cli_error_response(
            query_id=query_id,
            packet=packet,
            error=output or f"Hermes CLI exited with {completed.returncode}.",
            diagnostics={"backend": "hermes_cli", "returncode": completed.returncode},
            trace_id=trace_id,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_ms=elapsed_ms,
            provider=provider,
            model=model,
            command_summary=command_summary,
            prompt_char_count=len(prompt),
            artifact_refs=artifact_refs,
            usage=usage,
            artifact_warnings=artifact_warnings,
        )

    warnings: list[str] = list(resume_warnings)
    if not lookup_data.get("success"):
        warnings.append(str(lookup_data.get("error") or "Preflight dungeon_context_lookup failed."))
    if not context_packet:
        warnings.append("Hermes CLI answer has no preflight context packet.")
    warnings.append("Hermes CLI may call additional tools; exact internal tool payloads require Hermes session artifacts.")
    warnings.extend(artifact_warnings)
    steps = [
        {
            "name": "dungeon_context_lookup",
            "summary": (
                f"success={bool(lookup_data.get('success'))} "
                f"elapsed_ms={lookup_elapsed_ms} "
                f"admitted={context_summary.get('admitted_count', 0)} "
                f"rejected={context_summary.get('rejected_count', 0)}"
            ),
        },
        {
            "name": "hermes_cli_oneshot",
            "summary": f"returncode=0 stdout_chars={len(output)}",
        },
    ]
    agent_trace = _build_agent_trace(
        trace_id=trace_id,
        runtime="cli",
        backend="hermes",
        mode="hermes_cli_oneshot",
        status="ok",
        started_at=started_at,
        completed_at=completed_at,
        elapsed_ms=elapsed_ms,
        provider=provider,
        model=model,
        toolset="dungeonbuddy",
        command_summary=command_summary,
        prompt_preview=prompt,
        prompt_char_count=len(prompt),
        prompt_token_estimate=_estimate_token_count(prompt),
        usage=usage,
        steps=steps,
        context_summary=context_summary,
        artifact_refs=artifact_refs,
        warnings=warnings,
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
            "stdout_chars": len(output),
            "returncode": completed.returncode,
            "preflight_context_lookup": {
                "success": bool(lookup_data.get("success")),
                "elapsed_ms": lookup_elapsed_ms,
                "sufficiency_summary": sufficiency_summary,
            },
        },
        "provenance": {
            "mode": "hermes_cli_oneshot",
            "backend": "hermes",
            "runtime": "cli",
        },
        "citations": _citations_from_context_packet(context_packet),
        "context_packet": context_packet or None,
        "warnings": warnings,
        "mutations": [],
        "agent_trace": agent_trace,
    }


def _hermes_cli_error_response(
    *,
    query_id: str,
    packet: dict[str, Any],
    error: str,
    diagnostics: dict[str, Any],
    trace_id: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    elapsed_ms: int | None = None,
    provider: str | None = None,
    model: str | None = None,
    command_summary: str | None = None,
    prompt_char_count: int | None = None,
    artifact_refs: list[dict[str, Any]] | None = None,
    usage: dict[str, Any] | None = None,
    artifact_warnings: list[str] | None = None,
) -> dict[str, Any]:
    resolved_started = started_at or _utc_now_z()
    resolved_completed = completed_at or _utc_now_z()
    resolved_elapsed = elapsed_ms if elapsed_ms is not None else 0
    resolved_trace_id = trace_id or _new_trace_id("hermes-cli-trace")
    warnings = ["Hermes CLI query failed."]
    if artifact_warnings:
        warnings.extend(artifact_warnings)
    agent_trace = _build_agent_trace(
        trace_id=resolved_trace_id,
        runtime="cli",
        backend="hermes",
        mode="hermes_cli_oneshot",
        status="error",
        started_at=resolved_started,
        completed_at=resolved_completed,
        elapsed_ms=resolved_elapsed,
        provider=provider,
        model=model,
        toolset="dungeonbuddy",
        command_summary=command_summary,
        prompt_char_count=prompt_char_count,
        prompt_token_estimate=(
            max(1, prompt_char_count // 4) if prompt_char_count else _estimate_token_count(error)
        ),
        usage=usage or _usage_unavailable(),
        steps=[{"name": "hermes_cli_oneshot", "summary": "CLI query failed"}],
        context_summary={},
        artifact_refs=artifact_refs or [],
        warnings=warnings,
    )
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
        "warnings": warnings,
        "mutations": [],
        "agent_trace": agent_trace,
    }
