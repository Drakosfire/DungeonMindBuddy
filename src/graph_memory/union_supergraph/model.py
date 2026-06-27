from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _UnionSupergraphModel(BaseModel):
    """Base model for the union-supergraph read-model contract."""

    model_config = ConfigDict(extra="allow", strict=True)


class UnionSupergraphNodeState(_UnionSupergraphModel):
    """Known node state flags, while allowing the state map to expand."""

    memory_state: str | None = None
    canon_state: str | None = None
    approval_state: str | None = None


class UnionSupergraphEdgeState(_UnionSupergraphModel):
    """Known edge state flags, while allowing the state map to expand."""

    memory_state: str | None = None
    canon_state: str | None = None
    approval_state: str | None = None


class UnionSupergraphNode(_UnionSupergraphModel):
    node_id: str
    label: str
    kind: str
    role: str
    aliases: list[str] = Field(default_factory=list)
    source_domains: list[str]
    evidence_ref_ids: list[str]
    state: dict[str, Any]


class UnionSupergraphEdge(_UnionSupergraphModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    predicate: str
    label: str
    direction: str
    source_domains: list[str]
    session_ids: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str]
    state: dict[str, Any]


class UnionSupergraphEvidence(_UnionSupergraphModel):
    evidence_ref_id: str
    source_artifact_id: str
    source_domain: str
    evidence_role: str
    can_open_source: bool
    can_highlight_span: bool
    session_id: str | None = None
    source_span_ref_id: str | None = None
    locator: str | None = None
    uri: str | None = None
    source_locator: str | None = None
    line_ref: str | None = None


class UnionSupergraphSourceArtifact(_UnionSupergraphModel):
    source_artifact_id: str
    source_domain: str
    campaign_id: str
    uri: str


class UnionSupergraphAdjacencyItem(_UnionSupergraphModel):
    edge_id: str
    node_id: str
    anchored_to_focus_session: bool


class UnionSupergraphDiagnostics(_UnionSupergraphModel):
    canon_promotion: bool = False
    approved_memory_write: bool = False
    corpus_mutation: bool = False
    production_retrieval: bool = False


class UnionSupergraphStore(_UnionSupergraphModel):
    schema_: str = Field(validation_alias="schema", serialization_alias="schema")
    version: str
    campaign_id: str
    graph_id: str | None = None
    graph_domains: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    focus_session_id: str
    nodes: dict[str, UnionSupergraphNode]
    edges: dict[str, UnionSupergraphEdge]
    evidence: dict[str, UnionSupergraphEvidence]
    source_artifacts: dict[str, UnionSupergraphSourceArtifact]
    aliases: dict[str, str] = Field(default_factory=dict)
    adjacency: dict[str, list[UnionSupergraphAdjacencyItem]]
    diagnostics: UnionSupergraphDiagnostics

    @property
    def schema(self) -> str:
        return self.schema_
