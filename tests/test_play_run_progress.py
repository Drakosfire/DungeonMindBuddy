from __future__ import annotations

from pathlib import Path
from threading import Thread

import psycopg
import pytest

from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    PlayRunRegistryError,
    create_or_replay_play_run,
    empty_play_run_progress,
    get_play_run,
    list_play_runs,
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
    WorkspaceDocumentSnapshot,
    create_workspace_document,
    get_workspace_document_snapshot,
)
from tests.application_state.playable_binding import (
    playable_binding,
    remember_committed_playable,
)
from tests.application_state.play_runtime_helpers import (
    fetch_play_runtime_state,
    leftover_manifest_path,
    leftover_run_path,
)

pytest_plugins = ["tests.application_state.conftest"]

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


@pytest.fixture(autouse=True)
def _application_state(application_state_dsn: str) -> str:
    return application_state_dsn

PROGRESS_MARKDOWN = "\n".join(
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
        "<!-- dmb-playable-element:v1 kind=scene id=scene:keep -->",
        "## The Keep",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:inside -->",
        "### Inside",
        "",
        "<!-- dmb-playable-element:v1 kind=choice id=choice:door -->",
        "### The door",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:open -->",
        "#### Open it",
        "",
    ]
)

ADVANCED_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:harbor -->",
        "## Harbor",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:dock -->",
        "### Dock",
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
    return remember_committed_playable(get_workspace_document_snapshot(root, record.document_id))


def _create_committed_runbook(
    root: Path,
    *,
    name: str = "progress-run",
    markdown: str = PROGRESS_MARKDOWN,
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
    revision_n, sha = playable_binding(snapshot)
    return create_or_replay_play_run(
        root,
        run_id=RUN_ID_A,
        playable_artifact_id=snapshot.record.document_id,
        expected_playable_revision=revision_n,
        expected_playable_content_sha256=sha,
    )


def _seal(root: Path, snapshot: WorkspaceDocumentSnapshot):
    record = _create_run(root, snapshot)
    manifest = seal_or_replay_play_run_reference_manifest(root, RUN_ID_A)
    return record, manifest


def _update_run_progress(dsn: str, run_id: str, progress: dict) -> None:
    from psycopg.types.json import Jsonb

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            "UPDATE play.run SET progress = %(progress)s WHERE run_id = %(run_id)s",
            {"progress": Jsonb(progress), "run_id": run_id},
        )


def _write_leftover_run_file(root: Path, record) -> None:
    from src.live_play.live_store import write_json

    path = leftover_run_path(root, RUN_ID_A)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, record.model_dump(mode="json"))


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


def test_valid_snapshot_persists_and_reloads(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    record, manifest = _seal(tmp_path, snapshot)
    binding = (
        record.playable_artifact_id,
        record.playable_revision,
        record.playable_content_sha256,
        record.created_at,
    )

    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )

    assert updated.run_revision == 2
    assert updated.created_at == record.created_at
    assert updated.updated_at != record.updated_at
    assert (
        updated.playable_artifact_id,
        updated.playable_revision,
        updated.playable_content_sha256,
        updated.created_at,
    ) == binding
    assert updated.progress == _progress()
    reloaded = get_play_run(tmp_path, RUN_ID_A)
    assert reloaded == updated
    assert get_play_run_reference_manifest(tmp_path, RUN_ID_A) == manifest
    assert not leftover_manifest_path(tmp_path, RUN_ID_A).exists()


