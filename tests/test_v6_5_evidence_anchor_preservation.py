"""V6.5 acceptance proof for Buddy-native evidence and source anchors."""

from __future__ import annotations

import copy
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dungeonmind.application.vnext import (
    EvidenceReadService,
    InMemoryKnowledgeSourceReader,
    build_parsed_knowledge_revision,
)
from dungeonmind.application.vnext import (
    admission,
    evidence_reads,
    materialization,
    publication,
    source_anchors,
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
from graph_memory.vnext import (
    DungeonBuddyVNextProjectionInput,
    build_dungeonbuddy_read_context,
)

from apps.live_control_server.integrations.dungeonmind.vnext_complete_object import (
    DungeonBuddyVNextReadIdentity,
    project_complete_world_object_vnext,
)
from apps.live_control_server.models.world_graph_object_projection import (
    WorldGraphObjectProjectionRequest,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json"
REVISION_ID = "rev:v6-5-witness"
EVIDENCE_ID = "ev:session-28-mireward-arrival"
ASSERTION_ID = "as:brennan-name"
ARTIFACT_ID = "src:session-28-recap"
SOURCE_REVISION_ID = "sr:session-28-recap-rev1"
NODE_ID = "entity:npc:brennan-tallow"


@pytest.fixture
def preservation() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    evidence = data["evidence"][0]
    evidence.update(
        uri="buddy://recaps/session-28",
        source_locator="session-28.md",
        line_ref="L140-L146",
        source_span_ref_id="span:session-28:arrival",
    )
    data["sources"][0]["current_revision_id"] = SOURCE_REVISION_ID
    data["sources"][0]["uri"] = "buddy://recaps/session-28"
    data["source_revisions"][0]["locator"] = "session-28.md"
    return data


def _runtime(data: dict, *, revision_id: str = REVISION_ID):
    revision = KnowledgeRevision(
        space_id=data["space_id"],
        revision_id=revision_id,
        created_at=datetime(2026, 9, 27, tzinfo=UTC),
        operation_ids=["op:v6-5-witness"],
        graph_schema="dungeonbuddy.test:v6_5",
        graph_payload_sha256="5" * 64,
        domain_contract_ref=DomainContractRef.model_validate(data["domain_contract_ref"]),
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


def _context(
    data: dict,
    *,
    role: str = "gm",
    scope_mode: str = "campaign",
    campaign_id: str | None = "campaign-longmont",
    session_id: str | None = "session-28",
    revision_id: str = REVISION_ID,
    reader: InMemoryKnowledgeSourceReader | None = None,
):
    parsed, default_reader = _runtime(data, revision_id=revision_id)
    return build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id=data["space_id"],
            scope_mode=scope_mode,  # type: ignore[arg-type]
            role=role,  # type: ignore[arg-type]
            campaign_id=campaign_id,
            session_id=session_id,
            revision_id=revision_id,
        ),
        source_reader=reader or default_reader,
    )


def _add_campaign_b_support(data: dict) -> str:
    source = copy.deepcopy(data["sources"][0])
    source.update(
        source_artifact_id="src:campaign-b",
        current_revision_id="sr:campaign-b:1",
        uri="buddy://campaign-b/source",
    )
    data["sources"].append(source)
    revision = copy.deepcopy(data["source_revisions"][0])
    revision.update(
        source_revision_id="sr:campaign-b:1",
        source_artifact_id="src:campaign-b",
        content_sha256="b" * 64,
    )
    data["source_revisions"].append(revision)
    evidence = copy.deepcopy(data["evidence"][0])
    evidence.update(
        evidence_ref_id="ev:campaign-b",
        source_artifact_id="src:campaign-b",
        source_revision_id="sr:campaign-b:1",
        source_span_ref_id=None,
    )
    data["evidence"].append(evidence)
    assertion = copy.deepcopy(data["assertions"][2])
    assertion["assertion_id"] = "as:brennan-name-campaign-b"
    assertion["metadata"]["scope"][0]["value"] = "campaign-b"
    assertion["metadata"]["evidence_ref_ids"] = ["ev:campaign-b"]
    data["assertions"].append(assertion)
    return "ev:campaign-b"


def _add_gm_only_support(data: dict, *, standing: str = "established") -> str:
    evidence = copy.deepcopy(data["evidence"][0])
    evidence.update(
        evidence_ref_id=f"ev:gm-only:{standing}",
        locator="secret:42",
        uri="buddy://secret/source",
        source_locator="secret.md",
        line_ref="L42",
        source_span_ref_id="span:secret:42",
    )
    data["evidence"].append(evidence)
    assertion = copy.deepcopy(data["assertions"][3])
    assertion["assertion_id"] = f"as:gm-only:{standing}"
    assertion["metadata"]["standing"] = standing
    assertion["metadata"]["evidence_ref_ids"] = [evidence["evidence_ref_id"]]
    data["assertions"].append(assertion)
    return evidence["evidence_ref_id"]


def test_exact_native_reads_preserve_evidence_source_and_span_identity(
    preservation: dict,
) -> None:
    context = _context(preservation)
    service = EvidenceReadService()

    assertion = service.get_assertion_evidence(context, ASSERTION_ID)
    evidence = service.get_evidence(context, EVIDENCE_ID)
    anchor = evidence.anchors[0]
    resolved = service.resolve_source_anchor(context, anchor.anchor_id)

    assert assertion.available and evidence.available and resolved.resolved
    assert assertion.evidence == (evidence.evidence,)
    assert resolved.evidence == evidence.evidence
    assert evidence.identity.space_id == "eldyrwild"
    assert evidence.identity.revision_id == REVISION_ID
    assert evidence.evidence is not None
    assert evidence.evidence.source_artifact_id == ARTIFACT_ID
    assert evidence.evidence.source_revision_id == SOURCE_REVISION_ID
    assert evidence.evidence.locator == "paragraph:14"
    assert evidence.evidence.uri == "buddy://recaps/session-28"
    assert evidence.evidence.source_locator == "session-28.md"
    assert evidence.evidence.line_ref == "L140-L146"
    assert evidence.evidence.source_span_ref_id == "span:session-28:arrival"
    assert evidence.evidence.can_open_source is True
    assert evidence.evidence.can_highlight_span is True
    assert evidence.source_artifacts[0].current_revision_id == SOURCE_REVISION_ID
    assert evidence.source_revisions[0].content_sha256 == (
        preservation["source_revisions"][0]["content_sha256"]
    )
    assert tuple(item.assertion_id for item in evidence.admitted_supporter_assertions) == (
        "as:brennan-classification",
        "as:brennan-located-in-mireward",
        "as:brennan-name",
        "as:brennan-secret-plan",
        "as:mireward-classification",
    )
    assert anchor.source_span_ref_id == "span:session-28:arrival"
    assert resolved.anchor == anchor
    assert assertion.completeness.status == "complete"
    assert evidence.completeness.status == "complete"
    assert resolved.completeness.status == "complete"
    assert assertion.result_digest and evidence.result_digest and resolved.result_digest


def test_missing_span_is_preserved_and_never_derived_from_locator(
    preservation: dict,
) -> None:
    preservation["evidence"][0]["source_span_ref_id"] = None
    result = EvidenceReadService().get_evidence(_context(preservation), EVIDENCE_ID)

    assert result.available
    assert result.evidence is not None
    assert result.evidence.locator == "paragraph:14"
    assert result.evidence.can_highlight_span is True
    assert result.evidence.source_span_ref_id is None
    assert result.anchors[0].source_span_ref_id is None


def test_complete_object_evidence_ids_join_to_native_reads_without_semantic_drift(
    preservation: dict,
) -> None:
    parsed, reader = _runtime(preservation)
    request = WorldGraphObjectProjectionRequest.model_validate(
        {
            "schema": "dmb_world_graph_object_projection_request_v1",
            "worldId": "eldyrwild",
            "campaignId": "campaign-longmont",
            "nodeId": NODE_ID,
            "focus": {
                "kind": "session",
                "campaignId": "campaign-longmont",
                "sessionId": "session-28",
            },
            "admissibility": "gm",
            "revisionPin": REVISION_ID,
        }
    )
    projection = project_complete_world_object_vnext(
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
    context = build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            role="gm",
            campaign_id="campaign-longmont",
            session_id="session-28",
            revision_id=REVISION_ID,
        ),
        source_reader=reader,
    )
    service = EvidenceReadService()

    assert projection.node is not None
    assert projection.node.evidence_ref_ids == [EVIDENCE_ID]
    native = service.get_evidence(context, projection.node.evidence_ref_ids[0])
    assert native.available
    assert {item.assertion_id for item in native.admitted_supporter_assertions} >= {
        item.assertion_id for item in projection.assertions
    }
    assert projection.assertions[0].temporal_scope is not None
    assert projection.source_bindings[0].source_domain == "recap"
    assert projection.source_bindings[0].session_id == "session-28"
    assert native.source_revisions[0].content_sha256 == (
        projection.source_bindings[0].content_sha256
    )


