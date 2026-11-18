"""V6.2 proof for the dormant native-vNext complete-object adapter."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import apps.live_control_server.integrations.dungeonmind.vnext_complete_object as adapter

from dungeonmind.application.vnext import (
    InMemoryKnowledgeSourceReader,
    ParsedAssertion,
    ParsedAssertionMetadata,
    ParsedLiteralValue,
    ParsedPublicVisibility,
    ParsedTimelessTemporalScope,
    build_parsed_knowledge_revision,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext import (
    Assertion,
    DomainContractRef,
    Entity,
    EvidenceRefV3,
    IdentityAlias,
    KnowledgeRevision,
    SourceArtifactV3,
    SourceRevisionV2,
)

from apps.live_control_server.integrations.dungeonmind.vnext_complete_object import (
    DungeonBuddyVNextReadIdentity,
    VNextCompleteObjectProjectionError,
    _assertion_value,
    project_complete_world_object_vnext,
)
from apps.live_control_server.models.world_graph_object_projection import (
    WorldGraphObjectProjectionRequest,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json"
REVISION_ID = "rev:v6-2-witness"
NODE_ID = "entity:npc:brennan-tallow"


@pytest.fixture
def preservation() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _runtime(data: dict):
    revision = KnowledgeRevision(
        space_id=data["space_id"],
        revision_id=REVISION_ID,
        created_at=datetime(2026, 9, 25, tzinfo=UTC),
        operation_ids=["op:v6-2-witness"],
        graph_schema="dungeonbuddy.test:v6_2",
        graph_payload_sha256="2" * 64,
        domain_contract_ref=DomainContractRef.model_validate(
            data["domain_contract_ref"]
        ),
        semantic_profile_ref=SemanticProfileRef.model_validate(
            data["semantic_profile_ref"]
        ),
    )
    parsed = build_parsed_knowledge_revision(
        revision,
        entities=[Entity.model_validate(item) for item in data["entities"]],
        assertions=[Assertion.model_validate(item) for item in data["assertions"]],
        aliases=[IdentityAlias.model_validate(item) for item in data["aliases"]],
        evidence=[EvidenceRefV3.model_validate(item) for item in data["evidence"]],
    )
    reader = InMemoryKnowledgeSourceReader(
        artifacts={
            item["source_artifact_id"]: SourceArtifactV3.model_validate(item)
            for item in data["sources"]
        },
        revisions={
            item["source_revision_id"]: SourceRevisionV2.model_validate(item)
            for item in data["source_revisions"]
        },
    )
    return parsed, reader


def _request(
    *,
    role: str = "gm",
    node_id: str = NODE_ID,
    focus_session: str = "session-28",
    revision_id: str | None = REVISION_ID,
) -> WorldGraphObjectProjectionRequest:
    return WorldGraphObjectProjectionRequest.model_validate(
        {
            "schema": "dmb_world_graph_object_projection_request_v1",
            "worldId": "eldyrwild",
            "campaignId": "campaign-longmont",
            "nodeId": node_id,
            "focus": {
                "kind": "session",
                "campaignId": "campaign-longmont",
                "sessionId": focus_session,
            },
            "admissibility": role,
            "revisionPin": revision_id,
        }
    )


def _project(data: dict, request: WorldGraphObjectProjectionRequest):
    parsed, reader = _runtime(data)
    return project_complete_world_object_vnext(
        parsed_revision=parsed,
        source_reader=reader,
        request=request,
        read_identity=DungeonBuddyVNextReadIdentity(
            space_id="eldyrwild",
            revision_id=REVISION_ID,
            head_revision_id=REVISION_ID,
            is_head=True,
        ),
    )


def _add_nonfocus_evidence(data: dict) -> str:
    source = copy.deepcopy(data["sources"][0])
    source["source_artifact_id"] = "src:session-99-recap"
    source["domain_metadata"][0]["payload"]["session_id"] = "session-99"
    data["sources"].append(source)

    revision = copy.deepcopy(data["source_revisions"][0])
    revision["source_revision_id"] = "sr:session-99-recap-rev1"
    revision["source_artifact_id"] = source["source_artifact_id"]
    revision["content_sha256"] = "9" * 64
    data["source_revisions"].append(revision)

    evidence = copy.deepcopy(data["evidence"][0])
    evidence["evidence_ref_id"] = "ev:session-99-recap"
    evidence["source_artifact_id"] = source["source_artifact_id"]
    evidence["source_revision_id"] = revision["source_revision_id"]
    data["evidence"].append(evidence)
    return evidence["evidence_ref_id"]


def test_canonical_gm_projection_preserves_complete_object_semantics(
    preservation: dict,
) -> None:
    result = _project(preservation, _request())

    assert result.found is True
    assert result.node is not None
    assert result.node.label == "Brennan Tallow"
    assert result.node.kind == "npc"
    assert result.node.aliases == ["Old Tallow"]
    assert result.node.summary == "Secretly smuggles Mireward night-root to the docks"
    assert result.node.anchored_to_focus_session is True
    assert [item.node_id for item in result.related_nodes] == ["entity:loc:mireward"]
    assert result.related_nodes[0].kind == "location"
    assert result.relationships[0].predicate == "located_in"
    assert result.relationships[0].direction == "outgoing"
    assert result.relationships[0].epistemic_kind == "observed_event"
    assert result.relationships[0].campaign_scope == "campaign-longmont"
    assert result.relationships[0].temporal_scope == {
        "kind": "domain_ref",
        "schema": "dungeonbuddy.time:fictional_anchor_v1",
        "payload": {"campaign_id": "campaign-longmont", "session_number": 28},
    }
    assert {item.assertion_id for item in result.assertions} == {
        "as:brennan-classification",
        "as:brennan-name",
        "as:brennan-secret-plan",
    }
    assert (
        result.source_bindings[0].content_sha256
        == preservation["source_revisions"][0]["content_sha256"]
    )
    assert result.source_bindings[0].source_domain == "recap"
    assert result.source_bindings[0].session_id == "session-28"
    assert result.snapshot is not None
    assert result.snapshot.revision_id == REVISION_ID
    assert result.snapshot.head_revision_id == REVISION_ID
    assert result.snapshot.is_head is True
    assert result.semantic_fingerprint


def test_player_projection_excludes_gm_and_retracted_truth(preservation: dict) -> None:
    result = _project(preservation, _request(role="player"))

    assert result.node is not None
    assert result.node.summary is None
    assert "as:brennan-secret-plan" not in {
        item.assertion_id for item in result.assertions
    }
    assert "as:brennan-retracted-rumor" not in {
        item.assertion_id for item in result.assertions
    }
    assert result.node.aliases == ["Old Tallow"]


def test_focus_only_changes_presentation_not_truth_or_fingerprint(
    preservation: dict,
) -> None:
    focused = _project(preservation, _request(focus_session="session-28"))
    unfocused = _project(preservation, _request(focus_session="session-99"))

    assert focused.semantic_fingerprint == unfocused.semantic_fingerprint
    assert focused.node is not None and unfocused.node is not None
    assert focused.node.anchored_to_focus_session is True
    assert unfocused.node.anchored_to_focus_session is False
    assert focused.node.label == unfocused.node.label
    assert focused.node.kind == unfocused.node.kind
    assert focused.node.aliases == unfocused.node.aliases
    assert focused.node.summary == unfocused.node.summary
    assert focused.node.evidence_ref_ids == unfocused.node.evidence_ref_ids


def test_selected_node_anchor_includes_relationship_evidence(
    preservation: dict,
) -> None:
    nonfocus_id = _add_nonfocus_evidence(preservation)
    for assertion in preservation["assertions"]:
        if assertion["assertion_id"] != "as:brennan-located-in-mireward":
            assertion["metadata"]["evidence_ref_ids"] = [nonfocus_id]
    preservation["aliases"][0]["evidence_ref_ids"] = [nonfocus_id]

    result = _project(preservation, _request())

    assert result.node is not None
    assert not any(
        badge.is_focus_session_evidence for badge in result.node.evidence_badges
    )
    assert result.node.adjacency[0].anchored_to_focus_session is True
    assert result.node.anchored_to_focus_session is True
    related = result.related_nodes[0]
    assert related.evidence_ref_ids == [nonfocus_id]
    assert [badge.evidence_ref_id for badge in related.evidence_badges] == [nonfocus_id]
    assert related.adjacency[0].evidence_ref_ids == ["ev:session-28-mireward-arrival"]
    assert related.anchored_to_focus_session is True


def test_related_back_adjacency_uses_only_its_relationship_evidence(
    preservation: dict,
) -> None:
    nonfocus_id = _add_nonfocus_evidence(preservation)
    relationship = next(
        item
        for item in preservation["assertions"]
        if item["assertion_id"] == "as:brennan-located-in-mireward"
    )
    relationship["metadata"]["evidence_ref_ids"] = [nonfocus_id]

    result = _project(preservation, _request())

    related = result.related_nodes[0]
    assert related.evidence_ref_ids == ["ev:session-28-mireward-arrival"]
    assert [badge.evidence_ref_id for badge in related.evidence_badges] == [
        "ev:session-28-mireward-arrival"
    ]
    assert related.adjacency[0].evidence_ref_ids == [nonfocus_id]
    assert related.anchored_to_focus_session is True
    assert related.adjacency[0].anchored_to_focus_session is False


def test_incoming_relationship_direction_is_relative_to_selected(
    preservation: dict,
) -> None:
    relationship = next(
        item
        for item in preservation["assertions"]
        if item["assertion_id"] == "as:brennan-located-in-mireward"
    )
    relationship["subject_entity_id"] = "entity:loc:mireward"
    relationship["value"]["entity_id"] = NODE_ID

    result = _project(preservation, _request())

    assert len(result.relationships) == 1
    assert result.relationships[0].source_node_id == "entity:loc:mireward"
    assert result.relationships[0].target_node_id == NODE_ID
    assert result.relationships[0].direction == "incoming"
    assert result.node is not None
    assert result.node.adjacency[0].direction == "incoming"
    assert result.related_nodes[0].adjacency[0].direction == "outgoing"


def test_bounded_read_and_presentation_work_shape(
    preservation: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    parsed, inner_reader = _runtime(preservation)

    class RecordingReader:
        def __init__(self):
            self.calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

        def open_coherent_view(self):
            return self

        def get_provenance_snapshot(self, *, artifact_ids, revision_ids):
            self.calls.append((tuple(artifact_ids), tuple(revision_ids)))
            return inner_reader.get_provenance_snapshot(
                artifact_ids=artifact_ids, revision_ids=revision_ids
            )

    real_service = adapter.EntityReadService()

    class RecordingService:
        def __init__(self):
            self.complete_calls: list[str] = []
            self.basic_calls: list[str] = []
            self.kernel_snapshot_calls = 0

        def get_complete_entity(self, context, entity_id):
            self.complete_calls.append(entity_id)
            before = len(reader.calls)
            result = real_service.get_complete_entity(context, entity_id)
            self.kernel_snapshot_calls += len(reader.calls) - before
            return result

        def get_entity(self, context, entity_id):
            self.basic_calls.append(entity_id)
            before = len(reader.calls)
            result = real_service.get_entity(context, entity_id)
            self.kernel_snapshot_calls += len(reader.calls) - before
            return result

    reader = RecordingReader()
    service = RecordingService()
    monkeypatch.setattr(adapter, "EntityReadService", lambda: service)

    result = project_complete_world_object_vnext(
        parsed_revision=parsed,
        source_reader=reader,
        request=_request(),
        read_identity=DungeonBuddyVNextReadIdentity(
            space_id="eldyrwild",
            revision_id=REVISION_ID,
            head_revision_id=REVISION_ID,
            is_head=True,
        ),
    )

    assert service.complete_calls == [NODE_ID]
    assert service.basic_calls == [item.node_id for item in result.related_nodes]
    assert service.basic_calls == ["entity:loc:mireward"]
    assert len(reader.calls) - service.kernel_snapshot_calls == 1
    assert reader.calls[-1] == (
        ("src:session-28-recap",),
        ("sr:session-28-recap-rev1",),
    )


def test_missing_object_is_clean_and_exact_revision_identity_is_preserved(
    preservation: dict,
) -> None:
    result = _project(preservation, _request(node_id="entity:missing"))

    assert result.found is False
    assert result.node is None
    assert result.resolved_node_id is None
    assert result.snapshot is not None
    assert result.snapshot.revision_id == REVISION_ID


@pytest.mark.parametrize("field", ["name", "classification"])
def test_ambiguous_display_fields_fail_closed(preservation: dict, field: str) -> None:
    duplicate = copy.deepcopy(
        next(
            item
            for item in preservation["assertions"]
            if item["predicate"] == f"dnd5e:{field}"
            and item["subject_entity_id"] == NODE_ID
        )
    )
    duplicate["assertion_id"] = f"as:brennan-second-{field}"
    if field == "name":
        duplicate["value"]["value"] = "Brennan Two"
    else:
        duplicate["value"]["term"] = "dnd5e:location"
    preservation["assertions"].append(duplicate)

    with pytest.raises(VNextCompleteObjectProjectionError, match="ambiguous"):
        _project(preservation, _request())


def test_ambiguous_summary_is_not_silently_selected(preservation: dict) -> None:
    duplicate = copy.deepcopy(preservation["assertions"][3])
    duplicate["assertion_id"] = "as:brennan-second-summary"
    duplicate["value"]["value"] = "A second admitted summary"
    preservation["assertions"].append(duplicate)

    result = _project(preservation, _request())

    assert result.node is not None
    assert result.node.summary is None
    assert {
        item.assertion_id
        for item in result.assertions
        if item.assertion_kind == "summary"
    } == {"as:brennan-secret-plan", "as:brennan-second-summary"}


def test_unknown_role_and_revision_mismatch_fail_closed(preservation: dict) -> None:
    with pytest.raises(
        VNextCompleteObjectProjectionError, match="unknown admissibility"
    ):
        _project(preservation, _request(role="oracle"))
    with pytest.raises(
        VNextCompleteObjectProjectionError, match="revision pin mismatch"
    ):
        _project(preservation, _request(revision_id="rev:wrong"))


def test_conflicting_source_context_metadata_fails_closed(preservation: dict) -> None:
    preservation["sources"][0]["domain_metadata"].append(
        {
            "schema": "dungeonbuddy.source:context_v1",
            "payload": {
                "campaign_id": "campaign-other",
                "session_id": "session-28",
            },
        }
    )

    with pytest.raises(VNextCompleteObjectProjectionError, match="conflicting source"):
        _project(preservation, _request())


def test_unrepresentable_literal_shape_fails_closed() -> None:
    assertion = ParsedAssertion(
        assertion_id="as:unsupported",
        subject_entity_id=NODE_ID,
        predicate="dnd5e:summary",
        value=ParsedLiteralValue(
            value=("not", "representable"), canonical_json_text="[]"
        ),
        metadata=ParsedAssertionMetadata(
            scope=(),
            visibility=ParsedPublicVisibility(),
            epistemic_basis="asserted",
            claim_mode="dungeonbuddy.claim:fact",
            standing="established",
            evidence_ref_ids=(),
            temporal_scope=ParsedTimelessTemporalScope(),
            domain_metadata=(),
        ),
    )

    with pytest.raises(VNextCompleteObjectProjectionError, match="losslessly"):
        _assertion_value(assertion)


def test_adapter_does_not_cross_alias_or_legacy_read_authority_boundary() -> None:
    source = (
        ROOT
        / "apps/live_control_server/integrations/dungeonmind/vnext_complete_object.py"
    ).read_text(encoding="utf-8")

    assert "aliases_by_entity" not in source
    assert "graph_memory.adapters.dungeonmind_reader" not in source
    assert "get_world_graph_object_projection" not in source
