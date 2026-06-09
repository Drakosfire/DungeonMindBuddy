from __future__ import annotations

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app


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

    response = _post_workbench_command(client, "statblock.draft.generate")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_statblock_workbench_command_v1"
    assert body["mode"] == "mock_command"
    assert body["command_status"] == "ok"
    assert body["artifact"]
    artifact = body["artifact"]
    assert artifact["title"] == "Geomantic Drake Juvenile"
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
