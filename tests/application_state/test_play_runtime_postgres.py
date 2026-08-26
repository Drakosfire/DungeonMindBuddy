from __future__ import annotations

from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest

from apps.live_control_server.services.play_run_rebase import rebase_or_replay_play_run
from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    PlayRunRegistryError,
    create_or_replay_play_run,
    derive_v2_opening_beat_id,
    empty_play_run_progress,
    ensure_v2_native_ready,
    get_play_run,
    list_play_runs,
    replace_play_run_progress,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    get_play_run_reference_manifest,
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
    V2_SOURCE_MARKDOWN,
    commit_runbook_markdown,
    corrupt_play_run_manifest_document,
    corrupt_play_run_progress,
    count_play_rows,
    create_committed_runbook,
    create_run,
    empty_progress,
    fetch_play_runtime_state,
    gate_progress,
    hidden_legacy_runtime_dirs,
    leftover_manifest_path,
    leftover_run_path,
    measure_file_backed_baseline_latency,
    measure_ms,
    playable_of,
    unknown_schema_manifest,
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
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()
    assert not leftover_manifest_path(tmp_path, RUN_ID_A).exists()
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
    assert not leftover_run_path(tmp_path, RUN_ID_A).exists()


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


def test_get_and_list_reject_corrupt_persisted_progress(
    tmp_path: Path, application_state_dsn: str
) -> None:
    create_run(tmp_path, create_committed_runbook(tmp_path))
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=gate_progress(),
    )
    cases = [
        gate_progress().model_dump(mode="json") | {"current_scene_id": "scene:ghost"},
        gate_progress().model_dump(mode="json")
        | {"resolved_beat_ids": ["beat:briefing", "beat:arrival"]},
        gate_progress().model_dump(mode="json")
        | {"resolved_beat_ids": ["beat:arrival", "beat:arrival"]},
    ]
    for progress in cases:
        corrupt_play_run_progress(application_state_dsn, RUN_ID_A, progress)
        with pytest.raises(PlayRunRegistryError) as get_exc:
            get_play_run(tmp_path, RUN_ID_A)
        assert get_exc.value.status_code == 500
        with pytest.raises(PlayRunRegistryError) as list_exc:
            list_play_runs(tmp_path)
        assert list_exc.value.status_code == 500


def test_progress_write_does_not_repair_corrupt_stored_progress(
    tmp_path: Path, application_state_dsn: str
) -> None:
    create_run(tmp_path, create_committed_runbook(tmp_path))
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=gate_progress(),
    )
    cases = [
        gate_progress().model_dump(mode="json") | {"current_scene_id": "scene:ghost"},
        gate_progress().model_dump(mode="json")
        | {"resolved_beat_ids": ["beat:briefing", "beat:arrival"]},
        gate_progress().model_dump(mode="json")
        | {"resolved_beat_ids": ["beat:arrival", "beat:arrival"]},
    ]
    for progress in cases:
        corrupt_play_run_progress(application_state_dsn, RUN_ID_A, progress)
        before = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)
        with pytest.raises(PlayRunRegistryError) as exc_info:
            replace_play_run_progress(
                tmp_path,
                run_id=RUN_ID_A,
                expected_run_revision=before["run"]["run_revision"],
                progress=gate_progress(),
            )
        assert exc_info.value.status_code == 500
        assert fetch_play_runtime_state(application_state_dsn, RUN_ID_A) == before


