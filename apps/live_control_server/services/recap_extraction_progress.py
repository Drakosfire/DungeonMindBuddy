"""Session-scoped live progress for recap category graph extraction."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.services.graph_ingest_run_registry import (
    DEFAULT_GRAPH_INGEST_RUN_ROOTS,
    GRAPH_INGEST_RUNS_ENV,
)

LIVE_EXTRACTION_PROGRESS_SCHEMA = "dmb_category_extraction_progress_v0"
LIVE_EXTRACTION_PROGRESS_FILENAME = "live_extraction_progress.json"

ExtractionProgressPhase = Literal[
    "idle",
    "normalizing",
    "extracting",
    "materializing",
    "done",
    "error",
]


def _runs_root(repo_root: Path) -> Path:
    env_root = os.environ.get(GRAPH_INGEST_RUNS_ENV)
    relative = Path(env_root) if env_root else Path(DEFAULT_GRAPH_INGEST_RUN_ROOTS[0])
    if relative.is_absolute():
        return relative
    return (repo_root / relative).resolve()


def live_extraction_progress_path(
    repo_root: Path,
    *,
    campaign_id: str,
    session: int,
) -> Path:
    return (
        _runs_root(repo_root)
        / campaign_id
        / f"session-{session}"
        / LIVE_EXTRACTION_PROGRESS_FILENAME
    )


def idle_live_extraction_progress(
    *,
    campaign_id: str,
    session: int,
) -> dict[str, Any]:
    return {
        "schema": LIVE_EXTRACTION_PROGRESS_SCHEMA,
        "campaign_id": campaign_id,
        "session": session,
        "phase": "idle",
        "current_pass": None,
        "current_label": None,
        "completed_passes": [],
        "pass_index": 0,
        "pass_total": 0,
        "nodes_so_far": 0,
        "edges_so_far": 0,
        "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def write_live_extraction_progress(
    repo_root: Path,
    *,
    campaign_id: str,
    session: int,
    phase: ExtractionProgressPhase,
    current_pass: str | None = None,
    current_label: str | None = None,
    completed_passes: list[str] | None = None,
    pass_index: int = 0,
    pass_total: int = 0,
    nodes_so_far: int = 0,
    edges_so_far: int = 0,
) -> dict[str, Any]:
    path = live_extraction_progress_path(
        repo_root, campaign_id=campaign_id, session=session
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": LIVE_EXTRACTION_PROGRESS_SCHEMA,
        "campaign_id": campaign_id,
        "session": session,
        "phase": phase,
        "current_pass": current_pass,
        "current_label": current_label,
        "completed_passes": list(completed_passes or []),
        "pass_index": max(0, int(pass_index)),
        "pass_total": max(0, int(pass_total)),
        "nodes_so_far": max(0, int(nodes_so_far)),
        "edges_so_far": max(0, int(edges_so_far)),
        "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_live_extraction_progress(
    repo_root: Path,
    *,
    campaign_id: str,
    session: int,
) -> dict[str, Any]:
    path = live_extraction_progress_path(
        repo_root, campaign_id=campaign_id, session=session
    )
    if not path.is_file():
        return idle_live_extraction_progress(campaign_id=campaign_id, session=session)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return idle_live_extraction_progress(campaign_id=campaign_id, session=session)
    if not isinstance(payload, dict):
        return idle_live_extraction_progress(campaign_id=campaign_id, session=session)
    base = idle_live_extraction_progress(campaign_id=campaign_id, session=session)
    base.update(payload)
    base["campaign_id"] = campaign_id
    base["session"] = session
    base["schema"] = LIVE_EXTRACTION_PROGRESS_SCHEMA
    return base
