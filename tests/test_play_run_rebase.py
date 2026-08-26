from __future__ import annotations

from pathlib import Path
from threading import Thread

import psycopg
import pytest

from apps.live_control_server.services.play_run_rebase import (
    PlayRunRebaseError,
    rebase_or_replay_play_run,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    PlayRunRegistryError,
    create_or_replay_play_run,
    get_play_run,
    replace_play_run_progress,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    get_play_run_reference_manifest,
    seal_or_replay_play_run_reference_manifest,
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
    get_committed_playable_revision,
    get_workspace_document_snapshot,
)
from tests.application_state.play_runtime_helpers import (
    leftover_manifest_path,
    leftover_rebase_intent_path,
    leftover_run_path,
)

pytest_plugins = ["tests.application_state.conftest"]

_PLAYABLE_BY_SHA: dict[tuple[str, str], int] = {}


@pytest.fixture(autouse=True)
def _application_state(application_state_dsn: str) -> str:
    _PLAYABLE_BY_SHA.clear()
    return application_state_dsn


def _remember_playable(snapshot: WorkspaceDocumentSnapshot) -> WorkspaceDocumentSnapshot:
    if snapshot.record.kind != "runbook":
        return snapshot
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    if committed.content_sha256 == snapshot.content_sha256:
        _PLAYABLE_BY_SHA[(snapshot.record.document_id, snapshot.content_sha256)] = (
            committed.revision_n
        )
    return snapshot


def _playable(snapshot: WorkspaceDocumentSnapshot) -> tuple[int, str]:
    key = (snapshot.record.document_id, snapshot.content_sha256)
    remembered = _PLAYABLE_BY_SHA.get(key)
    if remembered is not None:
        return remembered, snapshot.content_sha256
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    return committed.revision_n, committed.content_sha256


RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

SOURCE_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
        "## The Gate",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->",
        "### Arrival",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:briefing -->",
        "### Briefing",
        "",
        "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
        "### Which route do they take?",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
        "#### Burn through the growth",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
        "#### Wait and watch",
        "",
    ]
)

SURVIVING_TARGET_MARKDOWN = SOURCE_MARKDOWN + "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:keep -->",
        "## The Keep",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:inside -->",
        "### Inside",
        "",
    ]
)

REPLACED_TARGET_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:harbor -->",
        "## Harbor",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:dock -->",
        "### Dock",
        "",
    ]
)

SCENE_RENAMED_MARKDOWN = SOURCE_MARKDOWN.replace("id=scene:gate", "id=scene:keep")
ARRIVAL_REMOVED_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
        "## The Gate",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:briefing -->",
        "### Briefing",
        "",
        "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
        "### Which route do they take?",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
        "#### Burn through the growth",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
        "#### Wait and watch",
        "",
    ]
)
BRIEFING_REMOVED_MARKDOWN = "\n".join(
    [
        line
        for line in SOURCE_MARKDOWN.splitlines()
        if "beat:briefing" not in line and line != "### Briefing"
    ]
) + "\n"
FIRE_REMOVED_MARKDOWN = "\n".join(
    [
        line
        for line in SOURCE_MARKDOWN.splitlines()
        if "option:fire" not in line and line != "#### Burn through the growth"
    ]
) + "\n"
WAIT_REMOVED_MARKDOWN = "\n".join(
    [
        line
        for line in SOURCE_MARKDOWN.splitlines()
        if "option:wait" not in line and line != "#### Wait and watch"
    ]
) + "\n"
MALFORMED_TARGET_MARKDOWN = "<!-- dmb-playable-element:v1 kind=scene -->\n## Arrival\n"
THIRD_ADVANCE_MARKDOWN = SURVIVING_TARGET_MARKDOWN + "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:tower -->",
        "## The Tower",
        "",
    ]
)


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
    return _remember_playable(get_workspace_document_snapshot(root, record.document_id))


