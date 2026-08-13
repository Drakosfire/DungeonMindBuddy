"""Persisted Play run-state for scene/beat dogfood (notes + progress).

Stored under ``out/workspace/play/{run_id}.json`` — reviewable after the table.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from apps.live_control_server.config import repo_root
from src.live_play.live_store import load_json, write_json

PLAY_RUN_STATE_DIR_REL = "out/workspace/play"
PLAY_RUN_STATE_SCHEMA = "dmb_play_run_state_v1"
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class PlayRunBranch(BaseModel):
    hook: Literal["hill", "alchemist", "guild"] | None = "hill"
    aftermath: Literal["celebration", "fire"] | None = None


class PlayRunStateDocument(BaseModel):
    schema_version: Literal["dmb_play_run_state_v1"] = PLAY_RUN_STATE_SCHEMA
    run_id: str
    campaign_id: str = "of-conks-cons"
    adventure_id: str = "hempholm"
    updated_at: str = ""
    current_scene_id: str = "hook"
    branch: PlayRunBranch = Field(default_factory=PlayRunBranch)
    resolved_beat_ids: list[str] = Field(default_factory=list)
    scene_notes: dict[str, str] = Field(default_factory=dict)

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not RUN_ID_RE.match(cleaned):
            raise ValueError("run_id must match [a-z0-9][a-z0-9._-]*")
        return cleaned


def play_run_state_dir(root: Path | None = None) -> Path:
    base = root if root is not None else repo_root()
    return (base / PLAY_RUN_STATE_DIR_REL).resolve()


def play_run_state_path(run_id: str, root: Path | None = None) -> Path:
    cleaned = run_id.strip()
    if not RUN_ID_RE.match(cleaned):
        raise ValueError("invalid run_id")
    directory = play_run_state_dir(root)
    path = (directory / f"{cleaned}.json").resolve()
    if not str(path).startswith(str(directory)):
        raise ValueError("run_id escapes play workspace")
    return path


def default_play_run_state(run_id: str) -> PlayRunStateDocument:
    return PlayRunStateDocument(
        run_id=run_id.strip(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def load_play_run_state(
    run_id: str,
    root: Path | None = None,
) -> PlayRunStateDocument:
    path = play_run_state_path(run_id, root)
    if not path.is_file():
        return default_play_run_state(run_id)
    raw = load_json(path)
    if not isinstance(raw, dict):
        return default_play_run_state(run_id)
    # Accept either schema or schema_version key from early sketches.
    if "schema_version" not in raw and raw.get("schema") == PLAY_RUN_STATE_SCHEMA:
        raw = {**raw, "schema_version": PLAY_RUN_STATE_SCHEMA}
    raw.setdefault("run_id", run_id.strip())
    return PlayRunStateDocument.model_validate(raw)


def save_play_run_state(
    document: PlayRunStateDocument | dict[str, Any],
    root: Path | None = None,
) -> PlayRunStateDocument:
    if isinstance(document, dict):
        payload = {**document}
        if "schema_version" not in payload and payload.get("schema") == PLAY_RUN_STATE_SCHEMA:
            payload["schema_version"] = PLAY_RUN_STATE_SCHEMA
        doc = PlayRunStateDocument.model_validate(payload)
    else:
        doc = document
    doc = doc.model_copy(
        update={"updated_at": datetime.now(timezone.utc).isoformat()},
    )
    path = play_run_state_path(doc.run_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, doc.model_dump(mode="json"))
    return doc
