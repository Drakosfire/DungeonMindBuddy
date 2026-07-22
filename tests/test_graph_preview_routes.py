from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    mark_workspace_document_committed,
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.services.workspace_document_registry.repo_root",
        lambda: tmp_path,
        raising=False,
    )
    return TestClient(create_app())


def test_launch_requires_committed_source(client: TestClient, tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="Draft lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    response = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={"document_id": record.document_id, "expected_revision": record.revision},
    )
    assert response.status_code == 422
    assert "committed" in response.json()["detail"]


def test_launch_rejects_stale_revision(client: TestClient, tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Mirathorn is a river city.\n", encoding="utf-8")
    committed = mark_workspace_document_committed(tmp_path, record.document_id)
    response = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={"document_id": committed.document_id, "expected_revision": committed.revision - 1},
    )
    assert response.status_code == 409


def test_launch_returns_exact_run_and_status_reload(client: TestClient, tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Mirathorn is a river city.\n", encoding="utf-8")
    committed = mark_workspace_document_committed(tmp_path, record.document_id)

    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={"document_id": committed.document_id, "expected_revision": committed.revision},
    )
    assert launch.status_code == 200, launch.text
    payload = launch.json()
    run_id = payload["run"]["run_id"]
    assert payload["document_id"] == committed.document_id
    assert payload["graph_review_handoff"]["extraction_run_id"] == run_id
    assert "latest" not in payload["graph_review_handoff"]["href"]

    status = client.get(f"/api/live/graph-preview/extraction-runs/{run_id}")
    assert status.status_code == 200
    assert status.json()["run_id"] == run_id
