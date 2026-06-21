"""Deterministic session-memory JSONL sentence-unit materializer v0.

This module only reads an explicit JSONL path supplied by callers. It never
scans corpus data, imports production retrieval/session-memory modules, calls
LLMs, or infers entities, aliases, relationships, or campaign facts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.graph_memory.ontology_ir import GraphBundle, GraphEdge, GraphNode, ProvenanceRef, SourceRef, TaxonomyRef, ValidationStatus
from src.graph_memory.report import GraphReport, RecordSummary, build_graph_report, summarize_records
from src.graph_memory.validation_rules import ValidationIssue, load_taxonomy_registry, validate_bundle_against_taxonomy

SCHEMA_VERSION = "0.1"
TAXONOMY_REGISTRY_VERSION = "0.1"
CREATED_BY = "session_memory_sentence_unit_materializer_v0"
SESSION_MEMORY_RECORD_SCHEMA = "dmb_session_memory_record_v1"
ADMITTED_SOURCE_FAMILY = "session_memory_jsonl_sentence_units"


@dataclass(frozen=True)
class SessionMemoryRouteSummary:
    subject_class: str
    normalized_route: str
    proposed: bool
    tag_kind: str | None


@dataclass(frozen=True)
class SessionMemoryRecord:
    schema: str
    campaign_id: str
    session_number: int
    source_recap_path: str
    unit_id: str
    line_start: int
    line_end: int
    text_blake3: str | None
    lexical_plain: str
    routes: list[SessionMemoryRouteSummary]


@dataclass(frozen=True)
class SessionMemoryCoverage:
    input_record_count: int
    source_document_count: int
    source_unit_count: int
    records_with_routes: int
    total_route_mentions: int
    proposed_route_mentions: int
    explicit_route_mentions: int


def _ref(vocabulary: str, term: str) -> TaxonomyRef:
    return TaxonomyRef(vocabulary=vocabulary, term=term)


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_str(data: dict[str, Any], key: str, line_number: int) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line {line_number}: {key} must be a nonblank string")
    return value


def _require_int(data: dict[str, Any], key: str, line_number: int) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"line {line_number}: {key} must be an integer")
    return value


def _parse_route(raw: Any, line_number: int) -> SessionMemoryRouteSummary:
    route = _require_mapping(raw, f"line {line_number}: route")
    tag_kind = route.get("tag_kind")
    if tag_kind is not None and not isinstance(tag_kind, str):
        raise ValueError(f"line {line_number}: route.tag_kind must be a string or null")
    return SessionMemoryRouteSummary(
        subject_class=_require_str(route, "subject_class", line_number),
        normalized_route=_require_str(route, "normalized_route", line_number),
        proposed=bool(route.get("proposed", False)),
        tag_kind=tag_kind,
    )


def _parse_record(data: dict[str, Any], line_number: int) -> SessionMemoryRecord:
    schema = _require_str(data, "schema", line_number)
    if schema != SESSION_MEMORY_RECORD_SCHEMA:
        raise ValueError(f"line {line_number}: unsupported schema {schema!r}; expected {SESSION_MEMORY_RECORD_SCHEMA!r}")
    line_start = _require_int(data, "line_start", line_number)
    line_end = _require_int(data, "line_end", line_number)
    if line_start <= 0 or line_end < line_start:
        raise ValueError(f"line {line_number}: line_start/line_end must be positive and ordered")
    text_blake3 = data.get("text_blake3")
    if text_blake3 is not None and not isinstance(text_blake3, str):
        raise ValueError(f"line {line_number}: text_blake3 must be a string or null")
    routes_raw = data.get("routes", [])
    if routes_raw is None:
        routes_raw = []
    if not isinstance(routes_raw, list):
        raise ValueError(f"line {line_number}: routes must be a list when present")
    return SessionMemoryRecord(
        schema=schema,
        campaign_id=_require_str(data, "campaign_id", line_number),
        session_number=_require_int(data, "session_number", line_number),
        source_recap_path=_require_str(data, "source_recap_path", line_number),
        unit_id=_require_str(data, "unit_id", line_number),
        line_start=line_start,
        line_end=line_end,
        text_blake3=text_blake3,
        lexical_plain=_require_str(data, "lexical_plain", line_number),
        routes=[_parse_route(route, line_number) for route in routes_raw],
    )


def load_session_memory_jsonl(path: Path, *, limit: int | None = None) -> list[SessionMemoryRecord]:
    """Load session-memory sentence/source-unit JSONL records from one explicit path."""
    records: list[SessionMemoryRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_number}: malformed JSONL record: {exc.msg}") from exc
            records.append(_parse_record(_require_mapping(raw, f"line {line_number}"), line_number))
            if limit is not None and len(records) >= limit:
                break
    return records


def _safe_id_part(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "source"


def _source_ref(record: SessionMemoryRecord, *, document_level: bool = False) -> SourceRef:
    return SourceRef(
        source_id=record.source_recap_path,
        source_kind=_ref("source_kind", "session_memory_record"),
        source_layer=_ref("source_layer", "memory_layer"),
        source_path=record.source_recap_path,
        source_reference=f"{record.campaign_id}/session-{record.session_number}/{record.unit_id}",
        line_start=None if document_level else record.line_start,
        line_end=None if document_level else record.line_end,
        anchor=None if document_level else record.unit_id,
    )


def _provenance(record: SessionMemoryRecord, record_id: str, *, document_level: bool = False) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=f"{record_id}:provenance",
        source_refs=[_source_ref(record, document_level=document_level)],
        authority_state=_ref("authority_state", "system_derived"),
        evidence_role=_ref("evidence_role", "diagnostic_only"),
        visibility_state=_ref("visibility_state", "internal_diagnostic"),
        notes="Materialized deterministically from session-memory JSONL sentence-unit records.",
    )


def _document_node_id(source_recap_path: str) -> str:
    return f"session-memory:source-document:{_safe_id_part(source_recap_path)}"


def _unit_node_id(record: SessionMemoryRecord) -> str:
    return f"session-memory:source-unit:{_safe_id_part(record.campaign_id)}:s{record.session_number}:{_safe_id_part(record.unit_id)}"


def session_memory_coverage(records: Iterable[SessionMemoryRecord]) -> SessionMemoryCoverage:
    materialized = list(records)
    total_routes = sum(len(record.routes) for record in materialized)
    proposed = sum(1 for record in materialized for route in record.routes if route.proposed)
    return SessionMemoryCoverage(
        input_record_count=len(materialized),
        source_document_count=len({record.source_recap_path for record in materialized}),
        source_unit_count=len(materialized),
        records_with_routes=sum(1 for record in materialized if record.routes),
        total_route_mentions=total_routes,
        proposed_route_mentions=proposed,
        explicit_route_mentions=total_routes - proposed,
    )


def materialize_session_memory_records(records: list[SessionMemoryRecord]) -> GraphBundle:
    """Materialize candidate/internal/diagnostic source-document and source-unit records."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    documents: dict[str, list[SessionMemoryRecord]] = {}
    for record in records:
        documents.setdefault(record.source_recap_path, []).append(record)

    for source_path in sorted(documents):
        doc_records = documents[source_path]
        first = doc_records[0]
        document_id = _document_node_id(source_path)
        route_count = sum(len(record.routes) for record in doc_records)
        nodes.append(
            GraphNode(
                node_id=document_id,
                kind=_ref("entity_kind", "source_document"),
                label=source_path,
                aliases=[],
                properties={
                    "campaign_id": first.campaign_id,
                    "session_number": first.session_number,
                    "source_recap_path": source_path,
                    "record_count": len(doc_records),
                    "route_count": route_count,
                },
                provenance=[_provenance(first, document_id, document_level=True)],
                lifecycle_state=_ref("lifecycle_state", "candidate"),
                visibility_state=_ref("visibility_state", "internal_diagnostic"),
            )
        )
        for record in sorted(doc_records, key=lambda item: (item.line_start, item.unit_id)):
            unit_id = _unit_node_id(record)
            nodes.append(
                GraphNode(
                    node_id=unit_id,
                    kind=_ref("entity_kind", "source_unit"),
                    label=record.unit_id,
                    aliases=[],
                    properties={
                        "campaign_id": record.campaign_id,
                        "session_number": record.session_number,
                        "unit_id": record.unit_id,
                        "line_start": record.line_start,
                        "line_end": record.line_end,
                        "text_blake3": record.text_blake3,
                        "text_length": len(record.lexical_plain),
                        "route_count": len(record.routes),
                        "has_routes": bool(record.routes),
                    },
                    provenance=[_provenance(record, unit_id)],
                    lifecycle_state=_ref("lifecycle_state", "candidate"),
                    visibility_state=_ref("visibility_state", "internal_diagnostic"),
                )
            )
            edge_id = f"session-memory:source-derivation:{_safe_id_part(record.unit_id)}"
            edges.append(
                GraphEdge(
                    edge_id=edge_id,
                    subject_id=document_id,
                    object_id=unit_id,
                    predicate_family=_ref("relationship_predicate_family", "source_derivation"),
                    label="source derivation",
                    properties={},
                    provenance=[_provenance(record, edge_id)],
                    lifecycle_state=_ref("lifecycle_state", "candidate"),
                    visibility_state=_ref("visibility_state", "internal_diagnostic"),
                )
            )

    return GraphBundle(
        bundle_id="session-memory:sentence-units:graph-bundle",
        schema_version=SCHEMA_VERSION,
        taxonomy_registry_version=TAXONOMY_REGISTRY_VERSION,
        created_by=CREATED_BY,
        description="Candidate diagnostic graph bundle from explicit session-memory JSONL sentence-unit records.",
        nodes=nodes,
        edges=edges,
        validation=[
            ValidationStatus(
                state=_ref("lifecycle_state", "candidate"),
                severity=_ref("validation_severity", "info"),
                message="Materialized deterministically from session-memory JSONL sentence-unit records.",
            )
        ],
    )


