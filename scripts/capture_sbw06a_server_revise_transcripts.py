#!/usr/bin/env python3
"""Verify SBW06a Server revise fixtures (copied, reviewed — not live-captured).

These fixtures were copied from DungeonMindServer PR #24
(``Docs/Design/fixtures/dungeonbuddy-statblock-v1-api/``) at the merge commit
recorded in MANIFEST.json, then reviewed for StrictModel validity and
request/response coherence.

This script does **not** regenerate fixtures from a live Server. It fail-closes
if MANIFEST provenance or on-disk digests drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EXPECTED_SCHEMA = "sbw06a_server_revise_transcript_manifest_v1"
EXPECTED_PROVENANCE = "copied_reviewed_server_fixtures"
FIXTURE_NAMES = (
    "revise-request.json",
    "revise-replay-response.json",
    "revise-conflict-response.json",
)


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify copied/reviewed SBW06a Server revise fixtures against MANIFEST.json"
        )
    )
    parser.add_argument(
        "--buddy-repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    buddy = args.buddy_repo.resolve()
    fixture_dir = buddy / "tests/fixtures/statblocks/v1/server_revise_transcripts"
    manifest_path = fixture_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise SystemExit(
            f"Unexpected manifest schema: {manifest.get('schema')!r} "
            f"(expected {EXPECTED_SCHEMA!r})"
        )
    if manifest.get("provenance") != EXPECTED_PROVENANCE:
        raise SystemExit(
            f"Unexpected provenance: {manifest.get('provenance')!r} "
            f"(expected {EXPECTED_PROVENANCE!r}). "
            "These are copied reviewed Server fixtures, not live transcripts."
        )

    digests = manifest.get("transcripts") or {}
    errors: list[str] = []
    for name in FIXTURE_NAMES:
        path = fixture_dir / name
        if not path.is_file():
            errors.append(f"missing fixture: {name}")
            continue
        key = name.removesuffix(".json")
        expected = digests.get(key)
        observed = _sha256_file(path)
        if expected != observed:
            errors.append(
                f"digest mismatch for {name}: manifest={expected} observed={observed}"
            )

    openapi_path = (
        buddy
        / "apps/live_control_server/integrations/dungeonmind_statblocks/openapi"
        / "dungeonbuddy-statblocks-v1.json"
    )
    if openapi_path.is_file():
        from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
            OPENAPI_FINGERPRINT,
        )

        buddy_fp = manifest.get("buddy_vendored_openapi_fingerprint")
        if buddy_fp != OPENAPI_FINGERPRINT:
            errors.append(
                "MANIFEST buddy_vendored_openapi_fingerprint does not match "
                f"generated OPENAPI_FINGERPRINT ({buddy_fp} != {OPENAPI_FINGERPRINT})"
            )
        server_fp = (manifest.get("dungeonmind_server") or {}).get("openapi_fingerprint")
        if server_fp != OPENAPI_FINGERPRINT:
            errors.append(
                "MANIFEST server openapi_fingerprint does not match Buddy fingerprint"
            )

    if errors:
        raise SystemExit("Fixture verification failed:\n- " + "\n- ".join(errors))

    print(
        "OK: SBW06a revise fixtures verified as copied_reviewed_server_fixtures "
        f"under {fixture_dir}"
    )


if __name__ == "__main__":
    # Allow importing Buddy generated fingerprint when run via uv from repo root.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
