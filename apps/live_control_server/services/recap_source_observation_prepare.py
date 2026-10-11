"""Internal source-proven existing-subject observations; no public request or writer."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringObjectRefPayload
from graph_memory.candidate_graph_to_contribution import map_recap_source_observation
from graph_memory.extract_identity_gate import IdentityGateResult
from graph_memory.extract_promote_proposal import compute_proposal_digest, validate_recap_source_observation_basis
from graph_memory.extract_promote_review_projection import project_promote_review_as_dicts

KEY = "recap_source_observation_basis"
SCHEMA = "dmb_recap_source_observation_basis_v1"


class RecapSourceObservationPrepareError(ValueError):
    code = "source_observation_binding_invalid"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RecapSourceObservationPrepareError(message)


def _source_run(root: Path, run_id: str):
    from apps.live_control_server.services.recap_source_subject_proof import _source_run as load, SourceSubjectProofError
    try:
        return load(root,run_id)
    except SourceSubjectProofError as exc:
        raise RecapSourceObservationPrepareError(str(exc)) from exc


def _subject_proof(*, bundle, world_id, parent_id, historical_id, basis, resolved, preview, refs):
    from apps.live_control_server.services.recap_source_subject_proof import prove_source_subject, SourceSubjectProofError
    rows,observations=[],[]
    common=None
    for ref in refs:
        try:
            proven=prove_source_subject(bundle=bundle,world_id=world_id,parent_id=parent_id,
                historical_id=historical_id,basis=basis,resolved=resolved,preview=preview,ref=ref)
        except SourceSubjectProofError as exc:
            raise RecapSourceObservationPrepareError(str(exc)) from exc
        node,complete=proven.node,proven.complete
        # Description support and duplicate eligibility belong only to this purpose.
        publication=bundle.finalized_review_publications.get_for_published_revision(world_id,historical_id)
        state=bundle.contribution_reviews.get(world_id,publication.review_id)
        assertion=next(a for a in state.reviewed_contribution.assertions
                       if a.assertion_id==proven.row["historical_assertion_id"])
        _require(json.loads(assertion.value).get("summary")==(node.description or "").strip(),
                 "historical node description differs from pinned candidate")
        observation=map_recap_source_observation(
            node,durable_node_id=ref.node_id,source_revision_id=resolved.source_revision_id,
            verified_source_artifact_id=resolved.source_artifact_id,campaign_scope=resolved.campaign_id,
            session_id=resolved.session_id,campaign_id=resolved.campaign_id,source_uri=resolved.sealed_source_uri,
            identity_resolution_outcome="resolved_existing")
        _require(observation is not None,"source node has no eligible description")
        _require(not any(r.source_artifact_id==resolved.source_artifact_id
            and r.source_revision_id==resolved.source_revision_id and r.text==observation.value["summary"]
            for r in complete.reviewed_source_observations),
            "description observation is already published for this source/subject")
        rows.append({**proven.row,"description_sha256":hashlib.sha256(node.description.strip().encode()).hexdigest(),
                     "observation_assertion_id":observation.assertion_id})
        observations.append(observation)
        common=proven.common
    _require(len({r["subject_id"] for r in rows})==len(rows) and rows,"duplicate or empty subject references")
    return {"schema":SCHEMA,**common,"subjects":rows},observations


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
