"""Kernel world projection tests (PR007A)."""

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.union_supergraph.model import (
    UnionSupergraphEvidence,
    UnionSupergraphSourceArtifact,
)
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.kernel.world_projection import WorldGraphProjectionError
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "c8eb7e6ca7e735c40822cb1e6835f9949f2cd915b57f5704e7b4daeb72cf2fca"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "f69c69f271c427209860d902636347b70fea5920"
ACTOR = "gm"
EVENT_ID = "event:longmont-c2:session-23:mireward-gate-battle"
TRIPOD_ID = "threat:tripod-null-calf"
TRIPOD_CONTRIBUTION_ID = "contribution:022187fdefdf4557"

DUP_ALIGNED_CONTRIBUTION_ID = "contribution:aabbccdd11223344"
DUP_MISSING_CONTRIBUTION_ID = "contribution:bbccddeeff001122"
DUP_DIVERGENT_CONTRIBUTION_ID = "contribution:ccddeeff00112233"
RECAP_SOURCE_ARTIFACT_ID = "corpus:eldyrwild:session-23-recap"
DUP_SOURCE_ARTIFACT_ID = "graph-native:test:dup-aligned-battlefield"
FALLBACK_EDGE_CONTRIBUTION_ID = "contribution:ddccbbaa99887766"
FALLBACK_SPLIT_NODE_ID = "threat:test-fallback-split"
FALLBACK_SPLIT_CONTRIBUTION_ID = "contribution:aabbccddeeff1122"
ATTR_ONLY_ARTIFACT_ID = "graph-native:test:attr-direct-artifact"
ATTR_ONLY_CONTRIBUTION_ID = "contribution:eeff001122334455"

ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


def _revision_graph_path(root: Path, revision_id: str) -> Path:
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "graph.json"
    )


def _revision_manifest_path(root: Path, revision_id: str) -> Path:
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "revision.json"
    )


def _attestation() -> WorldInitializationApprovalAttestation:
    return WorldInitializationApprovalAttestation(
        bundle_id=BUNDLE_ID,
        bundle_digest=BUNDLE_DIGEST,
        approved_bundle_merge_sha=APPROVED_MERGE_SHA,
    )


def _plan(bundle) -> WorldInitializationPlan:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    return WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=_attestation(),
    )


def _initialize(root: Path, bundle) -> kernel.WorldInitializationResult:
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _request(
    *,
    revision_pin: str | None = None,
    campaign_id: str = CAMPAIGN_ID,
    admissibility: str = "gm",
    query_text: str | None = None,
    focus_kind: str = "none",
    session_id: str | None = None,
) -> WorldGraphProjectionRequest:
    focus = WorldGraphProjectionFocus(kind=focus_kind, session_id=session_id)
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=campaign_id,
        focus=focus,
        admissibility=admissibility,
        revision_pin=revision_pin,
        query_text=query_text,
    )


def _initialized_head_revision(root: Path, bundle) -> str:
    result = _initialize(root, bundle)
    assert result.published is True
    head, _revision, _store = kernel.open_current_world_graph(root, WORLD_ID)
    return head.head_revision_id


def _load_tripod_contribution_json(root: Path) -> dict:
    return json.loads(
        (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contributions"
            / "contribution__022187fdefdf4557.json"
        ).read_text(encoding="utf-8")
    )


def _assertions_from_contribution_json(payload: dict) -> list:
    return [
        kernel.GraphContributionAssertion.model_validate(assertion)
        for assertion in payload["accepted_assertions"]
    ]


def test_head_projection_matches_initialized_world(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    head_revision_id = _initialized_head_revision(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())

    assert projection.snapshot.revision_id == head_revision_id
    assert projection.snapshot.head_revision_id == head_revision_id
    assert projection.snapshot.is_head is True
    assert projection.summary.node_count == 12
    assert projection.summary.relationship_count == 11
    assert projection.summary.attribute_count == 3


def test_revision_pin_projection_reads_historical_revision(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    revisions_dir = tmp_path / "graph_memory" / "worlds" / WORLD_ID / "revisions"
    revision_ids = sorted(path.name for path in revisions_dir.iterdir() if path.is_dir())
    pinned = revision_ids[3]

    projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned),
    )

    assert projection.snapshot.revision_id == pinned
    assert projection.snapshot.head_revision_id == result.current_head_revision_id
    assert projection.snapshot.is_head is False


