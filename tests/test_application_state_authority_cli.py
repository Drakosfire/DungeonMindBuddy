from bootstrap_env import LOCAL_GRAPH_PROFILE_ENV
from scripts import application_state_authority as cli


def test_authority_cli_reports_invalid_profile_before_dispatch(tmp_path, monkeypatch, capsys):
    profile = tmp_path / "profile.env"
    profile.write_text("invalid=profile\n", encoding="utf-8")
    profile.chmod(0o600)
    monkeypatch.setenv(LOCAL_GRAPH_PROFILE_ENV, str(profile))

    def unexpected_dispatch(*args, **kwargs):
        raise AssertionError("profile must be validated before dispatch")

    monkeypatch.setattr(cli, "_cmd_backup", unexpected_dispatch)
    output = tmp_path / "backup.dump"
    assert cli.main(["backup", "--source-dsn", "postgresql://user:synthetic-secret@[", "--out", str(output)]) == 2
    diagnostic = capsys.readouterr().err
    assert "local_graph_profile_fields_invalid" in diagnostic
    assert "Traceback" not in diagnostic
    assert "synthetic-secret" not in diagnostic
    assert not output.exists()


def test_recovery_checks_client_before_database_work(tmp_path, monkeypatch):
    import pytest
    from application_state import authority

    def unexpected_database_call(*args, **kwargs):
        pytest.fail("client preflight must run before database work")

    monkeypatch.setattr(authority.shutil, "which", lambda command: None)
    monkeypatch.setattr(authority, "assert_safe_application_state_dsn", lambda dsn: None)
    monkeypatch.setattr(authority, "assert_dsn_is_not_world_graph", lambda *a, **kw: None)
    monkeypatch.setattr(authority, "assert_authority_target_isolated", lambda *a, **kw: None)
    monkeypatch.setattr(authority, "compute_fingerprint", unexpected_database_call)
    monkeypatch.setattr(authority, "database_has_app_state_schema", unexpected_database_call)
    monkeypatch.setattr(authority, "verify_backup_digest", lambda *a, **kw: None)
    monkeypatch.setattr(authority, "load_fingerprint_sidecar", lambda *a: object())
    output = tmp_path / "backup.dump"

    with pytest.raises(authority.ApplicationStateIntegrityError, match="pg_dump is required on PATH"):
        authority.backup_authority(source_dsn="synthetic", out_path=output)
    with pytest.raises(authority.ApplicationStateIntegrityError, match="pg_restore is required on PATH"):
        authority.restore_authority(target_dsn="synthetic", backup_path=output)
    assert not output.exists()


def test_recovery_client_version_errors_include_actionable_guidance():
    from application_state import authority

    dsn = "postgresql://user:synthetic-secret@localhost/dungeonbuddy_app_state_test"
    dump = authority._postgres_client_error(
        "pg_dump", f"aborting because of server version mismatch for {dsn}", dsn,
    )
    restore = authority._postgres_client_error(
        "pg_restore", "unsupported version (1.16) in file header", dsn,
    )
    assert "server version mismatch" in dump
    assert "source server's PostgreSQL major version" in dump
    assert "synthetic-secret" not in dump
    assert "unsupported version (1.16) in file header" in restore
    assert "toolchain that created the dump" in restore
    assert authority._postgres_client_error("pg_restore", "connection refused", dsn) == (
        "pg_restore failed: connection refused"
    )


