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
    accepted_assertion_id_set_sha256,
    accepted_assertions_dump_sha256,
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


def _expected_hashes(contribution: kernel.GraphContribution) -> tuple[str, str]:
    accepted = list(contribution.accepted_assertions)
    return (
        accepted_assertion_id_set_sha256(accepted),
        accepted_assertions_dump_sha256(accepted),
    )


def _validate(contribution: kernel.GraphContribution) -> None:
    id_set_sha, dump_sha = _expected_hashes(contribution)
    _validate_repair_target(
        contribution,
        expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
        expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
        expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
        expected_accepted_assertion_id_set_sha256=id_set_sha,
        expected_accepted_assertions_dump_sha256=dump_sha,
        drop_subjects=DROP_SUBJECTS,
    )

def test_validate_repair_target_accepts_session24_target() -> None:
    _validate(_repair_target_contribution())


def test_validate_repair_target_rejects_campaign_scope_mismatch() -> None:
    contribution = _repair_target_contribution()
    contribution = contribution.model_copy(update={"campaign_scope": "other-campaign"})
    id_set_sha, dump_sha = _expected_hashes(contribution)
    with pytest.raises(ValueError, match="campaign_scope mismatch"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            expected_accepted_assertion_id_set_sha256=id_set_sha,
            expected_accepted_assertions_dump_sha256=dump_sha,
            drop_subjects=DROP_SUBJECTS,
        )


def test_validate_repair_target_rejects_missing_drop_subjects() -> None:
    contribution = _repair_target_contribution(drop_subjects=frozenset({"pc:baergrom"}))
    id_set_sha, dump_sha = _expected_hashes(contribution)
    with pytest.raises(ValueError, match="expected node assertions missing"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            expected_accepted_assertion_id_set_sha256=id_set_sha,
            expected_accepted_assertions_dump_sha256=dump_sha,
            drop_subjects=DROP_SUBJECTS,
        )


def test_validate_repair_target_rejects_source_revision_mismatch() -> None:
    contribution = _repair_target_contribution()
    contribution = contribution.model_copy(update={"source_revision_id": "sha256:wrong"})
    id_set_sha, dump_sha = _expected_hashes(contribution)
    with pytest.raises(ValueError, match="source_revision_id mismatch"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            expected_accepted_assertion_id_set_sha256=id_set_sha,
            expected_accepted_assertions_dump_sha256=dump_sha,
            drop_subjects=DROP_SUBJECTS,
        )


def test_validate_repair_target_rejects_assertion_id_body_mismatch() -> None:
    contribution = _repair_target_contribution()
    assertion = contribution.accepted_assertions[0]
    mutated = assertion.model_copy(
        update={"value": {**dict(assertion.value), "role": "npc"}}
    )
    contribution = contribution.model_copy(
        update={"accepted_assertions": [mutated, *contribution.accepted_assertions[1:]]}
    )
    id_set_sha, dump_sha = _expected_hashes(contribution)
    with pytest.raises(ValueError, match="assertion_id does not match body"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            expected_accepted_assertion_id_set_sha256=id_set_sha,
            expected_accepted_assertions_dump_sha256=dump_sha,
            drop_subjects=DROP_SUBJECTS,
        )


def test_validate_repair_target_rejects_extra_accepted_assertion() -> None:
    contribution = _repair_target_contribution()
    extra = _node_assertion("pc:extra")
    contribution = contribution.model_copy(
        update={
            "accepted_assertions": [
                *contribution.accepted_assertions,
                extra,
            ]
        }
    )
    id_set_sha, dump_sha = _expected_hashes(contribution)
    with pytest.raises(ValueError, match="accepted_assertion_id_set_sha256 mismatch"):
        _validate_repair_target(
            contribution,
            expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
            expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
            expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
            expected_accepted_assertion_id_set_sha256=_expected_hashes(
                _repair_target_contribution()
            )[0],
            expected_accepted_assertions_dump_sha256=dump_sha,
            drop_subjects=DROP_SUBJECTS,
        )


def test_validate_repair_target_accepts_live_session24_contribution_if_present() -> None:
    from scripts.supersede_session24_overlapping_pc_node_assertions import (
        DEFAULT_OLD_CONTRIBUTION_ID,
        DEFAULT_ROOT,
        DEFAULT_WORLD_ID,
        EXPECTED_ACCEPTED_ASSERTION_ID_SET_SHA256,
        EXPECTED_ACCEPTED_ASSERTIONS_DUMP_SHA256,
    )
    from graph_memory.world_supergraph.contribution_store import load_contribution_record

    path = (
        DEFAULT_ROOT
        / "graph_memory/worlds"
        / DEFAULT_WORLD_ID
        / "contributions"
        / f"{DEFAULT_OLD_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    if not path.is_file():
        pytest.skip(f"live contribution not present: {path}")
    old = load_contribution_record(DEFAULT_ROOT, DEFAULT_WORLD_ID, DEFAULT_OLD_CONTRIBUTION_ID)
    _validate_repair_target(
        old,
        expected_campaign_scope=EXPECTED_CAMPAIGN_SCOPE,
        expected_source_artifact_id=EXPECTED_SOURCE_ARTIFACT_ID,
        expected_source_revision_id=EXPECTED_SOURCE_REVISION_ID,
        expected_accepted_assertion_id_set_sha256=EXPECTED_ACCEPTED_ASSERTION_ID_SET_SHA256,
        expected_accepted_assertions_dump_sha256=EXPECTED_ACCEPTED_ASSERTIONS_DUMP_SHA256,
        drop_subjects=DROP_SUBJECTS,
    )
