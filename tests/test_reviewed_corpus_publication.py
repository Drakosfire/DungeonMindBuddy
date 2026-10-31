from __future__ import annotations

from tests.application_state.world_catalog_fixtures import store_world


from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from dungeonmind.contracts.capability import (
    CapabilityPolicy,
    GraphScope,
    ToolCapabilityRule,
)
from dungeonmind.contracts.contribution import (
    GraphContributionV2,
    GraphContributionAssertionV2,
)
from dungeonmind.contracts.contribution_review import (
    ContributionPlanRef,
    ContributionAssertionVerdict,
    ContributionIdentityProposal,
    ContributionIdentityVerdict,
    derive_confirmation_id,
)
from dungeonmind.contracts.contribution_review_v2 import (
    ContributionReviewIntentV2,
    ContributionReviewSubmissionV2,
    CommitConfirmationReceiptV2,
    derive_review_intent_sha256_v2,
    contribution_v2_payload_sha256,
)
from dungeonmind.contracts.evidence import SourceArtifactV2, SourceRevision, EvidenceRef
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.memory import (
    InMemoryWorldGraphRepository,
    InMemorySourceRepository,
    InMemoryContributionRepository,
    InMemoryContributionReviewRepository,
    InMemoryFinalizedReviewPublicationRepository,
    InMemoryExistingWorldAdoptionRepository,
    InMemoryIdentityDecisionRepository,
)
from dungeonmind.application.graph_snapshot_v6 import UnionGraphV6Payload
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_v3_descriptor,
)
from apps.live_control_server.services.world_container_registry import (
    create_world_container,
    NativeGraphBindingRecord,
)
from apps.live_control_server.services.reviewed_corpus_publication import (
    CorePublicationBackend,
    ReviewedCorpusPacket,
    ReviewedCorpusPublicationProcedure,
    ProcedureStopped,
)
from apps.live_control_server.services.reviewed_corpus_publication_store import (
    PublicationProgressStore,
    ProgressConflict,
)

NOW = datetime(2026, 10, 12, 10, tzinfo=UTC)
BODY = b"# Fixture\n\nSynthetic reviewed statement.\n"