def test_campaign_world_role_and_standing_boundaries_fail_closed(
    preservation: dict,
) -> None:
    campaign_b = _add_campaign_b_support(preservation)
    gm_only = _add_gm_only_support(preservation)
    provisional_only = _add_gm_only_support(preservation, standing="provisional")
    retracted_only = _add_gm_only_support(preservation, standing="retracted")
    service = EvidenceReadService()

    campaign_a = _context(preservation, role="gm")
    world = _context(
        preservation,
        role="gm",
        scope_mode="world",
        campaign_id=None,
        session_id=None,
    )
    player = _context(preservation, role="player")

    assert service.get_evidence(campaign_a, EVIDENCE_ID).available
    assert not service.get_evidence(campaign_a, campaign_b).available
    assert service.get_evidence(world, campaign_b).available
    assert service.get_evidence(campaign_a, gm_only).available
    assert service.get_evidence(campaign_a, provisional_only).available
    for denied_id in (gm_only, provisional_only, retracted_only):
        denied = service.get_evidence(player, denied_id)
        assert not denied.available
        assert denied.evidence is None
        assert denied.anchors == ()
        assert denied.source_artifacts == ()
        assert denied.source_revisions == ()
        assert denied.admitted_supporter_assertions == ()
    assert not service.get_evidence(campaign_a, retracted_only).available


