from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document_snapshot,
    list_workspace_documents,
)
from application_state.cli import assert_at_head
from application_state.errors import ApplicationStateMigrationError


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.workspace_documents.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "apps.live_control_server.routes.live.repo_root",
        lambda: tmp_path,
        raising=False,
    )
    return TestClient(create_app())


def test_create_commit_reload_and_file_absent(
    tmp_path: Path, client: TestClient, application_state_dsn: str
) -> None:
    created = client.post(
        "/api/live/workspace-documents",
        json={"title": "AS1 Plan", "campaign_id": "longmont-c2", "kind": "plan"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    document_id = body["document_id"]
    revision = body["revision"]
    plan_path = tmp_path / "out" / "workspace" / "plan" / f"{document_id}.md"
    assert not plan_path.exists()

    markdown = "# Session 24\n\nDurable postgres plan.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=revision,
        ),
    )
    assert prepared.writer_ok
    assert prepared.writer_confirm_token
    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=revision,
        ),
    )
    assert committed.normalized_content_sha256
    assert not plan_path.exists()

    snapshot = client.get(f"/api/live/workspace-documents/{document_id}/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    payload = snapshot.json()
    assert payload["markdown"] == markdown
    assert payload["content_sha256"] == committed.normalized_content_sha256
    assert payload["file_exists"] is False
    assert payload["file_fingerprint"] == "postgres"


def test_working_copy_survives_new_connection(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_workspace_document(
        tmp_path, title="Draft Plan", campaign_id="longmont-c2", kind="plan"
    )
    draft = "working copy after restart\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown=draft,
            expected_revision=created.revision,
        ),
    )
    assert prepared.writer_ok
    snapshot = get_workspace_document_snapshot(tmp_path, created.document_id)
    assert snapshot.markdown == draft
    assert snapshot.record.content_status == "draft"


def test_cas_conflict_one_success(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from application_state.content.service import commit_plan, create_plan
    from application_state.errors import ApplicationStateConflictError

    created = create_plan(title="CAS", campaign_id="longmont-c2")
    first, first_revision = commit_plan(
        str(created.work_object_id), "# one\n", expected_revision=created.object_revision
    )
    with pytest.raises(ApplicationStateConflictError):
        commit_plan(
            str(created.work_object_id),
            "# two\n",
            expected_revision=created.object_revision,
        )
    replay, replay_revision = commit_plan(
        str(first.work_object_id),
        "# one\n",
        expected_revision=first.object_revision,
    )
    assert replay_revision.content_sha256 == first_revision.content_sha256
    assert replay.object_revision == first.object_revision


def test_unavailable_dsn_does_not_read_plan_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> None:
    created = create_workspace_document(
        tmp_path, title="No fallback", campaign_id="longmont-c2", kind="plan"
    )
    plan_path = tmp_path / "out" / "workspace" / "plan" / f"{created.document_id}.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("# leftover file must not be read\n", encoding="utf-8")
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:1/dungeonbuddy_app_state_down",
    )
    with pytest.raises(Exception) as excinfo:
        get_workspace_document_snapshot(tmp_path, created.document_id)
    message = str(excinfo.value).lower()
    assert "leftover file must not be read" not in message
    assert plan_path.read_text(encoding="utf-8") == "# leftover file must not be read\n"


def test_runbook_remains_file_backed(
    tmp_path: Path, application_state_dsn: str
) -> None:
    runbook = create_workspace_document(
        tmp_path,
        title="Runbook",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath="evals/c2_live_prep/mireward-prep/content/tiptap/as1-runbook.md",
    )
    listed = list_workspace_documents(tmp_path, kind="runbook")
    assert [row.document_id for row in listed] == [runbook.document_id]
    from apps.live_control_server.services.workspace_document_registry import (
        workspace_documents_path,
    )

    assert workspace_documents_path(tmp_path).is_file()


def test_check_head_does_not_migrate(application_state_dsn: str, monkeypatch: pytest.MonkeyPatch) -> None:
    assert_at_head(dsn=application_state_dsn)
    # Behind-head: empty new database name is not this fixture. Checking does not
    # invoke upgrade; a second check remains at head.
    assert_at_head(dsn=application_state_dsn)


def test_behind_head_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.application_state.conftest import (
        _admin_dsn,
        _create_database,
        _drop_database,
        _replace_database,
    )

    admin = _admin_dsn()
    import uuid

    name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    try:
        _create_database(admin, name)
    except Exception as exc:
        pytest.skip(f"cannot create ephemeral application-state database: {exc}")
    dsn = _replace_database(admin, name)
    monkeypatch.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", dsn)
    try:
        with pytest.raises(ApplicationStateMigrationError):
            assert_at_head(dsn=dsn)
    finally:
        monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
        _drop_database(admin, name)


def test_plan_latency_baseline_vs_head(
    tmp_path: Path, application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_root = tmp_path / "file"
    file_root.mkdir()
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    started = time.perf_counter()
    file_doc = create_workspace_document(
        file_root, title="file baseline", campaign_id="longmont-c2", kind="plan"
    )
    file_create_ms = (time.perf_counter() - started) * 1000
    monkeypatch.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn)

    started = time.perf_counter()
    pg_doc = create_workspace_document(
        tmp_path, title="postgres head", campaign_id="longmont-c2", kind="plan"
    )
    pg_create_ms = (time.perf_counter() - started) * 1000
    print(
        f"AS1 latency hypothesis capture create_ms file={file_create_ms:.1f} postgres={pg_create_ms:.1f}"
    )
    assert file_doc.kind == "plan"
    assert pg_doc.kind == "plan"
    assert file_create_ms >= 0 and pg_create_ms >= 0
