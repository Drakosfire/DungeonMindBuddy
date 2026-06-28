from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from graph_memory.evidence.source_domain import SourceDomain


class GraphMemorySourceArtifact(BaseModel):
    """A source artifact that can provide evidence for graph memory."""

    model_config = ConfigDict(extra="allow", strict=True)

    source_artifact_id: str
    source_domain: SourceDomain | str
    campaign_id: str
    uri: str
