#!/usr/bin/env python3
"""CLI for the Eldyrwild relationship semantic closure program.

Commands:
  status    Read-only closure status against the locked manifest.
  preflight Whole-ledger fail-closed verification against the exact Q4 base.
  apply     Apply the 55-unit closure program in manifest order (prefix-safe).
  verify    Verify post-closure head inventory (314/314/0/3) and unit states.
  finalize  Refuse nonzero residual; emit the live pin JSON on success.

Examples:
  uv run python scripts/apply_eldyrwild_relationship_semantic_closure.py status
  uv run python scripts/apply_eldyrwild_relationship_semantic_closure.py apply \
      --expected-base-revision-id rev:3759d8d6a02f09306397918234a2ded2
"""

from __future__ import annotations

import argparse
import json
import sys

from apps.live_control_server.services import (
    eldyrwild_relationship_semantic_closure as closure_service,
)
from apps.live_control_server.services.eldyrwild_relationship_semantic_closure import (
    BASE_REVISION_ID,
    RelationshipSemanticClosureError,
    apply_relationship_semantic_closure,
    finalize_relationship_semantic_closure,
    get_relationship_semantic_closure_status,
    verify_relationship_semantic_closure,
)


def _dump(payload: object) -> None:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(by_alias=True, mode="json")  # type: ignore[union-attr]
    print(json.dumps(payload, indent=1, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["status", "preflight", "apply", "verify", "finalize"]
    )
    parser.add_argument(
        "--expected-base-revision-id",
        default=None,
        help="Required for apply; must equal the exact Q4 base revision.",
    )
    parser.add_argument(
        "--allow-live-world",
        action="store_true",
        help="Permit mutation of the canonical live world graph root.",
    )
    args = parser.parse_args()

    try:
        if args.command == "status":
            _dump(get_relationship_semantic_closure_status())
            return 0
        if args.command == "preflight":
            manifest = closure_service._load_manifest()
            diagnostics = closure_service._preflight(
                root=closure_service._resolve_root(None),
                manifest=manifest,
                expected_base_revision_id=(
                    args.expected_base_revision_id or BASE_REVISION_ID
                ),
                repo=None,
            )
            _dump({"preflight_passed": not diagnostics, "diagnostics": diagnostics})
            return 0 if not diagnostics else 1
        if args.command == "apply":
            if not args.expected_base_revision_id:
                print(
                    "apply requires --expected-base-revision-id "
                    f"(exact Q4 base {BASE_REVISION_ID})",
                    file=sys.stderr,
                )
                return 2
            result = apply_relationship_semantic_closure(
                expected_base_revision_id=args.expected_base_revision_id,
                allow_live_world=args.allow_live_world,
            )
            _dump(result)
            return 0 if result.failed_unit_id is None and result.verify_passed else 1
        if args.command == "verify":
            pin = verify_relationship_semantic_closure()
            if pin is None:
                print("closure verify failed: head is not a clean closure exit")
                return 1
            _dump(pin)
            return 0
        if args.command == "finalize":
            pin = finalize_relationship_semantic_closure(
                allow_live_world=args.allow_live_world
            )
            _dump(pin)
            return 0
    except RelationshipSemanticClosureError as exc:
        print(f"error[{exc.code}]: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