def materialize_session_memory_jsonl(path: Path, *, limit: int | None = None) -> GraphBundle:
    return materialize_session_memory_records(load_session_memory_jsonl(path, limit=limit))


def validate_session_memory_gate(gate_manifest_path: Path) -> dict[str, Any]:
    with gate_manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("gate manifest must be a JSON object")
    decision = _require_mapping(manifest.get("gate_decision"), "gate_decision")
    if decision.get("admitted_source_family") != ADMITTED_SOURCE_FAMILY:
        raise ValueError("real-structure gate does not admit session_memory_jsonl_sentence_units")
    constraints = _require_mapping(manifest.get("global_constraints"), "global_constraints")
    for key in ["no_production_retrieval_changes", "no_corpus_mutation", "no_llm_calls", "no_entity_extraction", "no_alias_resolution", "no_relationship_inference", "no_promoted_records", "diagnostic_only_default", "must_run_validation_rules", "must_emit_report"]:
        if constraints.get(key) is not True:
            raise ValueError(f"gate global constraint is not enabled: {key}")
    candidates = manifest.get("candidate_source_families")
    if not isinstance(candidates, list):
        raise ValueError("candidate_source_families must be a list")
    admitted = [candidate for candidate in candidates if isinstance(candidate, dict) and candidate.get("id") == ADMITTED_SOURCE_FAMILY]
    if len(admitted) != 1 or admitted[0].get("admitted_for_next_materializer") is not True:
        raise ValueError("session-memory source family is not admitted for next materializer")
    defaults = _require_mapping(admitted[0].get("required_record_defaults"), "required_record_defaults")
    if defaults.get("lifecycle_state") != "candidate" or defaults.get("visibility_state") != "internal_diagnostic" or defaults.get("evidence_role_default") != "diagnostic_only":
        raise ValueError("admitted source family defaults do not match candidate/internal/diagnostic")
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("status") in {"blocked", "deferred"} and candidate.get("admitted_for_next_materializer") is not False:
            raise ValueError(f"blocked/deferred family is admitted: {candidate.get('id')}")
    return manifest


def materialize_validate_and_report_session_memory(jsonl_path: Path, taxonomy_registry_path: Path, *, gate_manifest_path: Path, limit: int | None = None) -> tuple[GraphBundle, GraphReport, list[RecordSummary], list[ValidationIssue]]:
    validate_session_memory_gate(gate_manifest_path)
    taxonomy_registry = load_taxonomy_registry(taxonomy_registry_path)
    records = load_session_memory_jsonl(jsonl_path, limit=limit)
    bundle = materialize_session_memory_records(records)
    result = validate_bundle_against_taxonomy(bundle, taxonomy_registry)
    report = build_graph_report(bundle, result.issues)
    summaries = summarize_records(bundle)
    return bundle, report, summaries, result.issues
