"""Kernel world projection tests (PR007A)."""

from __future__ import annotations

import shutil
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
    assert battlefield.active_contribution_ids == ["contribution:022187fdefdf4557"]


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
    assert projection.query_context.revision_id == head_revision_id
    assert projection.query_context.matched_node_ids[0] == TRIPOD_ID


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