def test_invalid_revision_pin_fails_closed(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(revision_pin="rev:00000000000000000000000000000000"),
        )
    assert exc_info.value.code == "revision_not_found"


def test_invalid_format_revision_pin_fails_invalid_request(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(revision_pin="rev:missing-pin"),
        )
    assert exc_info.value.code == "invalid_request"


def test_tripod_attributes_reconstructed_from_revision_bound_contributions(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())

    tripod_attributes = {
        attribute.label or attribute.predicate
        for attribute in projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
    }
    assert tripod_attributes == {
        "battlefield_role",
        "challenge_expectation",
        "first_appearance",
    }
    battlefield = next(
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    assert "positional controller" in (battlefield.text_value or "").casefold()
    assert battlefield.active_contribution_ids == [TRIPOD_CONTRIBUTION_ID]


def test_relationship_to_mireward_gate_battle_present(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())

    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    relationship = next(
        item for item in projection.relationships if item.edge_id == edge_id
    )
    assert relationship.target_node_id == EVENT_ID


def test_positional_controller_search_selects_tripod_same_revision(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    head_revision_id = _initialized_head_revision(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="positional controller"),
    )

    assert projection.query_context is not None
    assert projection.query_context.snapshot.revision_id == head_revision_id
    assert projection.query_context.revision_id == head_revision_id
    assert projection.query_context.matched_node_ids[0] == TRIPOD_ID
    assert projection.query_context.match_reasons[TRIPOD_ID]


def test_threats_ready_natural_language_search_selects_tripod(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="What threats should I have ready?"),
    )

    assert projection.query_context is not None
    assert TRIPOD_ID in projection.query_context.matched_node_ids
    assert any(
        reason.startswith("token:threat")
        for reason in projection.query_context.match_reasons.get(TRIPOD_ID, [])
    )


def test_tripod_battle_natural_language_search_selects_tripod(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Tripod Mireward gate battle positional"),
    )

    assert projection.query_context is not None
    assert TRIPOD_ID in projection.query_context.matched_node_ids


def test_node_views_retain_badges_adjacency_and_lineage_fields(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)

    assert tripod.evidence_badges
    assert tripod.evidence_ref_ids
    assert tripod.source_artifact_ids
    assert any(candidate.node_id == EVENT_ID for candidate in tripod.adjacency)
    assert tripod.suggested_expansions


def test_search_collects_node_evidence_without_matching_attribute(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Tripod Null-Calf"),
    )

    assert projection.query_context is not None
    assert projection.query_context.evidence
    assert projection.query_context.source_artifacts
    node_evidence_ids = {
        evidence_id
        for node in projection.query_context.nodes
        for evidence_id in node.evidence_ref_ids
    }
    assert node_evidence_ids
    assert any(
        item.evidence_ref_id in node_evidence_ids
        for item in projection.query_context.evidence
    )


def test_search_collects_relationship_source_artifacts(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="positional controller"),
    )

    assert projection.query_context is not None
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    relationship = next(
        item for item in projection.query_context.relationships if item.edge_id == edge_id
    )
    assert relationship.evidence_ref_ids
    relationship_evidence = {
        item.evidence_ref_id: item.source_artifact_id
        for item in projection.query_context.evidence
    }
    for evidence_ref_id in relationship.evidence_ref_ids:
        artifact_id = relationship_evidence[evidence_ref_id]
        assert any(
            item.source_artifact_id == artifact_id
            for item in projection.query_context.source_artifacts
        )