def corpus_case(tmp_path: Path, bundle=None):
    if bundle is None:
        graph, sources, contributions = (
            InMemoryWorldGraphRepository(),
            InMemorySourceRepository(),
            InMemoryContributionRepository(),
        )
        reviews = InMemoryContributionReviewRepository(contributions)
        publication = InMemoryFinalizedReviewPublicationRepository(
            reviews, graph, source_repository=sources
        )
        bundle = SimpleNamespace(
            world_graph=graph,
            sources=sources,
            contributions=contributions,
            contribution_reviews=reviews,
            finalized_review_publications=publication,
            reviewed_world_initializations=SimpleNamespace(
                get_for_world=lambda _world: None
            ),
        )
        bundle.existing_world_adoptions = InMemoryExistingWorldAdoptionRepository(
            graph, sources, contributions, InMemoryIdentityDecisionRepository()
        )
    profile = SemanticProfileRef(
        profile_id="dungeonmind.dnd5e",
        profile_revision="dnd5e-profile-v3",
        descriptor_sha256=descriptor_sha256(load_builtin_v3_descriptor()),
    )
    native = "native-corpus-test"
    payload = UnionGraphV6Payload.model_validate(
        {
            "world_id": native,
            "semantic_profile": profile.model_dump(mode="json"),
            "relationship_endpoint_aspect_schema": "dm_relationship_endpoint_aspect_v1",
            "objects": [],
            "relationships": [],
            "evidence_refs": [],
        }
    ).model_dump(mode="json")
    from dungeonmind.application.existing_world_adoption import adopt_existing_world
    from dungeonmind.contracts.existing_world_adoption import (
        ExistingWorldAdoptionBundleV2,
        ExistingWorldAdoptionSourceProvenanceV1,
        existing_world_adoption_bundle_v2_canonical_bytes,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _build_graph_reader,
    )

    adoption = ExistingWorldAdoptionBundleV2(
        adoption_id="adoption:fixture",
        world_id=native,
        source_provenance=ExistingWorldAdoptionSourceProvenanceV1(
            producer_id="synthetic-fixture",
            producer_revision="1",
            source_world_revision_id="legacy:fixture",
            source_graph_payload_sha256=canonical_sha256(payload),
        ),
        graph_schema="dm_union_graph_v6",
        graph_payload=payload,
        source_artifacts=[],
        source_revisions=[],
        contributions=[],
        identity_decisions=[],
    )
    adopt_existing_world(
        existing_world_adoption_bundle_v2_canonical_bytes(adoption),
        adopted_at=NOW,
        adoption_repository=bundle.existing_world_adoptions,
        graph_reader=_build_graph_reader(),
    )
    parent = bundle.world_graph.get_revision(
        native, bundle.world_graph.get_head(native).head_revision_id
    ).revision
    registry = tmp_path / "registry"
    managed = create_world_container(registry, name="Synthetic Corpus")
    store_world(managed.model_copy(update={"native_graph_binding": NativeGraphBindingRecord(
        native_world_id=native, binding_version=1, status="active",
        validated_at=NOW.isoformat(), validated_head_revision_id=parent.revision_id,
    )}))
    artifacts = tmp_path / "artifacts"
    body_path = artifacts / managed.source_root_relpath / "fixture.md"
    body_path.parent.mkdir(parents=True)
    body_path.write_bytes(BODY)
    uri = "repo://" + body_path.relative_to(artifacts).as_posix()
    sha = hashlib.sha256(BODY).hexdigest()
    source = SourceArtifactV2(
        source_artifact_id="source:fixture",
        world_id=native,
        campaign_id="fixture-campaign",
        session_id="session-1",
        source_domain_key="fixture.recaps",
        source_domain="session_recap",
        uri=uri,
        current_revision_id="sha256:" + sha,
        authority="primary",
        visibility="gm",
        artifact_kind=None,
        document_class=None,
        source_visibility_state=None,
        workspace_document_ref=None,
        review_state="reviewed",
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )
    revision = SourceRevision(
        source_revision_id=source.current_revision_id,
        source_artifact_id=source.source_artifact_id,
        content_sha256=sha,
        body_storage="external",
        locator=uri,
        created_at=NOW,
    )
    evidence = EvidenceRef(
        evidence_ref_id="evidence:shared",
        source_artifact_id=source.source_artifact_id,
        source_revision_id=revision.source_revision_id,
        source_domain="session_recap",
        evidence_role="support",
        can_open_source=True,
        can_highlight_span=False,
        locator="heading:Fixture",
        uri=uri,
    )
    assertions = [
        GraphContributionAssertionV2(
            assertion_id="assertion:" + suffix,
            assertion_kind="node",
            subject_object_id="npc:" + suffix,
            label="Fixture " + suffix,
            value=json.dumps({"dm_kind": "dnd5e:npc", "kind": "npc"}),
            evidence_refs=[evidence],
            campaign_scope="fixture-campaign",
        )
        for suffix in ("a", "b")
    ]
    assertions.append(
        GraphContributionAssertionV2(
            assertion_id="assertion:edge",
            assertion_kind="edge",
            subject_object_id="npc:a",
            object_object_id="npc:b",
            predicate="knows_about",
            value='{"dm_predicate":"dnd5e:knows_about"}',
            evidence_refs=[evidence],
            campaign_scope="fixture-campaign",
        )
    )
    candidate = GraphContributionV2(
        contribution_id="contrib:" + "a" * 32,
        world_id=native,
        source_kind="graph_review",
        produced_at=NOW,
        source_artifact_id=source.source_artifact_id,
        source_revision_id=revision.source_revision_id,
        campaign_scope="fixture-campaign",
        assertions=assertions,
    )
    plan = ContributionPlanRef(
        source_plan_schema="synthetic_reviewed_packet_v1",
        source_plan_id="fixture:plan",
        source_plan_sha256="1" * 64,
        source_input_sha256="2" * 64,
        preview_content_sha256="3" * 64,
        candidate_contribution_sha256=contribution_v2_payload_sha256(candidate),
        expected_parent_revision_id=parent.revision_id,
        base_graph_schema="dm_union_graph_v6",
        base_graph_payload_sha256=canonical_sha256(payload),
        semantic_profile=profile,
    )
    proposals = [
        ContributionIdentityProposal(
            candidate_id="candidate:" + suffix,
            candidate_kind="dnd5e:npc",
            planned_outcome="provisional_new",
            target_object_id="npc:" + suffix,
        )
        for suffix in ("a", "b")
    ]
    identities = [
        ContributionIdentityVerdict(
            candidate_id="candidate:" + suffix,
            verdict="create_new",
            target_object_id="npc:" + suffix,
        )
        for suffix in ("a", "b")
    ]
    verdicts = [
        ContributionAssertionVerdict(
            assertion_id=a.assertion_id, acceptance_state="accepted"
        )
        for a in assertions
    ]
    operation = "reviewop:" + "0" * 32
    intent_sha = derive_review_intent_sha256_v2(
        operation_id=operation,
        world_id=native,
        campaign_id="fixture-campaign",
        plan_ref=plan,
        candidate_contribution=candidate,
        identity_proposals=proposals,
        identity_verdicts=identities,
        assertion_verdicts=verdicts,
        reviewer_id="gm:synthetic-review",
        reviewed_at=NOW,
    )
    intent = ContributionReviewIntentV2(
        operation_id=operation,
        world_id=native,
        campaign_id="fixture-campaign",
        plan_ref=plan,
        candidate_contribution=candidate,
        identity_proposals=proposals,
        identity_verdicts=identities,
        assertion_verdicts=verdicts,
        reviewer_id="gm:synthetic-review",
        reviewed_at=NOW,
        review_intent_sha256=intent_sha,
    )
    submission = ContributionReviewSubmissionV2(
        intent=intent,
        confirmation=CommitConfirmationReceiptV2(
            confirmation_id=derive_confirmation_id(
                operation_id=operation,
                review_intent_sha256=intent_sha,
                actor=intent.reviewer_id,
                confirmed_at=NOW,
            ),
            operation_id=operation,
            review_intent_sha256=intent_sha,
            actor=intent.reviewer_id,
            world_id=native,
            campaign_id=intent.campaign_id,
            expected_parent_revision_id=parent.revision_id,
            confirmed_at=NOW,
        ),
    )
    policy = CapabilityPolicy(
        policy_id="fixture:approved-policy",
        graph_scope=GraphScope(
            world_id=native,
            campaign_id=intent.campaign_id,
            admissibility="gm",
            revision_pin=parent.revision_id,
        ),
        enabled_tools=["dungeonmind.finalize_contribution_review_v2"],
        tool_rules=[
            ToolCapabilityRule(
                tool_name="dungeonmind.finalize_contribution_review_v2",
                category="confirm_commit",
                allowed_effects=["commit"],
            )
        ],
    )
    packet = ReviewedCorpusPacket(
        managed_world_id=managed.world_id,
        native_world_id=native,
        binding_version=1,
        source_root_relpath=managed.source_root_relpath,
        sources=[
            {
                "admission_id": "admission:fixture",
                "artifact": source,
                "revision": revision,
            }
        ],
        submission=submission,
        capability_policy=policy,
    )
    backend = CorePublicationBackend(
        bundle, artifact_root=artifacts, registry_root=registry
    )
    store = PublicationProgressStore(tmp_path / "progress")
    return SimpleNamespace(
        packet=packet,
        backend=backend,
        store=store,
        bundle=bundle,
        root=artifacts,
        registry=registry,
        body_path=body_path,
        parent=parent,
        payload=payload,
    )


