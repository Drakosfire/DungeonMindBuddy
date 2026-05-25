from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.live_play.classify_live_turn import TurnClassification, classify_live_turn
from src.live_play.resolve_roll import ResolvedRoll, RollResolveError, resolve_roll_command
from src.live_play.roll_table_registry import RollTableRegistry

_EVENT_COUNTER = 0


@dataclass(frozen=True)
class LiveTurnResult:
    answer: str
    classification: TurnClassification
    events_to_write: list[dict[str, object]]
    jobs_to_queue: list[dict[str, object]]
    next_suggestions: list[str]
    provenance: dict[str, object]
    diagnostics: list[str]


def _next_event_id(factory: Callable[[], str] | None) -> str:
    global _EVENT_COUNTER
    if factory is not None:
        return factory()
    _EVENT_COUNTER += 1
    return f"evt-live-{_EVENT_COUNTER:04d}"


def _pending_roll_suggestions(packet: dict[str, Any], current_table: str | None) -> list[str]:
    suggestions: list[str] = []
    for row in packet.get("roll_stack", []):
        table_id = row["table_id"]
        if row.get("status") != "pending":
            continue
        if table_id == current_table:
            continue
        suggestions.append(table_id)
    return suggestions[:3]


def _headline_from_row(row_text: str) -> str:
    bold = re.search(r"\*\*([^*]+)\*\*", row_text)
    if bold:
        return bold.group(1).strip()
    return row_text.split("·", 1)[0].strip()[:80]


def _build_event(
    packet: dict[str, Any],
    text: str,
    classification: TurnClassification,
    *,
    created_at: str,
    event_id: str,
    session_clock: str,
    derived_fields: dict[str, object],
    summary: str,
    jobs_to_queue: list[dict[str, object]],
    provenance: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "id": event_id,
        "created_at": created_at,
        "campaign_id": packet["campaign_id"],
        "session": packet["session"],
        "session_clock": session_clock,
        "event_type": classification.event_type,
        "event_origin": "user_input",
        "latency_mode": classification.latency_mode,
        "input_text": text,
        "summary": summary,
        "derived_fields": derived_fields,
        "provenance": provenance,
        "jobs_to_queue": jobs_to_queue,
    }


