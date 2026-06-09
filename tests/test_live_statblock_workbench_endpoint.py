from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app

ROOT = Path(__file__).resolve().parents[1]
LIVE_SESSION_FIXTURE = ROOT / "evals/c2_live_prep/live/session_22"


def test_statblock_workbench_sample_endpoint_returns_mock_artifact() -> None:
    client = TestClient(create_app())

    response = client.get("/api/live/statblocks/workbench/sample")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_statblock_workbench_sample_v1"
    assert body["mode"] == "sample_mock"
    assert body["command_status"] == "ok"
    assert body["diagnostics"]
    assert "MockStatBlockGeneratorProvider" in " ".join(body["diagnostics"])

    artifact = body["artifact"]
    assert artifact["markdown"]
    assert artifact["structured_statblock"]
    assert artifact["combat_defaults"]
    assert artifact["provenance"]
    assert artifact["breadcrumbs"]
    assert artifact["review_status"] == "needs_dm_review"
    assert artifact["lifecycle_state"] == "live_draft"
    assert artifact["storage_status"] == "not_stored"
    assert artifact["corpus_status"] == "not_promoted"
    assert artifact["source_refs"]

    actions = body["available_actions"]
    assert {action["action_id"] for action in actions} == {
        "store_draft",
        "preview_corpus_promotion",
        "promote_to_corpus",
        "ingest_to_semantic_layer",
        "add_to_combat",
    }
    assert all(action["enabled"] is False for action in actions)
    assert all(action["disabled_reason"] for action in actions)