def procedure(case):
    times = iter([NOW + timedelta(seconds=i) for i in range(1, 10)])
    return ReviewedCorpusPublicationProcedure(
        case.backend, case.store, clock=lambda: next(times)
    )


def execute(case, **kwargs):
    return procedure(case).run(
        case.packet,
        selected_world_id=case.packet.managed_world_id,
        execute=True,
        schema_ready=True,
        backup_verified=True,
        **kwargs,
    )


def standing_neighborhood(case):
    """Synthetic unrelated existing neighborhood above the unchanged 16 bound."""
    import copy

    parent = case.bundle.world_graph.get_revision(
        case.packet.native_world_id,
        case.backend.publication_probe(case.packet).published_revision_id,
    )
    payload = copy.deepcopy(parent.graph_payload)
    node = next(row for row in payload["objects"] if row["object_id"] == "npc:b")
    relationship = payload["relationships"][0]
    for index in range(20):
        row = copy.deepcopy(node)
        row["object_id"] = f"npc:standing-{index}"
        row["aliases"] = []
        row["assertion_metadata"]["assertion_id"] = f"ka:standing:node:{index}"
        payload["objects"].append(row)
        edge = copy.deepcopy(relationship)
        edge["relationship_id"] = f"edge:standing:{index}"
        edge["source_object_id"] = "npc:a"
        edge["target_object_id"] = row["object_id"]
        edge["assertion_metadata"]["assertion_id"] = f"ka:standing:edge:{index}"
        payload["relationships"].append(edge)
    child = case.bundle.world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=case.packet.native_world_id,
            parent_revision_id=parent.revision.revision_id,
            expected_parent_revision_id=parent.revision.revision_id,
            operation_ids=["fixture:standing-neighborhood"],
            graph_schema="dm_union_graph_v6",
            graph_payload=payload,
            created_at=NOW + timedelta(hours=1),
        )
    )
    return child.revision_id


