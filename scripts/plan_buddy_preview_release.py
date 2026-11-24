#!/usr/bin/env python3
"""Produce a read-only plan for an isolated local Buddy release rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

_SHA = re.compile(r"[0-9a-f]{40}")
_IMAGE = re.compile(r"sha256:[0-9a-f]{64}")
_REQUEST = {
    "environment",
    "source_commit",
    "candidate_image_id",
    "expected_current_image_id",
}
_WITNESS = {"source_commit", "image_id", "network_mode", "live_status", "spa_status"}


def _read(path: Path) -> dict:
    def unique(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate field: {key}")
            result[key] = value
        return result

    with path.open("rb") as stream:
        content = stream.read(16_385)
    if len(content) > 16_384:
        raise ValueError("Rehearsal input exceeds 16 KiB")
    result = json.loads(content, object_pairs_hook=unique)
    if type(result) is not dict:
        raise ValueError("Expected a JSON object")
    return result


def _check_id(pattern: re.Pattern, value: object, label: str) -> None:
    if type(value) is not str or not pattern.fullmatch(value):
        raise ValueError(f"Invalid {label}")


def plan_release(request: dict, witness: dict, observed: str | None) -> dict:
    if request.keys() != _REQUEST or witness.keys() != _WITNESS:
        raise ValueError("Unexpected or missing rehearsal fields")
    if request["environment"] != "local-preview":
        raise ValueError("Only local-preview is supported")
    _check_id(_SHA, request["source_commit"], "source commit")
    _check_id(_IMAGE, request["candidate_image_id"], "candidate image ID")
    for value, label in (
        (request["expected_current_image_id"], "expected current image ID"),
        (observed, "observed current image ID"),
    ):
        if value is not None:
            _check_id(_IMAGE, value, label)
    if request["expected_current_image_id"] != observed:
        raise ValueError("Stale request: expected current image differs from observation")
    if (
        witness["source_commit"] != request["source_commit"]
        or witness["image_id"] != request["candidate_image_id"]
    ):
        raise ValueError("Preview evidence does not match the exact source and image")
    if witness["network_mode"] != "none" or any(
        type(witness[key]) is not int or witness[key] != 200
        for key in ("live_status", "spa_status")
    ):
        raise ValueError("Require network-disabled preview liveness and SPA success")
    encoded = json.dumps(
        {"request": request, "preview_witness": witness}, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return {
        "rehearsal_id": hashlib.sha256(encoded).hexdigest(),
        "mode": "dry-run",
        "request": request,
        "preview_witness": witness,
        "observed_current_image_id": observed,
        "prior_image_for_rehearsal": observed,
        "disposition": (
            "already_current"
            if observed == request["candidate_image_id"]
            else "ready_for_disposable_rehearsal"
        ),
        "mutation_performed": False,
        "production_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("preview_witness", type=Path)
    parser.add_argument(
        "--observed-current-image-id",
        required=True,
        help="Independent disposable target observation: exact Docker image ID or 'none'",
    )
    args = parser.parse_args(argv)
    observed = None if args.observed_current_image_id == "none" else args.observed_current_image_id
    try:
        plan = plan_release(_read(args.request), _read(args.preview_witness), observed)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"Rehearsal refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(plan, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
