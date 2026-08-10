#!/usr/bin/env python3
"""Status/apply the approved Session-24 Lysandra→Caelynn false-leads correction.

Usage:
  python scripts/apply_eldyrwild_session24_lysandra_caelynn_false_leads_correction.py \\
      status [--root PATH]
  python scripts/apply_eldyrwild_session24_lysandra_caelynn_false_leads_correction.py \\
      apply --expected-parent-revision-id REV [--root PATH] [--allow-live-world]
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

from apps.live_control_server.services.eldyrwild_session24_lysandra_caelynn_false_leads_correction import (  # noqa: E402
    Session24LysandraCaelynnFalseLeadsCorrectionError,
    apply_session24_lysandra_caelynn_false_leads_correction,
    get_session24_lysandra_caelynn_false_leads_correction_status,
)


def _print(model: object) -> None:
    payload = (
        model.model_dump(mode="json", by_alias=True)
        if hasattr(model, "model_dump")
        else model
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status")
    status.add_argument("--root", type=Path)
    status.add_argument("--expected-parent-revision-id", default=None)

    apply = sub.add_parser("apply")
    apply.add_argument("--root", type=Path)
    apply.add_argument("--expected-parent-revision-id", required=True)
    apply.add_argument(
        "--allow-live-world",
        action="store_true",
        help="Required when --root resolves to the canonical live world root",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            status = get_session24_lysandra_caelynn_false_leads_correction_status(
                root=args.root,
                expected_parent_revision_id=args.expected_parent_revision_id,
            )
            _print(status)
            if status.eligibility == "integrity_failure":
                return 1
            return 0
        result = apply_session24_lysandra_caelynn_false_leads_correction(
            expected_parent_revision_id=args.expected_parent_revision_id,
            root=args.root,
            allow_live_world=bool(args.allow_live_world),
        )
        _print(result)
        if result.eligibility == "already_applied" and not result.published:
            return 0
        if result.failure_code or not result.published:
            return 1
        return 0
    except Session24LysandraCaelynnFalseLeadsCorrectionError as exc:
        _print({"code": exc.code, "message": str(exc), "status_code": exc.status_code})
        return 1
    except ValueError as exc:
        _print({"code": "kernel_rejected", "message": str(exc), "status_code": 400})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