def test_anchor_tokens_are_deterministic_context_bound_and_fail_closed(
    preservation: dict,
) -> None:
    service = EvidenceReadService()
    context = _context(preservation)
    rebuilt = _context(preservation)
    first = service.get_evidence(context, EVIDENCE_ID)
    second = service.get_evidence(context, EVIDENCE_ID)
    token = first.anchors[0].anchor_id

    assert token == second.anchors[0].anchor_id
    assert service.resolve_source_anchor(context, token).resolved
    assert service.resolve_source_anchor(rebuilt, token).resolved
    assert not service.resolve_source_anchor(context, "not-an-anchor").resolved
    assert not service.resolve_source_anchor(context, token + "forged").resolved

    changed_contexts = (
        _context(preservation, role="player"),
        _context(preservation, session_id="session-99"),
        _context(preservation, revision_id="rev:v6-5-other"),
    )
    for changed in changed_contexts:
        denied = service.resolve_source_anchor(changed, token)
        assert not denied.resolved
        assert denied.anchor is None and denied.evidence is None
        assert denied.source_artifacts == () and denied.source_revisions == ()

    foreign = copy.deepcopy(preservation)
    foreign["space_id"] = "foreign-world"
    assert not service.resolve_source_anchor(_context(foreign), token).resolved


def test_focus_changes_anchor_identity_not_truth_or_fictional_time(
    preservation: dict,
) -> None:
    service = EvidenceReadService()
    focused = _context(preservation, session_id="session-28")
    unfocused = _context(preservation, session_id="session-99")

    focused_read = service.get_evidence(focused, EVIDENCE_ID)
    unfocused_read = service.get_evidence(unfocused, EVIDENCE_ID)
    assert focused_read.evidence == unfocused_read.evidence
    assert tuple(item.assertion_id for item in focused_read.admitted_supporter_assertions) == tuple(
        item.assertion_id for item in unfocused_read.admitted_supporter_assertions
    )
    focused_time = {
        item.assertion_id: item.metadata.temporal_scope
        for item in focused_read.admitted_supporter_assertions
    }
    unfocused_time = {
        item.assertion_id: item.metadata.temporal_scope
        for item in unfocused_read.admitted_supporter_assertions
    }
    assert focused_time == unfocused_time
    assert focused_read.anchors[0].anchor_id != unfocused_read.anchors[0].anchor_id
    assert not service.resolve_source_anchor(
        unfocused, focused_read.anchors[0].anchor_id
    ).resolved


