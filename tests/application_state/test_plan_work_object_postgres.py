from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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


def test_current_world_plan_read_returns_immutable_basis_and_divergence(
    application_state_dsn: str,
) -> None:
    from application_state.content.service import (
        autosave_plan,
        commit_plan,
        create_world_plan,
        read_current_world_plan_revision,
    )

    world_id = "world-current-plan-read"
    created = create_world_plan(title="Current Plan", world_id=world_id)
    body = "# Committed fact\n\nThe sealed phrase is amber lantern.\n"
    committed_obj, committed = commit_plan(
        str(created.work_object_id), body, expected_world_id=world_id
    )
    autosave_plan(
        str(created.work_object_id),
        "# Uncommitted draft\n\nThis is not sent.\n",
        expected_world_id=world_id,
    )

    result = read_current_world_plan_revision(
        str(created.work_object_id),
        expected_world_id=world_id,
        expected_revision_n=committed.revision_n,
        expected_sha256=committed.content_sha256,
    )

    assert result.markdown == body
    assert result.world_id == world_id
    assert result.document_id == created.work_object_id
    assert result.work_revision_id == committed.work_revision_id
    assert result.revision_n == committed.revision_n
    assert result.content_sha256 == committed.content_sha256
    assert result.committed_status == "committed"
    assert result.has_divergent_working_copy is True
    assert committed_obj.current_revision_id == result.work_revision_id


def test_current_world_plan_read_rejects_wrong_owner_kind_and_status(
    application_state_dsn: str,
) -> None:
    from application_state.content.service import (
        commit_plan,
        create_world_plan,
        create_world_runbook,
        read_current_world_plan_revision,
        update_plan_metadata,
    )
    from application_state.errors import (
        ApplicationStateConflictError,
        ApplicationStateNotFoundError,
    )

    world_id = "world-current-plan-owner-check"
    created = create_world_plan(title="Owned Plan", world_id=world_id)
    _, committed = commit_plan(
        str(created.work_object_id), "# Current\n", expected_world_id=world_id
    )
    pin = {
        "expected_revision_n": committed.revision_n,
        "expected_sha256": committed.content_sha256,
    }
    with pytest.raises(ApplicationStateConflictError, match="not owned"):
        read_current_world_plan_revision(
            str(created.work_object_id), expected_world_id="another-world", **pin
        )

    runbook = create_world_runbook(title="Not a Plan", world_id=world_id)
    with pytest.raises(ApplicationStateNotFoundError, match="workspace document not found"):
        read_current_world_plan_revision(
            str(runbook.work_object_id), expected_world_id=world_id, **pin
        )

    discarded = update_plan_metadata(
        str(created.work_object_id), status="discarded"
    )
    assert discarded.status == "discarded"
    with pytest.raises(ApplicationStateConflictError, match="not active"):
        read_current_world_plan_revision(
            str(created.work_object_id), expected_world_id=world_id, **pin
        )


def test_current_world_plan_read_requires_current_pinned_commit(
    application_state_dsn: str,
) -> None:
    from application_state.content.service import (
        commit_plan,
        create_world_plan,
        read_current_world_plan_revision,
    )
    from application_state.errors import ApplicationStateConflictError

    world_id = "world-current-plan-pin-check"
    uncommitted = create_world_plan(title="No commit", world_id=world_id)
    with pytest.raises(ApplicationStateConflictError, match="no current committed"):
        read_current_world_plan_revision(
            str(uncommitted.work_object_id),
            expected_world_id=world_id,
            expected_revision_n=1,
            expected_sha256="a" * 64,
        )

    created = create_world_plan(title="Revisioned", world_id=world_id)
    _, first = commit_plan(
        str(created.work_object_id), "# First\n", expected_world_id=world_id
    )
    _, second = commit_plan(
        str(created.work_object_id), "# Second\n", expected_world_id=world_id
    )
    with pytest.raises(ApplicationStateConflictError, match="revision number"):
        read_current_world_plan_revision(
            str(created.work_object_id),
            expected_world_id=world_id,
            expected_revision_n=first.revision_n,
            expected_sha256=first.content_sha256,
        )
    with pytest.raises(ApplicationStateConflictError, match="SHA"):
        read_current_world_plan_revision(
            str(created.work_object_id),
            expected_world_id=world_id,
            expected_revision_n=second.revision_n,
            expected_sha256="0" * 64,
        )


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


