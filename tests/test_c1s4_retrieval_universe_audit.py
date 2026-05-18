from pathlib import Path

from evals.c1s4_preplanning_vertical_slice.audit_retrieval_universe import (
    build_expected_evidence_manifest,
    classify_retrieval_failure,
    run_audit,
)
from evals.c1s4_preplanning_vertical_slice.context_classification import is_allowed_retrieval_corpus_path


def test_expected_manifest_builds() -> None:
    rows = build_expected_evidence_manifest()
    assert rows
    assert any(r.group_id == "pippa_character_continuity" for r in rows)
    assert all(r.required_lane for r in rows)


def test_disk_hygiene_classification() -> None:
    assert Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md").exists()
    assert is_allowed_retrieval_corpus_path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md")
    assert is_allowed_retrieval_corpus_path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/pippa/README.md")
    assert not is_allowed_retrieval_corpus_path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json")
    assert not is_allowed_retrieval_corpus_path("Docs/Plans/foo.md")


def test_taxonomy_classification() -> None:
    assert classify_retrieval_failure(exists=True, allowed=True, in_records=False, direct_hit=False, step2c_retrieved=False, step2c_candidate=False) == "source_not_materialized_as_retrieval_record"
    assert classify_retrieval_failure(exists=True, allowed=True, in_records=True, direct_hit=False, step2c_retrieved=False, step2c_candidate=False) == "source_indexed_but_direct_probe_miss"
    assert classify_retrieval_failure(exists=True, allowed=True, in_records=True, direct_hit=True, step2c_retrieved=False, step2c_candidate=False) == "direct_probe_hit_step2c_miss"
    assert classify_retrieval_failure(exists=True, allowed=True, in_records=True, direct_hit=True, step2c_retrieved=True, step2c_candidate=False) == "step2c_retrieved_but_candidate_missing"


def test_pr57_artifacts_generated(tmp_path: Path) -> None:
    summary = run_audit(step2c_report=None, output_dir=tmp_path)
    assert summary["schema"]
    assert (tmp_path / "pr57_retrieval_universe_summary.json").exists()
    assert (tmp_path / "pr57_expected_evidence_manifest.csv").exists()
    assert (tmp_path / "pr57_direct_probe_results.csv").exists()
