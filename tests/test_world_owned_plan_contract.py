from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.live_control_server.routes import live
from apps.live_control_server.routes import workspace_documents
from apps.live_control_server.services.workspace_document_registry import (
    CreateWorldOwnedPlanRequestV2,
)
from apps.live_control_server.services.world_container_registry import create_world_container


def test_managed_world_plan_context_v2_is_exact_and_non_authoritative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = create_world_container(tmp_path, name="Plan Contract World")
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)

    response = live.get_live_plan_view(world_id=world.world_id, scope_mode="world")

    assert response["schema_version"] == "dmb_managed_world_plan_context_v2"
    assert response["scope_mode"] == "world"
    assert response["world_id"] == world.world_id
    assert response["campaign_id"] is None
    assert response["session"] is None
    assert response["authoritative"] is False
    assert response["derived_from"] == ["managed_world_container"]
    assert response["timeline"] == []


def test_legacy_managed_plan_context_remains_v1_compatibility_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = create_world_container(tmp_path, name="Plan Contract World")
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)

    response = live.get_live_plan_view(world_id=world.world_id)

    assert response["schema_version"] == "dmb_managed_world_plan_context_v1"
    assert response["campaign_id"] == world.world_id
    assert response["session"] == 0


def test_world_context_requires_exact_world_id() -> None:
    with pytest.raises(HTTPException) as error:
        live.get_live_plan_view(world_id=None, scope_mode="world")
    assert error.value.status_code == 422


def _client(monkeypatch: pytest.MonkeyPatch, root: Path) -> TestClient:
    monkeypatch.setattr(workspace_documents, "repo_root", lambda: root)
    app = FastAPI()
    app.include_router(workspace_documents.router)
    app.include_router(live.router)
    return TestClient(app)


