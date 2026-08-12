#!/usr/bin/env -S uv run python
"""Status/build/verify CLI for the non-publishing Eldyrwild repair authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
    RelationshipNodeKindSourceRepairError,
    build_relationship_node_kind_source_repair,
    get_relationship_node_kind_source_repair_status,
    verify_relationship_node_kind_source_repair,
)


def _path(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and verify the non-publishing Eldyrwild node-kind repair."
    )
    parser.add_argument("command", choices=("status", "build", "verify"))
    parser.add_argument("--root", help="world graph root (defaults to environment)")
    parser.add_argument("--repo", help="repository root (defaults to this repository)")
    parser.add_argument(
        "--allow-live-world",
        action="store_true",
        help="no-op guard acknowledgement; this CLI never mutates the graph",
    )
    args = parser.parse_args(argv)
    root = _path(args.root)
    repo = _path(args.repo)

    try:
        if args.command == "status":
            value = get_relationship_node_kind_source_repair_status(root, repo=repo)
            print(value.model_dump_json(by_alias=True, indent=2))
            return 0 if value.eligibility == "eligible" else 1
        if args.command == "build":
            value = build_relationship_node_kind_source_repair(
                root=root,
                repo=repo,
                allow_live_world=args.allow_live_world,
            )
            print(value.model_dump_json(by_alias=True, indent=2))
            return 0
        value = verify_relationship_node_kind_source_repair(root=root, repo=repo)
        if value is None:
            print(
                json.dumps(
                    {
                        "repair_id": (
                            "eldyrwild-relationship-node-kind-source-repair-v1"
                        ),
                        "verified": False,
                    },
                    indent=2,
                )
            )
            return 1
        print(value.model_dump_json(by_alias=True, indent=2))
        return 0
    except RelationshipNodeKindSourceRepairError as exc:
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
