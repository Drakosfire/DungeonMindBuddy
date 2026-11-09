"""Retain URI-vs-file coverage at current source adapters after snapshot-engine removal."""

from pathlib import Path

import pytest

from src.graph_memory.extraction.recap_source_adapter import RecapSourceAdapter
from src.graph_memory.extraction.worldbuilding_source_adapter import WorldbuildingSourceAdapter


def test_is_non_filesystem_uri_detects_schemes(tmp_path: Path, monkeypatch) -> None:
    # Explicit metadata locators grant no filesystem authority. Exercise the real
    # current adapter instead of recreating the deleted engine's private predicate.
    with monkeypatch.context() as context:
        context.setattr(Path, "read_text", lambda *args, **kwargs: pytest.fail("metadata URI opened as a path"))
        for uri in ("fixture://corpus-ref/pc_baergrom", "https://example.test/x"):
            source = WorldbuildingSourceAdapter(
                source_artifact_id="synthetic-source", source_text="Known source bytes.", source_uri=uri,
            ).normalize()
            assert source.source_uri == uri
            assert source.source_text == "Known source bytes."
            assert all(span["source_uri"] == uri for span in source.source_span_index["spans"])
    # Explicit filesystem input continues to read its bytes and report its locator.
    for relative in ("corpus/eldyrwild-markdown/x.md", "out/graph_memory/runs/x.json"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Actual file bytes.")
        source = WorldbuildingSourceAdapter(source_artifact_id="file-source", source_path=path).normalize()
        assert source.source_text == "Actual file bytes."
        assert source.source_uri == path.as_posix()


def test_assert_skips_worldbuilding_and_fixture_uris(tmp_path: Path) -> None:
    for uri in ("Longmont Campaign/Campaign 1/PCs/baergrom/README.md", "fixture://corpus-ref/pc_baergrom"):
        source = WorldbuildingSourceAdapter(
            source_artifact_id="worldbuilding-source", source_text="Provided worldbuilding bytes.",
            source_uri=uri, campaign_id="synthetic-world",
        ).normalize()
        assert source.source_uri == uri and source.session_id is None
        assert source.source_text == "Provided worldbuilding bytes."
        assert source.source_sha256 and source.source_span_index["spans"]
    real = tmp_path / "out/real.md"
    real.parent.mkdir(parents=True)
    real.write_text("Actual recap bytes.")
    adapter = RecapSourceAdapter(campaign_id="synthetic-world", session_id="session-1", recap_path=real)
    source = adapter.normalize()
    assert source.source_text == "Actual recap bytes."
    assert source.source_uri == real.as_posix() and source.session_id == "session-1"
    real.unlink()
    with pytest.raises(FileNotFoundError):
        adapter.normalize()
