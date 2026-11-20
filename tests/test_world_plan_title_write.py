from pathlib import Path

import pytest
from pydantic import ValidationError

from application_state.content.service import (
    create_world_plan,
    commit_plan,
    get_content_optional,
    current_committed_revision,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWritePrepareRequest as Prepare,
    TiptapMarkdownWriteCommitRequest as Commit,
    TiptapMarkdownWriteConflictError,
    TiptapMarkdownWriteError,
    prepare_tiptap_markdown_write,
    commit_tiptap_markdown_write,
)

WORLD = "title-save-world"
BODY = "# Original\n\nA source quotation.\n"


def seed():
    obj = create_world_plan(title="Original title", world_id=WORLD)
    return commit_plan(
        str(obj.work_object_id),
        BODY,
        expected_revision=obj.object_revision,
        expected_world_id=WORLD,
    )


def prepare(root, obj, body=BODY, **kwargs):
    return prepare_tiptap_markdown_write(
        root=root,
        request=Prepare(
            document_id=str(obj.work_object_id),
            markdown=body,
            expected_revision=obj.object_revision,
            schema_version="dmb_tiptap_markdown_write_prepare_v2",
            scope_mode="world",
            world_id=WORLD,
            **kwargs,
        ),
    )


def commit(root, obj, prepared, body=BODY, **kwargs):
    return commit_tiptap_markdown_write(
        root=root,
        request=Commit(
            document_id=str(obj.work_object_id),
            markdown=body,
            expected_revision=prepared.registry_revision,
            writer_confirm_token=prepared.writer_confirm_token,
            schema_version="dmb_tiptap_markdown_write_commit_v2",
            scope_mode="world",
            world_id=WORLD,
            **kwargs,
        ),
    )


def test_title_only_commit_keeps_content_revision_and_replays(
    application_state_dsn, tmp_path: Path
):
    obj, original = seed()
    prepared = prepare(tmp_path, obj, title="  Renamed title  ")
    assert prepared.title == "Renamed title"
    assert get_content_optional(str(obj.work_object_id)).title == "Original title"
    saved = commit(tmp_path, obj, prepared, title="Renamed title")
    current = get_content_optional(str(obj.work_object_id))
    assert saved.title == current.title == "Renamed title"
    assert current.object_revision == prepared.registry_revision + 1
    revision = current_committed_revision(str(obj.work_object_id)).work_revision
    assert revision.work_revision_id == original.work_revision_id
    assert revision.content_sha256 == original.content_sha256
    assert revision.revision_n == original.revision_n
    replay = commit(tmp_path, obj, prepared, title="Renamed title")
    assert replay.registry_revision == saved.registry_revision


def test_title_and_body_commit_atomically_and_omission_retains_title(
    application_state_dsn, tmp_path: Path
):
    obj, original = seed()
    body = BODY + "\nNew content.\n"
    prepared = prepare(tmp_path, obj, body, title="New title")
    saved = commit(tmp_path, obj, prepared, body, title="New title")
    assert saved.title == "New title"
    revision = current_committed_revision(str(obj.work_object_id)).work_revision
    assert revision.revision_n == original.revision_n + 1
    assert revision.markdown == body
    obj = get_content_optional(str(obj.work_object_id))
    prepared = prepare(tmp_path, obj)
    saved = commit(tmp_path, obj, prepared)
    assert saved.title == "New title"


def test_title_token_cannot_be_retargeted_or_omitted(
    application_state_dsn, tmp_path: Path
):
    obj, _ = seed()
    prepared = prepare(tmp_path, obj, title="Reviewed title")
    for kwargs in [{"title": "Other title"}, {}]:
        with pytest.raises(TiptapMarkdownWriteConflictError):
            commit(tmp_path, obj, prepared, **kwargs)
    assert get_content_optional(str(obj.work_object_id)).title == "Original title"


def test_stale_same_body_does_not_prove_a_different_title_committed(
    application_state_dsn, tmp_path: Path
):
    obj, _ = seed()
    prepared = prepare(tmp_path, obj, title="My title")
    commit_plan(
        str(obj.work_object_id),
        BODY,
        title="Other writer title",
        expected_revision=prepared.registry_revision,
        expected_world_id=WORLD,
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit(tmp_path, obj, prepared, title="My title")
    assert get_content_optional(str(obj.work_object_id)).title == "Other writer title"


def test_commit_rollback_keeps_title_and_content(
    application_state_dsn, tmp_path: Path, monkeypatch
):
    from application_state.content import service

    obj, original = seed()
    body = BODY + "\nMust roll back.\n"
    prepared = prepare(tmp_path, obj, body, title="Must roll back")

    def fail(*args, **kwargs):
        raise RuntimeError("injected transactional failure")

    monkeypatch.setattr(service.repo, "update_work_object", fail)
    with pytest.raises(RuntimeError, match="injected"):
        commit(tmp_path, obj, prepared, body, title="Must roll back")
    assert get_content_optional(str(obj.work_object_id)).title == "Original title"
    assert (
        current_committed_revision(
            str(obj.work_object_id)
        ).work_revision.work_revision_id
        == original.work_revision_id
    )


@pytest.mark.parametrize("value", [None, "", "  "])
def test_explicit_invalid_title_is_rejected(value):
    for model, schema in [
        (Prepare, "dmb_tiptap_markdown_write_prepare_v2"),
        (Commit, "dmb_tiptap_markdown_write_commit_v2"),
    ]:
        with pytest.raises(ValidationError):
            model(
                document_id="id",
                markdown=BODY,
                title=value,
                schema_version=schema,
                scope_mode="world",
                world_id=WORLD,
                **({"writer_confirm_token": "token"} if model is Commit else {}),
            )


def test_legacy_scope_cannot_introduce_title():
    with pytest.raises(ValidationError):
        Prepare(document_id="id", markdown=BODY, title="New")


def test_wrong_world_and_runbook_title_rejected(application_state_dsn, tmp_path: Path):
    from application_state.content.service import create_world_runbook

    obj, _ = seed()
    with pytest.raises(TiptapMarkdownWriteConflictError):
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=Prepare(
                document_id=str(obj.work_object_id),
                markdown=BODY,
                expected_revision=obj.object_revision,
                title="New",
                schema_version="dmb_tiptap_markdown_write_prepare_v2",
                scope_mode="world",
                world_id="other",
            ),
        )
    runbook = create_world_runbook(title="Runbook", world_id=WORLD)
    with pytest.raises(TiptapMarkdownWriteError):
        prepare(tmp_path, runbook, title="Not a Plan")
