from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def _seed_event(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Weather 16.",
        },
    )
    assert response.status_code == 200
    events_response = client.get("/api/live/events")
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert events
    return events[-1]


def _command(*, target_type: str, target_id: str, label: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "observation": "The hail result should be remembered as pressure on the wagon axle.",
        "session_clock": "during travel day 1",
        "visibility": "live_note",
    }
    payload.update(overrides.pop("payload", {}))
    command = {
        "command_type": "append_observation",
        "target": {
            "target_type": target_type,
            "target_id": target_id,
            "label": label,
            "source_status": "authoritative",
        },
        "lane": "observed_play",
        "payload": payload,
        "evidence": [],
        "requested_by": {"requester_type": "human_ui", "requester_id": "live-control-ui"},
        "idempotency_key": overrides.pop("idempotency_key", None),
    }
    command.update(overrides)
    return command


def test_post_commands_accepts_append_observation_for_event_target(client: TestClient, isolated_session: Path) -> None:
    event = _seed_event(client)
    before_count = len((isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines())

    response = client.post(
        "/api/live/commands",
        json=_command(target_type="event", target_id=event["id"], label=event["summary"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert len(body["events_appended"]) == 1
    assert len(body["invalidations"]) >= 3
    after_lines = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(after_lines) == before_count + 1
    appended = json.loads(after_lines[-1])
    assert appended["event_type"] == "state_note"
    assert appended["event_origin"] == "server"
    assert appended["derived_fields"]["command_type"] == "append_observation"
    assert appended["derived_fields"]["target"]["target_type"] == "event"
    assert appended["derived_fields"]["target"]["target_id"] == event["id"]


def test_post_commands_accepts_append_observation_for_roll_table_target(
    client: TestClient,
    isolated_session: Path,
) -> None:
    before_count = len((isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines())
    response = client.post(
        "/api/live/commands",
        json=_command(target_type="roll_table", target_id="T-WX", label="Storm weather"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert len(body["events_appended"]) == 1
    after_lines = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(after_lines) == before_count + 1
    appended = json.loads(after_lines[-1])
    assert appended["event_type"] == "state_note"
    assert appended["derived_fields"]["target"]["target_type"] == "roll_table"
    assert appended["derived_fields"]["target"]["target_id"] == "T-WX"


def test_append_observation_mutates_only_event_log(client: TestClient, isolated_session: Path) -> None:
    event = _seed_event(client)
    packet = json.loads((isolated_session / "live_packet.json").read_text(encoding="utf-8"))
    roll_source = ROOT / str(packet["known_roll_tables"][0]["source_path"])
    watched = {
        "job_queue.jsonl": (isolated_session / "job_queue.jsonl").read_bytes(),
        "surface_layout.json": (isolated_session / "surface_layout.json").read_bytes(),
        "current_state.json": (isolated_session / "current_state.json").read_bytes(),
        "live_packet.json": (isolated_session / "live_packet.json").read_bytes(),
        "roll_source": roll_source.read_bytes(),
    }

    response = client.post(
        "/api/live/commands",
        json=_command(target_type="event", target_id=event["id"], label=event["summary"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    assert (isolated_session / "job_queue.jsonl").read_bytes() == watched["job_queue.jsonl"]
    assert (isolated_session / "surface_layout.json").read_bytes() == watched["surface_layout.json"]
    assert (isolated_session / "current_state.json").read_bytes() == watched["current_state.json"]
    assert (isolated_session / "live_packet.json").read_bytes() == watched["live_packet.json"]
    assert roll_source.read_bytes() == watched["roll_source"]


def test_unknown_event_target_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/live/commands",
        json=_command(target_type="event", target_id="evt-does-not-exist", label="Missing"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "unknown_target"


def test_unknown_roll_table_target_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/live/commands",
        json=_command(target_type="roll_table", target_id="T-DOES-NOT-EXIST", label="Missing"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "unknown_target"


def test_unsupported_target_type_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/live/commands",
        json=_command(target_type="npc", target_id="lysandra", label="Lysandra"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "unsupported_target"


def test_unsupported_command_rejected_without_mutation(client: TestClient, isolated_session: Path) -> None:
    event = _seed_event(client)
    before = (isolated_session / "event_log.jsonl").read_bytes()
    response = client.post(
        "/api/live/commands",
        json=_command(
            target_type="event",
            target_id=event["id"],
            label=event["summary"],
            command_type="update_layout",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "unsupported_command"
    assert (isolated_session / "event_log.jsonl").read_bytes() == before


def test_wrong_lane_rejected(client: TestClient) -> None:
    event = _seed_event(client)
    response = client.post(
        "/api/live/commands",
        json=_command(
            target_type="event",
            target_id=event["id"],
            label=event["summary"],
            lane="prep_note",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "invalid_lane"


def test_missing_or_empty_observation_rejected(client: TestClient) -> None:
    event = _seed_event(client)
    response = client.post(
        "/api/live/commands",
        json=_command(
            target_type="event",
            target_id=event["id"],
            label=event["summary"],
            payload={"observation": "   "},
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "invalid_payload"


def test_unknown_payload_field_rejected(client: TestClient) -> None:
    event = _seed_event(client)
    response = client.post(
        "/api/live/commands",
        json=_command(
            target_type="event",
            target_id=event["id"],
            label=event["summary"],
            payload={"observation": "valid", "unknown_field": "x"},
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["conflicts"][0]["conflict_type"] == "invalid_payload"


def test_duplicate_idempotency_key_returns_noop(client: TestClient, isolated_session: Path) -> None:
    event = _seed_event(client)
    key = "idem-1"
    first = client.post(
        "/api/live/commands",
        json=_command(
            target_type="event",
            target_id=event["id"],
            label=event["summary"],
            idempotency_key=key,
        ),
    )
    assert first.status_code == 200
    assert first.json()["status"] == "accepted"
    count_after_first = len((isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines())

    second = client.post(
        "/api/live/commands",
        json=_command(
            target_type="event",
            target_id=event["id"],
            label=event["summary"],
            idempotency_key=key,
        ),
    )
    assert second.status_code == 200
    body = second.json()
    assert body["status"] == "noop"
    assert len(body["events_appended"]) == 1
    assert "duplicate idempotency_key" in body["diagnostics"][0]
    count_after_second = len((isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines())
    assert count_after_second == count_after_first


def test_capabilities_enable_append_observation_for_event(client: TestClient) -> None:
    event = _seed_event(client)
    response = client.get(
        "/api/live/capabilities",
        params={"target_type": "event", "target_id": event["id"]},
    )
    assert response.status_code == 200
    caps = response.json()["capabilities"]
    append = next(cap for cap in caps if cap["command_type"] == "append_observation")
    queue = next(cap for cap in caps if cap["command_type"] == "queue_canon_patch")
    assert append["enabled"] is True
    assert append["disabled_reason"] is None
    assert append["required_fields"] == ["observation"]
    assert queue["enabled"] is False


def test_capabilities_enable_patch_and_append_for_roll_table(client: TestClient) -> None:
    response = client.get(
        "/api/live/capabilities",
        params={"target_type": "roll_table", "target_id": "T-WX"},
    )
    assert response.status_code == 200
    caps = response.json()["capabilities"]
    append = next(cap for cap in caps if cap["command_type"] == "append_observation")
    patch = next(cap for cap in caps if cap["command_type"] == "patch_artifact")
    assert append["enabled"] is True
    assert append["disabled_reason"] is None
    assert append["required_fields"] == ["observation"]
    assert patch["enabled"] is True
    assert patch["disabled_reason"] is None
    assert patch["required_fields"] == ["expected_file_state_token", "old_text", "new_text"]
