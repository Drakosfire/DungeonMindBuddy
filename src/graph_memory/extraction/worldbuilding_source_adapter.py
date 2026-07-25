"""Worldbuilding Markdown source adapter with null-session support."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.graph_memory.extraction.recap_source_adapter import (
    compute_text_sha256,
    split_paragraph_spans,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource
from src.graph_memory.source_span import build_stable_source_span_id


def build_worldbuilding_source_span_index(
    *,
    source_text: str,
    source_artifact_id: str,
    source_uri: str,
    source_sha256: str,
    campaign_id: str | None,
) -> dict[str, Any]:
    digest = source_sha256.removeprefix("sha256:")
    full_span_id = build_stable_source_span_id(
        source_artifact_id=source_artifact_id,
        content_sha256=digest,
        start_line=1,
        end_line=max(1, len(source_text.splitlines())),
    )
    spans: list[dict[str, Any]] = [
        {
            "span_id": full_span_id,
            "source_span_ref_id": full_span_id,
            "source_artifact_id": source_artifact_id,
            "kind": "full_text",
            "ordinal": 0,
            "source_uri": source_uri,
            "char_start": 0,
            "char_end": len(source_text),
            "line_start": 1,
            "line_end": max(1, len(source_text.splitlines())),
            "text_excerpt": source_text[:240],
            "preview_only": True,
        }
    ]
    for paragraph in split_paragraph_spans(source_text):
        span_id = build_stable_source_span_id(
            source_artifact_id=source_artifact_id,
            content_sha256=digest,
            start_line=int(paragraph["line_start"]),
            end_line=int(paragraph["line_end"]),
        )
        spans.append(
            {
                "span_id": span_id,
                "source_span_ref_id": span_id,
                "source_artifact_id": source_artifact_id,
                "kind": "paragraph",
                "ordinal": paragraph["ordinal"],
                "source_uri": source_uri,
                "char_start": paragraph["char_start"],
                "char_end": paragraph["char_end"],
                "line_start": paragraph["line_start"],
                "line_end": paragraph["line_end"],
                "text": paragraph["text"],
                "text_excerpt": str(paragraph["text"])[:240],
                "preview_only": True,
            }
        )
    return {
        "schema": "dmb_source_span_index_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": None,
        "source_sha256": source_sha256,
        "paragraph_span_count": len(spans) - 1,
        "spans": spans,
    }


class WorldbuildingSourceAdapter:
    source_domain = "worldbuilding"

    def __init__(
        self,
        *,
        source_artifact_id: str,
        source_text: str | None = None,
        source_path: Path | None = None,
        source_uri: str | None = None,
        campaign_id: str | None = None,
        document_class: str | None = "lore",
    ) -> None:
        if source_text is None and source_path is None:
            raise ValueError("source_text or source_path is required")
        self.source_artifact_id = source_artifact_id
        self._source_text = source_text
        self._source_path = source_path
        self._source_uri = source_uri
        self.campaign_id = campaign_id
        self.document_class = document_class

    def normalize(self) -> NormalizedExtractionSource:
        if self._source_text is not None:
            text = self._source_text
        else:
            assert self._source_path is not None
            text = self._source_path.read_text(encoding="utf-8")
        sha = compute_text_sha256(text)
        uri = self._source_uri or (
            self._source_path.as_posix()
            if self._source_path is not None
            else f"inline://{self.source_artifact_id}"
        )
        span_index = build_worldbuilding_source_span_index(
            source_text=text,
            source_artifact_id=self.source_artifact_id,
            source_uri=uri,
            source_sha256=sha,
            campaign_id=self.campaign_id,
        )
        return NormalizedExtractionSource(
            source_artifact_id=self.source_artifact_id,
            source_domain=self.source_domain,
            source_text=text,
            source_sha256=sha,
            source_uri=uri,
            campaign_id=self.campaign_id,
            session_id=None,
            document_class=self.document_class,
            source_span_index=span_index,
        )
