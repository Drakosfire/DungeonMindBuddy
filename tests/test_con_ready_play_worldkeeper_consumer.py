"""PLAY-1 proof of Buddy mapping into the real in-memory WorldKeeper lifecycle."""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dungeonmind.application.vnext import InMemoryKnowledgeSourceReader
from dungeonmind.application.vnext.materialization import (
    NATIVE_VNEXT_GRAPH_SCHEMA,
    encode_native_graph_payload,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext import (
    DomainContractRef,
    Entity,
    EvidenceRefV3,
    SourceArtifactV3,
    SourceRevisionV2,
)
from dungeonmind.contracts.vnext.common import LabelsAnyVisibility
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.memory.vnext_knowledge import (
    InMemoryKnowledgeRevisionRepository,
)
from worldkeeper.application import (
    CreateObject,
    CreateRelationship,
    DurableObjectRef,
    InvalidWorldChange,
    ResultOf,
)
from worldkeeper.application.commit import PreparedChangeStale
from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime

from apps.live_control_server.integrations.worldkeeper import (
    PlayAuthoringContext,
    PlayAuthoringMappingError,
    WorldKeeperGraphAuthoringConsumer,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringProposalPayload,
)
from graph_memory.vnext import (
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_dnd5e_semantic_profile,
    dungeonbuddy_world_domain_contract,
)

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
SPACE_ID = "space:play-witness"
CAMPAIGN_ID = "campaign:play-witness"
EVIDENCE_ID = "ev:play-session-note"


def _proposal(**fields: object) -> GraphObjectAuthoringProposalPayload:
    return GraphObjectAuthoringProposalPayload.model_validate(
        {
            "localProposalId": fields.pop("localProposalId"),
            "proposalKind": fields.pop("proposalKind"),
            "status": "staged_local",
            "visibility": {"visibility": "gm_private", "revealState": "unrevealed"},
            "provenancePreview": {"origin": "human_authored"},
            **fields,
        }
    )


def _brewery(**fields: object) -> GraphObjectAuthoringProposalPayload:
    return _proposal(
        localProposalId="brewery",
        proposalKind="object",
        objectRef={
            "label": "The Wizard's Tower Brewing Co",
            "kind": "location",
            "summary": "A brewery by the tower",
        },
        **fields,
    )


def _relationship(
    term: str = "works_at", **fields: object
) -> GraphObjectAuthoringProposalPayload:
    return _proposal(
        localProposalId="rel-pippa-brewery",
        proposalKind="relationship",
        sourceObjectRef={
            "refKind": "existing_graph_node",
            "nodeId": "ent:pippa",
            "label": "Pippa",
        },
        targetObjectRef={
            "refKind": "local_proposal",
            "localProposalId": "brewery",
            "label": "The Wizard's Tower Brewing Co",
        },
        relationshipType=term,
        direction="directed",
        **fields,
    )


def _context(**fields: object) -> PlayAuthoringContext:
    return PlayAuthoringContext(
        space_id=fields.get("space_id", SPACE_ID),  # type: ignore[arg-type]
        campaign_id=fields.get("campaign_id", CAMPAIGN_ID),  # type: ignore[arg-type]
        evidence_ref_ids=fields.get("evidence_ref_ids", (EVIDENCE_ID,)),  # type: ignore[arg-type]
    )


def _repository(
    *, v3: bool = True, evidence: bool = True
) -> InMemoryKnowledgeRevisionRepository:
    repo = InMemoryKnowledgeRevisionRepository()
    domain = dungeonbuddy_world_domain_contract()
    profile = (
        dungeonbuddy_dnd5e_custom_predicate_profile()
        if v3
        else dungeonbuddy_dnd5e_semantic_profile()
    )
    payload = encode_native_graph_payload(
        entities={"ent:pippa": Entity(entity_id="ent:pippa")},
        assertions={},
        aliases={},
        evidence=(
            {
                EVIDENCE_ID: EvidenceRefV3(
                    evidence_ref_id=EVIDENCE_ID,
                    source_artifact_id="art:play-session-note",
                    source_revision_id="srcrev:play-session-note",
                    evidence_role="support",
                    can_open_source=True,
                    can_highlight_span=False,
                    locator="session-note",
                )
            }
            if evidence
            else {}
        ),
    )
    repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=SPACE_ID,
            operation_ids=["op:play-genesis"],
            graph_schema=NATIVE_VNEXT_GRAPH_SCHEMA,
            graph_payload=payload,
            domain_contract_ref=DomainContractRef(
                domain_id=domain.domain_id,
                domain_revision=domain.domain_revision,
                descriptor_sha256=canonical_sha256(domain.model_dump(mode="json")),
            ),
            semantic_profile_ref=SemanticProfileRef(
                profile_id=profile.profile_id,
                profile_revision=profile.profile_revision,
                descriptor_sha256=canonical_sha256(profile.model_dump(mode="json")),
            ),
            created_at=NOW,
        )
    )
    return repo


