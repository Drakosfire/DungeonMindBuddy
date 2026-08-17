from __future__ import annotations

import json
from pathlib import Path
from threading import Event, Thread

import pytest

from apps.live_control_server.services.play_run_rebase import (
    PlayRunRebaseError,
    play_run_rebase_intent_path,
    rebase_or_replay_play_run,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    PlayRunRegistryError,
    create_or_replay_play_run,
    get_play_run,
    list_play_runs,
    play_run_path,
    replace_play_run_progress,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    get_play_run_reference_manifest,
    play_run_reference_manifest_path,
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
    WorkspaceDocumentSnapshot,
    create_workspace_document,
    get_workspace_document_snapshot,
    update_workspace_document_metadata,
)
from src.live_play.live_store import load_json, write_json

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
    return get_workspace_document_snapshot(root, record.document_id)


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
        expected_playable_revision=snapshot.loaded_revision,
        expected_playable_content_sha256=snapshot.content_sha256,
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
        target_playable_revision=snapshot.loaded_revision,
        target_playable_content_sha256=snapshot.content_sha256,
    )


def test_surviving_refs_rebase_replaces_binding_and_manifest(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    before = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    source_run_bytes = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    source_manifest_bytes = play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes()
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)

    rebased = _rebase(tmp_path, target, expected_run_revision=2)

    assert rebased.run_id == before.run_id
    assert rebased.campaign_id == before.campaign_id
    assert rebased.playable_artifact_id == before.playable_artifact_id
    assert rebased.created_at == before.created_at
    assert rebased.progress == before.progress
    assert rebased.playable_revision == target.loaded_revision
    assert rebased.playable_content_sha256 == target.content_sha256
    assert rebased.run_revision == 3
    assert rebased.rebased_from_run_revision == 2
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() != source_run_bytes
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes() != source_manifest_bytes
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert manifest.playable_revision == target.loaded_revision
    assert manifest.playable_content_sha256 == target.content_sha256
    assert {element.element_id for element in manifest.elements} >= {
        "scene:gate",
        "beat:arrival",
        "scene:keep",
    }
    assert not (tmp_path / "out/runtime/play/rebase-intents").exists() or list(
        (tmp_path / "out/runtime/play/rebase-intents").glob("*.json")
    ) == []


def test_empty_progress_can_cross_full_element_replacement(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, REPLACED_TARGET_MARKDOWN)
    rebased = _rebase(tmp_path, target, expected_run_revision=1)
    assert rebased.progress.current_scene_id is None
    assert rebased.playable_revision == target.loaded_revision
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
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    manifest_before = play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes()
    target = _advance(tmp_path, source, REPLACED_TARGET_MARKDOWN)

    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=2)
    assert exc_info.value.status_code == 409
    assert "current_scene_id" in str(exc_info.value)
    assert "scene:gate" in str(exc_info.value)
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes() == manifest_before
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


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
    assert rebased.playable_revision == target.loaded_revision


