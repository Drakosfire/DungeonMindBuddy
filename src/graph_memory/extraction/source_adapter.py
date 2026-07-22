"""Generic source adapter protocol for production extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class NormalizedExtractionSource:
    """Source-domain-neutral extraction input."""

    source_artifact_id: str
    source_domain: str
    source_text: str
    source_sha256: str
    source_uri: str
    campaign_id: str | None
    session_id: str | None
    document_class: str | None = None
    source_span_index: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_domain: str

    def normalize(self) -> NormalizedExtractionSource: ...
