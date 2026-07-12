"""Kernel world initialization tests (PR006D1)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import graph_memory.kernel as kernel
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationError,
    WorldInitializationPlan,
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

ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


def _world_dir(root: Path) -> Path:
    return root / "graph_memory" / "worlds" / WORLD_ID


def _receipt_path(root: Path) -> Path:
    return _world_dir(root) / "initialization" / "initial.json"


def _initializing_root(root: Path) -> Path:
    return root / "graph_memory" / ".initializing"


def _revision_ids(root: Path) -> list[str]:
    revisions_dir = _world_dir(root) / "revisions"
    if not revisions_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in revisions_dir.iterdir()
        if path.is_dir() and path.name.startswith("rev:")
    )


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


def _attestation() -> WorldInitializationApprovalAttestation:
    return WorldInitializationApprovalAttestation(
        bundle_id=BUNDLE_ID,
        bundle_digest=BUNDLE_DIGEST,
        approved_bundle_merge_sha=APPROVED_MERGE_SHA,
    )


def _plan(
    bundle=None,
    *,
    contribution_ids: list[str] | None = None,
    world_id: str = WORLD_ID,
    campaign_id: str = CAMPAIGN_ID,
    focus_session_id: str = FOCUS_SESSION_ID,
) -> WorldInitializationPlan:
    ids = list(contribution_ids or ORDERED_CONTRIBUTION_IDS)
    if bundle is None:
        ordered_contributions = [
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256="0" * 64,
            )
            for contribution_id in ids
        ]
    else:
        by_id = {item.contribution_id: item for item in bundle.contributions}
        ordered_contributions = [
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ids
        ]
    return WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=world_id,
        campaign_id=campaign_id,
        focus_session_id=focus_session_id,
        ordered_contributions=ordered_contributions,
        approval_attestation=_attestation(),
    )


def _initialize(root: Path, bundle) -> kernel.WorldInitializationResult:
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def test_empty_baseline_store_is_structurally_valid() -> None:
    store = kernel.build_empty_technical_baseline_store(CAMPAIGN_ID, FOCUS_SESSION_ID)
    assert store.schema == "dmb_union_supergraph_store_v0"
    assert store.version == "0.1"
    assert store.nodes == {}
    assert store.edges == {}


def test_initialize_publishes_rebuildable_world(tmp_path: Path, loaded_bundle) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    assert result.published is True
    assert result.state == "active"
    assert result.receipt is not None
    assert result.receipt.plan_binding_verified is True
    assert result.receipt.approval_attestation.bundle_digest == BUNDLE_DIGEST
    assert result.baseline_revision_id == result.receipt.baseline_revision_id
    assert result.initial_head_revision_id == result.current_head_revision_id

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    assert len(store.nodes) > 0
    assert len(store.edges) > 0
    assert len(store.assertion_support) > 0
    assert len(store.evidence) > 0

    revision_ids = _revision_ids(tmp_path)
    assert len(revision_ids) == 1 + len(ORDERED_CONTRIBUTION_IDS)

    index = __import__(
        "graph_memory.world_supergraph.contribution_store",
        fromlist=["load_contribution_index"],
    ).load_contribution_index(tmp_path, WORLD_ID)
    assert index.baseline_revision_id == result.baseline_revision_id
    assert index.active_contribution_ids == ORDERED_CONTRIBUTION_IDS

    rebuild = kernel.rebuild_from_contributions(tmp_path, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in rebuild.diagnostics

    receipt = kernel.read_initialization_receipt(tmp_path, WORLD_ID)
    assert receipt is not None
    assert receipt.focus_session_id == FOCUS_SESSION_ID
    assert receipt.plan_digest == kernel.compute_initialization_plan_digest(
        _plan(loaded_bundle)
    )
    assert receipt.ordered_contributions == _plan(loaded_bundle).ordered_contributions
    assert receipt.rebuild_equivalent is True
    assert receipt.world_integrity_ok is True
    assert receipt.contribution_integrity_ok is True


def test_second_initialize_is_idempotent_no_op(tmp_path: Path, loaded_bundle) -> None:
    first = _initialize(tmp_path, loaded_bundle)
    second = _initialize(tmp_path, loaded_bundle)

    assert first.published is True
    assert second.published is False
    assert second.state == "active"
    assert second.current_head_revision_id == first.current_head_revision_id
    assert len(_revision_ids(tmp_path)) == 7


def test_empty_contribution_input_fails(tmp_path: Path) -> None:
    with pytest.raises(WorldInitializationError, match="non-empty"):
        initialize_world_from_contributions(
            tmp_path,
            plan=_plan(),
            contributions=[],
            actor=ACTOR,
        )


def test_mismatched_contribution_world_ids_fail(tmp_path: Path, loaded_bundle) -> None:
    contributions = list(loaded_bundle.contributions)
    contributions[0] = contributions[0].model_copy(update={"world_id": "other-world"})
    with pytest.raises(WorldInitializationError, match="world_id"):
        initialize_world_from_contributions(
            tmp_path,
            plan=_plan(loaded_bundle),
            contributions=contributions,
            actor=ACTOR,
        )


def test_plan_contribution_binding_mismatch_fails(
    tmp_path: Path, loaded_bundle
) -> None:
    plan = _plan(loaded_bundle, contribution_ids=ORDERED_CONTRIBUTION_IDS[::-1])
    with pytest.raises(WorldInitializationError, match="not bound"):
        initialize_world_from_contributions(
            tmp_path,
            plan=plan,
            contributions=list(loaded_bundle.contributions),
            actor=ACTOR,
        )


def test_plan_rejects_tampered_accepted_assertion_with_same_id(
    tmp_path: Path, loaded_bundle
) -> None:
    original = loaded_bundle.contributions[0]
    tampered_assertion = original.accepted_assertions[0].model_copy(
        update={"label": "tampered without changing assertion id"}
    )
    tampered = original.model_copy(
        update={
            "accepted_assertions": [
                tampered_assertion,
                *original.accepted_assertions[1:],
            ]
        }
    )

    with pytest.raises(WorldInitializationError, match="payload digest"):
        initialize_world_from_contributions(
            tmp_path,
            plan=_plan(loaded_bundle),
            contributions=[tampered, *loaded_bundle.contributions[1:]],
            actor=ACTOR,
        )


@pytest.mark.parametrize("field", ["rejected_assertions", "unresolved_mentions"])
def test_plan_rejects_tampered_nonaccepted_content(
    tmp_path: Path, loaded_bundle, field: str
) -> None:
    original = loaded_bundle.contributions[0]
    if field == "rejected_assertions":
        content = [
            original.accepted_assertions[0].model_copy(
                update={"acceptance_state": "rejected"}
            )
        ]
    else:
        content = [
            kernel.ContributionIdentityMention(
                mention_id="mention:tampered",
                label="tampered",
                object_kind="npc",
                identity_resolution_outcome="ambiguous",
            )
        ]
    tampered = original.model_copy(update={field: content})

    with pytest.raises(WorldInitializationError, match="payload digest"):
        initialize_world_from_contributions(
            tmp_path,
            plan=_plan(loaded_bundle),
            contributions=[tampered, *loaded_bundle.contributions[1:]],
            actor=ACTOR,
        )


def test_identity_decision_references_are_rejected_explicitly(
    tmp_path: Path, loaded_bundle
) -> None:
    original = loaded_bundle.contributions[0]
    tampered = original.model_copy(
        update={"identity_decision_ids": ["decision:unsupported"]}
    )
    entries = list(_plan(loaded_bundle).ordered_contributions)
    entries[0] = entries[0].model_copy(
        update={
            "payload_sha256": kernel.compute_contribution_payload_sha256(tampered)
        }
    )

    with pytest.raises(WorldInitializationError, match="identity decision"):
        initialize_world_from_contributions(
            tmp_path,
            plan=_plan(loaded_bundle).model_copy(
                update={"ordered_contributions": entries}
            ),
            contributions=[tampered, *loaded_bundle.contributions[1:]],
            actor=ACTOR,
        )


def test_plan_schema_is_literal_validated() -> None:
    with pytest.raises(ValidationError):
        WorldInitializationPlan(
            schema="wrong-schema",
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            focus_session_id=FOCUS_SESSION_ID,
            ordered_contributions=[],
            approval_attestation=_attestation(),
        )


def test_foreign_head_without_receipt_fails_closed(
    tmp_path: Path, loaded_bundle
) -> None:
    baseline = kernel.build_empty_technical_baseline_store(CAMPAIGN_ID, FOCUS_SESSION_ID)
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        baseline,
        operation_ids=["foreign-baseline"],
    )

    with pytest.raises(WorldInitializationError) as exc_info:
        _initialize(tmp_path, loaded_bundle)
    assert exc_info.value.state == "blocked_existing_world"
    assert _world_dir(tmp_path).exists()
    assert kernel.read_initialization_receipt(tmp_path, WORLD_ID) is None
    assert len(_revision_ids(tmp_path)) == 1


def test_different_bundle_receipt_fails_closed(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    receipt_path = _receipt_path(tmp_path)
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["approval_attestation"]["bundle_digest"] = "deadbeef" * 8
    receipt_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(WorldInitializationError) as exc_info:
        _initialize(tmp_path, loaded_bundle)
    assert exc_info.value.state == "blocked_existing_world"


def test_idempotency_requires_plan_order_campaign_and_focus_match(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)

    reordered_plan = _plan(
        loaded_bundle,
        contribution_ids=ORDERED_CONTRIBUTION_IDS[::-1],
    )
    with pytest.raises(WorldInitializationError) as reordered:
        initialize_world_from_contributions(
            tmp_path,
            plan=reordered_plan,
            contributions=list(reversed(loaded_bundle.contributions)),
            actor=ACTOR,
        )
    assert reordered.value.state == "blocked_existing_world"

    for changed_plan in (
        _plan(loaded_bundle, campaign_id="other-campaign"),
        _plan(loaded_bundle, focus_session_id="session-other"),
    ):
        with pytest.raises(WorldInitializationError) as changed:
            initialize_world_from_contributions(
                tmp_path,
                plan=changed_plan,
                contributions=list(loaded_bundle.contributions),
                actor=ACTOR,
            )
        assert changed.value.state == "blocked_existing_world"


def test_descendant_head_is_active_head_advanced(
    tmp_path: Path, loaded_bundle
) -> None:
    first = _initialize(tmp_path, loaded_bundle)
    assert first.receipt is not None
    _head, _rev, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    advanced = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["post-init-noop-publish"],
        expected_parent_revision_id=first.current_head_revision_id,
    )
    state = kernel.inspect_world_initialization_state(
        tmp_path,
        world_id=WORLD_ID,
        plan=_plan(loaded_bundle),
    )
    assert state == "active_head_advanced"
    second = _initialize(tmp_path, loaded_bundle)
    assert second.published is False
    assert second.state == "active_head_advanced"
    assert second.current_head_revision_id == advanced.revision.revision_id


def test_rollback_before_initialized_head_is_inconsistent(
    tmp_path: Path, loaded_bundle
) -> None:
    first = _initialize(tmp_path, loaded_bundle)
    assert first.baseline_revision_id is not None
    kernel.rollback_world_graph_head(
        tmp_path,
        WORLD_ID,
        first.baseline_revision_id,
    )
    state = kernel.inspect_world_initialization_state(
        tmp_path,
        world_id=WORLD_ID,
        plan=_plan(loaded_bundle),
    )
    assert state == "inconsistent_lineage"
    with pytest.raises(WorldInitializationError) as exc_info:
        _initialize(tmp_path, loaded_bundle)
    assert exc_info.value.state == "inconsistent_lineage"


def test_merge_failure_at_first_contribution_leaves_production_absent(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization.merge_contribution_to_revision",
        side_effect=RuntimeError("injected merge failure at one"),
    ):
        with pytest.raises(WorldInitializationError):
            _initialize(tmp_path, loaded_bundle)
    assert not _world_dir(tmp_path).exists()


def test_merge_failure_at_third_contribution_leaves_production_absent(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    original_merge = kernel.merge_contribution_to_revision
    calls = {"count": 0}

    def failing_merge(root, *, world_id, contribution, expected_parent_revision_id=None):
        calls["count"] += 1
        if calls["count"] == 3:
            raise RuntimeError("injected merge failure")
        return original_merge(
            root,
            world_id=world_id,
            contribution=contribution,
            expected_parent_revision_id=expected_parent_revision_id,
        )

    with patch(
        "graph_memory.kernel.world_initialization.merge_contribution_to_revision",
        side_effect=failing_merge,
    ):
        with pytest.raises(WorldInitializationError):
            _initialize(tmp_path, loaded_bundle)

    assert not _world_dir(tmp_path).exists()
    initializing_root = _initializing_root(tmp_path)
    if initializing_root.exists():
        assert list(initializing_root.iterdir()) == []


def test_merge_failure_at_sixth_contribution_leaves_production_absent(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    original_merge = kernel.merge_contribution_to_revision
    calls = {"count": 0}

    def failing_merge(root, *, world_id, contribution, expected_parent_revision_id=None):
        calls["count"] += 1
        if calls["count"] == 6:
            raise RuntimeError("injected merge failure at six")
        return original_merge(
            root,
            world_id=world_id,
            contribution=contribution,
            expected_parent_revision_id=expected_parent_revision_id,
        )

    with patch(
        "graph_memory.kernel.world_initialization.merge_contribution_to_revision",
        side_effect=failing_merge,
    ):
        with pytest.raises(WorldInitializationError):
            _initialize(tmp_path, loaded_bundle)
    assert not _world_dir(tmp_path).exists()


def test_baseline_publish_failure_leaves_production_absent(
    tmp_path: Path, loaded_bundle
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization.publish_world_revision",
        side_effect=RuntimeError("injected baseline failure"),
    ):
        with pytest.raises(WorldInitializationError):
            _initialize(tmp_path, loaded_bundle)
    assert not _world_dir(tmp_path).exists()


def test_rebuild_failure_leaves_production_absent(
    tmp_path: Path, loaded_bundle
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization.rebuild_from_contributions",
        side_effect=RuntimeError("injected rebuild failure"),
    ):
        with pytest.raises(WorldInitializationError):
            _initialize(tmp_path, loaded_bundle)
    assert not _world_dir(tmp_path).exists()


def test_world_integrity_failure_leaves_production_absent(
    tmp_path: Path, loaded_bundle
) -> None:
    class FakeHealth:
        load_ok = False
        validation_ok = False
        errors = ["injected integrity failure"]

    with patch(
        "graph_memory.kernel.world_initialization.build_world_graph_integrity_report",
        return_value=FakeHealth(),
    ):
        with pytest.raises(WorldInitializationError, match="world integrity"):
            _initialize(tmp_path, loaded_bundle)
    assert not _world_dir(tmp_path).exists()


def test_rename_failure_before_promotion_leaves_production_absent(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization.os.rename",
        side_effect=OSError("injected"),
    ):
        with pytest.raises(WorldInitializationError):
            _initialize(tmp_path, loaded_bundle)

    assert not _world_dir(tmp_path).exists()


def test_receipt_failure_before_promotion_leaves_production_absent(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization._write_initialization_receipt",
        side_effect=RuntimeError("injected receipt failure"),
    ):
        with pytest.raises(WorldInitializationError):
            _initialize(tmp_path, loaded_bundle)

    assert not _world_dir(tmp_path).exists()


def test_cleanup_failure_after_promotion_still_returns_published(
    tmp_path: Path, loaded_bundle
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization._cleanup_staging",
        side_effect=RuntimeError("injected post-promotion cleanup failure"),
    ):
        result = _initialize(tmp_path, loaded_bundle)

    assert result.published is True
    assert result.state == "active"
    assert _world_dir(tmp_path).exists()
    assert any("post_promotion_cleanup_failed" in item for item in result.diagnostics)


def test_post_promotion_head_read_is_not_required(
    tmp_path: Path, loaded_bundle
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization.open_world_graph_head",
        side_effect=RuntimeError("injected post-promotion read failure"),
    ):
        result = _initialize(tmp_path, loaded_bundle)

    assert result.published is True
    assert result.receipt is not None
    assert result.current_head_revision_id == result.receipt.initial_head_revision_id
    assert _world_dir(tmp_path).exists()


def test_post_promotion_diagnostic_failure_still_returns_published(
    tmp_path: Path, loaded_bundle
) -> None:
    with patch(
        "graph_memory.kernel.world_initialization._best_effort_diagnostic",
        side_effect=RuntimeError("injected diagnostic failure"),
    ):
        result = _initialize(tmp_path, loaded_bundle)

    assert result.published is True
    assert result.state == "active"
    assert _world_dir(tmp_path).exists()
