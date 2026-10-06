#!/usr/bin/env python3
"""Presence-only preflight for the opt-in local Graph launch profile."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.live_control_server.config import (  # noqa: E402
    MANAGED_WORLD_DATA_ROOT_ENV,
    ManagedWorldDataRootError,
    managed_world_data_root,
)
from apps.live_control_server.services.world_container_registry import (  # noqa: E402
    WorldContainerRegistryError,
    list_world_containers,
    world_source_root_relpath,
)
from src.bootstrap_env import (  # noqa: E402
    LOCAL_GRAPH_PROFILE_ENV,
    LocalGraphProfileError,
    load_dungeonmindbuddy_dotenv,
)


def inspect_local_graph_profile(
    *, ui_port: int, api_port: int, server_root: Path,
    required_world: str | None = None,
) -> str | None:
    """Return a safe reason code, or None when local access is configured."""
    if not os.environ.get(LOCAL_GRAPH_PROFILE_ENV, "").strip():
        return "local_graph_profile_missing"
    if not os.environ.get(MANAGED_WORLD_DATA_ROOT_ENV, "").strip():
        return "managed_world_root_missing"
    if not server_root.is_absolute() or not server_root.is_dir():
        return "dungeonmind_server_root_invalid"
    if not (server_root / "dev_server.py").is_file() and not (server_root / "app.py").is_file():
        return "dungeonmind_server_root_invalid"
    try:
        load_dungeonmindbuddy_dotenv()
    except LocalGraphProfileError as exc:
        return str(exc)
    if (
        os.environ.get("DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN")
        != f"http://127.0.0.1:{ui_port}"
        or os.environ.get("DMB_AGENT_GRAPH_LOCAL_API_HOST")
        != f"127.0.0.1:{api_port}"
    ):
        return "local_graph_origin_host_mismatch"
    try:
        root = managed_world_data_root()
        records = list_world_containers(root)
    except (ManagedWorldDataRootError, WorldContainerRegistryError) as exc:
        return (
            str(exc) if isinstance(exc, ManagedWorldDataRootError)
            else "managed_world_registry_invalid"
        )
    def source_is_contained(relpath: str) -> bool:
        try:
            source = (root / relpath).resolve(strict=True)
        except (OSError, RuntimeError):
            return False
        return source.is_relative_to(root) and source.is_dir()

    active = [
        record for record in records
        if record.native_graph_binding is not None
        and record.native_graph_binding.status == "active"
        and record.source_root_relpath == world_source_root_relpath(record.world_id)
        and source_is_contained(record.source_root_relpath)
    ]
    if required_world:
        active = [record for record in active if record.world_id == required_world]
    if not active:
        return "managed_world_binding_unavailable"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-port", type=int, required=True)
    parser.add_argument("--api-port", type=int, required=True)
    parser.add_argument("--server-root", type=Path, required=True)
    parser.add_argument("--require-world")
    args = parser.parse_args(argv)
    if not 1 <= args.ui_port <= 65535 or not 1 <= args.api_port <= 65535:
        reason = "local_graph_port_invalid"
    else:
        reason = inspect_local_graph_profile(
            ui_port=args.ui_port,
            api_port=args.api_port,
            server_root=args.server_root,
            required_world=args.require_world,
        )
    if reason is not None:
        print(f"Local Graph access: NOT CONFIGURED ({reason})")
        print("Graph-backed answer: UNVERIFIED")
        return 1
    print("Local Graph access: CONFIGURED")
    print("Graph-backed answer: UNVERIFIED (requires a real authorized turn)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
