"""Recap source adapter mapping existing recap descriptors into normalized input."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource


def compute_text_sha256(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _line_number_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def split_paragraph_spans(text: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\s*\Z)", text, flags=re.DOTALL):
        paragraph = match.group(0).strip("\n")
        if not paragraph.strip():
            continue
        start = match.start() + (len(match.group(0)) - len(match.group(0).lstrip("\n")))
        end = start + len(paragraph)
        spans.append(
            {
                "ordinal": len(spans) + 1,
                "text": paragraph,
                "char_start": start,
                "char_end": end,
                "line_start": _line_number_at(text, start),
                "line_end": _line_number_at(text, max(start, end - 1)),
            }
        )
    return spans


def build_recap_source_span_index(
    *,
    recap_text: str,
    campaign_id: str,
    session_id: str,
    source_uri: str,
    source_sha256: str,
) -> dict[str, Any]:
    source_artifact_id = f"artifact:recap:{campaign_id}:{session_id}"
    spans: list[dict[str, Any]] = [
        {
            "span_id": f"{session_id}:recap:full_text",
            "source_span_ref_id": f"{session_id}:recap:full_text",
            "source_artifact_id": source_artifact_id,
            "kind": "full_text",
            "ordinal": 0,
            "source_uri": source_uri,
            "char_start": 0,
            "char_end": len(recap_text),
            "line_start": 1,
            "line_end": max(1, len(recap_text.splitlines())),
            "text_excerpt": recap_text[:240],
            "preview_only": True,
        }
    ]
    for paragraph in split_paragraph_spans(recap_text):
        spans.append(
            {
                "span_id": f"{session_id}:recap:paragraph:{paragraph['ordinal']:03d}",
                "source_span_ref_id": f"{session_id}:recap:paragraph:{paragraph['ordinal']:03d}",
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
        "session_id": session_id,
        "source_sha256": source_sha256,
        "paragraph_span_count": len(spans) - 1,
        "spans": spans,
    }


class RecapSourceAdapter:
    source_domain = "recap"

    def __init__(
        self,
        *,
        campaign_id: str,
        session_id: str,
        recap_text: str | None = None,
        recap_path: Path | None = None,
        source_uri: str | None = None,
        source_artifact_id: str | None = None,
    ) -> None:
        if recap_text is None and recap_path is None:
            raise ValueError("recap_text or recap_path is required")
        self.campaign_id = campaign_id
        self.session_id = session_id
        self._recap_path = recap_path
        self._recap_text = recap_text
        self._source_uri = source_uri
        self._source_artifact_id = source_artifact_id

    def normalize(self) -> NormalizedExtractionSource:
        if self._recap_text is not None:
            text = self._recap_text
        else:
            assert self._recap_path is not None
            text = self._recap_path.read_text(encoding="utf-8")
        sha = compute_text_sha256(text)
        uri = self._source_uri or (
            self._recap_path.as_posix() if self._recap_path is not None else f"inline://{self.session_id}"
        )
        artifact_id = self._source_artifact_id or f"artifact:recap:{self.campaign_id}:{self.session_id}"
        span_index = build_recap_source_span_index(
            recap_text=text,
            campaign_id=self.campaign_id,
            session_id=self.session_id,
            source_uri=uri,
            source_sha256=sha,
        )
        return NormalizedExtractionSource(
            source_artifact_id=artifact_id,
            source_domain=self.source_domain,
            source_text=text,
            source_sha256=sha,
            source_uri=uri,
            campaign_id=self.campaign_id,
            session_id=self.session_id,
            document_class="recap",
            source_span_index=span_index,
        )
