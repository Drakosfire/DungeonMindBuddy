from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.live_control_server.services.play_run_registry import (
    PlayRunRegistryError,
    create_or_replay_play_run,
    get_play_run,
    list_play_runs,
    play_run_path,
    play_runs_dir,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    WorkspaceDocumentSnapshot,
    create_workspace_document,
    discard_workspace_document,
    get_committed_playable_revision,
    get_workspace_document_snapshot,
)

pytest_plugins = ["tests.application_state.conftest"]

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
RUN_ID_C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
RUN_ID_D = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


_PLAYABLE_BY_SHA: dict[tuple[str, str], int] = {}


@pytest.fixture(autouse=True)
def _application_state(application_state_dsn: str) -> str:
    _PLAYABLE_BY_SHA.clear()
    return application_state_dsn


def _playable(snapshot: WorkspaceDocumentSnapshot) -> tuple[int, str]:
    key = (snapshot.record.document_id, snapshot.content_sha256)
    remembered = _PLAYABLE_BY_SHA.get(key)
    if remembered is not None:
        return remembered, snapshot.content_sha256
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    return committed.revision_n, committed.content_sha256


def _commit_record(
    root: Path,
    record: WorkspaceDocumentRecord,
    markdown: str,
) -> WorkspaceDocumentSnapshot:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=record.revision,
        ),
    )
    snapshot = get_workspace_document_snapshot(root, record.document_id)
    if snapshot.record.kind != "runbook":
        return snapshot
    committed = get_committed_playable_revision(record.document_id, kind=None)
    if committed.content_sha256 == snapshot.content_sha256:
        _PLAYABLE_BY_SHA[(snapshot.record.document_id, snapshot.content_sha256)] = (
            committed.revision_n
        )
    return snapshot


def _create_committed_runbook(
    root: Path,
    *,
    name: str = "play-run-test",
    markdown: str = "# Runbook\n\nA durable playable.\n",
) -> WorkspaceDocumentSnapshot:
    record = create_workspace_document(
        root,
        title=f"Runbook {name}",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            f"{name}.md"
        ),
    )
    return _commit_record(root, record, markdown)


def _advance_runbook(
    root: Path,
    snapshot: WorkspaceDocumentSnapshot,
    markdown: str,
) -> WorkspaceDocumentSnapshot:
    return _commit_record(root, snapshot.record, markdown)


def _create_run(
    root: Path,
    snapshot: WorkspaceDocumentSnapshot,
    *,
    run_id: str = RUN_ID_A,
):
    try:
        revision_n, sha = _playable(snapshot)
    except WorkspaceDocumentRegistryError:
        revision_n, sha = snapshot.loaded_revision, snapshot.content_sha256
    return create_or_replay_play_run(
        root,
        run_id=run_id,
        playable_artifact_id=snapshot.record.document_id,
        expected_playable_revision=revision_n,
        expected_playable_content_sha256=sha,
    )


def test_exact_create_persists_binding_without_mutating_runbook(tmp_path: Path) -> None:
    snapshot_before = _create_committed_runbook(tmp_path)

    record = _create_run(tmp_path, snapshot_before)

    assert record.run_id == RUN_ID_A
    assert record.campaign_id == "longmont-c2"
    assert record.playable_artifact_id == snapshot_before.record.document_id
    assert record.playable_revision == _playable(snapshot_before)[0]
    assert record.playable_content_sha256 == _playable(snapshot_before)[1]
    assert record.run_revision == 1
    assert record.created_at == record.updated_at

    assert not play_run_path(tmp_path, RUN_ID_A).exists()
    assert "markdown" not in record.model_dump_json()
    assert record.progress.current_scene_id is None
    assert record.progress.current_beat_id is None
    assert record.progress.resolved_beat_ids == []
    assert record.progress.selections == {}
    assert record.progress.notes_by_element_id == {}

    snapshot_after = get_workspace_document_snapshot(
        tmp_path,
        snapshot_before.record.document_id,
    )
    assert snapshot_after.loaded_revision == snapshot_before.loaded_revision
    assert snapshot_after.content_sha256 == snapshot_before.content_sha256
    assert snapshot_after.markdown == snapshot_before.markdown


