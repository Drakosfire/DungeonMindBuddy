from __future__ import annotations
from tests.page_fixtures import create_page_fixture, save_page
from apps.live_control_server.services.workspace_document_registry import get_workspace_document

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.workspace_document_registry import (REGISTRY_SCHEMA, WorkspaceDocumentRecord, WorkspaceDocumentRegistryError, create_workspace_document, discard_workspace_document, list_workspace_documents, restore_workspace_document, update_workspace_document_metadata, workspace_documents_path)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.workspace_documents.repo_root",
        lambda: root,
    )
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    return TestClient(create_app(), client=("127.0.0.1", 50000))


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
    assert not workspace_documents_path(root).exists()

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


def test_update_bumps_revision_and_stale_expected_revision_conflicts(
    root: Path,
) -> None:
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
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest,
        TiptapMarkdownWritePrepareRequest,
        commit_tiptap_markdown_write,
        prepare_tiptap_markdown_write,
    )

    created = create_workspace_document(
        root,
        title="Commit me",
        campaign_id="longmont-c2",
        kind="plan",
    )
    assert created.content_status == "draft"
    markdown = "# committed via Tiptap\n"
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown=markdown,
            expected_revision=created.revision,
        ),
    )
    committed = commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=created.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=created.revision,
        ),
    )
    assert committed.committed_record.content_status == "committed"
    loaded = get_workspace_document(root, created.document_id)
    assert loaded.content_status == "committed"


def test_mark_committed_stale_expected_revision_conflicts(root: Path) -> None:
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest,
        TiptapMarkdownWriteConflictError,
        TiptapMarkdownWritePrepareRequest,
        commit_tiptap_markdown_write,
        prepare_tiptap_markdown_write,
    )

    created = create_workspace_document(
        root,
        title="Commit me",
        campaign_id="longmont-c2",
        kind="plan",
    )
    markdown = "# stale token\n"
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown=markdown,
            expected_revision=created.revision,
        ),
    )
    after_prepare = get_workspace_document(root, created.document_id)
    update_workspace_document_metadata(
        root,
        created.document_id,
        title="Updated",
        expected_revision=after_prepare.revision,
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit_tiptap_markdown_write(
            root=root,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=created.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=created.revision,
            ),
        )


def _worldbuilding_source(
    root: Path, *, title: str = "Shepherd Cult Lore"
) -> WorkspaceDocumentRecord:
    return create_page_fixture(
        root,
        title=title,
        campaign_id="longmont-c2",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )










def test_worldbuilding_source_rejects_unsafe_world_id(root: Path) -> None:
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="Bad",
            campaign_id="longmont-c2",
            kind="worldbuilding_source",
            world_id="../../tmp",
            source_domain="worldbuilding",
            document_class="lore",
            authority_state="draft",
            visibility_state="internal",
        )
    assert exc_info.value.status_code == 422
    assert "world_id" in str(exc_info.value)