def test_tiptap_exact_commit_replay_returns_existing_revision(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from uuid import UUID

    from application_state.content import repository as repo
    from application_state.unit_of_work import unit_of_work

    created = create_workspace_document(
        tmp_path, title="Tiptap replay", campaign_id="longmont-c2", kind="plan"
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


def test_runbook_fails_closed_when_app_state_is_down(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:1/dungeonbuddy_app_state_down",
    )
    with pytest.raises(WorkspaceDocumentRegistryError) as excinfo:
        create_workspace_document(
            tmp_path,
            title="Runbook",
            campaign_id="longmont-c2",
            kind="runbook",
            target_relpath="evals/c2_live_prep/mireward-prep/content/tiptap/as1-runbook.md",
        )
    assert excinfo.value.status_code == 503


def test_unfiltered_document_list_fails_closed_when_app_state_is_down(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = create_workspace_document(
        tmp_path,
        title="Visible lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:1/dungeonbuddy_app_state_down",
    )
    with pytest.raises(WorkspaceDocumentRegistryError) as excinfo:
        list_workspace_documents(tmp_path)
    assert excinfo.value.status_code == 503
    unfiltered = client.get("/api/live/workspace-documents")
    assert unfiltered.status_code == 503, unfiltered.text
    filtered = client.get("/api/live/workspace-documents", params={"kind": "runbook"})
    assert filtered.status_code == 503, filtered.text
    worldbuilding = client.get(
        "/api/live/workspace-documents", params={"kind": "worldbuilding_source"}
    )
    assert worldbuilding.status_code == 200, worldbuilding.text
    assert [row["document_id"] for row in worldbuilding.json()["records"]] == [
        world.document_id
    ]


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


def test_plan_load_and_commit_latency(
    tmp_path: Path, application_state_dsn: str
) -> None:
    markdown = "# latency witness\n"
    baseline = create_workspace_document(
        tmp_path,
        title="latency baseline",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    head = create_workspace_document(
        tmp_path, title="latency head", campaign_id="longmont-c2", kind="plan"
    )
    baseline_autosave_ms, baseline_commit_ms, baseline_load_ms, baseline_markdown = (
        _measure_prepare_commit_load(
            root=tmp_path,
            document_id=baseline.document_id,
            expected_revision=baseline.revision,
            markdown=markdown,
        )
    )
    head_autosave_ms, head_commit_ms, head_load_ms, head_markdown = (
        _measure_prepare_commit_load(
            root=tmp_path,
            document_id=head.document_id,
            expected_revision=head.revision,
            markdown=markdown,
        )
    )
    print(
        "AS1 latency hypothesis capture "
        "baseline_file_worldbuilding "
        f"autosave_ms={baseline_autosave_ms:.1f} "
        f"commit_ms={baseline_commit_ms:.1f} "
        f"load_ms={baseline_load_ms:.1f} "
        "head_postgres_plan "
        f"autosave_ms={head_autosave_ms:.1f} "
        f"commit_ms={head_commit_ms:.1f} "
        f"load_ms={head_load_ms:.1f}"
    )
    assert baseline_markdown == markdown
    assert head_markdown == markdown
    assert (
        baseline_autosave_ms >= 0
        and baseline_commit_ms >= 0
        and baseline_load_ms >= 0
        and head_autosave_ms >= 0
        and head_commit_ms >= 0
        and head_load_ms >= 0
    )


def test_world_plan_revisions_keep_the_world_owner_after_later_commits(
    application_state_dsn: str,
) -> None:
    from application_state.content.service import (
        commit_plan,
        create_world_plan,
        exact_committed_revision,
    )
    from application_state.content.types import sha256_utf8
    from application_state.errors import ApplicationStateConflictError

    created = create_world_plan(title="World plan", world_id="demo-world-a")
    first, first_revision = commit_plan(
        str(created.work_object_id),
        "# first plan revision\n",
        expected_revision=created.object_revision,
        expected_world_id="demo-world-a",
    )
    assert first.world_id == "demo-world-a"
    assert first_revision.world_id == "demo-world-a"

    second, second_revision = commit_plan(
        str(first.work_object_id),
        "# second plan revision\n",
        expected_revision=first.object_revision,
        expected_world_id="demo-world-a",
    )
    assert second_revision.world_id == "demo-world-a"
    historical = exact_committed_revision(
        str(created.work_object_id),
        1,
        kind="plan",
        expected_sha256=sha256_utf8("# first plan revision\n"),
        expected_world_id="demo-world-a",
    )
    assert historical.work_revision.work_revision_id == first_revision.work_revision_id
    assert historical.work_revision.world_id == "demo-world-a"
    assert historical.work_revision.markdown == "# first plan revision\n"

    with pytest.raises(ApplicationStateConflictError, match="selected World"):
        exact_committed_revision(
            str(created.work_object_id),
            1,
            kind="plan",
            expected_sha256=sha256_utf8("# first plan revision\n"),
            expected_world_id="demo-world-b",
        )


def test_world_owner_migration_backfills_only_explicit_world_scope(
    application_state_dsn: str,
) -> None:
    import psycopg
    from alembic import command

    from application_state.cli import alembic_config, upgrade_to_head
    from application_state.content.types import sha256_utf8

    command.downgrade(alembic_config(), "20260928_0007")
    now = datetime.now(UTC)
    world_id = "migration-backfill-world"
    plan_id = uuid4()
    plan_revision_id = uuid4()
    runbook_id = uuid4()
    runbook_revision_id = uuid4()
    plan_markdown = "# pre-migration World Plan\n"
    runbook_markdown = "# pre-migration campaign Runbook\n"

    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            """
            INSERT INTO content.work_object (
                work_object_id, kind, campaign_id, world_id, title, target_session,
                target_relpath, status, current_revision_id, object_revision,
                created_at, updated_at
            ) VALUES (%s, 'plan', NULL, %s, 'World Plan', NULL, NULL,
                      'active', NULL, 1, %s, %s)
            """,
            (plan_id, world_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO content.work_object (
                work_object_id, kind, campaign_id, world_id, title, target_session,
                target_relpath, status, current_revision_id, object_revision,
                created_at, updated_at
            ) VALUES (%s, 'runbook', %s, NULL, 'Campaign Runbook', 4, NULL,
                      'active', NULL, 1, %s, %s)
            """,
            (runbook_id, world_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO content.work_revision (
                work_revision_id, work_object_id, revision_n, markdown,
                content_sha256, created_at
            ) VALUES (%s, %s, 1, %s, %s, %s)
            """,
            (
                plan_revision_id,
                plan_id,
                plan_markdown,
                sha256_utf8(plan_markdown),
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO content.work_revision (
                work_revision_id, work_object_id, revision_n, markdown,
                content_sha256, created_at
            ) VALUES (%s, %s, 1, %s, %s, %s)
            """,
            (
                runbook_revision_id,
                runbook_id,
                runbook_markdown,
                sha256_utf8(runbook_markdown),
                now,
            ),
        )
        conn.execute(
            """
            UPDATE content.work_object
            SET current_revision_id = %s, object_revision = 2
            WHERE work_object_id = %s
            """,
            (plan_revision_id, plan_id),
        )
        conn.execute(
            """
            UPDATE content.work_object
            SET current_revision_id = %s, object_revision = 2
            WHERE work_object_id = %s
            """,
            (runbook_revision_id, runbook_id),
        )

    upgrade_to_head(dsn=application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        plan_owner = conn.execute(
            "SELECT world_id FROM content.work_revision WHERE work_revision_id = %s",
            (plan_revision_id,),
        ).fetchone()
        runbook_owner = conn.execute(
            "SELECT world_id FROM content.work_revision WHERE work_revision_id = %s",
            (runbook_revision_id,),
        ).fetchone()
    assert plan_owner == (world_id,)
    assert runbook_owner == (None,)
