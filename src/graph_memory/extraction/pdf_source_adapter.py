"""PDF/OCR source adapter with page-lineage normalization."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from src.graph_memory.extraction.pdf_lineage import (
    PdfLineageError,
    PdfPageMap,
    assert_ocr_matches_page_map,
    build_pdf_page_span_id,
    build_pdf_source_artifact_id,
    normalize_digest,
    validate_page_map_payload,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource


def compute_bytes_sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def compute_text_sha256(text: str) -> str:
    return compute_bytes_sha256(text.encode("utf-8"))


class PdfOcrSourceAdapter:
    """Normalize a PDF identity + validated OCR derivation into extraction input."""

    source_domain = "statblock"

    def __init__(
        self,
        *,
        pdf_bytes: bytes | None = None,
        pdf_path: Path | None = None,
        pdf_sha256: str | None = None,
        ocr_text: str,
        page_map: Mapping[str, Any] | PdfPageMap,
        campaign_id: str | None = None,
        document_class: str | None = "mechanical",
        source_uri: str | None = None,
    ) -> None:
        if pdf_bytes is None and pdf_path is None and pdf_sha256 is None:
            raise PdfLineageError("pdf_bytes, pdf_path, or pdf_sha256 is required")
        self._pdf_bytes = pdf_bytes
        self._pdf_path = pdf_path
        self._pdf_sha256 = pdf_sha256
        self._ocr_text = ocr_text
        self._page_map_input = page_map
        self.campaign_id = campaign_id
        self.document_class = document_class
        self._source_uri = source_uri

    def _resolve_pdf_digest(self) -> str:
        if self._pdf_sha256 is not None:
            return normalize_digest(self._pdf_sha256)
        if self._pdf_bytes is not None:
            return compute_bytes_sha256(self._pdf_bytes)
        assert self._pdf_path is not None
        if not self._pdf_path.is_file():
            raise PdfLineageError(f"pdf path missing: {self._pdf_path}")
        return compute_bytes_sha256(self._pdf_path.read_bytes())

    def normalize(self) -> NormalizedExtractionSource:
        ocr_text = self._ocr_text if self._ocr_text.endswith("\n") else f"{self._ocr_text}\n"
        ocr_sha256 = compute_text_sha256(ocr_text)
        pdf_sha256 = self._resolve_pdf_digest()

        if isinstance(self._page_map_input, PdfPageMap):
            page_map = self._page_map_input
        else:
            payload = dict(self._page_map_input)
            payload.setdefault("pdf_sha256", pdf_sha256)
            payload.setdefault("ocr_sha256", ocr_sha256)
            page_map = validate_page_map_payload(payload)

        if page_map.pdf_sha256 != pdf_sha256:
            raise PdfLineageError("page map pdf_sha256 does not match PDF digest")
        if page_map.ocr_sha256 != ocr_sha256:
            raise PdfLineageError("page map ocr_sha256 does not match OCR digest")
        assert_ocr_matches_page_map(ocr_text=ocr_text, page_map=page_map)

        source_artifact_id = build_pdf_source_artifact_id(
            pdf_sha256=pdf_sha256,
            ocr_sha256=ocr_sha256,
        )
        source_uri = self._source_uri or f"pdf://{pdf_sha256.removeprefix('sha256:')[:12]}"
        spans: list[dict[str, Any]] = []
        char_cursor = 0
        for ordinal, region in enumerate(page_map.regions, start=1):
            span_id = build_pdf_page_span_id(
                pdf_sha256=pdf_sha256,
                page=region.page,
                region_id=region.region_id,
            )
            start = ocr_text.find(region.text)
            if start < 0:
                raise PdfLineageError(
                    f"unable to locate region {region.region_id} in OCR text"
                )
            end = start + len(region.text)
            spans.append(
                {
                    "span_id": span_id,
                    "source_span_ref_id": span_id,
                    "source_artifact_id": source_artifact_id,
                    "kind": "pdf_page_region",
                    "ordinal": ordinal,
                    "source_uri": source_uri,
                    "char_start": start,
                    "char_end": end,
                    "page": region.page,
                    "region_id": region.region_id,
                    "pdf_sha256": pdf_sha256,
                    "ocr_sha256": ocr_sha256,
                    "bbox": list(region.bbox) if region.bbox is not None else None,
                    "text": region.text,
                    "text_excerpt": region.text[:240],
                    "preview_only": True,
                    "lineage": {
                        "parent_pdf_sha256": pdf_sha256,
                        "ocr_sha256": ocr_sha256,
                        "page": region.page,
                        "region_id": region.region_id,
                    },
                }
            )
            char_cursor = max(char_cursor, end)

        span_index = {
            "schema": "dmb_source_span_index_v0",
            "version": "0.1",
            "campaign_id": self.campaign_id,
            "session_id": None,
            "source_sha256": ocr_sha256,
            "pdf_sha256": pdf_sha256,
            "ocr_sha256": ocr_sha256,
            "page_count": page_map.page_count,
            "paragraph_span_count": len(spans),
            "spans": spans,
            "lineage": {
                "parent_pdf_sha256": pdf_sha256,
                "ocr_sha256": ocr_sha256,
                "derived_from": "pdf_ocr",
            },
        }
        return NormalizedExtractionSource(
            source_artifact_id=source_artifact_id,
            source_domain=self.source_domain,
            source_text=ocr_text,
            source_sha256=ocr_sha256,
            source_uri=source_uri,
            campaign_id=self.campaign_id,
            session_id=None,
            document_class=self.document_class,
            source_span_index=span_index,
            metadata={
                "pdf_sha256": pdf_sha256,
                "ocr_sha256": ocr_sha256,
                "page_count": page_map.page_count,
                "page_map": page_map.to_dict(),
                "duplicate_policy": "reuse_canonical_pdf_ocr_identity",
            },
        )
