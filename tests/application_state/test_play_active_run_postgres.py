from __future__ import annotations

from pathlib import Path
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_active_run import (
    PlayActiveRunError,
    clear_play_active_run,
    get_play_active_run,
    set_play_active_run,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunRegistryError,
    get_play_run,
    replace_play_run_progress,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    get_play_run_reference_manifest,
)
from apps.live_control_server.services.workspace_document_registry import (
    get_committed_playable_revision,
)
from tests.application_state.play_runtime_helpers import (
    RUN_ID_A,
    RUN_ID_B,
    corrupt_play_run_manifest_document,
    corrupt_play_run_progress,
    count_active_run_rows,
    create_committed_runbook,
    create_run,
    fetch_play_active_run_row,
    gate_progress,
    leftover_active_run_path,
    measure_file_backed_active_run_latency,
    measure_ms,
    unknown_schema_manifest,
    unreadable_path,
    write_legacy_active_run_pointer,
)


def test_missing_row_is_public_null_and_set_is_idempotent(
    tmp_path: Path, application_state_dsn: str
) -> None:
    empty = get_play_active_run(tmp_path)
    assert empty.run_id is None
    assert empty.selected_at is None
    assert count_active_run_rows(application_state_dsn) == 0

    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot)
    first = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    second = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    assert first.run_id == RUN_ID_A
    assert second == first
    assert fetch_play_active_run_row(application_state_dsn)["run_id"] == RUN_ID_A
    assert not leftover_active_run_path(tmp_path).exists()