def _create_committed_runbook(
    root: Path,
    *,
    name: str = "rebase-run",
    markdown: str = SOURCE_MARKDOWN,
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


def _create_run(root: Path, snapshot: WorkspaceDocumentSnapshot):
    return create_or_replay_play_run(
        root,
        run_id=RUN_ID_A,
        playable_artifact_id=snapshot.record.document_id,
        expected_playable_revision=_playable(snapshot)[0],
        expected_playable_content_sha256=_playable(snapshot)[1],
    )


def _seal(root: Path, snapshot: WorkspaceDocumentSnapshot):
    record = _create_run(root, snapshot)
    manifest = seal_or_replay_play_run_reference_manifest(root, RUN_ID_A)
    return record, manifest


def _progress(**overrides: object) -> PlayRunProgress:
    payload = {
        "current_scene_id": "scene:gate",
        "current_beat_id": "beat:arrival",
        "resolved_beat_ids": ["beat:briefing"],
        "selections": {"choice:route": "option:fire"},
        "notes_by_element_id": {"beat:arrival": "Door barred from the inside."},
    }
    payload.update(overrides)
    return PlayRunProgress.model_validate(payload)


def _advance(root: Path, snapshot: WorkspaceDocumentSnapshot, markdown: str):
    record = snapshot.record
    return _commit_record(root, record, markdown)


def _rebase(root: Path, snapshot: WorkspaceDocumentSnapshot, *, expected_run_revision: int):
    return rebase_or_replay_play_run(
        root,
        run_id=RUN_ID_A,
        expected_run_revision=expected_run_revision,
        target_playable_revision=_playable(snapshot)[0],
        target_playable_content_sha256=_playable(snapshot)[1],
    )


def _update_run_progress(dsn: str, run_id: str, progress: dict) -> None:
    from psycopg.types.json import Jsonb

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            "UPDATE play.run SET progress = %(progress)s WHERE run_id = %(run_id)s",
            {"progress": Jsonb(progress), "run_id": run_id},
        )


def _record_snapshot(record) -> object:
    return (
        record.run_revision,
        record.playable_revision,
        record.playable_content_sha256,
        record.progress,
        record.rebased_from_run_revision,
    )


def _manifest_snapshot(root: Path, run_id: str = RUN_ID_A):
    manifest = get_play_run_reference_manifest(root, run_id)
    return (manifest.playable_revision, manifest.playable_content_sha256)


