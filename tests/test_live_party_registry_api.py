"""Tests for GET /api/live/party-registry."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.party_registry_surface import (
    PARTY_REGISTRY_SURFACE_SCHEMA,
    build_party_registry_surface,
)

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


def test_build_party_registry_surface_session_22_has_members() -> None:
    payload = build_party_registry_surface(campaign_id="longmont-c2", session=22)
    assert payload.schema_version == PARTY_REGISTRY_SURFACE_SCHEMA
    assert payload.session == 22
    assert payload.pc_slugs
    assert payload.companion_slugs
    assert any(m.slug == "captain_lysandra_ironveil" for m in payload.members)
    assert not payload.warnings
    assert payload.session_graph_context["session_id"] == "session-22"


def test_build_party_registry_surface_session_23_warns_missing_roster() -> None:
    payload = build_party_registry_surface(campaign_id="longmont-c2", session=23)
    assert payload.session == 23
    assert payload.members == []
    assert any("session_pc_rosters['23']" in w for w in payload.warnings)
    assert not payload.session_graph_context["anchor_members"]


def test_get_party_registry_api(client: TestClient) -> None:
    response = client.get(
        "/api/live/party-registry",
        params={"campaign_id": "longmont-c2", "session": 22},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == PARTY_REGISTRY_SURFACE_SCHEMA
    assert body["campaign_id"] == "longmont-c2"
    assert body["session"] == 22
    assert body["members"]
    assert body["session_graph_context"]["session_id"] == "session-22"


def test_get_party_registry_api_session_23_warnings(client: TestClient) -> None:
    response = client.get(
        "/api/live/party-registry",
        params={"campaign_id": "longmont-c2", "session": 23},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session"] == 23
    assert body["members"] == []
    assert any("session_pc_rosters['23']" in w for w in body["warnings"])
