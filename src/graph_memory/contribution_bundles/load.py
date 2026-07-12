"""Load checksum-locked GraphContribution bundles without graph writes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from graph_memory.contribution_bundles.models import (
    ContributionBundleManifest,
    LoadedContributionBundle,
)
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.identity_models import IdentityDecisionRecord


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _resolve_inside_bundle(bundle_path: Path, relative: str) -> Path:
    if not relative or relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError(f"path escapes bundle root: {relative!r}")
    resolved = (bundle_path / relative).resolve()
    bundle_root = bundle_path.resolve()
    if not resolved.is_relative_to(bundle_root):
        raise ValueError(f"path escapes bundle root: {relative!r}")
    return resolved


def compute_bundle_digest(manifest_payload: dict[str, Any]) -> str:
    """Digest of the manifest payload excluding ``bundle_digest`` itself."""
    payload = {
        key: value for key, value in manifest_payload.items() if key != "bundle_digest"
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return _sha256_bytes(canonical.encode("utf-8"))


def load_contribution_bundle(bundle_path: Path) -> LoadedContributionBundle:
    """Load and checksum-verify a contribution bundle. Performs no graph writes."""
    root = bundle_path.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"bundle directory not found: {root}")

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json missing under {root}")

    raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw_manifest, dict):
        raise ValueError("manifest.json must be a JSON object")

    expected_digest = raw_manifest.get("bundle_digest")
    if not isinstance(expected_digest, str) or not expected_digest.strip():
        raise ValueError("bundle_digest is required and must be a non-empty string")
    computed_digest = compute_bundle_digest(raw_manifest)
    if expected_digest != computed_digest:
        raise ValueError(
            "bundle_digest mismatch: "
            f"manifest={expected_digest!r} computed={computed_digest!r}"
        )

    manifest = ContributionBundleManifest.model_validate(raw_manifest)

    contributions_dir = root / "contributions"
    if contributions_dir.is_dir():
        listed = {entry.path for entry in manifest.ordered_contributions}
        for child in sorted(contributions_dir.glob("*.json")):
            relative = f"contributions/{child.name}"
            if relative not in listed:
                raise ValueError(f"unlisted contribution file: {relative}")

    contributions: list[GraphContribution] = []
    seen_paths: set[str] = set()
    seen_ids: set[str] = set()
    for entry in manifest.ordered_contributions:
        if entry.path in seen_paths:
            raise ValueError(f"duplicate contribution path: {entry.path}")
        if entry.contribution_id in seen_ids:
            raise ValueError(f"duplicate contribution_id: {entry.contribution_id}")
        seen_paths.add(entry.path)
        seen_ids.add(entry.contribution_id)

        file_path = _resolve_inside_bundle(root, entry.path)
        if not file_path.is_file():
            raise FileNotFoundError(f"contribution file missing: {entry.path}")
        raw_bytes = file_path.read_bytes()
        digest = _sha256_bytes(raw_bytes)
        if digest != entry.sha256:
            raise ValueError(
                f"sha256 mismatch for {entry.path}: "
                f"manifest={entry.sha256!r} file={digest!r}"
            )
        payload = json.loads(raw_bytes.decode("utf-8"))
        contribution = GraphContribution.model_validate(payload)
        if contribution.contribution_id != entry.contribution_id:
            raise ValueError(
                f"contribution_id mismatch for {entry.path}: "
                f"manifest={entry.contribution_id!r} "
                f"record={contribution.contribution_id!r}"
            )
        contributions.append(contribution)

    identity_records: list[IdentityDecisionRecord] = []
    for decision_id in manifest.identity_decisions:
        raise ValueError(
            "PR006C initial bundle does not embed identity decision payloads; "
            f"unexpected identity_decisions entry: {decision_id!r}"
        )

    return LoadedContributionBundle(
        bundle_path=root,
        manifest=manifest,
        contributions=contributions,
        identity_decision_records=identity_records,
    )
