#!/usr/bin/env python3
"""Operator CLI for exact historical Plan adoption (DFC-2a).

Preview is the default. Writes require explicit --apply. Selection is exact
UUID only; there is no --all, title matching, session matching, latest, or
--force.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT), str(_REPO_ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from product_continuity.plan_adoption import (  # noqa: E402
    PlanAdoptionInputError,
    PlanAdoptionReport,
    run_plan_adoption,
)


def _repo_root() -> Path:
    return _REPO_ROOT


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Adopt explicitly selected historical Plans into the currently "
            "configured APP-STATE. Preview by default; --apply required to write."
        )
    )
    parser.add_argument(
        "--historical-root",
        required=True,
        metavar="PATH",
        help="Exactly one historical repository/worktree root (no implicit discovery)",
    )
    parser.add_argument(
        "--document-id",
        action="append",
        dest="document_ids",
        required=True,
        metavar="UUID",
        help="Exact Plan document UUID to adopt (repeatable)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the importer write. Default is preview-only.",
    )
    parser.add_argument(
        "--current-root",
        type=Path,
        default=None,
        help="Current Buddy checkout root (default: repository containing this script)",
    )
    return parser.parse_args(argv)


def _print_report(report: PlanAdoptionReport) -> None:
    auth = report.authority
    mode = "apply" if report.mode == "apply" else "preview"
    print(f"Historical Plan adoption ({mode})")
    print(
        f"  APP-STATE: configured={auth.app_state_configured} "
        f"readable={auth.app_state_readable} "
        f"db={auth.database_name}@{auth.host}:{auth.port} "
        f"schema={auth.schema_head_status}"
    )
    print(f"  current root: {report.current_repo_root}")
    print(f"  historical root: {report.historical_root}")
    print(f"  selected: {len(report.selected_ids)}")
    print(f"  blocked: {'yes' if report.blocked else 'no'}")
    print(f"  applied: {'yes' if report.applied else 'no'}")
    if report.mode == "apply":
        print(f"  importer imported: {report.importer_imported}")
        print(f"  importer no-op: {report.importer_noop}")
        print(f"  importer skipped empty: {report.importer_skipped_empty}")
        print(f"  product verification: {report.product_verification}")
    if report.historical_root_unchanged is not None:
        print(
            "  historical root unchanged: "
            f"{'yes' if report.historical_root_unchanged else 'NO'}"
        )
    for row in report.dispositions:
        classification = row.classification or "ABSENT"
        title = row.title or ""
        print(f"  {row.document_id}  {classification}  {row.action}  {title}".rstrip())
        for reason in row.reason:
            print(f"    {reason}")
    if report.product_verification_detail:
        print(f"  product verification detail: {report.product_verification_detail}")
    if report.detail:
        print(f"  detail: {report.detail}")


def main(argv: list[str] | None = None) -> int:
    load_dungeonmindbuddy_dotenv()
    args = _parse_args(argv)
    current_root = (args.current_root or _repo_root()).resolve()
    historical_root = Path(args.historical_root).expanduser().resolve()
    try:
        report = run_plan_adoption(
            current_repo_root=current_root,
            historical_root=historical_root,
            document_ids=list(args.document_ids),
            apply=bool(args.apply),
        )
    except PlanAdoptionInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _print_report(report)
    if report.blocked:
        return 2
    if report.product_verification == "failed":
        return 2
    if report.historical_root_unchanged is False:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
