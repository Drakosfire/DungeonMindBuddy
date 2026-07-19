#!/usr/bin/env python3
"""Apply the approved Campaign 1 additive World Graph bundle onto an existing head.

Requires the Eldyrwild C2 bootstrap to already be active.

Usage:
  python scripts/apply_eldyrwild_c1_additive_bundle.py status [--root PATH]
  python scripts/apply_eldyrwild_c1_additive_bundle.py apply --actor gm [--root PATH]
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

from apps.live_control_server.services.c1_world_graph_additive_apply import (  # noqa: E402
    C1AdditiveApplyError,
    apply_approved_c1_additive_bundle,
    get_c1_additive_apply_status,
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

    apply = sub.add_parser("apply")
    apply.add_argument("--root", type=Path)
    apply.add_argument("--actor", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            _print(get_c1_additive_apply_status(root=args.root))
            return 0
        _print(apply_approved_c1_additive_bundle(actor=args.actor, root=args.root))
        return 0
    except C1AdditiveApplyError as exc:
        _print({"code": exc.code, "message": str(exc), "status_code": exc.status_code})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
