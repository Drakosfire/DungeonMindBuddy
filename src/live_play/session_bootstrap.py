from __future__ import annotations

import argparse
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.live_control_server.schema_validation import (
    validate_before_append,
    validate_live_packet,
    validate_live_surface_layout,
)
from apps.live_control_server.session_store import refresh_current_state
from src.live_play.live_store import write_json
from src.live_play.recap_ingestion import RecapIngestionResult, ingest_recap_markdown
from src.live_play.session_paths import (
    default_live_session_dir,
    live_sessions_root,
    repo_root,
    resolve_allowed_output_dir,
    session_workspace_dir,
    workspace_has_live_files,
)
from src.live_play.surface_layout_invariants import (
    validate_catalog_layout_consistency,
    validate_surface_layout_invariants,
)

SCHEMA_VERSION = "0.1.0"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recap_frontmatter_block(
    *,
    campaign_id: str,
    source_session: int | None,
    planning_session: int,
    ingested_at: str,
) -> str:
    lines = [
        "---",
        f"campaign_id: {campaign_id}",
        f"source_session: {source_session if source_session is not None else ''}",
        f"planning_session: {planning_session}",
        f"ingested_at: {ingested_at!r}",
        'generated_by: "session_bootstrap"',
        "---",
        "",
    ]
    return "\n".join(lines)


def _read_recap_body(recap_path: Path) -> str:
    try:
        raw = recap_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"recap must be UTF-8 readable: {recap_path}") from exc
    if not raw.strip():
        raise ValueError("recap file is empty")
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            body_start = end + len("\n---")
            if body_start < len(raw) and raw[body_start] == "\n":
                body_start += 1
            return raw[body_start:].lstrip("\n")
    return raw


def _default_surface_catalog() -> list[dict[str, Any]]:
    return [
        {
            "module_id": "chat",
            "title": "Chat",
            "default_slot": "main",
            "required": True,
            "enabled_by_default": True,
            "description": "Live query input and classification.",
            "config_schema": None,
        },
        {
            "module_id": "record",
            "title": "Record",
            "default_slot": "sidebar",
            "required": True,
            "enabled_by_default": True,
            "description": "Append-only session event stream.",
            "config_schema": None,
        },
        {
            "module_id": "now",
            "title": "Now",
            "default_slot": "sidebar",
            "required": False,
            "enabled_by_default": True,
            "description": "Current planning frame from recap bootstrap.",
            "config_schema": None,
        },
        {
            "module_id": "open_loops",
            "title": "Open loops",
            "default_slot": "sidebar",
            "required": False,
            "enabled_by_default": True,
            "description": "Recap-derived open threads for next-session prep.",
            "config_schema": None,
        },
        {
            "module_id": "roll_stack",
            "title": "Roll stack",
            "default_slot": "bottom",
            "required": False,
            "enabled_by_default": True,
            "description": "Pending tables when seeded later; empty at bootstrap.",
            "config_schema": None,
        },
        {
            "module_id": "timeline",
            "title": "Timeline",
            "default_slot": "bottom",
            "required": False,
            "enabled_by_default": True,
            "description": "Plan-view beats from recap ingestion.",
            "config_schema": None,
        },
        {
            "module_id": "ingestion",
            "title": "Ingestion",
            "default_slot": "sidebar",
            "required": False,
            "enabled_by_default": False,
            "description": "Raw recap ingestion operator pane over PR92 orchestration.",
            "config_schema": None,
        },
        {
            "module_id": "sources",
            "title": "Sources",
            "default_slot": "overlay",
            "required": False,
            "enabled_by_default": False,
            "description": "Context lookup provenance (off until wired).",
            "config_schema": None,
        },
        {
            "module_id": "queue",
            "title": "Queue",
            "default_slot": "bottom",
            "required": False,
            "enabled_by_default": False,
            "description": "Background jobs; none seeded at bootstrap.",
            "config_schema": None,
        },
    ]


