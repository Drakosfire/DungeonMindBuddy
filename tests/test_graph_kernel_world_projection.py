"""Kernel world projection tests (PR007A)."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
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
            _request(revision_pin="rev:missing-pin"),
        )
    assert exc_info.value.code == "revision_not_found"


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
    duplicate["source_revision_id"] = "dup-revision"
    duplicate["accepted_assertions"] = [
        item
        for item in original["accepted_assertions"]
        if item["assertion_id"] == assertion.assertion_id
    ]
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
