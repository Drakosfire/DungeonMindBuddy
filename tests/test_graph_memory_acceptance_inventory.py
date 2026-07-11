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
    paths = ["optional/note.md", "pcs/alpha/hub.md", "recaps/s1.md"]
    hashes = {
        "optional/note.md": hashlib.sha256(b"opt\n").hexdigest(),
        "pcs/alpha/hub.md": hashlib.sha256(b"pc\n").hexdigest(),
        "recaps/s1.md": hashlib.sha256(b"one\n").hexdigest(),
    }

    def digest(lines: list[str]) -> str:
        return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()

    return {
        "schema": "dmb_world_acceptance_inventory_manifest_v2",
        "version": "2.0",
        "world_id": "eldyrwild",
        "campaign_id": "longmont-c2",
        "corpus_root": "corpus/eldyrwild-markdown",
        "source_kind": "source_extraction",
        "extraction_profile": "eldyrwild-c2-acceptance-v1",
        "expected": {
            "source_count": 3,
            "path_set_sha256": digest(paths),
            "content_set_sha256": digest(
                [f"{path}\t{hashes[path]}" for path in paths]
            ),
        },
        "families": [
            {
                "family_id": "canonical_recaps",
                "required": True,
                "reason": "recaps",
                "canon_layer": "campaign",
                "campaign_scope": "longmont-c2",
                "source_authority": "canonical_play",
                "selection": {"files": ["recaps/s1.md"]},
            },
            {
                "family_id": "pc_hubs",
                "required": True,
                "reason": "pcs",
                "canon_layer": "campaign",
                "campaign_scope": "longmont-c2",
                "source_authority": "campaign_reference",
                "selection": {"files": ["pcs/alpha/hub.md"]},
            },
            {
                "family_id": "world_support",
                "required": True,
                "reason": "world support",
                "canon_layer": "world",
                "campaign_scope": None,
                "source_authority": "world_reference",
                "selection": {"files": ["optional/note.md"]},
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
    payload["families"][1]["selection"]["glob"] = "**/*.md"
    with pytest.raises(AcceptanceInventoryError, match="unknown keys"):
        load_acceptance_manifest(_wm(tmp_path, payload))
    payload = _base()
    payload["families"][0]["requird"] = True
    with pytest.raises(AcceptanceInventoryError, match="unknown keys"):
        load_acceptance_manifest(_wm(tmp_path, payload))


def test_expansion_missing_duplicate_paths(tmp_path: Path) -> None:
    root = _corpus(tmp_path)
    report = _build(tmp_path)
    paths = [s.path for s in report.sources]
    assert paths == sorted(paths)
    assert "corpus/eldyrwild-markdown/recaps/s1.md" in paths
    assert "corpus/eldyrwild-markdown/pcs/alpha/hub.md" in paths
    assert report.summary["required_missing_count"] == 0
    (root / "recaps" / "new.md").write_text("not selected\n", encoding="utf-8")
    assert _build(tmp_path).summary["source_count"] == 3
    (root / "recaps" / "s1.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(AcceptanceInventoryError, match="content-set digest drift"):
        _build(tmp_path)
    (root / "recaps" / "s1.md").write_text("one\n", encoding="utf-8")

    payload = _base()
    payload["families"][0]["selection"]["files"] = ["recaps/missing.md"]
    with pytest.raises(AcceptanceInventoryError, match="required file missing"):
        _build(tmp_path, payload)

    payload = _base()
    payload["families"].append(
        {
            "family_id": "dup",
            "required": True,
            "reason": "dup",
            "canon_layer": "campaign",
            "campaign_scope": "longmont-c2",
            "source_authority": "campaign_reference",
            "selection": {"files": ["recaps/s1.md"]},
        }
    )
    with pytest.raises(AcceptanceInventoryError, match="duplicate selection"):
        _build(tmp_path, payload)


def test_path_and_pinned_selection_validation(tmp_path: Path) -> None:
    cases = [
        (["../outside.md"], "\\.\\."),
        (["/tmp/abs.md"], "relative"),
    ]
    for files, match in cases:
        payload = _base()
        payload["families"][0]["selection"]["files"] = files
        with pytest.raises(AcceptanceInventoryError, match=match):
            load_acceptance_manifest(_wm(tmp_path, payload))
    payload = _base()
    payload["families"][0]["selection"]["exclude_files"] = ["recaps/s1.md"]
    with pytest.raises(AcceptanceInventoryError, match="unknown keys"):
        load_acceptance_manifest(_wm(tmp_path, payload))
    payload = _base()
    payload["families"][2]["campaign_scope"] = "longmont-c2"
    with pytest.raises(AcceptanceInventoryError, match="must be null"):
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
    payload["families"][1]["selection"]["files"] = ["pcs/alpha-link/hub.md"]
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
            "required": True,
            "reason": "same inode",
            "canon_layer": "campaign",
            "campaign_scope": "longmont-c2",
            "source_authority": "campaign_reference",
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
    assert recap.source_artifact_id == "recaps/s1.md"
    assert recap.source_revision_id == f"sha256:{recap.sha256}"
    assert recap.canon_layer == "campaign"
    assert recap.campaign_scope == "longmont-c2"
    assert recap.size_bytes == 4
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    write_acceptance_inventory(report, a)
    write_acceptance_inventory(report, b)
    assert a.read_bytes() == b.read_bytes()
    with pytest.raises(AcceptanceInventoryError, match="overwrite the manifest"):
        write_acceptance_inventory(
            report, load_acceptance_manifest(_wm(tmp_path, _base())).manifest_path
        )
    with pytest.raises(AcceptanceInventoryError, match="inside the corpus"):
        write_acceptance_inventory(
            report, tmp_path / "corpus" / "eldyrwild-markdown" / "blocked.json"
        )

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
    report = build_acceptance_inventory(REPO, loaded)
    assert report.summary == {
        "source_count": 118,
        "required_source_count": 118,
        "optional_source_count": 0,
        "required_missing_count": 0,
        "diagnostic_count": 0,
    }
    assert report.contract == {
        "source_count": 118,
        "path_set_sha256": "499ea886b24c34110e44d5dc820e4a8b88440cc5417cba04d4c4399d47e4538c",
        "content_set_sha256": "c88dd03b1f1bc925a5f7ffe6332240f6830d9f62037fb13b8909e9bf4de06ef7",
    }
    assert {f.family_id: len(f.selection.files) for f in loaded.families} == {
        "canonical_recaps": 23,
        "party_registry": 1,
        "pc_hubs": 25,
        "required_world_hubs": 2,
        "campaign_support": 23,
        "world_support": 44,
    }
    assert {family["family_id"]: family["source_count"] for family in report.families} == {
        "canonical_recaps": 23,
        "party_registry": 1,
        "pc_hubs": 25,
        "required_world_hubs": 2,
        "campaign_support": 23,
        "world_support": 44,
    }
    for source in report.sources:
        if source.canon_layer == "world":
            assert source.campaign_scope is None
        else:
            assert source.campaign_scope == "longmont-c2"
        if source.source_artifact_id.startswith("Elderwyld/"):
            assert source.canon_layer == "world"
            assert source.campaign_scope is None
        if source.source_artifact_id.startswith("Longmont Campaign/Campaign 2/"):
            assert source.canon_layer == "campaign"
            assert source.campaign_scope == "longmont-c2"
