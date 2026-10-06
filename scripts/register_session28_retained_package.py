#!/usr/bin/env python3
"""Preview or register the pinned retained Session 28 review package.

Preview is read-only and is the default. Registration requires ``--apply``
and the exact fingerprint emitted by the current preview.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT), str(_REPO_ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from apps.live_control_server.services.session28_retained_package_registration import (  # noqa: E402
    RetainedPackageRegistrationError,
    preview_retained_package,
    register_retained_package,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Register the retained run; requires the exact current preview fingerprint.",
    )
    parser.add_argument(
        "--expected-preview-fingerprint",
        metavar="SHA256",
        help="Fingerprint returned by a current preview; required with --apply.",
    )
    args = parser.parse_args(argv)

    if args.apply and not args.expected_preview_fingerprint:
        parser.error("--apply requires --expected-preview-fingerprint from a preview")
    if not args.apply and args.expected_preview_fingerprint:
        parser.error("--expected-preview-fingerprint is only valid with --apply")

    try:
        if args.apply:
            payload = register_retained_package(
                package_root=args.package_root,
                inventory_path=args.inventory,
                repo_root=_REPO_ROOT,
                expected_preview_fingerprint=args.expected_preview_fingerprint,
            )
        else:
            payload = preview_retained_package(
                package_root=args.package_root,
                inventory_path=args.inventory,
            ).as_preview()
    except RetainedPackageRegistrationError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
