from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    create_extraction_run,
    get_extraction_run,
    update_extraction_run_status,
)
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    create_source_artifact_from_workspace_document,
    get_source_artifact,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    mark_workspace_document_committed,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _committed_worldbuilding(root: Path):
    record = create_workspace_document(
        root,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    return mark_workspace_document_committed(root, record.document_id, expected_revision=1)


def test_source_artifact_registry_idempotent_for_same_revision(tmp_path: Path) -> None:
    record = _committed_worldbuilding(tmp_path)
    markdown = "# Lore\n\nBody.\n"
    first = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
        markdown=markdown,
    )
    second = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
        markdown=markdown,
    )
    assert first.source_artifact_id == second.source_artifact_id
    assert first.source_artifact_id != record.document_id
    assert first.session_id is None
    loaded = get_source_artifact(tmp_path, first.source_artifact_id)
    assert loaded.source_artifact_id == first.source_artifact_id


def test_source_artifact_requires_committed_workspace(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    with pytest.raises(SourceArtifactRegistryError, match="committed"):
        create_source_artifact_from_workspace_document(
            tmp_path,
            document_id=record.document_id,
            markdown="# Lore\n",
        )


def test_extraction_run_exact_reload_and_no_latest(tmp_path: Path) -> None:
    run = create_extraction_run(
        tmp_path,
        source_artifact_id="artifact:worldbuilding:x",
        source_domain="worldbuilding",
        campaign_id="eldyrwild",
        session_id=None,
    )
    loaded = get_extraction_run(tmp_path, run.run_id)
    assert loaded.run_id == run.run_id
    with pytest.raises(GraphRunRegistryError) as exc_info:
        get_extraction_run(tmp_path, "missing-run")
    assert exc_info.value.status_code == 404


def test_extraction_run_rejects_fabricated_worldbuilding_session(tmp_path: Path) -> None:
    with pytest.raises(GraphRunRegistryError, match="session_id"):
        create_extraction_run(
            tmp_path,
            source_artifact_id="artifact:worldbuilding:x",
            source_domain="worldbuilding",
            session_id="session-1",
        )


def test_partial_components_cannot_become_reviewable(tmp_path: Path) -> None:
    run = create_extraction_run(
        tmp_path,
        source_artifact_id="artifact:worldbuilding:x",
        source_domain="worldbuilding",
    )
    with pytest.raises(GraphRunRegistryError, match="incomplete"):
        update_extraction_run_status(
            tmp_path,
            run.run_id,
            status=ExtractionRunStatus.REVIEWABLE,
            components={
                "source_artifact": ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                    uri="repo://x.md",
                    exists=True,
                ),
            },
        )