def test_identical_replay_returns_existing_record_and_bytes_unchanged(
    tmp_path: Path,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    first = _create_run(tmp_path, snapshot)

    second = _create_run(tmp_path, snapshot)

    assert second == first
    assert second.run_revision == 1
    assert second.created_at == first.created_at
    assert second.updated_at == first.updated_at
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_replay_remains_idempotent_after_runbook_advances(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    first = _create_run(tmp_path, snapshot)

    advanced = _advance_runbook(
        tmp_path,
        snapshot,
        "# Runbook\n\nA newer playable revision.\n",
    )
    assert advanced.loaded_revision > snapshot.loaded_revision
    assert advanced.content_sha256 != snapshot.content_sha256

    replayed = _create_run(tmp_path, snapshot)

    assert replayed == first
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_same_run_id_different_binding_fails_without_overwrite(tmp_path: Path) -> None:
    snapshot_a = _create_committed_runbook(tmp_path, name="binding-a")
    snapshot_b = _create_committed_runbook(tmp_path, name="binding-b")
    first = _create_run(tmp_path, snapshot_a)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        _create_run(tmp_path, snapshot_b)

    assert exc_info.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A) == first
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_stale_revision_after_real_workspace_commit_fails_without_run(
    tmp_path: Path,
) -> None:
    old = _create_committed_runbook(tmp_path, name="stale-revision")
    old_revision, old_sha = _playable(old)
    current = _advance_runbook(
        tmp_path,
        old,
        "# Runbook\n\nRevision N plus one.\n",
    )
    current_revision, _ = _playable(current)
    assert current_revision == old_revision + 1

    with pytest.raises(PlayRunRegistryError) as exc_info:
        create_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            playable_artifact_id=old.record.document_id,
            expected_playable_revision=old_revision,
            expected_playable_content_sha256=old_sha,
        )

    assert exc_info.value.status_code == 409
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_stale_sha_with_current_revision_fails_without_run(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path, name="stale-sha")
    wrong_sha = hashlib.sha256(b"not the runbook").hexdigest()
    assert wrong_sha != snapshot.content_sha256

    with pytest.raises(PlayRunRegistryError) as exc_info:
        create_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            playable_artifact_id=snapshot.record.document_id,
            expected_playable_revision=_playable(snapshot)[0],
            expected_playable_content_sha256=wrong_sha,
        )

    assert exc_info.value.status_code == 409
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_committed_non_runbook_is_not_admitted(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="Plan is not a Runbook",
        campaign_id="longmont-c2",
        kind="plan",
    )
    snapshot = _commit_record(tmp_path, record, "# Plan\n\nNot runnable here.\n")

    with pytest.raises(PlayRunRegistryError) as exc_info:
        _create_run(tmp_path, snapshot)

    assert exc_info.value.status_code == 422
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_draft_runbook_is_not_admitted(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="Draft Runbook",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/draft-runbook.md"
        ),
    )
    snapshot = get_workspace_document_snapshot(tmp_path, record.document_id)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        _create_run(tmp_path, snapshot)

    assert exc_info.value.status_code == 409
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_discarded_runbook_is_not_admitted(tmp_path: Path) -> None:
    committed = _create_committed_runbook(tmp_path, name="discarded")
    discarded = discard_workspace_document(
        tmp_path,
        committed.record.document_id,
        expected_revision=committed.loaded_revision,
    )
    snapshot = get_workspace_document_snapshot(tmp_path, discarded.document_id)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        _create_run(tmp_path, snapshot)

    assert exc_info.value.status_code == 409
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_fresh_reads_recover_persisted_run_and_list(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path, name="restart")
    created = _create_run(tmp_path, snapshot)

    loaded = get_play_run(tmp_path, RUN_ID_A)
    listed = list_play_runs(tmp_path)

    assert loaded == created
    assert listed == [created]