def test_wrong_target_snapshot_is_409(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            target_playable_revision=target.loaded_revision,
            target_playable_content_sha256="0" * 64,
        )
    assert exc_info.value.status_code == 409
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_missing_source_manifest_empty_progress_is_allowed(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _create_run(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    rebased = _rebase(tmp_path, target, expected_run_revision=1)
    assert rebased.run_revision == 2
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).is_file()


def test_missing_source_manifest_with_progress_is_409(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    record = _create_run(tmp_path, source)
    payload = json.loads(play_run_path(tmp_path, RUN_ID_A).read_text(encoding="utf-8"))
    payload["progress"] = _progress().model_dump(mode="json")
    play_run_path(tmp_path, RUN_ID_A).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=record.run_revision)
    assert exc_info.value.status_code == 500
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_intent_write_failure_leaves_source_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    manifest_before = play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes()

    def boom(path: Path, data: dict) -> None:
        if "rebase-intents" in path.parts:
            raise OSError("intent disk full")
        write_json(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 500
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes() == manifest_before
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_manifest_write_failure_after_intent_recovers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = write_json

    def boom(path: Path, data: dict) -> None:
        if path == play_run_reference_manifest_path(tmp_path, RUN_ID_A) and play_run_rebase_intent_path(
            tmp_path, RUN_ID_A
        ).is_file():
            raise OSError("manifest disk full")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 503
    assert play_run_rebase_intent_path(tmp_path, RUN_ID_A).is_file()
    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        original,
    )
    with pytest.raises(PlayRunRegistryError) as get_exc:
        get_play_run(tmp_path, RUN_ID_A)
    assert get_exc.value.status_code == 503
    recovered = _rebase(tmp_path, target, expected_run_revision=1)
    assert recovered.run_revision == 2
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_run_write_failure_after_manifest_recovers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = write_json
    source_run = play_run_path(tmp_path, RUN_ID_A).read_bytes()

    def boom(path: Path, data: dict) -> None:
        if path == play_run_path(tmp_path, RUN_ID_A) and play_run_rebase_intent_path(
            tmp_path, RUN_ID_A
        ).is_file():
            raise OSError("run disk full")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 503
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == source_run
    assert play_run_rebase_intent_path(tmp_path, RUN_ID_A).is_file()
    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        original,
    )
    recovered = _rebase(tmp_path, target, expected_run_revision=1)
    assert recovered.run_revision == 2
    assert recovered.playable_revision == target.loaded_revision


def test_cleanup_failure_after_commit_recovers_without_increment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original_unlink = Path.unlink

    def boom(self: Path, *args: object, **kwargs: object) -> None:
        if self == play_run_rebase_intent_path(tmp_path, RUN_ID_A):
            raise OSError("unlink failed")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", boom)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 503
    assert play_run_rebase_intent_path(tmp_path, RUN_ID_A).is_file()
    monkeypatch.setattr(Path, "unlink", original_unlink)
    recovered = _rebase(tmp_path, target, expected_run_revision=1)
    assert recovered.run_revision == 2
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_completed_replay_proves_target_pair(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    first = _rebase(tmp_path, target, expected_run_revision=1)
    replayed = _rebase(tmp_path, target, expected_run_revision=1)
    assert replayed == first
    run_bytes = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    manifest_path = play_run_reference_manifest_path(tmp_path, RUN_ID_A)
    manifest_bytes = manifest_path.read_bytes()
    manifest_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 500
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_bytes
    assert manifest_path.read_bytes() != manifest_bytes


def test_pending_intent_isolates_predecessors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = write_json

    def boom(path: Path, data: dict) -> None:
        if path == play_run_reference_manifest_path(tmp_path, RUN_ID_A) and play_run_rebase_intent_path(
            tmp_path, RUN_ID_A
        ).is_file():
            raise OSError("stop after intent")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    with pytest.raises(PlayRunRebaseError):
        _rebase(tmp_path, target, expected_run_revision=1)
    assert play_run_rebase_intent_path(tmp_path, RUN_ID_A).is_file()

    with pytest.raises(PlayRunRegistryError) as get_exc:
        get_play_run(tmp_path, RUN_ID_A)
    assert get_exc.value.status_code == 503
    with pytest.raises(PlayRunRegistryError) as list_exc:
        list_play_runs(tmp_path)
    assert list_exc.value.status_code == 503
    with pytest.raises(PlayRunRegistryError) as progress_exc:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_progress(
                current_scene_id=None,
                current_beat_id=None,
                resolved_beat_ids=[],
                selections={},
                notes_by_element_id={},
            ),
        )
    assert progress_exc.value.status_code == 503
    with pytest.raises(PlayRunRegistryError) as seal_exc:
        seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert seal_exc.value.status_code == 503
    with pytest.raises(PlayRunRegistryError) as manifest_get_exc:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert manifest_get_exc.value.status_code == 503
    with pytest.raises(PlayRunRegistryError) as create_exc:
        create_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            playable_artifact_id=source.record.document_id,
            expected_playable_revision=source.loaded_revision,
            expected_playable_content_sha256=source.content_sha256,
        )
    assert create_exc.value.status_code == 503
    with pytest.raises(PlayRunRebaseError) as other_exc:
        rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            target_playable_revision=target.loaded_revision + 5,
            target_playable_content_sha256=target.content_sha256,
        )
    assert other_exc.value.status_code == 409


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
            expected_playable_revision=source.loaded_revision,
            expected_playable_content_sha256=source.content_sha256,
        )
    assert exc_info.value.status_code == 409
    replayed = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=created.playable_artifact_id,
        expected_playable_revision=target.loaded_revision,
        expected_playable_content_sha256=target.content_sha256,
    )
    assert replayed.playable_revision == target.loaded_revision


