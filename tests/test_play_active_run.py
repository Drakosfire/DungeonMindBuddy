from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.play_active_run import (
    PlayActiveRunError,
    get_play_active_run,
    play_active_run_path,
    set_play_active_run,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    seal_or_replay_play_run_reference_manifest,
)
from apps.live_control_server.services.play_run_registry import (
    create_or_replay_play_run,
    get_play_run,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document_snapshot,
)

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _create_committed_run(root: Path, *, run_id: str, name: str):
    document = create_workspace_document(
        root,
        title=f"Runbook {name}",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            f"{name}.md"
        ),
    )
    markdown = f"# {name}\n\nAt the table.\n"
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document.document_id,
            markdown=markdown,
            expected_revision=document.revision,
        ),
    )
    assert prepared.writer_ok is True
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=document.revision,
        ),
    )
    snapshot = get_workspace_document_snapshot(root, document.document_id)
    run = create_or_replay_play_run(
        root,
        run_id=run_id,
        playable_artifact_id=document.document_id,
        expected_playable_revision=snapshot.loaded_revision,
        expected_playable_content_sha256=snapshot.content_sha256,
    )
    return run


def test_missing_selection_is_a_normal_null_state(tmp_path: Path) -> None:
    state = get_play_active_run(tmp_path)

    assert state.run_id is None
    assert state.selected_at is None
    assert not play_active_run_path(tmp_path).exists()


def test_malformed_selection_fails_closed_without_resetting(tmp_path: Path) -> None:
    path = play_active_run_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"schema_version":"dmb_play_active_run_v1","run_id":"broken"}\n')

    with pytest.raises(PlayActiveRunError, match="malformed persisted"):
        get_play_active_run(tmp_path)

    assert path.read_text() == '{"schema_version":"dmb_play_active_run_v1","run_id":"broken"}\n'


def test_valid_selection_is_idempotent_and_survives_re_read(tmp_path: Path) -> None:
    run = _create_committed_run(tmp_path, run_id=RUN_ID_A, name="north-gate")
    seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)

    first = set_play_active_run(tmp_path, run_id=run.run_id)
    bytes_before = play_active_run_path(tmp_path).read_bytes()
    second = set_play_active_run(tmp_path, run_id=run.run_id)

    assert first.run_id == RUN_ID_A
    assert second == first
    assert play_active_run_path(tmp_path).read_bytes() == bytes_before
    assert get_play_active_run(tmp_path) == first
    assert get_play_run(tmp_path, RUN_ID_A) == run


def test_different_valid_run_replaces_pointer_without_mutating_runs(tmp_path: Path) -> None:
    run_a = _create_committed_run(tmp_path, run_id=RUN_ID_A, name="north-gate")
    run_b = _create_committed_run(tmp_path, run_id=RUN_ID_B, name="south-wall")
    seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_B)

    set_play_active_run(tmp_path, run_id=run_a.run_id)
    replaced = set_play_active_run(tmp_path, run_id=run_b.run_id)

    assert replaced.run_id == RUN_ID_B
    assert get_play_run(tmp_path, RUN_ID_A) == run_a
    assert get_play_run(tmp_path, RUN_ID_B) == run_b


def test_invalid_or_unsealed_run_never_writes_pointer(tmp_path: Path) -> None:
    with pytest.raises(PlayActiveRunError) as missing:
        set_play_active_run(tmp_path, run_id=RUN_ID_A)
    assert missing.value.status_code == 404
    assert not play_active_run_path(tmp_path).exists()

    run = _create_committed_run(tmp_path, run_id=RUN_ID_A, name="unsealed")
    with pytest.raises(PlayActiveRunError) as unsealed:
        set_play_active_run(tmp_path, run_id=run.run_id)
    assert unsealed.value.status_code == 409
    assert not play_active_run_path(tmp_path).exists()


def test_noncanonical_uuid_is_rejected_before_any_write(tmp_path: Path) -> None:
    with pytest.raises(PlayActiveRunError) as error:
        set_play_active_run(tmp_path, run_id=RUN_ID_A.upper())

    assert error.value.status_code == 422
    assert not play_active_run_path(tmp_path).exists()