def test_different_run_ids_may_bind_same_playable_revision(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path, name="multi-run")

    run_a = _create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    run_b = _create_run(tmp_path, snapshot, run_id=RUN_ID_B)

    assert run_a.playable_artifact_id == run_b.playable_artifact_id
    assert run_a.playable_revision == run_b.playable_revision
    assert run_a.playable_content_sha256 == run_b.playable_content_sha256
    assert run_a.run_id != run_b.run_id
    assert {record.run_id for record in list_play_runs(tmp_path)} == {
        RUN_ID_A,
        RUN_ID_B,
    }


def test_malformed_persisted_run_fails_get_and_whole_list(tmp_path: Path) -> None:
    path = play_runs_dir(tmp_path) / f"{RUN_ID_A}.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(PlayRunRegistryError) as get_exc:
        get_play_run(tmp_path, RUN_ID_A)
    assert get_exc.value.status_code == 404

    assert list_play_runs(tmp_path) == []
    assert path.read_text(encoding="utf-8") == "{not-json\n"


def test_list_is_created_descending_then_run_id_ascending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path, name="ordering")
    timestamps = iter(
        [
            "2026-08-15T12:00:00Z",
            "2026-08-15T12:00:00Z",
            "2026-08-15T13:00:00Z",
            "2026-08-15T11:00:00Z",
        ]
    )
    def fake_now_utc() -> datetime:
        return datetime.fromisoformat(next(timestamps).replace("Z", "+00:00"))

    monkeypatch.setattr(
        "application_state.play.repository.now_utc",
        fake_now_utc,
    )

    _create_run(tmp_path, snapshot, run_id=RUN_ID_B)
    _create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    _create_run(tmp_path, snapshot, run_id=RUN_ID_C)
    _create_run(tmp_path, snapshot, run_id=RUN_ID_D)

    assert [record.run_id for record in list_play_runs(tmp_path)] == [
        RUN_ID_C,
        RUN_ID_A,
        RUN_ID_B,
        RUN_ID_D,
    ]


def test_list_filters_by_campaign_and_playable_artifact(tmp_path: Path) -> None:
    snapshot_a = _create_committed_runbook(tmp_path, name="filter-a")
    snapshot_b = _create_committed_runbook(tmp_path, name="filter-b")
    _create_run(tmp_path, snapshot_a, run_id=RUN_ID_A)
    _create_run(tmp_path, snapshot_b, run_id=RUN_ID_B)

    by_campaign = list_play_runs(tmp_path, campaign_id="longmont-c2")
    by_artifact = list_play_runs(
        tmp_path,
        playable_artifact_id=snapshot_a.record.document_id,
    )

    assert {record.run_id for record in by_campaign} == {RUN_ID_A, RUN_ID_B}
    assert [record.run_id for record in by_artifact] == [RUN_ID_A]


def test_invalid_and_unknown_run_ids_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(PlayRunRegistryError) as invalid:
        get_play_run(tmp_path, "not-a-uuid")
    assert invalid.value.status_code == 422

    with pytest.raises(PlayRunRegistryError) as unknown:
        get_play_run(tmp_path, RUN_ID_A)
    assert unknown.value.status_code == 404


def test_noncanonical_uuid_and_sha_are_rejected_before_workspace_read(
    tmp_path: Path,
) -> None:
    snapshot = _create_committed_runbook(tmp_path, name="canonical-input")

    with pytest.raises(PlayRunRegistryError) as uuid_exc:
        create_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A.upper(),
            playable_artifact_id=snapshot.record.document_id,
            expected_playable_revision=_playable(snapshot)[0],
            expected_playable_content_sha256=snapshot.content_sha256,
        )
    assert uuid_exc.value.status_code == 422

    with pytest.raises(PlayRunRegistryError) as sha_exc:
        create_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            playable_artifact_id=snapshot.record.document_id,
            expected_playable_revision=_playable(snapshot)[0],
            expected_playable_content_sha256=snapshot.content_sha256.upper(),
        )
    assert sha_exc.value.status_code == 422
