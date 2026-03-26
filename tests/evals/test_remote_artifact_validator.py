from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from evals.corpus_remote.build_remote_inventory import (
    _collect_local_inventory,
    generate_remote_artifacts,
)
from evals.corpus_remote.run_remote_snapshot_pipeline import main as run_pipeline_main
from evals.corpus_remote.validate_remote_artifacts import (
    main as validate_main,
    validate_artifacts,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_validate_remote_artifacts_passes_for_generated_payloads(tmp_path: Path) -> None:
    _write(tmp_path / "World" / "Lore.md", "world")
    _write(tmp_path / "Longmont Campaign" / "Campaign 2" / "Session 20 Recap.docx", "x")
    records = _collect_local_inventory(tmp_path)
    out_dir = tmp_path / "out"
    generate_remote_artifacts(
        source_host="gpu_desktop",
        records=records,
        sample_size=20,
        out_dir=out_dir,
    )

    errors = validate_artifacts(
        inventory_path=out_dir / "remote_inventory.json",
        manifest_path=out_dir / "normalization_manifest.json",
        reproducibility_path=out_dir / "reproducibility_report.json",
    )
    assert errors == []


def test_validate_remote_artifacts_fails_for_invalid_campaign_document(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "Longmont Campaign" / "Campaign 2" / "Session 20 Recap.docx", "x")
    records = _collect_local_inventory(tmp_path)
    out_dir = tmp_path / "out"
    generate_remote_artifacts(
        source_host="gpu_desktop",
        records=records,
        sample_size=20,
        out_dir=out_dir,
    )

    manifest_path = out_dir / "normalization_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["documents"][0]["canon_layer"] = "campaign"
    manifest["documents"][0]["campaign_id"] = None
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    errors = validate_artifacts(
        inventory_path=out_dir / "remote_inventory.json",
        manifest_path=manifest_path,
        reproducibility_path=out_dir / "reproducibility_report.json",
    )
    assert any("canon_layer=campaign" in error for error in errors)


def test_run_remote_snapshot_pipeline_local_mode(monkeypatch: object, tmp_path: Path) -> None:
    _write(tmp_path / "World" / "Lore.md", "world")
    _write(tmp_path / "Longmont Campaign" / "Campaign 2" / "Session 20 Recap.docx", "x")
    out_dir = tmp_path / "out"

    def _fake_parse_args() -> argparse.Namespace:
        return argparse.Namespace(
            source_host="gpu_desktop",
            sample_size=10,
            out_dir=str(out_dir),
            local_root=str(tmp_path),
            ssh_host=None,
            remote_root=None,
        )

    from evals.corpus_remote import run_remote_snapshot_pipeline as runner

    monkeypatch.setattr(runner, "parse_args", _fake_parse_args)
    exit_code = run_pipeline_main()
    assert exit_code == 0
    assert (out_dir / "remote_inventory.json").exists()
    assert (out_dir / "normalization_manifest.json").exists()
    assert (out_dir / "reproducibility_report.json").exists()


def test_run_remote_snapshot_pipeline_requires_remote_arguments(
    monkeypatch: object,
) -> None:
    def _fake_parse_args() -> argparse.Namespace:
        return argparse.Namespace(
            source_host="gpu_desktop",
            sample_size=10,
            out_dir="out/evals/corpus_remote",
            local_root=None,
            ssh_host=None,
            remote_root=None,
        )

    from evals.corpus_remote import run_remote_snapshot_pipeline as runner

    monkeypatch.setattr(runner, "parse_args", _fake_parse_args)
    with pytest.raises(ValueError):
        run_pipeline_main()


def test_validate_main_returns_nonzero_on_snapshot_mismatch(
    monkeypatch: object, tmp_path: Path
) -> None:
    _write(tmp_path / "World" / "Lore.md", "world")
    records = _collect_local_inventory(tmp_path)
    out_dir = tmp_path / "out"
    generate_remote_artifacts(
        source_host="gpu_desktop",
        records=records,
        sample_size=10,
        out_dir=out_dir,
    )
    inventory_path = out_dir / "remote_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["snapshot_id"] = "snapshot_broken"
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    def _fake_parse_args() -> argparse.Namespace:
        return argparse.Namespace(
            inventory=str(out_dir / "remote_inventory.json"),
            manifest=str(out_dir / "normalization_manifest.json"),
            reproducibility=str(out_dir / "reproducibility_report.json"),
        )

    from evals.corpus_remote import validate_remote_artifacts as validator

    monkeypatch.setattr(validator, "parse_args", _fake_parse_args)
    assert validate_main() == 1