def _default_surface_layout(
    *,
    campaign_id: str,
    session: int,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "layout_version": 1,
        "updated_at": generated_at,
        "campaign_id": campaign_id,
        "session": session,
        "modules": [
            {"module_id": "chat", "slot": "main", "order": 0, "enabled": True, "collapsed": False, "size": "2fr", "config": {}},
            {"module_id": "record", "slot": "sidebar", "order": 0, "enabled": True, "collapsed": False, "size": "1fr", "config": {"tail_count": 50}},
            {"module_id": "now", "slot": "sidebar", "order": 1, "enabled": True, "collapsed": False, "size": None, "config": {}},
            {"module_id": "open_loops", "slot": "sidebar", "order": 2, "enabled": True, "collapsed": False, "size": None, "config": {}},
            {"module_id": "ingestion", "slot": "sidebar", "order": 3, "enabled": False, "collapsed": True, "size": None, "config": {}},
            {"module_id": "roll_stack", "slot": "bottom", "order": 0, "enabled": True, "collapsed": False, "size": "compact", "config": {"expand_tables_inline": True}},
            {"module_id": "timeline", "slot": "bottom", "order": 1, "enabled": True, "collapsed": False, "size": None, "config": {}},
            {"module_id": "queue", "slot": "bottom", "order": 2, "enabled": False, "collapsed": True, "size": "compact", "config": {"show_completed": False}},
            {"module_id": "sources", "slot": "overlay", "order": 0, "enabled": False, "collapsed": True, "size": None, "config": {}},
        ],
    }


