from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.workspace_document_registry import (
    REGISTRY_SCHEMA,
    WorkspaceDocumentRegistryError,
    create_workspace_document,
    discard_workspace_document,
    get_workspace_document,
    list_workspace_documents,
    mark_workspace_document_committed,
    restore_workspace_document,
    update_workspace_document_metadata,
    workspace_documents_path,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.workspace_documents.repo_root",
        lambda: root,
    )
    return TestClient(create_app())


def test_create_issues_uuid_persists_and_get_round_trips(root: Path) -> None:
    created = create_workspace_document(
        root,
        title="Session 24 Plan",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=24,
    )

    uuid.UUID(created.document_id)
    assert created.revision == 1
    assert created.status == "active"
    assert created.content_status == "draft"
    assert workspace_documents_path(root).is_file()

    loaded = get_workspace_document(root, created.document_id)
    assert loaded.model_dump() == created.model_dump()


def test_list_filters_by_campaign_kind_and_status(root: Path) -> None:
    plan_a = create_workspace_document(
        root,
        title="Plan A",
        campaign_id="longmont-c2",
        kind="plan",
    )
    runbook_a = create_workspace_document(
        root,
        title="Runbook A",
        campaign_id="longmont-c2",
        kind="runbook",
    )
    plan_b = create_workspace_document(
        root,
        title="Plan B",
        campaign_id="longmont-c3",
        kind="plan",
    )
    discard_workspace_document(root, runbook_a.document_id)

    active = list_workspace_documents(root)
    assert {r.document_id for r in active} == {plan_a.document_id, plan_b.document_id}

    c2_active = list_workspace_documents(root, campaign_id="longmont-c2")
    assert {r.document_id for r in c2_active} == {plan_a.document_id}

    plans = list_workspace_documents(root, kind="plan", status=None)
    assert {r.document_id for r in plans} == {plan_a.document_id, plan_b.document_id}

    discarded = list_workspace_documents(root, status="discarded")
    assert {r.document_id for r in discarded} == {runbook_a.document_id}


def test_update_bumps_revision_and_stale_expected_revision_conflicts(root: Path) -> None:
    created = create_workspace_document(
        root,
        title="Original",
        campaign_id="longmont-c2",
        kind="plan",
    )

    updated = update_workspace_document_metadata(
        root,
        created.document_id,
        title="Renamed",
        expected_revision=1,
    )
    assert updated.title == "Renamed"
    assert updated.revision == 2

    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        update_workspace_document_metadata(
            root,
            created.document_id,
            title="Too Late",
            expected_revision=1,
        )
    assert exc_info.value.status_code == 409


def test_discard_retains_record_and_restore_brings_back(root: Path) -> None:
    created = create_workspace_document(
        root,
        title="Disposable",
        campaign_id="longmont-c2",
        kind="runbook",
    )

    discarded = discard_workspace_document(root, created.document_id)
    assert discarded.status == "discarded"
    assert discarded.revision == 2

    still_there = get_workspace_document(root, created.document_id)
    assert still_there.status == "discarded"
    assert list_workspace_documents(root) == []

    restored = restore_workspace_document(root, created.document_id)
    assert restored.status == "active"
    assert restored.revision == 3
    assert list_workspace_documents(root) == [restored]


def test_invalid_uuid_raises_422(client: TestClient) -> None:
    response = client.get("/api/live/workspace-documents/not-a-uuid")
    assert response.status_code == 422
    assert "invalid document_id" in response.json()["detail"]


def test_unknown_document_raises_404(client: TestClient) -> None:
    missing_id = str(uuid.uuid4())
    response = client.get(f"/api/live/workspace-documents/{missing_id}")
    assert response.status_code == 404
    assert "workspace document not found" in response.json()["detail"]


def test_empty_title_rejected_on_create(client: TestClient) -> None:
    response = client.post(
        "/api/live/workspace-documents",
        json={
            "title": "   ",
            "campaign_id": "longmont-c2",
            "kind": "plan",
        },
    )
    assert response.status_code == 422
    assert "title is required" in response.json()["detail"]


def test_api_create_list_and_patch(client: TestClient) -> None:
    create_response = client.post(
        "/api/live/workspace-documents",
        json={
            "title": "API Plan",
            "campaign_id": "longmont-c2",
            "kind": "plan",
            "target_session": 22,
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["schema_version"] == "dmb_workspace_document_record_v1"
    assert created["title"] == "API Plan"

    list_response = client.get(
        "/api/live/workspace-documents",
        params={"campaign_id": "longmont-c2", "kind": "plan"},
    )
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["schema_version"] == REGISTRY_SCHEMA
    assert len(payload["records"]) == 1

    patch_response = client.patch(
        f"/api/live/workspace-documents/{created['document_id']}",
        json={"title": "API Plan v2", "expected_revision": 1},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "API Plan v2"
    assert patch_response.json()["revision"] == 2

    stale_patch = client.patch(
        f"/api/live/workspace-documents/{created['document_id']}",
        json={"title": "Stale", "expected_revision": 1},
    )
    assert stale_patch.status_code == 409


def test_mark_committed_sets_content_status_and_bumps_revision(root: Path) -> None:
    created = create_workspace_document(
        root,
        title="Commit me",
        campaign_id="longmont-c2",
        kind="plan",
        target_relpath="evals/c2_live_prep/mireward-prep/content/tiptap/spike.md",
    )
    assert created.content_status == "draft"

    committed = mark_workspace_document_committed(
        root,
        created.document_id,
        expected_revision=1,
    )
    assert committed.content_status == "committed"
    assert committed.revision == 2

    loaded = get_workspace_document(root, created.document_id)
    assert loaded.content_status == "committed"
    assert loaded.revision == 2


def test_mark_committed_stale_expected_revision_conflicts(root: Path) -> None:
    created = create_workspace_document(
        root,
        title="Commit me",
        campaign_id="longmont-c2",
        kind="plan",
    )
    update_workspace_document_metadata(
        root,
        created.document_id,
        title="Updated",
        expected_revision=1,
    )

    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        mark_workspace_document_committed(
            root,
            created.document_id,
            expected_revision=1,
        )
    assert exc_info.value.status_code == 409