def test_world_plan_create_rejects_mixed_scope_fields_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = False

    def unexpected_create(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("invalid mixed-scope body reached create")

    monkeypatch.setattr(workspace_documents, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(workspace_documents, "create_world_owned_plan_v2", unexpected_create)
    client = _client(monkeypatch, tmp_path)
    response = client.post(
        "/api/live/workspace-documents/world-plans",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": "world-a",
            "title": "Plan",
            "campaign_id": "campaign-b",
            "kind": "runbook",
            "target_session": 7,
        },
    )

    assert response.status_code == 422
    assert called is False


def test_world_plan_inventory_rejects_campaign_selector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.get(
        "/api/live/workspace-documents/world-plans",
        params={"world_id": "world-a", "campaign_id": "campaign-b"},
    )

    assert response.status_code == 422


def test_create_world_owned_plan_request_forbids_ignored_fields() -> None:
    with pytest.raises(ValidationError):
        CreateWorldOwnedPlanRequestV2.model_validate(
            {
                "world_id": "world-a",
                "title": "Plan",
                "campaign_id": "campaign-b",
            }
        )


def test_world_plan_revision_and_mutation_routes_emit_v2_and_reject_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    world = create_world_container(tmp_path, name="Revision route world")
    client = _client(monkeypatch, tmp_path)
    created = client.post(
        "/api/live/workspace-documents/world-plans",
        json={
            "schema_version": "dmb_workspace_document_create_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "title": "Plan",
        },
    )
    assert created.status_code == 200
    record = created.json()
    document_id = record["document_id"]

    prepared = client.post(
        "/api/live/tiptap/markdown-write/prepare",
        json={
            "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": "# Saved Plan\n",
            "expected_revision": record["revision"],
        },
    )
    assert prepared.status_code == 200
    body = prepared.json()
    committed = client.post(
        "/api/live/tiptap/markdown-write/commit",
        json={
            "schema_version": "dmb_tiptap_markdown_write_commit_v2",
            "scope_mode": "world",
            "world_id": world.world_id,
            "document_id": document_id,
            "markdown": "# Saved Plan\n",
            "expected_revision": body["registry_revision"],
            "writer_confirm_token": body["writer_confirm_token"],
        },
    )
    assert committed.status_code == 200

    for path in (
        f"/api/live/workspace-documents/{document_id}/committed-revision",
        f"/api/live/workspace-documents/{document_id}/committed-revision/1",
    ):
        revision_response = client.get(path)
        assert revision_response.status_code == 200
        revision = revision_response.json()
        assert revision["schema_version"] == "dmb_workspace_committed_revision_v2"
        assert revision["world_id"] == world.world_id
        assert revision["campaign_id"] is None

    current = client.get(f"/api/live/workspace-documents/{document_id}").json()
    patched = client.patch(
        f"/api/live/workspace-documents/{document_id}",
        json={"title": "Renamed Plan", "expected_revision": current["revision"]},
    )
    assert patched.status_code == 200
    assert patched.json()["schema_version"] == "dmb_world_owned_plan_record_v2"

    current = patched.json()
    wrong_session = client.patch(
        f"/api/live/workspace-documents/{document_id}",
        json={"target_session": 7, "expected_revision": current["revision"]},
    )
    assert wrong_session.status_code == 422
    after_rejection = client.get(
        f"/api/live/workspace-documents/{document_id}/snapshot"
    ).json()
    assert after_rejection["record"]["target_session"] is None
    assert after_rejection["record"]["revision"] == current["revision"]

    discarded = client.post(
        f"/api/live/workspace-documents/{document_id}/discard",
        json={"expected_revision": current["revision"]},
    )
    assert discarded.status_code == 200
    assert discarded.json()["schema_version"] == "dmb_world_owned_plan_record_v2"
    restored = client.post(
        f"/api/live/workspace-documents/{document_id}/restore",
        json={"expected_revision": discarded.json()["revision"]},
    )
    assert restored.status_code == 200
    assert restored.json()["schema_version"] == "dmb_world_owned_plan_record_v2"
    assert restored.json()["world_id"] == world.world_id


def test_world_plan_migration_preserves_campaign_rows_and_refuses_unsafe_downgrade(
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    from alembic import command

    from application_state.cli import _current_and_head, alembic_config, upgrade_to_head
    import application_state.content.service as content_service
    from application_state.content.service import (
        autosave_plan,
        commit_plan,
        create_plan,
        create_world_plan,
        get_plan,
        snapshot_plan,
    )

    config = alembic_config()
    command.downgrade(config, "20260906_0006")
    current, _ = _current_and_head(application_state_dsn)
    assert current == "20260906_0006"

    # Seed ordinary historical campaign data while the prior schema is active;
    # only the head guard is bypassed so these calls use the same repository path.
    with monkeypatch.context() as migration_seed:
        migration_seed.setattr(content_service, "assert_at_head", lambda **_: None)
        plan = create_plan(title="Prior campaign Plan", campaign_id="campaign-old")
        autosaved = autosave_plan(
            str(plan.work_object_id), "# Retained before upgrade\n", expected_revision=1
        )
        committed, _ = commit_plan(
            str(plan.work_object_id),
            "# Retained before upgrade\n",
            expected_revision=autosaved.object_revision,
        )

    command.upgrade(config, "head")
    upgrade_to_head(dsn=application_state_dsn)
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20260928_0007"
    loaded = get_plan(str(committed.work_object_id))
    snapshot = snapshot_plan(str(committed.work_object_id))
    assert loaded.campaign_id == "campaign-old"
    assert loaded.world_id is None
    assert snapshot.markdown == "# Retained before upgrade\n"

    world_plan = create_world_plan(title="World Plan", world_id="world-a")
    with pytest.raises(Exception, match="cannot downgrade while World-owned Plans exist"):
        command.downgrade(config, "20260906_0006")
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20260928_0007"
    assert get_plan(str(world_plan.work_object_id)).world_id == "world-a"