def test_unknown_and_cross_membership_references_are_422_without_write(
    tmp_path: Path,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    record_before = get_play_run(tmp_path, RUN_ID_A)

    cases = [
        _progress(current_scene_id="scene:ghost"),
        _progress(current_beat_id="choice:route"),
        _progress(current_scene_id="scene:gate", current_beat_id="beat:inside"),
        _progress(resolved_beat_ids=["beat:missing"]),
        _progress(selections={"choice:route": "option:open"}),
        _progress(notes_by_element_id={"scene:ghost": "nope"}),
    ]
    for progress in cases:
        with pytest.raises(PlayRunRegistryError) as exc_info:
            replace_play_run_progress(
                tmp_path,
                run_id=RUN_ID_A,
                expected_run_revision=1,
                progress=progress,
            )
        assert exc_info.value.status_code == 422
        assert get_play_run(tmp_path, RUN_ID_A) == record_before
        assert get_play_run(tmp_path, RUN_ID_A).run_revision == 1


def test_missing_manifest_is_409_without_auto_seal_or_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    created = _create_run(tmp_path, snapshot)

    def explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("progress mutation must not consult workspace state")

    monkeypatch.setattr(
        "apps.live_control_server.services.workspace_document_registry.get_workspace_document_snapshot",
        explode,
    )

    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )

    assert updated.run_revision == 2
    assert updated.progress == _progress()
    assert get_play_run(tmp_path, RUN_ID_A) == updated
    assert created.run_revision == 1
    assert not leftover_manifest_path(tmp_path, RUN_ID_A).exists()


def test_runbook_advance_is_irrelevant_after_seal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    record, _manifest = _seal(tmp_path, snapshot)
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=snapshot.record.document_id,
            markdown=ADVANCED_MARKDOWN,
            expected_revision=snapshot.loaded_revision,
        ),
    )
    commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=snapshot.record.document_id,
            markdown=ADVANCED_MARKDOWN,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=snapshot.loaded_revision,
        ),
    )
    advanced = get_workspace_document_snapshot(tmp_path, snapshot.record.document_id)
    assert advanced.loaded_revision > record.playable_revision

    def explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("progress mutation must not consult current Runbook")

    monkeypatch.setattr(
        "apps.live_control_server.services.workspace_document_registry.get_workspace_document_snapshot",
        explode,
    )

    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    assert updated.run_revision == 2
    assert updated.playable_revision == record.playable_revision
    assert updated.progress.current_scene_id == "scene:gate"


def test_concurrent_cas_has_one_winner(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    first_progress = _progress()
    second_progress = _progress(
        current_beat_id=None,
        resolved_beat_ids=["beat:arrival", "beat:inside"],
        selections={"choice:door": "option:open"},
        notes_by_element_id={"scene:keep": "Quiet."},
    )
    results: list[object] = []
    errors: list[PlayRunRegistryError] = []

    def write(progress: PlayRunProgress) -> None:
        try:
            results.append(
                replace_play_run_progress(
                    tmp_path,
                    run_id=RUN_ID_A,
                    expected_run_revision=1,
                    progress=progress,
                )
            )
        except PlayRunRegistryError as exc:
            errors.append(exc)

    threads = [
        Thread(target=write, args=(first_progress,), daemon=True),
        Thread(target=write, args=(second_progress,), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2.0)
        assert not thread.is_alive()

    assert len(results) == 1
    assert len(errors) == 1
    assert errors[0].status_code == 409
    winner = results[0]
    final = get_play_run(tmp_path, RUN_ID_A)
    assert final == winner
    assert final.run_revision == 2
    assert final.progress in (first_progress, second_progress)


def test_current_token_same_state_is_byte_preserving_noop(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    first = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )

    replayed = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=2,
        progress=_progress(resolved_beat_ids=["beat:briefing", "beat:briefing"]),
    )

    assert replayed == first
    assert replayed.run_revision == 2
    assert replayed.updated_at == first.updated_at
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()


def test_lost_response_replay_does_not_increment_again(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    first = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )

    replayed = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )

    assert replayed == first
    assert replayed.run_revision == 2
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()


def test_stale_different_state_is_409(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    first = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )

    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_progress(current_beat_id=None),
        )

    assert exc_info.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A) == first
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()


def test_create_replay_after_progress_does_not_reset(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    created = _create_run(tmp_path, snapshot)
    seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    progressed = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )

    replayed = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=created.playable_artifact_id,
        expected_playable_revision=created.playable_revision,
        expected_playable_content_sha256=created.playable_content_sha256,
    )

    assert replayed == progressed
    assert replayed.run_revision == 2
    assert replayed.progress == _progress()
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()