def build_live_packet(
    ingestion: RecapIngestionResult,
    *,
    next_session_label: str | None = None,
    party_position: str | None = None,
    route_intent: str | None = None,
    active_weather: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    created_at = generated_at or _now_utc()
    session = ingestion.planning_session
    label = next_session_label or f"Session {session}"
    open_loops = [
        {
            "loop_id": loop.loop_id,
            "title": loop.title,
            "status": "open",
            "summary": loop.summary,
            "source_paths": [{"path": "recap.md", "role": "fresh_recap", "notes": loop.source_line[:120]}],
        }
        for loop in ingestion.candidate_open_loops
    ]
    planning_beats = [
        {
            "beat_id": beat.beat_id,
            "label": beat.label,
            "summary": beat.summary,
            "time_hint": beat.time_hint,
            "status": "projected",
            "table_ready_prompt": beat.table_ready_prompt,
        }
        for beat in ingestion.candidate_planning_beats
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": ingestion.campaign_id,
        "session": session,
        "packet_id": f"{ingestion.campaign_id}-session-{session}-live-packet",
        "created_at": created_at,
        "source_paths": [
            {
                "path": "recap.md",
                "role": "fresh_recap",
                "notes": f"Bootstrapped from {ingestion.recap_path}",
            }
        ],
        "latency_modes": ["fast_live", "context_lookup", "prep_architect", "post_session"],
        "known_roll_tables": [],
        "current_state_seed": {
            "day_label": label,
            "party_position": party_position or "From recap bootstrap",
            "route_intent": route_intent or "Review recap and prepare next session",
            "active_weather": active_weather,
            "next_suggested_beat": (
                ingestion.candidate_planning_beats[0].label
                if ingestion.candidate_planning_beats
                else "Review recap-derived planning beats"
            ),
        },
        "open_loops": open_loops,
        "roll_stack": [],
        "planning_beats": planning_beats,
        "surface_catalog": _default_surface_catalog(),
        "context_packets": [],
    }


def build_bootstrap_event(
    ingestion: RecapIngestionResult,
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    created = created_at or _now_utc()
    event_id = f"evt-recap-ingested-{uuid.uuid4().hex[:12]}"
    return {
        "schema_version": SCHEMA_VERSION,
        "id": event_id,
        "created_at": created,
        "campaign_id": ingestion.campaign_id,
        "session": ingestion.planning_session,
        "session_clock": "session-bootstrap",
        "event_type": "state_note",
        "event_origin": "server",
        "latency_mode": None,
        "summary": f"Fresh recap ingested for Session {ingestion.planning_session} planning.",
        "derived_fields": {
            "command_type": "bootstrap_session_from_recap",
            "recap_path": "recap.md",
            "source_session": ingestion.source_session,
            "planning_session": ingestion.planning_session,
            "candidate_open_loop_count": len(ingestion.candidate_open_loops),
            "candidate_planning_beat_count": len(ingestion.candidate_planning_beats),
        },
        "provenance": {
            "source_paths": [
                {
                    "path": "recap.md",
                    "role": "fresh_recap",
                    "notes": "Source recap used to bootstrap planning session.",
                }
            ],
            "generated_by": "session_bootstrap",
            "notes": "Deterministic PR90 bootstrap event.",
        },
        "jobs_to_queue": [],
    }


def _validate_workspace_payload(
    packet: dict[str, Any],
    layout: dict[str, Any],
    events: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> None:
    validate_live_packet(packet)
    validate_live_surface_layout(layout)
    validate_surface_layout_invariants(layout)
    validate_catalog_layout_consistency(packet, layout)
    validate_before_append(events, jobs)


def bootstrap_session_workspace(
    *,
    recap_path: Path,
    campaign_id: str,
    session: int,
    output_dir: Path,
    source_session: int | None = None,
    next_session_label: str | None = None,
    party_position: str | None = None,
    route_intent: str | None = None,
    active_weather: str | None = None,
    force: bool = False,
) -> Path:
    if not recap_path.is_file():
        raise FileNotFoundError(f"recap file not found: {recap_path}")

    out = resolve_allowed_output_dir(output_dir)
    if workspace_has_live_files(out) and not force:
        raise FileExistsError(
            f"session workspace already exists at {out}; pass --force to overwrite"
        )

    ingestion = ingest_recap_markdown(
        recap_path=recap_path,
        campaign_id=campaign_id,
        planning_session=session,
        source_session=source_session,
    )
    generated_at = _now_utc()
    recap_body = _read_recap_body(recap_path)
    recap_md = _recap_frontmatter_block(
        campaign_id=campaign_id,
        source_session=source_session,
        planning_session=session,
        ingested_at=generated_at,
    ) + recap_body

    packet = build_live_packet(
        ingestion,
        next_session_label=next_session_label,
        party_position=party_position,
        route_intent=route_intent,
        active_weather=active_weather,
        generated_at=generated_at,
    )
    layout = _default_surface_layout(
        campaign_id=campaign_id,
        session=session,
        generated_at=generated_at,
    )
    events = [build_bootstrap_event(ingestion, created_at=generated_at)]
    jobs: list[dict[str, Any]] = []

    _validate_workspace_payload(packet, layout, events, jobs)

    out.mkdir(parents=True, exist_ok=True)
    (out / "recap.md").write_text(recap_md, encoding="utf-8")
    write_json(out / "live_packet.json", packet)
    write_json(out / "surface_layout.json", layout)
    (out / "event_log.jsonl").write_text(
        json.dumps(events[0], ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (out / "job_queue.jsonl").write_text("", encoding="utf-8")
    refresh_current_state(out)
    return out


def activate_session_workspace(
    source_dir: Path,
    *,
    target_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """Copy a bootstrapped workspace into the live session directory the server reads."""
    src = source_dir.resolve()
    if not (src / "live_packet.json").is_file():
        raise ValueError(f"not a bootstrapped workspace: {src}")

    dest = (target_dir or default_live_session_dir()).resolve()
    if workspace_has_live_files(dest) and not force:
        raise FileExistsError(
            f"live target already contains session files at {dest}; pass --force to overwrite"
        )
    dest.mkdir(parents=True, exist_ok=True)
    names = (
        "recap.md",
        "live_packet.json",
        "surface_layout.json",
        "event_log.jsonl",
        "job_queue.jsonl",
        "current_state.json",
    )
    for name in names:
        path = src / name
        if path.is_file():
            shutil.copy2(path, dest / name)
    return dest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a C2 live-control session workspace from a fresh recap file.",
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--recap-path", type=Path, required=True)
    parser.add_argument("--previous-session", type=int, default=None, dest="source_session")
    parser.add_argument("--next-session-label", default=None)
    parser.add_argument("--party-position", default=None)
    parser.add_argument("--route-intent", default=None)
    parser.add_argument("--active-weather", default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=f"Session workspace (default: {live_sessions_root()}/session_<N>)",
    )
    parser.add_argument(
        "--write-current-live",
        action="store_true",
        help="Activate into the default live session directory after bootstrap.",
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Alias for --write-current-live.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    recap_path = args.recap_path.expanduser().resolve()
    if not recap_path.is_file():
        print(f"recap file not found: {recap_path}", flush=True)
        return 2

    out_dir = args.out_dir or session_workspace_dir(session=args.session)
    try:
        workspace = bootstrap_session_workspace(
            recap_path=recap_path,
            campaign_id=args.campaign_id,
            session=args.session,
            output_dir=out_dir,
            source_session=args.source_session,
            next_session_label=args.next_session_label,
            party_position=args.party_position,
            route_intent=args.route_intent,
            active_weather=args.active_weather,
            force=args.force,
        )
    except (FileExistsError, ValueError, FileNotFoundError) as exc:
        print(str(exc), flush=True)
        return 2

    print(f"bootstrapped session workspace: {workspace}", flush=True)

    try:
        if args.write_current_live or args.activate:
            live_dir = activate_session_workspace(workspace, force=args.force)
            print(f"activated live session directory: {live_dir}", flush=True)
    except (FileExistsError, ValueError) as exc:
        print(str(exc), flush=True)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