def _consumer(
    repo: InMemoryKnowledgeRevisionRepository, *, prepared_id: str = "prepared:play-1"
) -> WorldKeeperGraphAuthoringConsumer:
    return WorldKeeperGraphAuthoringConsumer(
        DungeonMindWorldKeeperRuntime(
            repository=repo,
            domain_contract=dungeonbuddy_world_domain_contract(),
            semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
            clock=lambda: NOW,
            prepared_id_factory=lambda: prepared_id,
        )
    )


def test_works_at_witness_prepares_without_mutation_commits_once_and_retries() -> None:
    repo = _repository()
    consumer = _consumer(repo)
    proposals = (_relationship(), _brewery())  # dependency appears first on purpose
    intent = consumer.build_intent(context=_context(), proposals=proposals)
    assert intent.space_id == SPACE_ID
    assert intent.producer == "dungeonbuddy:con-ready-play"
    relationship = intent.operations[0]
    brewery = intent.operations[1]
    assert isinstance(relationship, CreateRelationship)
    assert isinstance(brewery, CreateObject)
    assert relationship.source == DurableObjectRef("ent:pippa")
    assert relationship.target == ResultOf("brewery")
    assert relationship.predicate == "dungeonbuddy.custom:works_at"
    assert relationship.metadata.scope[0].axis == "dungeonbuddy.scope:campaign"
    assert relationship.metadata.scope[0].value == CAMPAIGN_ID
    assert relationship.metadata.visibility.labels == ("dungeonbuddy.visibility:gm",)
    assert relationship.metadata.evidence_ref_ids == (EVIDENCE_ID,)
    assert relationship.metadata.claim_mode == "dungeonbuddy.claim:fact"
    assert [(fact.client_op_id, fact.predicate) for fact in brewery.facts] == [
        ("brewery.fact.name", "dnd5e:name"),
        ("brewery.fact.classification", "dnd5e:classification"),
        ("brewery.fact.summary", "dnd5e:summary"),
    ]
    assert all(
        not item.client_op_id.startswith(("ent:", "asrt:"))
        for item in (relationship, brewery, *brewery.facts)
    )
    before = repo.get_head(SPACE_ID)
    events_before = repo.head_events(SPACE_ID)
    prepared = consumer.prepare(context=_context(), proposals=proposals)
    assert prepared.semantic_profile_ref.revision == "2"
    assert [item.client_op_id for item in prepared.prospective_handles] == ["brewery"]
    assert prepared.prepared_operations[0].predicate == "dungeonbuddy.custom:works_at"
    assert repo.get_head(SPACE_ID) == before
    assert repo.head_events(SPACE_ID) == events_before

    committed = consumer.commit(prepared, confirmed_by="user:gm")
    events_after = repo.head_events(SPACE_ID)
    replayed = consumer.commit(prepared, confirmed_by="user:gm")
    assert committed == replayed
    assert repo.head_events(SPACE_ID) == events_after
    assert len(events_after) == len(events_before) + 1
    assert committed.verification.exact_child_read_back
    entity_id = next(
        item.durable_object_id
        for item in committed.object_results
        if item.client_op_id == "brewery"
    )
    assertion_id = next(
        item.durable_assertion_id
        for item in committed.assertion_results
        if item.client_op_id == "rel-pippa-brewery"
    )
    assert entity_id.startswith("ent:")
    assert assertion_id.startswith("asrt:")
    child = repo.get_revision(SPACE_ID, committed.child_revision_id)
    assert child is not None
    assertion = next(
        item
        for item in child.graph_payload["assertions"]
        if item["assertion_id"] == assertion_id
    )
    assert assertion["predicate"] == "dungeonbuddy.custom:works_at"
    assert assertion["subject_entity_id"] == "ent:pippa"
    assert assertion["value"] == {"kind": "entity_ref", "entity_id": entity_id}