def test_retracted_attribute_contribution_omits_attribute_on_head_keeps_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id

    retracted = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=TRIPOD_CONTRIBUTION_ID,
        reason="tripod prep withdrawn for test",
    )
    assert retracted.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    assert not any(
        attribute.subject_node_id == TRIPOD_ID for attribute in head_projection.attributes
    )
    assert TRIPOD_ID not in {node.node_id for node in head_projection.nodes}

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_attributes = {
        attribute.label or attribute.predicate
        for attribute in pinned_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
    }
    assert pinned_attributes == {
        "battlefield_role",
        "challenge_expectation",
        "first_appearance",
    }
    assert any(node.node_id == TRIPOD_ID for node in pinned_projection.nodes)


def test_superseded_attribute_contribution_omits_attribute_on_head_keeps_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    original_payload = _load_tripod_contribution_json(tmp_path)
    replacement_assertions = _assertions_from_contribution_json(original_payload)
    for assertion in replacement_assertions:
        if (assertion.label or assertion.predicate) == "battlefield_role":
            assertion.value = {"text": "Replacement role text"}

    replacement_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="supersede-1",
        accepted_assertions=replacement_assertions,
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    superseded = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=replacement_contribution,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert superseded.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    battlefield = next(
        attribute
        for attribute in head_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    assert "replacement role text" in (battlefield.text_value or "").casefold()
    assert not any(
        "positional controller" in (attribute.text_value or "").casefold()
        for attribute in head_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
    )

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_battlefield = next(
        attribute
        for attribute in pinned_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    assert "positional controller" in (pinned_battlefield.text_value or "").casefold()


def test_superseded_edge_contribution_shows_replacement_on_head_keeps_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    original_payload = _load_tripod_contribution_json(tmp_path)
    replacement_assertions = _assertions_from_contribution_json(original_payload)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    for assertion in replacement_assertions:
        value = dict(assertion.value)
        if str(value.get("edge_id") or "") != edge_id:
            continue
        assertion.label = "replacement appeared label"
        assertion.value = {**value, "session_ids": ["session-99"]}

    replacement_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="supersede-edge-1",
        accepted_assertions=replacement_assertions,
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    superseded = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=replacement_contribution,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert superseded.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    head_relationship = next(
        item for item in head_projection.relationships if item.edge_id == edge_id
    )
    assert head_relationship.label == "replacement appeared label"
    assert head_relationship.session_ids == ["session-99"]

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_relationship = next(
        item for item in pinned_projection.relationships if item.edge_id == edge_id
    )
    assert pinned_relationship.label == "appeared in"
    assert pinned_relationship.session_ids != ["session-99"]


def test_malformed_stored_json_at_pinned_revision_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, pinned_revision_id)
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request(revision_pin=pinned_revision_id))
    assert exc_info.value.code == "projection_integrity_error"


def test_manifest_hash_mismatch_at_pinned_revision_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, pinned_revision_id)
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["campaign_id"] = "tampered-campaign-id"
    graph_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request(revision_pin=pinned_revision_id))
    assert exc_info.value.code == "projection_integrity_error"


