from __future__ import annotations

from typing import Any


def derive_current_state_fields(
    packet: dict[str, Any],
    layout: dict[str, Any],
    events: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Recompute count/list fields that current_state.json must mirror from authoritative sources."""
    return {
        "open_loop_count": len(packet["open_loops"]),
        "pending_roll_tables": [
            row["table_id"] for row in packet["roll_stack"] if row["status"] == "pending"
        ],
        "enabled_surface_modules": [
            row["module_id"] for row in layout["modules"] if row["enabled"]
        ],
        "queued_job_count": len([job for job in jobs if job["status"] == "queued"]),
        "recent_event_count": len(events),
    }
