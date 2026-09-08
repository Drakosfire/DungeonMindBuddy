#!/usr/bin/env python3
"""Operator CLI for broad exact C1/C2 source adoption into APP-STATE.

Preview is the default. Writes require --apply, the preview fingerprint, and a
revalidated World head.
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
from product_continuity.source_adoption import (  # noqa: E402
    SourceAdoptionInputError,
    SourceAdoptionReport,
    apply_source_adoption,
    preview_source_adoption,
)


def _repo_root() -> Path:
    return _REPO_ROOT


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Adopt exact recoverable C1/C2 source material into APP-STATE. "
            "Preview by default; --apply requires --expected-set-sha256."
        )
    )
    parser.add_argument("--world-id", required=True)
    parser.add_argument(
        "--campaign",
        action="append",
        dest="campaigns",
        required=True,
        metavar="ID",
        help="Campaign id to include (repeatable)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist ADOPTABLE_EXACT targets. Default is preview-only.",
    )
    parser.add_argument(
        "--expected-set-sha256",
        default=None,
        metavar="HEX",
        help="Required with --apply: preview source_target_set_sha256",
    )
    parser.add_argument(
        "--expected-world-head",
        default=None,
        metavar="REV",
        help="Required with --apply: World head observed during preview",
    )
    parser.add_argument(
        "--current-root",
        type=Path,
        default=None,
        help="Checkout used as the operator byte locator (default: this repository)",
    )
    return parser.parse_args(argv)


def _print_report(report: SourceAdoptionReport) -> None:
    mode = "apply" if report.mode == "apply" else "preview"
    print(f"Historical source adoption ({mode})")
    print(f"  world_id: {report.world_id}")
    print(f"  campaigns: {', '.join(report.campaign_ids)}")
    print(f"  world_head: {report.world_head or ''}")
    print(f"  ingest_runs: {report.ingest_run_count}")
    print(f"  claims: {report.claim_count}")
    print(f"  targets: {report.target_count}")
    print(f"  source_target_set_sha256: {report.source_target_set_sha256}")
    print(f"  blocked: {'yes' if report.blocked else 'no'}")
    print(f"  applied: {'yes' if report.applied else 'no'}")
    print(f"  newly_adopted: {report.newly_adopted}")
    print(f"  noop: {report.noop}")
    print(f"  skipped: {report.skipped}")
    print(f"  new_durable_identities: {report.new_durable_identities}")
    for name in sorted(report.counts):
        print(f"  {name}: {report.counts[name]}")
    for target in report.targets:
        digest = (target.content_sha256 or "")[:12]
        revision = target.source_revision_id or target.known_source_revision_id or ""
        print(
            f"  {target.source_artifact_id}  {digest}  {target.classification}  "
            f"{target.identity_kind}  {revision}".rstrip()
        )
        for reason in target.reason:
            print(f"    {reason}")
    if report.detail:
        print(f"  detail: {report.detail}")


def main(argv: list[str] | None = None) -> int:
    load_dungeonmindbuddy_dotenv(override=True)
    args = _parse_args(argv)
    repo_root = (args.current_root or _repo_root()).resolve()
    try:
        if args.apply:
            report = apply_source_adoption(
                repo_root=repo_root,
                world_id=args.world_id,
                campaign_ids=list(args.campaigns),
                expected_set_sha256=args.expected_set_sha256 or "",
                expected_world_head=args.expected_world_head,
            )
        else:
            report = preview_source_adoption(
                repo_root=repo_root,
                world_id=args.world_id,
                campaign_ids=list(args.campaigns),
            )
    except SourceAdoptionInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _print_report(report)
    if report.blocked:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
