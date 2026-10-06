from __future__ import annotations

from pathlib import Path
from threading import Event, Thread, current_thread
from time import monotonic, sleep
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from application_state.content.service import commit_runbook, create_world_runbook
from application_state.errors import ApplicationStateError
from application_state.play.service import (
    create_world_play_run,
    get_world_play_active_run,
    get_world_play_run_aggregate,
    set_world_play_active_run,
)
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


def _create_world_run(*, world_id: str, run_id: str):
    created = create_world_runbook(title=f"Active Run {world_id}", world_id=world_id)
    work_object, revision = commit_runbook(
        str(created.work_object_id),
        "<!-- dmb-playable-element:v2 kind=beat id=beat:opening -->\n## Opening\n",
        expected_revision=created.object_revision,
    )
    return create_world_play_run(
        world_id=world_id,
        run_id=run_id,
        playable_artifact_id=work_object.work_object_id,
        expected_playable_revision=revision.revision_n,
        expected_playable_content_sha256=revision.content_sha256,
    )


def test_world_selection_resumes_and_projects_empty_without_mutation(
    application_state_dsn: str, tmp_path: Path
) -> None:
    world_a = f"world-a-{uuid4()}"
    world_b = f"world-b-{uuid4()}"
    world_run = _create_world_run(world_id=world_a, run_id=RUN_ID_A)
    _create_world_run(world_id=world_b, run_id=RUN_ID_B)

    assert set_world_play_active_run(world_a, RUN_ID_A).run_id == world_run.run.run_id
    selected = set_world_play_active_run(world_a, RUN_ID_A)
    assert selected == set_world_play_active_run(world_a, RUN_ID_A)
    assert get_world_play_active_run(world_id=world_a) == selected

    before = fetch_play_active_run_row(application_state_dsn)
    assert get_world_play_active_run(world_id=world_b) is None
    assert get_play_active_run(tmp_path).run_id is None
    assert fetch_play_active_run_row(application_state_dsn) == before

    with pytest.raises(ApplicationStateError) as wrong_owner:
        set_world_play_active_run(world_b, RUN_ID_A)
    assert wrong_owner.value.status_code == 404
    assert fetch_play_active_run_row(application_state_dsn) == before
    assert get_world_play_active_run(world_id=world_a) == selected


def test_concurrent_same_world_selection_waits_for_first_commit_and_is_idempotent(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import application_state.play.service as play_service

    world_id = f"world-same-run-race-{uuid4()}"
    _create_world_run(world_id=world_id, run_id=RUN_ID_A)

    first_upsert_complete = Event()
    release_first = Event()
    second_lock_attempted = Event()
    second_lock_acquired = Event()
    second_pid: list[int] = []
    upsert_callers: list[str] = []
    results: dict[str, object] = {}
    errors: list[BaseException] = []
    original_lock_run = play_service.repo.lock_run
    original_upsert_active_run = play_service.repo.upsert_active_run

    def observe_run_lock(conn, run_id):
        if current_thread().name == "same-run-selection-second":
            second_pid.append(conn.execute("SELECT pg_backend_pid()").fetchone()[0])
            second_lock_attempted.set()
            row = original_lock_run(conn, run_id)
            second_lock_acquired.set()
            return row
        return original_lock_run(conn, run_id)

    def hold_first_transaction(conn, *, run_id, selected_at):
        upsert_callers.append(current_thread().name)
        row = original_upsert_active_run(conn, run_id=run_id, selected_at=selected_at)
        if current_thread().name == "same-run-selection-first":
            first_upsert_complete.set()
            if not release_first.wait(timeout=10):
                raise TimeoutError("test did not release the first selection transaction")
        return row

    monkeypatch.setattr(play_service.repo, "lock_run", observe_run_lock)
    monkeypatch.setattr(play_service.repo, "upsert_active_run", hold_first_transaction)

    def select(name: str) -> None:
        try:
            results[name] = set_world_play_active_run(world_id, RUN_ID_A)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    first = Thread(target=select, args=("first",), name="same-run-selection-first")
    second = Thread(target=select, args=("second",), name="same-run-selection-second")
    first.start()
    second_started = False
    observed_lock_wait = False
    try:
        assert first_upsert_complete.wait(timeout=5)
        second.start()
        second_started = True
        assert second_lock_attempted.wait(timeout=5)
        deadline = monotonic() + 5
        with psycopg.connect(application_state_dsn, autocommit=True) as observer:
            while monotonic() < deadline:
                row = observer.execute(
                    "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s",
                    (second_pid[0],),
                ).fetchone()
                if row is not None and row[0] == "Lock":
                    observed_lock_wait = True
                    break
                sleep(0.01)
        assert observed_lock_wait, "second selector never waited on PostgreSQL's Run lock"
        assert not second_lock_acquired.is_set()
    finally:
        release_first.set()
        first.join(timeout=10)
        if second_started:
            second.join(timeout=10)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert second_lock_acquired.is_set()
    assert upsert_callers == ["same-run-selection-first"]
    assert results["first"] == results["second"]
    persisted = fetch_play_active_run_row(application_state_dsn)
    assert persisted is not None
    assert persisted["run_id"] == RUN_ID_A
    assert persisted["selected_at"] == getattr(results["first"], "selected_at")


def test_campaign_active_run_remains_legacy_and_world_projection_is_empty(
    application_state_dsn: str, tmp_path: Path
) -> None:
    snapshot = create_committed_runbook(tmp_path, name="active-campaign-control")
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    selected = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    assert get_play_active_run(tmp_path) == selected
    assert get_world_play_active_run(world_id="unrelated-world") is None

    world_id = f"world-v2-{uuid4()}"
    _create_world_run(world_id=world_id, run_id=RUN_ID_B)
    set_world_play_active_run(world_id, RUN_ID_B)
    assert get_play_active_run(tmp_path).run_id is None
    assert fetch_play_active_run_row(application_state_dsn)["run_id"] == RUN_ID_B


def test_corrupt_world_aggregate_cannot_be_selected_or_healed(
    application_state_dsn: str,
) -> None:
    from tests.application_state.play_runtime_helpers import (
        corrupt_play_run_manifest_document,
        unknown_schema_manifest,
    )

    world_id = f"world-corrupt-{uuid4()}"
    _create_world_run(world_id=world_id, run_id=RUN_ID_A)
    set_world_play_active_run(world_id, RUN_ID_A)
    manifest = get_world_play_run_aggregate(
        RUN_ID_A, world_id=world_id
    ).manifest.manifest
    corrupt_play_run_manifest_document(
        application_state_dsn,
        RUN_ID_A,
        unknown_schema_manifest(manifest),
    )
    before = fetch_play_active_run_row(application_state_dsn)
    with pytest.raises(ApplicationStateError) as corrupt:
        set_world_play_active_run(world_id, RUN_ID_A)
    assert corrupt.value.status_code == 500
    assert fetch_play_active_run_row(application_state_dsn) == before
    with pytest.raises(ApplicationStateError) as read_corrupt:
        get_world_play_active_run(world_id=world_id)
    assert read_corrupt.value.status_code == 500


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
