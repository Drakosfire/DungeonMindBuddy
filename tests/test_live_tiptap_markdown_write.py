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
    create_workspace_document,
    discard_workspace_document,
    get_workspace_document,
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
):
    return create_workspace_document(
        root,
        title=title,
        campaign_id="longmont-c2",
        kind="plan",
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
    assert response.registry_revision == doc.revision
    assert not response.file_exists
    assert "# North gate" in (response.writer_diff or "")
    assert not (tmp_path / TARGET).exists()


def test_commit_writes_after_prepare(tmp_path: Path):
    doc = create_doc(tmp_path)
    preview = prepare(tmp_path, doc.document_id)
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "")
    assert response.writer_ok and response.bytes_written
    assert response.file_fingerprint
    assert response.title == doc.title
    assert response.target_relpath == TARGET
    assert (tmp_path / TARGET).read_text() == "# North gate\n"

    committed = get_workspace_document(tmp_path, doc.document_id)
    assert committed.content_status == "committed"
    assert committed.revision == doc.revision + 1
    assert response.registry_revision == committed.revision


def test_stale_token_is_rejected_without_overwrite(tmp_path: Path):
    doc = create_doc(tmp_path)
    preview = prepare(tmp_path, doc.document_id)
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_text("changed\n")
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        commit(tmp_path, doc.document_id, preview.writer_confirm_token or "")
    assert exc.value.status_code == 409
    assert target.read_text() == "changed\n"


def test_discarded_document_blocks_prepare_and_commit(tmp_path: Path):
    doc = create_doc(tmp_path)
    discard_workspace_document(tmp_path, doc.document_id)
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        prepare(tmp_path, doc.document_id)
    assert exc.value.status_code == 409


def test_missing_target_relpath_blocks_prepare(tmp_path: Path):
    doc = create_workspace_document(
        tmp_path,
        title="No path",
        campaign_id="longmont-c2",
        kind="plan",
    )
    with pytest.raises(TiptapMarkdownWriteError) as exc:
        prepare(tmp_path, doc.document_id)
    assert exc.value.status_code == 422
    assert "no target_relpath" in str(exc.value)


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
    update_workspace_document_metadata(
        tmp_path,
        doc.document_id,
        title="Renamed",
        expected_revision=1,
    )
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        commit(
            tmp_path,
            doc.document_id,
            preview.writer_confirm_token or "",
            expected_revision=1,
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
    doc = create_doc(tmp_path, target=relpath)
    with pytest.raises(TiptapMarkdownWriteError):
        prepare(tmp_path, doc.document_id)


def test_normalize_rejects_disallowed_paths():
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath(
            "evals/c2_live_prep/mireward-prep/content/tiptap/foo.json"
        )


def test_overwrite_creates_backup(tmp_path: Path):
    doc = create_doc(tmp_path)
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_text("old\n")
    preview = prepare(tmp_path, doc.document_id, "new")
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "", "new")
    assert response.backup_relpath
    assert (tmp_path / response.backup_relpath).read_text() == "old\n"
    assert target.read_text() == "new\n"


def test_prepare_accepts_plan_session_prep_target(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    markdown = "# C2 Session 23 Prep\n"
    response = prepare(tmp_path, doc.document_id, markdown)
    assert response.writer_ok and response.writer_confirm_token
    assert response.target_relpath == PLAN_TARGET
    assert response.title == "Session 23 Prep"
    assert not (tmp_path / PLAN_TARGET).exists()


def test_commit_creates_plan_session_prep_file(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    markdown = "# C2 Session 23 Prep\n"
    preview = prepare(tmp_path, doc.document_id, markdown)
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "", markdown)
    assert response.writer_ok
    assert (tmp_path / PLAN_TARGET).read_text() == markdown


def test_plan_session_prep_prepare_diagnostics_do_not_claim_corpus_untouched(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    response = prepare(tmp_path, doc.document_id, "# Prep\n")
    assert "corpus was not mutated" not in response.diagnostics


def test_plan_session_prep_commit_diagnostics_do_not_claim_corpus_untouched(tmp_path: Path):
    doc = create_doc(tmp_path, target=PLAN_TARGET, title="Session 23 Prep")
    preview = prepare(tmp_path, doc.document_id, "# Prep\n")
    response = commit(tmp_path, doc.document_id, preview.writer_confirm_token or "", "# Prep\n")
    assert "corpus was not mutated" not in response.diagnostics


def test_eval_prepare_diagnostics_still_claim_corpus_untouched(tmp_path: Path):
    doc = create_doc(tmp_path)
    response = prepare(tmp_path, doc.document_id)
    assert "corpus was not mutated" in response.diagnostics
