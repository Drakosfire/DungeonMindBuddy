from __future__ import annotations

import importlib.util
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest

from apps.live_control_server.services.play_run_registry import (
    create_or_replay_play_run,
    ensure_v2_native_ready,
    get_play_run,
    list_play_runs,
)
from apps.live_control_server.services.workspace_document_registry import (
    get_committed_playable_revision,
    list_workspace_documents,
)
from application_state.config import APPLICATION_STATE_DSN_ENV, load_runtime_dsn
from application_state.content.service import commit_runbook, create_runbook
from application_state.content.types import WorkObject, sha256_utf8
from application_state.errors import ApplicationStateUnavailableError
from application_state.naming import database_name_from_dsn
from tests.application_state.conftest import (
    _admin_dsn,
    _create_database,
    _drop_database,
    _replace_database,
)
from tests.application_state.play_runtime_helpers import RUN_ID_A

_BOOTSTRAP_PATH = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap_local_play.py"

V2_BREACH_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:survive-breach -->",
        "## Survive the Current Breach",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:tunnel -->",
        "### Tunnel Breach",
        "",
        "Tunnel unique body.",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->",
        "### North Gate",
        "",
        "North Gate body.",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:courtyard -->",
        "### Courtyard",
        "",
        "Courtyard body.",
        "",
    ]
)

SECRET_PASSWORD = "super-secret-df0-password"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("bootstrap_local_play", _BOOTSTRAP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bootstrap = load_bootstrap()


def _database_exists(admin_dsn: str, name: str) -> bool:
    import psycopg

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        row = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        return row is not None


@pytest.fixture
def provisionable_dsn(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, str, str]]:
    admin = _admin_dsn()
    name = f"dungeonbuddy_application_state_{uuid.uuid4().hex[:12]}"
    dsn = _replace_database(admin, name)
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    try:
        yield dsn, name, admin
    finally:
        if _database_exists(admin, name):
            _drop_database(admin, name)


def _committed_runbook() -> WorkObject:
    obj = create_runbook(
        title="Survive the Current Breach", campaign_id="longmont-c2", target_session=23
    )
    obj, _revision = commit_runbook(
        str(obj.work_object_id), V2_BREACH_MARKDOWN, expected_revision=obj.object_revision
    )
    return obj


def _assert_no_secrets(output: str, dsn: str | None = None) -> None:
    lowered = output.lower()
    assert SECRET_PASSWORD not in output
    assert "super-secret-df0-password" not in lowered
    if dsn:
        assert dsn not in output
        parsed = urlparse(dsn)
        if parsed.password:
            assert parsed.password not in output


def _unavailable_message() -> str:
    try:
        load_runtime_dsn()
    except ApplicationStateUnavailableError as exc:
        return str(exc)
    raise AssertionError("expected unavailable")


def test_may_create_only_standard_buddy_names() -> None:
    assert bootstrap.may_create_logical_database("dungeonbuddy_application_state") is True
    assert bootstrap.may_create_logical_database("dungeonbuddy_application_state_df0abc") is True
    assert bootstrap.may_create_logical_database("buddy_custom_state") is False
    assert bootstrap.may_create_logical_database("dungeonbuddy_application_state-dash") is False
    assert bootstrap.may_create_logical_database("dungeonmind") is False


