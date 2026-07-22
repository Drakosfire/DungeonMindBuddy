from __future__ import annotations

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app


def test_readiness_route_reports_disabled_without_secrets(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DUNGEONMIND_STATBLOCKS_ENABLED", "false")
    monkeypatch.delenv("DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY", raising=False)
    client = TestClient(create_app())
    response = client.get("/api/live/statblocks/v1/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "dmb_statblock_integration_readiness_v1"
    assert payload["configured"] is False
    assert payload["available"] is False
    assert payload["diagnostics"] == ["integration_disabled"]
    assert "super-secret" not in response.text
