from __future__ import annotations

import uuid
from pathlib import Path

from tools.batch_ingest_corpus import collect_legacy_corpus_markdown_paths


def test_collect_legacy_corpus_markdown_paths_excludes_dungeonbuddy_managed_storage(
    tmp_path: Path,
) -> None:
    corpus_root = tmp_path / "corpus" / "eldyrwild-markdown"
    campaign_md = corpus_root / "Elderwyld" / "Places" / "Ironveil.md"
    campaign_md.parent.mkdir(parents=True)
    campaign_md.write_text("# Ironveil\n", encoding="utf-8")

    document_id = str(uuid.uuid4())
    managed_md = (
        corpus_root
        / "_dungeonbuddy"
        / "sources"
        / document_id
        / "source.md"
    )
    managed_md.parent.mkdir(parents=True)
    managed_md.write_text("# Managed source\n", encoding="utf-8")

    paths = collect_legacy_corpus_markdown_paths(corpus_root)

    assert campaign_md.resolve() in paths
    assert managed_md.resolve() not in paths


def test_collect_legacy_corpus_markdown_paths_filters_managed_paths_file_entries(
    tmp_path: Path,
    capsys,
) -> None:
    corpus_root = tmp_path / "corpus" / "eldyrwild-markdown"
    campaign_md = corpus_root / "Elderwyld" / "Places" / "Ironveil.md"
    campaign_md.parent.mkdir(parents=True)
    campaign_md.write_text("# Ironveil\n", encoding="utf-8")

    document_id = str(uuid.uuid4())
    managed_rel = f"_dungeonbuddy/sources/{document_id}/source.md"
    managed_md = corpus_root / managed_rel
    managed_md.parent.mkdir(parents=True)
    managed_md.write_text("# Managed source\n", encoding="utf-8")

    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(
        "\n".join(
            [
                "Elderwyld/Places/Ironveil.md",
                managed_rel,
            ]
        ),
        encoding="utf-8",
    )

    paths = collect_legacy_corpus_markdown_paths(corpus_root, paths_file=paths_file)

    assert paths == [campaign_md.resolve()]
    captured = capsys.readouterr()
    assert "Warning: skipping managed _dungeonbuddy path" in captured.err
