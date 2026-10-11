"""Internal source-proven existing-subject observations; no public request or writer."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringObjectRefPayload
from graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph, map_recap_source_observation
from graph_memory.extract_identity_gate import IdentityGateResult, _qualified_source_local_id
from graph_memory.extract_promote_proposal import compute_proposal_digest, validate_recap_source_observation_basis
from graph_memory.extract_promote_review_projection import project_promote_review_as_dicts
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.contracts.contribution_review_v2 import contribution_v2_payload_sha256
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import CURRENT_V5_TARGET

KEY = "recap_source_observation_basis"
SCHEMA = "dmb_recap_source_observation_basis_v1"


class RecapSourceObservationPrepareError(ValueError):
    code = "source_observation_binding_invalid"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RecapSourceObservationPrepareError(message)


def _source_run(root: Path, run_id: str):
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
    run = get_extraction_run(root, run_id)
    resolved = resolve_promotable_ingest_run(run_id, root=root)
    _require(run.status.value == "reviewable" and resolved.source_domain == "recap",
             "source run is not a reviewable recap")
    from apps.live_control_server.services.extract_promote import (
        _assert_and_project_candidate_evidence, _load_frozen_span_index_for_resolved_run,
    )
    raw = json.loads(resolved.candidate_graph_path.read_bytes())
    _assert_and_project_candidate_evidence(
        candidate_payload=raw, source_prose=resolved.normalized_recap_path.read_text(),
        source_artifact_id=resolved.source_artifact_id,
        span_index=_load_frozen_span_index_for_resolved_run(resolved),
    )
    return run, resolved, raw, load_typed_candidate_graph(raw)


def _history(bundle: Any, world_id: str, parent_id: str, published_id: str):
    cursor, visited = parent_id, set()
    while cursor != published_id:
        _require(cursor is not None and cursor not in visited, "historical publication is not on parent lineage")
        visited.add(cursor)
        stored = bundle.world_graph.get_revision(world_id, cursor)
        _require(stored is not None, "parent lineage is unreadable")
        cursor = stored.revision.parent_revision_id
    publication = bundle.finalized_review_publications.get_for_published_revision(world_id, published_id)
    _require(publication is not None, "historical publication is missing")
    state = bundle.contribution_reviews.get(world_id, publication.review_id)
    _require(state is not None, "historical finalized review is missing")
    contribution = state.reviewed_contribution
    _require(
        state.record.review_intent_sha256 == publication.review_intent_sha256
        and state.record.reviewed_contribution_id == publication.reviewed_contribution_id
        and contribution_v2_payload_sha256(contribution) == publication.reviewed_contribution_sha256,
        "historical review/contribution/publication digest drift",
    )
    published = bundle.world_graph.get_revision(world_id, published_id)
    _require(published is not None
             and published.revision.graph_payload_sha256 == publication.graph_payload_sha256,
             "historical publication payload drift")
    return publication, state


def _subject_proof(*, bundle, world_id, parent_id, historical_id, basis, resolved, preview, refs):
    publication, state = _history(bundle, world_id, parent_id, historical_id)
    candidate_binding = state.candidate_contribution.diagnostics.get("reviewed_extract_confirmation")
    _require(isinstance(candidate_binding, dict), "historical reviewed extract binding is missing")
    parent = bundle.world_graph.get_revision(world_id, parent_id)
    _require(parent is not None, "current parent is missing")
    _require(parent.revision.world_id == world_id
             and canonical_sha256(parent.graph_payload) == parent.revision.graph_payload_sha256,
             "current parent payload integrity drift")
    current = {obj["object_id"]: obj for obj in parent.graph_payload["objects"]}
    nodes = {node.node_id: node for node in preview.nodes}
    accepted = [a for a in state.reviewed_contribution.assertions
                if a.assertion_kind == "node" and str(a.acceptance_state) == "accepted"]
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as reads
    from graph_memory.retrieval.models import WorldGraphObjectRequest, RETRIEVAL_OBJECT_REQUEST_SCHEMA
    services = reads.direct_services_from_bundle(bundle, world_id)
    hashes = {
        "source_body_sha256": hashlib.sha256(resolved.normalized_recap_path.read_bytes()).hexdigest(),
        "candidate_graph_sha256": hashlib.sha256(resolved.candidate_graph_path.read_bytes()).hexdigest(),
        "source_span_index_sha256": hashlib.sha256(resolved.source_span_index_path.read_bytes()).hexdigest(),
    }
    native_source = bundle.sources.get_artifact(resolved.source_artifact_id)
    native_revision = bundle.sources.get_revision(resolved.source_revision_id)
    _require(native_source is not None and native_revision is not None
             and native_source.world_id == world_id
             and native_source.campaign_id == resolved.campaign_id
             and str(native_source.status) == "active"
             and str(native_source.source_domain) == "session_recap"
             and native_source.current_revision_id == resolved.source_revision_id
             and native_revision.source_artifact_id == resolved.source_artifact_id
             and native_revision.content_sha256 == hashes["source_body_sha256"],
             "native source catalog pair changed or is unavailable")
    _require(all(candidate_binding.get(k) == v for k, v in hashes.items()), "historical source/component hash drift")
    _require(candidate_binding["source_artifact_id"] == resolved.source_artifact_id
             and candidate_binding["source_revision_id"] == resolved.source_revision_id,
             "historical source identity drift")
    rows, observations = [], []
    for ref in refs:
        _require(ref.ref_kind == "existing_graph_node" and bool(ref.node_id), "exact existing-object reference required")
        _require(ref.node_id in current, "existing subject is missing on pinned parent")
        matches = [a for a in accepted if a.subject_object_id == ref.node_id]
        _require(len(matches) == 1, "subject lacks one selected accepted historical node")
        assertion = matches[0]
        _require(str(assertion.identity_resolution_outcome) == "created_new"
                 and assertion.campaign_scope == resolved.campaign_id,
                 "historical node is not an accepted source-local creation")
        value = json.loads(assertion.value)
        qualified_kind = value.get("dm_kind")
        _require(isinstance(qualified_kind, str) and bool(qualified_kind),
                 "historical node lacks its qualified kind")
        _require(current[ref.node_id]["kind"] == qualified_kind, "current subject kind changed")
        request = WorldGraphObjectRequest.model_validate({
            "schema":RETRIEVAL_OBJECT_REQUEST_SCHEMA,"worldId":world_id,
            "campaignId":resolved.campaign_id,"admissibility":"gm",
            "revisionPin":parent_id,"nodeId":ref.node_id,
        })
        complete = services.retrieval.get_complete_object(
            reads._map_retrieval_context(request, services.binding), object_id=ref.node_id,
        )
        _require(complete.found and complete.object.object_id == ref.node_id,
                 "source-proven subject is not active in current authority")
        metadata = current[ref.node_id]["assertion_metadata"]
        _require(metadata["canon_state"] == "canonical"
                 and metadata["assertion_id"] == assertion.assertion_id
                 and metadata["campaign_scope"] == resolved.campaign_id,
                 "current subject origin/standing/scope changed")
        _require(ref.kind is None or ref.kind == qualified_kind
                 or CURRENT_V5_TARGET.buddy_to_dm_kind.get(ref.kind) == qualified_kind,
                 "existing reference kind disagrees")
        raw_ids = [raw for raw in nodes if _qualified_source_local_id(basis, raw) == ref.node_id]
        _require(len(raw_ids) == 1, "candidate lacks exact source-qualified subject")
        node = nodes[raw_ids[0]]
        _require(value.get("summary") == (node.description or "").strip(),
                 "historical node description differs from pinned candidate")
        _require(assertion.source_artifact_id == resolved.source_artifact_id
                 and assertion.source_revision_id == resolved.source_revision_id
                 and assertion.assertion_id in candidate_binding["selected_assertion_ids"],
                 "historical selected assertion/source binding differs")
        observation = map_recap_source_observation(
            node, durable_node_id=ref.node_id, source_revision_id=resolved.source_revision_id,
            verified_source_artifact_id=resolved.source_artifact_id,
            campaign_scope=resolved.campaign_id, session_id=resolved.session_id,
            campaign_id=resolved.campaign_id, source_uri=resolved.sealed_source_uri,
            identity_resolution_outcome="resolved_existing",
        )
        _require(observation is not None, "source node has no eligible description")
        _require(not any(
            row.source_artifact_id == resolved.source_artifact_id
            and row.source_revision_id == resolved.source_revision_id
            and row.text == observation.value["summary"]
            for row in complete.reviewed_source_observations
        ), "description observation is already published for this source/subject")
        rows.append({
            "raw_node_id":node.node_id, "subject_id":ref.node_id,
            "subject_kind":qualified_kind, "historical_assertion_id":assertion.assertion_id,
            "current_subject_sha256":canonical_sha256(current[ref.node_id]),
            "description_sha256":hashlib.sha256(node.description.strip().encode()).hexdigest(),
            "observation_assertion_id":observation.assertion_id,
        })
        observations.append(observation)
    _require(len({r["subject_id"] for r in rows}) == len(rows) and rows, "duplicate or empty subject references")
    return {
        "schema":SCHEMA, "world_id":world_id, "parent_revision_id":parent_id,
        "source_run_id":resolved.run_id, "historical_publication_revision_id":historical_id,
        "historical_publication_sha256":canonical_sha256(publication.model_dump(mode="json")),
        "historical_review_id":state.record.review_id,
        "historical_review_intent_sha256":state.record.review_intent_sha256,
        "historical_contribution_sha256":publication.reviewed_contribution_sha256,
        "historical_prepared_package_sha256":candidate_binding["prepared_package_sha256"],
        "historical_identity_basis":basis, "subjects":rows, **hashes,
    }, observations


def prepare_recap_source_observations(
    *, bundle: Any, managed_world_id: str, source_run_id: str,
    historical_publication_revision_id: str, historical_package_bytes: bytes,
    subjects: Sequence[GraphObjectAuthoringObjectRefPayload], repo_root: Path,
) -> dict[str, Any]:
    from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
    from apps.live_control_server.services.extract_promote import _seal_publication_target
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.models.world_graph_contributions import create_graph_contribution
    binding = resolve_managed_world_binding(managed_world_id)
    head = bundle.world_graph.get_head(binding.native_world_id)
    _require(head is not None, "native head is missing")
    parent_id = head.head_revision_id
    root = artifact_data_root(repo_root)
    _run, resolved, raw, preview = _source_run(root, source_run_id)
    _require(resolved.world_id in (None, binding.native_world_id), "source declares a foreign World")
    old = json.loads(historical_package_bytes)
    _require(compute_proposal_digest(old["effect"]) == old["proposal_digest"], "historical package seal drift")
    historical_basis = {key:value for key,value in old["effect"]["identity_basis"].items() if key != "nodes"}
    proof, observations = _subject_proof(
        bundle=bundle, world_id=binding.native_world_id, parent_id=parent_id,
        historical_id=historical_publication_revision_id, basis=historical_basis,
        resolved=resolved, preview=preview, refs=subjects,
    )
    _require(hashlib.sha256(historical_package_bytes).hexdigest() == proof["historical_prepared_package_sha256"],
             "historical package bytes differ from finalized review")
    meta = old["effect"]["contribution_meta"]
    identity_basis = {**historical_basis, "parent_revision_id":parent_id, "nodes":{
        row["raw_node_id"]:{"classification":"source_proven_existing",
            "proposed_node_id":row["subject_id"],"outcome":"resolved_existing"}
        for row in proof["subjects"]}}
    gate = IdentityGateResult(
        parent_revision_id=parent_id, world_id=binding.native_world_id,
        contribution=create_graph_contribution(
            world_id=binding.native_world_id,source_kind="source_extraction",
            source_artifact_id=resolved.source_artifact_id,source_revision_id=resolved.source_revision_id,
            extraction_profile=meta["extraction_profile"],campaign_scope=resolved.campaign_id,
            authored_by="service:buddy:recap-observation-prepare"),
        accepted_proposals=observations,
        node_id_map={r["raw_node_id"]:r["subject_id"] for r in proof["subjects"]},
        identity_outcome_snapshot={r["raw_node_id"]:"resolved_existing" for r in proof["subjects"]},
        identity_basis=identity_basis, candidate_preview_id=preview.preview_id,
        candidate_schema=preview.schema,candidate_version=preview.version,
        source_revision_id=resolved.source_revision_id,source_artifact_id=resolved.source_artifact_id,
        verified_source_uri=resolved.sealed_source_uri,
    )
    package = gate.to_review_package(prepared_by="service:buddy:recap-observation-prepare",
                                    candidate_graph_path=str(resolved.candidate_graph_path))
    effect=package["effect"]
    effect[KEY]=proof
    effect["source_admission"]=copy.deepcopy(old["effect"]["source_admission"])
    effect["candidate_admission"]={**copy.deepcopy(old["effect"]["candidate_admission"]),
        "parent_revision_id":parent_id,"confirmable":True}
    package["proposal_digest"]=compute_proposal_digest(effect)
    context=writes.load_production_mutation_context(binding.native_world_id)
    _require(context.head_revision_id == parent_id, "parent changed while preparing")
    package=writes.bind_identity_ledger_to_package(package,context)
    package=_seal_publication_target(package,binding)
    validate_recap_source_observation_basis(package["effect"])
    reprove_recap_source_observation_binding(bundle=bundle,package=package,repo_root=root)
    items,summary=project_promote_review_as_dicts(gate,contribution_slice_id="0:source_extraction")
    return {"review_package":package,"review_items":items,"review_summary":summary}


def reprove_recap_source_observation_binding(*, bundle, package, repo_root):
    proof=package.get("effect",{}).get(KEY)
    if proof is None:
        return
    validate_recap_source_observation_basis(package["effect"])
    _,resolved,_raw,preview=_source_run(artifact_data_root(repo_root),proof["source_run_id"])
    refs=[GraphObjectAuthoringObjectRefPayload(
        refKind="existing_graph_node",nodeId=row["subject_id"],label="exact source-proven subject",
        kind=row["subject_kind"]) for row in proof["subjects"]]
    actual,observations=_subject_proof(
        bundle=bundle,world_id=proof["world_id"],parent_id=proof["parent_revision_id"],
        historical_id=proof["historical_publication_revision_id"],
        basis=proof["historical_identity_basis"],resolved=resolved,preview=preview,refs=refs)
    _require(actual == proof, "source-proven existing-subject proof drift")
    expected={a.assertion_id:a.model_dump(mode="json") for a in observations}
    supplied={a["assertion_id"]:a for a in package["effect"]["accepted_proposals"]}
    _require(expected == supplied, "observation/source/subject/text descriptor drift")