def test_create_replay_rejects_corrupt_stored_manifest(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, name="corrupt-manifest-create")
    created = create_run(tmp_path, snapshot)
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    cases = [
        {},
        unknown_schema_manifest(manifest.model_dump(mode="json", exclude_none=True)),
    ]
    for document in cases:
        corrupt_play_run_manifest_document(application_state_dsn, RUN_ID_A, document)
        before = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)
        with pytest.raises(PlayRunRegistryError) as create_exc:
            create_run(tmp_path, snapshot)
        assert create_exc.value.status_code == 500
        with pytest.raises(PlayRunRegistryError) as get_exc:
            get_play_run(tmp_path, RUN_ID_A)
        assert get_exc.value.status_code == 500
        with pytest.raises(PlayRunRegistryError) as list_exc:
            list_play_runs(tmp_path)
        assert list_exc.value.status_code == 500
        with pytest.raises(PlayRunReferenceManifestError) as manifest_exc:
            get_play_run_reference_manifest(tmp_path, RUN_ID_A)
        assert manifest_exc.value.status_code == 500
        leftover = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)
        assert leftover == before
        assert leftover["run"]["run_revision"] == created.run_revision
        assert leftover["run"]["progress"] == empty_progress().model_dump(mode="json")
        assert leftover["manifest"]["manifest"] == document


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
    baseline = measure_file_backed_baseline_latency()
    print(
        "AS3 latency hypothesis capture "
        f"baseline_file_b4d63daa "
        f"start_plus_seal_p50_ms={baseline['start_plus_seal_p50_ms']:.1f} "
        f"start_plus_seal_p95_ms={baseline['start_plus_seal_p95_ms']:.1f} "
        f"cas_p50_ms={baseline['cas_p50_ms']:.1f} "
        f"cas_p95_ms={baseline['cas_p95_ms']:.1f} "
        "postgres_head "
        f"start_plus_seal_p50_ms={start_p50:.1f} "
        f"start_plus_seal_p95_ms={start_p95:.1f} "
        f"start_plus_seal_max_ms={start_max:.1f} "
        f"cas_p50_ms={cas_p50:.1f} "
        f"cas_p95_ms={cas_p95:.1f} "
        f"cas_max_ms={cas_max:.1f} "
        "hypotheses start_plus_seal_p95_ms=250 cas_p95_ms=50"
    )
    assert baseline["start_plus_seal_p50_ms"] >= 0
    assert baseline["cas_p50_ms"] >= 0


BF2_SPINE_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:z-opening beat_kind=spine -->",
        "## Opening",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:a-later beat_kind=spine -->",
        "## Later",
        "",
    ]
)

BF2_NO_SPINE_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:optional-first beat_kind=optional -->",
        "## Optional first",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:interrupt-second beat_kind=interrupt -->",
        "## Interrupt",
        "",
    ]
)


def _v2_seed_progress(beat_id: str) -> PlayRunProgress:
    return PlayRunProgress(
        current_beat_id=beat_id,
        current_scene_id=None,
        resolved_beat_ids=[],
        selections={},
        notes_by_element_id={},
    )


def test_v2_empty_progress_seed_persists_first_spine_from_document_order(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-spine", markdown=BF2_SPINE_MARKDOWN
    )
    record = create_run(tmp_path, snapshot)
    assert record.progress == empty_progress()
    opening = derive_v2_opening_beat_id(snapshot.markdown)
    assert opening == "beat:z-opening"
    seeded = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_seed_progress(opening),
    )
    assert seeded.progress.current_beat_id == "beat:z-opening"
    assert seeded.progress.current_scene_id is None
    reloaded = get_play_run(tmp_path, RUN_ID_A)
    assert reloaded.progress.current_beat_id == "beat:z-opening"
    assert reloaded.run_revision == 2
    assert count_play_rows(application_state_dsn) == (1, 1)


def test_v2_no_spine_seeds_first_beat(tmp_path: Path) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-no-spine", markdown=BF2_NO_SPINE_MARKDOWN
    )
    create_run(tmp_path, snapshot)
    opening = derive_v2_opening_beat_id(snapshot.markdown)
    assert opening == "beat:optional-first"
    seeded = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_seed_progress(opening),
    )
    assert seeded.progress.current_beat_id == "beat:optional-first"


def test_v2_zero_beat_markdown_has_no_opening_seed() -> None:
    assert derive_v2_opening_beat_id("# no playable beats\n") is None
    assert derive_v2_opening_beat_id(V2_SOURCE_MARKDOWN) == "beat:arrival"


def test_v2_historical_revision_remains_authority_after_newer_commit(
    tmp_path: Path,
) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-historical", markdown=BF2_SPINE_MARKDOWN
    )
    created = create_run(tmp_path, snapshot)
    opening = derive_v2_opening_beat_id(snapshot.markdown)
    seeded = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_seed_progress(opening),
    )
    commit_runbook_markdown(
        tmp_path,
        snapshot.record.document_id,
        BF2_SPINE_MARKDOWN + "\n<!-- dmb-playable-element:v2 kind=beat id=beat:newer beat_kind=spine -->\n## Newer\n",
        snapshot.loaded_revision,
    )
    reopened = get_play_run(tmp_path, RUN_ID_A)
    assert reopened.playable_revision == created.playable_revision
    assert reopened.playable_content_sha256 == created.playable_content_sha256
    assert reopened.progress.current_beat_id == "beat:z-opening"
    assert reopened.run_revision == seeded.run_revision