def observation_packet(case, parent_revision_id=None):
    """Synthetic immutable review of a standing subject; no extraction or node write."""
    parent = case.bundle.world_graph.get_revision(
        case.packet.native_world_id,
        parent_revision_id
        or case.backend.publication_probe(case.packet).published_revision_id,
    )
    evidence = case.packet.submission.intent.candidate_contribution.assertions[
        0
    ].evidence_refs[0]
    assertion = GraphContributionAssertionV2(
        assertion_id="assertion:observation",
        assertion_kind="attribute",
        subject_object_id="npc:a",
        value=json.dumps(
            {
                "property_term": "session_observation",
                "summary": "Synthetic reviewed statement.",
                "kind": "dnd5e:npc",
            }
        ),
        evidence_refs=[evidence],
        campaign_scope="fixture-campaign",
    )
    candidate = case.packet.submission.intent.candidate_contribution.model_copy(
        update={"contribution_id": "contrib:" + "b" * 32, "assertions": [assertion]}
    )
    plan = case.packet.submission.intent.plan_ref.model_copy(
        update={
            "source_plan_id": "fixture:observation-plan",
            "source_plan_sha256": "4" * 64,
            "candidate_contribution_sha256": contribution_v2_payload_sha256(candidate),
            "expected_parent_revision_id": parent.revision.revision_id,
            "base_graph_payload_sha256": canonical_sha256(parent.graph_payload),
        }
    )
    at = NOW + timedelta(days=1)
    operation = "reviewop:" + "1" * 32
    verdicts = [
        ContributionAssertionVerdict(
            assertion_id=assertion.assertion_id, acceptance_state="accepted"
        )
    ]
    fields = dict(
        operation_id=operation,
        world_id=case.packet.native_world_id,
        campaign_id="fixture-campaign",
        plan_ref=plan,
        candidate_contribution=candidate,
        identity_proposals=[],
        identity_verdicts=[],
        assertion_verdicts=verdicts,
        reviewer_id="gm:synthetic-review",
        reviewed_at=at,
    )
    digest = derive_review_intent_sha256_v2(**fields)
    submission = ContributionReviewSubmissionV2(
        intent=ContributionReviewIntentV2(**fields, review_intent_sha256=digest),
        confirmation=CommitConfirmationReceiptV2(
            confirmation_id=derive_confirmation_id(
                operation_id=operation,
                review_intent_sha256=digest,
                actor=fields["reviewer_id"],
                confirmed_at=at,
            ),
            operation_id=operation,
            review_intent_sha256=digest,
            actor=fields["reviewer_id"],
            world_id=case.packet.native_world_id,
            campaign_id="fixture-campaign",
            expected_parent_revision_id=parent.revision.revision_id,
            confirmed_at=at,
        ),
    )
    policy = case.packet.capability_policy.model_copy(
        update={
            "graph_scope": case.packet.capability_policy.graph_scope.model_copy(
                update={"revision_pin": parent.revision.revision_id}
            )
        }
    )
    return case.packet.model_copy(
        update={
            "sources": (
                case.packet.sources[0].model_copy(
                    update={"admission_id": "admission:observation"}
                ),
            ),
            "submission": submission,
            "capability_policy": policy,
        }
    )


@pytest.fixture
def case(tmp_path, monkeypatch):
    result = corpus_case(tmp_path)

    def verify(packet, publication):
        effects = result.backend.effects(packet)
        assert publication.graph_payload_sha256 == effects["graph_payload_sha256"]
        return {
            "core_verified": True,
            "selected_world_service_verified": False,
            "source_open_status": "incomplete",
            "effects": effects,
            "buddy_http_route_status": "not_exercised",
            "product_ready": False,
        }

    monkeypatch.setattr(result.backend, "verify", verify)
    return result


def test_uninterrupted_sequence_derived_effects_and_private_journal(case):
    result = execute(case)
    assert result["status"] == "published"
    effects = result["verification"]["effects"]
    assert (
        len(effects["introduced_evidence_ids"]) == 1
    )  # shared evidence, not assertion/table counts
    assert (
        len(effects["changed_object_ids"]) == 2
        and len(effects["changed_relationship_ids"]) == 1
    )
    journal = case.store.read(case.packet.operation_id)
    assert journal["identities"]["review_id"] == case.packet.review_id
    assert all(s["status"] == "committed" for s in journal["stages"].values())
    text = json.dumps(journal)
    assert "Synthetic reviewed statement" not in text and "repo://" not in text
    assert result["all_stage_atomicity"] is False and result["product_ready"] is False


