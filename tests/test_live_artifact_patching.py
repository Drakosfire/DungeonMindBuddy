from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.routes import live as live_routes
from apps.live_control_server.schema_validation import validate_before_append
from src.live_play.live_store import append_jsonl

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    tables_dir = repo_root / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    primary_table = tables_dir / "storm_weather.md"
    primary_table.write_text(
        "# Storm weather\n| 1 | Heavy rain |\n| 2 | Hail dent |\n",
        encoding="utf-8",
    )
    secondary_table = tables_dir / "road_encounter.md"
    secondary_table.write_text(
        "# Road encounter\n| 1 | Wandering merchant |\n| 2 | Bridge toll |\n",
        encoding="utf-8",
    )

    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, session_dir / name)
    (session_dir / "event_log.jsonl").write_text("", encoding="utf-8")
    (session_dir / "job_queue.jsonl").write_text("", encoding="utf-8")

    packet_path = session_dir / "live_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["known_roll_tables"] = [
        {
            "table_id": "T-WX",
            "title": "Storm weather",
            "dice": "d20",
            "source_path": "tables/storm_weather.md",
            "status": "pending",
            "default_latency_mode": "fast_live",
        },
        {
            "table_id": "R5",
            "title": "Road encounter",
            "dice": "d20",
            "source_path": "tables/road_encounter.md",
            "status": "pending",
            "default_latency_mode": "fast_live",
        },
    ]
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setenv(SESSION_DIR_ENV, str(session_dir))
    monkeypatch.setattr(live_routes, "repo_root", lambda: repo_root)
    return {
        "repo_root": repo_root,
        "session_dir": session_dir,
        "primary_table": primary_table,
        "secondary_table": secondary_table,
    }


@pytest.fixture
def client(isolated_session: dict[str, Path]) -> TestClient:
    del isolated_session
    return TestClient(create_app())


def _artifact_token(client: TestClient, table_id: str = "T-WX") -> str:
    response = client.get(
        "/api/live/artifact",
        params={"target_type": "roll_table", "target_id": table_id},
    )
    assert response.status_code == 200
    body = response.json()
    return str(body["file_state_token"])