def test_worldbuilding_source_succeeds_without_world_directory(
    root: Path,
) -> None:
    """Registered World membership is sufficient; Save creates body directories."""
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    world = create_world_container(root, name="Managed Compose World")
    assert not (root / world.source_root_relpath).exists()
    created = create_page_fixture(
        root,
        title="First managed source",
        campaign_id=world.world_id,
        kind="worldbuilding_source",
        world_id=world.world_id,
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    assert created.world_id == world.world_id
    assert created.campaign_id == world.world_id
    assert created.target_relpath is None




def test_worldbuilding_source_rejects_client_supplied_target(root: Path) -> None:
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_page_fixture(
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
    assert "not caller-assigned" in str(exc_info.value)


def test_worldbuilding_source_requires_explicit_metadata(root: Path) -> None:
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_page_fixture(
            root,
            title="Missing metadata",
            campaign_id="eldyrwild",
            kind="worldbuilding_source",
        )
    assert exc_info.value.status_code == 422


def test_worldbuilding_metadata_update_and_discard_restore(root: Path) -> None:
    created = create_page_fixture(
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

    discarded = discard_workspace_document(
        root, created.document_id, expected_revision=2
    )
    assert discarded.status == "discarded"
    restored = restore_workspace_document(
        root, created.document_id, expected_revision=3
    )
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


@pytest.mark.parametrize("campaign_id", [None, "longmont-c2"])
def test_api_worldbuilding_create_list_and_patch(client: TestClient, campaign_id: str | None) -> None:
    from application_state.world_catalog.service import create_world
    create_world(name="Eldyrwild")
    create_response = client.post(
        "/api/live/workspace-documents",
        json={
            "title": "API Worldbuilding",
            "world_id": "eldyrwild",
            "campaign_id": campaign_id,
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
    assert created["target_relpath"] is None

    list_response = client.get(
        "/api/live/workspace-documents",
        params={"kind": "worldbuilding_source", "world_id": "eldyrwild"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["records"]) == 1

    patch_response = client.patch(
        f"/api/live/workspace-documents/{created['document_id']}",
        json={"authority_state": "canonical", "expected_revision": 1},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["authority_state"] == "canonical"




def test_snapshot_draft_without_file_returns_empty_markdown(root: Path) -> None:
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )

    created = create_page_fixture(
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
    assert snapshot.file_fingerprint == "postgres"




def test_snapshot_api_returns_committed_markdown(
    client: TestClient, root: Path
) -> None:
    created = create_page_fixture(
        root,
        title="WB with file",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    assert created.target_relpath is None
    body = "# Lore\n\nHello snapshot.\n"
    created = save_page(root, created.document_id, body)
    get_workspace_document(root, created.document_id)

    response = client.get(
        f"/api/live/workspace-documents/{created.document_id}/snapshot"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["markdown"] == body.replace("\r\n", "\n").replace("\r", "\n")
    assert payload["file_exists"] is False
    assert payload["loaded_revision"] == payload["record"]["revision"]
    assert payload["content_sha256"]




def test_commit_receipt_matches_snapshot_fingerprint(root: Path) -> None:
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest,
        TiptapMarkdownWritePrepareRequest,
        commit_tiptap_markdown_write,
        prepare_tiptap_markdown_write,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )

    created = create_page_fixture(
        root,
        title="Receipt Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Lore\n\nReceipt body.\n"
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown=markdown,
            expected_revision=created.revision,
        ),
    )
    receipt = commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=created.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=created.revision,
        ),
    )
    snapshot = get_workspace_document_snapshot(root, created.document_id)
    assert receipt.committed_revision == snapshot.loaded_revision
    assert receipt.normalized_content_sha256 == snapshot.content_sha256
    assert receipt.file_fingerprint == snapshot.file_fingerprint
    assert receipt.committed_record.document_id == snapshot.record.document_id


def test_create_rejects_duplicate_non_null_target_relpath(root: Path) -> None:

    target = "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 28 Prep.md"
    first = create_workspace_document(
        root,
        title="C2 Session 28 Prep",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=28,
        target_relpath=target,
    )
    before_count = len(list_workspace_documents(root, status=None))

    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="C2 Session 28 Prep again",
            campaign_id="longmont-c2",
            kind="plan",
            target_session=28,
            target_relpath=target,
        )

    assert exc_info.value.status_code == 409
    assert first.document_id in str(exc_info.value)
    assert len(list_workspace_documents(root, status=None)) == before_count

    second = create_workspace_document(
        root,
        title="C2 Session 29 Prep",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=29,
        target_relpath=target.replace("Session 28", "Session 29"),
    )
    assert second.document_id != first.document_id
    assert second.target_relpath != first.target_relpath


def test_create_rejects_target_relpath_owned_by_discarded_document(root: Path) -> None:
    target = "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 30 Prep.md"
    first = create_workspace_document(
        root,
        title="C2 Session 30 Prep",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=30,
        target_relpath=target,
    )
    discard_workspace_document(root, first.document_id)

    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="C2 Session 30 Prep revived",
            campaign_id="longmont-c2",
            kind="plan",
            target_session=30,
            target_relpath=target,
        )

    assert exc_info.value.status_code == 409
    assert first.document_id in str(exc_info.value)
















def test_plan_metadata_rejects_target_relpath_transition(root: Path) -> None:
    workspace = create_workspace_document(
        root,
        title="If the party goes north",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=27,
    )
    assert workspace.target_relpath == f"out/workspace/plan/{workspace.document_id}.md"
    before = get_workspace_document(root, workspace.document_id)
    canonical = (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/"
        "Session Prep/Session 27 Prep.md"
    )

    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        update_workspace_document_metadata(
            root,
            workspace.document_id,
            target_relpath=canonical,
            expected_revision=before.revision,
        )
    assert exc_info.value.status_code == 422
    assert "cannot be changed via metadata update" in str(exc_info.value)

    after = get_workspace_document(root, workspace.document_id)
    assert after.model_dump() == before.model_dump()


def test_plan_create_omitted_path_assigns_uuid_workspace_target(root: Path) -> None:
    first = create_workspace_document(
        root,
        title="If the party goes north",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=27,
    )
    second = create_workspace_document(
        root,
        title="If the siege breaks",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=27,
    )
    assert first.document_id != second.document_id
    assert first.target_session == second.target_session == 27
    assert first.target_relpath == f"out/workspace/plan/{first.document_id}.md"
    assert second.target_relpath == f"out/workspace/plan/{second.document_id}.md"
    assert first.status == second.status == "active"


def test_plan_create_explicit_canonical_path_remains_supported(root: Path) -> None:
    canonical = (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/"
        "Session Prep/Session 50 Prep.md"
    )
    created = create_workspace_document(
        root,
        title="Canonical Session 50",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=50,
        target_relpath=canonical,
    )
    assert created.target_relpath == canonical
    assert created.status == "active"


def test_plan_create_rejects_arbitrary_explicit_path_without_record(root: Path) -> None:
    before = list_workspace_documents(root)
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="Illegal path",
            campaign_id="longmont-c2",
            kind="plan",
            target_session=27,
            target_relpath="corpus/eldyrwild-markdown/Longmont Campaign/escape.md",
        )
    assert exc_info.value.status_code == 422
    assert "plan target_relpath must match" in str(exc_info.value)
    assert list_workspace_documents(root) == before


def test_plan_create_rejects_foreign_workspace_uuid_path_without_record(
    root: Path,
) -> None:
    foreign = "out/workspace/plan/11111111-1111-4111-8111-111111111111.md"
    before = list_workspace_documents(root)
    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        create_workspace_document(
            root,
            title="Foreign workspace path",
            campaign_id="longmont-c2",
            kind="plan",
            target_session=27,
            target_relpath=foreign,
        )
    assert exc_info.value.status_code == 422
    assert "plan target_relpath must match" in str(exc_info.value)
    assert list_workspace_documents(root) == before


def test_api_plan_create_rejects_illegal_explicit_path(
    client: TestClient,
    root: Path,
) -> None:
    response = client.post(
        "/api/live/workspace-documents",
        json={
            "title": "API illegal Plan path",
            "campaign_id": "longmont-c2",
            "kind": "plan",
            "target_session": 27,
            "target_relpath": "out/workspace/plan/not-a-uuid.md",
        },
    )
    assert response.status_code == 422
    assert list_workspace_documents(root) == []


def test_plan_workspace_create_ignores_discarded_canonical_owner(root: Path) -> None:
    canonical = (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/"
        "Session Prep/Session 23 Prep.md"
    )
    discarded = create_workspace_document(
        root,
        title="Old Session 23",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=23,
        target_relpath=canonical,
    )
    discard_workspace_document(root, discarded.document_id)

    created = create_workspace_document(
        root,
        title="Workspace Session 23 sketch",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=23,
    )
    assert created.target_relpath == f"out/workspace/plan/{created.document_id}.md"
    assert created.status == "active"


def test_api_patch_rejects_plan_target_relpath_promotion(
    client: TestClient,
    root: Path,
) -> None:
    created = create_workspace_document(
        root,
        title="Workspace draft",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=27,
    )
    before = get_workspace_document(root, created.document_id)
    canonical = (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/"
        "Session Prep/Session 27 Prep.md"
    )

    response = client.patch(
        f"/api/live/workspace-documents/{created.document_id}",
        json={"target_relpath": canonical, "expected_revision": before.revision},
    )
    assert response.status_code == 422
    assert "cannot be changed via metadata update" in response.json()["detail"]

    after = get_workspace_document(root, created.document_id)
    assert after.model_dump() == before.model_dump()


def test_api_patch_rejects_duplicate_target_relpath_including_discarded_owner(
    client: TestClient,
    root: Path,
) -> None:
    path_a = "evals/c2_live_prep/mireward-prep/content/tiptap/api-unique-a.md"
    path_b = "evals/c2_live_prep/mireward-prep/content/tiptap/api-unique-b.md"
    owner = create_workspace_document(
        root,
        title="Discarded owner",
        campaign_id="longmont-c2",
        kind="runbook",
        target_session=45,
        target_relpath=path_a,
    )
    discard_workspace_document(root, owner.document_id)
    other = create_workspace_document(
        root,
        title="Active other",
        campaign_id="longmont-c2",
        kind="runbook",
        target_session=46,
        target_relpath=path_b,
    )
    before = get_workspace_document(root, other.document_id)

    response = client.patch(
        f"/api/live/workspace-documents/{other.document_id}",
        json={"target_relpath": path_a, "expected_revision": before.revision},
    )
    assert response.status_code == 422
    assert "cannot be changed via metadata update" in response.json()["detail"]

    after = get_workspace_document(root, other.document_id)
    assert after.model_dump() == before.model_dump()


def test_current_world_plan_revision_delegates_all_pins_to_content_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from application_state.content import service as content_service
    from apps.live_control_server.services import (
        workspace_document_registry as registry,
    )

    document_id = str(uuid.uuid4())
    expected = SimpleNamespace(markdown="# committed\n")
    observed: dict[str, object] = {}

    def read_current(document: str, **kwargs: object) -> SimpleNamespace:
        observed["document_id"] = document
        observed.update(kwargs)
        return expected

    monkeypatch.setattr(
        content_service, "read_current_world_plan_revision", read_current
    )

    result = registry.get_current_world_plan_revision(
        document_id,
        expected_world_id="world-1",
        expected_revision=7,
        expected_revision_n=4,
        expected_content_sha256="b" * 64,
    )

    assert result is expected
    assert observed == {
        "document_id": document_id,
        "expected_world_id": "world-1",
        "expected_revision": 7,
        "expected_revision_n": 4,
        "expected_content_sha256": "b" * 64,
    }


def test_current_world_plan_revision_maps_content_conflict_to_registry_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from application_state.content import service as content_service
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services import (
        workspace_document_registry as registry,
    )

    def reject(*_args: object, **_kwargs: object) -> None:
        raise ApplicationStateConflictError("World Plan digest changed")

    monkeypatch.setattr(content_service, "read_current_world_plan_revision", reject)

    with pytest.raises(WorkspaceDocumentRegistryError) as exc_info:
        registry.get_current_world_plan_revision(
            str(uuid.uuid4()),
            expected_world_id="world-1",
            expected_revision=7,
            expected_revision_n=4,
            expected_content_sha256="b" * 64,
        )

    assert exc_info.value.status_code == 409
    assert "digest changed" in str(exc_info.value)

pytestmark = pytest.mark.usefixtures("application_state_dsn")