def test_tampered_graph_payload_with_matching_hash_fails_revision_identity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, pinned_revision_id)
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["campaign_id"] = "tampered-campaign-id"
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ) + "\n"
    graph_path.write_text(canonical, encoding="utf-8")

    manifest_path = _revision_manifest_path(tmp_path, pinned_revision_id)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["graph_payload_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request(revision_pin=pinned_revision_id))
    assert exc_info.value.code == "projection_integrity_error"


def test_malformed_head_revision_fails_integrity_without_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    head_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, head_revision_id)
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_multi_source_active_contributions_project_when_semantically_aligned(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_ALIGNED_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_ALIGNED_CONTRIBUTION_ID
    duplicate["source_artifact_id"] = RECAP_SOURCE_ARTIFACT_ID
    duplicate["source_revision_id"] = "dup-revision"
    duplicate_assertion = next(
        item
        for item in original["accepted_assertions"]
        if item["assertion_id"] == assertion.assertion_id
    )
    duplicate_aligned = deepcopy(duplicate_assertion)
    duplicate_aligned["evidence_ref_ids"] = ["evidence:bundle:v1:statblock:tripod-challenge"]
    duplicate_aligned["source_artifact_id"] = RECAP_SOURCE_ARTIFACT_ID
    duplicate_aligned["value"] = {
        **duplicate_assertion["value"],
        "source_domains": ["recap"],
        "source_domain": "recap",
        "source_artifact_id": RECAP_SOURCE_ARTIFACT_ID,
        "evidence_ref_ids": ["evidence:bundle:v1:statblock:tripod-challenge"],
        "evidence": [
            {
                "evidence_ref_id": "evidence:bundle:v1:statblock:tripod-challenge",
                "locator": "jsonptr:/accepted_assertions/0",
                "source_artifact_id": RECAP_SOURCE_ARTIFACT_ID,
                "source_domain": "recap",
            }
        ],
        "source_artifacts": [
            {
                "campaign_id": CAMPAIGN_ID,
                "source_artifact_id": RECAP_SOURCE_ARTIFACT_ID,
                "source_domain": "recap",
                "uri": "corpus://eldyrwild/session-23-recap",
            }
        ],
    }
    duplicate["accepted_assertions"] = [duplicate_aligned]
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_ALIGNED_CONTRIBUTION_ID,
        }
    )
    store.assertion_support[assertion.assertion_id] = support
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-alignment"],
    )

    projection = kernel.project_world_graph(tmp_path, _request())
    battlefield = next(
        item
        for item in projection.attributes
        if item.assertion_id == assertion.assertion_id
    )
    assert set(battlefield.active_contribution_ids) == {
        TRIPOD_CONTRIBUTION_ID,
        DUP_ALIGNED_CONTRIBUTION_ID,
    }
    assert "evidence:bundle:v1:statblock:tripod-battlefield-role" in battlefield.evidence_ref_ids
    assert "evidence:bundle:v1:statblock:tripod-challenge" in battlefield.evidence_ref_ids


def test_multi_source_missing_assertion_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )

    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_MISSING_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_MISSING_CONTRIBUTION_ID
    duplicate["accepted_assertions"] = [
        item
        for item in original["accepted_assertions"]
        if item["assertion_id"] != assertion.assertion_id
    ]
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_MISSING_CONTRIBUTION_ID,
        }
    )
    store.assertion_support[assertion.assertion_id] = support
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-missing-assertion"],
    )

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_multi_source_semantic_divergence_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )

    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_DIVERGENT_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_DIVERGENT_CONTRIBUTION_ID
    duplicate_assertions = []
    for item in original["accepted_assertions"]:
        if item["assertion_id"] != assertion.assertion_id:
            continue
        divergent = deepcopy(item)
        divergent["value"] = {"text": "Divergent battlefield role"}
        duplicate_assertions.append(divergent)
    duplicate["accepted_assertions"] = duplicate_assertions
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_DIVERGENT_CONTRIBUTION_ID,
        }
    )
    store.assertion_support[assertion.assertion_id] = support
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-divergence"],
    )

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_unsupported_edge_omitted_from_relationships_and_node_adjacency(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    edge = store.edges[edge_id]
    edge_state = dict(edge.state or {})
    edge_state["memory_state"] = "unsupported_assertion"
    store.edges[edge_id] = edge.model_copy(update={"state": edge_state})

    for assertion_id, raw_support in store.assertion_support.items():
        support = dict(raw_support)
        if support.get("graph_object_id") != edge_id:
            continue
        support["support_state"] = "unsupported"
        support["active_contribution_ids"] = []
        store.assertion_support[assertion_id] = support
        break

    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-edge-only-retraction"],
    )

    projection = kernel.project_world_graph(tmp_path, _request())
    assert not any(relationship.edge_id == edge_id for relationship in projection.relationships)

    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    event = next(node for node in projection.nodes if node.node_id == EVENT_ID)
    assert not any(candidate.edge_id == edge_id for candidate in tripod.adjacency)
    assert not any(
        expansion.edge_id == edge_id for expansion in tripod.suggested_expansions
    )
    assert not any(candidate.edge_id == edge_id for candidate in event.adjacency)
    assert not any(
        expansion.edge_id == edge_id for expansion in event.suggested_expansions
    )