@pytest.mark.parametrize("stage", ["source:admission:fixture", "review", "publication"])
def test_resume_each_committed_stage_preserves_ids_and_first_times(case, stage):
    execute(case, stop_after=stage)
    before = case.store.read(case.packet.operation_id)
    result = execute(case)
    assert result["status"] == "published"
    after = case.store.read(case.packet.operation_id)
    for name, value in before["stages"].items():
        assert after["stages"][name] == value
    assert after["operation_id"] == case.packet.operation_id
    assert case.backend.review_probe(case.packet).record.reviewed_at == NOW


@pytest.mark.parametrize("method", ["admit", "finalize", "publish"])
def test_lost_response_probes_exact_receipt_and_never_duplicates(
    case, monkeypatch, method
):
    original = getattr(case.backend, method)
    calls = []

    def lost(*args):
        calls.append(args)
        original(*args)
        raise RuntimeError("synthetic lost response")

    monkeypatch.setattr(case.backend, method, lost)
    assert execute(case)["status"] == "published"
    assert execute(case)["status"] == "published"
    assert len(calls) == 1


def test_unknown_without_receipt_stops_and_only_probes(case, monkeypatch):
    calls = []

    def uncertain(*args):
        calls.append(args)
        raise RuntimeError("unknown transport")

    monkeypatch.setattr(case.backend, "admit", uncertain)
    assert execute(case)["status"] == "unknown"
    assert execute(case)["code"] == "unresolved_previous_attempt"
    assert len(calls) == 1 and case.backend.review_probe(case.packet) is None


def test_read_only_inspection_does_not_create_files_or_effects(case):
    result = procedure(case).run(
        case.packet, selected_world_id=case.packet.managed_world_id
    )
    assert result["status"] == "pending" and not case.store.directory.exists()
    assert case.backend.source_probe(case.packet, case.packet.sources[0]) is None
    execute(case, stop_after="review")
    before = {p.name: p.read_bytes() for p in case.store.directory.iterdir()}
    assert (
        procedure(case).run(
            case.packet, selected_world_id=case.packet.managed_world_id
        )["status"]
        == "pending"
    )
    assert before == {p.name: p.read_bytes() for p in case.store.directory.iterdir()}
    assert case.backend.publication_probe(case.packet) is None


def test_changed_packet_or_source_stops_preserving_committed_work(case):
    execute(case, stop_after="review")
    before = case.store.read(case.packet.operation_id)
    changed = case.packet.model_copy(update={"source_root_relpath": "wrong"})
    with pytest.raises(ProcedureStopped):
        procedure(case).run(changed, selected_world_id=changed.managed_world_id)
    case.body_path.write_bytes(BODY + b"drift")
    result = execute(case)
    assert result["status"] == "blocked" and result["code"] == "source_bytes_changed"
    assert case.store.read(case.packet.operation_id) == before
    assert case.backend.review_probe(case.packet) is not None


def test_stale_parent_after_review_preserves_source_and_review(case):
    execute(case, stop_after="review")
    case.bundle.world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=case.packet.native_world_id,
            parent_revision_id=case.parent.revision_id,
            expected_parent_revision_id=case.parent.revision_id,
            operation_ids=["unrelated:graph"],
            graph_schema="dm_union_graph_v6",
            graph_payload=case.payload,
            created_at=NOW + timedelta(days=1),
        )
    )
    result = execute(case)
    assert result["status"] == "blocked" and result["code"] == "stale_parent"
    assert case.backend.review_probe(case.packet) is not None
    assert case.backend.source_probe(case.packet, case.packet.sources[0]) is not None
    assert case.backend.publication_probe(case.packet) is None


def test_prerequisites_binding_and_local_concurrency_fail_before_writes(case):
    with pytest.raises(ProcedureStopped, match="external_prerequisites_required"):
        procedure(case).run(
            case.packet, selected_world_id=case.packet.managed_world_id, execute=True
        )
    with pytest.raises(ProcedureStopped, match="selected_world_mismatch"):
        procedure(case).run(case.packet, selected_world_id="foreign-world")
    with case.store.exclusive(case.packet.operation_id):
        with pytest.raises(ProgressConflict, match="operation_busy"):
            execute(case)
    assert case.backend.source_probe(case.packet, case.packet.sources[0]) is None


