"""AS5 owning-boundary witnesses: Play works without filesystem persistence."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_active_run import (
    PLAY_ACTIVE_RUN_SCHEMA,
    PlayActiveRunError,
    get_play_active_run,
    set_play_active_run,
)
from apps.live_control_server.services.play_run_rebase import (
    PlayRunRebaseError,
    rebase_or_replay_play_run,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunRecord,
    PlayRunRegistryError,
    create_or_replay_play_run,
    get_play_run,
    list_play_runs,
    replace_play_run_progress,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    derive_sealed_manifest,
    get_play_run_reference_manifest,
    seal_or_replay_play_run_reference_manifest,
)
from apps.live_control_server.services.workspace_document_registry import (
    get_committed_playable_revision,
    get_workspace_document_snapshot,
)
from application_state.cli import alembic_config
from application_state.config import APPLICATION_STATE_DSN_ENV
from tests.application_state.play_runtime_helpers import (
    RUN_ID_A,
    RUN_ID_B,
    SURVIVING_TARGET_MARKDOWN,
    commit_runbook_markdown,
    count_active_run_rows,
    count_play_rows,
    create_committed_runbook,
    create_run,
    fetch_play_active_run_row,
    fetch_play_runtime_state,
    gate_progress,
    playable_of,
)

AS4_PREDECESSOR_SHA = "993f837b6f2fc601acf2ae3a4b7926af1858ac6c"
LEGACY_PLAY_REL = Path("out/runtime/play")
CREATED_AT = "2026-01-15T12:00:00Z"
SELECTED_AT = "2026-01-15T12:34:56Z"
DOWN_DSN = "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:1/dungeonbuddy_app_state_down"

_PREDECESSOR_IMPORT_SCRIPT = r"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from application_state.play.import_active_run import import_play_active_run_from_legacy_file
from application_state.play.import_runtime import import_play_runtime_from_legacy_files

root = Path(sys.argv[1])
runtime = import_play_runtime_from_legacy_files(root)
active = import_play_active_run_from_legacy_file(root)
print(
    json.dumps(
        {
            "runtime_imported": runtime.imported,
            "runtime_noop": runtime.noop,
            "runtime_run_ids": list(runtime.run_ids),
            "active_imported": active.imported,
            "active_noop": active.noop,
        }
    )
)
"""


def _play_dir(root: Path) -> Path:
    return root / LEGACY_PLAY_REL


def _assert_play_dir_absent(root: Path) -> None:
    assert not _play_dir(root).exists()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _hand_write_legacy_runtime(
    root: Path,
    *,
    snapshot,
    run_id: str = RUN_ID_A,
    progress=None,
    selected_at: str = SELECTED_AT,
) -> None:
    revision_n, sha = playable_of(snapshot)
    progress_model = progress if progress is not None else gate_progress()
    record = PlayRunRecord(
        run_id=run_id,
        campaign_id=snapshot.record.campaign_id,
        playable_artifact_id=snapshot.record.document_id,
        playable_revision=revision_n,
        playable_content_sha256=sha,
        run_revision=1,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        progress=progress_model,
    )
    _write_json(_play_dir(root) / "runs" / f"{run_id}.json", record.model_dump(mode="json"))
    manifest = derive_sealed_manifest(
        snapshot.markdown,
        run_id=run_id,
        playable_artifact_id=snapshot.record.document_id,
        playable_revision=revision_n,
        playable_content_sha256=sha,
        sealed_at=CREATED_AT,
    )
    _write_json(
        _play_dir(root) / "reference-manifests" / f"{run_id}.json",
        manifest.model_dump(mode="json", exclude_none=True),
    )
    _write_json(
        _play_dir(root) / "active-run.json",
        {
            "schema_version": PLAY_ACTIVE_RUN_SCHEMA,
            "run_id": run_id,
            "selected_at": selected_at,
        },
    )


