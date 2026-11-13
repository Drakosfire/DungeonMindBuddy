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
