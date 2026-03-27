from __future__ import annotations

import json
from pathlib import Path

from evals.corpus_remote.build_remote_inventory import (
    _collect_local_inventory,
    _infer_canon_layer,
    generate_remote_artifacts,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_collect_local_inventory_only_includes_supported_extensions(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "Docs" / "world_lore.md", "# lore")
    _write(tmp_path / "Docs" / "Campaign 2" / "session_20_recap.docx", "binary-ish")
    _write(tmp_path / "Docs" / "image.png", "not included")

    records = _collect_local_inventory(tmp_path)
    paths = {Path(record.path).name for record in records}
    assert "world_lore.md" in paths
    assert "session_20_recap.docx" in paths
    assert "image.png" not in paths


def test_generate_remote_artifacts_produces_required_files(tmp_path: Path) -> None:
    _write(tmp_path / "World" / "elderwyld_module.md", "world seed")
    _write(
        tmp_path / "Longmont Campaign" / "Campaign 2" / "Session 20 Recap.docx",
        "session data",
    )
    records = _collect_local_inventory(tmp_path)

    out_dir = tmp_path / "out"
    inventory, manifest, reproducibility = generate_remote_artifacts(
        source_host="gpu_desktop",
        records=records,
        sample_size=10,
        out_dir=out_dir,
    )

    inventory_path = out_dir / "remote_inventory.json"
    manifest_path = out_dir / "normalization_manifest.json"
    reproducibility_path = out_dir / "reproducibility_report.json"
    assert inventory_path.exists()
    assert manifest_path.exists()
    assert reproducibility_path.exists()

    loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded_manifest["snapshot_id"] == inventory["snapshot_id"]
    campaign_docs = [
        doc
        for doc in loaded_manifest["documents"]
        if "campaign 2" in doc["remote_path"].lower()
    ]
    assert campaign_docs, "Expected at least one campaign document in manifest"
    for doc in campaign_docs:
        assert doc["canon_layer"] == "campaign"
        assert doc["campaign_id"] == "campaign_2"

    assert reproducibility["document_counts_match"] is True
    assert manifest["documents"]


def test_campaign_context_folder_name_does_not_force_campaign_layer() -> None:
    layer, campaign_id = _infer_canon_layer(
        "corpus/eldyrwild-markdown/Elderwyld/World Lore/stonebridge.md"
    )
    assert layer == "world"
    assert campaign_id is None