def test_fresh_context_rejects_anchor_after_evidence_locator_drift(
    preservation: dict,
) -> None:
    service = EvidenceReadService()
    old_context = _context(preservation)
    token = service.get_evidence(old_context, EVIDENCE_ID).anchors[0].anchor_id

    changed = copy.deepcopy(preservation)
    changed["evidence"][0]["locator"] = "paragraph:15"
    changed["evidence"][0]["line_ref"] = "L147-L150"
    fresh = _context(changed)

    assert service.resolve_source_anchor(old_context, token).resolved
    assert service.get_evidence(fresh, EVIDENCE_ID).available
    assert not service.resolve_source_anchor(fresh, token).resolved


@pytest.mark.parametrize(
    ("mutation", "expected_available"),
    [
        ("missing_artifact", False),
        ("missing_revision", False),
        ("artifact_retracted", False),
        ("artifact_visibility", True),
        ("artifact_revision", True),
        ("revision_artifact", False),
        ("revision_digest", True),
    ],
)
def test_pinned_context_stays_coherent_while_fresh_context_rejects_stale_anchor(
    preservation: dict,
    mutation: str,
    expected_available: bool,
) -> None:
    parsed, reader = _runtime(preservation)
    old_context = build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            role="gm",
            campaign_id="campaign-longmont",
            session_id="session-28",
            revision_id=REVISION_ID,
        ),
        source_reader=reader,
    )
    service = EvidenceReadService()
    old = service.get_evidence(old_context, EVIDENCE_ID)
    token = old.anchors[0].anchor_id

    if mutation == "missing_artifact":
        del reader._artifacts[ARTIFACT_ID]
    elif mutation == "missing_revision":
        del reader._revisions[SOURCE_REVISION_ID]
    elif mutation == "artifact_retracted":
        artifact = reader._artifacts[ARTIFACT_ID].model_copy(
            update={"status": "retracted"}
        )
        reader._artifacts[ARTIFACT_ID] = artifact
    elif mutation == "artifact_visibility":
        payload = reader._artifacts[ARTIFACT_ID].model_dump(mode="json")
        payload["visibility"] = {
            "kind": "labels_any",
            "labels": ["dungeonbuddy.visibility:gm"],
        }
        reader._artifacts[ARTIFACT_ID] = SourceArtifactV3.model_validate(payload)
    elif mutation == "artifact_revision":
        artifact = reader._artifacts[ARTIFACT_ID].model_copy(
            update={"current_revision_id": "sr:other"}
        )
        reader._artifacts[ARTIFACT_ID] = artifact
    elif mutation == "revision_artifact":
        revision = reader._revisions[SOURCE_REVISION_ID].model_copy(
            update={"source_artifact_id": "src:other"}
        )
        reader._revisions[SOURCE_REVISION_ID] = revision
    else:
        revision = reader._revisions[SOURCE_REVISION_ID].model_copy(
            update={"content_sha256": "d" * 64}
        )
        reader._revisions[SOURCE_REVISION_ID] = revision

    assert service.resolve_source_anchor(old_context, token).resolved
    fresh = build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            role="gm",
            campaign_id="campaign-longmont",
            session_id="session-28",
            revision_id=REVISION_ID,
        ),
        source_reader=reader,
    )
    fresh_read = service.get_evidence(fresh, EVIDENCE_ID)
    assert fresh_read.available is expected_available
    assert not service.resolve_source_anchor(fresh, token).resolved


def test_native_vnext_boundaries_do_not_import_buddy_or_legacy_policy() -> None:
    modules = (admission, evidence_reads, source_anchors, materialization, publication)
    forbidden_imports = (
        "from graph_memory",
        "import graph_memory",
        "from apps.live_control_server",
        "import apps.live_control_server",
        "from worldkeeper",
        "import worldkeeper",
    )
    for module in modules:
        source = inspect.getsource(module)
        assert not any(term in source for term in forbidden_imports), module.__name__
        assert "dungeonbuddy.visibility:gm" not in source
        assert "dungeonbuddy.visibility:player" not in source
        assert "dungeonbuddy.scope:campaign" not in source
        assert "dnd5e:npc" not in source
        assert "dungeonbuddy.time:fictional_anchor_v1" not in source
