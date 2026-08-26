from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.services.play_active_run import (
    get_play_active_run,
    play_active_run_path,
    set_play_active_run,
)
from apps.live_control_server.services.play_run_rebase import (
    PlayRunRebaseIntent,
    play_run_rebase_intent_path,
)
from apps.live_control_server.services.play_run_registry import (
    get_play_run,
    play_run_path,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    derive_sealed_manifest,
    get_play_run_reference_manifest,
    play_run_reference_manifest_path,
)
from apps.live_control_server.services.registry_file_lock import registry_token
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from application_state.play.import_runtime import import_play_runtime_from_legacy_files
from src.live_play.live_store import write_json
from tests.application_state.play_runtime_helpers import (
    RUN_ID_A,
    SOURCE_MARKDOWN,
    SURVIVING_TARGET_MARKDOWN,
    commit_runbook_markdown,
    count_play_rows,
    create_committed_runbook,
    gate_progress,
    playable_of,
    write_legacy_run_and_manifest,
)


def test_legacy_pair_imports_exactly_and_second_pass_is_noop(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    write_legacy_run_and_manifest(
        tmp_path,
        run_id=RUN_ID_A,
        snapshot=snapshot,
        run_revision=4,
        progress=gate_progress(),
    )
    report = import_play_runtime_from_legacy_files(tmp_path)
    assert report.imported == 1
    assert report.noop == 0
    replay = import_play_runtime_from_legacy_files(tmp_path)
    assert replay.imported == 0
    assert replay.noop == 1
    loaded = get_play_run(tmp_path, RUN_ID_A)
    assert loaded.run_revision == 4
    assert loaded.progress.selections == {"choice:route": "option:fire"}
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert manifest.playable_revision == loaded.playable_revision
    assert count_play_rows(application_state_dsn) == (1, 1)


def test_import_conflict_fails_closed(tmp_path: Path, application_state_dsn: str) -> None:
    snapshot = create_committed_runbook(tmp_path)
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot, run_revision=2)
    import_play_runtime_from_legacy_files(tmp_path)
    write_legacy_run_and_manifest(
        tmp_path,
        run_id=RUN_ID_A,
        snapshot=snapshot,
        run_revision=3,
        progress=gate_progress(),
    )
    with pytest.raises(ApplicationStateConflictError):
        import_play_runtime_from_legacy_files(tmp_path)
    assert get_play_run(tmp_path, RUN_ID_A).run_revision == 2


def test_missing_sidecar_stops_import(tmp_path: Path, application_state_dsn: str) -> None:
    snapshot = create_committed_runbook(tmp_path, name="missing-sidecar")
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot)
    play_run_reference_manifest_path(tmp_path, RUN_ID_A).unlink()
    with pytest.raises(ApplicationStateIntegrityError, match="missing its sealed manifest"):
        import_play_runtime_from_legacy_files(tmp_path)
    assert count_play_rows(application_state_dsn) == (0, 0)


def test_pending_intent_is_recovered_before_capture(
    tmp_path: Path, application_state_dsn: str
) -> None:
    source = create_committed_runbook(tmp_path, markdown=SOURCE_MARKDOWN)
    source_revision, source_sha = playable_of(source)
    write_legacy_run_and_manifest(
        tmp_path,
        run_id=RUN_ID_A,
        snapshot=source,
        playable_revision=source_revision,
        playable_content_sha256=source_sha,
        markdown=SOURCE_MARKDOWN,
    )
    commit_runbook_markdown(
        tmp_path,
        source.record.document_id,
        SURVIVING_TARGET_MARKDOWN,
        source.loaded_revision,
    )
    from apps.live_control_server.services.play_run_registry import PlayRunRecord
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )

    target_snapshot = get_workspace_document_snapshot(tmp_path, source.record.document_id)
    target_revision, target_sha = playable_of(target_snapshot)
    run_path = play_run_path(tmp_path, RUN_ID_A)
    manifest_path = play_run_reference_manifest_path(tmp_path, RUN_ID_A)
    source_record = PlayRunRecord.model_validate(json.loads(run_path.read_text(encoding="utf-8")))
    target_run = source_record.model_copy(
        update={
            "playable_revision": target_revision,
            "playable_content_sha256": target_sha,
            "run_revision": source_record.run_revision + 1,
            "updated_at": "2026-01-02T00:00:00Z",
            "rebased_from_run_revision": source_record.run_revision,
        }
    )
    target_manifest = derive_sealed_manifest(
        SURVIVING_TARGET_MARKDOWN,
        run_id=RUN_ID_A,
        playable_artifact_id=source.record.document_id,
        playable_revision=target_revision,
        playable_content_sha256=target_sha,
        sealed_at="2026-01-02T00:00:00Z",
    )
    intent = PlayRunRebaseIntent(
        run_id=RUN_ID_A,
        expected_source_run_revision=source_record.run_revision,
        source_playable_artifact_id=source.record.document_id,
        source_playable_revision=source_revision,
        source_playable_content_sha256=source_sha,
        source_run_token=registry_token(run_path),
        source_manifest_token=registry_token(manifest_path),
        target_run=target_run,
        target_manifest=target_manifest,
        prepared_at="2026-01-02T00:00:00Z",
    )
    intent_path = play_run_rebase_intent_path(tmp_path, RUN_ID_A)
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(intent_path, intent.model_dump(mode="json"))
    report = import_play_runtime_from_legacy_files(tmp_path)
    assert report.recovered_intents == 1
    assert report.imported == 1
    loaded = get_play_run(tmp_path, RUN_ID_A)
    assert loaded.playable_revision == target_revision
    assert loaded.playable_content_sha256 == target_sha
    assert loaded.run_revision == 2
    assert not intent_path.exists()


def test_active_run_pointer_stays_file_backed_after_import(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, name="active-pointer")
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot)
    import_play_runtime_from_legacy_files(tmp_path)
    selected = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    assert selected.run_id == RUN_ID_A
    assert play_active_run_path(tmp_path).is_file()
    pointer = get_play_active_run(tmp_path)
    assert pointer.run_id == RUN_ID_A
    assert get_play_run(tmp_path, RUN_ID_A).run_id == RUN_ID_A
    assert get_play_run_reference_manifest(tmp_path, RUN_ID_A).run_id == RUN_ID_A
    assert play_active_run_path(tmp_path).is_file()
