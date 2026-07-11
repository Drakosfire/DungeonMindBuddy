"""Tests for read-only Eldyrwild C2 acceptance inventory."""

from __future__ import annotations

import hashlib
import json
import os
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


def _wm(tmp: Path, payload: dict, name: str = "manifest.json") -> Path:
    path = tmp / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _corpus(tmp: Path) -> Path:
    root = tmp / "corpus" / "eldyrwild-markdown"
    for rel, text in {
        "recaps/s1.md": "one\n",
        "pcs/alpha/hub.md": "pc\n",
        "optional/note.md": "opt\n",
    }.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def _base() -> dict:
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


def _build(tmp: Path, payload: dict | None = None):
    return build_acceptance_inventory(
        tmp, load_acceptance_manifest(_wm(tmp, payload or _base()))
    )


def test_strict_schema_unknown_and_version(tmp_path: Path) -> None:
    for mutate, match in [
        (lambda p: p.__setitem__("schema", "nope") or p, "unsupported manifest schema"),
        (lambda p: p.__setitem__("version", "9.9") or p, "unsupported manifest version"),
        (lambda p: p.__setitem__("extra", True) or p, "unknown keys"),
    ]:
        payload = mutate(_base())
        with pytest.raises(AcceptanceInventoryError, match=match):
            load_acceptance_manifest(_wm(tmp_path, payload))
    payload = _base()
    sel = payload["families"][1]["selection"]
    del sel["minimum_per_root"]
    sel["minimum_per_rooot"] = 1
    with pytest.raises(AcceptanceInventoryError, match="unknown keys"):
        load_acceptance_manifest(_wm(tmp_path, payload))
    payload = _base()
    payload["families"][0]["requird"] = True
    with pytest.raises(AcceptanceInventoryError, match="unknown keys"):
        load_acceptance_manifest(_wm(tmp_path, payload))


def test_expansion_missing_duplicate_paths(tmp_path: Path) -> None:
    _corpus(tmp_path)
    report = _build(tmp_path)
    paths = [s.path for s in report.sources]
    assert paths == sorted(paths)
    assert "corpus/eldyrwild-markdown/recaps/s1.md" in paths
    assert "corpus/eldyrwild-markdown/pcs/alpha/hub.md" in paths
    assert report.summary["required_missing_count"] == 0

    payload = _base()
    payload["families"][0]["selection"]["files"] = ["recaps/missing.md"]
    with pytest.raises(AcceptanceInventoryError, match="required file missing"):
        _build(tmp_path, payload)

    payload = _base()
    payload["families"][2]["selection"]["roots"] = ["optional-missing"]
    report = _build(tmp_path, payload)
    assert any(d.code == "optional_root_missing" for d in report.diagnostics)

    payload = _base()
    payload["families"].append(
        {
            "family_id": "dup",
            "required": False,
            "reason": "dup",
            "selection": {"files": ["recaps/s1.md"]},
        }
    )
    with pytest.raises(AcceptanceInventoryError, match="duplicate selection"):
        _build(tmp_path, payload)


def test_path_glob_and_exclude_validation(tmp_path: Path) -> None:
    cases = [
        (["../outside.md"], None, "\\.\\."),
        (["/tmp/abs.md"], None, "relative"),
        (None, "/tmp/*.md", "relative"),
        (None, "../*.md", "\\.\\."),
    ]
    for files, glob, match in cases:
        payload = _base()
        if files is not None:
            payload["families"][0]["selection"]["files"] = files
        if glob is not None:
            payload["families"][1]["selection"]["glob"] = glob
        with pytest.raises(AcceptanceInventoryError, match=match):
            load_acceptance_manifest(_wm(tmp_path, payload))
    payload = _base()
    payload["families"][0]["selection"]["exclude_files"] = ["recaps/s1.md"]
    with pytest.raises(AcceptanceInventoryError, match="overlap"):
        load_acceptance_manifest(_wm(tmp_path, payload))


def test_symlink_and_physical_duplicate(tmp_path: Path) -> None:
    root = _corpus(tmp_path)
    link = root / "recaps" / "link.md"
    link.symlink_to(root / "recaps" / "s1.md")
    payload = _base()
    payload["families"][0]["selection"]["files"] = ["recaps/link.md"]
    with pytest.raises(AcceptanceInventoryError, match="symlinks are not allowed"):
        _build(tmp_path, payload)

    link.unlink()
    (root / "pcs" / "alpha-link").symlink_to(root / "pcs" / "alpha")
    payload = _base()
    payload["families"][1]["selection"]["roots"] = ["pcs/alpha-link"]
    with pytest.raises(AcceptanceInventoryError, match="symlinks are not allowed"):
        _build(tmp_path, payload)

    outside = tmp_path / "outside.md"
    outside.write_text("x\n", encoding="utf-8")
    escape = root / "recaps" / "escape.md"
    escape.symlink_to(outside)
    payload = _base()
    payload["families"][0]["selection"]["files"] = ["recaps/escape.md"]
    with pytest.raises(AcceptanceInventoryError, match="symlinks are not allowed"):
        _build(tmp_path, payload)

    escape.unlink()
    hard = root / "recaps" / "hard.md"
    os.link(root / "recaps" / "s1.md", hard)
    payload = _base()
    payload["families"].append(
        {
            "family_id": "hardlink",
            "required": False,
            "reason": "same inode",
            "selection": {"files": ["recaps/hard.md"]},
        }
    )
    with pytest.raises(AcceptanceInventoryError, match="duplicate physical source"):
        _build(tmp_path, payload)


def test_sha256_determinism_cli_and_real_manifest(tmp_path: Path) -> None:
    _corpus(tmp_path)
    report = _build(tmp_path)
    recap = next(s for s in report.sources if s.path.endswith("recaps/s1.md"))
    assert recap.sha256 == hashlib.sha256(b"one\n").hexdigest()
    assert recap.size_bytes == 4
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    write_acceptance_inventory(report, a)
    write_acceptance_inventory(report, b)
    assert a.read_bytes() == b.read_bytes()

    out = tmp_path / "out" / "inv.json"
    ok = subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(tmp_path),
         "--manifest", str(_wm(tmp_path, _base())), "--output", str(out)],
        check=False, capture_output=True, text=True, cwd=str(REPO),
    )
    assert ok.returncode == 0, ok.stderr
    assert out.is_file()

    bad_payload = _base()
    bad_payload["families"][0]["selection"]["files"] = ["recaps/nope.md"]
    bad = subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(tmp_path),
         "--manifest", str(_wm(tmp_path, bad_payload, "bad/manifest.json")),
         "--output", str(tmp_path / "out" / "bad.json")],
        check=False, capture_output=True, text=True, cwd=str(REPO),
    )
    assert bad.returncode != 0
    assert '"ok": false' in bad.stdout

    missing = subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(tmp_path),
         "--manifest", str(tmp_path / "missing.json"),
         "--output", str(tmp_path / "out" / "m.json")],
        check=False, capture_output=True, text=True, cwd=str(REPO),
    )
    assert missing.returncode != 0
    assert "Traceback" not in missing.stderr
    assert "manifest unreadable" in missing.stdout

    loaded = load_acceptance_manifest(MANIFEST)
    assert loaded.world_id == "eldyrwild"
    recaps = next(f for f in loaded.families if f.family_id == "canonical_recaps")
    assert len(recaps.selection.files) == 23
