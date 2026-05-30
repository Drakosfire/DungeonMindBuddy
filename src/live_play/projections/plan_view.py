from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .targets import ProjectionSourceStatus, ProjectionTargetType

PLAN_VIEW_SCHEMA_VERSION = "0.1.0"

TimelineStatus = str


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ref(
    *,
    target_type: ProjectionTargetType,
    target_id: str,
    label: str,
    source_status: ProjectionSourceStatus,
    role: str | None = None,
) -> dict[str, str | None]:
    return {
        "target_type": target_type,
        "target_id": target_id,
        "label": label,
        "source_status": source_status,
        "role": role,
    }


def _state_links(
    *,
    event_ids: list[str] | None = None,
    job_ids: list[str] | None = None,
    open_loop_ids: list[str] | None = None,
) -> dict[str, list[str]]:
    return {
        "event_ids": event_ids or [],
        "job_ids": job_ids or [],
        "open_loop_ids": open_loop_ids or [],
    }


def _event_ids_for(events: list[dict[str, Any]], *, event_type: str) -> list[str]:
    out: list[str] = []
    for event in events:
        if event.get("event_type") != event_type:
            continue
        event_id = event.get("id")
        if isinstance(event_id, str) and event_id:
            out.append(event_id)
    return out


def _job_ids_for(jobs: list[dict[str, Any]], *, job_type: str) -> list[str]:
    out: list[str] = []
    for job in jobs:
        if job.get("job_type") != job_type:
            continue
        job_id = job.get("id")
        if isinstance(job_id, str) and job_id:
            out.append(job_id)
    return out


def _loop_status(packet: dict[str, Any], loop_id: str) -> TimelineStatus:
    for row in packet.get("open_loops", []):
        if row.get("loop_id") == loop_id:
            status = row.get("status")
            if status in {"open", "owed"}:
                return "active"
            if status in {"blocked"}:
                return "blocked"
            if status in {"closed"}:
                return "played"
    return "projected"


