#!/usr/bin/env python3
"""Canonical assembled-runtime preflight entry point (SURFACE-INTEGRATION SI-1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.live_control_server.services.runtime_preflight import (  # noqa: E402
    format_runtime_preflight_report,
    run_runtime_preflight,
)
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report assembled DungeonBuddy runtime foundation readiness."
    )
    parser.add_argument(
        "--require-world",
        metavar="WORLD_ID",
        help="Fail when the named world is absent from the mounted authority database.",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Do not load repo .env / .env.development before checks.",
    )
    args = parser.parse_args(argv)

    if not args.no_dotenv:
        load_dungeonmindbuddy_dotenv()

    report = run_runtime_preflight(
        repo_root=_REPO_ROOT,
        require_world=args.require_world,
        load_env=not args.no_dotenv,
    )
    sys.stdout.write(format_runtime_preflight_report(report))
    return 0 if report.status == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
