"""Opt-in local Graph profile over existing operator files, without provider IO."""

from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

import pytest

from apps.live_control_server.config import (
    MANAGED_WORLD_DATA_ROOT_ENV,
    ManagedWorldDataRootError,
    managed_world_data_root,
)
from apps.live_control_server.routes import world_containers as world_routes
from apps.live_control_server.services.world_container_registry import (
    NativeGraphBindingRecord,
    WorldContainerRecord,
    WorldContainerRegistryDocument,
    get_world_container,
    world_source_root_relpath,
)
from scripts.preflight_local_graph_profile import inspect_local_graph_profile, main
from src.bootstrap_env import LOCAL_GRAPH_PROFILE_ENV


def _operator_root(tmp_path: Path) -> Path:
    root = tmp_path / "operator-data"
    registry = root / "out/registries/world_containers.json"
    registry.parent.mkdir(parents=True)
    source = root / world_source_root_relpath("elderwyld")
    source.mkdir(parents=True)
    record = WorldContainerRecord(
        world_id="elderwyld", name="Elderwyld",
        source_root_relpath=world_source_root_relpath("elderwyld"),
        created_at="2026-10-06T00:00:00Z",
        native_graph_binding=NativeGraphBindingRecord(
            native_world_id="native-elderwyld", status="active", binding_version=1,
            validated_at="2026-10-06T00:00:00Z", validated_head_revision_id="rev:test",
        ),
    )
    registry.write_text(
        WorldContainerRegistryDocument(records=[record]).model_dump_json(),
        encoding="utf-8",
    )
    return root


def _private_profile(tmp_path: Path) -> Path:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    path = directory / "local-operator.env"
    path.write_text(
        "DMB_AGENT_GRAPH_AUTH_MODE=local_operator\n"
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT=local\n"
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN=" + "z" * 32 + "\n"
        "DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN=http://127.0.0.1:5202\n"
        "DMB_AGENT_GRAPH_LOCAL_API_HOST=127.0.0.1:8000\n"
        f"DMB_AGENT_GRAPH_SESSION_STORE={directory / 'sessions.json'}\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def test_existing_world_registry_reopens_from_two_code_checkouts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _operator_root(tmp_path)
    monkeypatch.setenv(MANAGED_WORLD_DATA_ROOT_ENV, str(operator))
    for name in ("checkout-a", "checkout-b"):
        checkout = tmp_path / name
        checkout.mkdir()
        monkeypatch.setattr(world_routes, "repo_root", lambda checkout=checkout: checkout)
        assert not (checkout / "out/registries/world_containers.json").exists()
        assert managed_world_data_root(checkout) == operator
        records = world_routes.get_world_containers()["records"]
        assert [record["world_id"] for record in records] == ["elderwyld"]
        assert get_world_container(managed_world_data_root(checkout), "elderwyld").native_graph_binding.status == "active"
    monkeypatch.delenv(MANAGED_WORLD_DATA_ROOT_ENV)
    assert managed_world_data_root(tmp_path / "checkout-a") == tmp_path / "checkout-a"


def test_invalid_opted_in_root_never_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    for invalid in ("relative-root", str(tmp_path / "missing"), str(checkout)):
        monkeypatch.setenv(MANAGED_WORLD_DATA_ROOT_ENV, invalid)
        with pytest.raises(ManagedWorldDataRootError):
            managed_world_data_root(checkout)


def test_preflight_reports_configuration_not_answer_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    operator = _operator_root(tmp_path)
    private = _private_profile(tmp_path)
    server = tmp_path / "server"
    server.mkdir()
    (server / "dev_server.py").write_text("# synthetic\n")
    monkeypatch.setenv(MANAGED_WORLD_DATA_ROOT_ENV, str(operator))
    monkeypatch.setenv(LOCAL_GRAPH_PROFILE_ENV, str(private))
    assert inspect_local_graph_profile(
        ui_port=5202, api_port=8000, server_root=server, required_world="elderwyld",
    ) is None
    assert main([
        "--ui-port", "5202", "--api-port", "8000", "--server-root", str(server),
        "--require-world", "elderwyld",
    ]) == 0
    output = capsys.readouterr().out
    assert "Local Graph access: CONFIGURED" in output
    assert "Graph-backed answer: UNVERIFIED" in output
    assert "z" * 32 not in output
    assert inspect_local_graph_profile(
        ui_port=5173, api_port=8000, server_root=server,
    ) == "local_graph_origin_host_mismatch"
    assert inspect_local_graph_profile(
        ui_port=5202, api_port=8000, server_root=server, required_world="unknown",
    ) == "managed_world_binding_unavailable"

    source = operator / world_source_root_relpath("elderwyld")
    source.rmdir()
    source.symlink_to(tmp_path, target_is_directory=True)
    assert inspect_local_graph_profile(
        ui_port=5202, api_port=8000, server_root=server, required_world="elderwyld",
    ) == "managed_world_binding_unavailable"


def test_opted_in_launcher_refuses_unowned_api_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _operator_root(tmp_path)
    private = _private_profile(tmp_path)
    server = tmp_path / "server"
    server.mkdir()
    (server / "dev_server.py").write_text("# synthetic\n")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        env = dict(os.environ)
        env.update({
            LOCAL_GRAPH_PROFILE_ENV: str(private),
            MANAGED_WORLD_DATA_ROOT_ENV: str(operator),
            "DUNGEONMIND_SERVER_ROOT": str(server),
            "BUDDY_API_PORT": str(port),
            "BUDDY_UI_PORT": "5202",
        })
        result = subprocess.run(
            ["bash", "run"], cwd=Path(__file__).resolve().parents[1],
            env=env, capture_output=True, text=True, timeout=10, check=False,
        )
    assert result.returncode != 0
    assert "cannot verify an existing API/UI listener" in result.stderr
    assert "local stack up" not in result.stdout