def test_get_waits_for_in_process_half_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = write_json
    write_entered = Event()
    allow_write = Event()
    get_done = Event()
    rebase_errors: list[BaseException] = []
    get_errors: list[BaseException] = []
    records: list[object] = []

    def gated(path: Path, data: dict) -> None:
        if path == play_run_path(tmp_path, RUN_ID_A) and play_run_rebase_intent_path(
            tmp_path, RUN_ID_A
        ).is_file():
            write_entered.set()
            if not allow_write.wait(timeout=2.0):
                raise AssertionError("timed out waiting to release Run write")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        gated,
    )

    def run_rebase() -> None:
        try:
            records.append(_rebase(tmp_path, target, expected_run_revision=1))
        except BaseException as exc:  # noqa: BLE001
            rebase_errors.append(exc)

    def run_get() -> None:
        try:
            records.append(get_play_run(tmp_path, RUN_ID_A))
        except BaseException as exc:  # noqa: BLE001
            get_errors.append(exc)
        finally:
            get_done.set()

    rebase_thread = Thread(target=run_rebase, daemon=True)
    rebase_thread.start()
    assert write_entered.wait(timeout=2.0)

    get_thread = Thread(target=run_get, daemon=True)
    get_thread.start()
    try:
        assert not get_done.wait(timeout=0.1)
        assert json.loads(play_run_path(tmp_path, RUN_ID_A).read_text(encoding="utf-8"))[
            "playable_revision"
        ] == source.loaded_revision
        assert json.loads(
            play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_text(encoding="utf-8")
        )["playable_revision"] == target.loaded_revision
    finally:
        allow_write.set()

    rebase_thread.join(timeout=2.0)
    get_thread.join(timeout=2.0)
    assert not rebase_thread.is_alive()
    assert not get_thread.is_alive()
    assert rebase_errors == []
    assert get_errors == []
    assert len(records) == 2
    assert {record.run_revision for record in records} == {2}  # type: ignore[attr-defined]


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
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    manifest_before = play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes()
    target = _advance(tmp_path, source, markdown)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=2)
    assert exc_info.value.status_code == 409
    assert needle in str(exc_info.value)
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes() == manifest_before
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_malformed_target_markdown_is_409_before_intent(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    target = _advance(tmp_path, source, MALFORMED_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 409
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


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
    assert getattr(errors[0], "status_code", None) in {409, 503}
    current = get_play_run(tmp_path, RUN_ID_A)
    assert current.run_revision == 2
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_rebase_holds_workspace_lock_through_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = write_json
    write_entered = Event()
    allow_write = Event()
    mutation_started = Event()
    mutation_done = Event()
    rebase_errors: list[BaseException] = []
    mutation_errors: list[BaseException] = []

    def gated(path: Path, data: dict) -> None:
        if "rebase-intents" in path.parts:
            write_entered.set()
            if not allow_write.wait(timeout=2.0):
                raise AssertionError("timed out waiting to release intent write")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        gated,
    )

    def run_rebase() -> None:
        try:
            _rebase(tmp_path, target, expected_run_revision=1)
        except BaseException as exc:  # noqa: BLE001
            rebase_errors.append(exc)

    def mutate_runbook() -> None:
        mutation_started.set()
        try:
            update_workspace_document_metadata(
                tmp_path,
                source.record.document_id,
                title="Advanced during rebase prepare",
                expected_revision=target.loaded_revision,
            )
        except BaseException as exc:  # noqa: BLE001
            mutation_errors.append(exc)
        finally:
            mutation_done.set()

    rebase_thread = Thread(target=run_rebase, daemon=True)
    rebase_thread.start()
    assert write_entered.wait(timeout=2.0)
    mutation_thread = Thread(target=mutate_runbook, daemon=True)
    mutation_thread.start()
    assert mutation_started.wait(timeout=2.0)
    try:
        assert not mutation_done.wait(timeout=0.1)
    finally:
        allow_write.set()
    rebase_thread.join(timeout=2.0)
    mutation_thread.join(timeout=2.0)
    assert not rebase_thread.is_alive()
    assert not mutation_thread.is_alive()
    assert rebase_errors == []
    assert mutation_errors == []
    assert get_play_run(tmp_path, RUN_ID_A).playable_revision == target.loaded_revision


def test_corrupt_intent_fails_closed(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    intent_path = play_run_rebase_intent_path(tmp_path, RUN_ID_A)
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text("{not-json", encoding="utf-8")
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 500
    assert intent_path.read_text(encoding="utf-8") == "{not-json"
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before


def test_contradictory_recovery_stage_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = write_json

    def boom(path: Path, data: dict) -> None:
        if path == play_run_reference_manifest_path(tmp_path, RUN_ID_A) and play_run_rebase_intent_path(
            tmp_path, RUN_ID_A
        ).is_file():
            raise OSError("stop after intent")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    with pytest.raises(PlayRunRebaseError):
        _rebase(tmp_path, target, expected_run_revision=1)
    play_run_path(tmp_path, RUN_ID_A).write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        original,
    )
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 500
    assert play_run_path(tmp_path, RUN_ID_A).read_text(encoding="utf-8") == "{}\n"
    assert play_run_rebase_intent_path(tmp_path, RUN_ID_A).is_file()


def test_workspace_advance_after_intent_does_not_retarget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = write_json

    def boom(path: Path, data: dict) -> None:
        if path == play_run_reference_manifest_path(tmp_path, RUN_ID_A) and play_run_rebase_intent_path(
            tmp_path, RUN_ID_A
        ).is_file():
            raise OSError("stop after intent")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    with pytest.raises(PlayRunRebaseError):
        _rebase(tmp_path, target, expected_run_revision=1)
    later = _advance(tmp_path, target, THIRD_ADVANCE_MARKDOWN)
    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        original,
    )
    recovered = _rebase(tmp_path, target, expected_run_revision=1)
    assert recovered.playable_revision == target.loaded_revision
    assert recovered.playable_content_sha256 == target.content_sha256
    assert recovered.playable_revision != later.loaded_revision
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert "scene:tower" not in {element.element_id for element in manifest.elements}
    assert "scene:keep" in {element.element_id for element in manifest.elements}


