"""End-to-end: multi-session edge provenance accumulates session_ids."""

from __future__ import annotations

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
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ACTOR = "gm"

SOURCE_NODE_ID = "pc:caelynn"
TARGET_NODE_ID = "threat:tripod-null-calf"
EDGE_ID = f"edge:{SOURCE_NODE_ID}:aware_of:{TARGET_NODE_ID}"
PREDICATE = "aware_of"
LABEL = "aware of"

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


def _initialize(root: Path, bundle) -> kernel.WorldInitializationResult:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
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
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id=BUNDLE_ID,
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )
    return initialize_world_from_contributions(
        root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _projection_request() -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus=WorldGraphProjectionFocus(kind="none"),
        admissibility="gm",
    )


def _edge_assertion(
    *,
    session_id: str,
    contribution_id: str,
    evidence_ref_id: str,
    source_artifact_id: str,
) -> kernel.GraphContributionAssertion:
    # Provenance uses manual_seed so store validation does not require
    # session evidence span refs; session_ids on the edge value are the
    # multi-session provenance under test.
    return kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        contribution_id=contribution_id,
        subject_node_id=SOURCE_NODE_ID,
        target_node_id=TARGET_NODE_ID,
        predicate=PREDICATE,
        label=LABEL,
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        evidence_ref_ids=[evidence_ref_id],
        temporal_scope={"session_id": session_id},
        value={
            "edge_id": EDGE_ID,
            "direction": "outbound",
            "source_domains": ["manual_seed"],
            "session_ids": [session_id],
            "source_domain": "manual_seed",
            "source_artifact_id": source_artifact_id,
            "source_artifacts": [
                {
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": f"graph-data://test/{source_artifact_id}",
                }
            ],
            "evidence_ref_ids": [evidence_ref_id],
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": f"test://{session_id}/{EDGE_ID}",
                }
            ],
        },
    )


def test_same_edge_from_two_sessions_projects_both_session_ids(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Publish the same edge from two sessions; projected relationship keeps both."""
    _initialize(tmp_path, loaded_bundle)

    first = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:multi-session-edge-s22",
        source_revision_id="multi-session-edge-s22",
        accepted_assertions=[
            _edge_assertion(
                session_id="session-22",
                contribution_id="contribution:pending",
                evidence_ref_id="evidence:test:multi-session-edge-s22",
                source_artifact_id="graph-native:test:multi-session-edge-s22",
            )
        ],
    )
    first_merge = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=first,
    )
    assert first_merge.published is True

    second = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:multi-session-edge-s25",
        source_revision_id="multi-session-edge-s25",
        accepted_assertions=[
            _edge_assertion(
                session_id="session-25",
                contribution_id="contribution:pending",
                evidence_ref_id="evidence:test:multi-session-edge-s25",
                source_artifact_id="graph-native:test:multi-session-edge-s25",
            )
        ],
    )
    second_merge = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=second,
    )
    assert second_merge.published is True

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    store_edge = store.edges[EDGE_ID]
    assert store_edge.session_ids == ["session-22", "session-25"]

    projection = kernel.project_world_graph(tmp_path, _projection_request())
    relationship = next(
        item for item in projection.relationships if item.edge_id == EDGE_ID
    )
    assert relationship.session_ids == ["session-22", "session-25"]