def test_evidence_fixture_names_one_coherent_source_revision() -> None:
    reader = InMemoryKnowledgeSourceReader(
        artifacts={
            "art:play-session-note": SourceArtifactV3(
                source_artifact_id="art:play-session-note",
                source_classification="dungeonbuddy:source_classification",
                current_revision_id="srcrev:play-session-note",
                authority="primary",
                visibility=LabelsAnyVisibility(labels=["dungeonbuddy.visibility:gm"]),
                status="active",
            )
        },
        revisions={
            "srcrev:play-session-note": SourceRevisionV2(
                source_revision_id="srcrev:play-session-note",
                source_artifact_id="art:play-session-note",
                content_sha256="a" * 64,
                body_storage="memory:play-session-note",
                created_at=NOW,
            )
        },
    )
    snapshot = reader.get_provenance_snapshot(
        artifact_ids=["art:play-session-note"],
        revision_ids=["srcrev:play-session-note"],
    )
    assert not snapshot.missing_artifact_ids
    assert not snapshot.missing_revision_ids
    assert snapshot.artifacts_by_id["art:play-session-note"].current_revision_id == (
        "srcrev:play-session-note"
    )


def test_operation_order_and_fixed_predicate_preserve_exact_mapping() -> None:
    consumer = _consumer(_repository())
    ordered = consumer.build_intent(
        context=_context(), proposals=(_brewery(), _relationship())
    )
    reversed_intent = consumer.build_intent(
        context=_context(), proposals=(_relationship(), _brewery())
    )
    assert {item.client_op_id: item for item in ordered.operations} == {
        item.client_op_id: item for item in reversed_intent.operations
    }
    fixed = consumer.build_intent(
        context=_context(), proposals=(_brewery(), _relationship("dnd5e:located_in"))
    )
    assert isinstance(fixed.operations[1], CreateRelationship)
    assert fixed.operations[1].predicate == "dnd5e:located_in"


def test_consumer_uses_only_injected_service_for_prepare_and_commit() -> None:
    repo = _repository()
    runtime = DungeonMindWorldKeeperRuntime(
        repository=repo,
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
        clock=lambda: NOW,
        prepared_id_factory=lambda: "prepared:injected",
    )

    class RecordingService:
        def __init__(self) -> None:
            self.intent = None
            self.prepared = None

        def prepare_change(self, intent):
            self.intent = intent
            return runtime.prepare_change(intent)

        def commit_prepared_change(self, prepared, confirmed_by):
            self.prepared = prepared
            return runtime.commit_prepared_change(prepared, confirmed_by)

    service = RecordingService()
    consumer = WorldKeeperGraphAuthoringConsumer(service)
    prepared = consumer.prepare(
        context=_context(), proposals=(_brewery(), _relationship())
    )
    committed = consumer.commit(prepared, confirmed_by="user:gm")
    assert service.intent is not None
    assert service.intent.operations[1].predicate == "dungeonbuddy.custom:works_at"
    assert service.prepared is prepared
    assert committed.prepared_change_id == "prepared:injected"


@pytest.mark.parametrize("term", ["mentors", "trained_by"])
def test_new_custom_terms_use_the_same_open_namespace_branch(term: str) -> None:
    repo = _repository()
    consumer = _consumer(repo, prepared_id=f"prepared:{term}")
    intent = consumer.build_intent(
        context=_context(), proposals=(_brewery(), _relationship(term))
    )
    assert isinstance(intent.operations[1], CreateRelationship)
    assert intent.operations[1].predicate == f"dungeonbuddy.custom:{term}"
    prepared = consumer.prepare(
        context=_context(), proposals=(_brewery(), _relationship(term))
    )
    committed = consumer.commit(prepared, confirmed_by="user:gm")
    child = repo.get_revision(SPACE_ID, committed.child_revision_id)
    assert child is not None
    assert any(
        item["predicate"] == f"dungeonbuddy.custom:{term}"
        for item in child.graph_payload["assertions"]
    )


