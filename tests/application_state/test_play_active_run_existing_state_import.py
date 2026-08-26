from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.play_active_run import (
    get_play_active_run,
    load_legacy_play_active_run_file,
    play_active_run_path,
    set_play_active_run,
)
from apps.live_control_server.services.play_run_registry import get_play_run
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from application_state.play.import_active_run import import_play_active_run_from_legacy_file
from application_state.play.import_runtime import import_play_runtime_from_legacy_files
from tests.application_state.play_runtime_helpers import (
    RUN_ID_A,
    RUN_ID_B,
    count_active_run_rows,
    create_committed_runbook,
    create_run,
    fetch_play_active_run_row,
    write_legacy_active_run_pointer,
    write_legacy_run_and_manifest,
)

SELECTED_AT = "2026-01-01T00:00:00Z"


def test_legacy_pointer_imports_exactly_and_replay_is_noop(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot)
    write_legacy_active_run_pointer(tmp_path, run_id=RUN_ID_A, selected_at=SELECTED_AT)
    import_play_runtime_from_legacy_files(tmp_path)

    report = import_play_active_run_from_legacy_file(tmp_path)
    assert report.imported == 1
    assert report.noop == 0
    loaded = get_play_active_run(tmp_path)
    assert loaded.run_id == RUN_ID_A
    assert loaded.selected_at == SELECTED_AT
    assert get_play_run(tmp_path, RUN_ID_A).run_id == RUN_ID_A
    replay = import_play_active_run_from_legacy_file(tmp_path)
    assert replay.imported == 0
    assert replay.noop == 1
    assert get_play_active_run(tmp_path) == loaded
    assert count_active_run_rows(application_state_dsn) == 1


def test_absent_or_null_pointer_imports_no_row(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot)
    import_play_runtime_from_legacy_files(tmp_path)

    missing = import_play_active_run_from_legacy_file(tmp_path)
    assert missing.imported == 0
    assert missing.noop == 1
    assert get_play_active_run(tmp_path).run_id is None
    assert count_active_run_rows(application_state_dsn) == 0

    write_legacy_active_run_pointer(tmp_path, run_id=RUN_ID_A, selected_at=SELECTED_AT)
    path = play_active_run_path(tmp_path)
    path.write_text(
        '{"schema_version":"dmb_play_active_run_v1","run_id":null,"selected_at":null}\n'
    )
    null_report = import_play_active_run_from_legacy_file(tmp_path)
    assert null_report.noop == 1
    assert count_active_run_rows(application_state_dsn) == 0


def test_malformed_pointer_does_not_write(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot)
    import_play_runtime_from_legacy_files(tmp_path)
    path = play_active_run_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"schema_version":"dmb_play_active_run_v1","run_id":"broken"}\n')

    with pytest.raises(ApplicationStateIntegrityError, match="malformed persisted"):
        import_play_active_run_from_legacy_file(tmp_path)
    assert count_active_run_rows(application_state_dsn) == 0
    assert get_play_active_run(tmp_path).run_id is None


def test_missing_referenced_run_fails_without_write(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot)
    import_play_runtime_from_legacy_files(tmp_path)
    write_legacy_active_run_pointer(tmp_path, run_id=RUN_ID_B, selected_at=SELECTED_AT)

    with pytest.raises(ApplicationStateIntegrityError, match="missing Play Run"):
        import_play_active_run_from_legacy_file(tmp_path)
    assert count_active_run_rows(application_state_dsn) == 0


def test_conflicting_db_selection_is_not_overwritten(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    write_legacy_run_and_manifest(tmp_path, run_id=RUN_ID_A, snapshot=snapshot)
    write_legacy_run_and_manifest(
        tmp_path,
        run_id=RUN_ID_B,
        snapshot=create_committed_runbook(tmp_path, name="other"),
    )
    import_play_runtime_from_legacy_files(tmp_path)
    first = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    write_legacy_active_run_pointer(tmp_path, run_id=RUN_ID_B, selected_at=SELECTED_AT)

    with pytest.raises(ApplicationStateConflictError, match="conflicts with the stored"):
        import_play_active_run_from_legacy_file(tmp_path)
    assert get_play_active_run(tmp_path) == first
    assert fetch_play_active_run_row(application_state_dsn)["run_id"] == RUN_ID_A


def test_conflicting_timestamp_is_not_overwritten(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot)
    first = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    write_legacy_active_run_pointer(tmp_path, run_id=RUN_ID_A, selected_at=SELECTED_AT)

    with pytest.raises(ApplicationStateConflictError, match="conflicts with the stored"):
        import_play_active_run_from_legacy_file(tmp_path)
    assert get_play_active_run(tmp_path) == first
    assert load_legacy_play_active_run_file(tmp_path).selected_at == SELECTED_AT
