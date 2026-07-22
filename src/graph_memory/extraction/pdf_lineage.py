"""PDF/OCR page and region evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class PdfLineageError(ValueError):
    """Fail-closed PDF/OCR lineage validation error."""


@dataclass(frozen=True)
class PdfPageRegion:
    region_id: str
    page: int
    text: str
    bbox: tuple[float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "region_id": self.region_id,
            "page": self.page,
            "text": self.text,
        }
        if self.bbox is not None:
            payload["bbox"] = list(self.bbox)
        return payload


@dataclass(frozen=True)
class PdfPageMap:
    """Validated page map for a PDF-derived OCR artifact."""

    pdf_sha256: str
    ocr_sha256: str
    page_count: int
    regions: tuple[PdfPageRegion, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "dmb_pdf_page_map_v1",
            "version": "0.1",
            "pdf_sha256": self.pdf_sha256,
            "ocr_sha256": self.ocr_sha256,
            "page_count": self.page_count,
            "regions": [region.to_dict() for region in self.regions],
        }


def normalize_digest(raw: str | None) -> str:
    text = (raw or "").strip().lower()
    if text.startswith("sha256:"):
        text = text[len("sha256:") :]
    text = text.strip()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise PdfLineageError("content digest must be sha256 hex")
    return f"sha256:{text}"


def build_pdf_source_artifact_id(*, pdf_sha256: str, ocr_sha256: str) -> str:
    pdf_digest = normalize_digest(pdf_sha256).removeprefix("sha256:")
    ocr_digest = normalize_digest(ocr_sha256).removeprefix("sha256:")
    return f"artifact:pdf:{pdf_digest[:12]}:ocr:{ocr_digest[:12]}"


def build_pdf_page_span_id(
    *,
    pdf_sha256: str,
    page: int,
    region_id: str,
) -> str:
    if page < 1:
        raise PdfLineageError("page numbers are 1-indexed and must be >= 1")
    region = (region_id or "").strip()
    if not region:
        raise PdfLineageError("region_id is required")
    digest = normalize_digest(pdf_sha256).removeprefix("sha256:")
    return f"span:pdf:{digest[:12]}:p{page}:{region}"


def validate_page_map_payload(payload: Mapping[str, Any]) -> PdfPageMap:
    """Validate a page map payload and return a typed page map."""
    pdf_sha256 = normalize_digest(str(payload.get("pdf_sha256") or ""))
    ocr_sha256 = normalize_digest(str(payload.get("ocr_sha256") or ""))
    page_count = payload.get("page_count")
    if not isinstance(page_count, int) or page_count < 1:
        raise PdfLineageError("page_count must be a positive int")

    raw_regions = payload.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise PdfLineageError("page map requires at least one region")

    regions: list[PdfPageRegion] = []
    seen_region_ids: set[str] = set()
    for index, row in enumerate(raw_regions):
        if not isinstance(row, Mapping):
            raise PdfLineageError(f"regions[{index}] must be an object")
        region_id = str(row.get("region_id") or "").strip()
        if not region_id:
            raise PdfLineageError(f"regions[{index}] missing region_id")
        if region_id in seen_region_ids:
            raise PdfLineageError(f"duplicate region_id {region_id!r}")
        seen_region_ids.add(region_id)
        page = row.get("page")
        if not isinstance(page, int) or page < 1 or page > page_count:
            raise PdfLineageError(
                f"regions[{index}] page must be in 1..{page_count}"
            )
        text = str(row.get("text") or "")
        if not text.strip():
            raise PdfLineageError(f"regions[{index}] text is empty")
        bbox = row.get("bbox")
        parsed_bbox: tuple[float, float, float, float] | None = None
        if bbox is not None:
            if not isinstance(bbox, Sequence) or len(bbox) != 4:
                raise PdfLineageError(f"regions[{index}] bbox must have 4 numbers")
            parsed_bbox = tuple(float(v) for v in bbox)  # type: ignore[assignment]
        regions.append(
            PdfPageRegion(
                region_id=region_id,
                page=page,
                text=text,
                bbox=parsed_bbox,
            )
        )

    return PdfPageMap(
        pdf_sha256=pdf_sha256,
        ocr_sha256=ocr_sha256,
        page_count=page_count,
        regions=tuple(regions),
    )


def assert_ocr_matches_page_map(*, ocr_text: str, page_map: PdfPageMap) -> None:
    """Fail closed when OCR text cannot satisfy the page map regions."""
    if not (ocr_text or "").strip():
        raise PdfLineageError("OCR text is empty")
    missing = [
        region.region_id
        for region in page_map.regions
        if region.text.strip() not in ocr_text
    ]
    if missing:
        raise PdfLineageError(
            "OCR text missing page-map regions: " + ", ".join(missing[:5])
        )
