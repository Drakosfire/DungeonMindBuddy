"""Disposable end-to-end producer and historical-subject preparation fixtures."""
from datetime import timedelta
import copy
import hashlib
import json
import os
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from tests._cutover_direct_dungeonmind_read_helpers import _payload, _seed_sources, NOW
from tests.test_candidate_graph_to_contribution import _semantic, _diagnostics
from dungeonmind.application.existing_world_adoption import adopt_existing_world
from dungeonmind.contracts.existing_world_adoption import (
    ExistingWorldAdoptionBundleV2, ExistingWorldAdoptionSourceProvenanceV1,
    existing_world_adoption_bundle_v2_canonical_bytes,
)
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle
from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import DungeonMindWorldGraphSourceAdmissionAdapter
from apps.live_control_server.services import extract_promote
from apps.live_control_server.services.candidate_graph_admission import prepare_candidate_graph_admission
from apps.live_control_server.services.graph_run_registry import create_extraction_run, update_extraction_run_status
from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact, source_span_index_path
from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding
from apps.live_control_server.models.reviewed_extract_confirmation import TrustedGMExtractContext
from apps.live_control_server.services.reviewed_extract_confirmation import confirm_reviewed_extract
from graph_memory.ingestion.extraction_run import ExtractionRunComponentRef, ExtractionRunStatus
from apps.live_control_server.services.recap_source_observation_prepare import prepare_recap_source_observations, RecapSourceObservationPrepareError
from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringObjectRefPayload

TEXT="Clerk Mira records festival entries.\n"
pytestmark = pytest.mark.skipif(
    not os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL"),
    reason="dedicated disposable Core database required",
)


def review_and_confirm(case, package, selected):
    package_bytes=(json.dumps(package,sort_keys=True,indent=2)+"\n").encode()
    parent=case["bundle"].world_graph.get_revision(case["world"],package["effect"]["parent_revision_id"])
    review={
        "schema_version":"dmb_reviewed_extract_confirmation_v1",
        "semantic_reviewer_kind":"agent_steward","semantic_reviewer_id":"test:independent-review",
        "reviewed_at":(NOW+timedelta(days=1)).isoformat(),
        "proposal_id":package["proposal_id"],"proposal_digest":package["proposal_digest"],
        "prepared_package_sha256":hashlib.sha256(package_bytes).hexdigest(),
        "source_run_id":case["run_id"],"source_artifact_id":case["artifact"].source_artifact_id,
        "source_revision_id":package["effect"]["source_revision_id"],
        "source_body_sha256":case["artifact"].content_sha256,
        "source_span_index_sha256":hashlib.sha256(case["span"].read_bytes()).hexdigest(),
        "candidate_graph_sha256":hashlib.sha256(case["candidate"].read_bytes()).hexdigest(),
        "candidate_admission_digest":package["effect"]["candidate_admission"]["candidate_digest"],
        "expected_parent_revision_id":parent.revision.revision_id,
        "expected_parent_payload_sha256":parent.revision.graph_payload_sha256,
        "decisions":sorted([{"assertion_id":a["assertion_id"],
            "disposition":"accept" if a["assertion_id"] in selected else "defer"}
            for a in package["effect"]["accepted_proposals"]],key=lambda x:x["assertion_id"]),
        "selected_assertion_ids":sorted(selected),
    }
    data=json.dumps(review,sort_keys=True).encode()
    context=TrustedGMExtractContext(
        managed_world_id="managed-test",native_world_id=case["world"],campaign_id="longmont-c2",
        expected_parent_revision_id=parent.revision.revision_id)
    kwargs=dict(
        context=context,artifact_bytes=data,artifact_sha256=hashlib.sha256(data).hexdigest(),
        sealed_package_bytes=package_bytes,gm_capability_policy=writes._confirm_capability_policy(
            world_id=case["world"],campaign_id="longmont-c2",parent_revision_id=parent.revision.revision_id),
        database_url=case["dsn"],repo_root=case["root"])
    receipt=confirm_reviewed_extract(**kwargs)
    return receipt,package_bytes,kwargs