def _exercise_full_play_chain(root: Path) -> dict:
    _assert_play_dir_absent(root)
    snapshot = create_committed_runbook(root, name="as5-absent")
    created = create_run(root, snapshot)
    _assert_play_dir_absent(root)
    manifest = seal_or_replay_play_run_reference_manifest(root, RUN_ID_A)
    loaded_manifest = get_play_run_reference_manifest(root, RUN_ID_A)
    assert loaded_manifest == manifest
    listed = list_play_runs(root)
    loaded = get_play_run(root, RUN_ID_A)
    assert listed == [loaded]
    assert loaded.run_id == created.run_id
    progressed = replace_play_run_progress(
        root,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        progress=gate_progress(),
    )
    original_revision = created.playable_revision
    original_sha = created.playable_content_sha256
    commit_runbook_markdown(
        root,
        snapshot.record.document_id,
        SURVIVING_TARGET_MARKDOWN,
        snapshot.loaded_revision,
    )
    later = get_workspace_document_snapshot(root, snapshot.record.document_id)
    target_revision, target_sha = playable_of(later)
    rebased = rebase_or_replay_play_run(
        root,
        run_id=RUN_ID_A,
        expected_run_revision=progressed.run_revision,
        target_playable_revision=target_revision,
        target_playable_content_sha256=target_sha,
    )
    selected = set_play_active_run(root, run_id=RUN_ID_A)
    resumed = get_play_active_run(root)
    assert resumed == selected
    historical = get_committed_playable_revision(
        snapshot.record.document_id,
        revision_n=original_revision,
        expected_sha256=original_sha,
        kind="runbook",
    )
    current = get_committed_playable_revision(snapshot.record.document_id, kind="runbook")
    _assert_play_dir_absent(root)
    return {
        "created": created,
        "progressed": progressed,
        "rebased": rebased,
        "selected": selected,
        "historical": historical,
        "current": current,
        "original_revision": original_revision,
        "original_sha": original_sha,
        "target_revision": target_revision,
        "target_sha": target_sha,
    }


def test_alembic_head_remains_0004(application_state_dsn: str) -> None:
    from alembic.script import ScriptDirectory

    from application_state.cli import _current_and_head

    current, head = _current_and_head(application_state_dsn)
    script_heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    assert current == head == "20260825_0004"
    assert script_heads == ["20260825_0004"]


def test_full_play_chain_with_play_dir_absent(
    tmp_path: Path, application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _exercise_full_play_chain(tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
    )
    first = TestClient(create_app()).get("/api/live/play-active-run")
    assert first.status_code == 200
    assert first.json()["run_id"] == RUN_ID_A

    other_root = tmp_path / "worktree-b"
    other_root.mkdir()
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: other_root,
    )
    restarted = TestClient(create_app()).get("/api/live/play-active-run")
    assert restarted.status_code == 200
    assert restarted.json() == first.json() == result["selected"].model_dump(mode="json")

    resumed = get_play_run(other_root, RUN_ID_A)
    manifest = get_play_run_reference_manifest(other_root, RUN_ID_A)
    assert resumed.run_revision == result["rebased"].run_revision
    assert resumed.progress.model_dump(mode="json") == gate_progress().model_dump(mode="json")
    assert resumed.playable_revision == result["target_revision"]
    assert resumed.playable_content_sha256 == result["target_sha"]
    assert manifest.playable_revision == result["target_revision"]
    assert result["historical"].revision_n == result["original_revision"]
    assert result["historical"].content_sha256 == result["original_sha"]
    assert result["current"].revision_n == result["target_revision"]
    assert count_play_rows(application_state_dsn) == (1, 1)
    assert count_active_run_rows(application_state_dsn) == 1
    _assert_play_dir_absent(tmp_path)
    _assert_play_dir_absent(other_root)


def test_hostile_play_sentinel_is_untouched(
    tmp_path: Path, application_state_dsn: str
) -> None:
    sentinel = _play_dir(tmp_path)
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_bytes(b"hostile-not-a-directory")
    sentinel.chmod(0o444)
    before = (sentinel.stat().st_mtime_ns, sentinel.stat().st_size, sentinel.stat().st_mode)
    payload = sentinel.read_bytes()

    snapshot = create_committed_runbook(tmp_path, name="as5-hostile")
    created = create_run(tmp_path, snapshot)
    replace_play_run_progress(
        tmp_path,
        run_id=RUN_ID_A,
        expected_run_revision=created.run_revision,
        progress=gate_progress(),
    )
    set_play_active_run(tmp_path, run_id=RUN_ID_A)
    assert get_play_run(tmp_path, RUN_ID_A).progress.current_beat_id == "beat:arrival"
    assert get_play_active_run(tmp_path).run_id == RUN_ID_A
    assert list_play_runs(tmp_path)[0].run_id == RUN_ID_A

    after = sentinel.stat()
    assert sentinel.is_file()
    assert not sentinel.is_dir()
    assert sentinel.read_bytes() == payload
    assert (after.st_mtime_ns, after.st_size, after.st_mode) == before
    assert count_play_rows(application_state_dsn) == (1, 1)


