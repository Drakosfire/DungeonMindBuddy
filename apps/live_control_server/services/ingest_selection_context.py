"""Resolve a read-only source/candidate context from exact retained authority.

Candidate records are proposals, not accepted World identities. The context
hash is a precondition for later revalidation, never a bearer capability.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from application_state.errors import ApplicationStateError
from application_state.ingest.components import get_component_bytes
from application_state.source import service as source_service
from apps.live_control_server.config import artifact_data_root, repo_root
from apps.live_control_server.integrations.dungeonmind.vnext_review_context import (
    NativeReviewConflict,
    resolve_native_review_context,
)
from apps.live_control_server.models.ingest_selection_context import (
    IngestSelectionContextRequest,
)
from apps.live_control_server.services.extract_promote import ExtractPromoteError
from apps.live_control_server.services.graph_run_registry import (
    get_extraction_run,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRunStatus,
    normalize_content_digest,
)
from graph_memory.source_span import (
    source_span_index_from_dict,
    validate_source_span_index,
)

NEIGHBORHOOD_EDGE_LIMIT = 64


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _record_hash(value: object) -> str:
    return _hash(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    )


def _reject(message: str, *, conflict: bool = False):
    raise ExtractPromoteError(
        message,
        code="ingest_selection_conflict" if conflict else "ingest_selection_invalid",
        status_code=409 if conflict else 422,
    )


def _records(rows: object, key: str) -> dict[str, dict]:
    if not isinstance(rows, list):
        _reject("candidate record collection is malformed")
    records = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get(key), str)
            or not row[key]
            or row[key] in records
        ):
            _reject("candidate record identities are missing or ambiguous")
        records[row[key]] = row
    return records


def _load_component(run, kind: str, expected: str) -> tuple[bytes, str]:
    component = run.components.get(kind)
    if component is None or normalize_content_digest(component.sha256) != expected:
        _reject("selected component precondition changed", conflict=True)
    try:
        data = get_component_bytes(run_id=run.run_id, kind=component.kind, content_sha256=expected)
    except ApplicationStateError as exc:
        raise ExtractPromoteError(
            f"selected stored output is unavailable: {exc}",
            code="ingest_selection_conflict" if exc.status_code < 500 else "ingest_selection_unavailable",
            status_code=409 if exc.status_code < 500 else exc.status_code,
        ) from exc
    return data, expected


def _scope(run, source, expected_world: str | None) -> dict:
    # This caller reconciles one frozen recap. World ownership of its source
    # does not grant a World-wide assertion query or a campaign fallback.
    if run.source_domain != "recap" or any(
        not isinstance(value, str) or not value.strip()
        for value in (run.campaign_id, run.session_id)
    ):
        _reject("native review requires a recap with exact campaign and session")
    observation = run.lineage.get("world_campaign_ingest_context")
    observation = observation if isinstance(observation, dict) else {}
    world = expected_world
    if not isinstance(world, str) or not world.strip():
        _reject("native review requires an active managed World binding")
    if observation.get("managed_world_id") not in (None, world):
        _reject("selection belongs to another World", conflict=True)
    if observation and observation.get("campaign_id") != run.campaign_id:
        _reject("run World observation belongs to another campaign")
    if observation.get("session_id") not in (None, run.session_id):
        _reject("run World observation belongs to another session")
    binding = resolve_managed_world_binding(world)
    # APP source ownership is native; the selected product World is managed.
    # Join them through the existing binding instead of comparing namespaces.
    if observation and (
        observation.get("native_world_id") != binding.native_world_id
        or observation.get("binding_version") != binding.binding_version
    ):
        _reject("World binding changed since extraction", conflict=True)
    if source.world_id != binding.native_world_id:
        _reject("source does not belong to the selected native World")
    result = {
        "managed_world_id": world,
        "native_world_id": binding.native_world_id,
        "binding_version": binding.binding_version,
        "campaign_id": run.campaign_id,
        "session_id": run.session_id,
        "status": "bound",
        "admitted_world_facts_included": False,
    }
    return result


def resolve_ingest_selection_context(
    run_id: str,
    request: IngestSelectionContextRequest,
    *,
    operator_subject: str,
) -> dict:
    root = artifact_data_root(repo_root())
    run = get_extraction_run(root, run_id)
    if run.revision != request.expected_run_revision:
        _reject("selected run revision changed", conflict=True)
    if run.status != ExtractionRunStatus.REVIEWABLE:
        _reject("selection requires a frozen reviewable run")
    component = run.components.get("source_artifact")
    if (
        component is None
        or normalize_content_digest(component.sha256) != request.expected_source_sha256
    ):
        _reject("selected source precondition changed", conflict=True)
    source = source_service.get_source_markdown(
        source_artifact_id=run.source_artifact_id,
        content_sha256=request.expected_source_sha256,
    )
    if source is None:
        _reject("exact saved source is unavailable")
    if (
        source.source_artifact_id != run.source_artifact_id
        or source.source_domain != run.source_domain
        or source.campaign_id != run.campaign_id
        or source.session_id != run.session_id
        or source.content_sha256.removeprefix("sha256:")
        != request.expected_source_sha256
        or source.encoding != "utf-8"
        or _hash(source.markdown.encode("utf-8")) != request.expected_source_sha256
    ):
        _reject("saved source identity or content does not match run")
    scope = _scope(run, source, request.expected_world_id)
    candidate_bytes, candidate_sha = _load_component(
        run, "candidate_graph", request.expected_candidate_sha256
    )
    span_bytes, span_sha = _load_component(
        run, "source_span_index", request.expected_span_index_sha256
    )
    try:
        candidate = json.loads(candidate_bytes)
        index = source_span_index_from_dict(json.loads(span_bytes))
        validate_source_span_index(
            index,
            source_artifact_id=run.source_artifact_id,
            content_sha256=request.expected_source_sha256,
        )
    except (ValueError, TypeError, KeyError):
        _reject("selected candidate or source index is malformed")
    if not isinstance(candidate, dict):
        _reject("selected candidate root must be an object")
    if (
        candidate.get("campaign_id") != run.campaign_id
        or candidate.get("session_id") != run.session_id
        or run.source_artifact_id not in candidate.get("source_artifact_ids", [])
    ):
        _reject("candidate scope does not match selected run")
    nodes = _records(candidate.get("nodes"), "node_id")
    edges = _records(candidate.get("edges"), "edge_id")
    if set(request.node_ids) - nodes.keys() or set(request.edge_ids) - edges.keys():
        _reject("selected record is missing from frozen candidate")
    selected_nodes = set(request.node_ids)
    for edge_id in request.edge_ids:
        edge = edges[edge_id]
        endpoints = [edge.get("from_node_id"), edge.get("to_node_id")]
        if any(endpoint not in nodes for endpoint in endpoints):
            _reject("selected relationship has an invalid endpoint")
        selected_nodes.update(endpoints)
    incident = sorted(
        edge_id
        for edge_id, edge in edges.items()
        if edge_id not in request.edge_ids
        and (
            edge.get("from_node_id") in selected_nodes
            or edge.get("to_node_id") in selected_nodes
        )
    )
    kept_incident = incident[:NEIGHBORHOOD_EDGE_LIMIT]
    returned_edges = sorted(set(request.edge_ids) | set(kept_incident))
    context_node_ids = set(selected_nodes)
    for edge_id in returned_edges:
        edge = edges[edge_id]
        if edge.get("from_node_id") not in nodes or edge.get("to_node_id") not in nodes:
            _reject("selected neighborhood has an invalid endpoint")
        context_node_ids.update((edge["from_node_id"], edge["to_node_id"]))
    passage = None
    if request.source_selection is not None:
        selection = request.source_selection
        spans = [
            span
            for span in index.spans
            if span.source_span_id == selection.source_span_ref_id
        ]
        if len(spans) != 1:
            _reject("selected span is missing or ambiguous in frozen source")
        span = spans[0]
        lines = source.markdown.splitlines(keepends=True)
        if not (1 <= span.start_line <= span.end_line <= len(lines)):
            _reject("selected paragraph line bounds are invalid")
        start = sum(len(line) for line in lines[: span.start_line - 1])
        end = start + len(
            "".join(lines[span.start_line - 1 : span.end_line]).rstrip("\r\n")
        )
        if not (start <= selection.start < selection.end <= end):
            _reject("selection lies outside its frozen paragraph")
        if source.markdown[selection.start : selection.end] != selection.text:
            _reject("selection text or Unicode offsets are stale", conflict=True)
        passage = {
            "source_span_ref_id": span.source_span_id,
            "start": selection.start,
            "end": selection.end,
            "text": selection.text,
            "paragraph": source.markdown[start:end],
            "paragraph_start": start,
            "paragraph_end": end,
            "offset_unit": "unicode_code_points",
            "range_convention": "source_relative_half_open",
            "provenance": "saved_source",
        }
    try:
        native_context = resolve_native_review_context(
            scope=scope,
            nodes=[nodes[key] for key in sorted(selected_nodes)],
        )
    except NativeReviewConflict as exc:
        _reject(str(exc), conflict=True)
    scope["admitted_world_facts_included"] = any(
        alternative["entity_result"]["assertions"]
        for selection in native_context["selections"]
        for alternative in selection["alternatives"]
    )
    response = {
        "schema": "dmb_ingest_native_review_context_v2",
        "run_id": run.run_id,
        "run_revision": run.revision,
        "source_domain": run.source_domain,
        "profile_id": run.profile_id,
        "candidate_sha256": candidate_sha,
        "source_artifact_id": run.source_artifact_id,
        "source_sha256": request.expected_source_sha256,
        "span_index_sha256": span_sha,
        "scope": scope,
        "native_context": native_context,
        "source_selection": passage,
        "selected_node_ids": sorted(request.node_ids),
        "selected_edge_ids": sorted(request.edge_ids),
        "nodes": [
            {
                "record": deepcopy(nodes[key]),
                "sha256": _record_hash(nodes[key]),
                "identity_authority": "candidate_only",
            }
            for key in sorted(context_node_ids)
        ],
        "edges": [
            {
                "record": deepcopy(edges[key]),
                "sha256": _record_hash(edges[key]),
                "identity_authority": "candidate_only",
            }
            for key in returned_edges
        ],
        "neighborhood": {
            "incident_edge_count": len(incident),
            "returned_incident_edge_count": len(kept_incident),
            "limit": NEIGHBORHOOD_EDGE_LIMIT,
            "truncated": len(incident) > len(kept_incident),
        },
        "annotation": (
            {
                "text": request.annotation,
                "provenance": "operator_annotation",
                "operator_subject": operator_subject,
            }
            if request.annotation is not None
            else None
        ),
        "permissions": {
            "graph_write": False,
            "candidate_write": False,
            "provider_call": False,
        },
    }
    # A concurrent lifecycle change must not be hidden by an otherwise valid stored snapshot.
    if get_extraction_run(root, run_id).revision != run.revision:
        _reject("selected run changed while resolving context", conflict=True)
    final_scope = _scope(run, source, request.expected_world_id)
    final_scope["admitted_world_facts_included"] = scope["admitted_world_facts_included"]
    if final_scope != scope:
        _reject("World binding changed while resolving context", conflict=True)
    response["context_sha256"] = _record_hash(response)
    return response
