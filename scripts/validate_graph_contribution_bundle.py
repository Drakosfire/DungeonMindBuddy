#!/usr/bin/env python3
"""Validate an approved GraphContribution bundle (PR006C). No world publication."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure src/ is importable when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from graph_memory.contribution_bundles import (  # noqa: E402
    load_contribution_bundle,
    validate_contribution_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load and validate a checksum-locked GraphContribution bundle."
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="Path to the bundle directory containing manifest.json",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        required=True,
        help="Destination path for the machine-readable validation report",
    )
    args = parser.parse_args()

    try:
        bundle = load_contribution_bundle(args.bundle)
        report = validate_contribution_bundle(bundle)
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        payload = {
            "ok": False,
            "validation_errors": [f"load_or_validate_failed: {exc}"],
            "bundle_path": str(args.bundle),
        }
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    payload = report.model_dump(mode="json")
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"bundle_id: {report.bundle_id}")
    print(f"bundle_digest: {report.bundle_digest}")
    print(f"world_id: {report.world_id}")
    print(f"contributions: {report.contribution_count}")
    print(f"accepted_assertions: {report.accepted_assertion_count}")
    print(f"nodes_required: {report.required_node_count}")
    print(f"edges_required: {report.required_edge_count}")
    print(f"source_domains: {', '.join(report.source_domains)}")
    print(f"ok: {report.ok}")
    if report.validation_errors:
        print("errors:")
        for error in report.validation_errors:
            print(f"  - {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
