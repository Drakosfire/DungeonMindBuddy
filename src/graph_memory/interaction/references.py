"""Graph references, source citations, and inference references."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.interaction.schema_constants import (
    GRAPH_REFERENCE_SCHEMA,
    INFERENCE_REFERENCE_SCHEMA,
    SOURCE_CITATION_SCHEMA,
)


class GraphReference(BaseModel):
    """Clickable durable graph object/claim identity. Not a source citation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_graph_reference_v1"] = Field(
        default=GRAPH_REFERENCE_SCHEMA,
        alias="schema",
    )
    kind: Literal["graph_reference"] = "graph_reference"
    revision_id: str
    object_kind: Literal["assertion", "node", "relationship", "claim"]
    object_id: str
    label: str | None = None
    claim_id: str | None = None


class SourceCitation(BaseModel):
    """Created only after a successful integrity-checked source read."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_source_citation_v1"] = Field(
        default=SOURCE_CITATION_SCHEMA,
        alias="schema",
    )
    kind: Literal["source_citation"] = "source_citation"
    revision_id: str
    anchor_id: str
    source_artifact_id: str | None = None
    content_sha256: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    truncated: bool = False
    source_read_id: str | None = None


class InferenceReference(BaseModel):
    """Disclosed noncanonical Hermes inference with supporting claim IDs."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_inference_reference_v1"] = Field(
        default=INFERENCE_REFERENCE_SCHEMA,
        alias="schema",
    )
    kind: Literal["inference_reference"] = "inference_reference"
    inference_id: str
    text: str
    supporting_claim_ids: list[str] = Field(default_factory=list)
    reasoning_label: str = "prep_implication"
    speculation: Literal["low", "medium", "high"] = "low"
    canonical: Literal[False] = False


__all__ = [
    "GraphReference",
    "InferenceReference",
    "SourceCitation",
]
