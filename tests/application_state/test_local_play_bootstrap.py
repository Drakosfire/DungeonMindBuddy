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
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryDocument,
    get_committed_playable_revision,
    list_workspace_documents,
    workspace_documents_path,
)
from application_state.config import APPLICATION_STATE_DSN_ENV, load_runtime_dsn
from application_state.content.types import sha256_utf8
from application_state.errors import ApplicationStateUnavailableError
from application_state.naming import database_name_from_dsn
from src.live_play.live_store import write_json
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


def _legacy_runbook(
    root: Path,
    *,
    markdown: str | None,
    content_status: str = "committed",
    revision: int = 17,
    title: str = "Survive the Current Breach",
) -> WorkspaceDocumentRecord:
    document_id = str(uuid.uuid4())
    relpath = f"out/workspace/runbooks/{document_id}.md"
    if markdown is not None:
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
    now = "2026-01-01T00:00:00Z"
    return WorkspaceDocumentRecord(
        document_id=document_id,
        title=title,
        campaign_id="longmont-c2",
        target_session=23,
        kind="runbook",
        target_relpath=relpath,
        status="active",
        content_status=content_status,  # type: ignore[arg-type]
        revision=revision,
        created_at=now,
        updated_at=now,
    )


def _write_leftover_registry(root: Path, *records: WorkspaceDocumentRecord) -> None:
    path = workspace_documents_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, WorkspaceDocumentRegistryDocument(records=list(records)).model_dump(mode="json"))


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
    code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
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
    code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
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
    check_code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
    check_out = capsys.readouterr().out
    apply_code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
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
    code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 2
    assert "PLAY READINESS: UNAVAILABLE" in output
    _assert_no_secrets(output, dsn)