def test_journal_cannot_manufacture_commit_authority(case):
    execute(case, stop_after="source:admission:fixture")
    value = case.store.read(case.packet.operation_id)
    value["stages"]["review"] = {
        "status": "committed",
        "first_attempt_at": NOW.isoformat(),
    }
    case.store.write(case.packet.operation_id, value)
    result = execute(case)
    assert (
        result["status"] == "unknown" and case.backend.review_probe(case.packet) is None
    )


def test_immutable_packet_digest_conflict(case):
    execute(case, stop_after="review")
    changed = case.packet.model_copy(
        update={
            "capability_policy": case.packet.capability_policy.model_copy(
                update={"policy_id": "changed"}
            )
        }
    )
    with pytest.raises(ProgressConflict, match="immutable_input_changed"):
        procedure(case).run(changed, selected_world_id=changed.managed_world_id)
    assert case.backend.publication_probe(case.packet) is None


def test_source_authority_drift_stops_without_repair(case):
    execute(case, stop_after="review")
    case.bundle.sources._artifacts[
        case.packet.sources[0].artifact.source_artifact_id
    ] = case.packet.sources[0].artifact.model_copy(
        update={"source_domain_key": "changed"}
    )
    with pytest.raises(ProcedureStopped, match="source_authority_changed"):
        execute(case)
    assert case.backend.publication_probe(case.packet) is None


def test_unrelated_catalog_rows_are_not_global_count_failures(case):
    source = case.packet.sources[0]
    case.bundle.sources.put_artifact(
        source.artifact.model_copy(
            update={
                "source_artifact_id": "source:unrelated",
                "world_id": "unrelated-world",
                "current_revision_id": "revision:unrelated",
            }
        )
    )
    case.bundle.sources.put_revision(
        source.revision.model_copy(
            update={
                "source_revision_id": "revision:unrelated",
                "source_artifact_id": "source:unrelated",
            }
        )
    )
    result = execute(case)
    assert result["verification"]["effects"]["source_pairs"] == [
        [source.artifact.source_artifact_id, source.revision.source_revision_id]
    ]


