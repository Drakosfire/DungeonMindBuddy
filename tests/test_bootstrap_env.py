"""``src.bootstrap_env`` — repo dotenv loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.bootstrap_env import (
    LOCAL_GRAPH_PROFILE_ENV,
    LocalGraphProfileError,
    load_dungeonmindbuddy_dotenv,
    read_local_graph_profile,
)


def test_load_dungeonmindbuddy_dotenv_idempotent() -> None:
    load_dungeonmindbuddy_dotenv()
    load_dungeonmindbuddy_dotenv()


def _private_profile(tmp_path: Path) -> Path:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    path = directory / "operator.env"
    path.write_text(
        "DMB_AGENT_GRAPH_AUTH_MODE=local_operator\n"
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT=local\n"
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN=" + "x" * 32 + "\n"
        "DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN=http://127.0.0.1:5202\n"
        "DMB_AGENT_GRAPH_LOCAL_API_HOST=127.0.0.1:8000\n"
        f"DMB_AGENT_GRAPH_SESSION_STORE={directory / 'sessions.json'}\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def test_explicit_private_profile_overrides_only_auth_session_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    path = _private_profile(tmp_path)
    monkeypatch.setenv(LOCAL_GRAPH_PROFILE_ENV, str(path))
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "wrong")
    monkeypatch.setenv("OPENAI_API_KEY", "provider-test-only")
    load_dungeonmindbuddy_dotenv(override=False)
    assert read_local_graph_profile(str(path))["DMB_AGENT_GRAPH_AUTH_MODE"] == "local_operator"
    assert __import__("os").environ["DMB_AGENT_GRAPH_AUTH_MODE"] == "local_operator"
    assert __import__("os").environ["OPENAI_API_KEY"] == "provider-test-only"
    assert "x" * 32 not in capsys.readouterr().out


@pytest.mark.parametrize("defect", ["world_readable", "parent_broad", "extra_key", "relative", "symlink"])
def test_private_profile_fails_closed(
    defect: str, tmp_path: Path,
) -> None:
    path = _private_profile(tmp_path)
    if defect == "world_readable":
        path.chmod(0o644)
    elif defect == "parent_broad":
        path.parent.chmod(0o755)
    elif defect == "extra_key":
        with path.open("a", encoding="utf-8") as handle:
            handle.write("UNRELATED_SECRET=ignored\n")
    elif defect == "relative":
        path = Path("operator.env")
    else:
        link = tmp_path / "link.env"
        link.symlink_to(path)
        path = link
    with pytest.raises(LocalGraphProfileError):
        read_local_graph_profile(str(path))
