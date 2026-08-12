"""Reviewed-source world initialization tests (CR02A / Kernel nano-commit 2)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import graph_memory.kernel as kernel
from graph_memory.kernel.reviewed_world_initialization import (
    REVIEWED_PLAN_SCHEMA,
    REVIEWED_RECEIPT_SCHEMA,
    SESSIONLESS_FOCUS_SESSION_ID,
    ReviewedWorldInitializationAttestation,
    ReviewedWorldInitializationError,
    ReviewedWorldInitializationPlan,
    compute_reviewed_initialization_plan_digest,
    initialize_reviewed_world,
    inspect_reviewed_world_initialization_state,
    read_reviewed_initialization_receipt,
)
from graph_memory.kernel.world_initialization import build_empty_technical_baseline_store
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.validate import validate_union_supergraph_store_payload

WORLD_ID = "hesta-apothecary"
CAMPAIGN_ID = "hesta-apothecary"
ACTOR = "gm"
PLAN_ID = "reviewed-init-plan:hesta-v1"
RUN_ID = "extraction-run:hesta-source-1"
SOURCE_ARTIFACT_ID = "source-artifact:hesta-notes"
SOURCE_REVISION_ID = "sha256:" + ("ab" * 32)
WORKSPACE_DOCUMENT_ID = "workspace-doc:hesta"
WORKSPACE_DOCUMENT_REVISION = "rev:workspace-hesta-1"
DECISION_DIGEST = "cd" * 32
NODE_ID = "npc:hesta"
FAKE_SESSION_PATTERNS = (
    re.compile(r"session-0\b"),
    re.compile(r"session-1\b"),
    re.compile(r"first-session\b"),
    re.compile(r"session-\d+\b"),
)


def _world_dir(root: Path) -> Path:
    return root / "graph_memory" / "worlds" / WORLD_ID


def _reviewed_receipt_path(root: Path) -> Path:
    return _world_dir(root) / "initialization" / "reviewed_initialization_receipt.json"


def _legacy_receipt_path(root: Path) -> Path:
    return _world_dir(root) / "initialization" / "initial.json"


def _attestation() -> ReviewedWorldInitializationAttestation:
    return ReviewedWorldInitializationAttestation(
        run_id=RUN_ID,
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_revision_id=SOURCE_REVISION_ID,
        workspace_document_id=WORKSPACE_DOCUMENT_ID,
        workspace_document_revision=WORKSPACE_DOCUMENT_REVISION,
        decision_digest=DECISION_DIGEST,
    )


def _make_contribution():
    evidence_ref_id = "evidence:hesta:intro"
    node = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=NODE_ID,
        label="Hesta",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=SOURCE_ARTIFACT_ID,
        value={
            "kind": "npc",
            "role": "ally",
            "source_domains": ["worldbuilding"],
            "aliases": ["Hesta"],
            "canon_state": "worldbuilding_draft",
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": SOURCE_ARTIFACT_ID,
                    "source_domain": "worldbuilding",
                    "locator": "span:hesta-intro",
                }
            ],
            "source_artifacts": [
                {
                    "source_artifact_id": SOURCE_ARTIFACT_ID,
                    "source_domain": "worldbuilding",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": f"graph-data://test/{SOURCE_ARTIFACT_ID}",
                }
            ],
        },
        evidence_ref_ids=[evidence_ref_id],
    )
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_revision_id=SOURCE_REVISION_ID,
        extraction_profile="worldbuilding_shepherds_flock_v0",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=[node],
        authored_by="live_control:reviewed_world_init_test",
    )


def _plan(contribution) -> ReviewedWorldInitializationPlan:
    return ReviewedWorldInitializationPlan(
        schema=REVIEWED_PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=SESSIONLESS_FOCUS_SESSION_ID,
        plan_id=PLAN_ID,
        contribution_id=contribution.contribution_id,
        contribution_payload_sha256=kernel.compute_contribution_payload_sha256(
            contribution
        ),
        approval_attestation=_attestation(),
    )


def _initialize(root: Path, contribution=None):
    contribution = contribution or _make_contribution()
    return (
        initialize_reviewed_world(
            root,
            plan=_plan(contribution),
            contribution=contribution,
            actor=ACTOR,
        ),
        contribution,
    )


def _assert_no_invented_sessions(payload: object) -> None:
    text = json.dumps(payload, sort_keys=True)
    for pattern in FAKE_SESSION_PATTERNS:
        assert pattern.search(text) is None, f"invented session token matched {pattern}"


def test_empty_focus_baseline_is_structurally_valid() -> None:
    store = build_empty_technical_baseline_store(
        CAMPAIGN_ID, SESSIONLESS_FOCUS_SESSION_ID
    )
    payload = store.model_dump(mode="json", by_alias=True)
    report = validate_union_supergraph_store_payload(payload)
    assert report["valid"] is True
    assert store.focus_session_id == ""
    _assert_no_invented_sessions(payload)


def test_reviewed_plan_rejects_invented_focus_session() -> None:
    contribution = _make_contribution()
    with pytest.raises(ValidationError, match="focus_session_id"):
        ReviewedWorldInitializationPlan(
            schema=REVIEWED_PLAN_SCHEMA,
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            focus_session_id="session-1",
            plan_id=PLAN_ID,
            contribution_id=contribution.contribution_id,
            contribution_payload_sha256=kernel.compute_contribution_payload_sha256(
                contribution
            ),
            approval_attestation=_attestation(),
        )


def test_initialize_reviewed_world_publishes_contribution_and_receipt(
    tmp_path: Path,
) -> None:
    result, contribution = _initialize(tmp_path)
    assert result.published is True
    assert result.outcome == "published"
    assert result.receipt is not None
    assert result.receipt.focus_session_id == ""
    assert result.receipt.schema_ == REVIEWED_RECEIPT_SCHEMA
    assert result.receipt.contribution_id == contribution.contribution_id
    assert result.receipt.plan_id == PLAN_ID
    assert result.receipt.run_id == RUN_ID

    assert _world_dir(tmp_path).is_dir()
    assert _reviewed_receipt_path(tmp_path).is_file()
    assert not _legacy_receipt_path(tmp_path).exists()

    head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    assert store.focus_session_id == ""
    assert NODE_ID in store.nodes
    assert head.head_revision_id == result.initial_head_revision_id

    index = __import__(
        "graph_memory.world_supergraph.contribution_store",
        fromlist=["load_contribution_index"],
    ).load_contribution_index(tmp_path, WORLD_ID)
    assert index.active_contribution_ids == [contribution.contribution_id]
    assert index.baseline_revision_id == result.baseline_revision_id

    receipt_payload = json.loads(
        _reviewed_receipt_path(tmp_path).read_text(encoding="utf-8")
    )
    assert "approved_bundle_merge_sha" not in receipt_payload
    assert "bundle_id" not in receipt_payload
    assert "bundle_digest" not in receipt_payload
    assert "approval_attestation" not in receipt_payload
    assert receipt_payload["focus_session_id"] == ""
    _assert_no_invented_sessions(receipt_payload)
    _assert_no_invented_sessions(store.model_dump(mode="json", by_alias=True))

    # Projection treats empty store focus as no session focus (non-user-visible).
    projection = kernel.project_world_graph(
        tmp_path,
        WorldGraphProjectionRequest(
            schema=PROJECTION_REQUEST_SCHEMA,
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            focus=WorldGraphProjectionFocus(kind="none", session_id=None),
        ),
    )
    dumped = projection.model_dump(mode="json", by_alias=True)
    _assert_no_invented_sessions(dumped)
    assert any(node.node_id == NODE_ID for node in projection.nodes)


def test_merge_failure_mid_staging_leaves_production_absent(tmp_path: Path) -> None:
    contribution = _make_contribution()
    with patch(
        "graph_memory.kernel.world_initialization.merge_contribution_to_revision",
        side_effect=RuntimeError("injected merge failure"),
    ):
        with pytest.raises(ReviewedWorldInitializationError) as exc_info:
            initialize_reviewed_world(
                tmp_path,
                plan=_plan(contribution),
                contribution=contribution,
                actor=ACTOR,
            )
    assert exc_info.value.outcome == "error"
    assert not _world_dir(tmp_path).exists()


def test_retry_same_plan_is_already_initialized(tmp_path: Path) -> None:
    first, contribution = _initialize(tmp_path)
    second = initialize_reviewed_world(
        tmp_path,
        plan=_plan(contribution),
        contribution=contribution,
        actor=ACTOR,
    )
    assert first.published is True
    assert second.published is False
    assert second.outcome == "already_initialized"
    assert second.state == "already_initialized"
    assert second.current_head_revision_id == first.current_head_revision_id

    index = __import__(
        "graph_memory.world_supergraph.contribution_store",
        fromlist=["load_contribution_index"],
    ).load_contribution_index(tmp_path, WORLD_ID)
    assert index.active_contribution_ids == [contribution.contribution_id]
    revisions = list((_world_dir(tmp_path) / "revisions").iterdir())
    # empty baseline + one contribution
    assert len([p for p in revisions if p.is_dir()]) == 2


def test_mismatched_plan_against_existing_receipt_is_blocked(tmp_path: Path) -> None:
    _first, contribution = _initialize(tmp_path)
    mismatched = ReviewedWorldInitializationPlan(
        schema=REVIEWED_PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id="",
        plan_id="reviewed-init-plan:other",
        contribution_id=contribution.contribution_id,
        contribution_payload_sha256=kernel.compute_contribution_payload_sha256(
            contribution
        ),
        approval_attestation=_attestation().model_copy(
            update={"decision_digest": "ef" * 32}
        ),
    )
    state = inspect_reviewed_world_initialization_state(
        tmp_path, world_id=WORLD_ID, plan=mismatched
    )
    assert state == "blocked"
    with pytest.raises(ReviewedWorldInitializationError) as exc_info:
        initialize_reviewed_world(
            tmp_path,
            plan=mismatched,
            contribution=contribution,
            actor=ACTOR,
        )
    assert exc_info.value.outcome == "blocked"
    assert exc_info.value.state == "blocked"


def test_reviewed_receipt_has_no_bundle_attestation_fields(tmp_path: Path) -> None:
    result, contribution = _initialize(tmp_path)
    receipt = result.receipt
    assert receipt is not None
    payload = receipt.model_dump(mode="json", by_alias=True)
    forbidden = {
        "approved_bundle_merge_sha",
        "bundle_id",
        "bundle_digest",
        "approval_attestation",
    }
    assert forbidden.isdisjoint(payload.keys())
    reloaded = read_reviewed_initialization_receipt(tmp_path, WORLD_ID)
    assert reloaded is not None
    assert reloaded.focus_session_id == ""
    assert reloaded.decision_digest == DECISION_DIGEST
    assert reloaded.plan_digest == compute_reviewed_initialization_plan_digest(
        _plan(contribution)
    )


def test_legacy_bundle_init_still_works(tmp_path: Path) -> None:
    """Smoke that factoring did not break certified-bundle initialization."""
    from graph_memory.contribution_bundles import load_contribution_bundle
    from graph_memory.kernel.world_initialization import (
        initialize_world_from_contributions,
    )
    from graph_memory.kernel.world_initialization_models import (
        PLAN_SCHEMA,
        WorldInitializationApprovalAttestation,
        WorldInitializationContribution,
        WorldInitializationPlan,
    )

    repo_root = Path(__file__).resolve().parents[1]
    bundle_path = (
        repo_root
        / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
    )
    bundle = load_contribution_bundle(bundle_path)
    ordered = [
        WorldInitializationContribution(
            contribution_id=item.contribution_id,
            payload_sha256=kernel.compute_contribution_payload_sha256(item),
        )
        for item in bundle.contributions
    ]
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id="eldyrwild",
        campaign_id="longmont-c2",
        focus_session_id="session-23",
        ordered_contributions=ordered,
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id="eldyrwild-longmont-c2-initial-v1",
            bundle_digest=(
                "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
            ),
            approved_bundle_merge_sha="65ae001e0852d827ecd680200a965a576c705b1d",
        ),
    )
    result = initialize_world_from_contributions(
        tmp_path,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )
    assert result.published is True
    assert result.state == "active"
    legacy = kernel.read_initialization_receipt(tmp_path, "eldyrwild")
    assert legacy is not None
    assert legacy.approval_attestation.approved_bundle_merge_sha.startswith("65ae")
    assert not (
        tmp_path
        / "graph_memory"
        / "worlds"
        / "eldyrwild"
        / "initialization"
        / "reviewed_initialization_receipt.json"
    ).exists()