def test_backup_stages_and_preserves_existing_set(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import pytest
    from application_state import authority

    out = tmp_path / "backup.dump"
    dsn = "postgresql://user@localhost/dungeonbuddy_app_state_test"
    fingerprint = SimpleNamespace(digest="before", to_json=lambda: "{}")
    monkeypatch.setattr(authority, "_require_postgres_client", lambda command: command)
    monkeypatch.setattr(authority, "compute_fingerprint", lambda dsn: fingerprint)

    def dump(args, **kwargs):
        staged = out.parent / args[args.index("--file") + 1]
        assert staged.parent != out.parent
        assert not out.exists()
        staged.write_bytes(b"dump bytes")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(authority.subprocess, "run", dump)
    original_dump = dump

    def changed_source(args, **kwargs):
        result = original_dump(args, **kwargs)
        fingerprint.digest = "before"
        monkeypatch.setattr(
            authority, "compute_fingerprint", lambda dsn: SimpleNamespace(digest="after"),
        )
        return result

    monkeypatch.setattr(authority.subprocess, "run", changed_source)
    with pytest.raises(authority.ApplicationStateIntegrityError, match="changed during backup"):
        authority.backup_authority(source_dsn=dsn, out_path=out)
    assert list(tmp_path.iterdir()) == []

    monkeypatch.setattr(authority, "compute_fingerprint", lambda dsn: fingerprint)
    monkeypatch.setattr(authority.subprocess, "run", original_dump)
    link = type(out).hardlink_to

    def fail_second_link(path, target):
        if path == authority.fingerprint_sidecar_path(out):
            assert authority.sha256_sidecar_path(out).is_file()
            raise OSError("synthetic publication failure")
        link(path, target)

    with monkeypatch.context() as publication:
        publication.setattr(type(out), "hardlink_to", fail_second_link)
        with pytest.raises(OSError, match="synthetic publication failure"):
            authority.backup_authority(source_dsn=dsn, out_path=out)
    assert list(tmp_path.iterdir()) == []

    record = authority.backup_authority(source_dsn=dsn, out_path=out)
    assert authority.verify_backup_digest(out) == record.backup_sha256
    before = {path: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(authority.ApplicationStateIntegrityError, match="destination already exists"):
        authority.backup_authority(source_dsn=dsn, out_path=out)
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_recovery_client_deadline_and_interrupt(monkeypatch):
    import pytest
    from application_state import authority

    def timeout(argv, **kwargs):
        assert kwargs["timeout"] == 3
        raise authority.subprocess.TimeoutExpired(argv, 3)

    monkeypatch.setattr(authority.subprocess, "run", timeout)
    with pytest.raises(authority.ApplicationStateUnavailableError, match="timed out after 3 seconds"):
        authority._run_recovery_client(["pg_dump"], env={}, timeout_seconds=3, failure_hint="Retry.")

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(authority.subprocess, "run", interrupt)
    with pytest.raises(authority.ApplicationStateUnavailableError, match="recreate the target"):
        authority._run_recovery_client(
            ["pg_restore"], env={}, timeout_seconds=None, failure_hint="Discard and recreate the target.",
        )


def test_failed_restore_never_reports_ready(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace

    from application_state import authority

    def fail_replay(argv, **kwargs):
        assert "--single-transaction" in argv
        return SimpleNamespace(returncode=1, stderr="synthetic replay failure")

    def unexpected_fingerprint(*args, **kwargs):
        raise AssertionError("failed replay must stop before fingerprint verification")

    monkeypatch.setattr("bootstrap_env.load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setattr(authority, "verify_backup_digest", lambda *args, **kwargs: None)
    monkeypatch.setattr(authority, "load_fingerprint_sidecar", lambda path: object())
    monkeypatch.setattr(authority, "_require_postgres_client", lambda command: command)
    monkeypatch.setattr(authority, "database_has_app_state_schema", lambda dsn: False)
    monkeypatch.setattr(authority, "compute_fingerprint", unexpected_fingerprint)
    monkeypatch.setattr(authority.subprocess, "run", fail_replay)
    code = cli.main([
        "restore",
        "--target-dsn", "postgresql://user@localhost/dungeonbuddy_app_state_test",
        "--backup", str(tmp_path / "backup.dump"),
    ])
    output = capsys.readouterr()
    assert code == 2
    assert "READY" not in output.out
    assert "pg_restore failed: synthetic replay failure" in output.err