def _patch_command(
    *,
    expected_file_state_token: str,
    old_text: str,
    new_text: str,
    idempotency_key: str | None = None,
    lane: str = "prep_note",
    target_type: str = "roll_table",
    target_id: str = "T-WX",
    payload_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "expected_file_state_token": expected_file_state_token,
        "old_text": old_text,
        "new_text": new_text,
        "rationale": "Record live table correction from play.",
        "dry_run": False,
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return {
        "command_type": "patch_artifact",
        "target": {
            "target_type": target_type,
            "target_id": target_id,
            "label": "Storm weather",
            "source_status": "authoritative",
        },
        "lane": lane,
        "payload": payload,
        "evidence": [],
        "requested_by": {"requester_type": "human_ui", "requester_id": "live-control-ui"},
        "idempotency_key": idempotency_key,
    }


def _event_log_lines(session_dir: Path) -> list[str]:
    text = (session_dir / "event_log.jsonl").read_text(encoding="utf-8").strip()
    return [] if not text else text.splitlines()


def test_patch_artifact_accepted_updates_one_allowlisted_file_and_appends_audit_event(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    session_dir = isolated_session["session_dir"]
    primary_table = isolated_session["primary_table"]
    secondary_table = isolated_session["secondary_table"]

    token = _artifact_token(client)
    watched = {
        "job_queue": (session_dir / "job_queue.jsonl").read_bytes(),
        "surface_layout": (session_dir / "surface_layout.json").read_bytes(),
        "current_state": (session_dir / "current_state.json").read_bytes(),
        "live_packet": (session_dir / "live_packet.json").read_bytes(),
        "secondary_table": secondary_table.read_bytes(),
    }
    old_text = "| 1 | Heavy rain |"
    new_text = "| 1 | Heavy rain; wagon axle stress worsens |"

    response = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text=old_text,
            new_text=new_text,
            idempotency_key="patch-accepted-1",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["events_appended"]
    assert body["artifacts_changed"][0]["target_type"] == "roll_table"
    assert body["artifacts_changed"][0]["target_id"] == "T-WX"
    invalidation_keys = {row["projection_key"] for row in body["invalidations"]}
    assert {"live.artifact", "live.capabilities", "live.plan_view", "live.events"} <= invalidation_keys
    patch_meta = body["metadata"]["patch"]
    assert patch_meta["source_path"] == "tables/storm_weather.md"
    assert patch_meta["replacement_count"] == 1
    assert patch_meta["dry_run"] is False
    assert patch_meta["file_state_token_before"] != patch_meta["file_state_token_after"]
    assert "+++ b/tables/storm_weather.md" in patch_meta["unified_diff"]

    patched_text = primary_table.read_text(encoding="utf-8")
    assert old_text not in patched_text
    assert new_text in patched_text
    assert secondary_table.read_bytes() == watched["secondary_table"]
    assert (session_dir / "job_queue.jsonl").read_bytes() == watched["job_queue"]
    assert (session_dir / "surface_layout.json").read_bytes() == watched["surface_layout"]
    assert (session_dir / "current_state.json").read_bytes() == watched["current_state"]
    assert (session_dir / "live_packet.json").read_bytes() == watched["live_packet"]

    events = _event_log_lines(session_dir)
    assert len(events) == 1
    audit = json.loads(events[0])
    assert audit["event_type"] == "state_note"
    assert audit["derived_fields"]["command_type"] == "patch_artifact"
    assert audit["derived_fields"]["target"]["target_id"] == "T-WX"
    assert audit["derived_fields"]["idempotency_key"] == "patch-accepted-1"


def test_patch_artifact_dry_run_returns_preview_without_writes(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    session_dir = isolated_session["session_dir"]
    primary_table = isolated_session["primary_table"]
    before_text = primary_table.read_text(encoding="utf-8")
    before_events = _event_log_lines(session_dir)

    token = _artifact_token(client)
    response = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text="| 1 | Heavy rain |",
            new_text="| 1 | Heavy rain; no write in dry run |",
            payload_overrides={"dry_run": True},
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "noop"
    assert body["events_appended"] == []
    assert body["artifacts_changed"] == []
    assert body["invalidations"] == []
    assert "dry_run preview only" in body["diagnostics"][0]
    assert body["metadata"]["patch"]["dry_run"] is True
    assert body["metadata"]["patch"]["replacement_count"] == 1
    assert body["metadata"]["patch"]["unified_diff"]
    assert primary_table.read_text(encoding="utf-8") == before_text
    assert _event_log_lines(session_dir) == before_events


def test_patch_artifact_stale_token_returns_conflict_without_write(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    primary_table = isolated_session["primary_table"]
    token = _artifact_token(client)
    primary_table.write_text(
        "# Storm weather\n| 1 | Heavy rain changed after read |\n| 2 | Hail dent |\n",
        encoding="utf-8",
    )

    response = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text="| 1 | Heavy rain changed after read |",
            new_text="| 1 | New text |",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "conflict"
    assert body["conflicts"][0]["conflict_type"] == "stale_artifact"
    assert "artifact changed since it was read" in body["conflicts"][0]["message"]
    assert _event_log_lines(isolated_session["session_dir"]) == []


@pytest.mark.parametrize(
    ("payload_overrides", "expected_fragment"),
    [
        ({"expected_file_state_token": ""}, "expected_file_state_token"),
        ({"old_text": ""}, "old_text"),
        ({"new_text": ""}, "new_text"),
        ({"old_text": "| 1 | Heavy rain |", "new_text": "| 1 | Heavy rain |"}, "must differ"),
        ({"unknown_field": "x"}, "unsupported payload fields"),
        ({"source_path": "tables/storm_weather.md"}, "forbidden payload fields"),
    ],
)
def test_patch_artifact_payload_validation_rejects_invalid_commands(
    client: TestClient,
    payload_overrides: dict[str, Any],
    expected_fragment: str,
) -> None:
    token = _artifact_token(client)
    response = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text="| 1 | Heavy rain |",
            new_text="| 1 | Heavy rain updated |",
            payload_overrides=payload_overrides,
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "invalid_payload"
    assert expected_fragment in body["conflicts"][0]["message"]


def test_patch_artifact_rejects_no_match_and_multiple_match_cases(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    token = _artifact_token(client)
    no_match = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text="| 77 | Missing row |",
            new_text="| 77 | Should never apply |",
        ),
    )
    assert no_match.status_code == 200
    no_match_body = no_match.json()
    assert no_match_body["status"] == "rejected"
    assert "not found" in no_match_body["conflicts"][0]["message"]

    primary_table = isolated_session["primary_table"]
    primary_table.write_text(
        "# Storm weather\n| 1 | Duplicate row |\n| 2 | Duplicate row |\n",
        encoding="utf-8",
    )
    fresh_token = _artifact_token(client)
    multi_match = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=fresh_token,
            old_text="Duplicate row",
            new_text="Changed row",
        ),
    )
    assert multi_match.status_code == 200
    multi_match_body = multi_match.json()
    assert multi_match_body["status"] == "rejected"
    assert "exactly once" in multi_match_body["conflicts"][0]["message"]


def test_patch_artifact_rejects_when_patched_markdown_fails_parse(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    primary_table = isolated_session["primary_table"]
    token = _artifact_token(client)
    entire_file = primary_table.read_text(encoding="utf-8")
    response = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text=entire_file,
            new_text="This is not a parseable roll table.",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "invalid_artifact_patch"
    assert "failed parse validation" in body["conflicts"][0]["message"]
    assert _event_log_lines(isolated_session["session_dir"]) == []


def test_patch_artifact_rejects_unknown_target_wrong_lane_and_non_roll_table_target(
    client: TestClient,
) -> None:
    token = _artifact_token(client)
    unknown_target = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text="| 1 | Heavy rain |",
            new_text="| 1 | Changed |",
            target_id="T-UNKNOWN",
        ),
    )
    assert unknown_target.status_code == 200
    assert unknown_target.json()["conflicts"][0]["conflict_type"] == "unknown_target"

    wrong_lane = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text="| 1 | Heavy rain |",
            new_text="| 1 | Changed |",
            lane="observed_play",
        ),
    )
    assert wrong_lane.status_code == 200
    assert wrong_lane.json()["conflicts"][0]["conflict_type"] == "invalid_lane"

    wrong_target_type = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token=token,
            old_text="| 1 | Heavy rain |",
            new_text="| 1 | Changed |",
            target_type="event",
            target_id="evt-1",
        ),
    )
    assert wrong_target_type.status_code == 200
    assert wrong_target_type.json()["conflicts"][0]["conflict_type"] == "unsupported_target"


