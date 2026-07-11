"""Tests for acceptance manifest inventory (PR006)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from graph_memory.materialization.acceptance_manifest import (
    AcceptanceManifestError,
    build_inventory,
    load_acceptance_manifest,
    sha256_file,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "config/graph_memory/eldyrwild_c2_acceptance_manifest.json"
MINIMAL_MANIFEST = (
    REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_acceptance_manifest.json"
)


def test_load_acceptance_manifest_schema() -> None:
    manifest = load_acceptance_manifest(MANIFEST)
    assert manifest["world_id"] == "eldyrwild"
    assert manifest["campaign_scope"] == "longmont-c2"


def test_inventory_excludes_archive_recaps() -> None:
    inventory = build_inventory(
        load_acceptance_manifest(MANIFEST),
        repo_root=REPO_ROOT,
        manifest_path=MANIFEST,
    )
    paths = [item["path"] for item in inventory["source_items"] if item["domain"] == "recap"]
    assert all("_archive" not in path for path in paths)
    assert inventory["recap_count"] == 23
    assert inventory["recap_session_numbers"] == list(range(1, 24))


def test_inventory_requires_exactly_one_recap_per_session() -> None:
    manifest = load_acceptance_manifest(MINIMAL_MANIFEST)
    inventory = build_inventory(
        manifest,
        repo_root=REPO_ROOT,
        manifest_path=MINIMAL_MANIFEST,
    )
    assert inventory["recap_count"] == 2


def test_inventory_missing_required_fails_closed(tmp_path: Path) -> None:
    manifest = load_acceptance_manifest(MINIMAL_MANIFEST)
    manifest = json.loads(json.dumps(manifest))
    manifest["required_world_roots"] = ["corpus/missing/world/root"]
    with pytest.raises(AcceptanceManifestError) as exc:
        build_inventory(manifest, repo_root=REPO_ROOT, manifest_path=MINIMAL_MANIFEST)
    assert exc.value.errors


def test_sha256_file_prefix() -> None:
    digest = sha256_file(MANIFEST)
    assert digest.startswith("sha256:")
    assert len(digest) == 7 + 64