def test_check_reports_missing_database_without_creating(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    assert _database_exists(admin, name) is False
    code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
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
    code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
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
    from application_state.content.import_runbooks import freeze_legacy_runbook, import_runbooks_from_snapshots

    record = _legacy_runbook(tmp_path, markdown=V2_BREACH_MARKDOWN)
    import_runbooks_from_snapshots([freeze_legacy_runbook(record, V2_BREACH_MARKDOWN)])
    code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 0
    assert "PLAY READINESS: READY" in output
    assert "active startable Runbooks: 1" in output
    assert "status: ready" in output


def test_check_zero_committed_runbooks_is_content_not_ready(
    application_state_dsn: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
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
    code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 2
    assert upgraded == []
    assert created == []
    assert "PLAY READINESS: BLOCKED" in output


def test_apply_creates_standard_suffix_database(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    record = _legacy_runbook(tmp_path, markdown=V2_BREACH_MARKDOWN)
    _write_leftover_registry(tmp_path, record)
    assert _database_exists(admin, name) is False
    check_code = bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
    capsys.readouterr()
    assert check_code == 2
    assert _database_exists(admin, name) is False
    code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 0
    assert _database_exists(admin, name) is True
    assert "created: yes" in output
    assert "PLAY READINESS: READY" in output
    assert "imported: 1" in output
    _assert_no_secrets(output, dsn)


def test_apply_refuses_arbitrary_custom_database_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    admin = _admin_dsn()
    name = f"buddy_custom_df0_{uuid.uuid4().hex[:10]}"
    dsn = _replace_database(admin, name)
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    try:
        code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
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
    code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
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
    code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 2
    current, head, status = bootstrap._schema_status(dsn)
    assert current == head
    assert status == "ready"
    assert "status: ready" in output
    assert "Play content: NOT READY" in output


def test_apply_adopts_legacy_committed_runbook_exactly(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = _legacy_runbook(tmp_path, markdown=V2_BREACH_MARKDOWN, revision=17)
    _write_leftover_registry(tmp_path, record)
    first = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    first_out = capsys.readouterr().out
    assert first == 0
    assert "imported: 1" in first_out
    listed = list_workspace_documents(tmp_path, kind="runbook", status="active")
    assert [row.document_id for row in listed] == [record.document_id]
    committed = get_committed_playable_revision(record.document_id)
    assert committed.revision_n == 17
    assert committed.markdown == V2_BREACH_MARKDOWN
    assert committed.content_sha256 == sha256_utf8(V2_BREACH_MARKDOWN)
    second = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    second_out = capsys.readouterr().out
    assert second == 0
    assert "imported: 0" in second_out
    assert "noop: 1" in second_out
    replay = get_committed_playable_revision(record.document_id)
    assert replay.revision_n == 17
    assert replay.content_sha256 == committed.content_sha256


def test_legacy_draft_runbook_is_not_startable(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = _legacy_runbook(
        tmp_path,
        markdown="# draft only\n",
        content_status="draft",
        revision=3,
    )
    _write_leftover_registry(tmp_path, record)
    code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 2
    assert "Play content: NOT READY" in output
    assert "active startable Runbooks: 0" in output
    listed = list_workspace_documents(tmp_path, kind="runbook", status="active")
    assert listed[0].document_id == record.document_id
    assert listed[0].content_status == "draft"


def test_missing_committed_legacy_bytes_fail_closed(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = _legacy_runbook(tmp_path, markdown=None, content_status="committed")
    _write_leftover_registry(tmp_path, record)
    code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 2
    assert "PLAY READINESS: BLOCKED" in output
    assert list_workspace_documents(tmp_path, kind="runbook", status="active") == []


def test_identity_content_conflict_fails_closed_without_overwrite(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = _legacy_runbook(tmp_path, markdown=V2_BREACH_MARKDOWN, revision=17)
    _write_leftover_registry(tmp_path, record)
    assert bootstrap.main(["apply"], load_env=False, repo_root=tmp_path) == 0
    capsys.readouterr()
    target = tmp_path / str(record.target_relpath)
    target.write_text("# different semantic bytes\n", encoding="utf-8")
    code = bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    output = capsys.readouterr().out
    assert code == 2
    assert "PLAY READINESS: BLOCKED" in output
    committed = get_committed_playable_revision(record.document_id)
    assert committed.markdown == V2_BREACH_MARKDOWN
    assert committed.revision_n == 17


def test_second_apply_does_not_mutate_existing_run(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = _legacy_runbook(tmp_path, markdown=V2_BREACH_MARKDOWN, revision=17)
    _write_leftover_registry(tmp_path, record)
    assert bootstrap.main(["apply"], load_env=False, repo_root=tmp_path) == 0
    capsys.readouterr()
    committed = get_committed_playable_revision(record.document_id)
    created = create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=record.document_id,
        expected_playable_revision=committed.revision_n,
        expected_playable_content_sha256=committed.content_sha256,
    )
    ready = ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert ready.progress.current_beat_id == "beat:survive-breach"
    assert bootstrap.main(["apply"], load_env=False, repo_root=tmp_path) == 0
    output = capsys.readouterr().out
    assert "noop: 1" in output
    unchanged = get_play_run(tmp_path, RUN_ID_A)
    assert unchanged.run_revision == ready.run_revision
    assert unchanged.progress.current_beat_id == ready.progress.current_beat_id
    assert unchanged.progress.current_scene_id == ready.progress.current_scene_id
    assert list_play_runs(tmp_path)[0].run_id == RUN_ID_A
    assert created.run_id == RUN_ID_A


def test_bootstrap_to_native_ready_play_seam(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, name, admin = provisionable_dsn
    record = _legacy_runbook(tmp_path, markdown=V2_BREACH_MARKDOWN, revision=17)
    _write_leftover_registry(tmp_path, record)
    assert bootstrap.main(["check"], load_env=False, repo_root=tmp_path) == 2
    capsys.readouterr()
    assert _database_exists(admin, name) is False
    assert bootstrap.main(["apply"], load_env=False, repo_root=tmp_path) == 0
    capsys.readouterr()
    listed = list_workspace_documents(tmp_path, kind="runbook", status="active")
    assert listed[0].document_id == record.document_id
    committed = get_committed_playable_revision(record.document_id)
    assert committed.revision_n == 17
    assert committed.content_sha256 == sha256_utf8(V2_BREACH_MARKDOWN)
    assert "Tunnel unique body." in committed.markdown
    create_or_replay_play_run(
        tmp_path,
        run_id=RUN_ID_A,
        playable_artifact_id=record.document_id,
        expected_playable_revision=committed.revision_n,
        expected_playable_content_sha256=committed.content_sha256,
    )
    ready = ensure_v2_native_ready(tmp_path, RUN_ID_A)
    assert ready.playable_artifact_id == record.document_id
    assert ready.playable_revision == 17
    assert ready.playable_content_sha256 == committed.content_sha256
    assert ready.progress.current_beat_id == "beat:survive-breach"
    assert ready.progress.current_scene_id is None
    assert bootstrap.main(["apply"], load_env=False, repo_root=tmp_path) == 0
    capsys.readouterr()
    assert get_play_run(tmp_path, RUN_ID_A).run_id == RUN_ID_A
    del dsn


def test_check_and_apply_never_print_full_dsn(
    provisionable_dsn: tuple[str, str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn, _name, _admin = provisionable_dsn
    bootstrap.main(["check"], load_env=False, repo_root=tmp_path)
    check_out = capsys.readouterr().out
    bootstrap.main(["apply"], load_env=False, repo_root=tmp_path)
    apply_out = capsys.readouterr().out
    _assert_no_secrets(check_out, dsn)
    _assert_no_secrets(apply_out, dsn)
    assert "username:" in apply_out
    assert "host:" in apply_out
    assert "database:" in apply_out