def test_multi_source_one_supporter_retracted_drops_retracted_evidence_on_head(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)

    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    original_evidence = "evidence:bundle:v1:statblock:tripod-battlefield-role"
    duplicate_evidence = "evidence:bundle:v1:statblock:dup-aligned-battlefield-only"

    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_ALIGNED_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_ALIGNED_CONTRIBUTION_ID
    duplicate["source_artifact_id"] = DUP_SOURCE_ARTIFACT_ID
    duplicate["source_revision_id"] = "dup-revision"
    duplicate_assertion = next(
        item
        for item in original["accepted_assertions"]
        if item["assertion_id"] == assertion.assertion_id
    )
    duplicate_aligned = deepcopy(duplicate_assertion)
    duplicate_aligned["evidence_ref_ids"] = [duplicate_evidence]
    duplicate_aligned["source_artifact_id"] = DUP_SOURCE_ARTIFACT_ID
    duplicate_aligned["value"] = {
        **duplicate_assertion["value"],
        "source_domains": ["statblock"],
        "source_domain": "statblock",
        "source_artifact_id": DUP_SOURCE_ARTIFACT_ID,
        "evidence_ref_ids": [duplicate_evidence],
        "evidence": [
            {
                "evidence_ref_id": duplicate_evidence,
                "locator": "jsonptr:/accepted_assertions/0",
                "source_artifact_id": DUP_SOURCE_ARTIFACT_ID,
                "source_domain": "statblock",
            }
        ],
        "source_artifacts": [
            {
                "campaign_id": CAMPAIGN_ID,
                "source_artifact_id": DUP_SOURCE_ARTIFACT_ID,
                "source_domain": "statblock",
                "uri": "graph-data://test/dup-aligned-battlefield",
            }
        ],
    }
    duplicate["accepted_assertions"] = [duplicate_aligned]
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_ALIGNED_CONTRIBUTION_ID,
        }
    )
    support["evidence_ref_ids"] = sorted(
        {
            *support.get("evidence_ref_ids", []),
            original_evidence,
            duplicate_evidence,
        }
    )
    store.assertion_support[assertion.assertion_id] = support
    store.evidence[duplicate_evidence] = UnionSupergraphEvidence(
        evidence_ref_id=duplicate_evidence,
        source_artifact_id=DUP_SOURCE_ARTIFACT_ID,
        source_domain="statblock",
        evidence_role="contribution_support",
        can_open_source=True,
        can_highlight_span=False,
        locator="jsonptr:/accepted_assertions/0",
    )
    if DUP_SOURCE_ARTIFACT_ID not in store.source_artifacts:
        store.source_artifacts[DUP_SOURCE_ARTIFACT_ID] = UnionSupergraphSourceArtifact(
            source_artifact_id=DUP_SOURCE_ARTIFACT_ID,
            source_domain="statblock",
            campaign_id=CAMPAIGN_ID,
            uri="graph-data://test/dup-aligned-battlefield",
        )
    multi_source = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-before-retract"],
    )
    pinned_revision_id = multi_source.revision.revision_id

    retracted = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=DUP_ALIGNED_CONTRIBUTION_ID,
        reason="duplicate battlefield provenance withdrawn",
    )
    assert retracted.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    head_battlefield = next(
        item
        for item in head_projection.attributes
        if item.assertion_id == assertion.assertion_id
    )
    assert original_evidence in head_battlefield.evidence_ref_ids
    assert duplicate_evidence not in head_battlefield.evidence_ref_ids
    assert DUP_ALIGNED_CONTRIBUTION_ID not in head_battlefield.active_contribution_ids

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_battlefield = next(
        item
        for item in pinned_projection.attributes
        if item.assertion_id == assertion.assertion_id
    )
    assert original_evidence in pinned_battlefield.evidence_ref_ids
    assert duplicate_evidence in pinned_battlefield.evidence_ref_ids

    head_top_level_evidence_ids = {
        item.evidence_ref_id for item in head_projection.evidence
    }
    head_top_level_artifact_ids = {
        item.source_artifact_id for item in head_projection.source_artifacts
    }
    assert duplicate_evidence not in head_top_level_evidence_ids
    assert DUP_SOURCE_ARTIFACT_ID not in head_top_level_artifact_ids
    assert head_top_level_artifact_ids == {
        item.source_artifact_id for item in head_projection.evidence
    }

    pinned_top_level_evidence_ids = {
        item.evidence_ref_id for item in pinned_projection.evidence
    }
    pinned_top_level_artifact_ids = {
        item.source_artifact_id for item in pinned_projection.source_artifacts
    }
    assert duplicate_evidence in pinned_top_level_evidence_ids
    assert DUP_SOURCE_ARTIFACT_ID in pinned_top_level_artifact_ids
    assert pinned_top_level_artifact_ids == {
        item.source_artifact_id for item in pinned_projection.evidence
    }


