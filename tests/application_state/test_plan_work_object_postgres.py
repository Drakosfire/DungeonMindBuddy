from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    create_workspace_document,
    get_workspace_document_snapshot,
    list_workspace_documents,
)
from application_state.cli import assert_at_head
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateMigrationError,
)


def _schema_fingerprint(dsn: str) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn:
        schemas = tuple(
            row[0]
            for row in conn.execute(
                "SELECT nspname FROM pg_namespace "
                "WHERE nspname IN ('application_state', 'content') ORDER BY 1"
            )
        )
        tables = tuple(
            row[0]
            for row in conn.execute(
                """
                SELECT schemaname || '.' || tablename
                FROM pg_tables
                WHERE schemaname IN ('application_state', 'content')
                ORDER BY 1
                """
            )
        )
        version_table = conn.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'application_state'
                  AND table_name = 'schema_migrations'
            )
            """
        ).fetchone()
        has_version = bool(version_table and version_table[0])
    return schemas, tables, has_version


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
    lock_dir = tmp_path / "out" / "registries" / ".locks"
    assert not lock_dir.exists()

    snapshot = client.get(f"/api/live/workspace-documents/{document_id}/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    payload = snapshot.json()
    assert payload["markdown"] == markdown
    assert payload["content_sha256"] == committed.normalized_content_sha256
    assert payload["file_exists"] is False
    assert payload["file_fingerprint"] == "postgres"
    assert payload["record"]["content_status"] == "committed"


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


def test_divergent_working_copy_is_not_presented_as_committed(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from application_state.content.service import commit_plan, create_plan

    created = create_plan(title="Draft vs committed", campaign_id="longmont-c2")
    commit_plan(
        str(created.work_object_id),
        "# committed\n",
        expected_revision=created.object_revision,
    )
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=str(created.work_object_id),
            markdown="# recoverable draft\n",
        ),
    )
    assert prepared.writer_ok
    snapshot = get_workspace_document_snapshot(tmp_path, str(created.work_object_id))
    assert snapshot.markdown == "# recoverable draft\n"
    assert snapshot.record.content_status == "draft"


def test_cas_conflict_one_success(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from application_state.content.service import commit_plan, create_plan

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


def test_stale_cas_identical_commit_replay_returns_existing_revision(
    application_state_dsn: str,
) -> None:
    from application_state.content.service import commit_plan, create_plan
    from application_state.content import repository as repo
    from application_state.unit_of_work import unit_of_work

    created = create_plan(title="Stale replay", campaign_id="longmont-c2")
    first, first_revision = commit_plan(
        str(created.work_object_id),
        "# one\n",
        expected_revision=created.object_revision,
    )
    replay, replay_revision = commit_plan(
        str(created.work_object_id),
        "# one\n",
        expected_revision=created.object_revision,
    )
    assert replay_revision.work_revision_id == first_revision.work_revision_id
    assert replay.object_revision == first.object_revision
    dsn = application_state_dsn
    with unit_of_work(dsn) as conn:
        assert repo.next_revision_n(conn, created.work_object_id) == 2


def test_working_copy_cas_rejects_stale_autosave(
    application_state_dsn: str,
) -> None:
    from application_state.content.service import autosave_plan, create_plan, snapshot_plan

    created = create_plan(title="WC CAS", campaign_id="longmont-c2")
    first = autosave_plan(
        str(created.work_object_id),
        "# accepted draft\n",
        expected_revision=created.object_revision,
    )
    with pytest.raises(ApplicationStateConflictError):
        autosave_plan(
            str(created.work_object_id),
            "# stale overwrite\n",
            expected_revision=created.object_revision,
        )
    snapshot = snapshot_plan(str(created.work_object_id))
    assert snapshot.markdown == "# accepted draft\n"
    assert snapshot.from_working_copy is True
    assert first.object_revision == created.object_revision + 1


def test_transaction_failure_before_commit_leaves_no_partial_revision(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from application_state.content import repository as repo
    from application_state.content.service import commit_plan, create_plan, get_plan
    from application_state.unit_of_work import unit_of_work

    created = create_plan(title="Crash before COMMIT", campaign_id="longmont-c2")

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected failure before COMMIT")

    monkeypatch.setattr(repo, "update_work_object", _boom)
    with pytest.raises(RuntimeError, match="injected failure before COMMIT"):
        commit_plan(
            str(created.work_object_id),
            "# should not persist\n",
            expected_revision=created.object_revision,
        )

    after = get_plan(str(created.work_object_id))
    assert after.current_revision_id is None
    assert after.object_revision == created.object_revision
    with unit_of_work(application_state_dsn) as conn:
        assert repo.next_revision_n(conn, created.work_object_id) == 1


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


def test_missing_dsn_fails_closed_and_does_not_restore_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> None:
    from application_state.config import plan_kind_uses_postgres

    created = create_workspace_document(
        tmp_path, title="Switched", campaign_id="longmont-c2", kind="plan"
    )
    plan_path = tmp_path / "out" / "workspace" / "plan" / f"{created.document_id}.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("# must not become authority\n", encoding="utf-8")
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    assert plan_kind_uses_postgres() is True
    with pytest.raises(WorkspaceDocumentRegistryError) as excinfo:
        get_workspace_document_snapshot(tmp_path, created.document_id)
    assert excinfo.value.status_code == 503
    assert "must not become authority" not in str(excinfo.value)
    assert plan_path.read_text(encoding="utf-8") == "# must not become authority\n"


def test_runbook_remains_file_backed_when_app_state_is_down(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:1/dungeonbuddy_app_state_down",
    )
    runbook = create_workspace_document(
        tmp_path,
        title="Runbook",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath="evals/c2_live_prep/mireward-prep/content/tiptap/as1-runbook.md",
    )
    listed = list_workspace_documents(tmp_path, kind="runbook")
    assert [row.document_id for row in listed] == [runbook.document_id]
    snapshot = get_workspace_document_snapshot(tmp_path, runbook.document_id)
    assert snapshot.record.kind == "runbook"
    from apps.live_control_server.services.workspace_document_registry import (
        workspace_documents_path,
    )

    assert workspace_documents_path(tmp_path).is_file()


def test_authoring_canonicalizes_trailing_newlines_and_rejects_whitespace_only(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_workspace_document(
        tmp_path, title="Canonical", campaign_id="longmont-c2", kind="plan"
    )

    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown="# Missing newline",
            expected_revision=created.revision,
        ),
    )
    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=created.document_id,
            markdown="# Missing newline",
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=created.revision,
        ),
    )
    snapshot = get_workspace_document_snapshot(tmp_path, created.document_id)
    assert snapshot.markdown == "# Missing newline\n"
    assert snapshot.content_sha256 == committed.normalized_content_sha256

    excess = create_workspace_document(
        tmp_path, title="Excess newlines", campaign_id="longmont-c2", kind="plan"
    )
    prepared_excess = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=excess.document_id,
            markdown="# Extra\n\n\n",
            expected_revision=excess.revision,
        ),
    )
    commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=excess.document_id,
            markdown="# Extra\n\n\n",
            writer_confirm_token=prepared_excess.writer_confirm_token or "",
            expected_revision=excess.revision,
        ),
    )
    assert get_workspace_document_snapshot(tmp_path, excess.document_id).markdown == "# Extra\n"

    blank = create_workspace_document(
        tmp_path, title="Blank", campaign_id="longmont-c2", kind="plan"
    )
    with pytest.raises(TiptapMarkdownWriteError, match="markdown must not be empty"):
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id=blank.document_id,
                markdown="   \n",
                expected_revision=blank.revision,
            ),
        )


def test_plan_commit_succeeds_when_registry_lock_path_is_unwritable(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_workspace_document(
        tmp_path, title="No flock", campaign_id="longmont-c2", kind="plan"
    )
    registries = tmp_path / "out" / "registries"
    registries.mkdir(parents=True, exist_ok=True)
    (registries / ".locks").write_text("not a directory", encoding="utf-8")
    markdown = "# no filesystem lock\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown=markdown,
            expected_revision=created.revision,
        ),
    )
    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=created.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=created.revision,
        ),
    )
    assert committed.writer_ok is True
    snapshot = get_workspace_document_snapshot(tmp_path, created.document_id)
    assert snapshot.markdown == markdown


def test_check_head_does_not_migrate(application_state_dsn: str) -> None:
    before = _schema_fingerprint(application_state_dsn)
    assert_at_head(dsn=application_state_dsn)
    assert _schema_fingerprint(application_state_dsn) == before


def test_behind_head_fails_closed_without_mutating_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        pytest.fail(
            "AS1 owning-boundary tests require real disposable PostgreSQL; "
            f"could not create {name}: {exc}"
        )
    dsn = _replace_database(admin, name)
    monkeypatch.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", dsn)
    try:
        before = _schema_fingerprint(dsn)
        with pytest.raises(ApplicationStateMigrationError):
            assert_at_head(dsn=dsn)
        assert _schema_fingerprint(dsn) == before
        assert before == ((), (), False)
    finally:
        monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
        _drop_database(admin, name)


def test_plan_load_and_commit_latency(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_workspace_document(
        tmp_path, title="latency", campaign_id="longmont-c2", kind="plan"
    )
    markdown = "# latency witness\n"
    started = time.perf_counter()
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=created.document_id,
            markdown=markdown,
            expected_revision=created.revision,
        ),
    )
    autosave_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=created.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=created.revision,
        ),
    )
    commit_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    snapshot = get_workspace_document_snapshot(tmp_path, created.document_id)
    load_ms = (time.perf_counter() - started) * 1000
    print(
        "AS1 latency hypothesis capture "
        f"autosave_ms={autosave_ms:.1f} commit_ms={commit_ms:.1f} load_ms={load_ms:.1f}"
    )
    assert snapshot.markdown == markdown
    assert autosave_ms >= 0 and commit_ms >= 0 and load_ms >= 0
