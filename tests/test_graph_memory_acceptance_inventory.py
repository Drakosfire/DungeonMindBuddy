"""Tests for read-only Eldyrwild C2 acceptance inventory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from graph_memory.materialization.acceptance_inventory import (
    AcceptanceInventoryError,
    build_acceptance_inventory,
    load_acceptance_manifest,
    write_acceptance_inventory,
)

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "config/graph_memory/eldyrwild_c2_acceptance_inventory.json"
CLI = REPO / "scripts/inventory_eldyrwild_c2_acceptance.py"


def _write_manifest(tmp: Path, payload: dict) -> Path:
    path = tmp / "manifest.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _mini_corpus(tmp: Path) -> Path:
    root = tmp / "corpus" / "eldyrwild-markdown"
    (root / "recaps").mkdir(parents=True)
    (root / "pcs" / "alpha").mkdir(parents=True)
    (root / "optional").mkdir(parents=True)
    (root / "recaps" / "s1.md").write_text("one\n", encoding="utf-8")
    (root / "pcs" / "alpha" / "hub.md").write_text("pc\n", encoding="utf-8")
    (root / "optional" / "note.md").write_text("opt\n", encoding="utf-8")
    return root


def _base_payload() -> dict:
    return {
        "schema": "dmb_world_acceptance_inventory_manifest_v1",
        "version": "1.0",
        "world_id": "eldyrwild",
        "campaign_id": "longmont-c2",
        "corpus_root": "corpus/eldyrwild-markdown",
        "families": [
            {
                "family_id": "canonical_recaps",
                "required": True,
                "reason": "recaps",
                "selection": {"files": ["recaps/s1.md"]},
            },
            {
                "family_id": "pc_hubs",
                "required": True,
                "reason": "pcs",
                "selection": {
                    "roots": ["pcs/alpha"],
                    "glob": "**/*.md",
                    "minimum_per_root": 1,
                },
            },
            {
                "family_id": "support",
                "required": False,
                "reason": "optional support",
                "selection": {"roots": ["optional"], "glob": "**/*.md"},
            },
        ],
    }


def test_strict_manifest_validation(tmp_path: Path) -> None:
    bad = _base_payload()
    bad["schema"] = "nope"
    path = _write_manifest(tmp_path, bad)
    with pytest.raises(AcceptanceInventoryError, match="unsupported manifest schema"):
        load_acceptance_manifest(path)


def test_exact_file_and_root_glob_expansion(tmp_path: Path) -> None:
    _mini_corpus(tmp_path)
    manifest = load_acceptance_manifest(_write_manifest(tmp_path, _base_payload()))
    report = build_acceptance_inventory(tmp_path, manifest)
    paths = [item.path for item in report.sources]
    assert paths == sorted(paths)
    assert "corpus/eldyrwild-markdown/recaps/s1.md" in paths
    assert "corpus/eldyrwild-markdown/pcs/alpha/hub.md" in paths
    assert "corpus/eldyrwild-markdown/optional/note.md" in paths
    assert report.summary["required_missing_count"] == 0


def test_required_missing_fails(tmp_path: Path) -> None:
    _mini_corpus(tmp_path)
    payload = _base_payload()
    payload["families"][0]["selection"]["files"] = ["recaps/missing.md"]
    manifest = load_acceptance_manifest(_write_manifest(tmp_path, payload))
    with pytest.raises(AcceptanceInventoryError, match="required file missing"):
        build_acceptance_inventory(tmp_path, manifest)


def test_optional_missing_is_diagnostic(tmp_path: Path) -> None:
    _mini_corpus(tmp_path)
    payload = _base_payload()
    payload["families"][2]["selection"]["roots"] = ["optional-missing"]
    manifest = load_acceptance_manifest(_write_manifest(tmp_path, payload))
    report = build_acceptance_inventory(tmp_path, manifest)
    assert report.summary["required_missing_count"] == 0
    assert any(item.code == "optional_root_missing" for item in report.diagnostics)


def test_duplicate_selection_rejected(tmp_path: Path) -> None:
    _mini_corpus(tmp_path)
    payload = _base_payload()
    payload["families"].append(
        {
            "family_id": "dup",
            "required": False,
            "reason": "dup",
            "selection": {"files": ["recaps/s1.md"]},
        }
    )
    manifest = load_acceptance_manifest(_write_manifest(tmp_path, payload))
    with pytest.raises(AcceptanceInventoryError, match="duplicate selection"):
        build_acceptance_inventory(tmp_path, manifest)


def test_traversal_and_absolute_rejected(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["families"][0]["selection"]["files"] = ["../outside.md"]
    with pytest.raises(AcceptanceInventoryError, match="\\.\\."):
        load_acceptance_manifest(_write_manifest(tmp_path, payload))
    payload = _base_payload()
    payload["families"][0]["selection"]["files"] = ["/tmp/abs.md"]
    with pytest.raises(AcceptanceInventoryError, match="relative"):
        load_acceptance_manifest(_write_manifest(tmp_path, payload))


def test_sha256_and_deterministic_write(tmp_path: Path) -> None:
    _mini_corpus(tmp_path)
    manifest = load_acceptance_manifest(_write_manifest(tmp_path, _base_payload()))
    report = build_acceptance_inventory(tmp_path, manifest)
    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"
    write_acceptance_inventory(report, out_a)
    write_acceptance_inventory(report, out_b)
    assert out_a.read_bytes() == out_b.read_bytes()
    for item in report.sources:
        assert len(item.sha256) == 64
        assert int(item.sha256, 16) >= 0


def test_cli_success_and_failure(tmp_path: Path) -> None:
    _mini_corpus(tmp_path)
    manifest = _write_manifest(tmp_path, _base_payload())
    out = tmp_path / "out" / "inv.json"
    ok = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(tmp_path),
            "--manifest",
            str(manifest),
            "--output",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert ok.returncode == 0, ok.stderr
    assert out.is_file()
    payload = _base_payload()
    payload["families"][0]["selection"]["files"] = ["recaps/nope.md"]
    bad_manifest = _write_manifest(tmp_path, payload)
    bad_out = tmp_path / "out" / "bad.json"
    bad = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(tmp_path),
            "--manifest",
            str(bad_manifest),
            "--output",
            str(bad_out),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert bad.returncode != 0
    assert not bad_out.exists()


def test_real_manifest_loads() -> None:
    manifest = load_acceptance_manifest(MANIFEST)
    assert manifest.world_id == "eldyrwild"
    assert any(fam.family_id == "canonical_recaps" for fam in manifest.families)
    recaps = next(fam for fam in manifest.families if fam.family_id == "canonical_recaps")
    assert len(recaps.selection.files) == 23