def test_clear_removes_row_and_failed_set_does_not_clear(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    create_run(tmp_path, create_committed_runbook(tmp_path, name="other"), run_id=RUN_ID_B)
    first = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    with pytest.raises(PlayActiveRunError) as missing:
        set_play_active_run(tmp_path, run_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    assert missing.value.status_code == 404
    assert get_play_active_run(tmp_path) == first
    cleared = clear_play_active_run(tmp_path)
    assert cleared.run_id is None
    assert count_active_run_rows(application_state_dsn) == 0


def test_corrupt_aggregate_does_not_mutate_pointer(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    create_run(tmp_path, create_committed_runbook(tmp_path, name="second"), run_id=RUN_ID_B)
    selected = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    before = fetch_play_active_run_row(application_state_dsn)
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_B)

    corrupt_play_run_progress(
        application_state_dsn,
        RUN_ID_B,
        gate_progress().model_dump(mode="json") | {"current_scene_id": "scene:ghost"},
    )
    with pytest.raises(PlayActiveRunError) as progress_exc:
        set_play_active_run(tmp_path, run_id=RUN_ID_B)
    assert progress_exc.value.status_code == 500
    assert fetch_play_active_run_row(application_state_dsn) == before
    assert get_play_active_run(tmp_path) == selected

    corrupt_play_run_manifest_document(
        application_state_dsn,
        RUN_ID_B,
        unknown_schema_manifest(manifest.model_dump(mode="json", exclude_none=True)),
    )
    with pytest.raises(PlayActiveRunError) as manifest_exc:
        set_play_active_run(tmp_path, run_id=RUN_ID_B)
    assert manifest_exc.value.status_code == 500
    assert fetch_play_active_run_row(application_state_dsn) == before


def test_legacy_file_absent_unreadable_or_contradictory_is_ignored(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    create_run(tmp_path, create_committed_runbook(tmp_path, name="other"), run_id=RUN_ID_B)
    selected = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    assert not leftover_active_run_path(tmp_path).exists()
    assert get_play_active_run(tmp_path) == selected

    other_root = tmp_path / "other-checkout"
    other_root.mkdir()
    assert get_play_active_run(other_root) == selected
    assert not leftover_active_run_path(other_root).exists()

    write_legacy_active_run_pointer(
        tmp_path, run_id=RUN_ID_B, selected_at="2026-01-01T00:00:00Z"
    )
    assert get_play_active_run(tmp_path) == selected
    replaced = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    assert replaced == selected
    assert leftover_active_run_path(tmp_path).read_text()

    with unreadable_path(leftover_active_run_path(tmp_path)):
        assert get_play_active_run(tmp_path).run_id == RUN_ID_A
        assert set_play_active_run(tmp_path, run_id=RUN_ID_A) == selected


def test_new_app_instance_and_different_root_resume_exact_current_moment(
    tmp_path: Path, application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    created = create_run(tmp_path, snapshot)
    progressed = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        progress=gate_progress(),
    )
    selected = set_play_active_run(tmp_path, run_id=RUN_ID_A)

    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
    )
    first_client = TestClient(create_app())
    first = first_client.get("/api/live/play-active-run")
    assert first.status_code == 200
    assert first.json()["run_id"] == RUN_ID_A

    other_root = tmp_path / "worktree-b"
    other_root.mkdir()
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: other_root,
    )
    second_client = TestClient(create_app())
    restarted = second_client.get("/api/live/play-active-run")
    assert restarted.status_code == 200
    assert restarted.json() == first.json() == selected.model_dump(mode="json")

    run = get_play_run(other_root, RUN_ID_A)
    manifest = get_play_run_reference_manifest(other_root, RUN_ID_A)
    committed = get_committed_playable_revision(run.playable_artifact_id, kind="runbook")
    assert run.run_revision == progressed.run_revision
    assert run.progress.model_dump(mode="json") == gate_progress().model_dump(mode="json")
    assert run.playable_revision == created.playable_revision
    assert run.playable_content_sha256 == created.playable_content_sha256
    assert committed.revision_n == run.playable_revision
    assert committed.content_sha256 == run.playable_content_sha256
    assert manifest.run_id == RUN_ID_A
    assert not leftover_active_run_path(other_root).exists()


def test_corrupt_selected_run_fails_truthfully_without_fallback(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    create_run(tmp_path, create_committed_runbook(tmp_path, name="other"), run_id=RUN_ID_B)
    selected = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    corrupt_play_run_progress(
        application_state_dsn,
        RUN_ID_A,
        gate_progress().model_dump(mode="json") | {"current_scene_id": "scene:ghost"},
    )
    assert get_play_active_run(tmp_path) == selected
    with pytest.raises(PlayRunRegistryError) as exc_info:
        get_play_run(tmp_path, RUN_ID_A)
    assert exc_info.value.status_code == 500
    assert get_play_active_run(tmp_path).run_id == RUN_ID_A
    assert get_play_run(tmp_path, RUN_ID_B).run_id == RUN_ID_B


def test_last_explicit_selection_wins_without_cas(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    create_run(tmp_path, create_committed_runbook(tmp_path, name="other"), run_id=RUN_ID_B)
    errors: list[BaseException] = []

    def write(run_id: str) -> None:
        try:
            set_play_active_run(tmp_path, run_id=run_id)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        Thread(target=write, args=(RUN_ID_A,)),
        Thread(target=write, args=(RUN_ID_B,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    active = get_play_active_run(tmp_path)
    assert active.run_id in {RUN_ID_A, RUN_ID_B}
    assert count_active_run_rows(application_state_dsn) == 1


def test_active_run_latency_samples(tmp_path: Path, application_state_dsn: str) -> None:
    snapshot = create_committed_runbook(tmp_path, name="latency")
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    create_run(tmp_path, create_committed_runbook(tmp_path, name="latency-b"), run_id=RUN_ID_B)
    set_play_active_run(tmp_path, run_id=RUN_ID_A)

    get_p50, get_p95, _ = measure_ms(lambda: get_play_active_run(tmp_path))

    def switch() -> None:
        current = get_play_active_run(tmp_path)
        target = RUN_ID_B if current.run_id == RUN_ID_A else RUN_ID_A
        set_play_active_run(tmp_path, run_id=target)

    put_p50, put_p95, _ = measure_ms(switch)

    def resume_chain() -> None:
        active = get_play_active_run(tmp_path)
        assert active.run_id is not None
        run = get_play_run(tmp_path, active.run_id)
        manifest = get_play_run_reference_manifest(tmp_path, active.run_id)
        committed = get_committed_playable_revision(run.playable_artifact_id, kind="runbook")
        assert manifest.run_id == run.run_id
        assert committed.revision_n == run.playable_revision

    resume_p50, resume_p95, _ = measure_ms(resume_chain)
    baseline = measure_file_backed_active_run_latency()
    print(
        "AS4 latency file-backed AS3 baseline vs head "
        f"get_p50={baseline['get_p50_ms']:.1f}->{get_p50:.1f} "
        f"get_p95={baseline['get_p95_ms']:.1f}->{get_p95:.1f} "
        f"put_p50={baseline['put_p50_ms']:.1f}->{put_p50:.1f} "
        f"put_p95={baseline['put_p95_ms']:.1f}->{put_p95:.1f} "
        f"resume_p50={resume_p50:.1f} resume_p95={resume_p95:.1f} "
        "(AS3 Runtime CAS ~74ms p95 retained; measurements are not merge gates)"
    )
