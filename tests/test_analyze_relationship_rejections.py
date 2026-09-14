"""Unit tests for Stage 4L Relationship Rejection Analysis."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_OUT = (
    REPO_ROOT
    / "out/stage4l_c1_s1_s10_chronological_graph_rehearsal/relationship_rejection_analysis"
)


def test_relationship_rejection_artifacts_exist_and_consistent() -> None:
    rel_path = ANALYSIS_OUT / "relationships.json"
    sum_path = ANALYSIS_OUT / "summary.json"
    rep_path = ANALYSIS_OUT / "REPORT.md"

    assert rel_path.exists(), "relationships.json must exist"
    assert sum_path.exists(), "summary.json must exist"
    assert rep_path.exists(), "REPORT.md must exist"

    records = json.loads(rel_path.read_text(encoding="utf-8"))
    assert len(records) == 276, (
        f"Expected 276 extracted relationships, got {len(records)}"
    )

    published = [r for r in records if r["published"]]
    rejects = [r for r in records if not r["published"]]

    assert len(published) == 150, f"Expected 150 published, got {len(published)}"
    assert len(rejects) == 126, f"Expected 126 rejects, got {len(rejects)}"

    summary = json.loads(sum_path.read_text(encoding="utf-8"))
    assert summary["metadata"]["total_extracted_relationships"] == 276
    assert summary["metadata"]["published_relationships"] == 150
    assert summary["metadata"]["unpublished_relationships"] == 126
    assert summary["metadata"]["model_calls"] == 0

    cats = summary["rejection_categories"]
    assert sum(cats.values()) == 126, (
        f"Category sum must equal 126, got {sum(cats.values())}"
    )
    assert "endpoint_identity_unresolved_or_wrong" in cats
    assert "endpoint_kind_missing_or_weak" in cats
    assert "ontology_endpoint_contract_too_narrow" in cats
    assert "extraction_semantically_bad" in cats
    assert "predicate_unmapped" in cats

    report_text = rep_path.read_text(encoding="utf-8")
    assert "276 extracted relationship denominator" in report_text
    assert "150 ( 54.3%)" in report_text
    assert "126" in report_text
    assert "Captain Lysandra" in report_text
    assert "NO — fix identity resolution" in report_text
