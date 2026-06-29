from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from graph_memory.evidence.source_domain import SourceDomain


class GraphMemoryEvidenceRef(BaseModel):
    """A provenance-bearing evidence reference for graph memory."""

    model_config = ConfigDict(extra="allow", strict=True)

    evidence_ref_id: str
    source_artifact_id: str
    source_domain: SourceDomain | str
    evidence_role: str
    can_open_source: bool
    can_highlight_span: bool
    session_id: str | None = None
    source_span_ref_id: str | None = None
    locator: str | None = None
    uri: str | None = None
    source_locator: str | None = None
    line_ref: str | None = None

    @property
    def is_session_scoped(self) -> bool:
        return self.session_id is not None

    @property
    def has_source_locator(self) -> bool:
        return any(
            [
                self.source_span_ref_id,
                self.locator,
                self.uri,
                self.source_locator,
                self.line_ref,
            ]
        )
