#!/usr/bin/env -S uv run python
"""Status/build/verify CLI for CUTOVER alias assertion package after PR #575."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.live_control_server.services.cutover_alias_assertion_package_after_575 import (  # noqa: E402
    CutoverAliasAssertionPackageAfter575Error,
    build_cutover_alias_assertion_package_after_575,
    get_cutover_alias_assertion_package_after_575_status,
    verify_cutover_alias_assertion_package_after_575,
)


def _path(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and verify the non-publishing CUTOVER alias assertion "
            "package after PR #575."
        )
    )
    parser.add_argument("command", choices=("status", "build", "verify"))
    parser.add_argument("--root", help="world graph root (defaults to environment)")
    parser.add_argument("--repo", help="repository root (defaults to this repository)")
    parser.add_argument(
        "--allow-live-world",
        action="store_true",
        help="no-op observation acknowledgement; this CLI never mutates the graph",
    )
    args = parser.parse_args(argv)
    root = _path(args.root)
    repo = _path(args.repo)

    try:
        if args.command == "status":
            value = get_cutover_alias_assertion_package_after_575_status(
                root, repo=repo
            )
            print(value.model_dump_json(by_alias=True, indent=2))
            return 0 if value.eligibility == "eligible" else 1
        if args.command == "build":
            value = build_cutover_alias_assertion_package_after_575(
                root=root,
                repo=repo,
                allow_live_world=args.allow_live_world,
            )
            print(value.model_dump_json(by_alias=True, indent=2))
            return 0
        value = verify_cutover_alias_assertion_package_after_575(
            root=root, repo=repo
        )
        print(value.model_dump_json(by_alias=True, indent=2))
        return 0 if value.verified else 1
    except CutoverAliasAssertionPackageAfter575Error as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "code": exc.code,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
