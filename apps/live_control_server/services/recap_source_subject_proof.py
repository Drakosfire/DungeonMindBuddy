"""Shared historical identity/source proof; no description emission or publication."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.contracts.contribution_review_v2 import contribution_v2_payload_sha256
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET,
)
from graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph
from graph_memory.extract_identity_gate import _qualified_source_local_id


class SourceSubjectProofError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceSubjectProofError(message)


def _source_run(root: Path, run_id: str):
    from apps.live_control_server.services.graph_run_registry import (
        load_reviewable_extraction_data, GraphRunRegistryError,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from apps.live_control_server.services.extract_promote import (
        _assert_and_project_candidate_evidence,
    )

    try:
        data = load_reviewable_extraction_data(root, run_id)
    except GraphRunRegistryError as exc:
        raise SourceSubjectProofError(str(exc)) from exc
    resolved = resolve_promotable_ingest_run(run_id, root=root)
    run = data.run
    _require(
        run.source_domain == resolved.source_domain == "recap"
        and run.source_artifact_id == resolved.source_artifact_id
        and data.source_artifact.world_id == resolved.world_id
        and (run.campaign_id or "") == resolved.campaign_id
        and (run.session_id or "") == resolved.session_id
        and f"sha256:{hashlib.sha256(data.source_bytes).hexdigest()}" == resolved.source_revision_id,
        "resolved source differs from the exact reviewable recap",
    )
    raw = json.loads(data.candidate_bytes)
    _assert_and_project_candidate_evidence(
        candidate_payload=raw,
        source_prose=data.source_bytes.decode("utf-8"),
        source_artifact_id=resolved.source_artifact_id,
        span_index=data.span_index,
    )
    return data, resolved, raw, load_typed_candidate_graph(raw)


def _history(bundle: Any, world_id: str, parent_id: str, published_id: str):
    cursor, visited = parent_id, set()
    while cursor != published_id:
        _require(
            cursor is not None and cursor not in visited,
            "historical publication is not on parent lineage",
        )
        visited.add(cursor)
        stored = bundle.world_graph.get_revision(world_id, cursor)
        _require(stored is not None, "parent lineage is unreadable")
        cursor = stored.revision.parent_revision_id
    publication = bundle.finalized_review_publications.get_for_published_revision(
        world_id, published_id
    )
    _require(publication is not None, "historical publication is missing")
    state = bundle.contribution_reviews.get(world_id, publication.review_id)
    _require(state is not None, "historical finalized review is missing")
    contribution = state.reviewed_contribution
    _require(
        state.record.review_intent_sha256 == publication.review_intent_sha256
        and state.record.reviewed_contribution_id
        == publication.reviewed_contribution_id
        and contribution_v2_payload_sha256(contribution)
        == publication.reviewed_contribution_sha256,
        "historical review/contribution/publication digest drift",
    )
    published = bundle.world_graph.get_revision(world_id, published_id)
    _require(
        published is not None
        and published.revision.graph_payload_sha256 == publication.graph_payload_sha256,
        "historical publication payload drift",
    )
    return publication, state


@dataclass(frozen=True)
class ProvenSourceSubject:
    row: dict
    common: dict
    node: Any
    complete: Any


def prove_source_subject(
    *, bundle, world_id, parent_id, historical_id, basis, resolved, preview, ref, source_data
):
    publication, state = _history(bundle, world_id, parent_id, historical_id)
    candidate_binding = state.candidate_contribution.diagnostics.get(
        "reviewed_extract_confirmation"
    )
    _require(
        isinstance(candidate_binding, dict),
        "historical reviewed extract binding is missing",
    )
    parent = bundle.world_graph.get_revision(world_id, parent_id)
    _require(parent is not None, "current parent is missing")
    _require(
        parent.revision.world_id == world_id
        and canonical_sha256(parent.graph_payload)
        == parent.revision.graph_payload_sha256,
        "current parent payload integrity drift",
    )
    current = {obj["object_id"]: obj for obj in parent.graph_payload["objects"]}
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    identity_context = world_graph_writes.mutation_context_from_revision_payload(
        parent,
        world_id=world_id,
        head_revision_id=parent_id,
        dungeonmind_decisions=bundle.identity_decisions.list_for_world(world_id),
    )
    nodes = {node.node_id: node for node in preview.nodes}
    accepted = [
        a
        for a in state.reviewed_contribution.assertions
        if a.assertion_kind == "node" and str(a.acceptance_state) == "accepted"
    ]
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )
    from graph_memory.retrieval.models import (
        WorldGraphObjectRequest,
        RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    )

    services = reads.direct_services_from_bundle(bundle, world_id)
    hashes = {
        "source_body_sha256": hashlib.sha256(source_data.source_bytes).hexdigest(),
        "candidate_graph_sha256": hashlib.sha256(source_data.candidate_bytes).hexdigest(),
        "source_span_index_sha256": hashlib.sha256(source_data.span_bytes).hexdigest(),
    }
    native_source = bundle.sources.get_artifact(resolved.source_artifact_id)
    native_revision = bundle.sources.get_revision(resolved.source_revision_id)
    _require(
        native_source is not None
        and native_revision is not None
        and native_source.world_id == world_id
        and native_source.campaign_id == resolved.campaign_id
        and str(native_source.status) == "active"
        and str(native_source.source_domain) == "session_recap"
        and native_source.current_revision_id == resolved.source_revision_id
        and native_revision.source_artifact_id == resolved.source_artifact_id
        and native_revision.content_sha256 == hashes["source_body_sha256"],
        "native source catalog pair changed or is unavailable",
    )
    _require(
        all(candidate_binding.get(k) == v for k, v in hashes.items()),
        "historical source/component hash drift",
    )
    from apps.live_control_server.services.candidate_graph_admission import (
        canonical_candidate_digest,
    )

    actual_digest = canonical_candidate_digest(
        json.loads(source_data.candidate_bytes)
    )
    _require(
        candidate_binding.get("candidate_admission_digest") == actual_digest
        and basis.get("candidate_sha256") == actual_digest,
        "historical FULL candidate digest drift",
    )
    _require(
        candidate_binding["source_artifact_id"] == resolved.source_artifact_id
        and candidate_binding["source_revision_id"] == resolved.source_revision_id,
        "historical source identity drift",
    )

    _require(
        ref.ref_kind == "existing_graph_node" and bool(ref.node_id),
        "exact existing-object reference required",
    )
    _require(ref.node_id in current, "existing subject is missing on pinned parent")
    _require(
        ref.node_id not in identity_context.identity_redirects,
        "source-proven subject has been redirected or merged",
    )
    matches = [a for a in accepted if a.subject_object_id == ref.node_id]
    _require(len(matches) == 1, "subject lacks one selected accepted historical node")
    assertion = matches[0]
    _require(
        str(assertion.identity_resolution_outcome) == "created_new"
        and assertion.campaign_scope == resolved.campaign_id,
        "historical node is not an accepted source-local creation",
    )
    value = json.loads(assertion.value)
    qualified_kind = value.get("dm_kind")
    _require(
        isinstance(qualified_kind, str) and bool(qualified_kind),
        "historical node lacks its qualified kind",
    )
    _require(
        current[ref.node_id]["kind"] == qualified_kind, "current subject kind changed"
    )
    request = WorldGraphObjectRequest.model_validate(
        {
            "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
            "worldId": world_id,
            "campaignId": resolved.campaign_id,
            "admissibility": "gm",
            "revisionPin": parent_id,
            "nodeId": ref.node_id,
        }
    )
    complete = services.retrieval.get_complete_object(
        reads._map_retrieval_context(request, services.binding),
        object_id=ref.node_id,
    )
    _require(
        complete.found and complete.object.object_id == ref.node_id,
        "source-proven subject is not active in current authority",
    )
    metadata = current[ref.node_id]["assertion_metadata"]
    _require(
        metadata["canon_state"] == "canonical"
        and metadata["assertion_id"] == assertion.assertion_id
        and metadata["campaign_scope"] == resolved.campaign_id,
        "current subject origin/standing/scope changed",
    )
    _require(
        ref.kind is None
        or ref.kind == qualified_kind
        or CURRENT_V5_TARGET.buddy_to_dm_kind.get(ref.kind) == qualified_kind,
        "existing reference kind disagrees",
    )
    raw_ids = [
        raw for raw in nodes if _qualified_source_local_id(basis, raw) == ref.node_id
    ]
    _require(len(raw_ids) == 1, "candidate lacks exact source-qualified subject")
    node = nodes[raw_ids[0]]

    _require(
        assertion.source_artifact_id == resolved.source_artifact_id
        and assertion.source_revision_id == resolved.source_revision_id
        and assertion.assertion_id in candidate_binding["selected_assertion_ids"],
        "historical selected assertion/source binding differs",
    )

    row = {
        "raw_node_id": node.node_id,
        "subject_id": ref.node_id,
        "subject_kind": qualified_kind,
        "historical_assertion_id": assertion.assertion_id,
        "current_subject_sha256": canonical_sha256(current[ref.node_id]),
    }
    common = {
        "world_id": world_id,
        "parent_revision_id": parent_id,
        "source_run_id": resolved.run_id,
        "historical_publication_revision_id": historical_id,
        "historical_publication_sha256": canonical_sha256(
            publication.model_dump(mode="json")
        ),
        "historical_review_id": state.record.review_id,
        "historical_review_intent_sha256": state.record.review_intent_sha256,
        "historical_contribution_sha256": publication.reviewed_contribution_sha256,
        "historical_prepared_package_sha256": candidate_binding[
            "prepared_package_sha256"
        ],
        "historical_identity_basis": basis,
        **hashes,
    }
    return ProvenSourceSubject(row, common, node, complete)