def _build_planning_beats_timeline(
    packet: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    beats = packet.get("planning_beats")
    if not isinstance(beats, list) or not beats:
        return None

    bootstrap_event_ids = _event_ids_for(events, event_type="state_note")
    rows: list[dict[str, Any]] = []
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        beat_id = beat.get("beat_id")
        label = beat.get("label")
        if not isinstance(beat_id, str) or not beat_id.strip():
            continue
        if not isinstance(label, str) or not label.strip():
            continue
        open_loop_ids = [
            loop.get("loop_id")
            for loop in packet.get("open_loops", [])
            if isinstance(loop, dict) and isinstance(loop.get("loop_id"), str)
        ]
        refs = [
            _ref(
                target_type="source_packet",
                target_id="recap.md",
                label="Fresh recap",
                source_status="authoritative",
                role="fresh_recap",
            )
        ]
        if open_loop_ids:
            refs.append(
                _ref(
                    target_type="open_loop",
                    target_id=open_loop_ids[0],
                    label=open_loop_ids[0].replace("-", " ").title(),
                    source_status="authoritative",
                    role="open_loop",
                )
            )
        rows.append(
            {
                "id": f"beat-{beat_id}",
                "label": label,
                "status": beat.get("status") or "projected",
                "time_hint": beat.get("time_hint"),
                "summary": beat.get("summary") or label,
                "table_ready_prompt": beat.get("table_ready_prompt")
                or f"What should the table resolve for {label}?",
                "refs": refs,
                "state_links": _state_links(
                    event_ids=bootstrap_event_ids[:1],
                    open_loop_ids=open_loop_ids[:3],
                ),
            }
        )
    return rows or None


def _build_seeded_timeline(packet: dict[str, Any], events: list[dict[str, Any]], jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    correction_event_ids = _event_ids_for(events, event_type="canon_correction")
    commit_event_ids = _event_ids_for(events, event_type="canon_commit")
    loop_event_ids = _event_ids_for(events, event_type="open_loop_update")
    propagation_job_ids = _job_ids_for(jobs, job_type="post_session_propagation")
    benchmark_job_ids = _job_ids_for(jobs, job_type="benchmark_candidate")

    return [
        {
            "id": "beat-pretravel-silver-raven-dispatch",
            "label": "Pre-travel Silver Raven dispatch",
            "status": "projected",
            "time_hint": "Pre-travel",
            "summary": "The session opens with comms pressure and Silver Raven coordination before the northward march.",
            "table_ready_prompt": "Who receives the next outbound message first?",
            "refs": [
                _ref(
                    target_type="runbook_section",
                    target_id="session22-runbook-pretravel",
                    label="Session 22 runbook pre-travel beats",
                    source_status="derived",
                    role="procedural_anchor",
                ),
                _ref(
                    target_type="open_loop",
                    target_id="silver-raven-reply",
                    label="Silver Raven reply",
                    source_status="authoritative",
                    role="open_loop",
                ),
            ],
            "state_links": _state_links(open_loop_ids=["silver-raven-reply"]),
        },
        {
            "id": "beat-day1-weather-front",
            "label": "Travel Day 1 weather/front beat",
            "status": "projected",
            "time_hint": "Day 1",
            "summary": "Weather and march pressure establish the day-one travel frame.",
            "table_ready_prompt": "Roll T-WX and narrate immediate travel consequences.",
            "refs": [
                _ref(
                    target_type="roll_table",
                    target_id="T-WX",
                    label="Storm weather",
                    source_status="authoritative",
                    role="next_roll",
                )
            ],
            "state_links": _state_links(job_ids=benchmark_job_ids),
        },
        {
            "id": "beat-day1-puddle-identify",
            "label": "Delayed reflection puddle / Identify beat",
            "status": "projected",
            "time_hint": "Day 1, after weather",
            "summary": "A bottled puddle sample and delayed reflection mystery become a context-heavy beat.",
            "table_ready_prompt": "Decide if this routes to context lookup or state note at the table.",
            "refs": [
                _ref(
                    target_type="runbook_section",
                    target_id="session22-runbook-delayed-reflection",
                    label="Delayed reflection notes",
                    source_status="derived",
                    role="context_anchor",
                )
            ],
            "state_links": _state_links(event_ids=commit_event_ids),
        },
        {
            "id": "beat-day1-hester-mull-courier",
            "label": "Hester Mull courier encounter",
            "status": "projected",
            "time_hint": "Day 1",
            "summary": "A road encounter beat provides social pressure during the first travel leg.",
            "table_ready_prompt": "Roll R5 if encounter pressure is needed now.",
            "refs": [
                _ref(
                    target_type="roll_table",
                    target_id="R5",
                    label="Road encounter",
                    source_status="authoritative",
                    role="encounter_roll",
                )
            ],
            "state_links": _state_links(),
        },
        {
            "id": "beat-grobnok-callback-no-call-loop",
            "label": "Grobnok callback / no-call open loop",
            "status": _loop_status(packet, "grobnok-evening-contact"),
            "time_hint": "Day 1 evening -> Day 2 morning",
            "summary": "Grobnok contact remains a visible loop until resolved.",
            "table_ready_prompt": "Has evening contact occurred, or does the loop remain owed?",
            "refs": [
                _ref(
                    target_type="open_loop",
                    target_id="grobnok-evening-contact",
                    label="Grobnok evening contact",
                    source_status="authoritative",
                    role="open_loop",
                )
            ],
            "state_links": _state_links(event_ids=loop_event_ids, open_loop_ids=["grobnok-evening-contact"]),
        },
        {
            "id": "beat-day2-forced-march-outskirts",
            "label": "Day 2 forced march to Mireward outskirts",
            "status": "projected",
            "time_hint": "Day 2 late",
            "summary": "Travel pressure escalates as the party pushes toward Mireward outskirts.",
            "table_ready_prompt": "Use T-DIL if a travel complication beat is needed before the gate.",
            "refs": [
                _ref(
                    target_type="roll_table",
                    target_id="T-DIL",
                    label="Travel dilemma",
                    source_status="authoritative",
                    role="complication_roll",
                )
            ],
            "state_links": _state_links(),
        },
        {
            "id": "beat-mireward-gate-arrival-lysandro-reveal",
            "label": "Mireward gate arrival / Lysandro reveal",
            "status": "projected",
            "time_hint": "Day 2, ~22:00",
            "summary": "The party reaches the gate apron and relationship revelations can change social stakes.",
            "table_ready_prompt": "What does the party see first at the gate apron?",
            "refs": [
                _ref(
                    target_type="location",
                    target_id="mireward-gate",
                    label="Mireward Gate",
                    source_status="derived",
                    role="scene_location",
                ),
                _ref(
                    target_type="npc",
                    target_id="lysandro-ironveil",
                    label="Lysandro Ironveil",
                    source_status="derived",
                    role="scene_npc",
                ),
            ],
            "state_links": _state_links(event_ids=correction_event_ids, job_ids=propagation_job_ids),
        },
        {
            "id": "beat-gate-dilemma-next-roll",
            "label": "Gate dilemma next roll",
            "status": "projected",
            "time_hint": "At gate trigger",
            "summary": "If gate pressure spikes, the gate dilemma table is the next deterministic input.",
            "table_ready_prompt": "Roll T-DIL-G when gate pressure calls for a dilemma beat.",
            "refs": [
                _ref(
                    target_type="roll_table",
                    target_id="T-DIL-G",
                    label="Gate dilemma table",
                    source_status="authoritative",
                    role="next_roll",
                )
            ],
            "state_links": _state_links(),
        },
    ]


def build_session_plan_projection(
    packet: dict[str, Any],
    events: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    source_paths = packet.get("source_paths", [])
    derived_from = ["live_packet.json", "event_log.jsonl", "job_queue.jsonl"]
    if source_paths:
        derived_from.extend(
            [
                f"{row.get('role', 'source')}:{row.get('path')}"
                for row in source_paths
                if isinstance(row, dict) and row.get("path")
            ]
        )

    timeline = _build_planning_beats_timeline(packet, events)
    if timeline is None:
        timeline = _build_seeded_timeline(packet, events, jobs)

    return {
        "schema_version": PLAN_VIEW_SCHEMA_VERSION,
        "campaign_id": packet["campaign_id"],
        "session": packet["session"],
        "authoritative": False,
        "generated_at": generated_at or _now_utc(),
        "derived_from": derived_from,
        "timeline": timeline,
    }
