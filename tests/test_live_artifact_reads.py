from __future__ import annotations

import json
import shutil
from pathlib import Path

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


def _seed_event(client: TestClient) -> str:
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
    return str(events[-1]["id"])


def test_get_artifact_event_returns_read_only_envelope(client: TestClient) -> None:
    event_id = _seed_event(client)
    response = client.get(
        "/api/live/artifact",
        params={"target_type": "event", "target_id": event_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "0.1.0"
    assert body["artifact_kind"] == "event"
    assert body["read_only"] is True
    assert body["target"]["target_type"] == "event"
    assert body["target"]["target_id"] == event_id
    assert body["target"]["label"]
    assert body["payload"]["content_type"] == "application/json"
    assert isinstance(body["payload"]["data"], dict)
    assert body["payload"]["data"]["id"] == event_id
    assert isinstance(body["file_state_token"], str) and body["file_state_token"]


def test_get_artifact_event_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/live/artifact",
        params={"target_type": "event", "target_id": "evt-does-not-exist"},
    )
    assert response.status_code == 404


def test_get_artifact_roll_table_returns_markdown_and_metadata(client: TestClient) -> None:
    response = client.get(
        "/api/live/artifact",
        params={"target_type": "roll_table", "target_id": "T-WX"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["artifact_kind"] == "roll_table"
    assert body["target"]["target_type"] == "roll_table"
    assert body["target"]["target_id"] == "T-WX"
    assert body["target"]["label"] == "Storm weather"
    assert body["payload"]["content_type"] == "text/markdown"
    assert isinstance(body["payload"]["text"], str) and body["payload"]["text"]
    assert body["metadata"]["table_id"] == "T-WX"
    assert body["metadata"]["dice"] == "d20"
    assert "status" in body["metadata"]
    assert body["provenance"]["source_path"]
    assert body["provenance"]["source_path"].startswith("corpus/")
    assert isinstance(body["file_state_token"], str) and body["file_state_token"]


def test_get_artifact_roll_table_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/live/artifact",
        params={"target_type": "roll_table", "target_id": "T-DOES-NOT-EXIST"},
    )
    assert response.status_code == 404


def test_get_artifact_roll_table_rejects_escape_source_path_in_packet(
    client: TestClient,
    isolated_session: Path,
) -> None:
    packet_path = isolated_session / "live_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    tables = list(packet.get("known_roll_tables", []))
    assert tables
    tables[0]["source_path"] = "../../etc/passwd"
    packet["known_roll_tables"] = tables
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    response = client.get(
        "/api/live/artifact",
        params={"target_type": "roll_table", "target_id": tables[0]["table_id"]},
    )
    assert response.status_code == 404


def test_get_artifact_unsupported_target_type_returns_422(client: TestClient) -> None:
    response = client.get(
        "/api/live/artifact",
        params={"target_type": "npc", "target_id": "npc-1"},
    )
    assert response.status_code == 422


def test_get_artifact_path_like_target_id_is_not_treated_as_path(client: TestClient) -> None:
    response = client.get(
        "/api/live/artifact",
        params={"target_type": "roll_table", "target_id": "../../etc/passwd"},
    )
    assert response.status_code == 404


def test_get_artifact_rejects_forbidden_path_query_fields(client: TestClient) -> None:
    response = client.get(
        "/api/live/artifact",
        params={
            "target_type": "roll_table",
            "target_id": "T-WX",
            "source_path": "corpus/eldyrwild-markdown/secrets.md",
        },
    )
    assert response.status_code == 422


def test_artifact_reads_do_not_mutate_session_files(client: TestClient, isolated_session: Path) -> None:
    watched = ("event_log.jsonl", "job_queue.jsonl", "surface_layout.json", "current_state.json")
    event_id = _seed_event(client)
    before = {name: (isolated_session / name).read_bytes() for name in watched}

    a = client.get("/api/live/artifact", params={"target_type": "event", "target_id": event_id})
    b = client.get("/api/live/artifact", params={"target_type": "roll_table", "target_id": "T-WX"})
    c = client.get("/api/live/capabilities", params={"target_type": "event", "target_id": event_id})
    d = client.get("/api/live/capabilities", params={"target_type": "roll_table", "target_id": "T-WX"})
    assert a.status_code == 200
    assert b.status_code == 200
    assert c.status_code == 200
    assert d.status_code == 200

    after = {name: (isolated_session / name).read_bytes() for name in watched}
    assert before == after


def test_get_capabilities_event_returns_expected_capabilities(client: TestClient) -> None:
    event_id = _seed_event(client)
    response = client.get(
        "/api/live/capabilities",
        params={"target_type": "event", "target_id": event_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["target"]["target_type"] == "event"
    capabilities = body["capabilities"]
    append = next(cap for cap in capabilities if cap["command_type"] == "append_observation")
    queue = next(cap for cap in capabilities if cap["command_type"] == "queue_canon_patch")
    assert append["enabled"] is True
    assert append["disabled_reason"] is None
    assert append["required_fields"] == ["observation"]
    assert queue["enabled"] is False
    assert queue["disabled_reason"]


def test_get_capabilities_event_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/live/capabilities",
        params={"target_type": "event", "target_id": "evt-does-not-exist"},
    )
    assert response.status_code == 404


def test_get_capabilities_roll_table_returns_expected_capabilities(client: TestClient) -> None:
    response = client.get(
        "/api/live/capabilities",
        params={"target_type": "roll_table", "target_id": "T-WX"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["target"]["target_type"] == "roll_table"
    capabilities = body["capabilities"]
    append = next(cap for cap in capabilities if cap["command_type"] == "append_observation")
    patch = next(cap for cap in capabilities if cap["command_type"] == "patch_artifact")
    assert append["enabled"] is True
    assert append["disabled_reason"] is None
    assert append["required_fields"] == ["observation"]
    assert patch["enabled"] is True
    assert patch["disabled_reason"] is None
    assert patch["required_fields"] == ["expected_file_state_token", "old_text", "new_text"]


def test_get_capabilities_roll_table_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/live/capabilities",
        params={"target_type": "roll_table", "target_id": "T-DOES-NOT-EXIST"},
    )
    assert response.status_code == 404


def test_get_capabilities_unsupported_target_type_returns_422(client: TestClient) -> None:
    response = client.get(
        "/api/live/capabilities",
        params={"target_type": "npc", "target_id": "npc-1"},
    )
    assert response.status_code == 422


def test_get_capabilities_rejects_forbidden_path_query_fields(client: TestClient) -> None:
    response = client.get(
        "/api/live/capabilities",
        params={
            "target_type": "roll_table",
            "target_id": "T-WX",
            "absolute_path": "/etc/passwd",
        },
    )
    assert response.status_code == 422