def test_v2_stale_cas_cannot_overwrite_newer_position(tmp_path: Path) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-stale", markdown=BF2_SPINE_MARKDOWN
    )
    create_run(tmp_path, snapshot)
    first = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=_v2_seed_progress("beat:z-opening"),
    )
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            progress=_v2_seed_progress("beat:a-later"),
        )
    assert exc_info.value.status_code == 409
    assert get_play_run(tmp_path, RUN_ID_A) == first


def test_v2_equivalent_first_seeds_converge(tmp_path: Path) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-converge", markdown=BF2_SPINE_MARKDOWN
    )
    create_run(tmp_path, snapshot)
    progress = _v2_seed_progress("beat:z-opening")
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            replace_play_run_progress(
                tmp_path,
                run_id=RUN_ID_A,
                expected_run_revision=1,
                progress=progress,
            )
        except PlayRunRegistryError as exc:
            errors.append(exc)

    threads = [Thread(target=worker), Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    final = get_play_run(tmp_path, RUN_ID_A)
    assert final.progress.current_beat_id == "beat:z-opening"
    assert final.progress.current_scene_id is None
    assert final.run_revision == 2
    for exc in errors:
        assert exc.status_code == 409


def test_v2_reread_preserves_exact_current_beat_and_scene(tmp_path: Path) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-reread", markdown=V2_SOURCE_MARKDOWN
    )
    create_run(tmp_path, snapshot)
    persisted = replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=1,
        progress=PlayRunProgress(
            current_beat_id="beat:arrival",
            current_scene_id="scene:gate",
            resolved_beat_ids=[],
            selections={},
            notes_by_element_id={},
        ),
    )
    reloaded = get_play_run(tmp_path, RUN_ID_A)
    assert reloaded.progress.current_beat_id == "beat:arrival"
    assert reloaded.progress.current_scene_id == "scene:gate"
    assert reloaded.run_revision == persisted.run_revision


BF2_FENCED_MARKDOWN = "\n".join(
    [
        "```",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:fenced-first beat_kind=spine -->",
        "## Fenced",
        "```",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:z-opening beat_kind=spine -->",
        "## Opening",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:a-later beat_kind=optional -->",
        "## Later",
        "",
    ]
)


def test_v2_opening_beat_ignores_fenced_markers(tmp_path: Path) -> None:
    assert derive_v2_opening_beat_id(BF2_FENCED_MARKDOWN) == "beat:z-opening"
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-fenced", markdown=BF2_FENCED_MARKDOWN
    )
    create_run(tmp_path, snapshot)
    seeded = ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert seeded.progress.current_beat_id == "beat:z-opening"
    assert seeded.progress.current_scene_id is None


def test_v2_native_first_admission_seeds_after_pinned_preflight(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-owning-seed", markdown=BF2_SPINE_MARKDOWN
    )
    record = create_run(tmp_path, snapshot)
    assert record.progress == empty_progress()
    seeded = ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert seeded.progress.current_beat_id == "beat:z-opening"
    assert seeded.progress.current_scene_id is None
    replayed = ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert replayed.run_revision == seeded.run_revision
    assert replayed.progress.current_beat_id == "beat:z-opening"
    with pytest.raises(PlayRunRegistryError) as exc_info:
        replace_play_run_progress(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=seeded.run_revision,
            progress=empty_play_run_progress(),
        )
    assert exc_info.value.status_code == 422
    preserved = get_play_run(tmp_path, RUN_ID_A)
    assert preserved.run_revision == seeded.run_revision
    assert preserved.progress.current_beat_id == "beat:z-opening"
    assert count_play_rows(application_state_dsn) == (1, 1)


def test_v2_native_first_admission_does_not_seed_corrupted_sealed_edges(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(
        tmp_path, name="bf2-corrupt-kind", markdown=BF2_SPINE_MARKDOWN
    )
    create_run(tmp_path, snapshot)
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    payload = manifest.model_dump(mode="json")
    first = payload["beats"][0]
    first["beat_kind"] = "optional" if first.get("beat_kind") == "spine" else "spine"
    payload["beats"][0] = first
    corrupt_play_run_manifest_document(application_state_dsn, RUN_ID_A, payload)
    with pytest.raises(PlayRunRegistryError) as exc_info:
        ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert "Beat kind" in str(exc_info.value)
    assert get_play_run(tmp_path, RUN_ID_A).progress == empty_progress()