@pytest.fixture
def observation_case(tmp_path,monkeypatch,application_state_dsn):
    dsn=os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL","").strip()
    if not dsn:
        pytest.skip("dedicated DMB_RECAP_OBSERVATION_TEST_DATABASE_URL required")
    parsed=urlparse(dsn)
    assert parsed.hostname in {"127.0.0.1","localhost"} and parsed.path.lstrip("/").startswith("dmb_observation_test_")
    token=uuid4().hex[:10]
    world="observation-test-"+token
    bundle=PostgresRepositoryBundle(PostgresDatabase(dsn))
    payload=_payload()
    payload["world_id"]=world
    evidence_ids={e["evidence_ref_id"] for e in payload["evidence_refs"]}
    def namespace_evidence(value):
        if isinstance(value,dict):
            return {k:namespace_evidence(v) for k,v in value.items()}
        if isinstance(value,list):
            return [namespace_evidence(v) for v in value]
        return value+":"+token if isinstance(value,str) and value in evidence_ids else value
    payload=namespace_evidence(payload)
    from dungeonmind.application.graph_snapshot_v6 import UnionGraphV6Payload
    payload=UnionGraphV6Payload.model_validate(payload).model_dump(mode="json")
    seed=_seed_sources()
    pairs={e["source_artifact_id"]:e["source_revision_id"] for e in payload["evidence_refs"]}
    sources=[]
    revisions=[]
    for artifact_id,revision_id in pairs.items():
        artifact=seed.get_artifact(artifact_id)
        revision=seed.get_revision(revision_id)
        new_id=artifact_id+":"+token
        new_revision=revision_id+":"+token
        sources.append(artifact.model_copy(update={"source_artifact_id":new_id,"world_id":world,"current_revision_id":new_revision}))
        revisions.append(revision.model_copy(update={"source_revision_id":new_revision,"source_artifact_id":new_id}))
        for evidence in payload["evidence_refs"]:
            if evidence["source_artifact_id"]==artifact_id:
                evidence["source_artifact_id"]=new_id
                evidence["source_revision_id"]=new_revision
    adoption=ExistingWorldAdoptionBundleV2(
        adoption_id="adoption:"+token,world_id=world,
        source_provenance=ExistingWorldAdoptionSourceProvenanceV1(
            producer_id="synthetic-test",producer_revision=token,source_world_revision_id="legacy:"+token,
            source_graph_payload_sha256=canonical_sha256(payload)),
        graph_schema="dm_union_graph_v6",graph_payload=payload,source_artifacts=sources,
        source_revisions=revisions,contributions=[],identity_decisions=[])
    adopt_existing_world(existing_world_adoption_bundle_v2_canonical_bytes(adoption),
        adopted_at=NOW,adoption_repository=bundle.existing_world_adoptions,graph_reader=writes._build_graph_reader())
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",dsn)
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT",str(tmp_path))
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY","dungeonmind")
    monkeypatch.setattr(extract_promote,"repo_root",lambda:tmp_path)
    binding=VerifiedManagedWorldBinding("managed-test",world,1,"corpus/managed-test-markdown")
    monkeypatch.setattr("apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding",lambda *_a,**_k:binding)
    monkeypatch.setattr(extract_promote,"resolve_managed_world_binding",lambda *_a,**_k:binding)
    artifact=create_recap_source_artifact(tmp_path,campaign_id="longmont-c2",session_id="session-22",
        recap_text=TEXT+"\nSynthetic fixture "+token+".\n")
    span=source_span_index_path(tmp_path,artifact.source_artifact_id)
    index=json.loads(span.read_text())
    candidate=tmp_path/"out/graph_memory/runs/extraction"/token/"candidate_graph.json"
    candidate.parent.mkdir(parents=True)
    node={
        "node_id":"npc_mira","label":"Clerk Mira","node_type":"character","description":TEXT.strip(),
        "importance":"medium","semantic_state":_semantic(),"proposed_action":"create",
        "confidence":"medium","warnings":[],"evidence_refs":[{
            "source_ref_id":index["source_ref_id"],"source_artifact_id":artifact.source_artifact_id,
            "source_anchor_id":"anchor:mira","label":"recap","evidence_role":"source_evidence",
            "can_open_source":True,"can_highlight_span":True,
            "source_span_ref_id":index["spans"][0]["source_span_id"],"anchor_quotes":[TEXT.strip()]}],
    }
    raw={"schema":"dmb_candidate_graph_preview_v0","version":"0.1","preview_id":"preview:"+token,
        "campaign_id":"longmont-c2","session_id":"session-22","source_artifact_ids":[artifact.source_artifact_id],
        "status":"preview","nodes":[node],"edges":[],"beats":[],"proposed_writes":[],
        "ignored_items":[],"deferred_items":[],"diagnostics":_diagnostics()}
    candidate.write_text(json.dumps(raw))
    paths={"source_artifact":tmp_path/artifact.uri.removeprefix("repo://"),"source_span_index":span,"candidate_graph":candidate}
    components={key:ExtractionRunComponentRef(kind=key,uri="repo://"+path.relative_to(tmp_path).as_posix(),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for key,path in paths.items()}
    run_id="run:"+token
    run=create_extraction_run(tmp_path,run_id=run_id,source_artifact_id=artifact.source_artifact_id,
        source_domain="recap",campaign_id="longmont-c2",session_id="session-22",
        profile_id="recap_category_v1@1.0",components=components)
    for status in ("prepared","extracted","validated","reviewable"):
        run=update_extraction_run_status(tmp_path,run_id,status=ExtractionRunStatus(status),
            expected_revision=run.revision)
    from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
    resolved=resolve_promotable_ingest_run(run_id,root=tmp_path)
    context=writes.load_production_mutation_context(world)
    result=prepare_candidate_graph_admission(
        candidate_graph=raw,source_uri=resolved.sealed_source_uri,source_revision_id="sha256:"+artifact.content_sha256,
        world_id=world,source_artifact_id=artifact.source_artifact_id,source_artifact=artifact,
        campaign_scope="longmont-c2",extraction_profile="recap_category_v1@1.0",
        repo_root=tmp_path,candidate_graph_path=str(candidate),prepared_by="test:producer",
        mutation_context=context,source_admission=DungeonMindWorldGraphSourceAdmissionAdapter(sources=bundle.sources))
    package=writes.bind_identity_ledger_to_package(result.review_package,context)
    package=extract_promote._seal_publication_target(package,binding)
    assert package["effect"]["accepted_proposals"], json.dumps(package["effect"]["candidate_admission"]["dispositions"])
    return dict(root=tmp_path,world=world,dsn=dsn,bundle=bundle,artifact=artifact,
        span=span,candidate=candidate,run_id=run_id,package=package)


def test_source_proven_existing_followup_has_no_node_or_authored_field_effect(observation_case):
    case=observation_case
    package=case["package"]
    node=next(a for a in package["effect"]["accepted_proposals"] if a["assertion_kind"]=="node")
    first,old_bytes,_=review_and_confirm(case,package,[node["assertion_id"]])
    parent=case["bundle"].world_graph.get_revision(case["world"],first["committed_revision_id"])
    before=copy.deepcopy(parent.graph_payload)
    ref=GraphObjectAuthoringObjectRefPayload(refKind="existing_graph_node",nodeId=node["subject_node_id"],label="label is not authority",kind="npc")
    prepared=prepare_recap_source_observations(
        bundle=case["bundle"],managed_world_id="managed-test",source_run_id=case["run_id"],
        historical_publication_revision_id=first["committed_revision_id"],
        historical_package_bytes=old_bytes,subjects=[ref],repo_root=case["root"])
    assert not prepared["review_items"][0]["selected_by_default"]
    assert TEXT.strip() in prepared["review_items"][0]["summary"]
    assertions=prepared["review_package"]["effect"]["accepted_proposals"]
    assert len(assertions)==1 and assertions[0]["assertion_kind"]=="attribute"
    second,_,kwargs=review_and_confirm(case,prepared["review_package"],[assertions[0]["assertion_id"]])
    child=case["bundle"].world_graph.get_revision(case["world"],second["committed_revision_id"])
    assert child.graph_payload==before
    assert confirm_reviewed_extract(**kwargs)["outcome"]=="already_applied"
    assert case["bundle"].world_graph.get_revision(case["world"],first["committed_revision_id"]).graph_payload==before


@pytest.mark.parametrize("drift",["package","subject","historical","description","kind","kind_suffix","source","span"])
def test_followup_rejects_unproved_historical_bindings(observation_case,drift):
    case=observation_case
    node=next(a for a in case["package"]["effect"]["accepted_proposals"] if a["assertion_kind"]=="node")
    receipt,old_bytes,_=review_and_confirm(case,case["package"],[node["assertion_id"]])
    ref=GraphObjectAuthoringObjectRefPayload(refKind="existing_graph_node",nodeId=node["subject_node_id"],label="exact")
    historical=receipt["committed_revision_id"]
    if drift=="package":
        old_bytes=old_bytes+b" "
    elif drift=="subject":
        ref.node_id="unproved"
    elif drift=="historical":
        historical=case["package"]["effect"]["parent_revision_id"]
    elif drift=="kind":
        ref.kind="location"
    elif drift=="kind_suffix":
        ref.kind="invented:npc"
    elif drift=="source":
        (case["root"]/case["artifact"].uri.removeprefix("repo://")).write_text("wrong body")
    elif drift=="span":
        case["span"].write_text(case["span"].read_text()+" ")
    else:
        case["candidate"].write_text(case["candidate"].read_text().replace("records festival","invented detail"))
    head=case["bundle"].world_graph.get_head(case["world"]).head_revision_id
    with pytest.raises((RecapSourceObservationPrepareError,ValueError)):
        prepare_recap_source_observations(
            bundle=case["bundle"],managed_world_id="managed-test",source_run_id=case["run_id"],
            historical_publication_revision_id=historical,historical_package_bytes=old_bytes,
            subjects=[ref],repo_root=case["root"])
    assert case["bundle"].world_graph.get_head(case["world"]).head_revision_id==head


def test_already_published_description_is_not_proposed_again(observation_case):
    case=observation_case
    package=case["package"]
    node=next(a for a in package["effect"]["accepted_proposals"] if a["assertion_kind"]=="node")
    first,old_bytes,_=review_and_confirm(case,package,[a["assertion_id"] for a in package["effect"]["accepted_proposals"]])
    with pytest.raises(RecapSourceObservationPrepareError,match="already published"):
        prepare_recap_source_observations(
            bundle=case["bundle"],managed_world_id="managed-test",source_run_id=case["run_id"],
            historical_publication_revision_id=first["committed_revision_id"],
            historical_package_bytes=old_bytes,subjects=[GraphObjectAuthoringObjectRefPayload(
                refKind="existing_graph_node",nodeId=node["subject_node_id"],label="exact",kind="dnd5e:npc")],
            repo_root=case["root"])


@pytest.mark.parametrize("drift",["text","subject_hash"])
def test_reproof_rejects_changed_sealed_descriptors_even_if_resealed(observation_case,drift):
    from apps.live_control_server.services.recap_source_observation_prepare import reprove_recap_source_observation_binding
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    case=observation_case
    package=case["package"]
    node=next(a for a in package["effect"]["accepted_proposals"] if a["assertion_kind"]=="node")
    first,old_bytes,_=review_and_confirm(case,package,[node["assertion_id"]])
    prepared=prepare_recap_source_observations(
        bundle=case["bundle"],managed_world_id="managed-test",source_run_id=case["run_id"],
        historical_publication_revision_id=first["committed_revision_id"],
        historical_package_bytes=old_bytes,subjects=[GraphObjectAuthoringObjectRefPayload(
            refKind="existing_graph_node",nodeId=node["subject_node_id"],label="exact")],
        repo_root=case["root"])
    altered=copy.deepcopy(prepared["review_package"])
    if drift=="text":
        altered["effect"]["accepted_proposals"][0]["value"]["summary"]="Unreviewed invented detail"
        altered["effect"]["recap_source_observation_basis"]["subjects"][0]["description_sha256"]=hashlib.sha256(b"Unreviewed invented detail").hexdigest()
    else:
        altered["effect"]["recap_source_observation_basis"]["subjects"][0]["current_subject_sha256"]="f"*64
    altered["proposal_digest"]=compute_proposal_digest(altered["effect"])
    with pytest.raises(RecapSourceObservationPrepareError,match="drift"):
        reprove_recap_source_observation_binding(
            bundle=case["bundle"],package=altered,repo_root=case["root"])
