"""Verified-snapshot path assert: hub/worldbuilding URIs are not filesystem gates."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from graph_memory.ingestion.graph_ingest_verified_snapshot import (
    _assert_store_source_paths_repo_contained,
    _is_non_filesystem_uri,
)


def test_is_non_filesystem_uri_detects_schemes() -> None:
    assert _is_non_filesystem_uri("fixture://corpus-ref/pc_baergrom")
    assert _is_non_filesystem_uri("https://example.test/x")
    assert not _is_non_filesystem_uri("corpus/eldyrwild-markdown/x.md")
    assert not _is_non_filesystem_uri("out/graph_memory/runs/x.json")


def test_assert_skips_worldbuilding_and_fixture_uris(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    real = repo / "out" / "real.json"
    real.parent.mkdir(parents=True)
    real.write_text("{}", encoding="utf-8")

    store = SimpleNamespace(
        source_artifacts={
            "wb": SimpleNamespace(
                source_domain="worldbuilding",
                uri="Longmont Campaign/Campaign 1/PCs/baergrom/README.md",
                recap_path=None,
                ingest_run_bundle_uri=None,
                session_id=None,
            ),
            "fixture": SimpleNamespace(
                source_domain="worldbuilding",
                uri="fixture://corpus-ref/pc_baergrom",
                recap_path=None,
                ingest_run_bundle_uri=None,
                session_id=None,
            ),
            "recap": SimpleNamespace(
                source_domain="recap",
                uri=str(real.relative_to(repo)),
                recap_path=None,
                ingest_run_bundle_uri=None,
                session_id="session-1",
            ),
        }
    )
    # Must not raise despite legacy hub path that does not exist under repo.
    _assert_store_source_paths_repo_contained(
        store, repo_root=repo, session_id="session-1"
    )
