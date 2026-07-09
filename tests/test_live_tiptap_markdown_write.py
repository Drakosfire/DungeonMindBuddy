from pathlib import Path

import pytest

from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteConflictError,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)

TARGET = "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md"
PLAN_TARGET = (
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md"
)


def prepare(root: Path, markdown: str = "# North gate\n", *, target: str = TARGET):
    return prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id="north-gate-callout-spike",
            title="North-gate callout spike",
            target_relpath=target,
            markdown=markdown,
        ),
    )


def commit(root: Path, token: str, markdown: str = "# North gate\n", *, target: str = TARGET):
    return commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id="north-gate-callout-spike",
            title="North-gate callout spike",
            target_relpath=target,
            markdown=markdown,
            writer_confirm_token=token,
        ),
    )


def test_prepare_create_returns_diff_and_token_without_writing(tmp_path: Path):
    response = prepare(tmp_path)
    assert response.writer_ok and response.writer_confirm_token
    assert not response.file_exists
    assert "# North gate" in (response.writer_diff or "")
    assert not (tmp_path / TARGET).exists()


def test_commit_writes_after_prepare(tmp_path: Path):
    preview = prepare(tmp_path)
    response = commit(tmp_path, preview.writer_confirm_token or "")
    assert response.writer_ok and response.bytes_written
    assert response.file_fingerprint
    assert (tmp_path / TARGET).read_text() == "# North gate\n"


def test_stale_token_is_rejected_without_overwrite(tmp_path: Path):
    preview = prepare(tmp_path)
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_text("changed\n")
    with pytest.raises(TiptapMarkdownWriteConflictError) as exc:
        commit(tmp_path, preview.writer_confirm_token or "")
    assert exc.value.status_code == 409
    assert target.read_text() == "changed\n"


@pytest.mark.parametrize(
    "relpath",
    ["../bad.md", "evals/c2_live_prep/mireward-prep/content/tiptap/../bad.md"],
)
def test_rejects_path_traversal(tmp_path: Path, relpath: str):
    with pytest.raises(TiptapMarkdownWriteError):
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id="doc",
                title="Title",
                target_relpath=relpath,
                markdown="text",
            ),
        )


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
    with pytest.raises(TiptapMarkdownWriteError):
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id="doc",
                title="Title",
                target_relpath=relpath,
                markdown="text",
            ),
        )


def test_overwrite_creates_backup(tmp_path: Path):
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_text("old\n")
    preview = prepare(tmp_path, "new")
    response = commit(tmp_path, preview.writer_confirm_token or "", "new")
    assert response.backup_relpath
    assert (tmp_path / response.backup_relpath).read_text() == "old\n"
    assert target.read_text() == "new\n"


def test_prepare_accepts_plan_session_prep_target(tmp_path: Path):
    markdown = "# C2 Session 23 Prep\n"
    response = prepare(tmp_path, markdown, target=PLAN_TARGET)
    assert response.writer_ok and response.writer_confirm_token
    assert response.target_relpath == PLAN_TARGET
    assert not (tmp_path / PLAN_TARGET).exists()


def test_commit_creates_plan_session_prep_file(tmp_path: Path):
    markdown = "# C2 Session 23 Prep\n"
    preview = prepare(tmp_path, markdown, target=PLAN_TARGET)
    response = commit(tmp_path, preview.writer_confirm_token or "", markdown, target=PLAN_TARGET)
    assert response.writer_ok
    assert (tmp_path / PLAN_TARGET).read_text() == markdown


def test_plan_session_prep_prepare_diagnostics_do_not_claim_corpus_untouched(tmp_path: Path):
    response = prepare(tmp_path, "# Prep\n", target=PLAN_TARGET)
    assert "corpus was not mutated" not in response.diagnostics


def test_plan_session_prep_commit_diagnostics_do_not_claim_corpus_untouched(tmp_path: Path):
    preview = prepare(tmp_path, "# Prep\n", target=PLAN_TARGET)
    response = commit(tmp_path, preview.writer_confirm_token or "", "# Prep\n", target=PLAN_TARGET)
    assert "corpus was not mutated" not in response.diagnostics


def test_eval_prepare_diagnostics_still_claim_corpus_untouched(tmp_path: Path):
    response = prepare(tmp_path)
    assert "corpus was not mutated" in response.diagnostics