def test_v2_pinned_parent_rejects_custom_profile_without_transition() -> None:
    repo = _repository(v3=False)
    consumer = _consumer(repo)
    before = repo.get_head(SPACE_ID)
    with pytest.raises(InvalidWorldChange, match="semantic_profile_mismatch"):
        consumer.prepare(context=_context(), proposals=(_brewery(), _relationship()))
    assert repo.get_head(SPACE_ID) == before
    assert len(repo.head_events(SPACE_ID)) == 1


def test_missing_evidence_fails_in_worldkeeper_prepare_without_publication() -> None:
    repo = _repository(evidence=False)
    consumer = _consumer(repo)
    before = repo.get_head(SPACE_ID)
    with pytest.raises(InvalidWorldChange, match="evidence_ref_absent"):
        consumer.prepare(context=_context(), proposals=(_brewery(), _relationship()))
    assert repo.get_head(SPACE_ID) == before


def test_stale_prepared_value_fails_without_repair_publication() -> None:
    repo = _repository()
    stale = _consumer(repo, prepared_id="prepared:stale").prepare(
        context=_context(), proposals=(_brewery(), _relationship())
    )
    fresh = _consumer(repo, prepared_id="prepared:fresh").prepare(
        context=_context(), proposals=(_brewery(), _relationship())
    )
    _consumer(repo).commit(fresh, confirmed_by="user:gm")
    events = repo.head_events(SPACE_ID)
    with pytest.raises(PreparedChangeStale):
        _consumer(repo).commit(stale, confirmed_by="user:gm")
    assert repo.head_events(SPACE_ID) == events


@pytest.mark.parametrize(
    ("proposals", "code"),
    [
        (("brewery", "brewery"), "duplicate_local_proposal_id"),
        (("brewery", "missing-local"), "unresolved_local_endpoint"),
        (("brewery", "relationship-local"), "unresolved_local_endpoint"),
        (("brewery", "manual-ref"), "unsupported_endpoint_kind"),
        (("brewery", "blank-existing"), "blank_durable_object_id"),
        (("brewery", "undirected"), "unsupported_relationship_direction"),
        (("brewery", "invalid-term"), "invalid_relationship_type"),
        (("brewery", "unknown-kind"), "unknown_object_kind"),
        (("brewery", "aliases"), "unsupported_alias_or_role"),
        (("brewery", "role"), "unsupported_alias_or_role"),
        (("brewery", "update"), "unsupported_relationship_operation"),
        (("brewery", "object-update"), "unsupported_object_operation"),
        (("brewery", "authored-node"), "invalid_target_endpoint"),
        (("brewery", "detail"), "unsupported_relationship_detail"),
        (("brewery", "scope"), "unsupported_graph_scope"),
        (("brewery", "link-existing"), "unsupported_proposal_kind"),
        (("brewery", "merge"), "unsupported_proposal_kind"),
    ],
)
def test_unsupported_proposal_meaning_fails_closed(
    proposals: tuple[str, str], code: str
) -> None:
    brewery = _brewery()
    relationship = _relationship()
    variant = proposals[1]
    if variant == "brewery":
        supplied = (brewery, brewery)
    elif variant == "missing-local":
        ref = dict(relationship.target_object_ref or {}, localProposalId="other")
        supplied = (brewery, relationship.model_copy(update={"target_object_ref": ref}))
    elif variant == "relationship-local":
        ref = dict(
            relationship.target_object_ref or {}, localProposalId="rel-pippa-brewery"
        )
        supplied = (brewery, relationship.model_copy(update={"target_object_ref": ref}))
    elif variant == "manual-ref":
        ref = {"refKind": "manual_ref", "label": "Unknown"}
        supplied = (brewery, relationship.model_copy(update={"target_object_ref": ref}))
    elif variant == "blank-existing":
        ref = dict(relationship.source_object_ref or {}, nodeId="")
        supplied = (brewery, relationship.model_copy(update={"source_object_ref": ref}))
    elif variant == "undirected":
        supplied = (
            brewery,
            relationship.model_copy(update={"direction": "undirected"}),
        )
    elif variant == "invalid-term":
        supplied = (
            brewery,
            relationship.model_copy(update={"relationship_type": "Works At"}),
        )
    elif variant == "unknown-kind":
        supplied = (
            brewery.model_copy(update={"object_ref": {"label": "A", "kind": "dragon"}}),
            relationship,
        )
    elif variant == "aliases":
        supplied = (
            brewery.model_copy(update={"object_ref": {"label": "A", "aliases": ["B"]}}),
            relationship,
        )
    elif variant == "role":
        supplied = (
            brewery.model_copy(
                update={"object_ref": {"label": "A", "role": "shopkeeper"}}
            ),
            relationship,
        )
    elif variant == "update":
        supplied = (brewery, relationship.model_copy(update={"operation": "update"}))
    elif variant == "object-update":
        supplied = (brewery.model_copy(update={"operation": "update"}), relationship)
    elif variant == "authored-node":
        ref = {"refKind": "authored_node", "nodeId": "authored:pippa", "label": "Pippa"}
        supplied = (brewery, relationship.model_copy(update={"target_object_ref": ref}))
    elif variant == "detail":
        supplied = (
            brewery,
            relationship.model_copy(update={"relationship_label": "brewery job"}),
        )
    elif variant == "scope":
        supplied = (
            brewery.model_copy(update={"graph_scopes": ["recap_graph", "recap_graph"]}),
            relationship,
        )
    elif variant == "link-existing":
        supplied = (
            brewery,
            relationship.model_copy(update={"proposal_kind": "link_existing"}),
        )
    else:
        supplied = (
            brewery,
            relationship.model_copy(update={"proposal_kind": "merge_objects"}),
        )
    with pytest.raises(PlayAuthoringMappingError) as error:
        _consumer(_repository()).build_intent(context=_context(), proposals=supplied)
    assert error.value.code == code