def test_statblock_workbench_sample_endpoint_does_not_expose_internal_key(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    client = TestClient(create_app())

    response = client.get("/api/live/statblocks/workbench/sample")

    assert response.status_code == 200
    body_text = response.text
    assert "super-secret-test-key" not in body_text
    assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in body_text
    assert "DUNGEONMIND_SERVER_URL" not in body_text
    assert "X-DungeonBuddy-Internal-Key" not in body_text


def _post_workbench_command(client: TestClient, command_type: str):
    return client.post(
        "/api/live/statblocks/workbench/command",
        json={"command_type": command_type, "requested_by": "human", "as_artifact": True},
    )


def test_statblock_workbench_generate_command_returns_mock_artifact() -> None:
    client = TestClient(create_app())

    sample_response = client.get("/api/live/statblocks/workbench/sample")
    response = _post_workbench_command(client, "statblock.draft.generate")

    assert sample_response.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_statblock_workbench_command_v1"
    assert body["mode"] == "mock_command"
    assert body["command_status"] == "ok"
    assert body["artifact"]
    artifact = body["artifact"]
    assert artifact["title"] == "Generated Obsidian Thornling"
    assert artifact["title"] != sample_response.json()["artifact"]["title"]
    assert artifact["markdown"]
    assert artifact["combat_defaults"]
    assert artifact["lifecycle_state"] == "live_draft"
    assert artifact["storage_status"] == "not_stored"
    assert artifact["corpus_status"] == "not_promoted"
    assert all(action["enabled"] is False for action in body["available_actions"])
    diagnostics = " ".join(body["diagnostics"])
    assert "MockStatBlockGeneratorProvider" in diagnostics
    assert "non-persistent" in diagnostics


def test_statblock_workbench_render_command_returns_different_mock_artifact() -> None:
    client = TestClient(create_app())

    generate_response = _post_workbench_command(client, "statblock.draft.generate")
    render_response = _post_workbench_command(client, "statblock.draft.render")

    assert generate_response.status_code == 200
    assert render_response.status_code == 200
    generate_body = generate_response.json()
    render_body = render_response.json()
    render_artifact = render_body["artifact"]
    assert render_artifact["title"] != generate_body["artifact"]["title"]
    assert render_artifact["title"] == "Rendered Clockwork Mire Sentinel"
    assert render_artifact["provenance"]["mode"] == "render_existing"
    assert render_artifact["provenance"]["generation_info"]["generated"] is False
    diagnostics = " ".join(render_body["diagnostics"])
    assert "mock" in diagnostics.lower()
    assert "non-persistent" in diagnostics


def test_statblock_workbench_unsupported_command_is_rejected() -> None:
    client = TestClient(create_app())

    response = _post_workbench_command(client, "statblock.draft.store")

    assert response.status_code == 422


def test_statblock_workbench_command_endpoint_does_not_expose_internal_key(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    monkeypatch.setenv("DUNGEONMIND_SERVER_URL", "https://example.invalid")
    client = TestClient(create_app())

    responses = [
        _post_workbench_command(client, "statblock.draft.generate"),
        _post_workbench_command(client, "statblock.draft.render"),
    ]

    for response in responses:
        assert response.status_code == 200
        body_text = response.text
        assert "super-secret-test-key" not in body_text
        assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in body_text
        assert "DUNGEONMIND_SERVER_URL" not in body_text
        assert "X-DungeonBuddy-Internal-Key" not in body_text



def _temp_live_session(tmp_path: Path, monkeypatch) -> Path:
    session_dir = tmp_path / "session_22"
    shutil.copytree(LIVE_SESSION_FIXTURE, session_dir)
    drafts_dir = session_dir / "statblock_drafts"
    if drafts_dir.exists():
        shutil.rmtree(drafts_dir)
    monkeypatch.setenv(SESSION_DIR_ENV, str(session_dir))
    return session_dir


def _sample_artifact(client: TestClient) -> dict:
    response = client.get("/api/live/statblocks/workbench/sample")
    assert response.status_code == 200
    return response.json()["artifact"]


def test_statblock_workbench_store_list_and_read_draft(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    event_log_before = (session_dir / "event_log.jsonl").read_bytes()
    job_queue_before = (session_dir / "job_queue.jsonl").read_bytes()
    packet_before = (session_dir / "live_packet.json").read_bytes()
    layout_before = (session_dir / "surface_layout.json").read_bytes()
    client = TestClient(create_app())
    artifact = _sample_artifact(client)

    store_response = client.post(
        "/api/live/statblocks/workbench/drafts",
        json={"artifact": artifact, "source": "workbench"},
    )

    assert store_response.status_code == 200
    body = store_response.json()
    assert body["schema_version"] == "dmb_statblock_draft_store_v1"
    assert body["record"]["schema_version"] == "dmb_statblock_draft_record_v1"
    assert body["record"]["storage_path"] == f"statblock_drafts/{artifact['artifact_id']}.json"
    assert not Path(body["record"]["storage_path"]).is_absolute()
    stored_artifact = body["record"]["artifact"]
    assert stored_artifact["lifecycle_state"] == "stored_artifact"
    assert stored_artifact["storage_status"] == "stored_draft"
    assert stored_artifact["corpus_status"] == "not_promoted"
    assert stored_artifact["markdown"] == artifact["markdown"]
    assert stored_artifact["combat_defaults"] == artifact["combat_defaults"]
    assert stored_artifact["provenance"] == artifact["provenance"]
    assert (session_dir / "statblock_drafts" / f"{artifact['artifact_id']}.json").is_file()
    assert not (tmp_path / f"{artifact['artifact_id']}.json").exists()

    list_response = client.get("/api/live/statblocks/workbench/drafts")
    assert list_response.status_code == 200
    draft_summary = list_response.json()["drafts"][0]
    assert draft_summary["artifact_id"] == artifact["artifact_id"]
    assert draft_summary["title"] == artifact["title"]
    assert draft_summary["storage_status"] == "stored_draft"
    assert "markdown" not in draft_summary

    read_response = client.get(
        f"/api/live/statblocks/workbench/drafts/{artifact['artifact_id']}"
    )
    assert read_response.status_code == 200
    read_record = read_response.json()["record"]
    assert read_record["artifact"]["markdown"] == artifact["markdown"]
    assert read_record["artifact"]["source_refs"] == artifact["source_refs"]
    assert read_record["artifact"]["breadcrumbs"] == artifact["breadcrumbs"]

    assert (session_dir / "event_log.jsonl").read_bytes() == event_log_before
    assert (session_dir / "job_queue.jsonl").read_bytes() == job_queue_before
    assert (session_dir / "live_packet.json").read_bytes() == packet_before
    assert (session_dir / "surface_layout.json").read_bytes() == layout_before


def test_statblock_workbench_unsafe_draft_id_rejected(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    client = TestClient(create_app())
    artifact = _sample_artifact(client)

    for artifact_id in ["../evil", "nested/path", "/path", "~/.ssh/id_rsa", "https://evil"]:
        unsafe_artifact = {**artifact, "artifact_id": artifact_id}
        response = client.post(
            "/api/live/statblocks/workbench/drafts",
            json={"artifact": unsafe_artifact, "source": "workbench"},
        )
        assert response.status_code == 422
    assert not (session_dir / "evil.json").exists()
    assert not (session_dir / "statblock_drafts").exists()


def test_statblock_workbench_missing_draft_returns_404(tmp_path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    client = TestClient(create_app())

    response = client.get("/api/live/statblocks/workbench/drafts/not-found")

    assert response.status_code == 404


def test_statblock_workbench_draft_endpoints_do_not_expose_internal_key(
    tmp_path, monkeypatch
) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    monkeypatch.setenv("DUNGEONMIND_SERVER_URL", "https://example.invalid")
    client = TestClient(create_app())
    artifact = _sample_artifact(client)
    store_response = client.post(
        "/api/live/statblocks/workbench/drafts",
        json={"artifact": artifact, "source": "workbench"},
    )
    responses = [
        store_response,
        client.get("/api/live/statblocks/workbench/drafts"),
        client.get(f"/api/live/statblocks/workbench/drafts/{artifact['artifact_id']}"),
    ]

    for response in responses:
        assert response.status_code == 200
        body_text = response.text
        assert "super-secret-test-key" not in body_text
        assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in body_text
        assert "DUNGEONMIND_SERVER_URL" not in body_text
        assert "X-DungeonBuddy-Internal-Key" not in body_text
