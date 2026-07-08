from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from graph_memory.evidence.evidence_ref import GraphMemoryEvidenceRef
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact


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


class UnionSupergraphEvidence(GraphMemoryEvidenceRef):
    """Evidence reference as used by the union-supergraph read model."""


class UnionSupergraphSourceArtifact(GraphMemorySourceArtifact):
    """Source artifact as used by the union-supergraph read model."""


class UnionSupergraphAdjacencyItem(_UnionSupergraphModel):
    edge_id: str
    node_id: str
    direction: str
    label: str | None = None
    anchored_to_focus_session: bool


class UnionSupergraphDiagnostics(_UnionSupergraphModel):
    canon_promotion: bool = False
    approved_memory_write: bool = False
    corpus_mutation: bool = False
    production_retrieval: bool = False


class UnionIdentityRedirect(_UnionSupergraphModel):
    """Durable graph identity redirect: merged-away node id -> canonical survivor id."""

    redirect_id: str
    campaign_id: str
    from_node_id: str
    to_node_id: str
    assertion_id: str
    event_id: str | None = None
    merge_reason: str | None = None
    created_at: str
    status: Literal["active", "retracted"]
    materialization_pass_id: str

    @field_validator("from_node_id", "to_node_id")
    @classmethod
    def _require_non_empty_node_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("node id must be non-empty")
        return value

    @field_validator("to_node_id")
    @classmethod
    def _reject_self_redirect(cls, value: str, info) -> str:
        from_node_id = info.data.get("from_node_id")
        if from_node_id is not None and value == from_node_id:
            raise ValueError("from_node_id and to_node_id must differ")
        return value


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
    identity_redirects: list[UnionIdentityRedirect] = Field(default_factory=list)
    adjacency: dict[str, list[UnionSupergraphAdjacencyItem]]
    diagnostics: UnionSupergraphDiagnostics

    @property
    def schema(self) -> str:
        return self.schema_
