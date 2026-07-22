"""PDF digest, page span, and OCR validation proofs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.graph_memory.extraction.pdf_lineage import (
    PdfLineageError,
    build_pdf_page_span_id,
    build_pdf_source_artifact_id,
    validate_page_map_payload,
)
from src.graph_memory.extraction.pdf_source_adapter import (
    PdfOcrSourceAdapter,
    compute_bytes_sha256,
    compute_text_sha256,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "graph_memory_layer"
    / "fixtures"
    / "pdf_lineage_fixture.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_pdf_and_ocr_digests_are_stable() -> None:
    fixture = _fixture()
    pdf_bytes = fixture["pdf_bytes_utf8"].encode("utf-8")
    ocr = fixture["ocr_text"]
    pdf_digest = compute_bytes_sha256(pdf_bytes)
    ocr_digest = compute_text_sha256(ocr if ocr.endswith("\n") else f"{ocr}\n")
    artifact_id = build_pdf_source_artifact_id(
        pdf_sha256=pdf_digest, ocr_sha256=ocr_digest
    )
    assert artifact_id.startswith("artifact:pdf:")
    assert artifact_id == build_pdf_source_artifact_id(
        pdf_sha256=pdf_digest, ocr_sha256=ocr_digest
    )


def test_page_span_ids_embed_pdf_page_region() -> None:
    digest = "sha256:" + ("ab" * 32)
    span_id = build_pdf_page_span_id(pdf_sha256=digest, page=2, region_id="title")
    assert span_id.startswith("span:pdf:")
    assert ":p2:title" in span_id


def test_invalid_page_map_and_empty_ocr_fail_closed() -> None:
    with pytest.raises(PdfLineageError):
        validate_page_map_payload(
            {
                "pdf_sha256": "sha256:" + ("11" * 32),
                "ocr_sha256": "sha256:" + ("22" * 32),
                "page_count": 1,
                "regions": [],
            }
        )
    with pytest.raises(PdfLineageError):
        PdfOcrSourceAdapter(
            pdf_sha256="sha256:" + ("11" * 32),
            ocr_text="   ",
            page_map={
                "page_count": 1,
                "regions": [{"region_id": "r1", "page": 1, "text": "x"}],
            },
        ).normalize()


def test_adapter_preserves_page_lineage_on_spans() -> None:
    fixture = _fixture()
    pdf_bytes = fixture["pdf_bytes_utf8"].encode("utf-8")
    adapter = PdfOcrSourceAdapter(
        pdf_bytes=pdf_bytes,
        ocr_text=fixture["ocr_text"],
        page_map=fixture["page_map"],
        campaign_id="longmont-c2",
    )
    source = adapter.normalize()
    assert source.session_id is None
    assert source.source_domain == "statblock"
    assert source.metadata["pdf_sha256"].startswith("sha256:")
    assert source.source_span_index["page_count"] == 1
    spans = source.source_span_index["spans"]
    assert len(spans) == 3
    for span in spans:
        assert span["kind"] == "pdf_page_region"
        assert span["page"] == 1
        assert span["lineage"]["parent_pdf_sha256"] == source.metadata["pdf_sha256"]
        assert span["source_span_ref_id"].startswith("span:pdf:")


def test_duplicate_pdf_ocr_identity_is_stable() -> None:
    fixture = _fixture()
    pdf_bytes = fixture["pdf_bytes_utf8"].encode("utf-8")
    first = PdfOcrSourceAdapter(
        pdf_bytes=pdf_bytes,
        ocr_text=fixture["ocr_text"],
        page_map=fixture["page_map"],
    ).normalize()
    second = PdfOcrSourceAdapter(
        pdf_bytes=pdf_bytes,
        ocr_text=fixture["ocr_text"],
        page_map=fixture["page_map"],
    ).normalize()
    assert first.source_artifact_id == second.source_artifact_id
