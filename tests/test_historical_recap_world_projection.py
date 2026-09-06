from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from apps.live_control_server.services import historical_recap_world_projection as projection_service
from application_state.source.types import SourceMarkdownRecord
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTrustBoundary,
)


RUN_ID = "graph-ingest:longmont-c2:session-25:20260808T005650Z"
ARTIFACT_ID = "artifact:recap:longmont-c2:session-25:fd38b5915b32"
MARKDOWN = "# Session 25\n\nBonogo arrives.\n"


def _run() -> ExtractionRun:
    return ExtractionRun(
        run_id=RUN_ID,
        source_artifact_id=ARTIFACT_ID,
        source_domain="recap",
        status=ExtractionRunStatus.VALIDATED,
        campaign_id="longmont-c2",
        session_id="session-25",
        components={
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri="repo://ignored-after-adoption.md",
                sha256="sha256:" + "a" * 64,
            )
        },
    )


def _source() -> SourceMarkdownRecord:
    return SourceMarkdownRecord(
        source_revision_id=uuid4(),
        source_artifact_id=ARTIFACT_ID,
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        content_sha256="a" * 64,
        media_type="text/markdown",
        encoding="utf-8",
        markdown=MARKDOWN,
        lineage={"adopted_from_run_id": RUN_ID},
        created_at=datetime.now(UTC),
    )


def _world() -> WorldGraphProjection:
    focus = WorldGraphProjectionFocus(
        kind="session",
        campaign_id="longmont-c2",
        session_id="session-25",
    )
    snapshot = WorldGraphProjectionSnapshot(
        world_id="eldyrwild",
        campaign_id="longmont-c2",
        revision_id="world-rev-25",
        head_revision_id="world-rev-25",
        is_head=True,
        focus=focus,
        admissibility="gm",
        scope_mode="campaign",
    )
    node = WorldGraphProjectionNodeView(
        node_id="node-bonogo",
        label="Bonogo",
        kind="character",
        role="npc",
    )
    return WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=snapshot,
        summary=WorldGraphProjectionSummary(
            node_count=1,
            relationship_count=0,
            attribute_count=0,
            evidence_count=0,
            source_artifact_count=0,
        ),
        nodes=[node],
        trust_boundary=WorldGraphProjectionTrustBoundary(
            can_trust=["current World snapshot"],
            cannot_trust=["historical identity"],
        ),
    )


def test_exact_run_projection_uses_durable_source_and_current_world(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(projection_service, "get_extraction_run", lambda _root, _id: _run())
    monkeypatch.setattr(
        projection_service.source_service,
        "get_source_markdown",
        lambda **_kwargs: _source(),
    )
    captured: dict[str, object] = {}

    def fake_project(request, *, root):
        captured["request"] = request
        captured["root"] = root
        return _world()

    monkeypatch.setattr(projection_service, "project_world_graph", fake_project)

    response = projection_service.build_historical_recap_world_projection(
        tmp_path,
        RUN_ID,
    )

    assert response.run_id == RUN_ID
    assert response.source_revision_id
    assert response.source_sha256 == "sha256:" + "a" * 64
    assert response.world_id == "eldyrwild"
    assert response.snapshot.revision_id == "world-rev-25"
    assert response.node_views["node-bonogo"].label == "Bonogo"
    assert "dmb-node:node-bonogo" in response.markdown
    assert captured["request"].world_id == "eldyrwild"
    assert captured["request"].focus.session_id == "session-25"


def test_exact_run_projection_fails_closed_when_source_was_not_adopted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(projection_service, "get_extraction_run", lambda _root, _id: _run())
    monkeypatch.setattr(
        projection_service.source_service,
        "get_source_markdown",
        lambda **_kwargs: None,
    )

    with pytest.raises(
        projection_service.HistoricalRecapProjectionError,
        match="not adopted into APP-STATE",
    ) as error:
        projection_service.build_historical_recap_world_projection(tmp_path, RUN_ID)

    assert error.value.code == "source_content_unavailable"
    assert error.value.status_code == 404


def test_exact_run_projection_preserves_dungeonmind_failure_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(projection_service, "get_extraction_run", lambda _root, _id: _run())
    monkeypatch.setattr(
        projection_service.source_service,
        "get_source_markdown",
        lambda **_kwargs: _source(),
    )
    monkeypatch.setattr(
        projection_service,
        "project_world_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            projection_service.WorldGraphProjectionServiceError(
                "DungeonMind World unavailable",
                code="world_authority_unavailable",
                status_code=503,
            )
        ),
    )

    with pytest.raises(
        projection_service.HistoricalRecapProjectionError,
        match="World unavailable",
    ) as error:
        projection_service.build_historical_recap_world_projection(tmp_path, RUN_ID)

    assert error.value.code == "world_authority_unavailable"
    assert error.value.status_code == 503


def test_exact_run_projection_fails_closed_without_world_binding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(projection_service, "get_extraction_run", lambda _root, _id: _run())
    monkeypatch.setattr(
        projection_service.source_service,
        "get_source_markdown",
        lambda **_kwargs: _source().model_copy(update={"world_id": None}),
    )

    with pytest.raises(
        projection_service.HistoricalRecapProjectionError,
        match="no current World binding",
    ) as error:
        projection_service.build_historical_recap_world_projection(tmp_path, RUN_ID)

    assert error.value.code == "world_binding_unavailable"
    assert error.value.status_code == 409
