"""Synthetic owning proof for trusted existing-endpoint relation preparation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from dungeonmind.application import publish_finalized_review
from dungeonmind.application.contribution_review_v2 import (
    finalize_contribution_review_v2,
)
from dungeonmind.application.graph_snapshot import (
    GRAPH_SCHEMA_V6,
    VersionedUnionGraphSnapshotReader,
)
from dungeonmind.application.graph_snapshot_v6 import UnionGraphV6Payload
from dungeonmind.application.semantic_profiles import descriptor_sha256
from dungeonmind.contracts import (
    Admissibility,
    CapabilityCategory,
    CapabilityEffect,
    CapabilityPolicy,
    GraphScope,
    ToolCapabilityRule,
)
from dungeonmind.contracts.contribution_review import derive_confirmation_id
from dungeonmind.contracts.contribution_review_v2 import (
    FINALIZE_REVIEW_V2_TOOL,
    CommitConfirmationReceiptV2,
    ContributionReviewSubmissionV2,
)
from dungeonmind.contracts.evidence import (
    SourceArtifact,
    SourceDomain,
    SourceRevision,
    SourceStatus,
)
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.memory import (
    InMemoryContributionRepository,
    InMemoryContributionReviewRepository,
    InMemoryFinalizedReviewPublicationRepository,
    InMemorySourceRepository,
    InMemoryWorldGraphRepository,
)
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_v3_descriptor,
)

from apps.live_control_server.models.reviewed_existing_relation_prepare import (
    PinnedExistingRelationReview,
    ReviewedExistingRelation,
    TrustedGMRelationContext,
)
from apps.live_control_server.services import (
    reviewed_existing_relation_prepare as subject,
)
from graph_memory.source_span import (
    build_source_span_index_for_text,
    source_span_index_to_dict,
)

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
WORLD = "world:test-relations"
CAMPAIGN = "camp:test-relations"
ARTIFACT = "artifact:test-relations"
SOURCE = "The scout knows the gate.\n"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _metadata(assertion_id: str, evidence_id: str) -> dict:
    return {
        "assertion_id": assertion_id,
        "campaign_scope": CAMPAIGN,
        "visibility": "gm",
        "epistemic_kind": "fact",
        "canon_state": "canonical",
        "evidence_ref_ids": [evidence_id],
        "session_refs": [],
        "temporal_scope": {"kind": "unknown", "fictional_time_ref": None},
    }


def _policy(
    parent_id: str, *, admissibility: Admissibility = Admissibility.GM
) -> CapabilityPolicy:
    return CapabilityPolicy(
        policy_id="policy:reviewed-relations",
        graph_scope=GraphScope(
            world_id=WORLD,
            campaign_id=CAMPAIGN,
            admissibility=admissibility,
            revision_pin=parent_id,
        ),
        enabled_tools=[FINALIZE_REVIEW_V2_TOOL, subject.PREPARE_TOOL_NAME],
        tool_rules=[
            ToolCapabilityRule(
                tool_name=FINALIZE_REVIEW_V2_TOOL,
                category=CapabilityCategory.CONFIRM_COMMIT,
                allowed_effects=[CapabilityEffect.COMMIT],
            ),
            ToolCapabilityRule(
                tool_name=subject.PREPARE_TOOL_NAME,
                category=CapabilityCategory.PREVIEW_WRITE,
                allowed_effects=[CapabilityEffect.PREVIEW_WRITE],
            ),
        ],
    )


def _case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    descriptor = load_builtin_v3_descriptor()
    profiles = StaticSemanticProfileRegistry([descriptor])
    profile = {
        "schema_version": "dm_semantic_profile_ref_v1",
        "profile_id": descriptor.profile_id,
        "profile_revision": descriptor.profile_revision,
        "descriptor_sha256": descriptor_sha256(descriptor),
    }
    parent_evidence = "evidence:parent"
    graph_payload = UnionGraphV6Payload.model_validate(
        {
            "world_id": WORLD,
            "semantic_profile": profile,
            "objects": [
                {
                    "object_id": "npc:scout",
                    "kind": "dnd5e:npc",
                    "label": "Scout",
                    "assertion_metadata": _metadata("ka:npc", parent_evidence),
                },
                {
                    "object_id": "loc:gate",
                    "kind": "dnd5e:location",
                    "label": "Gate",
                    "assertion_metadata": _metadata("ka:gate", parent_evidence),
                },
            ],
            "evidence_refs": [
                {
                    "evidence_ref_id": parent_evidence,
                    "source_artifact_id": "artifact:parent",
                    "source_revision_id": None,
                    "source_domain_key": "session_recap",
                    "source_domain": "session_recap",
                    "evidence_role": "support",
                    "can_open_source": True,
                    "can_highlight_span": False,
                    "session_id": None,
                    "source_span_ref_id": None,
                    "locator": None,
                    "uri": None,
                    "source_locator": None,
                    "line_ref": None,
                }
            ],
        }
    ).model_dump(mode="json")
    graph = InMemoryWorldGraphRepository()
    parent = graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["init:test-relations"],
            graph_schema=GRAPH_SCHEMA_V6,
            graph_payload=graph_payload,
            created_at=NOW,
        )
    )
    sources = InMemorySourceRepository()
    source_sha = _sha(SOURCE.encode())
    source_revision_id = f"sha256:{source_sha}"
    sources.put_artifact(
        SourceArtifact(
            source_artifact_id=ARTIFACT,
            source_domain=SourceDomain.SESSION_RECAP,
            world_id=WORLD,
            campaign_id=CAMPAIGN,
            session_id="session-1",
            current_revision_id=source_revision_id,
            status=SourceStatus.ACTIVE,
            created_at=NOW,
        )
    )
    sources.put_revision(
        SourceRevision(
            source_revision_id=source_revision_id,
            source_artifact_id=ARTIFACT,
            content_sha256=source_sha,
            body_storage="postgres",
            created_at=NOW,
        )
    )
    span_index = build_source_span_index_for_text(
        source_artifact_id=ARTIFACT,
        content_sha256=source_sha,
        text=SOURCE,
    )
    span_id = span_index.spans[0].source_span_id
    source_path = tmp_path / "source.md"
    candidate_path = tmp_path / "candidate.json"
    span_path = tmp_path / "spans.json"
    source_path.write_bytes(SOURCE.encode())
    candidate_path.write_bytes(
        json.dumps(
            {
                "campaign_id": CAMPAIGN,
                "edges": [
                    {
                        "edge_id": "edge:candidate",
                        "evidence_refs": [
                            {
                                "source_artifact_id": ARTIFACT,
                                "source_span_ref_id": span_id,
                                "anchor_quotes": ["knows the gate"],
                            }
                        ],
                    }
                ],
            },
            sort_keys=True,
        ).encode()
    )
    span_path.write_bytes(
        json.dumps(source_span_index_to_dict(span_index), sort_keys=True).encode()
    )
    run = SimpleNamespace(
        components={
            "source_artifact": SimpleNamespace(
                sha256="sha256:" + _sha(source_path.read_bytes())
            ),
            "candidate_graph": SimpleNamespace(
                sha256="sha256:" + _sha(candidate_path.read_bytes())
            ),
            "source_span_index": SimpleNamespace(
                sha256="sha256:" + _sha(span_path.read_bytes())
            ),
        }
    )
    resolved = SimpleNamespace(
        run_id="run:reviewed",
        world_id="buddy-world",
        campaign_id=CAMPAIGN,
        source_artifact_id=ARTIFACT,
        source_revision_id=source_revision_id,
        source_domain="recap",
        source_span_index_path=span_path,
        normalized_recap_path=source_path,
        candidate_graph_path=candidate_path,
    )
    monkeypatch.setattr(subject, "_resolve_source_run", lambda *_: (run, resolved))
    monkeypatch.setattr(
        subject,
        "_get_managed_world",
        lambda *_: SimpleNamespace(
            native_graph_binding=SimpleNamespace(
                status="active", native_world_id=WORLD
            ),
        ),
    )
    context = TrustedGMRelationContext(
        buddy_world_id="buddy-world",
        native_world_id=WORLD,
        campaign_id=CAMPAIGN,
        service_principal="service:buddy:reviewed-relations",
        expected_parent_revision_id=parent.revision_id,
        expected_parent_payload_sha256=canonical_sha256(graph_payload),
    )
    relation = ReviewedExistingRelation(
        candidate_edge_id="edge:candidate",
        relationship_id="edge:reviewed:scout-gate",
        subject_object_id="npc:scout",
        subject_kind="dnd5e:npc",
        qualified_predicate="dnd5e:aware_of",
        object_object_id="loc:gate",
        object_kind="dnd5e:location",
        source_span_ids=[span_id],
        semantic_rationale="Steward reviewed the cited sentence.",
    )
    review = PinnedExistingRelationReview(
        buddy_world_id=context.buddy_world_id,
        native_world_id=WORLD,
        campaign_id=CAMPAIGN,
        source_run_id=resolved.run_id,
        source_artifact_id=ARTIFACT,
        source_revision_id=source_revision_id,
        source_body_sha256=source_sha,
        source_span_index_sha256=_sha(span_path.read_bytes()),
        candidate_graph_sha256=_sha(candidate_path.read_bytes()),
        expected_parent_revision_id=parent.revision_id,
        expected_parent_payload_sha256=canonical_sha256(graph_payload),
        semantic_reviewer_kind="agent_steward",
        semantic_reviewer_id="steward:prime",
        reviewed_at=NOW,
        relations=[relation],
        review_sha256="0" * 64,
    )
    review = review.model_copy(update={"review_sha256": subject._record_digest(review)})
    return locals()


def _prepare(case: dict):
    return subject.prepare_reviewed_existing_relations(
        case["context"],
        case["review"],
        repo_root=case["tmp_path"],
        gm_capability_policy=_policy(case["parent"].revision_id),
        world_graph_repository=case["graph"],
        source_repository=case["sources"],
        semantic_profile_registry=case["profiles"],
    )


def _rebind(case: dict, **changes) -> None:
    review = case["review"].model_copy(update=changes)
    case["review"] = review.model_copy(
        update={"review_sha256": subject._record_digest(review)}
    )


def test_prepares_only_reviewed_existing_edges_and_core_publishes_exact_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    intent = _prepare(case)
    assert intent.identity_proposals == intent.identity_verdicts == []
    assert len(intent.candidate_contribution.assertions) == 1
    assert intent.candidate_contribution.assertions[0].assertion_kind == "edge"
    assert intent.reviewer_id == "service:buddy:reviewed-relations"
    assert (
        intent.candidate_contribution.diagnostics["semantic_reviewer_id"]
        == "steward:prime"
    )
    assert case["graph"].get_head(WORLD).head_revision_id == case["parent"].revision_id
    assert _prepare(case) == intent

    reviews = InMemoryContributionReviewRepository(InMemoryContributionRepository())
    publications = InMemoryFinalizedReviewPublicationRepository(reviews, case["graph"])
    confirmation = CommitConfirmationReceiptV2(
        confirmation_id=derive_confirmation_id(
            operation_id=intent.operation_id,
            review_intent_sha256=intent.review_intent_sha256,
            actor=intent.reviewer_id,
            confirmed_at=NOW,
        ),
        operation_id=intent.operation_id,
        review_intent_sha256=intent.review_intent_sha256,
        actor=intent.reviewer_id,
        world_id=WORLD,
        campaign_id=CAMPAIGN,
        expected_parent_revision_id=case["parent"].revision_id,
        confirmed_at=NOW,
    )
    state = finalize_contribution_review_v2(
        ContributionReviewSubmissionV2(intent=intent, confirmation=confirmation),
        capability_policy=_policy(case["parent"].revision_id),
        world_graph_repository=case["graph"],
        review_repository=reviews,
    )
    reader = VersionedUnionGraphSnapshotReader(profile_registry=case["profiles"])
    result = publish_finalized_review(
        WORLD,
        state.record.review_id,
        published_at=NOW,
        review_repository=reviews,
        world_graph_repository=case["graph"],
        publication_repository=publications,
        graph_reader=reader,
    )
    replay = publish_finalized_review(
        WORLD,
        state.record.review_id,
        published_at=NOW,
        review_repository=reviews,
        world_graph_repository=case["graph"],
        publication_repository=publications,
        graph_reader=reader,
    )
    assert replay == result
    published = case["graph"].get_revision(WORLD, result.published_revision_id)
    assert published is not None
    assert [item["object_id"] for item in published.graph_payload["objects"]] == [
        "npc:scout",
        "loc:gate",
    ]
    assert [
        item["relationship_id"] for item in published.graph_payload["relationships"]
    ] == ["edge:reviewed:scout-gate"]


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("foreign_endpoint", "endpoint_missing"),
        ("wrong_kind", "endpoint_kind_drift"),
        ("wrong_predicate", "predicate_kind_invalid"),
        ("missing_span", "candidate_evidence_drift"),
        ("parent_digest", "context_mismatch"),
        ("candidate_digest", "source_digest_drift"),
        ("source_digest", "source_not_admitted"),
        ("source_body_changed", "source_digest_drift"),
        ("span_index_changed", "source_digest_drift"),
        ("stale_parent", "parent_drift"),
        ("unsupported_predicate", "predicate_kind_invalid"),
        ("foreign_predicate_namespace", "predicate_invalid"),
        ("missing_candidate_edge", "candidate_edge_missing"),
        ("relationship_collision", "relationship_collision"),
        ("evidence_collision", "evidence_collision"),
        ("foreign_source", "source_not_admitted"),
        ("foreign_source_world", "source_not_admitted"),
        ("source_revision_moved", "source_not_admitted"),
        ("source_domain_changed", "source_domain_mismatch"),
        ("source_quote_changed", "source_quote_drift"),
    ],
)
def test_rejects_drift_and_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
    code: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    relation = case["review"].relations[0]
    if change == "foreign_endpoint":
        _rebind(
            case,
            relations=[
                relation.model_copy(update={"subject_object_id": "npc:foreign"})
            ],
        )
    elif change == "wrong_kind":
        _rebind(
            case,
            relations=[relation.model_copy(update={"subject_kind": "dnd5e:location"})],
        )
    elif change == "wrong_predicate":
        _rebind(
            case,
            relations=[
                relation.model_copy(update={"qualified_predicate": "dnd5e:contains"})
            ],
        )
    elif change == "missing_span":
        _rebind(
            case,
            relations=[
                relation.model_copy(update={"source_span_ids": ["span:missing"]})
            ],
        )
    elif change == "parent_digest":
        _rebind(case, expected_parent_payload_sha256="f" * 64)
    elif change == "candidate_digest":
        _rebind(case, candidate_graph_sha256="f" * 64)
    elif change == "source_digest":
        _rebind(case, source_body_sha256="f" * 64)
    elif change == "source_body_changed":
        case["source_path"].write_text("A different body.\n")
    elif change == "span_index_changed":
        case["span_path"].write_text("{}")
    elif change == "stale_parent":
        case["graph"].publish_revision(
            PublishRevisionCommand(
                world_id=WORLD,
                parent_revision_id=case["parent"].revision_id,
                expected_parent_revision_id=case["parent"].revision_id,
                operation_ids=["other:head"],
                graph_schema=GRAPH_SCHEMA_V6,
                graph_payload=case["graph_payload"],
                created_at=NOW,
            )
        )
    elif change == "unsupported_predicate":
        _rebind(
            case,
            relations=[
                relation.model_copy(update={"qualified_predicate": "dnd5e:invented"})
            ],
        )
    elif change == "foreign_predicate_namespace":
        _rebind(
            case,
            relations=[
                relation.model_copy(update={"qualified_predicate": "foreign:aware_of"})
            ],
        )
    elif change == "missing_candidate_edge":
        _rebind(
            case,
            relations=[
                relation.model_copy(update={"candidate_edge_id": "edge:missing"})
            ],
        )
    elif change == "relationship_collision":
        # A matching parent relationship is a collision even with another ID.
        collision_payload = UnionGraphV6Payload.model_validate(
            {
                **case["graph_payload"],
                "relationships": [
                    {
                        "relationship_id": "edge:existing",
                        "source_object_id": "npc:scout",
                        "target_object_id": "loc:gate",
                        "predicate": "dnd5e:aware_of",
                        "assertion_metadata": _metadata("ka:edge", "evidence:parent"),
                    }
                ],
            }
        ).model_dump(mode="json")
        case["graph"].publish_revision(
            PublishRevisionCommand(
                world_id=WORLD,
                parent_revision_id=case["parent"].revision_id,
                expected_parent_revision_id=case["parent"].revision_id,
                operation_ids=["other:relation"],
                graph_schema=GRAPH_SCHEMA_V6,
                graph_payload=collision_payload,
                created_at=NOW,
            )
        )
        # Pin the new parent so the collision gate, not stale-head gate, is exercised.
        new_parent = case["graph"].get_head(WORLD).head_revision_id
        new_payload = case["graph"].get_revision(WORLD, new_parent).graph_payload
        case["context"] = case["context"].model_copy(
            update={
                "expected_parent_revision_id": new_parent,
                "expected_parent_payload_sha256": canonical_sha256(new_payload),
            }
        )
        _rebind(
            case,
            expected_parent_revision_id=new_parent,
            expected_parent_payload_sha256=canonical_sha256(new_payload),
        )
        case["parent"] = SimpleNamespace(revision_id=new_parent)
    elif change == "evidence_collision":
        evidence_id = "evidence:reviewed:" + "c" * 64
        case["graph_payload"]["evidence_refs"].append(
            {
                **case["graph_payload"]["evidence_refs"][0],
                "evidence_ref_id": evidence_id,
            }
        )
        # Rebuild the fixture parent and pins to make the collision authoritative.
        graph = InMemoryWorldGraphRepository()
        parent = graph.publish_revision(
            PublishRevisionCommand(
                world_id=WORLD,
                parent_revision_id=None,
                expected_parent_revision_id=None,
                operation_ids=["init:collision"],
                graph_schema=GRAPH_SCHEMA_V6,
                graph_payload=case["graph_payload"],
                created_at=NOW,
            )
        )
        case["graph"] = graph
        case["parent"] = parent
        case["context"] = case["context"].model_copy(
            update={
                "expected_parent_revision_id": parent.revision_id,
                "expected_parent_payload_sha256": canonical_sha256(
                    case["graph_payload"]
                ),
            }
        )
        _rebind(
            case,
            expected_parent_revision_id=parent.revision_id,
            expected_parent_payload_sha256=canonical_sha256(case["graph_payload"]),
        )
        original_sha = subject._sha
        monkeypatch.setattr(
            subject,
            "_sha",
            lambda data: (
                "c" * 64
                if (
                    b"edge:reviewed:scout-gate" in data
                    and case["review"].review_sha256.encode() in data
                )
                else original_sha(data)
            ),
        )
    elif change == "foreign_source":
        case["sources"] = InMemorySourceRepository()
    elif change in {"foreign_source_world", "source_revision_moved"}:
        artifact = case["sources"].get_artifact(ARTIFACT)
        assert artifact is not None
        replacement = artifact.model_copy(
            update={
                "world_id": "world:foreign"
                if change == "foreign_source_world"
                else WORLD,
                "current_revision_id": "sha256:other"
                if change == "source_revision_moved"
                else artifact.current_revision_id,
            }
        )
        sources = InMemorySourceRepository()
        sources.put_artifact(replacement)
        sources.put_revision(
            case["sources"].get_revision(case["review"].source_revision_id)
        )
        case["sources"] = sources
    elif change == "source_domain_changed":
        case["resolved"].source_domain = "worldbuilding"
    elif change == "source_quote_changed":
        candidate = json.loads(case["candidate_path"].read_text())
        candidate["edges"][0]["evidence_refs"][0]["anchor_quotes"] = [
            "the gate was destroyed"
        ]
        case["candidate_path"].write_text(json.dumps(candidate, sort_keys=True))
        candidate_sha = _sha(case["candidate_path"].read_bytes())
        case["run"].components["candidate_graph"].sha256 = "sha256:" + candidate_sha
        _rebind(case, candidate_graph_sha256=candidate_sha)
    with pytest.raises(subject.ReviewedExistingRelationPrepareError) as caught:
        _prepare(case)
    assert caught.value.code == code


def test_requires_pinned_gm_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    with pytest.raises(subject.ReviewedExistingRelationPrepareError) as caught:
        subject.prepare_reviewed_existing_relations(
            case["context"],
            case["review"],
            repo_root=tmp_path,
            gm_capability_policy=_policy(
                case["parent"].revision_id, admissibility=Admissibility.PLAYER
            ),
            world_graph_repository=case["graph"],
            source_repository=case["sources"],
            semantic_profile_registry=case["profiles"],
        )
    assert caught.value.code == "gm_scope_required"


def test_requires_explicit_prepare_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    policy = CapabilityPolicy(
        policy_id="policy:read-only",
        graph_scope=GraphScope(
            world_id=WORLD,
            campaign_id=CAMPAIGN,
            admissibility=Admissibility.GM,
            revision_pin=case["parent"].revision_id,
        ),
        enabled_tools=[],
        tool_rules=[],
    )
    with pytest.raises(subject.ReviewedExistingRelationPrepareError) as caught:
        subject.prepare_reviewed_existing_relations(
            case["context"],
            case["review"],
            repo_root=tmp_path,
            gm_capability_policy=policy,
            world_graph_repository=case["graph"],
            source_repository=case["sources"],
            semantic_profile_registry=case["profiles"],
        )
    assert caught.value.code == "prepare_capability_denied"
