from pathlib import Path

import pytest

from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteConflictError,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    normalize_tiptap_target_relpath,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    create_workspace_document,
    discard_workspace_document,
    get_workspace_document,
    get_workspace_document_snapshot,
    update_workspace_document_metadata,
)

TARGET = "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md"
PLAN_TARGET = (
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md"
)


def create_doc(
    root: Path,
    *,
    target: str = TARGET,
    title: str = "North-gate callout spike",
    kind: str | None = None,
):
    resolved_kind = kind or (
        "plan" if target.startswith("corpus/eldyrwild-markdown/") else "runbook"
    )
    return create_workspace_document(
        root,
        title=title,
        campaign_id="longmont-c2",
        kind=resolved_kind,  # type: ignore[arg-type]
        target_relpath=target,
    )


def prepare(
    root: Path,
    document_id: str,
    markdown: str = "# North gate\n",
    *,
    expected_revision: int | None = None,
):
    return prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=expected_revision,
        ),
    )


def commit(
    root: Path,
    document_id: str,
    token: str,
    markdown: str = "# North gate\n",
    *,
    expected_revision: int | None = None,
):
    return commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=token,
            expected_revision=expected_revision,
        ),
    )


def test_prepare_create_returns_diff_and_token_without_writing(tmp_path: Path):
    doc = create_doc(tmp_path)
    response = prepare(tmp_path, doc.document_id)
    assert response.writer_ok and response.writer_confirm_token
    assert response.title == doc.title
    assert response.target_relpath == TARGET
    after_prepare = get_workspace_document(tmp_path, doc.document_id)
    assert response.registry_revision == after_prepare.revision
    assert not response.file_exists
    assert any("Markdown file is not authority" in item for item in response.diagnostics)
    assert not (tmp_path / TARGET).exists()


def test_commit_writes_after_prepare(tmp_path: Path):
    doc = create_doc(tmp_path)
    preview = prepare(tmp_path, doc.document_id)
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "")
    assert response.writer_ok and response.bytes_written
    assert response.file_fingerprint == "postgres"
    assert response.title == doc.title
    assert response.target_relpath == TARGET
    assert not (tmp_path / TARGET).exists()
    assert "WorkRevision committed in PostgreSQL" in response.diagnostics

    committed = get_workspace_document(tmp_path, doc.document_id)
    assert committed.content_status == "committed"
    assert response.registry_revision == committed.revision
    assert response.committed_revision == committed.revision
    assert response.normalized_content_sha256
    assert response.committed_record.revision == committed.revision
    snapshot = get_workspace_document_snapshot(tmp_path, doc.document_id)
    assert snapshot.markdown == "# North gate\n"
    assert snapshot.file_exists is False


def test_stale_token_is_rejected_without_overwrite(tmp_path: Path):
    doc = create_doc(tmp_path)
    preview = prepare(tmp_path, doc.document_id, "# North gate\n")
    prepare(tmp_path, doc.document_id, "# later draft\n")
    leftover = tmp_path / TARGET
    leftover.parent.mkdir(parents=True)
    leftover.write_text("changed\n")
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        commit(tmp_path, doc.document_id, preview.writer_confirm_token or "", "# North gate\n")
    assert exc.value.status_code == 409
    assert leftover.read_text() == "changed\n"
    snapshot = get_workspace_document_snapshot(tmp_path, doc.document_id)
    assert snapshot.markdown == "# later draft\n"


def test_discarded_document_blocks_prepare_and_commit(tmp_path: Path):
    doc = create_doc(tmp_path)
    discard_workspace_document(tmp_path, doc.document_id)
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        prepare(tmp_path, doc.document_id)
    assert exc.value.status_code == 409


def test_plan_create_without_target_assigns_workspace_path(tmp_path: Path):
    """Plan create no longer leaves target_relpath unset; prepare must succeed."""
    doc = create_workspace_document(
        tmp_path,
        title="No path",
        campaign_id="longmont-c2",
        kind="plan",
    )
    assert doc.target_relpath == f"out/workspace/plan/{doc.document_id}.md"
    response = prepare(tmp_path, doc.document_id)
    assert response.writer_ok is True
    assert response.target_relpath == doc.target_relpath


def test_stale_expected_revision_blocks_prepare(tmp_path: Path):
    doc = create_doc(tmp_path)
    update_workspace_document_metadata(
        tmp_path,
        doc.document_id,
        title="Renamed",
        expected_revision=1,
    )
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        prepare(tmp_path, doc.document_id, expected_revision=1)
    assert exc.value.status_code == 409


def test_stale_expected_revision_blocks_commit(tmp_path: Path):
    doc = create_doc(tmp_path)
    preview = prepare(tmp_path, doc.document_id)
    after_prepare = get_workspace_document(tmp_path, doc.document_id)
    update_workspace_document_metadata(
        tmp_path,
        doc.document_id,
        title="Renamed",
        expected_revision=after_prepare.revision,
    )
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        commit(
            tmp_path,
            doc.document_id,
            preview.writer_confirm_token or "",
            expected_revision=doc.revision,
        )
    assert exc.value.status_code == 409
    assert not (tmp_path / TARGET).exists()


