from pathlib import Path

from extraction_lab.campaign_memory_corpus_census import census_corpus


def test_census_is_zero_api_and_buckets_unparseable_sources(tmp_path: Path) -> None:
    good = tmp_path / "good.md"
    good.write_text(
        """---
title: Good
document_class: world
canon_layer: world
campaign_id: null
temporal_scope: evergreen
session: null
origin_session: null
last_updated_session: null
source_class: seed_reference
---
# Good

Enough useful text to form a deterministic evidence unit for census.
""",
        encoding="utf-8",
    )
    (tmp_path / "bad.md").write_text("---\ntitle: broken\n", encoding="utf-8")
    result = census_corpus(tmp_path)
    assert result["markdown_source_count"] == 2
    assert result["parseable_source_count"] == 1
    assert result["rejected_source_count"] == 1
    assert result["model_calls"] == 0
    assert result["silent_skip_count"] == 0
    assert sum(result["rejection_buckets"].values()) == 1
    assert {row["path"] for row in result["sources"]} == {"good.md", "bad.md"}


def test_census_selected_paths_do_not_drop_failures(tmp_path: Path) -> None:
    good = tmp_path / "keep.md"
    good.write_text(
        """---
title: Keep
document_class: world
canon_layer: world
campaign_id: null
temporal_scope: evergreen
session: null
origin_session: null
last_updated_session: null
source_class: seed_reference
---
# Keep

Selected path still has enough text for an evidence unit.
""",
        encoding="utf-8",
    )
    bad = tmp_path / "broken.md"
    bad.write_text("---\ntitle: broken\n", encoding="utf-8")
    result = census_corpus(tmp_path, paths=[good, bad])
    assert result["markdown_source_count"] == 2
    assert result["rejected_source_count"] == 1
    assert result["parseable_source_count"] == 1
