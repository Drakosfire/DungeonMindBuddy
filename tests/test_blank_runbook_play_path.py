from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import get_play_run

pytest_plugins = ["tests.application_state.conftest"]

CAMPAIGN_ID = "dogfood-local"
RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
BEAT_ID = "beat:untitled"
BLANK_MARKDOWN = (
    f"<!-- dmb-playable-element:v2 kind=beat id={BEAT_ID} beat_kind=spine -->\n"
    "## Untitled Beat\n"
)

@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.workspace_documents.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "apps.live_control_server.routes.live.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
    )
    return TestClient(create_app())


def _http_create_and_commit(
    client: TestClient,
    *,
    title: str,
    markdown: str,
    campaign_id: str = CAMPAIGN_ID,
) -> dict:
    created = client.post(
        "/api/live/workspace-documents",
        json={
            "title": title,
            "campaign_id": campaign_id,
            "kind": "runbook",
        },
    )
    assert created.status_code == 200, created.text
    record = created.json()
    prepared = client.post(
        "/api/live/tiptap/markdown-write/prepare",
        json={
            "document_id": record["document_id"],
            "markdown": markdown,
            "expected_revision": record["revision"],
        },
    )
    assert prepared.status_code == 200, prepared.text
    body = prepared.json()
    assert body["writer_ok"] is True
    assert body["writer_confirm_token"]
    committed = client.post(
        "/api/live/tiptap/markdown-write/commit",
        json={
            "document_id": record["document_id"],
            "markdown": markdown,
            "writer_confirm_token": body["writer_confirm_token"],
            "expected_revision": record["revision"],
        },
    )
    assert committed.status_code == 200, committed.text
    return committed.json()["committed_record"]


def test_http_blank_runbook_create_does_not_start_a_run_then_standard_start_seeds_beat_only(
    client: TestClient, tmp_path: Path
) -> None:
    before_runs = client.get("/api/live/play-runs")
    assert before_runs.status_code == 200
    assert before_runs.json()["records"] == []

    record = _http_create_and_commit(
        client, title="Blank Runbook", markdown=BLANK_MARKDOWN
    )
    assert record["kind"] == "runbook"
    assert record["title"] == "Blank Runbook"
    assert record["campaign_id"] == CAMPAIGN_ID
    assert record["campaign_id"] != "longmont-c2"
    assert record["target_relpath"] is None
    assert record["content_status"] == "committed"

    listed = client.get(
        "/api/live/workspace-documents",
        params={"kind": "runbook", "status": "active"},
    )
    assert listed.status_code == 200
    assert [item["document_id"] for item in listed.json()["records"]] == [record["document_id"]]

    after_create_runs = client.get("/api/live/play-runs")
    assert after_create_runs.status_code == 200
    assert after_create_runs.json()["records"] == []

    committed = client.get(
        f"/api/live/workspace-documents/{record['document_id']}/committed-revision"
    )
    assert committed.status_code == 200
    playable = committed.json()
    assert playable["markdown"] == BLANK_MARKDOWN
    assert "kind=scene" not in playable["markdown"]
    assert "kind=choice" not in playable["markdown"]
    assert "kind=option" not in playable["markdown"]

    started = client.put(
        f"/api/live/play-runs/{RUN_ID}",
        json={
            "playable_artifact_id": record["document_id"],
            "expected_playable_revision": playable["revision_n"],
            "expected_playable_content_sha256": playable["content_sha256"],
        },
    )
    assert started.status_code == 200, started.text
    assert started.json()["campaign_id"] == CAMPAIGN_ID
    assert started.json()["progress"]["current_beat_id"] is None
    assert started.json()["progress"]["current_scene_id"] is None

    ready = client.get(
        f"/api/live/play-runs/{RUN_ID}",
        params={"ensure_native_ready": "true"},
    )
    assert ready.status_code == 200, ready.text
    progress = ready.json()["progress"]
    assert progress["current_beat_id"] == BEAT_ID
    assert progress["current_scene_id"] is None
    persisted = get_play_run(tmp_path, RUN_ID)
    assert persisted.progress.current_beat_id == BEAT_ID
    assert persisted.progress.current_scene_id is None

    resumed = client.get(
        f"/api/live/play-runs/{RUN_ID}",
        params={"ensure_native_ready": "true"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["progress"]["current_beat_id"] == BEAT_ID
    assert resumed.json()["progress"]["current_scene_id"] is None
    assert resumed.json()["run_revision"] == ready.json()["run_revision"]


def test_http_uncommitted_runbook_is_not_startable(client: TestClient) -> None:
    created = client.post(
        "/api/live/workspace-documents",
        json={
            "title": "Blank Runbook",
            "campaign_id": CAMPAIGN_ID,
            "kind": "runbook",
        },
    )
    assert created.status_code == 200, created.text
    record = created.json()
    assert record["content_status"] == "draft"

    missing = client.get(
        f"/api/live/workspace-documents/{record['document_id']}/committed-revision"
    )
    assert missing.status_code in {404, 409, 422}

    listed = client.get("/api/live/play-runs")
    assert listed.status_code == 200
    assert listed.json()["records"] == []