def test_missing_dsn_is_actionable_and_read_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    probed: list[object] = []
    created: list[object] = []
    monkeypatch.setattr(bootstrap, "_probe_target_database", lambda dsn: probed.append(dsn) or (None, None, None))
    monkeypatch.setattr(bootstrap, "_create_logical_database", lambda dsn: created.append(dsn))
    code = bootstrap.main(["check"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert "PLAY READINESS: NEEDS CONFIGURATION" in output
    assert "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL" in output
    assert "Plan kind" not in output
    assert probed == []
    assert created == []


def test_missing_dsn_copy_is_domain_neutral(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
    message = _unavailable_message()
    assert "Plan kind cannot use application state" not in message
    assert "DungeonBuddy application state is unavailable" in message


def test_world_graph_dsn_as_app_state_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    world = "postgresql://buddy:secret@127.0.0.1:54329/dungeonbuddy_application_state_world"
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", world)
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, world)
    code = bootstrap.main(["check"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert "PLAY READINESS: BLOCKED" in output
    assert "isolation: rejected" in output
    assert "secret" not in output


def test_forbidden_dungeonmind_database_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(
        APPLICATION_STATE_DSN_ENV,
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind",
    )
    created: list[str] = []
    monkeypatch.setattr(bootstrap, "_create_logical_database", lambda dsn: created.append(dsn))
    check_code = bootstrap.main(["check"], load_env=False)
    check_out = capsys.readouterr().out
    apply_code = bootstrap.main(["apply"], load_env=False)
    apply_out = capsys.readouterr().out
    assert check_code == 2
    assert apply_code == 2
    assert "rejected" in check_out
    assert "rejected" in apply_out
    assert created == []
    assert "dungeonmind-dev" not in check_out
    assert "dungeonmind-dev" not in apply_out


def test_unreachable_postgres_is_named_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn = f"postgresql://buddy:{SECRET_PASSWORD}@127.0.0.1:1/dungeonbuddy_application_state"
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    code = bootstrap.main(["check"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert "PLAY READINESS: UNAVAILABLE" in output
    _assert_no_secrets(output, dsn)


def test_check_reports_missing_database_without_creating(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    assert _database_exists(admin, name) is False
    code = bootstrap.main(["check"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert "exists: no" in output
    assert "PLAY READINESS: NEEDS BOOTSTRAP" in output
    assert _database_exists(admin, name) is False
    _assert_no_secrets(output, dsn)


def test_check_reports_schema_behind_without_migrating(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    _create_database(admin, name)
    code = bootstrap.main(["check"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert "status: behind" in output
    assert "PLAY READINESS: NEEDS BOOTSTRAP" in output
    current, head, status = bootstrap._schema_status(dsn)
    assert current is None
    assert status == "behind"
    assert head
    _assert_no_secrets(output, dsn)


def test_check_ready_with_committed_runbook(
    application_state_dsn: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _committed_runbook()
    code = bootstrap.main(["check"], load_env=False)
    output = capsys.readouterr().out
    assert code == 0
    assert "PLAY READINESS: READY" in output
    assert "active startable Runbooks: 1" in output
    assert "status: ready" in output


def test_check_zero_committed_runbooks_is_content_not_ready(
    application_state_dsn: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = bootstrap.main(["check"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert "Application state: READY" in output
    assert "Play content: NOT READY" in output
    assert "No sample or fake Runbook was created." in output
    assert "active startable Runbooks: 0" in output


def test_apply_unsafe_dsn_makes_zero_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(
        APPLICATION_STATE_DSN_ENV,
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind",
    )
    upgraded: list[str] = []
    created: list[str] = []
    monkeypatch.setattr(bootstrap, "upgrade_to_head", lambda **kwargs: upgraded.append("yes"))
    monkeypatch.setattr(bootstrap, "_create_logical_database", lambda dsn: created.append(dsn))
    code = bootstrap.main(["apply"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert upgraded == []
    assert created == []
    assert "PLAY READINESS: BLOCKED" in output


def test_apply_creates_standard_suffix_database(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    assert _database_exists(admin, name) is False
    check_code = bootstrap.main(["check"], load_env=False)
    capsys.readouterr()
    assert check_code == 2
    assert _database_exists(admin, name) is False
    code = bootstrap.main(["apply"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    assert _database_exists(admin, name) is True
    assert "created: yes" in output
    assert "Play content: NOT READY" in output
    assert "active startable Runbooks: 0" in output
    _assert_no_secrets(output, dsn)


def test_apply_refuses_arbitrary_custom_database_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    admin = _admin_dsn()
    name = f"buddy_custom_df0_{uuid.uuid4().hex[:10]}"
    dsn = _replace_database(admin, name)
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    try:
        code = bootstrap.main(["apply"], load_env=False)
        output = capsys.readouterr().out
        assert code == 2
        assert "will not create an arbitrary" in output
        assert _database_exists(admin, name) is False
    finally:
        if _database_exists(admin, name):
            _drop_database(admin, name)


def test_apply_uses_existing_safe_database_without_drop(
    application_state_dsn: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    name = database_name_from_dsn(application_state_dsn)
    admin = _admin_dsn()
    assert _database_exists(admin, name) is True
    code = bootstrap.main(["apply"], load_env=False)
    output = capsys.readouterr().out
    assert _database_exists(admin, name) is True
    assert "created: yes" not in output
    assert "DROP" not in output
    assert "PLAY READINESS:" in output
    assert code == 2


def test_apply_upgrades_schema_behind_to_head(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    _create_database(admin, name)
    current, _head, status = bootstrap._schema_status(dsn)
    assert current is None
    assert status == "behind"
    code = bootstrap.main(["apply"], load_env=False)
    output = capsys.readouterr().out
    assert code == 2
    current, head, status = bootstrap._schema_status(dsn)
    assert current == head
    assert status == "ready"
    assert "status: ready" in output
    assert "Play content: NOT READY" in output


def test_second_apply_does_not_mutate_existing_run(
    application_state_dsn: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = _committed_runbook()
    document_id = str(record.work_object_id)
    committed = get_committed_playable_revision(document_id)
    created = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=document_id,
        expected_playable_revision=committed.revision_n,
        expected_playable_content_sha256=committed.content_sha256,
    )
    ready = ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert ready.progress.current_beat_id == "beat:survive-breach"
    for _ in range(2):
        assert bootstrap.main(["apply"], load_env=False) == 0
        capsys.readouterr()
        assert get_play_run(tmp_path, RUN_ID_A) == ready
        assert get_committed_playable_revision(document_id) == committed
    assert list_play_runs(tmp_path)[0].run_id == created.run_id


def test_bootstrap_then_normal_content_to_native_ready_play(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    assert not _database_exists(admin, name)
    assert bootstrap.main(["apply"], load_env=False) == 2
    assert "Play content: NOT READY" in capsys.readouterr().out
    record = _committed_runbook()
    document_id = str(record.work_object_id)
    listed = list_workspace_documents(tmp_path, kind="runbook", status="active")
    assert [row.document_id for row in listed] == [document_id]
    committed = get_committed_playable_revision(document_id)
    assert committed.content_sha256 == sha256_utf8(V2_BREACH_MARKDOWN)
    assert committed.markdown == V2_BREACH_MARKDOWN
    assert bootstrap.main(["check"], load_env=False) == 0
    capsys.readouterr()
    create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=document_id,
        expected_playable_revision=committed.revision_n,
        expected_playable_content_sha256=committed.content_sha256,
    )
    ready = ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert ready.playable_revision == committed.revision_n
    assert ready.playable_content_sha256 == committed.content_sha256
    assert ready.progress.current_beat_id == "beat:survive-breach"
    assert ready.progress.current_scene_id is None
    assert bootstrap.main(["apply"], load_env=False) == 0
    capsys.readouterr()
    assert get_play_run(tmp_path, RUN_ID_A) == ready


@pytest.mark.parametrize("with_content", [False, True])
def test_check_and_apply_ignore_and_preserve_stale_workspace_files(
    application_state_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    with_content: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from apps.live_control_server.services.runtime_preflight import _check_app_state

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    registry = tmp_path / "out/registries/workspace_documents.json"
    registry.parent.mkdir(parents=True)
    registry.write_bytes(b"malformed obsolete registry, not database authority")
    body = tmp_path / "out/workspace/runbooks/leftover.md"
    body.parent.mkdir(parents=True)
    body.write_bytes(b"preserve these unadopted bytes")
    expected = {f: f.read_bytes() for f in (registry, body)}
    if with_content:
        record = _committed_runbook()
        committed = get_committed_playable_revision(str(record.work_object_id))
    expected_code = 0 if with_content else 2
    for command in ("check", "apply", "apply", "check"):
        assert bootstrap.main([command], load_env=False) == expected_code
        output = capsys.readouterr().out
        assert "Legacy Runbooks" not in output
        assert "NEEDS BOOTSTRAP" not in output
        assert {f: f.read_bytes() for f in expected} == expected
        listed = list_workspace_documents(tmp_path, kind="runbook", status="active")
        assert len(listed) == int(with_content)
        if with_content:
            assert get_committed_playable_revision(str(record.work_object_id)) == committed
    # Exercise the assembled runtime consumer rather than just the CLI helper.
    assert _check_app_state(load_env=False).status == "READY"


def test_check_and_apply_never_print_full_dsn(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, _name, _admin = provisionable_dsn
    bootstrap.main(["check"], load_env=False)
    check_out = capsys.readouterr().out
    bootstrap.main(["apply"], load_env=False)
    apply_out = capsys.readouterr().out
    _assert_no_secrets(check_out, dsn)
    _assert_no_secrets(apply_out, dsn)
    assert "username:" in apply_out
    assert "host:" in apply_out
    assert "database:" in apply_out
