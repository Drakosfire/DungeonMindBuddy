#!/usr/bin/env python3
"""CLI: deterministic Eldyrwild C2 acceptance-corpus inventory (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from graph_memory.materialization.acceptance_inventory import (
    AcceptanceInventoryError,
    build_acceptance_inventory,
    load_acceptance_manifest,
    write_acceptance_inventory,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("config/graph_memory/eldyrwild_c2_acceptance_inventory.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Write inventory JSON only to this path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    try:
        manifest = load_acceptance_manifest(manifest_path)
        report = build_acceptance_inventory(repo_root, manifest)
        write_acceptance_inventory(report, args.output.resolve())
    except AcceptanceInventoryError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "summary": dict(report.summary),
                "manifest_sha256": report.manifest_sha256,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
