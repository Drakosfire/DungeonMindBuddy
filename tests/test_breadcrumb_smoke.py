from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    compare_to_baseline,
    dry_run_timeline_append,
    parse_frontmatter_and_body,
    parse_inline_tags,
    summarize_artifact,
)


def test_parse_frontmatter_and_inline_tags() -> None:
    text = """---
schema: dmb_recap_breadcrumbs_v1
---
# Recap

Caelynn calls Sara. [PC][Longmont Campaign/Campaign 2/PCs/caelynn/] [NPC][Longmont Campaign/Campaign 2/NPCs/sara/]
"""
    frontmatter, body = parse_frontmatter_and_body(text)
    tags = parse_inline_tags(text)

    assert frontmatter is not None
    assert "schema: dmb_recap_breadcrumbs_v1" in frontmatter
    assert "Caelynn calls Sara" in body
    assert [(t.tag_type, t.slug) for t in tags] == [("PC", "caelynn"), ("NPC", "sara")]


def test_baseline_comparison_counts_overlap_extra_and_missing() -> None:
    baseline = parse_inline_tags(
        "[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] "
        "[NPC][Longmont Campaign/Campaign 2/NPCs/sara/]"
    )
    got = parse_inline_tags(
        "[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] "
        "[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]"
    )

    out = compare_to_baseline(got, baseline)

    assert out["overlap_tag_total"] == 1
    assert out["precision_vs_baseline"] == 0.5
    assert out["recall_vs_baseline"] == 0.5
    assert out["extra_routes"][0]["tag_type"] == "Party"
    assert out["missing_routes"][0]["tag_type"] == "NPC"


def test_dry_run_timeline_append_uses_existing_timeline(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    recap = corpus / "Longmont Campaign" / "Campaign 2" / "Session Recaps" / "Session 20 - Recap.md"
    timeline = corpus / "Longmont Campaign" / "Campaign 2" / "PCs" / "caelynn" / "timeline.md"
    recap.parent.mkdir(parents=True)
    timeline.parent.mkdir(parents=True)
    recap.write_text("# Recap\n", encoding="utf-8")
    timeline.write_text(
        "Session | Beat (short) | Recap / prep\n--- | --- | ---\n",
        encoding="utf-8",
    )
    tag = parse_inline_tags("[PC][Longmont Campaign/Campaign 2/PCs/caelynn/]")[0]

    out = dry_run_timeline_append(
        corpus_root=corpus,
        tag=tag,
        session=20,
        recap_path="Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
    )

    assert out["ok"] is True
    assert out["phase"] == "preview"
    assert out["path"] == "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md"
    assert "Breadcrumb smoke route for caelynn" in out["diff"]


def test_summarize_artifact_reports_unknown_tags_and_missing_routes(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    recap = corpus / "Longmont Campaign" / "Campaign 2" / "Session Recaps" / "Session 20 - Recap.md"
    recap.parent.mkdir(parents=True)
    recap.write_text("# Recap\n", encoding="utf-8")
    artifact = tmp_path / "artifact.md"
    artifact.write_text(
        "---\n"
        "schema: dmb_recap_breadcrumbs_v1\n"
        "---\n"
        "Caelynn. [SubjectType][x] [PC][Longmont Campaign/Campaign 2/PCs/missing/]\n",
        encoding="utf-8",
    )

    out = summarize_artifact(
        artifact_path=artifact,
        corpus_root=corpus,
        source_recap_path="Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        session=20,
        baseline_tags=[],
    )

    assert out["parse"]["schema_marker_present"] is True
    assert out["unknown_tag_types"] == ["SubjectType"]
    assert out["route_checks"]["missing_non_candidate_routes"][0]["route"] == "x"


def test_summarize_artifact_ignores_frontmatter_tag_grammar(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    recap = corpus / "Longmont Campaign" / "Campaign 2" / "Session Recaps" / "Session 20 - Recap.md"
    timeline = corpus / "Longmont Campaign" / "Campaign 2" / "PCs" / "caelynn" / "timeline.md"
    recap.parent.mkdir(parents=True)
    timeline.parent.mkdir(parents=True)
    recap.write_text("# Recap\n", encoding="utf-8")
    timeline.write_text(
        "Session | Beat (short) | Recap / prep\n--- | --- | ---\n",
        encoding="utf-8",
    )
    artifact = tmp_path / "artifact.md"
    artifact.write_text(
        "---\n"
        "schema: dmb_recap_breadcrumbs_v1\n"
        'pc: "[PC][corpus-relative hub route]"\n'
        "---\n"
        "Caelynn. [PC][Longmont Campaign/Campaign 2/PCs/caelynn/]\n",
        encoding="utf-8",
    )

    out = summarize_artifact(
        artifact_path=artifact,
        corpus_root=corpus,
        source_recap_path="Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        session=20,
        baseline_tags=[],
    )

    assert out["tag_counts"] == {"PC": 1}
    assert out["route_checks"]["unique_routes"] == 1
    assert out["route_checks"]["missing_non_candidate_routes"] == []
