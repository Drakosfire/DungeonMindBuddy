"""Service-boundary tests for the PR006D2 Eldyrwild bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.models.world_graph_bootstrap import (
    WorldGraphBootstrapConfirmRequest,
    WorldGraphBootstrapPrepareRequest,
)
from apps.live_control_server.services import world_graph_bootstrap as bootstrap
from apps.live_control_server.services.world_graph_bootstrap import (
    APPROVED_CAMPAIGN_ID,
    APPROVED_FOCUS_SESSION_ID,
    APPROVED_WORLD_ID,
    WorldGraphBootstrapError,
    build_api_contract,
    confirm_world_graph_bootstrap,
    get_world_graph_bootstrap_status,
    prepare_world_graph_bootstrap,
)

FIXTURE_PATH = Path("tests/fixtures/world_graph_bootstrap/api-contract-v1.json")


def _prepare(root: Path, actor: str = "gm"):
    return prepare_world_graph_bootstrap(
        WorldGraphBootstrapPrepareRequest(actor=actor),
        root=root,
    )


def _confirm(prepared, root: Path, *, actor: str = "gm", proposal_id: str | None = None, token: str | None = None):
    return confirm_world_graph_bootstrap(
        WorldGraphBootstrapConfirmRequest(
            actor=actor,
            proposal_id=proposal_id or prepared.proposal_id,
            confirm_token=token or prepared.confirm_token,
        ),
        root=root,
    )


def _publish_foreign_world(root: Path) -> None:
    baseline = kernel.build_empty_technical_baseline_store(
        APPROVED_CAMPAIGN_ID,
        APPROVED_FOCUS_SESSION_ID,
    )
    kernel.publish_world_revision(
        root,
        APPROVED_WORLD_ID,
        baseline,
        operation_ids=["foreign-world-operation"],
    )


def test_status_ready_exposes_review_projection_and_trust_boundary(tmp_path: Path) -> None:
    response = get_world_graph_bootstrap_status(root=tmp_path)

    assert response.state == "ready"
    assert response.bundle_valid is True
    assert response.review is not None
    assert response.review.summary.model_dump(mode="json") == {
        "contribution_count": 6,
        "node_count": 12,
        "relationship_count": 11,
        "attribute_count": 3,
        "accepted_assertion_count": 30,
        "support_count": 26,
        "evidence_count": 30,
        "source_artifact_count": 6,
        "source_domains": ["manual_seed", "recap", "statblock", "worldbuilding"],
        "focus_sessions": ["session-22", "session-23"],
    }
    tripod = next(
        node
        for node in response.review.nodes
        if node.node_id == "threat:tripod-null-calf"
    )
    assert tripod.classification == "gmAuthored"
    assert tripod.kind == "threat"
    attributes = {
        attribute.attribute: attribute for attribute in response.review.attributes
    }
    assert set(attributes) == {
        "battlefield_role",
        "challenge_expectation",
        "first_appearance",
    }
    assert attributes["first_appearance"].text == "Mireward north-gate pressure sequence."
    assert any(
        evidence.locator_status == "unverified"
        for evidence in response.review.evidence
        if evidence.source_domain == "recap"
    )
    assert "No /ingest UI is delivered by PR006D2." in response.review.trust_boundary
    assert response.trust_boundary.can_trust
    assert response.receipt is None


def test_status_and_prepare_do_not_write_production_root(tmp_path: Path) -> None:
    before = set(tmp_path.rglob("*"))
    status = get_world_graph_bootstrap_status(root=tmp_path)
    prepared = _prepare(tmp_path)
    after = set(tmp_path.rglob("*"))

    assert status.state == "ready"
    assert prepared.prepared is True
    assert before == after == set()


def test_prepare_is_deterministic_and_binds_content(tmp_path: Path) -> None:
    first = _prepare(tmp_path)
    second = _prepare(tmp_path)

    assert first.proposal_id == second.proposal_id
    assert first.confirm_token == second.confirm_token
    assert first.plan_digest == second.plan_digest
    assert (
        first.predicted_baseline_revision_id == second.predicted_baseline_revision_id
    )
    assert (
        first.predicted_initial_head_revision_id
        == second.predicted_initial_head_revision_id
    )
    assert len(first.confirm_token) > 256
    assert first.effects.predicted_revision_count == 7


def test_first_and_repeated_confirmation_are_truthful(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    first = _confirm(prepared, tmp_path)
    second = _confirm(prepared, tmp_path)

    assert first.published is True
    assert first.state == "active"
    assert first.receipt is not None
    assert first.receipt.node_count == 12
    assert first.receipt.edge_count == 11
    assert first.receipt.accepted_assertion_count == 30
    assert first.receipt.assertion_support_count == 26
    assert first.receipt.evidence_count == 30
    assert first.receipt.source_artifact_count == 6
    assert first.receipt.source_domains == [
        "manual_seed",
        "recap",
        "statblock",
        "worldbuilding",
    ]
    assert second.published is False
    assert second.state == "active"
    assert second.current_head_revision_id == first.current_head_revision_id


def test_confirm_reports_active_descendant_head_without_republishing(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    first = _confirm(prepared, tmp_path)
    _head, _revision, store = kernel.open_current_world_graph(
        tmp_path, APPROVED_WORLD_ID
    )
    kernel.publish_world_revision(
        tmp_path,
        APPROVED_WORLD_ID,
        store,
        operation_ids=["later-valid-contribution"],
        expected_parent_revision_id=first.current_head_revision_id,
    )

    response = _confirm(prepared, tmp_path)

    assert response.published is False
    assert response.state == "active_head_advanced"


def test_foreign_world_is_blocked_before_prepare_or_confirm(tmp_path: Path) -> None:
    _publish_foreign_world(tmp_path)

    with pytest.raises(WorldGraphBootstrapError) as exc_info:
        _prepare(tmp_path)

    assert exc_info.value.code == "blocked_existing_world"
    assert exc_info.value.status_code == 409
    assert exc_info.value.bootstrap_state == "blocked_existing_world"


def test_inconsistent_lineage_is_stable(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    first = _confirm(prepared, tmp_path)
    assert first.receipt is not None
    kernel.rollback_world_graph_head(
        tmp_path,
        APPROVED_WORLD_ID,
        first.receipt.baseline_revision_id,
    )

    status = get_world_graph_bootstrap_status(root=tmp_path)

    assert status.state == "inconsistent_lineage"
    with pytest.raises(WorldGraphBootstrapError) as exc_info:
        _confirm(prepared, tmp_path)
    assert exc_info.value.code == "inconsistent_lineage"


def test_actor_proposal_and_token_mismatches_fail_closed(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)

    with pytest.raises(WorldGraphBootstrapError) as actor_error:
        _confirm(prepared, tmp_path, actor="another-gm")
    assert actor_error.value.code == "actor_mismatch"

    with pytest.raises(WorldGraphBootstrapError) as proposal_error:
        _confirm(prepared, tmp_path, proposal_id="wrong-proposal")
    assert proposal_error.value.code == "proposal_mismatch"

    with pytest.raises(WorldGraphBootstrapError) as token_error:
        _confirm(prepared, tmp_path, token="0" * len(prepared.confirm_token))
    assert token_error.value.code == "stale_confirmation"


def test_corrupt_receipt_is_normalized(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    _confirm(prepared, tmp_path)
    receipt_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / APPROVED_WORLD_ID
        / "initialization"
        / "initial.json"
    )
    receipt_path.write_text("{not-json", encoding="utf-8")

    status = get_world_graph_bootstrap_status(root=tmp_path)

    assert status.state == "error"
    assert status.diagnostics[0].code == "corrupt_initialization_receipt"
    with pytest.raises(WorldGraphBootstrapError) as exc_info:
        _prepare(tmp_path)
    assert exc_info.value.code == "corrupt_initialization_receipt"
    assert "JSONDecodeError" not in json.dumps(status.model_dump(mode="json"))
    assert str(tmp_path) not in json.dumps(status.model_dump(mode="json"))


def test_invalid_bundle_takes_precedence_over_existing_world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _publish_foreign_world(tmp_path)
    monkeypatch.setattr(
        bootstrap,
        "_approved_bundle_path",
        lambda: tmp_path / "missing-approved-bundle",
    )

    status = get_world_graph_bootstrap_status(root=tmp_path)

    assert status.state == "invalid_bundle"
    assert status.bundle_valid is False
    assert status.diagnostics[0].code == "bundle_unavailable"


def test_serialized_responses_have_no_absolute_paths(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    response = _confirm(prepared, tmp_path)
    serialized = json.dumps(response.model_dump(mode="json", by_alias=True))

    assert str(tmp_path) not in serialized
    assert "/tmp/" not in serialized


def test_contract_fixture_is_generated_from_models() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert fixture == build_api_contract()