def handle_live_turn(
    packet: dict[str, Any],
    text: str,
    *,
    root: Path | None = None,
    created_at: str = "2026-05-25T12:00:00Z",
    event_id_factory: Callable[[], str] | None = None,
    session_clock: str | None = None,
) -> LiveTurnResult:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    clock = session_clock or packet.get("current_state_seed", {}).get("day_label", "live")
    classification = classify_live_turn(text)
    diagnostics: list[str] = []
    events: list[dict[str, object]] = []
    jobs: list[dict[str, object]] = []
    provenance: dict[str, object] = {"generated_by": "handle_live_turn", "source_paths": []}

    if classification.event_type == "roll_result":
        registry = RollTableRegistry.from_packet(packet, root)
        command_text = text
        if classification.table_id and classification.roll is not None:
            if classification.table_id == "T-WX":
                command_text = f"Weather {classification.roll}."
            elif classification.table_id == "R5":
                command_text = f"R5 {classification.roll}."
            else:
                command_text = f"{classification.table_id} {classification.roll}."
        try:
            resolved: ResolvedRoll = resolve_roll_command(registry, command_text)
        except RollResolveError as exc:
            return LiveTurnResult(
                answer=f"Could not resolve roll: {exc.diagnostic.message}",
                classification=classification,
                events_to_write=[],
                jobs_to_queue=[],
                next_suggestions=_pending_roll_suggestions(packet, classification.table_id),
                provenance=provenance,
                diagnostics=[exc.diagnostic.code, exc.diagnostic.message],
            )
        headline = _headline_from_row(resolved.row_text)
        answer = f"{resolved.title} ({resolved.table_id} {resolved.roll}): {headline} — {resolved.row_text}"
        derived: dict[str, object] = {
            "table_id": resolved.table_id,
            "roll": resolved.roll,
            "row_locator": resolved.row_locator,
            "headline": headline,
        }
        if classification.skill_check:
            derived["skill_check"] = classification.skill_check
        event_id = _next_event_id(event_id_factory)
        event_jobs = [
            {
                "job_type": "benchmark_candidate",
                "payload": {"source_event_id": event_id},
                "reason": "Live prompt belongs in the Session 22 regression set.",
            }
        ]
        events.append(
            _build_event(
                packet,
                text,
                classification,
                created_at=created_at,
                event_id=event_id,
                session_clock=clock,
                derived_fields=derived,
                summary=f"Resolved {resolved.table_id} roll {resolved.roll}: {headline}.",
                jobs_to_queue=event_jobs,
                provenance=resolved.provenance,
            )
        )
        return LiveTurnResult(
            answer=answer,
            classification=classification,
            events_to_write=events,
            jobs_to_queue=[],
            next_suggestions=_pending_roll_suggestions(packet, resolved.table_id),
            provenance={"resolved_roll": resolved.provenance, "generated_by": "handle_live_turn"},
            diagnostics=diagnostics,
        )

    if classification.event_type == "open_loop_update":
        derived_fields = {
            "loop_id": "grobnok-evening-contact",
            "status": "owed",
            "note": "morning contact did not happen; evening contact still owed",
        }
        summary = "Grobnok did not call in the morning; evening contact remains owed."
        answer = (
            "Logged open-loop update: Grobnok did not call this morning. "
            "Evening contact is still owed on the live stack."
        )
        events.append(
            _build_event(
                packet,
                text,
                classification,
                created_at=created_at,
                event_id=_next_event_id(event_id_factory),
                session_clock=clock,
                derived_fields=derived_fields,
                summary=summary,
                jobs_to_queue=[],
                provenance=provenance,
            )
        )
        return LiveTurnResult(
            answer=answer,
            classification=classification,
            events_to_write=events,
            jobs_to_queue=jobs,
            next_suggestions=["T-WX", "T-NPC", "R5"],
            provenance=provenance,
            diagnostics=diagnostics,
        )

    if classification.event_type == "canon_correction":
        event_id = _next_event_id(event_id_factory)
        jobs = [
            {
                "schema_version": "0.1.0",
                "id": f"job-{event_id}-propagation",
                "created_at": created_at,
                "job_type": "post_session_propagation",
                "status": "queued",
                "payload": {"source_event_id": event_id, "correction": "Lysandro is Lysandra's father"},
                "created_from_event_id": event_id,
                "dependencies": [],
                "provenance": {
                    "source_paths": [],
                    "generated_by": "handle_live_turn",
                    "notes": "Queued for post-session propagation; no inline corpus edit.",
                },
            },
            {
                "schema_version": "0.1.0",
                "id": f"job-{event_id}-review",
                "created_at": created_at,
                "job_type": "manual_review",
                "status": "queued",
                "payload": {"source_event_id": event_id},
                "created_from_event_id": event_id,
                "dependencies": [],
                "provenance": {
                    "source_paths": [],
                    "generated_by": "handle_live_turn",
                    "notes": None,
                },
            },
        ]
        events.append(
            _build_event(
                packet,
                text,
                classification,
                created_at=created_at,
                event_id=event_id,
                session_clock=clock,
                derived_fields={"correction": "Lysandro is Lysandra's father (C2 table canon)"},
                summary="Canon correction logged; post-session propagation queued.",
                jobs_to_queue=[
                    {
                        "job_type": "post_session_propagation",
                        "payload": jobs[0]["payload"],
                        "reason": "Canon correction must not patch corpus inline during live play.",
                    },
                    {
                        "job_type": "manual_review",
                        "payload": {"source_event_id": event_id},
                        "reason": "GM-facing correction needs review before promotion.",
                    },
                ],
                provenance=provenance,
            )
        )
        return LiveTurnResult(
            answer="Logged canon correction. Post-session propagation and manual review are queued.",
            classification=classification,
            events_to_write=events,
            jobs_to_queue=jobs,
            next_suggestions=[],
            provenance=provenance,
            diagnostics=diagnostics,
        )

    if classification.event_type == "canon_commit":
        event_id = _next_event_id(event_id_factory)
        jobs = [
            {
                "schema_version": "0.1.0",
                "id": f"job-{event_id}-staging",
                "created_at": created_at,
                "job_type": "append_staging",
                "status": "queued",
                "payload": {"source_event_id": event_id, "note": text.strip()},
                "created_from_event_id": event_id,
                "dependencies": [],
                "provenance": {
                    "source_paths": [
                        {
                            "path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md",
                            "role": "staging_notes",
                            "notes": None,
                        }
                    ],
                    "generated_by": "handle_live_turn",
                    "notes": None,
                },
            },
            {
                "schema_version": "0.1.0",
                "id": f"job-{event_id}-benchmark",
                "created_at": created_at,
                "job_type": "benchmark_candidate",
                "status": "queued",
                "payload": {"source_event_id": event_id},
                "created_from_event_id": event_id,
                "dependencies": [],
                "provenance": {
                    "source_paths": [],
                    "generated_by": "handle_live_turn",
                    "notes": None,
                },
            },
        ]
        events.append(
            _build_event(
                packet,
                text,
                classification,
                created_at=created_at,
                event_id=event_id,
                session_clock=clock,
                derived_fields={"canon_commit": text.strip()},
                summary="Canon commit logged; staging append and benchmark candidate queued.",
                jobs_to_queue=[
                    {
                        "job_type": "append_staging",
                        "payload": jobs[0]["payload"],
                        "reason": "Session notes land in staging until recap promotion.",
                    },
                    {
                        "job_type": "benchmark_candidate",
                        "payload": {"source_event_id": event_id},
                        "reason": "Live canon commit is a regression fixture candidate.",
                    },
                ],
                provenance=provenance,
            )
        )
        return LiveTurnResult(
            answer="Logged canon commit. Staging append and benchmark candidate jobs are queued.",
            classification=classification,
            events_to_write=events,
            jobs_to_queue=jobs,
            next_suggestions=[],
            provenance=provenance,
            diagnostics=diagnostics,
        )

    if classification.event_type == "context_question":
        diagnostics.append("context_lookup_not_executed_in_L2")
        return LiveTurnResult(
            answer=(
                "Classified as context lookup. Roll resolver was not invoked; "
                "retrieval and NPC grounding are handled in a later slice."
            ),
            classification=classification,
            events_to_write=[
                _build_event(
                    packet,
                    text,
                    classification,
                    created_at=created_at,
                    event_id=_next_event_id(event_id_factory),
                    session_clock=clock,
                    derived_fields={"question": text.strip()},
                    summary="Context question routed to future context_lookup path.",
                    jobs_to_queue=[],
                    provenance=provenance,
                )
            ],
            jobs_to_queue=[],
            next_suggestions=[],
            provenance=provenance,
            diagnostics=diagnostics,
        )

    events.append(
        _build_event(
            packet,
            text,
            classification,
            created_at=created_at,
            event_id=_next_event_id(event_id_factory),
            session_clock=clock,
            derived_fields={"note": text.strip()},
            summary="Logged live-play state note.",
            jobs_to_queue=[],
            provenance=provenance,
        )
    )
    return LiveTurnResult(
        answer="Logged as a live-play state note.",
        classification=classification,
        events_to_write=events,
        jobs_to_queue=jobs,
        next_suggestions=[],
        provenance=provenance,
        diagnostics=diagnostics,
    )
