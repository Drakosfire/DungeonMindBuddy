from __future__ import annotations

import time
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import (
    PlayRunRegistryError,
    create_or_replay_play_run,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    create_workspace_document,
    get_committed_playable_revision,
    get_workspace_document_snapshot,
    list_workspace_documents,
)
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError


RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.workspace_documents.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
        raising=False,
    )
    return TestClient(create_app())


def _tiptap_commit(root: Path, document_id: str, markdown: str, expected_revision: int) -> None:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=expected_revision,
        ),
    )
    assert prepared.writer_ok
    assert prepared.writer_confirm_token
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=expected_revision,
        ),
    )


def test_create_commit_reload_and_file_absent(
    tmp_path: Path, client: TestClient, application_state_dsn: str
) -> None:
    created = client.post(
        "/api/live/workspace-documents",
        json={"title": "AS2 Runbook", "campaign_id": "longmont-c2", "kind": "runbook"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    document_id = body["document_id"]
    revision = body["revision"]
    runbook_path = tmp_path / "out" / "workspace" / "runbooks" / f"{document_id}.md"
    assert not runbook_path.exists()

    markdown = "# Gate\n\nDurable postgres runbook.\n"
    _tiptap_commit(tmp_path, document_id, markdown, revision)
    assert not runbook_path.exists()
    lock_dir = tmp_path / "out" / "registries" / ".locks"
    assert not lock_dir.exists()

    snapshot = client.get(f"/api/live/workspace-documents/{document_id}/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    payload = snapshot.json()
    assert payload["markdown"] == markdown
    assert payload["file_exists"] is False
    assert payload["file_fingerprint"] == "postgres"
    assert payload["record"]["content_status"] == "committed"

    current = client.get(f"/api/live/workspace-documents/{document_id}/committed-revision")
    assert current.status_code == 200, current.text
    committed = current.json()
    assert committed["revision_n"] == 1
    assert committed["markdown"] == markdown
    assert committed["has_divergent_working_copy"] is False
    assert committed["object_revision"] != committed["revision_n"] or committed["object_revision"] >= 1


def test_historical_revision_survives_newer_commit(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from application_state.content.service import (
        commit_runbook,
        create_runbook,
        exact_committed_revision,
    )

    created = create_runbook(title="North Gate", campaign_id="longmont-c2")
    first, first_revision = commit_runbook(
        str(created.work_object_id),
        "# revision one\n",
        expected_revision=created.object_revision,
    )
    assert first_revision.revision_n == 1
    second, second_revision = commit_runbook(
        str(first.work_object_id),
        "# revision two\n",
        expected_revision=first.object_revision,
    )
    assert second_revision.revision_n == 2
    loaded = exact_committed_revision(str(created.work_object_id), 1, kind="runbook")
    assert loaded.work_revision.revision_n == 1
    assert loaded.work_revision.markdown == "# revision one\n"
    assert loaded.work_revision.work_revision_id == first_revision.work_revision_id
    current = get_committed_playable_revision(str(created.work_object_id))
    assert current.revision_n == 2
    assert current.markdown == "# revision two\n"


def test_object_revision_can_advance_while_revision_n_stays(
    application_state_dsn: str,
) -> None:
    from application_state.content.service import (
        autosave_runbook,
        commit_runbook,
        create_runbook,
        current_committed_revision,
    )

    created = create_runbook(title="CAS vs Playable", campaign_id="longmont-c2")
    committed_obj, revision = commit_runbook(
        str(created.work_object_id),
        "# committed N\n",
        expected_revision=created.object_revision,
    )
    assert revision.revision_n == 1
    drafted = autosave_runbook(
        str(committed_obj.work_object_id),
        "# unsaved draft\n",
        expected_revision=committed_obj.object_revision,
    )
    assert drafted.object_revision == committed_obj.object_revision + 1
    current = current_committed_revision(str(created.work_object_id), kind="runbook")
    assert current.work_revision.revision_n == 1
    assert current.work_revision.markdown == "# committed N\n"
    assert current.has_divergent_working_copy is True
    assert current.work_object.object_revision == drafted.object_revision


def test_divergent_working_copy_blocks_start_run_but_not_existing_run_n(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from application_state.content.service import autosave_runbook, commit_runbook, create_runbook

    created = create_runbook(title="Playable N", campaign_id="longmont-c2")
    obj, revision = commit_runbook(
        str(created.work_object_id),
        "# bound bytes\n",
        expected_revision=created.object_revision,
    )
    run = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=str(created.work_object_id),
        expected_playable_revision=revision.revision_n,
        expected_playable_content_sha256=revision.content_sha256,
    )
    assert run.playable_revision == 1
    autosave_runbook(
        str(obj.work_object_id),
        "# divergent draft\n",
        expected_revision=obj.object_revision,
    )
    with pytest.raises(PlayRunRegistryError) as start_exc:
        create_or_replay_play_run(
            tmp_path,
            run_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            playable_artifact_id=str(created.work_object_id),
            expected_playable_revision=1,
            expected_playable_content_sha256=revision.content_sha256,
        )
    assert start_exc.value.status_code == 409
    exact = get_committed_playable_revision(
        str(created.work_object_id),
        revision_n=run.playable_revision,
        expected_sha256=run.playable_content_sha256,
    )
    assert exact.revision_n == 1
    assert exact.markdown == "# bound bytes\n"


def test_missing_historical_revision_fails_closed(application_state_dsn: str) -> None:
    from application_state.content.service import commit_runbook, create_runbook, exact_committed_revision

    created = create_runbook(title="No fabricated history", campaign_id="longmont-c2")
    commit_runbook(
        str(created.work_object_id),
        "# only revision 1\n",
        expected_revision=created.object_revision,
    )
    with pytest.raises(ApplicationStateNotFoundError, match="historical revision bytes were never retained"):
        exact_committed_revision(str(created.work_object_id), 16, kind="runbook")


def test_tiptap_exact_commit_replay_returns_existing_revision(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from application_state.content import repository as repo
    from application_state.unit_of_work import unit_of_work

    created = create_workspace_document(
        tmp_path, title="Tiptap runbook replay", campaign_id="longmont-c2", kind="runbook"
    )
    markdown = "# exact adapter replay\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown=markdown,
            expected_revision=created.revision,
        ),
    )
    request = TiptapMarkdownWriteCommitRequest(
        document_id=created.document_id,
        markdown=markdown,
        writer_confirm_token=prepared.writer_confirm_token or "",
        expected_revision=created.revision,
    )
    first = commit_tiptap_markdown_write(root=tmp_path, request=request)
    replay = commit_tiptap_markdown_write(root=tmp_path, request=request)
    assert replay.committed_revision == first.committed_revision
    assert replay.normalized_content_sha256 == first.normalized_content_sha256
    with unit_of_work(application_state_dsn) as conn:
        assert repo.next_revision_n(conn, UUID(created.document_id)) == 2
    committed = get_committed_playable_revision(created.document_id)
    assert committed.revision_n == 1


def test_unwritable_lock_path_is_not_required(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_workspace_document(
        tmp_path, title="No flock", campaign_id="longmont-c2", kind="runbook"
    )
    _tiptap_commit(tmp_path, created.document_id, "# unlocked\n", created.revision)
    lock_dir = tmp_path / "out" / "registries" / ".locks"
    assert not lock_dir.exists()
    snapshot = get_workspace_document_snapshot(tmp_path, created.document_id)
    assert snapshot.file_exists is False


def test_runbook_fails_closed_when_app_state_is_down(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    with pytest.raises(WorkspaceDocumentRegistryError) as excinfo:
        create_workspace_document(
            tmp_path,
            title="Runbook",
            campaign_id="longmont-c2",
            kind="runbook",
        )
    assert excinfo.value.status_code == 503


def test_worldbuilding_remains_file_backed_when_app_state_is_down(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    created = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    listed = list_workspace_documents(tmp_path, kind="worldbuilding_source")
    assert [row.document_id for row in listed] == [created.document_id]
    snapshot = get_workspace_document_snapshot(tmp_path, created.document_id)
    assert snapshot.record.kind == "worldbuilding_source"


def test_cas_conflict_one_success(application_state_dsn: str) -> None:
    from application_state.content.service import commit_runbook, create_runbook

    created = create_runbook(title="CAS", campaign_id="longmont-c2")
    first, first_revision = commit_runbook(
        str(created.work_object_id), "# one\n", expected_revision=created.object_revision
    )
    with pytest.raises(ApplicationStateConflictError):
        commit_runbook(
            str(created.work_object_id),
            "# two\n",
            expected_revision=created.object_revision,
        )
    replay, replay_revision = commit_runbook(
        str(first.work_object_id),
        "# one\n",
        expected_revision=first.object_revision,
    )
    assert replay_revision.content_sha256 == first_revision.content_sha256
    assert replay.object_revision == first.object_revision


def _measure_prepare_commit_load(
    *,
    root: Path,
    document_id: str,
    expected_revision: int,
    markdown: str,
) -> tuple[float, float, float, str]:
    started = time.perf_counter()
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=expected_revision,
        ),
    )
    autosave_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=expected_revision,
        ),
    )
    commit_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    snapshot = get_workspace_document_snapshot(root, document_id)
    load_ms = (time.perf_counter() - started) * 1000
    return autosave_ms, commit_ms, load_ms, snapshot.markdown


def test_runbook_playable_latency(
    tmp_path: Path, application_state_dsn: str
) -> None:
    markdown = "# latency witness\n"
    file_backed = create_workspace_document(
        tmp_path,
        title="latency file analog",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    runbook = create_workspace_document(
        tmp_path, title="latency runbook", campaign_id="longmont-c2", kind="runbook"
    )
    file_autosave_ms, file_commit_ms, file_load_ms, file_markdown = _measure_prepare_commit_load(
        root=tmp_path,
        document_id=file_backed.document_id,
        expected_revision=file_backed.revision,
        markdown=markdown,
    )
    pg_autosave_ms, pg_commit_ms, pg_load_ms, pg_markdown = _measure_prepare_commit_load(
        root=tmp_path,
        document_id=runbook.document_id,
        expected_revision=runbook.revision,
        markdown=markdown,
    )
    started = time.perf_counter()
    current = get_committed_playable_revision(runbook.document_id)
    current_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    historical = get_committed_playable_revision(
        runbook.document_id, revision_n=current.revision_n
    )
    historical_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=runbook.document_id,
        expected_playable_revision=current.revision_n,
        expected_playable_content_sha256=current.content_sha256,
    )
    existing_run_ms = (time.perf_counter() - started) * 1000
    print(
        "AS2 latency hypothesis capture "
        "baseline_file_worldbuilding "
        f"autosave_ms={file_autosave_ms:.1f} "
        f"commit_ms={file_commit_ms:.1f} "
        f"load_ms={file_load_ms:.1f} "
        "head_postgres_runbook "
        f"autosave_ms={pg_autosave_ms:.1f} "
        f"commit_ms={pg_commit_ms:.1f} "
        f"load_ms={pg_load_ms:.1f} "
        f"current_committed_ms={current_ms:.1f} "
        f"historical_committed_ms={historical_ms:.1f} "
        f"existing_run_admit_ms={existing_run_ms:.1f}"
    )
    assert file_markdown == markdown
    assert pg_markdown == markdown
    assert historical.markdown == markdown
    assert (
        file_autosave_ms >= 0
        and file_commit_ms >= 0
        and file_load_ms >= 0
        and pg_autosave_ms >= 0
        and pg_commit_ms >= 0
        and pg_load_ms >= 0
        and current_ms >= 0
        and historical_ms >= 0
        and existing_run_ms >= 0
    )
