#!/usr/bin/env python3
"""Buddy APP-STATE durable-authority operator entry point.

Supported operations against the durable local APP-STATE authority
(`compose.postgres.app-state.yml`):

  check       Status + fingerprint. OBSERVED unless --expect-fingerprint;
              schema-at-head alone is never READY.
  fingerprint Compute (and optionally write) the deterministic fingerprint.
  backup      External custom-format pg_dump + SHA-256 + fingerprint sidecars.
  restore     Verify dump SHA-256, restore into a second clean target, require
              fingerprint parity. Missing digest or expected fingerprint refuses.
  verify      Fingerprint two DSNs and report READY / NOT_READY.

Exit codes: 0 = READY/success, 2 = NOT_READY/blocked/error.
All output is secret-redacted. Runbook:
Docs/Runbooks/RUNBOOK-application-state-authority-recovery.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from application_state.authority import (  # noqa: E402
    ApplicationStateFingerprint,
    backup_authority,
    compare_fingerprints,
    compute_fingerprint,
    redact_dsn,
    redact_secrets,
    restore_authority,
    verify_parity,
)
from application_state.config import load_runtime_dsn  # noqa: E402
from application_state.errors import ApplicationStateError  # noqa: E402


def _resolve_dsn(flag: str | None) -> str:
    return flag or load_runtime_dsn()


def _print_fingerprint(fp: ApplicationStateFingerprint, *, dsn: str) -> None:
    print(f"dsn: {redact_dsn(dsn)}")
    print(f"alembic: current={fp.alembic_current} head={fp.alembic_head}")
    for domain in fp.domains:
        print(f"  {domain.name}: rows={domain.row_count} digest={domain.digest[:12]}…")
    print(f"fingerprint: {fp.digest}")


def _load_fingerprint(path: str) -> ApplicationStateFingerprint:
    return ApplicationStateFingerprint.from_json_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def _cmd_check(args: argparse.Namespace) -> int:
    dsn = _resolve_dsn(args.dsn)
    fp = compute_fingerprint(dsn)
    _print_fingerprint(fp, dsn=dsn)
    if not args.expect_fingerprint:
        print("OBSERVED: authority reachable, schema at head, fingerprint computed")
        print("READY requires --expect-fingerprint (schema-at-head alone is never READY)")
        return 0
    expected = _load_fingerprint(args.expect_fingerprint)
    mismatches = compare_fingerprints(expected, fp)
    if mismatches:
        print("NOT_READY: live fingerprint does not match expected:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  - {mismatch}", file=sys.stderr)
        return 2
    print("READY: live fingerprint matches expected")
    return 0


def _cmd_fingerprint(args: argparse.Namespace) -> int:
    dsn = _resolve_dsn(args.dsn)
    fp = compute_fingerprint(dsn)
    if args.out:
        Path(args.out).write_text(fp.to_json(), encoding="utf-8")
        print(f"fingerprint written: {args.out}")
    _print_fingerprint(fp, dsn=dsn)
    return 0


def _cmd_backup(args: argparse.Namespace) -> int:
    source = _resolve_dsn(args.source_dsn)
    record = backup_authority(source_dsn=source, out_path=args.out)
    print(f"source: {record.source}")
    print(f"backup: {record.backup_path}")
    print(f"backup sha256: {record.backup_sha256}")
    print(f"sidecars: {record.backup_path}.sha256, {record.backup_path}.fingerprint.json")
    _print_fingerprint(record.fingerprint, dsn=source)
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    target = _resolve_dsn(args.target_dsn)
    expect = (
        _load_fingerprint(args.expect_fingerprint) if args.expect_fingerprint else None
    )
    report = restore_authority(
        target_dsn=target,
        backup_path=args.backup,
        source_dsn=args.source_dsn,
        expect_fingerprint=expect,
        expected_sha256=args.expect_sha256,
    )
    print(f"target: {report.target}")
    _print_fingerprint(report.fingerprint, dsn=target)
    if report.ready:
        print("READY: backup SHA-256 verified; restored fingerprint matches expected")
        return 0
    print("NOT_READY: fingerprint mismatch after restore:", file=sys.stderr)
    for mismatch in report.mismatches:
        print(f"  - {mismatch}", file=sys.stderr)
    return 2


def _cmd_verify(args: argparse.Namespace) -> int:
    source = _resolve_dsn(args.source_dsn)
    target = _resolve_dsn(args.target_dsn)
    ready, mismatches, source_fp, target_fp = verify_parity(
        source_dsn=source, target_dsn=target
    )
    print(f"source: {redact_dsn(source)} fingerprint={source_fp.digest}")
    print(f"target: {redact_dsn(target)} fingerprint={target_fp.digest}")
    if ready:
        print("READY: source and target fingerprints are identical")
        return 0
    print("NOT_READY: fingerprints differ:", file=sys.stderr)
    for mismatch in mismatches:
        print(f"  - {mismatch}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser(
        "check",
        help="redacted authority status + fingerprint; READY only with --expect-fingerprint",
    )
    check.add_argument("--dsn", default=None)
    check.add_argument(
        "--expect-fingerprint",
        default=None,
        help="trusted fingerprint JSON; without this, check is OBSERVED never READY",
    )
    check.set_defaults(func=_cmd_check)

    fingerprint = commands.add_parser("fingerprint", help="compute the fingerprint")
    fingerprint.add_argument("--dsn", default=None)
    fingerprint.add_argument("--out", default=None, help="write fingerprint JSON here")
    fingerprint.set_defaults(func=_cmd_fingerprint)

    backup = commands.add_parser("backup", help="external custom-format backup")
    backup.add_argument("--source-dsn", default=None)
    backup.add_argument("--out", required=True, help="dump file path")
    backup.set_defaults(func=_cmd_backup)

    restore = commands.add_parser("restore", help="restore into a second clean target")
    restore.add_argument("--target-dsn", default=None)
    restore.add_argument("--backup", required=True, help="dump file path")
    restore.add_argument("--source-dsn", default=None, help="isolation cross-check")
    restore.add_argument(
        "--expect-fingerprint",
        default=None,
        help="trusted fingerprint JSON (defaults to <dump>.fingerprint.json sidecar)",
    )
    restore.add_argument(
        "--expect-sha256",
        default=None,
        help="trusted dump digest (defaults to <dump>.sha256 sidecar; sidecar required if omitted)",
    )
    restore.set_defaults(func=_cmd_restore)

    verify = commands.add_parser("verify", help="compare two authority fingerprints")
    verify.add_argument("--source-dsn", default=None)
    verify.add_argument("--target-dsn", required=True)
    verify.set_defaults(func=_cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    from bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    args = build_parser().parse_args(argv)
    involved = [
        getattr(args, "dsn", None),
        getattr(args, "source_dsn", None),
        getattr(args, "target_dsn", None),
    ]
    try:
        return int(args.func(args))
    except ApplicationStateError as exc:
        print(redact_secrets(str(exc), *involved), file=sys.stderr)
        return 2
    except Exception as exc:  # operator CLI: fail closed with redacted output
        print(
            redact_secrets(f"unexpected failure: {exc}", *involved),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