def test_persisted_ghost_reference_fails_closed_on_reads(
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    progress = _progress().model_dump(mode="json")
    progress["current_scene_id"] = "scene:ghost"
    _update_run_progress(application_state_dsn, RUN_ID_A, progress)
    before = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        get_play_run(tmp_path, RUN_ID_A)
    assert exc_info.value.status_code == 500

    with pytest.raises(PlayRunRegistryError) as exc_info:
        list_play_runs(tmp_path)
    assert exc_info.value.status_code == 500

    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=2,
            progress=_progress(),
        )
    assert exc_info.value.status_code == 500
    assert fetch_play_runtime_state(application_state_dsn, RUN_ID_A) == before


def test_persisted_cross_choice_selection_fails_closed(
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    progress = _progress().model_dump(mode="json")
    progress["selections"]["choice:route"] = "option:open"
    _update_run_progress(application_state_dsn, RUN_ID_A, progress)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        get_play_run(tmp_path, RUN_ID_A)
    assert exc_info.value.status_code == 500


@pytest.mark.parametrize(
    "tampered_beats",
    [
        ["beat:briefing", "beat:arrival"],
        ["beat:arrival", "beat:arrival"],
    ],
)
def test_persisted_resolved_beats_must_be_duplicate_free_and_sorted(
    tmp_path: Path,
    application_state_dsn: str,
    tampered_beats: list[str],
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(resolved_beat_ids=["beat:briefing", "beat:arrival"]),
    )
    progress = _progress(resolved_beat_ids=["beat:arrival", "beat:briefing"]).model_dump(mode="json")
    progress["resolved_beat_ids"] = tampered_beats
    _update_run_progress(application_state_dsn, RUN_ID_A, progress)
    before = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)

    with pytest.raises(PlayRunRegistryError) as exc_info:
        get_play_run(tmp_path, RUN_ID_A)
    assert exc_info.value.status_code == 500

    with pytest.raises(PlayRunRegistryError) as exc_info:
        list_play_runs(tmp_path)
    assert exc_info.value.status_code == 500

    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=2,
            progress=_progress(resolved_beat_ids=["beat:arrival", "beat:briefing"]),
        )
    assert exc_info.value.status_code == 500
    assert fetch_play_runtime_state(application_state_dsn, RUN_ID_A) == before


def test_legacy_record_without_progress_reads_empty_and_can_mutate(
    tmp_path: Path,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    created = _create_run(tmp_path, snapshot)
    loaded = get_play_run(tmp_path, RUN_ID_A)
    assert loaded.progress == empty_play_run_progress()

    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_progress(),
    )
    assert updated.run_revision == 2
    assert updated.progress == _progress()
    assert updated.playable_artifact_id == created.playable_artifact_id
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()


def test_unknown_run_is_404(tmp_path: Path) -> None:
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_progress(),
        )
    assert exc_info.value.status_code == 404


V2_PROGRESS_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:one beat_kind=spine -->",
        "## Beat 1",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:a -->",
        "### Scene A",
        "",
        "<!-- dmb-playable-element:v2 kind=choice id=choice:x -->",
        "### Decision X",
        "",
        "<!-- dmb-playable-element:v2 kind=option id=option:x1 activates=beat:two -->",
        "- Option X1",
        "",
        "<!-- dmb-playable-element:v2 kind=option id=option:x2 suppresses=scene:b -->",
        "- Option X2",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:two beat_kind=optional -->",
        "## Beat 2",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:b -->",
        "### Scene B",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:three beat_kind=spine -->",
        "## Beat 3",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:c -->",
        "### Scene C",
        "",
    ]
)


def _v2_progress(**overrides: object) -> PlayRunProgress:
    payload = {
        "current_scene_id": None,
        "current_beat_id": "beat:one",
        "resolved_beat_ids": [],
        "selections": {},
        "notes_by_element_id": {},
    }
    payload.update(overrides)
    return PlayRunProgress.model_validate(payload)


