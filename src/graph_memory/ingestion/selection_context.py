"""Identity/precondition-only selection request; no Graph write authority."""

from __future__ import annotations

from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
RecordId = Annotated[
    str, Field(min_length=1, max_length=512, pattern=r"^\S(?:[^\r\n\t]*\S)?$")
]


class SelectionModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, alias_generator=to_camel, populate_by_name=True
    )


class IngestSourceSelection(SelectionModel):
    """Half-open Unicode code-point offsets in exact source, never UTF-16 units."""

    source_span_ref_id: RecordId
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=16384)

    @model_validator(mode="after")
    def ordered(self):
        if self.start >= self.end:
            raise ValueError("selection must have a positive half-open range")
        return self


class IngestSelectionContextRequest(SelectionModel):
    expected_run_revision: int = Field(ge=1)
    expected_candidate_sha256: Digest
    expected_source_sha256: Digest
    expected_span_index_sha256: Digest
    expected_world_id: RecordId | None
    node_ids: list[RecordId] = Field(default_factory=list, max_length=32)
    edge_ids: list[RecordId] = Field(default_factory=list, max_length=32)
    source_selection: IngestSourceSelection | None = None
    annotation: str | None = Field(default=None, min_length=1, max_length=8192)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.node_ids and not self.edge_ids and self.source_selection is None:
            raise ValueError("select a source passage, node or relationship")
        if len(self.node_ids) != len(set(self.node_ids)) or len(self.edge_ids) != len(
            set(self.edge_ids)
        ):
            raise ValueError("duplicate selection identities")
        return self


class AgentKnowledgeSelection(SelectionModel):
    """Exact submitted selector; resolved context is always rebuilt by Buddy."""

    run_id: RecordId
    context_request: IngestSelectionContextRequest
    expected_context_sha256: Digest