@pytest.mark.parametrize(
    "relpath",
    ["../bad.md", "evals/c2_live_prep/mireward-prep/content/tiptap/../bad.md"],
)
def test_rejects_path_traversal(tmp_path: Path, relpath: str):
    doc = create_doc(tmp_path, target=relpath)
    with pytest.raises(TiptapMarkdownWriteError):
        prepare(tmp_path, doc.document_id)


@pytest.mark.parametrize(
    "relpath",
    [
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/foo.md",
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.json",
        "evals/c2_live_prep/mireward-prep/content/foo.md",
        "evals/c2_live_prep/mireward-prep/content/tiptap/foo.json",
    ],
)
def test_rejects_targets_outside_allowlist(tmp_path: Path, relpath: str):
    # Illegal Plan Session Prep paths are rejected at create (registry + writer policy).
    # Illegal runbook/eval paths still create, then fail at prepare/authorize.
    if relpath.startswith("corpus/eldyrwild-markdown/"):
        with pytest.raises(WorkspaceDocumentRegistryError) as exc:
            create_doc(tmp_path, target=relpath)
        assert "plan target_relpath" in str(exc.value)
        return

    doc = create_doc(tmp_path, target=relpath)
    with pytest.raises(TiptapMarkdownWriteError):
        prepare(tmp_path, doc.document_id)


def test_normalize_rejects_disallowed_paths():
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath(
            "evals/c2_live_prep/mireward-prep/content/tiptap/foo.json"
        )


def test_overwrite_does_not_mutate_leftover_file(tmp_path: Path):
    doc = create_doc(tmp_path)
    leftover = tmp_path / TARGET
    leftover.parent.mkdir(parents=True)
    leftover.write_text("old\n")
    preview = prepare(tmp_path, doc.document_id, "new")
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "", "new")
    assert response.backup_relpath is None
    assert leftover.read_text() == "old\n"
    assert "WorkRevision committed in PostgreSQL" in response.diagnostics
    snapshot = get_workspace_document_snapshot(tmp_path, doc.document_id)
    assert snapshot.markdown == "new\n"


def test_prepare_accepts_plan_session_prep_target(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    markdown = "# C2 Session 23 Prep\n"
    response = prepare(tmp_path, doc.document_id, markdown)
    assert response.writer_ok and response.writer_confirm_token
    assert response.target_relpath == PLAN_TARGET
    assert response.title == "Session 23 Prep"
    assert not (tmp_path / PLAN_TARGET).exists()


def test_commit_persists_plan_session_prep_in_postgres(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    markdown = "# C2 Session 23 Prep\n"
    preview = prepare(tmp_path, doc.document_id, markdown)
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "", markdown)
    assert response.writer_ok
    assert "WorkRevision committed in PostgreSQL" in response.diagnostics
    assert not (tmp_path / PLAN_TARGET).exists()
    snapshot = get_workspace_document_snapshot(tmp_path, doc.document_id)
    assert snapshot.markdown == markdown
    assert snapshot.file_exists is False


def test_plan_session_prep_prepare_diagnostics_do_not_claim_corpus_untouched(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    response = prepare(tmp_path, doc.document_id, "# Prep\n")
    assert "corpus was not mutated" not in response.diagnostics


def test_plan_session_prep_commit_diagnostics_do_not_claim_corpus_untouched(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    preview = prepare(tmp_path, doc.document_id, "# Prep\n")
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "", "# Prep\n")
    assert "corpus was not mutated" not in response.diagnostics


def test_eval_prepare_diagnostics_do_not_treat_file_as_authority(tmp_path: Path):
    doc = create_doc(tmp_path)
    response = prepare(tmp_path, doc.document_id)
    assert "corpus was not mutated" not in response.diagnostics
    assert any("Markdown file is not authority" in item for item in response.diagnostics)


def test_omitted_write_mode_remains_authoring_for_worldbuilding(tmp_path: Path):
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
    )

    record = create_workspace_document(
        tmp_path,
        title="Legacy",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Title\n\n| a | b |\n"
    response = prepare(
        tmp_path,
        record.document_id,
        markdown,
        expected_revision=1,
    )
    assert response.writer_ok is False


def test_source_import_write_mode_threads_through_prepare_commit(tmp_path: Path):
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
    )

    (tmp_path / "corpus" / "eldyrwild-markdown").mkdir(parents=True)
    record = create_workspace_document(
        tmp_path,
        title="Imported",
        campaign_id="longmont-c2",
        kind="worldbuilding_source",
        world_id="eldyrwild",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Imported\n\n| a | b |\n"
    preview = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
            write_mode="source_import",
        ),
    )
    assert preview.writer_ok is True
    response = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=preview.writer_confirm_token or "",
            expected_revision=1,
            write_mode="source_import",
        ),
    )
    assert response.writer_ok is True
    assert (tmp_path / (record.target_relpath or "")).read_text(encoding="utf-8") == markdown
