from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import (
    PLAY_RUN_RECORD_SCHEMA,
    PlayRunRegistryError,
    get_play_run,
    list_play_runs,
    play_runs_dir,
)

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
RUN_ID_C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
RUN_ID_D = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
PLAYABLE_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
SHA = "a" * 64


def _persist_record(root: Path, *, run_id: str, created_at: str) -> Path:
    path = play_runs_dir(root) / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": PLAY_RUN_RECORD_SCHEMA,
                "run_id": run_id,
                "campaign_id": "longmont-c2",
                "playable_artifact_id": PLAYABLE_ID,
                "playable_revision": 7,
                "playable_content_sha256": SHA,
                "run_revision": 1,
                "created_at": created_at,
                "updated_at": created_at,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_list_orders_mixed_timestamp_precision_by_time_then_run_id(tmp_path: Path) -> None:
    _persist_record(root=tmp_path, run_id=RUN_ID_B, created_at="2026-08-15T12:00:00Z")
    _persist_record(root=tmp_path, run_id=RUN_ID_A, created_at="2026-08-15T12:00:00Z")
    _persist_record(
        root=tmp_path,
        run_id=RUN_ID_C,
        created_at="2026-08-15T12:00:00.500000Z",
    )
    _persist_record(root=tmp_path, run_id=RUN_ID_D, created_at="2026-08-15T11:00:00Z")

    assert [record.run_id for record in list_play_runs(tmp_path)] == [
        RUN_ID_C,
        RUN_ID_A,
        RUN_ID_B,
        RUN_ID_D,
    ]


def test_persisted_run_id_must_match_filename_identity(tmp_path: Path) -> None:
    path = _persist_record(
        root=tmp_path,
        run_id=RUN_ID_B,
        created_at="2026-08-15T12:00:00Z",
    )
    mismatched = play_runs_dir(tmp_path) / f"{RUN_ID_A}.json"
    path.replace(mismatched)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        get_play_run(tmp_path, RUN_ID_A)

    assert exc_info.value.status_code == 500
    assert mismatched.is_file()


def test_unknown_playable_document_returns_404_and_creates_no_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
    )
    client = TestClient(create_app())

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json={
            "playable_artifact_id": PLAYABLE_ID,
            "expected_playable_revision": 1,
            "expected_playable_content_sha256": SHA,
        },
    )

    assert response.status_code == 404
    assert not (play_runs_dir(tmp_path) / f"{RUN_ID_A}.json").exists()
