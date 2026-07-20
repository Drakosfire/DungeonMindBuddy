"""Unit tests for Session 24 PC overlap repair script guards."""

from __future__ import annotations

import pytest

import graph_memory.kernel as kernel
from scripts.supersede_session24_overlapping_pc_node_assertions import (
    DROP_SUBJECTS,
    EXPECTED_CAMPAIGN_SCOPE,
    EXPECTED_SOURCE_ARTIFACT_ID,
    EXPECTED_SOURCE_REVISION_ID,
    _validate_repair_target,
)


def _node_assertion(subject_node_id: str) -> kernel.GraphContributionAssertion:
    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=subject_node_id,
        label=subject_node_id.split(":", 1)[-1],
        campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
        source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
        value={"kind": "pc", "role": "pc", "aliases": [subject_node_id.split(":", 1)[-1]]},
    )


def _repair_target_contribution(
    *,
    drop_subjects: frozenset[str] = DROP_SUBJECTS,
) -> kernel.GraphContribution:
    return kernel.create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
        source_revision_id=EXPECTED_SOURCE_REVISION_ID,
        campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
        accepted_assertions=[_node_assertion(subject) for subject in sorted(drop_subjects)],
    )


def test_validate_repair_target_accepts_session24_target() -> None:
    _validate_repair_target(
        _repair_target_contribution(),
        expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
        expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
        expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
        drop_subjects=DROP_SUBJECTS,
    )


def test_validate_repair_target_rejects_campaign_scope_mismatch() -> None:
    contribution = _repair_target_contribution()
    contribution = contribution.model_copy(update={"campaign_scope": "other-campaign"})
    with pytest.raises(ValueError, match="campaign_scope mismatch"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            drop_subjects=DROP_SUBJECTS,
        )


def test_validate_repair_target_rejects_missing_drop_subjects() -> None:
    contribution = _repair_target_contribution(drop_subjects=frozenset({"pc:baergrom"}))
    with pytest.raises(ValueError, match="expected node assertions missing"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            drop_subjects=DROP_SUBJECTS,
        )


def test_validate_repair_target_rejects_source_revision_mismatch() -> None:
    contribution = _repair_target_contribution()
    contribution = contribution.model_copy(update={"source_revision_id": "sha256:wrong"})
    with pytest.raises(ValueError, match="source_revision_id mismatch"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            drop_subjects=DROP_SUBJECTS,
        )
