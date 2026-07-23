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


def test_worldbuilding_source_issues_uuid_and_registry_owned_target(root: Path) -> None:
    created = create_workspace_document(
        root,
        title="Shepherd Cult Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="faction",
        authority_state="draft",
        visibility_state="internal",
    )

    uuid.UUID(created.document_id)
    assert created.kind == "worldbuilding_source"
    assert created.source_domain == "worldbuilding"
    assert created.document_class == "faction"
    assert created.authority_state == "draft"
    assert created.visibility_state == "internal"
    assert created.target_relpath == f"out/workspace/worldbuilding/{created.document_id}.md"
    assert created.target_session is None

    loaded = get_workspace_document(root, created.document_id)
    assert loaded.model_dump() == created.model_dump()


def test_worldbuilding_source_rejects_client_supplied_target(root: Path) -> None:
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="Bad",
            campaign_id="eldyrwild",
            kind="worldbuilding_source",
            target_relpath="corpus/eldyrwild-markdown/Elderwyld/escape.md",
            source_domain="worldbuilding",
            document_class="lore",
            authority_state="draft",
            visibility_state="internal",
        )
    assert exc_info.value.status_code == 422
    assert "registry-owned" in str(exc_info.value)


def test_worldbuilding_source_requires_explicit_metadata(root: Path) -> None:
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="Missing metadata",
            campaign_id="eldyrwild",
            kind="worldbuilding_source",
        )
    assert exc_info.value.status_code == 422


def test_worldbuilding_metadata_update_and_discard_restore(root: Path) -> None:
    created = create_workspace_document(
        root,
        title="Mirathorn",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="city",
        authority_state="draft",
        visibility_state="internal",
    )

    updated = update_workspace_document_metadata(
        root,
        created.document_id,
        authority_state="reviewed",
        visibility_state="player_safe",
        document_class="settlement",
        expected_revision=1,
    )
    assert updated.authority_state == "reviewed"
    assert updated.visibility_state == "player_safe"
    assert updated.document_class == "settlement"
    assert updated.revision == 2
    assert updated.target_relpath == created.target_relpath

    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        update_workspace_document_metadata(
            root,
            created.document_id,
            target_relpath="out/workspace/worldbuilding/nope.md",
            expected_revision=2,
        )
    assert exc_info.value.status_code == 422

    discarded = discard_workspace_document(root, created.document_id, expected_revision=2)
    assert discarded.status == "discarded"
    restored = restore_workspace_document(root, created.document_id, expected_revision=3)
    assert restored.status == "active"


def test_plan_rejects_worldbuilding_metadata(root: Path) -> None:
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="Plan",
            campaign_id="longmont-c2",
            kind="plan",
            source_domain="worldbuilding",
            document_class="plan",
            authority_state="draft",
            visibility_state="internal",
        )
    assert exc_info.value.status_code == 422


def test_api_worldbuilding_create_list_and_patch(client: TestClient) -> None:
    create_response = client.post(
        "/api/live/workspace-documents",
        json={
            "title": "API Worldbuilding",
            "campaign_id": "eldyrwild",
            "kind": "worldbuilding_source",
            "source_domain": "worldbuilding",
            "document_class": "lore",
            "authority_state": "draft",
            "visibility_state": "internal",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["kind"] == "worldbuilding_source"
    assert created["target_relpath"] == (
        f"out/workspace/worldbuilding/{created['document_id']}.md"
    )

    list_response = client.get(
        "/api/live/workspace-documents",
        params={"kind": "worldbuilding_source"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["records"]) == 1

    patch_response = client.patch(
        f"/api/live/workspace-documents/{created['document_id']}",
        json={"authority_state": "canonical", "expected_revision": 1},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["authority_state"] == "canonical"


def test_concurrent_commits_to_distinct_documents_preserve_both(root: Path) -> None:
    import threading

    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest,
        TiptapMarkdownWritePrepareRequest,
        commit_tiptap_markdown_write,
        prepare_tiptap_markdown_write,
    )

    docs = [
        create_workspace_document(
            root,
            title=f"Lore {idx}",
            campaign_id="eldyrwild",
            kind="worldbuilding_source",
            source_domain="worldbuilding",
            document_class="lore",
            authority_state="draft",
            visibility_state="internal",
        )
        for idx in range(2)
    ]
    markdowns = [f"# Lore {idx}\n\nBody {idx}.\n" for idx in range(2)]
    prepared = [
        prepare_tiptap_markdown_write(
            root=root,
            request=TiptapMarkdownWritePrepareRequest(
                document_id=doc.document_id,
                markdown=markdowns[idx],
                expected_revision=1,
            ),
        )
        for idx, doc in enumerate(docs)
    ]
    barrier = threading.Barrier(2)
    results: list[object] = []
    errors: list[BaseException] = []

    def worker(idx: int) -> None:
        barrier.wait()
        try:
            results.append(
                commit_tiptap_markdown_write(
                    root=root,
                    request=TiptapMarkdownWriteCommitRequest(
                        document_id=docs[idx].document_id,
                        markdown=markdowns[idx],
                        writer_confirm_token=prepared[idx].writer_confirm_token or "",
                        expected_revision=1,
                    ),
                )
            )
        except BaseException as exc:  # noqa: BLE001 - surface to main thread
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(idx,)) for idx in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()

    assert not errors
    assert len(results) == 2
    records = {
        get_workspace_document(root, doc.document_id).document_id: get_workspace_document(
            root, doc.document_id
        )
        for doc in docs
    }
    assert len(records) == 2
    for idx, doc in enumerate(docs):
        loaded = records[doc.document_id]
        assert loaded.content_status == "committed"
        assert loaded.revision == 2
        assert loaded.status == "active"
        target = root / loaded.target_relpath
        assert target.read_text(encoding="utf-8") == markdowns[idx]
    payload = (root / "out/registries/workspace_documents.json").read_text(encoding="utf-8")
    assert docs[0].document_id in payload
    assert docs[1].document_id in payload


def test_snapshot_draft_without_file_returns_empty_markdown(root: Path) -> None:
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )

    created = create_workspace_document(
        root,
        title="WB Draft",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    snapshot = get_workspace_document_snapshot(root, created.document_id)
    assert snapshot.record.document_id == created.document_id
    assert snapshot.loaded_revision == created.revision
    assert snapshot.file_exists is False
    assert snapshot.markdown == ""
    assert snapshot.content_sha256
    assert snapshot.file_fingerprint == "absent"


def test_snapshot_committed_missing_file_is_integrity_failure(root: Path) -> None:
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )

    created = create_workspace_document(
        root,
        title="WB Committed",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    mark_workspace_document_committed(root, created.document_id)
    with pytest.raises(WorkspaceDocumentRegistryError, match="missing"):
        get_workspace_document_snapshot(root, created.document_id)


def test_snapshot_api_returns_committed_markdown(client: TestClient, root: Path) -> None:
    created = create_workspace_document(
        root,
        title="WB with file",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    assert created.target_relpath is not None
    target = root / created.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "# Lore\n\nHello snapshot.\n"
    target.write_text(body, encoding="utf-8")
    mark_workspace_document_committed(root, created.document_id)

    response = client.get(f"/api/live/workspace-documents/{created.document_id}/snapshot")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["markdown"] == body.replace("\r\n", "\n").replace("\r", "\n")
    assert payload["file_exists"] is True
    assert payload["loaded_revision"] == payload["record"]["revision"]
    assert payload["content_sha256"]