def test_p2b1_replay_after_rebase_does_not_rewrite(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    _rebase(tmp_path, target, expected_run_revision=1)
    before = play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes()
    replayed = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert replayed.playable_revision == target.loaded_revision
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes() == before


def test_deleted_target_manifest_blocks_completed_replay(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    first = _rebase(tmp_path, target, expected_run_revision=1)
    run_bytes = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    play_run_reference_manifest_path(tmp_path, RUN_ID_A).unlink()
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 500
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_bytes
    assert first.run_revision == 2


def test_unsorted_persisted_resolved_beats_are_not_legitimized(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(selections={}, notes_by_element_id={}),
    )
    payload = json.loads(play_run_path(tmp_path, RUN_ID_A).read_text(encoding="utf-8"))
    payload["progress"]["resolved_beat_ids"] = ["beat:briefing", "beat:arrival"]
    play_run_path(tmp_path, RUN_ID_A).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=2)
    assert exc_info.value.status_code == 500
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def test_source_invalid_ref_is_not_saved_by_target_admission(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    payload = json.loads(play_run_path(tmp_path, RUN_ID_A).read_text(encoding="utf-8"))
    payload["progress"] = _progress(
        current_scene_id="scene:keep",
        current_beat_id=None,
        resolved_beat_ids=[],
        selections={},
        notes_by_element_id={},
    ).model_dump(mode="json")
    play_run_path(tmp_path, RUN_ID_A).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 500
    assert not play_run_rebase_intent_path(tmp_path, RUN_ID_A).exists()


def _stop_after_intent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    original = write_json

    def boom(path: Path, data: dict) -> None:
        if path == play_run_reference_manifest_path(tmp_path, RUN_ID_A) and play_run_rebase_intent_path(
            tmp_path, RUN_ID_A
        ).is_file():
            raise OSError("stop after intent")
        original(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        boom,
    )
    return original


def test_tampered_intent_progress_cannot_drop_source_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = _stop_after_intent(tmp_path, monkeypatch)
    with pytest.raises(PlayRunRebaseError):
        _rebase(tmp_path, target, expected_run_revision=2)
    intent_path = play_run_rebase_intent_path(tmp_path, RUN_ID_A)
    payload = load_json(intent_path)
    payload["target_run"]["progress"] = {
        "current_scene_id": None,
        "current_beat_id": None,
        "resolved_beat_ids": [],
        "selections": {},
        "notes_by_element_id": {},
    }
    original(intent_path, payload)
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        original,
    )
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=2)
    assert exc_info.value.status_code == 500
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before
    assert intent_path.is_file()