def _seal_v2(tmp_path: Path, *, name: str = "v2-progress"):
    snapshot = _create_committed_runbook(tmp_path, name=name, markdown=V2_PROGRESS_MARKDOWN)
    return _seal(tmp_path, snapshot)


def test_v1_beat_only_progress_still_rejected(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _seal(tmp_path, snapshot)
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_progress(current_scene_id=None, current_beat_id="beat:arrival"),
        )
    assert exc_info.value.status_code == 422
    assert "current_beat_id requires current_scene_id" in str(exc_info.value)
    assert get_play_run(tmp_path, RUN_ID_A).progress == empty_play_run_progress()


def test_v2_beat_only_progress_is_admitted(tmp_path: Path) -> None:
    _seal_v2(tmp_path)
    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_progress(),
    )
    assert updated.progress.current_beat_id == "beat:one"
    assert updated.progress.current_scene_id is None
    reloaded = get_play_run(tmp_path, RUN_ID_A)
    assert reloaded.progress == updated.progress


def test_v2_beat_and_same_beat_scene_is_admitted(tmp_path: Path) -> None:
    _seal_v2(tmp_path)
    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_progress(current_scene_id="scene:a"),
    )
    assert updated.progress.current_beat_id == "beat:one"
    assert updated.progress.current_scene_id == "scene:a"


def test_v2_cross_beat_scene_is_rejected(tmp_path: Path) -> None:
    _seal_v2(tmp_path)
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_v2_progress(current_scene_id="scene:b"),
        )
    assert exc_info.value.status_code == 422
    assert get_play_run(tmp_path, RUN_ID_A).progress == empty_play_run_progress()


def test_v2_unknown_ids_are_rejected(tmp_path: Path) -> None:
    _seal_v2(tmp_path)
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_v2_progress(current_beat_id="beat:ghost"),
        )
    assert exc_info.value.status_code == 422


def test_v2_valid_decision_option_selection_is_admitted(tmp_path: Path) -> None:
    _seal_v2(tmp_path)
    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_progress(selections={"choice:x": "option:x1"}),
    )
    assert updated.progress.selections == {"choice:x": "option:x1"}
    assert updated.progress.current_beat_id == "beat:one"


def test_v2_foreign_option_is_rejected(tmp_path: Path) -> None:
    _seal_v2(tmp_path)
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_v2_progress(selections={"choice:x": "option:ghost"}),
        )
    assert exc_info.value.status_code == 422


def test_v2_note_anchors_are_admitted(tmp_path: Path) -> None:
    _seal_v2(tmp_path)
    updated = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_progress(
            notes_by_element_id={
                "beat:one": "Beat note",
                "scene:a": "Scene note",
                "choice:x": "Decision note",
                "option:x1": "Option note",
            }
        ),
    )
    assert updated.progress.notes_by_element_id["beat:one"] == "Beat note"
    assert updated.progress.notes_by_element_id["option:x1"] == "Option note"


def test_v2_malformed_unknown_manifest_fails_closed(tmp_path: Path, application_state_dsn: str) -> None:
    _seal_v2(tmp_path, name="v2-malformed")
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        conn.execute(
            "UPDATE play.run_manifest SET manifest = manifest || %(patch)s::jsonb WHERE run_id = %(run_id)s",
            {
                "patch": '{"schema_version": "dmb_play_run_reference_manifest_v9"}',
                "run_id": RUN_ID_A,
            },
        )
    with pytest.raises(PlayRunRegistryError) as exc_info:
        get_play_run(tmp_path, RUN_ID_A)
    assert exc_info.value.status_code == 500


def test_v2_ready_run_rejects_empty_progress_clear(tmp_path: Path) -> None:
    _seal_v2(tmp_path, name="v2-empty-clear")
    seeded = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_progress(),
    )
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=seeded.run_revision,
            progress=empty_play_run_progress(),
        )
    assert exc_info.value.status_code == 422
    assert "cannot be cleared once READY" in str(exc_info.value)
    preserved = get_play_run(tmp_path, RUN_ID_A)
    assert preserved.run_revision == seeded.run_revision
    assert preserved.progress.current_beat_id == "beat:one"