def test_db_down_does_not_read_or_mutate_contradictory_legacy_files(
    tmp_path: Path, application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = create_committed_runbook(tmp_path, name="as5-down")
    create_run(tmp_path, snapshot, run_id=RUN_ID_A)
    selected = set_play_active_run(tmp_path, run_id=RUN_ID_A)
    _hand_write_legacy_runtime(
        tmp_path,
        snapshot=snapshot,
        run_id=RUN_ID_B,
        selected_at="2020-01-01T00:00:00Z",
    )
    play_dir = _play_dir(tmp_path)
    before = {
        path.relative_to(play_dir).as_posix(): path.read_bytes()
        for path in sorted(play_dir.rglob("*"))
        if path.is_file()
    }
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, DOWN_DSN)

    with pytest.raises(PlayRunRegistryError) as get_exc:
        get_play_run(tmp_path, RUN_ID_A)
    assert get_exc.value.status_code == 503
    with pytest.raises(PlayRunRegistryError) as list_exc:
        list_play_runs(tmp_path)
    assert list_exc.value.status_code == 503
    with pytest.raises(PlayRunReferenceManifestError) as manifest_exc:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert manifest_exc.value.status_code == 503
    with pytest.raises(PlayActiveRunError) as active_exc:
        get_play_active_run(tmp_path)
    assert active_exc.value.status_code == 503
    with pytest.raises(PlayActiveRunError) as set_exc:
        set_play_active_run(tmp_path, run_id=RUN_ID_B)
    assert set_exc.value.status_code == 503
    with pytest.raises(PlayRunRebaseError) as rebase_exc:
        rebase_or_replay_play_run(
            tmp_path,
            run_id=RUN_ID_A,
            expected_run_revision=1,
            target_playable_revision=2,
            target_playable_content_sha256="a" * 64,
        )
    assert rebase_exc.value.status_code == 503
    for message in (
        str(get_exc.value),
        str(list_exc.value),
        str(active_exc.value),
        str(set_exc.value),
    ):
        assert RUN_ID_B not in message
        assert "2020-01-01T00:00:00Z" not in message

    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, application_state_dsn)
    after = {
        path.relative_to(play_dir).as_posix(): path.read_bytes()
        for path in sorted(play_dir.rglob("*"))
        if path.is_file()
    }
    assert after == before
    assert get_play_active_run(tmp_path) == selected
    assert get_play_run(tmp_path, RUN_ID_A).run_id == RUN_ID_A
    assert fetch_play_active_run_row(application_state_dsn)["run_id"] == RUN_ID_A


def test_predecessor_import_then_as5_head_reads_same_db_without_files(
    tmp_path: Path, application_state_dsn: str
) -> None:
    snapshot = create_committed_runbook(tmp_path, name="as5-bridge")
    _hand_write_legacy_runtime(tmp_path, snapshot=snapshot)
    assert count_play_rows(application_state_dsn) == (0, 0)
    assert count_active_run_rows(application_state_dsn) == 0

    repo = Path(__file__).resolve().parents[2]
    worktree = Path(tempfile.gettempdir()) / f"as5-pred-{os.getpid()}"
    added = False
    try:
        subprocess.check_call(
            ["git", "worktree", "add", "--detach", str(worktree), AS4_PREDECESSOR_SHA],
            cwd=repo,
        )
        added = True
        env = {
            **os.environ,
            APPLICATION_STATE_DSN_ENV: application_state_dsn,
            "PYTHONPATH": os.pathsep.join((str(worktree / "src"), str(worktree))),
        }
        output = subprocess.check_output(
            [sys.executable, "-c", _PREDECESSOR_IMPORT_SCRIPT, str(tmp_path)],
            cwd=worktree,
            env=env,
            text=True,
        )
    finally:
        if added:
            subprocess.call(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=repo,
            )

    payload = json.loads(output.strip().splitlines()[-1])
    assert payload == {
        "runtime_imported": 1,
        "runtime_noop": 0,
        "runtime_run_ids": [RUN_ID_A],
        "active_imported": 1,
        "active_noop": 0,
    }
    stored = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)
    assert stored["run"]["run_revision"] == 1
    assert stored["run"]["progress"] == gate_progress().model_dump(mode="json")
    pointer = fetch_play_active_run_row(application_state_dsn)
    assert pointer is not None
    assert pointer["run_id"] == RUN_ID_A
    selected_at = pointer["selected_at"]
    iso = selected_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    assert iso.startswith("2026-01-15T12:34:56")

    shutil.rmtree(_play_dir(tmp_path))
    _assert_play_dir_absent(tmp_path)

    loaded = get_play_run(tmp_path, RUN_ID_A)
    manifest = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    active = get_play_active_run(tmp_path)
    committed = get_committed_playable_revision(loaded.playable_artifact_id, kind="runbook")
    assert loaded.progress.model_dump(mode="json") == gate_progress().model_dump(mode="json")
    assert loaded.playable_revision == playable_of(snapshot)[0]
    assert loaded.playable_content_sha256 == playable_of(snapshot)[1]
    assert manifest.run_id == RUN_ID_A
    assert active.run_id == RUN_ID_A
    assert committed.revision_n == loaded.playable_revision
    assert committed.content_sha256 == loaded.playable_content_sha256
    replayed = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=loaded.playable_artifact_id,
        expected_playable_revision=loaded.playable_revision,
        expected_playable_content_sha256=loaded.playable_content_sha256,
    )
    assert replayed.run_revision == loaded.run_revision
    _assert_play_dir_absent(tmp_path)