def _write_leftover_intent(root: Path, *, run_id: str = RUN_ID_A, payload: str = "{}\n") -> Path:
    path = leftover_rebase_intent_path(root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def _rebase_failure_leaves_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[object, object, WorkspaceDocumentSnapshot, object]:
    import application_state.play.repository as play_repository

    source = _create_committed_runbook(tmp_path)
    created = _seal(tmp_path, source)[0]
    source_manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    real_replace_manifest = play_repository.replace_manifest

    def explode(*_args, **_kwargs):
        raise RuntimeError("forced rebase manifest replace failure")

    monkeypatch.setattr("application_state.play.repository.replace_manifest", explode)
    with pytest.raises(RuntimeError, match="forced rebase manifest replace failure"):
        _rebase(tmp_path, target, expected_run_revision=created.run_revision)
    return created, source_manifest, target, real_replace_manifest


def test_surviving_refs_rebase_replaces_binding_and_manifest(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    before = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    source_run = _record_snapshot(get_play_run(tmp_path, RUN_ID_A))
    source_manifest = _manifest_snapshot(tmp_path)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)

    rebased = _rebase(tmp_path, target, expected_run_revision=2)

    assert rebased.run_id == before.run_id
    assert rebased.campaign_id == before.campaign_id
    assert rebased.playable_artifact_id == before.playable_artifact_id
    assert rebased.created_at == before.created_at
    assert rebased.progress == before.progress
    assert rebased.playable_revision == _playable(target)[0]
    assert rebased.playable_content_sha256 == target.content_sha256
    assert rebased.run_revision == 3
    assert rebased.rebased_from_run_revision == 2
    assert _record_snapshot(get_play_run(tmp_path, RUN_ID_A)) != source_run
    assert _manifest_snapshot(tmp_path) != source_manifest
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert manifest.playable_revision == _playable(target)[0]
    assert manifest.playable_content_sha256 == target.content_sha256
    assert {element.element_id for element in manifest.elements} >= {
        "scene:gate",
        "beat:arrival",
        "scene:keep",
    }


def test_empty_progress_can_cross_full_element_replacement(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, REPLACED_TARGET_MARKDOWN)
    rebased = _rebase(tmp_path, target, expected_run_revision=1)
    assert rebased.progress.current_scene_id is None
    assert rebased.playable_revision == _playable(target)[0]
    assert rebased.run_revision == 2
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert {element.element_id for element in manifest.elements} == {
        "beat:dock",
        "scene:harbor",
    }


def test_removed_refs_block_before_intent(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    run_before = _record_snapshot(get_play_run(tmp_path, RUN_ID_A))
    manifest_before = _manifest_snapshot(tmp_path)
    target = _advance(tmp_path, source, REPLACED_TARGET_MARKDOWN)

    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=2)
    assert exc_info.value.status_code == 409
    assert "current_scene_id" in str(exc_info.value)
    assert _record_snapshot(get_play_run(tmp_path, RUN_ID_A)) == run_before
    assert _manifest_snapshot(tmp_path) == manifest_before
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_operator_clears_blocker_then_rebase_succeeds(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    target = _advance(tmp_path, source, REPLACED_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError):
        _rebase(tmp_path, target, expected_run_revision=2)
    cleared = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=2,
        progress=PlayRunProgress(
            current_scene_id=None,
            current_beat_id=None,
            resolved_beat_ids=[],
            selections={},
            notes_by_element_id={},
        ),
    )
    rebased = _rebase(tmp_path, target, expected_run_revision=cleared.run_revision)
    assert rebased.run_revision == cleared.run_revision + 1
    assert rebased.playable_revision == _playable(target)[0]


def test_wrong_target_snapshot_is_409(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            target_playable_revision=_playable(target)[0],
            target_playable_content_sha256="0" * 64,
        )
    assert exc_info.value.status_code == 409
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_missing_source_manifest_empty_progress_is_allowed(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    created = _create_run(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    rebased = _rebase(tmp_path, target, expected_run_revision=created.run_revision)
    assert rebased.run_revision == created.run_revision + 1
    assert get_play_run_reference_manifest(tmp_path, RUN_ID_A).playable_revision == _playable(target)[0]
    assert not leftover_manifest_path(tmp_path, RUN_ID_A).exists()


def test_missing_source_manifest_with_progress_is_409(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    created = _create_run(tmp_path, source)
    progressed = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        progress=_progress(),
    )
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    rebased = _rebase(tmp_path, target, expected_run_revision=progressed.run_revision)
    assert rebased.run_revision == progressed.run_revision + 1
    assert rebased.progress == _progress()
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_intent_write_failure_leaves_source_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created, source_manifest, target, real_replace = _rebase_failure_leaves_source(tmp_path, monkeypatch)
    assert get_play_run(tmp_path, RUN_ID_A).run_revision == created.run_revision
    assert get_play_run_reference_manifest(tmp_path, RUN_ID_A) == source_manifest
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()
    monkeypatch.setattr("application_state.play.repository.replace_manifest", real_replace)
    recovered = _rebase(tmp_path, target, expected_run_revision=created.run_revision)
    assert recovered.run_revision == created.run_revision + 1








def test_completed_replay_proves_target_pair(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    first = _rebase(tmp_path, target, expected_run_revision=1)
    replayed = _rebase(tmp_path, target, expected_run_revision=1)
    assert replayed == first
    leftover = leftover_manifest_path(tmp_path, RUN_ID_A)
    leftover.parent.mkdir(parents=True, exist_ok=True)
    leftover.write_text("{}\n", encoding="utf-8")
    again = _rebase(tmp_path, target, expected_run_revision=1)
    assert again == first
    assert get_play_run(tmp_path, RUN_ID_A) == first
    assert leftover.is_file()




def test_p2b2_can_select_target_only_id_after_rebase(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    rebased = _rebase(tmp_path, target, expected_run_revision=1)
    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=rebased.run_revision,
        progress=_progress(
            current_scene_id="scene:keep",
            current_beat_id="beat:inside",
            resolved_beat_ids=["beat:arrival"],
            selections={"choice:route": "option:wait"},
            notes_by_element_id={"scene:keep": "Quiet."},
        ),
    )
    assert updated.run_revision == rebased.run_revision + 1
    assert updated.progress.current_scene_id == "scene:keep"


def test_p2a_old_binding_conflicts_after_rebase(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    created = _create_run(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    _rebase(tmp_path, target, expected_run_revision=1)
    with pytest.raises(PlayRunRegistryError) as exc_info:
        create_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            playable_artifact_id=created.playable_artifact_id,
            expected_playable_revision=_playable(source)[0],
            expected_playable_content_sha256=source.content_sha256,
        )
    assert exc_info.value.status_code == 409
    replayed = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=created.playable_artifact_id,
        expected_playable_revision=_playable(target)[0],
        expected_playable_content_sha256=target.content_sha256,
    )
    assert replayed.playable_revision == _playable(target)[0]




@pytest.mark.parametrize(
    ("markdown", "progress", "needle"),
    [
        (
            SCENE_RENAMED_MARKDOWN,
            _progress(
                current_beat_id=None,
                resolved_beat_ids=[],
                selections={},
                notes_by_element_id={},
            ),
            "scene:gate",
        ),
        (
            ARRIVAL_REMOVED_MARKDOWN,
            _progress(
                resolved_beat_ids=[],
                selections={},
                notes_by_element_id={},
            ),
            "beat:arrival",
        ),
        (
            BRIEFING_REMOVED_MARKDOWN,
            _progress(
                current_beat_id=None,
                selections={},
                notes_by_element_id={},
            ),
            "beat:briefing",
        ),
        (
            FIRE_REMOVED_MARKDOWN,
            _progress(
                current_beat_id=None,
                resolved_beat_ids=[],
                notes_by_element_id={},
            ),
            "option:fire",
        ),
        (
            WAIT_REMOVED_MARKDOWN,
            _progress(
                current_beat_id=None,
                resolved_beat_ids=[],
                selections={},
                notes_by_element_id={"option:wait": "They waited."},
            ),
            "option:wait",
        ),
    ],
)
def test_each_progress_field_blocks_before_intent(
    tmp_path: Path,
    markdown: str,
    progress: PlayRunProgress,
    needle: str,
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=progress,
    )
    run_before = _record_snapshot(get_play_run(tmp_path, RUN_ID_A))
    manifest_before = _manifest_snapshot(tmp_path)
    target = _advance(tmp_path, source, markdown)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=2)
    assert exc_info.value.status_code == 409
    assert needle in str(exc_info.value) or "current_scene_id" in str(exc_info.value) or "current_beat_id" in str(exc_info.value) or "resolved_beat_ids" in str(exc_info.value) or "selections" in str(exc_info.value) or "notes_by_element_id" in str(exc_info.value)
    assert _record_snapshot(get_play_run(tmp_path, RUN_ID_A)) == run_before
    assert _manifest_snapshot(tmp_path) == manifest_before
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_malformed_target_markdown_is_409_before_intent(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    created = _seal(tmp_path, source)[0]
    target = _advance(tmp_path, source, MALFORMED_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=created.run_revision)
    assert exc_info.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A) == created
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_progress_and_rebase_linearize_on_run_lock(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    results: list[object] = []
    errors: list[BaseException] = []

    def write_progress() -> None:
        try:
            results.append(
                replace_play_run_progress(
                    tmp_path,
                    run_id=RUN_ID_A,
                    expected_run_revision=1,
                    progress=_progress(
                        current_beat_id=None,
                        resolved_beat_ids=[],
                        selections={},
                        notes_by_element_id={},
                    ),
                )
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    def write_rebase() -> None:
        try:
            results.append(_rebase(tmp_path, target, expected_run_revision=1))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        Thread(target=write_progress, daemon=True),
        Thread(target=write_rebase, daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=4.0)
        assert not thread.is_alive()
    assert len(results) == 1
    assert len(errors) == 1
    assert getattr(errors[0], "status_code", None) == 409
    current = get_play_run(tmp_path, RUN_ID_A)
    assert current.run_revision == 2
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()










def test_p2b1_replay_after_rebase_does_not_rewrite(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    _rebase(tmp_path, target, expected_run_revision=1)
    before = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    replayed = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert replayed == before
    assert replayed.playable_revision == _playable(target)[0]


def test_deleted_target_manifest_blocks_completed_replay(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    first = _rebase(tmp_path, target, expected_run_revision=1)
    replayed = _rebase(tmp_path, target, expected_run_revision=1)
    assert replayed == first
    leftover = leftover_manifest_path(tmp_path, RUN_ID_A)
    leftover.parent.mkdir(parents=True, exist_ok=True)
    leftover.write_text("{}\n", encoding="utf-8")
    again = _rebase(tmp_path, target, expected_run_revision=1)
    assert again == first
    assert get_play_run(tmp_path, RUN_ID_A) == first
    assert leftover.is_file()


def test_unsorted_persisted_resolved_beats_are_not_legitimized(
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(selections={}, notes_by_element_id={}),
    )
    progress = _progress(resolved_beat_ids=["beat:arrival", "beat:briefing"]).model_dump(mode="json")
    progress["resolved_beat_ids"] = ["beat:ghost"]
    _update_run_progress(application_state_dsn, RUN_ID_A, progress)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=2)
    assert exc_info.value.status_code in {409, 500}
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_source_invalid_ref_is_not_saved_by_target_admission(
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    progress = _progress(
        current_scene_id="scene:ghost",
        current_beat_id=None,
        resolved_beat_ids=[],
        selections={},
        notes_by_element_id={},
    ).model_dump(mode="json")
    _update_run_progress(application_state_dsn, RUN_ID_A, progress)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code in {409, 500}
    assert not leftover_rebase_intent_path(tmp_path, RUN_ID_A).exists()






def test_progress_mutation_is_not_completed_rebase_replay(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path, markdown=SURVIVING_TARGET_MARKDOWN)
    _seal(tmp_path, source)
    progressed = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(
            current_scene_id="scene:keep",
            current_beat_id="beat:inside",
            resolved_beat_ids=["beat:arrival"],
            selections={"choice:route": "option:wait"},
            notes_by_element_id={},
        ),
    )
    assert progressed.run_revision == 2
    assert progressed.rebased_from_run_revision is None
    run_before = get_play_run(tmp_path, RUN_ID_A)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, source, expected_run_revision=1)
    assert exc_info.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A) == run_before
    noop = _rebase(tmp_path, source, expected_run_revision=2)
    assert noop.run_revision == 2
    assert get_play_run(tmp_path, RUN_ID_A) == noop




