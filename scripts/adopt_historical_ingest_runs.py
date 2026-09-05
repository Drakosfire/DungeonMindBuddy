#!/usr/bin/env python3
"""Operator CLI for exact historical Ingest run adoption (DFC-2c).

Preview is the default. Writes require explicit --apply and the preview
target_set_sha256. Selection is exact --run-id or explicit --all-historical-ingest.
There is no implicit --all, campaign/session matching, latest, or --force.
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
from product_continuity.ingest_adoption import (  # noqa: E402
    IngestAdoptionInputError,
    IngestAdoptionReport,
    run_ingest_adoption,
    sanitize_operator_detail,
)


def _repo_root() -> Path:
    return _REPO_ROOT


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Adopt explicitly selected historical Ingest runs into the currently "
            "configured APP-STATE. Preview by default; --apply requires "
            "--expected-set-sha256 from a matching preview."
        )
    )
    parser.add_argument(
        "--historical-root",
        action="append",
        default=[],
        metavar="PATH",
        help="Historical repository/worktree root (repeatable)",
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
        "--run-id",
        action="append",
        dest="run_ids",
        default=None,
        metavar="ID",
        help="Exact Ingest run_id to adopt (repeatable)",
    )
    parser.add_argument(
        "--all-historical-ingest",
        action="store_true",
        help="Select every admitted historical Ingest identity under the supplied roots",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the importer write. Default is preview-only.",
    )
    parser.add_argument(
        "--expected-set-sha256",
        default=None,
        metavar="HEX",
        help="Required with --apply: preview target_set_sha256 for the write set",
    )
    parser.add_argument(
        "--current-root",
        type=Path,
        default=None,
        help="Current Buddy checkout root (default: repository containing this script)",
    )
    return parser.parse_args(argv)


def _print_report(report: IngestAdoptionReport) -> None:
    auth = report.authority
    mode = "apply" if report.mode == "apply" else "preview"
    print(f"Historical Ingest adoption ({mode})")
    print(
        f"  APP-STATE: configured={auth.app_state_configured} "
        f"readable={auth.app_state_readable} "
        f"db={auth.database_name}@{auth.host}:{auth.port} "
        f"schema={auth.schema_head_status}"
    )
    print(f"  current root: {report.current_repo_root}")
    print(f"  historical roots: {len(report.historical_roots)}")
    for root in report.historical_roots:
        print(f"    {root.get('label')}")
    print(f"  selected: {report.selected_count}")
    print(f"  target_set_sha256: {report.target_set_sha256}")
    print(f"  blocked: {'yes' if report.blocked else 'no'}")
    print(f"  applied: {'yes' if report.applied else 'no'}")
    if report.mode == "apply":
        print(f"  importer imported: {report.importer_imported}")
        print(f"  importer no-op: {report.importer_noop}")
        print(f"  importer conflict: {report.importer_conflict}")
        print(f"  product verification: {report.product_verification}")
        print(f"  unavailable components: {report.unavailable_component_count}")
    if report.historical_roots_unchanged is not None:
        print(f"  historical roots unchanged: {report.historical_roots_unchanged}")
    for row in report.dispositions:
        classification = row.classification or "ABSENT"
        fingerprint = (row.durable_fingerprint or "")[:16]
        print(
            f"  {row.run_id}  {classification}  {row.action}  "
            f"{row.campaign_id or ''}  {row.session_id or ''}  {fingerprint}".rstrip()
        )
        for reason in row.reason:
            print(f"    {reason}")
    if report.product_verification_detail:
        print(
            "  product verification detail: "
            f"{sanitize_operator_detail(report.product_verification_detail)}"
        )
    if report.detail:
        print(f"  detail: {sanitize_operator_detail(report.detail)}")


def main(argv: list[str] | None = None) -> int:
    load_dungeonmindbuddy_dotenv()
    args = _parse_args(argv)
    current_root = (args.current_root or _repo_root()).resolve()
    labels = list(args.historical_root_label or [])
    roots: list[tuple[str, Path]] = []
    for index, raw in enumerate(args.historical_root or []):
        path = Path(raw).expanduser().resolve()
        label = labels[index] if index < len(labels) else path.name
        roots.append((label, path))
    try:
        report = run_ingest_adoption(
            current_repo_root=current_root,
            historical_roots=roots,
            run_ids=list(args.run_ids) if args.run_ids else None,
            all_historical=bool(args.all_historical_ingest),
            apply=bool(args.apply),
            expected_set_sha256=args.expected_set_sha256,
        )
    except IngestAdoptionInputError as exc:
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
    if report.historical_roots_unchanged == "false":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
