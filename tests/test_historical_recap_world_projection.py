from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

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
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionEvidenceView,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTrustBoundary,
)


RUN_ID = "graph-ingest:longmont-c2:session-25:20260808T005650Z"
ARTIFACT_ID = "artifact:recap:longmont-c2:session-25:fd38b5915b32"
OTHER_ARTIFACT_ID = "artifact:recap:longmont-c2:session-10:deadbeefdead"
SOURCE_REVISION_ID = UUID("8ed1e034-23c6-4295-b2ff-05d5cdd643a9")
MARKDOWN = "# Session 25\n\nBonogo arrives.\n"
WAREHOUSE_LINE = "Orik and Brin sheltered in the warehouse after the raid."
SIDECAR_POISON = "POISON sidecar paragraph that must never be attached"


def _run(*, digest: str = "a" * 64) -> ExtractionRun:
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
                sha256="sha256:" + digest,
            )
        },
    )


def _source(
    *,
    markdown: str = MARKDOWN,
    digest: str = "a" * 64,
    source_revision_id: UUID | None = None,
) -> SourceMarkdownRecord:
    return SourceMarkdownRecord(
        source_revision_id=source_revision_id or uuid4(),
        source_artifact_id=ARTIFACT_ID,
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        content_sha256=digest,
        media_type="text/markdown",
        encoding="utf-8",
        markdown=markdown,
        lineage={"adopted_from_run_id": RUN_ID},
        created_at=datetime.now(UTC),
    )


def _c2s25_markdown() -> str:
    lines = [f"Line {index}." for index in range(1, 24)]
    lines[22] = WAREHOUSE_LINE
    return "\n".join(lines) + "\n"


def _digest_for(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _span_id(digest: str, *, prefix: str | None = None) -> str:
    bound = (prefix or digest[:12]).lower()
    return f"evidence:{ARTIFACT_ID}:span:{bound}:23-23"


def _world(
    *,
    evidence_artifact_id: str = ARTIFACT_ID,
    span_id: str | None = None,
    sidecar_excerpt: str | None = None,
) -> WorldGraphProjection:
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
    evidence_ref_id = "evidence:c2s25:orik-brin"
    adjacency = [
        WorldGraphProjectionAdjacencyCandidate(
            edge_id="edge:orik:associated_with:brin",
            node_id="node:brin",
            label="Brin",
            kind="npc",
            predicate="associated_with",
            direction="outgoing",
            anchored_to_focus_session=True,
            source_domains=["recap"],
            evidence_ref_ids=[evidence_ref_id],
            edge_label="associated with",
            session_ids=["session-25"],
            campaign_scope="longmont-c2",
            related_summary="Known companion.",
            source_excerpt=sidecar_excerpt,
            source_excerpt_is_full_paragraph=bool(sidecar_excerpt),
            source_excerpt_highlight_spans=[],
        )
    ]
    orik = WorldGraphProjectionNodeView(
        node_id="node:orik",
        label="Orik",
        kind="npc",
        role="npc",
        aliases=["Orik"],
        source_domains=["recap"],
        summary="A Mireward defender.",
        anchored_to_focus_session=True,
        campaign_scope="longmont-c2",
        evidence_badges=[],
        adjacency=adjacency,
        suggested_expansions=[],
        evidence_ref_ids=[evidence_ref_id],
        source_artifact_ids=[evidence_artifact_id],
    )
    evidence = []
    if span_id is not None:
        evidence.append(
            WorldGraphProjectionEvidenceView(
                evidence_ref_id=evidence_ref_id,
                source_artifact_id=evidence_artifact_id,
                source_domain="recap",
                session_id="session-25",
                campaign_id="longmont-c2",
                source_span_ref_id=span_id,
                locator_status="unverified",
            )
        )
    return WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=snapshot,
        summary=WorldGraphProjectionSummary(
            node_count=1,
            relationship_count=1,
            attribute_count=0,
            evidence_count=len(evidence),
            source_artifact_count=1,
        ),
        nodes=[orik],
        evidence=evidence,
        trust_boundary=WorldGraphProjectionTrustBoundary(
            can_trust=["current World snapshot"],
            cannot_trust=["historical identity"],
        ),
    )


def _install_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    run: ExtractionRun,
    source: SourceMarkdownRecord,
    world: WorldGraphProjection,
) -> dict[str, object]:
    captured: dict[str, object] = {"calls": 0}
    monkeypatch.setattr(projection_service, "world_graph_root", lambda: tmp_path / "world-root")
    monkeypatch.setattr(projection_service, "get_extraction_run", lambda _root, _id: run)
    monkeypatch.setattr(
        projection_service.source_service,
        "get_source_markdown",
        lambda **_kwargs: source,
    )

    def fake_project(request, *, root, hydrate_product_local_excerpts=True):
        captured["calls"] = int(captured["calls"]) + 1
        captured["request"] = request
        captured["root"] = root
        captured["hydrate_product_local_excerpts"] = hydrate_product_local_excerpts
        return world

    monkeypatch.setattr(projection_service, "project_world_graph", fake_project)
    return captured