def test_patch_artifact_idempotency_duplicate_returns_noop_without_second_write(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    primary_table = isolated_session["primary_table"]
    token = _artifact_token(client)
    command = _patch_command(
        expected_file_state_token=token,
        old_text="| 1 | Heavy rain |",
        new_text="| 1 | Heavy rain idempotent update |",
        idempotency_key="patch-idem-1",
    )

    first = client.post("/api/live/commands", json=command)
    assert first.status_code == 200
    assert first.json()["status"] == "accepted"
    text_after_first = primary_table.read_text(encoding="utf-8")
    event_lines_after_first = _event_log_lines(isolated_session["session_dir"])
    assert len(event_lines_after_first) == 1

    second = client.post("/api/live/commands", json=command)
    assert second.status_code == 200
    body = second.json()
    assert body["status"] == "noop"
    assert body["events_appended"] == first.json()["events_appended"]
    assert "duplicate idempotency_key" in body["diagnostics"][0]
    assert primary_table.read_text(encoding="utf-8") == text_after_first
    assert _event_log_lines(isolated_session["session_dir"]) == event_lines_after_first


def test_patch_artifact_rejects_malicious_escaped_source_path_in_packet(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    session_dir = isolated_session["session_dir"]
    packet_path = session_dir / "live_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["known_roll_tables"][0]["source_path"] = "../../etc/passwd"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    response = client.post(
        "/api/live/commands",
        json=_patch_command(
            expected_file_state_token="bogus",
            old_text="foo",
            new_text="bar",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "invalid_source_path"
    assert _event_log_lines(session_dir) == []


def test_capabilities_enable_patch_artifact_for_roll_table_only(
    client: TestClient,
    isolated_session: dict[str, Path],
) -> None:
    roll_caps = client.get(
        "/api/live/capabilities",
        params={"target_type": "roll_table", "target_id": "T-WX"},
    )
    assert roll_caps.status_code == 200
    patch_cap = next(
        cap for cap in roll_caps.json()["capabilities"] if cap["command_type"] == "patch_artifact"
    )
    assert patch_cap["enabled"] is True
    assert patch_cap["lane"] == "prep_note"
    assert patch_cap["required_fields"] == ["expected_file_state_token", "old_text", "new_text"]
    assert patch_cap["metadata"]["supports_dry_run"] is True

    event_row = {
        "schema_version": "0.1.0",
        "id": "evt-test-capability-1",
        "created_at": "2026-05-25T12:00:00Z",
        "campaign_id": "longmont-c2",
        "session": 22,
        "session_clock": "test",
        "event_type": "state_note",
        "event_origin": "user_input",
        "latency_mode": "fast_live",
        "input_text": "seed event",
        "summary": "Seed event for capability lookup.",
        "derived_fields": {},
        "provenance": {
            "source_paths": [],
            "generated_by": "test_live_artifact_patching",
            "notes": None,
        },
        "jobs_to_queue": [],
    }
    validate_before_append([event_row], [])
    append_jsonl(isolated_session["session_dir"] / "event_log.jsonl", event_row)
    event_id = event_row["id"]
    event_caps = client.get(
        "/api/live/capabilities",
        params={"target_type": "event", "target_id": event_id},
    )
    assert event_caps.status_code == 200
    assert not any(
        cap["command_type"] == "patch_artifact"
        for cap in event_caps.json()["capabilities"]
    )
    event_patch = next(
        cap for cap in event_caps.json()["capabilities"] if cap["command_type"] == "queue_canon_patch"
    )
    assert event_patch["enabled"] is False