def test_current_production_has_no_legacy_play_importers() -> None:
    import importlib

    for module_name in (
        "application_state.play.import_runtime",
        "application_state.play.import_active_run",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
    play_pkg = importlib.import_module("application_state.play")
    for symbol in (
        "import_play_runtime_from_legacy_files",
        "import_play_active_run_from_legacy_file",
        "PlayRuntimeImportReport",
        "PlayActiveRunImportReport",
        "FrozenPlayRuntime",
    ):
        assert not hasattr(play_pkg, symbol)
    from apps.live_control_server.services import play_active_run, play_run_rebase, play_run_registry
    from apps.live_control_server.services import play_run_reference_manifest as play_manifest

    assert not hasattr(play_active_run, "load_legacy_play_active_run_file")
    assert not hasattr(play_active_run, "play_active_run_path")
    assert not hasattr(play_run_rebase, "recover_legacy_rebase_intents")
    assert not hasattr(play_run_rebase, "PlayRunRebaseIntent")
    assert not hasattr(play_run_registry, "play_run_path")
    assert not hasattr(play_manifest, "play_run_reference_manifest_path")


def test_play_production_modules_do_not_depend_on_file_locks_or_live_store() -> None:
    repo = Path(__file__).resolve().parents[2]
    production = [
        repo / "apps/live_control_server/services/play_run_registry.py",
        repo / "apps/live_control_server/services/play_run_reference_manifest.py",
        repo / "apps/live_control_server/services/play_run_rebase.py",
        repo / "apps/live_control_server/services/play_active_run.py",
        repo / "src/application_state/play/__init__.py",
        repo / "src/application_state/play/types.py",
        repo / "src/application_state/play/service.py",
        repo / "src/application_state/play/repository.py",
    ]
    forbidden = (
        "registry_mutation_lock",
        "registry_token",
        "live_store",
        "from src.live_play.live_store import",
        "out/runtime/play",
        "PLAY_RUNS_REL",
        "PLAY_RUN_REFERENCE_MANIFESTS_REL",
        "PLAY_RUN_REBASE_INTENTS_REL",
        "PLAY_ACTIVE_RUN_REL",
    )
    for path in production:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} still contains {token}"
    assert (repo / "apps/live_control_server/services/registry_file_lock.py").is_file()
    assert (repo / "src/live_play/live_store.py").is_file()


def test_current_production_has_no_legacy_play_importers() -> None:
    import importlib

    for module_name in (
        "application_state.play.import_runtime",
        "application_state.play.import_active_run",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
    play_pkg = importlib.import_module("application_state.play")
    for symbol in (
        "import_play_runtime_from_legacy_files",
        "import_play_active_run_from_legacy_file",
        "PlayRuntimeImportReport",
        "PlayActiveRunImportReport",
        "FrozenPlayRuntime",
    ):
        assert not hasattr(play_pkg, symbol)
    from apps.live_control_server.services import play_active_run, play_run_rebase, play_run_registry
    from apps.live_control_server.services import play_run_reference_manifest as play_manifest

    assert not hasattr(play_active_run, "load_legacy_play_active_run_file")
    assert not hasattr(play_active_run, "play_active_run_path")
    assert not hasattr(play_run_rebase, "recover_legacy_rebase_intents")
    assert not hasattr(play_run_rebase, "PlayRunRebaseIntent")
    assert not hasattr(play_run_registry, "play_run_path")
    assert not hasattr(play_manifest, "play_run_reference_manifest_path")


def test_play_production_modules_do_not_depend_on_file_locks_or_live_store() -> None:
    repo = Path(__file__).resolve().parents[2]
    production = [
        repo / "apps/live_control_server/services/play_run_registry.py",
        repo / "apps/live_control_server/services/play_run_reference_manifest.py",
        repo / "apps/live_control_server/services/play_run_rebase.py",
        repo / "apps/live_control_server/services/play_active_run.py",
        repo / "src/application_state/play/__init__.py",
        repo / "src/application_state/play/types.py",
        repo / "src/application_state/play/service.py",
        repo / "src/application_state/play/repository.py",
    ]
    forbidden = (
        "registry_mutation_lock",
        "registry_token",
        "live_store",
        "from src.live_play.live_store import",
        "out/runtime/play",
        "PLAY_RUNS_REL",
        "PLAY_RUN_REFERENCE_MANIFESTS_REL",
        "PLAY_RUN_REBASE_INTENTS_REL",
        "PLAY_ACTIVE_RUN_REL",
    )
    for path in production:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} still contains {token}"
    assert (repo / "apps/live_control_server/services/registry_file_lock.py").is_file()
    assert (repo / "src/live_play/live_store.py").is_file()