def test_exact_run_projection_uses_durable_source_and_current_world(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    world_root = tmp_path / "world-root"
    monkeypatch.setattr(projection_service, "world_graph_root", lambda: world_root)
    monkeypatch.setattr(projection_service, "get_extraction_run", lambda _root, _id: _run())
    monkeypatch.setattr(
        projection_service.source_service,
        "get_source_markdown",
        lambda **_kwargs: _source(),
    )
    captured: dict[str, object] = {}

    def fake_project(request, *, root, hydrate_product_local_excerpts=True):
        captured["request"] = request
        captured["root"] = root
        captured["hydrate_product_local_excerpts"] = hydrate_product_local_excerpts
        return WorldGraphProjection(
            schema="dmb_world_graph_projection_v1",
            snapshot=WorldGraphProjectionSnapshot(
                world_id="eldyrwild",
                campaign_id="longmont-c2",
                revision_id="world-rev-25",
                head_revision_id="world-rev-25",
                is_head=True,
                focus=WorldGraphProjectionFocus(
                    kind="session",
                    campaign_id="longmont-c2",
                    session_id="session-25",
                ),
                admissibility="gm",
                scope_mode="campaign",
            ),
            summary=WorldGraphProjectionSummary(
                node_count=1,
                relationship_count=0,
                attribute_count=0,
                evidence_count=0,
                source_artifact_count=0,
            ),
            nodes=[
                WorldGraphProjectionNodeView(
                    node_id="node-bonogo",
                    label="Bonogo",
                    kind="character",
                    role="npc",
                )
            ],
            trust_boundary=WorldGraphProjectionTrustBoundary(
                can_trust=["current World snapshot"],
                cannot_trust=["historical identity"],
            ),
        )

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
    assert captured["root"] == world_root
    assert captured["hydrate_product_local_excerpts"] is False


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


def test_orik_brin_excerpt_comes_from_app_state_without_source_sidecar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown = _c2s25_markdown()
    digest = _digest_for(markdown)
    span_id = _span_id(digest)
    sidecar = tmp_path / "source_span_index.json"
    sidecar.write_text(
        json.dumps({"spans": [{"span_id": span_id, "paragraph_text": SIDECAR_POISON}]}),
        encoding="utf-8",
    )
    captured = _install_projection(
        monkeypatch,
        tmp_path,
        run=_run(digest=digest),
        source=_source(
            markdown=markdown,
            digest=digest,
            source_revision_id=SOURCE_REVISION_ID,
        ),
        world=_world(span_id=span_id, sidecar_excerpt=SIDECAR_POISON),
    )

    response = projection_service.build_historical_recap_world_projection(tmp_path, RUN_ID)
    relationship = response.node_views["node:orik"].adjacency[0]

    assert captured["hydrate_product_local_excerpts"] is False
    assert captured["calls"] == 1
    assert response.source_revision_id == str(SOURCE_REVISION_ID)
    assert response.source_sha256 == f"sha256:{digest}"
    assert response.snapshot.revision_id == "world-rev-25"
    assert response.snapshot.head_revision_id == "world-rev-25"
    assert relationship.edge_id == "edge:orik:associated_with:brin"
    assert relationship.node_id == "node:brin"
    assert relationship.predicate == "associated_with"
    assert relationship.direction == "outgoing"
    assert relationship.source_excerpt == WAREHOUSE_LINE
    assert relationship.source_excerpt_is_full_paragraph is True
    assert relationship.source_excerpt_highlight_spans == []
    assert SIDECAR_POISON not in (relationship.source_excerpt or "")


def test_mismatched_digest_prefix_does_not_attach_excerpt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown = _c2s25_markdown()
    digest = _digest_for(markdown)
    captured = _install_projection(
        monkeypatch,
        tmp_path,
        run=_run(digest=digest),
        source=_source(markdown=markdown, digest=digest),
        world=_world(span_id=_span_id(digest, prefix="fd38b5915b32")),
    )

    response = projection_service.build_historical_recap_world_projection(tmp_path, RUN_ID)
    relationship = response.node_views["node:orik"].adjacency[0]

    assert captured["calls"] == 1
    assert relationship.node_id == "node:brin"
    assert relationship.source_excerpt is None
    assert relationship.source_excerpt_is_full_paragraph is False
    assert relationship.source_excerpt_highlight_spans == []
    assert digest[:12] != "fd38b5915b32"


def test_cross_artifact_evidence_does_not_attach_selected_source_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown = _c2s25_markdown()
    digest = _digest_for(markdown)
    captured = _install_projection(
        monkeypatch,
        tmp_path,
        run=_run(digest=digest),
        source=_source(markdown=markdown, digest=digest),
        world=_world(
            evidence_artifact_id=OTHER_ARTIFACT_ID,
            span_id=_span_id(digest),
        ),
    )

    response = projection_service.build_historical_recap_world_projection(tmp_path, RUN_ID)
    relationship = response.node_views["node:orik"].adjacency[0]

    assert captured["calls"] == 1
    assert relationship.evidence_ref_ids == ["evidence:c2s25:orik-brin"]
    assert relationship.source_excerpt is None
    assert WAREHOUSE_LINE not in (relationship.source_excerpt or "")
