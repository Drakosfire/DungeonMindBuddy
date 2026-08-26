from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.play_run_rebase import (
    PlayRunRebaseError,
    play_run_rebase_intent_path,
    rebase_or_replay_play_run,
)
from apps.live_control_server.services.play_run_registry import get_play_run
from apps.live_control_server.services.play_run_reference_manifest import (
    get_play_run_reference_manifest,
)
from apps.live_control_server.services.workspace_document_registry import (
    get_workspace_document_snapshot,
)
from tests.application_state.play_runtime_helpers import (
    RUN_ID_A,
    SOURCE_MARKDOWN,
    SURVIVING_TARGET_MARKDOWN,
    V2_SOURCE_MARKDOWN,
    V2_SURVIVING_TARGET_MARKDOWN,
    commit_runbook_markdown,
    create_committed_runbook,
    create_run,
    playable_of,
)


def _advance_to_surviving_target(root: Path, snapshot):
    commit_runbook_markdown(
        root,
        snapshot.record.document_id,
        SURVIVING_TARGET_MARKDOWN,
        snapshot.loaded_revision,
    )
    advanced = get_workspace_document_snapshot(root, snapshot.record.document_id)
    return playable_of(advanced)


def test_successful_rebase_moves_binding_and_manifest_once(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, markdown=SOURCE_MARKDOWN)
    created = create_run(tmp_path, snapshot)
    target_revision, target_sha = _advance_to_surviving_target(tmp_path, snapshot)
    rebased = rebase_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        target_playable_revision=target_revision,
        target_playable_content_sha256=target_sha,
    )
    assert rebased.run_revision == created.run_revision + 1
    assert rebased.playable_revision == target_revision
    assert rebased.playable_content_sha256 == target_sha
    assert rebased.rebased_from_run_revision == created.run_revision
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert manifest.playable_revision == target_revision
    assert manifest.playable_content_sha256 == target_sha
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_rebase_exact_replay_does_not_mutate_again(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, markdown=SOURCE_MARKDOWN)
    created = create_run(tmp_path, snapshot)
    target_revision, target_sha = _advance_to_surviving_target(tmp_path, snapshot)
    first = rebase_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        target_playable_revision=target_revision,
        target_playable_content_sha256=target_sha,
    )
    replayed = rebase_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        target_playable_revision=target_revision,
        target_playable_content_sha256=target_sha,
    )
    assert replayed == first
    same_head = rebase_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=first.run_revision,
        target_playable_revision=target_revision,
        target_playable_content_sha256=target_sha,
    )
    assert same_head == first


def test_rebase_failure_before_commit_leaves_source_and_writes_no_intent(
    tmp_path: Path,
    application_state_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = create_committed_runbook(tmp_path, markdown=SOURCE_MARKDOWN)
    created = create_run(tmp_path, snapshot)
    source_manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    target_revision, target_sha = _advance_to_surviving_target(tmp_path, snapshot)

    def explode(*_args, **_kwargs):
        raise RuntimeError("forced rebase manifest replace failure")

    monkeypatch.setattr("application_state.play.repository.replace_manifest", explode)
    with pytest.raises(RuntimeError, match="forced rebase manifest replace failure"):
        rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=created.run_revision,
            target_playable_revision=target_revision,
            target_playable_content_sha256=target_sha,
        )
    leftover = get_play_run(tmp_path, RUN_ID_A)
    assert leftover.playable_revision == created.playable_revision
    assert leftover.run_revision == created.run_revision
    assert leftover.rebased_from_run_revision is None
    assert get_play_run_reference_manifest(tmp_path, RUN_ID_A) == source_manifest
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_stale_rebase_expected_revision_is_409(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, markdown=SOURCE_MARKDOWN)
    created = create_run(tmp_path, snapshot)
    target_revision, target_sha = _advance_to_surviving_target(tmp_path, snapshot)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=created.run_revision + 3,
            target_playable_revision=target_revision,
            target_playable_content_sha256=target_sha,
        )
    assert exc_info.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A).run_revision == created.run_revision
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def _assert_cross_grammar_rebase_is_terminal(
    tmp_path: Path,
    *,
    source_markdown: str,
    target_markdown: str,
) -> None:
    snapshot = create_committed_runbook(tmp_path, markdown=source_markdown)
    created = create_run(tmp_path, snapshot)
    source_manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    commit_runbook_markdown(
        tmp_path,
        snapshot.record.document_id,
        target_markdown,
        snapshot.loaded_revision,
    )
    advanced = get_workspace_document_snapshot(tmp_path, snapshot.record.document_id)
    target_revision, target_sha = playable_of(advanced)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=created.run_revision,
            target_playable_revision=target_revision,
            target_playable_content_sha256=target_sha,
        )
    assert exc_info.value.status_code == 409
    leftover = get_play_run(tmp_path, RUN_ID_A)
    assert leftover.playable_revision == created.playable_revision
    assert leftover.playable_content_sha256 == created.playable_content_sha256
    assert leftover.run_revision == created.run_revision
    assert leftover.rebased_from_run_revision is None
    assert get_play_run_reference_manifest(tmp_path, RUN_ID_A) == source_manifest
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_v1_to_v2_rebase_is_fail_closed(tmp_path: Path, application_state_dsn: str) -> None:
    _assert_cross_grammar_rebase_is_terminal(
        tmp_path, source_markdown=SOURCE_MARKDOWN, target_markdown=V2_SOURCE_MARKDOWN
    )


def test_v2_to_v1_rebase_is_fail_closed(tmp_path: Path, application_state_dsn: str) -> None:
    _assert_cross_grammar_rebase_is_terminal(
        tmp_path, source_markdown=V2_SOURCE_MARKDOWN, target_markdown=SOURCE_MARKDOWN
    )


def test_same_grammar_v2_rebase_is_preserve_only(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, markdown=V2_SOURCE_MARKDOWN)
    created = create_run(tmp_path, snapshot)
    commit_runbook_markdown(
        tmp_path,
        snapshot.record.document_id,
        V2_SURVIVING_TARGET_MARKDOWN,
        snapshot.loaded_revision,
    )
    advanced = get_workspace_document_snapshot(tmp_path, snapshot.record.document_id)
    target_revision, target_sha = playable_of(advanced)
    rebased = rebase_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        target_playable_revision=target_revision,
        target_playable_content_sha256=target_sha,
    )
    assert rebased.run_revision == created.run_revision + 1
    assert rebased.playable_revision == target_revision
    assert get_play_run_reference_manifest(tmp_path, RUN_ID_A).schema_version == (
        "dmb_play_run_reference_manifest_v2"
    )
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()
