#!/usr/bin/env python3
"""Operator CLI for read-only historical product continuity inventory (DFC-1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from product_continuity.inventory import render_markdown, run_inventory  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402


def _repo_root() -> Path:
    return _REPO_ROOT


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare current DungeonBuddy product authorities with explicitly "
            "supplied historical roots. Read-only; never migrates."
        )
    )
    parser.add_argument(
        "--historical-root",
        action="append",
        default=[],
        metavar="PATH",
        help="Historical repository/worktree root to inspect (repeatable)",
    )
    parser.add_argument(
        "--historical-root-label",
        action="append",
        default=[],
        metavar="LABEL",
        help=(
            "Optional sanitized label for the corresponding --historical-root "
            "(repeatable, positional match). Defaults to the directory name."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out/product_continuity"),
        help="Directory for inventory.json and inventory.md (default: out/product_continuity)",
    )
    parser.add_argument(
        "--current-root",
        type=Path,
        default=None,
        help="Current Buddy checkout root (default: repository containing this script)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dungeonmindbuddy_dotenv()
    args = _parse_args(argv)
    current_root = (args.current_root or _repo_root()).resolve()
    labels = list(args.historical_root_label)
    roots: list[tuple[str, Path]] = []
    for index, raw in enumerate(args.historical_root):
        path = Path(raw).expanduser().resolve()
        label = labels[index] if index < len(labels) else path.name
        roots.append((label, path))

    try:
        report = run_inventory(current_repo_root=current_root, historical_roots=roots)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (current_root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "inventory.json"
    md_path = output_dir / "inventory.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    auth = report.authority
    print("Product continuity inventory")
    print(
        f"  APP-STATE: configured={auth.app_state_configured} "
        f"readable={auth.app_state_readable} "
        f"db={auth.database_name}@{auth.host}:{auth.port} "
        f"schema={auth.schema_head_status}"
    )
    print(f"  current root: {auth.current_repo_root}")
    print(f"  build registry: {auth.current_build_registry_locator}")
    print(f"  historical roots: {len(report.historical_roots)}")
    print(f"  items: {len(report.items)}")
    if report.classification_counts:
        counts = ", ".join(
            f"{key}={value}" for key, value in report.classification_counts.items()
        )
        print(f"  classifications: {counts}")
    else:
        print("  classifications: (none)")
    print(f"  incomplete: {report.incomplete}")
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")
    return 2 if report.incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
