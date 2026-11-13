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
