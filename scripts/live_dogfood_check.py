#!/usr/bin/env python3
"""Read-only local readiness checks for the statblock/combat dogfood run."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from importlib import import_module
from pathlib import Path

SESSION_DIR_ENV = "DUNGEONMIND_LIVE_SESSION_DIR"
EXPECTED_MODULES = ("statblock_workbench", "statblock_view", "combat_roster")


def _status(ok: bool) -> str:
    return "ok" if ok else "missing"


def check_imports() -> bool:
    ok = True
    for module in ("dotenv", "fastapi", "uvicorn"):
        try:
            import_module(module)
            print(f"backend import {module}: ok")
        except Exception as exc:  # pragma: no cover - diagnostic CLI path
            ok = False
            print(f"backend import {module}: failed ({exc})")
    return ok


def check_session(session_dir: Path) -> bool:
    ok = True
    print(f"session dir: {session_dir.resolve(strict=False)}")
    for rel in ("live_packet.json", "surface_layout.json"):
        exists = (session_dir / rel).is_file()
        ok = ok and exists
        print(f"{rel}: {_status(exists)}")

    layout_path = session_dir / "surface_layout.json"
    if layout_path.is_file():
        try:
            data = json.loads(layout_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            ok = False
            print(f"surface_layout.json: invalid JSON ({exc.msg} at line {exc.lineno}, column {exc.colno})")
        else:
            modules = {row.get("module_id"): row for row in data.get("modules", []) if isinstance(row, dict)}
            for module_id in EXPECTED_MODULES:
                row = modules.get(module_id)
                if row is None:
                    ok = False
                    print(f"module {module_id}: missing from surface_layout.json")
                else:
                    state = "enabled" if row.get("enabled") else "present but disabled"
                    print(f"module {module_id}: {state}")

    for rel in (
        "statblock_drafts",
        "statblock_retrieval/generated_statblocks_manifest.json",
        "combat/current_combat.json",
    ):
        print(f"artifact {rel}: {_status((session_dir / rel).exists())}")
    return ok


def check_ui_package(repo_root: Path) -> bool:
    package_path = repo_root / "apps/live-control-ui/package.json"
    if not package_path.is_file():
        print("UI package.json: missing")
        return False
    package = json.loads(package_path.read_text(encoding="utf-8"))
    has_types_node = "@types/node" in package.get("devDependencies", {})
    print(f"UI @types/node devDependency: {_status(has_types_node)}")
    return has_types_node


def check_http(server_url: str) -> bool:
    url = server_url.rstrip("/") + "/api/live/combat/current"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            print(f"HTTP {url}: {response.status}")
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"HTTP {url}: failed ({exc})")
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", help=f"Live session directory; defaults to {SESSION_DIR_ENV}.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to the current working directory.")
    parser.add_argument("--server-url", help="Optional backend URL for read-only HTTP smoke checks.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve(strict=False)
    session_dir = Path(args.session_dir or os.environ.get(SESSION_DIR_ENV, "evals/c2_live_prep/live/session_22"))
    if not session_dir.is_absolute():
        session_dir = repo_root / session_dir

    ok = True
    ok = check_imports() and ok
    ok = check_session(session_dir) and ok
    ok = check_ui_package(repo_root) and ok
    if args.server_url:
        ok = check_http(args.server_url) and ok

    print("\nStartup commands:")
    print("export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22")
    print("uv run uvicorn apps.live_control_server.main:app --reload")
    print("cd apps/live-control-ui && npm run dev")
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
