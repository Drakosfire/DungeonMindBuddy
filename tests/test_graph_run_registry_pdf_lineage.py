"""ExtractionRun registry persistence for PDF page evidence."""

from __future__ import annotations

import json
from pathlib import Path

from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)
from apps.live_control_server.services.graph_run_registry import (
    create_extraction_run,
    get_extraction_run,
    update_extraction_run_status,
)
from src.graph_memory.extraction.pdf_source_adapter import PdfOcrSourceAdapter

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "graph_memory_layer"
    / "fixtures"
    / "pdf_lineage_fixture.json"
)


def test_extraction_run_reload_preserves_page_evidence(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    source = PdfOcrSourceAdapter(
        pdf_bytes=fixture["pdf_bytes_utf8"].encode("utf-8"),
        ocr_text=fixture["ocr_text"],
        page_map=fixture["page_map"],
        campaign_id="longmont-c2",
    ).normalize()

    run_dir = tmp_path / "out" / "graph_memory" / "runs" / "pdf"
    run_dir.mkdir(parents=True)
    span_path = run_dir / "source_span_index.json"
    span_path.write_text(
        json.dumps(source.source_span_index, indent=2) + "\n", encoding="utf-8"
    )
    candidate_path = run_dir / "candidate_graph.json"
    candidate_path.write_text(
        json.dumps(
            {
                "schema": "dmb_candidate_graph_preview_v0",
                "session_id": None,
                "campaign_id": "longmont-c2",
                "nodes": [],
                "edges": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=source.source_uri,
            exists=True,
            sha256=source.source_sha256,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=span_path.as_posix(),
            exists=True,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=candidate_path.as_posix(),
            exists=True,
        ),
    }
    created = create_extraction_run(
        tmp_path,
        source_artifact_id=source.source_artifact_id,
        source_domain=source.source_domain,
        campaign_id=source.campaign_id,
        session_id=None,
        profile_id="pdf_mechanical_pilot_v0@0.1",
        components=components,
        status=ExtractionRunStatus.DRAFT,
    )
    updated = update_extraction_run_status(
        tmp_path,
        created.run_id,
        status=ExtractionRunStatus.REVIEWABLE,
        components=components,
    )
    assert updated.status == ExtractionRunStatus.REVIEWABLE

    reloaded = get_extraction_run(tmp_path, created.run_id)
    assert reloaded.source_artifact_id == source.source_artifact_id
    assert reloaded.session_id is None
    span_uri = reloaded.components["source_span_index"].uri
    payload = json.loads(Path(span_uri).read_text(encoding="utf-8"))
    assert payload["pdf_sha256"] == source.metadata["pdf_sha256"]
    assert all(span["kind"] == "pdf_page_region" for span in payload["spans"])
    assert all("page" in span and "region_id" in span for span in payload["spans"])
