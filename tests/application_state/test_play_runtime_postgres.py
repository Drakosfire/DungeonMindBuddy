from __future__ import annotations

from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest

from apps.live_control_server.services.play_run_rebase import rebase_or_replay_play_run
from apps.live_control_server.services.play_run_registry import (
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
from apps.live_control_server.services.workspace_document_registry import (
    get_workspace_document_snapshot,
)
from application_state.errors import ApplicationStateValidationError
from application_state.play.service import create_play_run
from tests.application_state.play_runtime_helpers import (
    INVALID_PLAYABLE_MARKDOWN,
    RUN_ID_A,
    RUN_ID_B,
    SURVIVING_TARGET_MARKDOWN,
    commit_runbook_markdown,
    count_play_rows,
    create_committed_runbook,
    create_run,
    empty_progress,
    gate_progress,
    hidden_legacy_runtime_dirs,
    measure_ms,
    playable_of,
)


def test_create_seals_manifest_atomically_and_writes_no_files(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    record = create_run(tmp_path, snapshot)
    assert record.run_revision == 1
    assert record.playable_artifact_id == snapshot.record.document_id
    assert "markdown" not in record.model_dump_json()
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    replayed = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert replayed == manifest
    assert manifest.playable_revision == record.playable_revision
    assert not play_run_path(tmp_path, RUN_ID_A).exists()
    assert not play_run_reference_manifest_path(tmp_path, RUN_ID_A).exists()
    assert count_play_rows(application_state_dsn) == (1, 1)


def test_manifest_derivation_failure_writes_neither_row(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="invalid-playable", markdown=INVALID_PLAYABLE_MARKDOWN
    )
    with pytest.raises((PlayRunRegistryError, ApplicationStateValidationError)):
        create_run(tmp_path, snapshot)
    assert count_play_rows(application_state_dsn) == (0, 0)
    assert not play_run_path(tmp_path, RUN_ID_A).exists()


def test_forced_manifest_insert_failure_rolls_back_run(
    tmp_path: Path,
    application_state_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = create_committed_runbook(tmp_path, name="forced-rollback")

    def explode(*_args, **_kwargs):
        raise RuntimeError("forced manifest insert failure")

    monkeypatch.setattr("application_state.play.repository.insert_manifest", explode)
    revision_n, sha = playable_of(snapshot)
    with pytest.raises(RuntimeError, match="forced manifest insert failure"):
        create_play_run(
            run_id=RUN_ID_A,
            playable_artifact_id=snapshot.record.document_id,
            expected_playable_revision=revision_n,
            expected_playable_content_sha256=sha,
        )
    assert count_play_rows(application_state_dsn) == (0, 0)


def test_create_replay_and_different_binding_conflict(
    tmp_path: Path, application_state_dsn: str
) -> None:
    first_snapshot = create_committed_runbook(tmp_path, name="binding-a")
    second_snapshot = create_committed_runbook(tmp_path, name="binding-b")
    first = create_run(tmp_path, first_snapshot)
    replayed = create_run(tmp_path, first_snapshot)
    assert replayed == first
    with pytest.raises(PlayRunRegistryError) as exc_info:
        create_run(tmp_path, second_snapshot)
    assert exc_info.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A) == first
    assert count_play_rows(application_state_dsn) == (1, 1)


def test_get_and_list_ignore_absent_legacy_files(
    tmp_path: Path, application_state_dsn: str
) -> None:
    first = create_run(tmp_path, create_committed_runbook(tmp_path, name="list-a"))
    create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_B,
        playable_artifact_id=first.playable_artifact_id,
        expected_playable_revision=first.playable_revision,
        expected_playable_content_sha256=first.playable_content_sha256,
    )
    with hidden_legacy_runtime_dirs(tmp_path):
        loaded = get_play_run(tmp_path, RUN_ID_A)
        listed = list_play_runs(tmp_path)
    assert loaded.run_id == RUN_ID_A
    assert [record.run_id for record in listed] == [RUN_ID_B, RUN_ID_A]


def test_progress_cas_one_winner_exact_retry_and_stale_conflict(
    tmp_path: Path, application_state_dsn: str
) -> None:
    create_run(tmp_path, create_committed_runbook(tmp_path))
    first_progress = gate_progress()
    second_progress = gate_progress().model_copy(
        update={"notes_by_element_id": {"scene:gate": "Other."}}
    )
    results: list[object] = []
    errors: list[PlayRunRegistryError] = []

    def write(progress) -> None:
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
        thread.join(timeout=5.0)
        assert not thread.is_alive()
    assert len(results) == 1
    assert len(errors) == 1
    assert errors[0].status_code == 409
    winner = results[0]
    assert winner.run_revision == 2
    retry = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=winner.progress,
    )
    assert retry == winner
    with pytest.raises(PlayRunRegistryError) as stale:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=empty_progress(),
        )
    assert stale.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A).run_revision == 2


def test_file_absence_progress_and_rebase_still_work(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path)
    create_run(tmp_path, snapshot)
    later = get_play_run(tmp_path, RUN_ID_A)
    commit_runbook_markdown(
        tmp_path,
        snapshot.record.document_id,
        SURVIVING_TARGET_MARKDOWN,
        snapshot.loaded_revision,
    )
    target = playable_of(get_workspace_document_snapshot(tmp_path, snapshot.record.document_id))
    with hidden_legacy_runtime_dirs(tmp_path):
        updated = replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=later.run_revision,
            progress=empty_progress(),
        )
        rebased = rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=updated.run_revision,
            target_playable_revision=target[0],
            target_playable_content_sha256=target[1],
        )
        assert get_play_run(tmp_path, RUN_ID_A).playable_revision == rebased.playable_revision
        assert list_play_runs(tmp_path)[0].run_id == RUN_ID_A


def test_play_runtime_latency_samples(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, name="latency")
    revision_n, sha = playable_of(snapshot)

    def start_and_seal() -> None:
        run_id = str(uuid4())
        create_or_replay_play_run(
            tmp_path,
            run_id=run_id,
            playable_artifact_id=snapshot.record.document_id,
            expected_playable_revision=revision_n,
            expected_playable_content_sha256=sha,
        )
        seal_or_replay_play_run_reference_manifest(tmp_path, run_id)

    start_p50, start_p95, start_max = measure_ms(start_and_seal, samples=30)
    durable = create_run(tmp_path, snapshot, run_id=RUN_ID_A)

    def cas() -> None:
        current = get_play_run(tmp_path, RUN_ID_A)
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=current.run_revision,
            progress=gate_progress().model_copy(
                update={"notes_by_element_id": {"scene:gate": str(uuid4())}}
            ),
        )

    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=durable.run_revision,
        progress=gate_progress(),
    )
    cas_p50, cas_p95, cas_max = measure_ms(cas, samples=30)
    print(
        "AS3 latency hypothesis capture postgres_head "
        f"start_plus_seal_p50_ms={start_p50:.1f} "
        f"start_plus_seal_p95_ms={start_p95:.1f} "
        f"start_plus_seal_max_ms={start_max:.1f} "
        f"cas_p50_ms={cas_p50:.1f} "
        f"cas_p95_ms={cas_p95:.1f} "
        f"cas_max_ms={cas_max:.1f} "
        "hypotheses start_plus_seal_p95_ms=250 cas_p95_ms=50"
    )