def test_tampered_intent_campaign_cannot_rewrite_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    target = _advance(tmp_path, source, SURVIVING_TARGET_MARKDOWN)
    original = _stop_after_intent(tmp_path, monkeypatch)
    with pytest.raises(PlayRunRebaseError):
        _rebase(tmp_path, target, expected_run_revision=1)
    intent_path = play_run_rebase_intent_path(tmp_path, RUN_ID_A)
    payload = load_json(intent_path)
    payload["target_run"]["campaign_id"] = "other-campaign"
    original(intent_path, payload)
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_rebase.write_json",
        original,
    )
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, target, expected_run_revision=1)
    assert exc_info.value.status_code == 500
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before
    assert json.loads(run_before)["campaign_id"] == "longmont-c2"


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
    run_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()
    with pytest.raises(PlayRunRebaseError) as exc_info:
        _rebase(tmp_path, source, expected_run_revision=1)
    assert exc_info.value.status_code == 409
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before
    noop = _rebase(tmp_path, source, expected_run_revision=2)
    assert noop.run_revision == 2
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_before


def test_orphan_pending_intent_fails_the_whole_list(tmp_path: Path) -> None:
    source = _create_committed_runbook(tmp_path)
    _seal(tmp_path, source)
    intent_path = play_run_rebase_intent_path(tmp_path, RUN_ID_B)
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PlayRunRegistryError) as listed:
        list_play_runs(tmp_path)
    assert listed.value.status_code == 503
    assert get_play_run(tmp_path, RUN_ID_A).run_id == RUN_ID_A


def test_orphan_intent_without_runs_dir_does_not_list_empty(tmp_path: Path) -> None:
    intent_path = play_run_rebase_intent_path(tmp_path, RUN_ID_A)
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PlayRunRegistryError) as listed:
        list_play_runs(tmp_path)
    assert listed.value.status_code == 503