def test_generated_fallback_evidence_surfaces_in_projection(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = "edge:threat:tripod-null-calf:related_to:location:mireward"
    source_node_id = TRIPOD_ID
    target_node_id = "location:mireward"
    edge_assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        contribution_id=FALLBACK_EDGE_CONTRIBUTION_ID,
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate="related_to",
        label="guards approach",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id="graph-native:test:fallback-edge",
        value={
            "edge_id": edge_id,
            "direction": "outbound",
            "source_domains": ["manual_seed"],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:fallback-edge",
        source_revision_id="fallback-edge-1",
        accepted_assertions=[edge_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True
    merged_contribution_id = merged.contribution_ids[0]
    fallback_evidence_id = f"evidence:{merged_contribution_id}:{edge_id}"

    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Tripod Null-Calf"),
    )
    relationship = next(
        item for item in projection.relationships if item.edge_id == edge_id
    )
    assert fallback_evidence_id in relationship.evidence_ref_ids

    source_node = next(node for node in projection.nodes if node.node_id == source_node_id)
    target_node = next(node for node in projection.nodes if node.node_id == target_node_id)
    assert fallback_evidence_id in source_node.evidence_ref_ids
    assert fallback_evidence_id in target_node.evidence_ref_ids
    assert any(
        badge.evidence_ref_id == fallback_evidence_id for badge in source_node.evidence_badges
    )

    assert projection.query_context is not None
    assert source_node_id in projection.query_context.matched_node_ids
    query_evidence_ids = {
        item.evidence_ref_id for item in projection.query_context.evidence
    }
    assert fallback_evidence_id in query_evidence_ids

    top_level_evidence_ids = {item.evidence_ref_id for item in projection.evidence}
    assert fallback_evidence_id in top_level_evidence_ids
    fallback_artifact_id = next(
        evidence.source_artifact_id
        for evidence in projection.evidence
        if evidence.evidence_ref_id == fallback_evidence_id
    )
    top_level_artifact_ids = {
        artifact.source_artifact_id for artifact in projection.source_artifacts
    }
    assert fallback_artifact_id in top_level_artifact_ids
    assert fallback_artifact_id in relationship.source_artifact_ids
    assert fallback_artifact_id in source_node.source_artifact_ids
    assert fallback_artifact_id in target_node.source_artifact_ids


def test_node_fallback_evidence_not_attributed_to_sibling_attribute(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    source_artifact_id = "graph-native:test:fallback-split"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        contribution_id=FALLBACK_SPLIT_CONTRIBUTION_ID,
        subject_node_id=FALLBACK_SPLIT_NODE_ID,
        label="Fallback Split Test",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Fallback Split Test"],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[],
    )
    attribute_assertion = kernel.build_assertion(
        assertion_kind="attribute",
        acceptance_state="accepted",
        contribution_id=FALLBACK_SPLIT_CONTRIBUTION_ID,
        subject_node_id=FALLBACK_SPLIT_NODE_ID,
        predicate="test_marker",
        label="test_marker",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "attribute": "test_marker",
            "text": "marker without evidence",
            "source_domains": ["manual_seed"],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=source_artifact_id,
        source_revision_id="fallback-split-1",
        accepted_assertions=[node_assertion, attribute_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True
    merged_contribution_id = merged.contribution_ids[0]
    fallback_evidence_id = f"evidence:{merged_contribution_id}:{FALLBACK_SPLIT_NODE_ID}"

    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Fallback Split Test"),
    )
    node = next(node for node in projection.nodes if node.node_id == FALLBACK_SPLIT_NODE_ID)
    attribute = next(
        item
        for item in projection.attributes
        if item.subject_node_id == FALLBACK_SPLIT_NODE_ID
        and (item.label or item.predicate) == "test_marker"
    )
    assert fallback_evidence_id in node.evidence_ref_ids
    assert fallback_evidence_id not in attribute.evidence_ref_ids
    assert attribute.evidence_ref_ids == []

    assert projection.query_context is not None
    assert FALLBACK_SPLIT_NODE_ID in projection.query_context.matched_node_ids
    query_attribute = next(
        item
        for item in projection.query_context.attributes
        if item.subject_node_id == FALLBACK_SPLIT_NODE_ID
        and (item.label or item.predicate) == "test_marker"
    )
    assert fallback_evidence_id not in query_attribute.evidence_ref_ids
    query_node = next(
        item for item in projection.query_context.nodes if item.node_id == FALLBACK_SPLIT_NODE_ID
    )
    assert fallback_evidence_id in query_node.evidence_ref_ids


def test_attribute_direct_source_artifact_surfaces_in_projection_closure(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    attribute_assertion = kernel.build_assertion(
        assertion_kind="attribute",
        acceptance_state="accepted",
        contribution_id=ATTR_ONLY_CONTRIBUTION_ID,
        subject_node_id=TRIPOD_ID,
        predicate="artifact_only_marker",
        label="artifact_only_marker",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=ATTR_ONLY_ARTIFACT_ID,
        value={
            "attribute": "artifact_only_marker",
            "text": "attribute with direct artifact only",
            "source_domains": ["manual_seed"],
            "source_artifacts": [
                {
                    "source_artifact_id": ATTR_ONLY_ARTIFACT_ID,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": "graph-data://test/attr-direct-artifact",
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=ATTR_ONLY_ARTIFACT_ID,
        source_revision_id="attr-artifact-only-1",
        accepted_assertions=[attribute_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True

    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Attr Artifact Only"),
    )
    attribute = next(
        item
        for item in projection.attributes
        if item.subject_node_id == TRIPOD_ID
        and (item.label or item.predicate) == "artifact_only_marker"
    )
    assert attribute.evidence_ref_ids == []
    assert ATTR_ONLY_ARTIFACT_ID in attribute.source_artifact_ids
    top_level_artifact_ids = {
        artifact.source_artifact_id for artifact in projection.source_artifacts
    }
    assert ATTR_ONLY_ARTIFACT_ID in top_level_artifact_ids

    assert projection.query_context is not None
    query_artifact_ids = {
        artifact.source_artifact_id for artifact in projection.query_context.source_artifacts
    }
    assert ATTR_ONLY_ARTIFACT_ID in query_artifact_ids


def test_unsupported_admissibility_fails_closed(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(admissibility="player"),
        )
    assert exc_info.value.code == "unsupported_admissibility"


def test_campaign_mismatch_fails_closed(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(campaign_id="foreign-campaign"),
        )
    assert exc_info.value.code == "campaign_scope_mismatch"


def test_integrity_failure_when_contribution_missing(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    contribution_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / "contribution__022187fdefdf4557.json"
    )
    assert contribution_path.is_file()
    shutil.move(
        contribution_path,
        contribution_path.with_suffix(".json.removed"),
    )

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_projection_apis_exported_from_kernel_public_api() -> None:
    for name in (
        "project_world_graph",
        "build_projection_payload",
        "resolve_projection_admissibility",
        "search_world_graph_projection",
        "WorldGraphProjectionError",
    ):
        assert name in kernel.__all__
        assert hasattr(kernel, name)
