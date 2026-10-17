from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from apps.live_control_server.services import source_artifact_registry as registry
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    create_extraction_run,
)
from application_state.ingest import service as ingest_service
from application_state.source import service as source_service
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
from src.live_play.live_store import write_json


def test_same_recap_is_idempotent_per_world_and_distinct_across_worlds(
    tmp_path: Path,
) -> None:
    first = registry.create_recap_source_artifact(
        tmp_path,
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        recap_text="Session 29\n\nMireward changes.\n",
    )
    first_again = registry.create_recap_source_artifact(
        tmp_path,
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        recap_text="Session 29\n\nMireward changes.\n",
    )
    second_world = registry.create_recap_source_artifact(
        tmp_path,
        world_id="world:conks-and-cons",
        campaign_id="longmont-c2",
        session_id="session-29",
        recap_text="Session 29\n\nMireward changes.\n",
    )

    assert first.source_artifact_id == first_again.source_artifact_id
    assert first_again.uri == first.uri
    assert first.source_artifact_id != second_world.source_artifact_id
    assert first.world_id == "world:elderwyld"
    assert second_world.world_id == "world:conks-and-cons"
    assert first.content_sha256 == second_world.content_sha256
    loaded, markdown = registry.load_registered_source_artifact_text(
        tmp_path, second_world.source_artifact_id
    )
    assert loaded.world_id == "world:conks-and-cons"
    assert markdown == "Session 29\n\nMireward changes.\n"


def test_fresh_recap_requires_world_before_writing_registry_or_source_bytes(
    tmp_path: Path,
) -> None:
    with pytest.raises(registry.SourceArtifactRegistryError, match="verified native world_id"):
        registry.create_recap_source_artifact(
            tmp_path,
            world_id=" ",
            campaign_id="longmont-c2",
            session_id="session-29",
            recap_text="Session 29\n\nNo implicit World.\n",
        )

    assert not registry.source_artifacts_path(tmp_path).exists()
    assert not (tmp_path / registry.DEFAULT_RECAP_SOURCE_CONTENT_ROOT).exists()
    assert not (tmp_path / registry.DEFAULT_SOURCE_SPAN_INDEX_DIR_REL).exists()


def test_existing_worldless_recap_registry_entry_remains_unchanged(tmp_path: Path) -> None:
    legacy = GraphMemorySourceArtifact(
        source_artifact_id="artifact:recap:longmont-c2:session-28:abc123abc123",
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-28",
        uri="repo://legacy/recap.md",
        content_sha256="a" * 64,
    )
    path = registry.source_artifacts_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        path,
        registry.SourceArtifactRegistryDocument(records=[legacy]).model_dump(mode="json"),
    )

    loaded = registry.get_source_artifact(tmp_path, legacy.source_artifact_id)

    assert loaded == legacy
    assert loaded.world_id is None
    assert registry._load(tmp_path).records == [legacy]


def test_mismatched_world_run_is_rejected_before_source_or_run_persistence(
    tmp_path: Path,
    application_state_dsn: str,
) -> None:
    assert application_state_dsn
    artifact = registry.create_recap_source_artifact(
        tmp_path,
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        recap_text="Session 29\n\nMireward changes.\n",
    )
    run_id = f"world-binding-mismatch-{uuid4()}"

    with pytest.raises(GraphRunRegistryError, match="does not match its exact"):
        create_extraction_run(
            tmp_path,
            run_id=run_id,
            source_artifact_id=artifact.source_artifact_id,
            source_domain="recap",
            campaign_id="longmont-c2",
            session_id="session-29",
            lineage={
                "native_world_id": "world:conks-and-cons",
                "campaign_id": "longmont-c2",
            },
        )

    assert ingest_service.get_extraction_run_optional(run_id) is None
    assert (
        source_service.get_source_markdown(
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=artifact.content_sha256 or "",
        )
        is None
    )
