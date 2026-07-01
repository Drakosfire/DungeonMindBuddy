"""Read-only pass-level manual review of vocabulary-ablation candidate graphs.

Loads the checked-in manual-review artifact produced by
``evals/graph_memory_layer/run_vocabulary_ablation_expanded_beds_dogfood.py``
and reshapes it for the Plan surface: per bed, per node/edge pass, the
vocabulary prompt text shown to the model alongside the extracted nodes/edges
for each variant (baseline vs edge_and_node_packet). This is a diagnostic
review surface, not a canon promotion path — no writes, no corpus mutation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field

from graph_memory.identity_resolution import node_type_class

MANUAL_REVIEW_SCHEMA = "dmb_graph_manual_review_v1"
MANUAL_REVIEW_VERSION = "0.1"

MANUAL_REVIEW_ARTIFACT_REL = (
    "evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/"
    "baseline_vs_edge_and_node_manual_review.json"
)

NODE_PASS_NAMES: tuple[str, ...] = (
    "actor_pass",
    "location_pass",
    "collective_pass",
    "object_pass",
    "thread_pass",
)
EDGE_PASS_NAME = "edge_pass"
ALL_PASS_NAMES: tuple[str, ...] = (*NODE_PASS_NAMES, EDGE_PASS_NAME)

_PASS_NAME_FOR_NODE_CLASS: dict[str, str] = {
    "actor": "actor_pass",
    "place": "location_pass",
    "collective": "collective_pass",
    "object": "object_pass",
    "thread": "thread_pass",
    "phenomenon": "thread_pass",
}


class GraphManualReviewError(ValueError):
    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class ManualReviewBedSummary(BaseModel):
    bed_id: str
    campaign_id: str | None = None
    session_id: str | None = None
    source_label: str | None = None
    variant_names: list[str] = Field(default_factory=list)


class ManualReviewBedsResponse(BaseModel):
    schema_version: Literal["dmb_graph_manual_review_beds_v1"] = "dmb_graph_manual_review_beds_v1"
    version: str = MANUAL_REVIEW_VERSION
    generated_at: str | None = None
    model_id: str | None = None
    beds: list[ManualReviewBedSummary] = Field(default_factory=list)


class ManualReviewNode(BaseModel):
    node_id: str
    label: str
    node_type: str
    pass_name: str | None = None
    description: str | None = None
    confidence: str | None = None
    importance: str | None = None
    corpus_ref: str | dict[str, Any] | None = None
    evidence_span_ids: list[str] = Field(default_factory=list)
    anchor_quotes: list[str] = Field(default_factory=list)


class ManualReviewEdge(BaseModel):
    edge_id: str
    from_node_id: str
    to_node_id: str
    from_label: str | None = None
    to_label: str | None = None
    relationship_type: str
    predicate_family: str | None = None
    confidence: str | None = None
    evidence_span_ids: list[str] = Field(default_factory=list)
    anchor_quotes: list[str] = Field(default_factory=list)


class ManualReviewVariantDetail(BaseModel):
    variant_name: str
    node_count: int = 0
    edge_count: int = 0
    cost_usd: float | None = None
    nodes: list[ManualReviewNode] = Field(default_factory=list)
    edges: list[ManualReviewEdge] = Field(default_factory=list)
    node_kinds: dict[str, int] = Field(default_factory=dict)
    edge_predicates: dict[str, int] = Field(default_factory=dict)
    gold_comparison: dict[str, Any] = Field(default_factory=dict)
    party_context: dict[str, Any] = Field(default_factory=dict)


class ManualReviewBedDetail(BaseModel):
    schema_version: Literal["dmb_graph_manual_review_bed_v1"] = "dmb_graph_manual_review_bed_v1"
    version: str = MANUAL_REVIEW_VERSION
    bed_id: str
    campaign_id: str | None = None
    session_id: str | None = None
    source_label: str | None = None
    generated_at: str | None = None
    model_id: str | None = None
    node_prompt_contexts: dict[str, str] = Field(default_factory=dict)
    edge_prompt_context: str = ""
    variant_names: list[str] = Field(default_factory=list)
    variants: dict[str, ManualReviewVariantDetail] = Field(default_factory=dict)


def _manual_review_path(root: Path) -> Path:
    return root / MANUAL_REVIEW_ARTIFACT_REL


def _load_manual_review_payload(root: Path) -> dict[str, Any]:
    path = _manual_review_path(root)
    if not path.exists():
        raise GraphManualReviewError(
            f"manual-review artifact not found: {MANUAL_REVIEW_ARTIFACT_REL}", status_code=404
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _find_bed(payload: Mapping[str, Any], bed_id: str) -> Mapping[str, Any]:
    for bed in payload.get("beds", []) or []:
        if isinstance(bed, Mapping) and bed.get("bed_id") == bed_id:
            return bed
    raise GraphManualReviewError(f"unknown manual-review bed: {bed_id}", status_code=404)


def _evidence_span_ids(evidence_refs: Any) -> list[str]:
    span_ids: list[str] = []
    if not isinstance(evidence_refs, list):
        return span_ids
    for ref in evidence_refs:
        if isinstance(ref, Mapping):
            span_id = ref.get("source_span_ref_id")
            if span_id:
                span_ids.append(str(span_id))
    return span_ids


def _evidence_anchor_quotes(evidence_refs: Any) -> list[str]:
    quotes: list[str] = []
    if not isinstance(evidence_refs, list):
        return quotes
    for ref in evidence_refs:
        if isinstance(ref, Mapping):
            for quote in ref.get("anchor_quotes") or []:
                if quote:
                    quotes.append(str(quote))
    return quotes


def _pass_name_for_node_type(node_type: str) -> str | None:
    return _PASS_NAME_FOR_NODE_CLASS.get(node_type_class(node_type))


def _build_node(raw: Mapping[str, Any]) -> ManualReviewNode:
    node_type = str(raw.get("node_type") or "")
    return ManualReviewNode(
        node_id=str(raw.get("node_id") or ""),
        label=str(raw.get("label") or ""),
        node_type=node_type,
        pass_name=_pass_name_for_node_type(node_type),
        description=raw.get("description"),
        confidence=raw.get("confidence"),
        importance=raw.get("importance"),
        corpus_ref=raw.get("corpus_ref"),
        evidence_span_ids=_evidence_span_ids(raw.get("evidence_refs")),
        anchor_quotes=_evidence_anchor_quotes(raw.get("evidence_refs")),
    )


def _build_edge(raw: Mapping[str, Any], label_by_id: Mapping[str, str]) -> ManualReviewEdge:
    from_id = str(raw.get("from_node_id") or "")
    to_id = str(raw.get("to_node_id") or "")
    return ManualReviewEdge(
        edge_id=str(raw.get("edge_id") or ""),
        from_node_id=from_id,
        to_node_id=to_id,
        from_label=label_by_id.get(from_id),
        to_label=label_by_id.get(to_id),
        relationship_type=str(raw.get("relationship_type") or raw.get("label") or ""),
        predicate_family=raw.get("predicate_family"),
        confidence=raw.get("confidence"),
        evidence_span_ids=_evidence_span_ids(raw.get("evidence_refs")),
        anchor_quotes=_evidence_anchor_quotes(raw.get("evidence_refs")),
    )


def _build_variant(variant_name: str, raw: Mapping[str, Any]) -> ManualReviewVariantDetail:
    graph = raw.get("candidate_graph", {}) if isinstance(raw.get("candidate_graph"), Mapping) else {}
    raw_nodes = [n for n in (graph.get("nodes") or []) if isinstance(n, Mapping)]
    raw_edges = [e for e in (graph.get("edges") or []) if isinstance(e, Mapping)]
    label_by_id = {str(n.get("node_id")): str(n.get("label") or "") for n in raw_nodes}
    nodes = [_build_node(n) for n in raw_nodes]
    edges = [_build_edge(e, label_by_id) for e in raw_edges]
    return ManualReviewVariantDetail(
        variant_name=variant_name,
        node_count=int(raw.get("node_count") or len(nodes)),
        edge_count=int(raw.get("edge_count") or len(edges)),
        cost_usd=raw.get("cost_usd"),
        nodes=nodes,
        edges=edges,
        node_kinds=dict(raw.get("node_kinds") or {}),
        edge_predicates=dict(raw.get("edge_predicates") or {}),
        gold_comparison=dict(raw.get("gold_comparison") or {}),
        party_context=dict(raw.get("party_context") or {}),
    )


def discover_manual_review_beds(root: Path) -> ManualReviewBedsResponse:
    payload = _load_manual_review_payload(root)
    beds: list[ManualReviewBedSummary] = []
    for bed in payload.get("beds", []) or []:
        if not isinstance(bed, Mapping):
            continue
        variants = bed.get("variants", {}) if isinstance(bed.get("variants"), Mapping) else {}
        beds.append(
            ManualReviewBedSummary(
                bed_id=str(bed.get("bed_id") or ""),
                campaign_id=bed.get("campaign_id"),
                session_id=bed.get("session_id"),
                source_label=bed.get("source_label"),
                variant_names=list(variants.keys()),
            )
        )
    return ManualReviewBedsResponse(
        generated_at=payload.get("generated_at"),
        model_id=payload.get("model_id"),
        beds=beds,
    )


def load_manual_review_bed(root: Path, bed_id: str) -> ManualReviewBedDetail:
    payload = _load_manual_review_payload(root)
    bed = _find_bed(payload, bed_id)
    variants_raw = bed.get("variants", {}) if isinstance(bed.get("variants"), Mapping) else {}
    variants = {
        variant_name: _build_variant(variant_name, variant_raw)
        for variant_name, variant_raw in variants_raw.items()
        if isinstance(variant_raw, Mapping)
    }
    edge_prompt_context = bed.get("edge_prompt_context")
    edge_prompt_text = (
        str(edge_prompt_context.get("context_text") or "")
        if isinstance(edge_prompt_context, Mapping)
        else ""
    )
    node_prompt_contexts_raw = bed.get("node_prompt_contexts")
    node_prompt_contexts: dict[str, str] = {}
    if isinstance(node_prompt_contexts_raw, Mapping):
        for pass_name in NODE_PASS_NAMES:
            entry = node_prompt_contexts_raw.get(pass_name)
            if isinstance(entry, Mapping):
                node_prompt_contexts[pass_name] = str(entry.get("context_text") or "")
    return ManualReviewBedDetail(
        bed_id=bed_id,
        campaign_id=bed.get("campaign_id"),
        session_id=bed.get("session_id"),
        source_label=bed.get("source_label"),
        generated_at=payload.get("generated_at"),
        model_id=payload.get("model_id"),
        node_prompt_contexts=node_prompt_contexts,
        edge_prompt_context=edge_prompt_text,
        variant_names=list(variants.keys()),
        variants=variants,
    )
