from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.graph_memory.vocabulary import load_vocabulary_artifact_bundle

FIXTURE_DIR = Path("evals/graph_memory_layer/examples/vocabulary_contract_fixtures")


def _copy_fixture_dir(tmp_path: Path) -> Path:
    target = tmp_path / "vocabulary_contract_fixtures"
    shutil.copytree(FIXTURE_DIR, target)
    return target


def _rewrite_manifest(root: Path, update_file_row) -> None:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for file_row in manifest["files"]:
        update_file_row(file_row)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_loads_deterministic_fixture_bundle():
    bundle = load_vocabulary_artifact_bundle(FIXTURE_DIR)

    assert bundle.manifest.schema == "dmb_vocabulary_contract_fixture_manifest_v1"
    assert bundle.manifest.authority_class == "vocabulary_contract_fixture"
    assert bundle.manifest.candidate_graph_comparison is False
    assert len(bundle.source_artifacts) == 2
    assert len(bundle.lexical_observations) == 2
    assert len(bundle.vocabulary_entries) == 3
    assert len(bundle.alias_candidates) == 2
    assert len(bundle.do_not_merge_decisions) == 1
    assert len(bundle.containment_hints) == 1
    assert bundle.context_vocabulary_packet is not None


def test_summary_captures_entity_kinds_and_risk_flags():
    summary = load_vocabulary_artifact_bundle(FIXTURE_DIR).summary()

    assert summary.entity_kind_counts["place"] == 1
    assert summary.entity_kind_counts["collective"] == 1
    assert summary.entity_kind_counts["combat_encounter"] == 1
    assert summary.risk_flag_counts["cross_type"] == 1
    assert summary.risk_flag_counts["place_vs_polity"] == 1
    assert summary.risk_flag_counts["combat_encounter_vs_creature_group"] == 1


def test_diagnostics_are_json_serializable_without_quote_text():
    diagnostics = load_vocabulary_artifact_bundle(FIXTURE_DIR).to_diagnostics()

    restored = json.loads(json.dumps(diagnostics))

    assert restored["counts"]["vocabulary_entries"] == 3
    assert restored["counts"]["context_vocabulary_packet"] == 1
    assert "quote" not in json.dumps(restored)


def test_missing_manifest_fails_clearly(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="manifest.json"):
        load_vocabulary_artifact_bundle(tmp_path)


def test_missing_listed_file_fails_clearly(tmp_path: Path):
    shutil.copy(FIXTURE_DIR / "manifest.json", tmp_path / "manifest.json")

    with pytest.raises(FileNotFoundError, match="source_artifacts.json"):
        load_vocabulary_artifact_bundle(tmp_path)


def test_count_mismatch_fails_clearly(tmp_path: Path):
    root = _copy_fixture_dir(tmp_path)

    def update(file_row):
        if file_row["path"] == "vocabulary_entries.json":
            file_row["count"] = 99

    _rewrite_manifest(root, update)

    with pytest.raises(ValueError, match="count"):
        load_vocabulary_artifact_bundle(root)


def test_unknown_model_fails_clearly(tmp_path: Path):
    root = _copy_fixture_dir(tmp_path)

    def update(file_row):
        if file_row["path"] == "vocabulary_entries.json":
            file_row["model"] = "NotARealVocabularyModel"

    _rewrite_manifest(root, update)

    with pytest.raises(ValueError, match="unknown model"):
        load_vocabulary_artifact_bundle(root)


def test_context_vocabulary_packet_must_be_single_object(tmp_path: Path):
    root = _copy_fixture_dir(tmp_path)
    packet_path = root / "context_vocabulary_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_path.write_text(json.dumps([packet], indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="ContextVocabularyPacket"):
        load_vocabulary_artifact_bundle(root)