def test_cli_masks_invalid_private_packet(tmp_path):
    import subprocess
    import sys

    path = tmp_path / "private.json"
    path.write_text('{"PRIVATE_CORPUS_BODY":"never display this"}')
    run = subprocess.run(
        [
            sys.executable,
            "scripts/resume_reviewed_corpus_publication.py",
            "--packet",
            str(path),
            "--packet-sha256",
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "--managed-world",
            "synthetic",
            "--journal-directory",
            str(tmp_path / "progress"),
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2 and "PRIVATE_CORPUS_BODY" not in run.stdout + run.stderr
    assert "never display this" not in run.stdout + run.stderr
    assert not (tmp_path / "progress").exists()


def real_verifier(case, monkeypatch):
    from apps.live_control_server.services import reviewed_corpus_publication as service

    monkeypatch.setattr(
        service,
        "project_managed_world_graph",
        lambda request, **_kwargs: SimpleNamespace(
            projection=SimpleNamespace(
                snapshot=SimpleNamespace(revision_id=request.revision_pin)
            )
        ),
    )
    monkeypatch.setattr(
        case.backend, "verify", CorePublicationBackend.verify.__get__(case.backend)
    )


def test_observation_only_reads_standing_subject_and_source(case, monkeypatch):
    execute(case)
    original = case.bundle.world_graph.get_revision(
        case.packet.native_world_id,
        case.backend.publication_probe(case.packet).published_revision_id,
    )
    case.packet = observation_packet(case)
    real_verifier(case, monkeypatch)
    result = execute(case)
    if result["verification"].get("status") == "unavailable":
        case.backend.verify(case.packet, case.backend.publication_probe(case.packet))
    assert result["status"] == "verified"
    effects = result["verification"]["effects"]
    assert (
        effects["changed_object_ids"] == [] and effects["introduced_evidence_ids"] == []
    )
    assert effects["readback_evidence_ids"] == ["evidence:shared"]
    assert result["verification"]["verified_assertion_ids"] == ["assertion:observation"]
    assert result["verification"]["opened_sources"]
    child = case.bundle.world_graph.get_revision(
        case.packet.native_world_id, result["published_revision_id"]
    )
    assert original.graph_payload["objects"] == child.graph_payload["objects"]


def test_missing_observation_cannot_be_verified(case, monkeypatch):
    execute(case)
    case.packet = observation_packet(case)
    execute(case)
    real_verifier(case, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )

    original = reads.get_object_with_reviewed_sources_direct

    def omitted(*args):
        result, observations, gaps, missing = original(*args)
        return result, [], gaps, missing

    monkeypatch.setattr(reads, "get_object_with_reviewed_sources_direct", omitted)
    with pytest.raises(ProcedureStopped, match="published_observation_unavailable"):
        case.backend.verify(case.packet, case.backend.publication_probe(case.packet))


@pytest.mark.parametrize(
    "change", ["missing", "wrong_target", "wrong_support", "outcome"]
)
def test_shared_node_evidence_cannot_mask_relationship_failure(
    case, monkeypatch, change
):
    execute(case)
    real_verifier(case, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )

    original = reads.get_evidence_direct

    def defective(*args):
        result = original(*args)
        if change == "missing":
            return result.model_copy(update={"relationships": []})
        if change == "wrong_target":
            return result.model_copy(
                update={
                    "request_summary": {
                        "target_kind": "relationship",
                        "target_id": "wrong",
                    }
                }
            )
        if change == "wrong_support":
            return result.model_copy(update={"source_anchors": []})
        return result.model_copy(update={"outcome": "partial"})

    monkeypatch.setattr(reads, "get_evidence_direct", defective)
    result = execute(case)
    assert (
        result["status"] == "published"
        and result["verification"]["status"] == "unavailable"
    )


@pytest.mark.parametrize("missing", [True, False])
def test_committed_publication_inspection_survives_local_source_loss(
    case, monkeypatch, missing
):
    execute(case)
    publication = case.backend.publication_probe(case.packet)
    real_verifier(case, monkeypatch)
    if missing:
        case.body_path.unlink()
    else:
        case.body_path.write_bytes(BODY + b"changed")

    def no_dispatch(*_args):
        pytest.fail("committed inspection/resume must not redispatch")

    for name in ("admit", "finalize", "publish"):
        monkeypatch.setattr(case.backend, name, no_dispatch)
    before = {p.name: p.read_bytes() for p in case.store.directory.iterdir()}
    result = procedure(case).run(
        case.packet, selected_world_id=case.packet.managed_world_id
    )
    assert (
        result["status"] == "published"
        and result["published_revision_id"] == publication.published_revision_id
    )
    assert result["verification"]["source_open_status"] == "unavailable"
    assert all(value == "committed" for value in result["observed_stages"].values())
    assert before == {p.name: p.read_bytes() for p in case.store.directory.iterdir()}
    assert execute(case)["published_revision_id"] == publication.published_revision_id


def test_missing_source_blocks_uncommitted_publication(case):
    execute(case, stop_after="review")
    case.body_path.unlink()
    result = execute(case)
    assert result["status"] == "blocked" and result["code"] == "source_body_unavailable"
    assert case.backend.publication_probe(case.packet) is None


def high_degree_observation(case, monkeypatch):
    execute(case)
    parent = standing_neighborhood(case)
    case.packet = observation_packet(case, parent)
    real_verifier(case, monkeypatch)


def standing_observation_bound_result(original, *args):
    """One required observation survives a bounded set of standing observations."""
    result, observations, gaps, missing = original(*args)
    required = observations[0]
    standing = [
        required.model_copy(update={"assertion_id": f"assertion:standing:{index}"})
        for index in range(23)
    ]
    result = result.model_copy(
        update={
            "outcome": "truncated",
            "coverage": result.coverage.model_copy(
                update={
                    "truncated_fields": sorted(
                        set(result.coverage.truncated_fields)
                        | {"reviewed_source_observations"}
                    )
                }
            ),
        }
    )
    return (
        result,
        [*standing, required],
        [*gaps, "reviewed_source_observation_anchor_bound"],
        missing,
    )


def test_high_degree_standing_relationships_do_not_hide_complete_operation(
    case, monkeypatch
):
    high_degree_observation(case, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )

    original = reads.get_object_with_reviewed_sources_direct
    seen = []

    def capture(services, request):
        result = original(services, request)
        seen.append(
            (
                result[0].outcome,
                result[0].coverage.truncated_fields,
                request.bounds.max_relationships,
            )
        )
        return result

    monkeypatch.setattr(reads, "get_object_with_reviewed_sources_direct", capture)
    result = execute(case)
    assert result["status"] == "verified"
    assert seen == [("truncated", ["relationships"], 16)]
    assert result["verification"]["verified_assertion_ids"] == ["assertion:observation"]
    assert result["verification"]["effects"]["changed_relationship_ids"] == []
    assert result["verification"]["opened_sources"] and not result["product_ready"]


def test_bounded_standing_observations_do_not_hide_complete_operation(
    case, monkeypatch
):
    high_degree_observation(case, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )

    original = reads.get_object_with_reviewed_sources_direct
    seen = []

    def bounded(*args):
        result = standing_observation_bound_result(original, *args)
        seen.append(
            (
                result[0].outcome,
                result[0].coverage.truncated_fields,
                result[2],
                len(result[1]),
                args[1].bounds.max_source_anchors,
            )
        )
        return result

    monkeypatch.setattr(reads, "get_object_with_reviewed_sources_direct", bounded)
    result = execute(case)
    assert result["status"] == "verified"
    assert seen == [
        (
            "truncated",
            ["relationships", "reviewed_source_observations"],
            ["reviewed_source_observation_anchor_bound"],
            24,
            24,
        )
    ]
    assert result["verification"]["verified_assertion_ids"] == ["assertion:observation"]
    assert result["verification"]["source_open_status"] == "verified"
    assert not result["product_ready"]


@pytest.mark.parametrize(
    "change",
    [
        "required_observation",
        "required_support",
        "other_gap",
        "missing_id",
        "other_truncated_field",
    ],
)
def test_bounded_standing_observations_cannot_hide_missing_operation_proof(
    case, monkeypatch, change
):
    high_degree_observation(case, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )

    original = reads.get_object_with_reviewed_sources_direct

    def incomplete(*args):
        result, observations, gaps, missing = standing_observation_bound_result(
            original, *args
        )
        if change == "required_observation":
            observations = observations[:-1]
        elif change == "required_support":
            result = result.model_copy(update={"source_anchors": []})
        elif change == "other_gap":
            gaps.append("other_coverage_gap")
        elif change == "missing_id":
            missing = ["required:missing"]
        else:
            result = result.model_copy(
                update={
                    "coverage": result.coverage.model_copy(
                        update={
                            "truncated_fields": [
                                *result.coverage.truncated_fields,
                                "source_anchors",
                            ]
                        }
                    )
                }
            )
        return result, observations, gaps, missing

    monkeypatch.setattr(reads, "get_object_with_reviewed_sources_direct", incomplete)
    result = execute(case)
    assert result["status"] == "published"
    assert result["verification"]["status"] == "unavailable"


@pytest.mark.parametrize(
    "change",
    [
        "node",
        "attributes",
        "source_anchors",
        "reviewed_source_observations",
        "nodes",
        "evidence",
        "gaps",
        "missing",
        "partial",
    ],
)
def test_required_operation_fields_still_fail_in_high_degree_context(
    case, monkeypatch, change
):
    high_degree_observation(case, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )

    original = reads.get_object_with_reviewed_sources_direct

    def incomplete(*args):
        result, observations, gaps, missing = original(*args)
        if change == "node":
            result = result.model_copy(update={"nodes": []})
        elif change in (
            "attributes",
            "source_anchors",
            "reviewed_source_observations",
            "nodes",
        ):
            result = result.model_copy(
                update={
                    "coverage": result.coverage.model_copy(
                        update={"truncated_fields": ["relationships", change]}
                    )
                }
            )
        elif change == "evidence":
            result = result.model_copy(
                update={
                    "coverage": result.coverage.model_copy(
                        update={"missing_evidence_ref_ids": ["evidence:shared"]}
                    )
                }
            )
        elif change == "gaps":
            gaps = ["required_facet_unavailable"]
        elif change == "missing":
            missing = ["assertion:observation"]
        else:
            result = result.model_copy(update={"outcome": "partial"})
        return result, observations, gaps, missing

    monkeypatch.setattr(reads, "get_object_with_reviewed_sources_direct", incomplete)
    result = execute(case)
    assert (
        result["status"] == "published"
        and result["verification"]["status"] == "unavailable"
    )


@pytest.mark.parametrize("change", ["lineage", "text", "support"])
def test_exact_observation_proof_survives_relationship_truncation_guard(
    case, monkeypatch, change
):
    high_degree_observation(case, monkeypatch)
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as reads,
    )

    original = reads.get_object_with_reviewed_sources_direct

    def incorrect(*args):
        result, observations, gaps, missing = original(*args)
        if change == "lineage":
            observations = [
                row.model_copy(update={"review_id": "review:wrong"})
                for row in observations
            ]
        elif change == "text":
            observations = [
                row.model_copy(update={"text": "wrong approved text"})
                for row in observations
            ]
        else:
            result = result.model_copy(update={"source_anchors": []})
        return result, observations, gaps, missing

    monkeypatch.setattr(reads, "get_object_with_reviewed_sources_direct", incorrect)
    result = execute(case)
    assert (
        result["status"] == "published"
        and result["verification"]["status"] == "unavailable"
    )

pytestmark = pytest.mark.usefixtures("application_state_dsn")
