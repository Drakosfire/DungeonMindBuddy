from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from apps.live_control_server.services import historical_recap_source_adoption as adoption
from application_state.source.types import SourceMarkdownRecord
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _run(uri: str, digest: str) -> ExtractionRun:
    return ExtractionRun(
        run_id="run-adopt-25",
        source_artifact_id="artifact:recap:longmont-c2:session-25:abc123",
        source_domain="recap",
        status=ExtractionRunStatus.VALIDATED,
        campaign_id="longmont-c2",
        session_id="session-25",
        components={
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri=uri,
                sha256=digest,
            )
        },
    )


def test_adoption_reads_exact_file_once_and_preserves_digest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown = "# Session 25\n\nExact source.\n"
    source_path = tmp_path / "recap.md"
    source_path.write_bytes(markdown.encode("utf-8"))
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    run = _run("repo://recap.md", digest)
    persisted: dict[str, object] = {}

    monkeypatch.setattr(adoption, "get_extraction_run", lambda _root, _run_id: run)

    def fake_persist(**kwargs):
        persisted.update(kwargs)
        return SourceMarkdownRecord(
            source_revision_id=uuid4(),
            source_artifact_id=kwargs["source_artifact_id"],
            source_domain=kwargs["source_domain"],
            campaign_id=kwargs["campaign_id"],
            session_id=kwargs["session_id"],
            world_id=kwargs["world_id"],
            content_sha256=kwargs["content_sha256"],
            media_type="text/markdown",
            encoding="utf-8",
            markdown=kwargs["markdown"],
            lineage=kwargs["lineage"],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(adoption.source_service, "persist_source_markdown", fake_persist)

    record = adoption.adopt_historical_recap_source(
        tmp_path,
        run_id=run.run_id,
        world_id="eldyrwild",
    )

    assert record.markdown == markdown
    assert persisted["content_sha256"] == digest
    assert persisted["world_id"] == "eldyrwild"
    assert persisted["lineage"] == {
        "adopted_from_run_id": run.run_id,
        "adopted_from_uri": "repo://recap.md",
    }


def test_adoption_fails_on_digest_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "recap.md"
    source_path.write_text("changed\n", encoding="utf-8")
    run = _run("repo://recap.md", "0" * 64)
    monkeypatch.setattr(adoption, "get_extraction_run", lambda _root, _run_id: run)

    with pytest.raises(adoption.GraphRunRegistryError, match="digest"):
        adoption.adopt_historical_recap_source(
            tmp_path,
            run_id=run.run_id,
            world_id="eldyrwild",
        )