def test_invalid_context_evidence_is_rejected_before_service_call() -> None:
    repo = _repository()
    before = repo.get_head(SPACE_ID)
    with pytest.raises(PlayAuthoringMappingError, match="invalid_evidence_ref_ids"):
        _consumer(repo).prepare(
            context=_context(evidence_ref_ids=("",)),
            proposals=(_brewery(), _relationship()),
        )
    assert repo.get_head(SPACE_ID) == before


def test_client_operation_id_collision_fails_before_prepare() -> None:
    conflicting = _proposal(
        localProposalId="brewery.fact.name",
        proposalKind="object",
        objectRef={"label": "Collision", "kind": "location"},
    )
    with pytest.raises(PlayAuthoringMappingError, match="duplicate_client_op_id"):
        _consumer(_repository()).build_intent(
            context=_context(), proposals=(_brewery(), conflicting)
        )


def test_consumer_source_has_no_dungeonmind_write_or_legacy_writer_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "apps/live_control_server/integrations/worldkeeper/graph_authoring_consumer.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_modules = (
        "dungeonmind.application",
        "dungeonmind.infrastructure",
        "world_graph_writes",
        "contribution_mapping",
        "assertion_qualification",
    )
    forbidden_calls = {
        "publish_prospective_contribution",
        "publish_prospective_publication",
        "allocate_prospective_result_id",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not node.module or not any(
                term in node.module for term in forbidden_modules
            )
        if isinstance(node, ast.Import):
            assert not any(
                term in alias.name for alias in node.names for term in forbidden_modules
            )
        if isinstance(node, ast.Call):
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else (node.func.id if isinstance(node.func, ast.Name) else "")
            )
            assert name not in forbidden_calls
    for production_path in (
        "apps/live_control_server/routes/graph_authoring.py",
        "apps/live_control_server/services/graph_object_authoring_prepare.py",
        "apps/live_control_server/services/graph_object_authoring_commit.py",
    ):
        source = (Path(__file__).resolve().parents[1] / production_path).read_text(
            encoding="utf-8"
        )
        assert "integrations.worldkeeper" not in source
