from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import json
from uuid import uuid4

import psycopg
import pytest

from application_state.cli import _current_and_head
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.ingest.service import (
    RecapSemanticBasisV1,
    RecapSemanticBasisV2,
    RecapSemanticBasisV3,
    RecapSemanticBasisV4,
    RecapSemanticBasisV6,
    RecapSemanticDispositionCommandV1,
    create_extraction_run,
    get_extraction_run,
    inspect_ingest_authority,
    list_extraction_runs,
    lookup_extraction_run_by_candidate_component,
    record_recap_semantic_disposition,
    supersede_extraction_run,
    update_extraction_run,
)
from application_state.ingest import repository as ingest_repo
from application_state.unit_of_work import unit_of_work
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _run(*, run_id: str | None = None, **overrides) -> ExtractionRun:
    now = "2026-09-02T18:00:00Z"
    payload = {
        "run_id": run_id or f"er_{uuid4().hex[:12]}",
        "source_artifact_id": "sa_world_1",
        "source_domain": "worldbuilding",
        "status": ExtractionRunStatus.DRAFT,
        "revision": 1,
        "campaign_id": "eldyrwild",
        "session_id": None,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(overrides)
    return ExtractionRun.model_validate(payload)


def _review_components() -> dict[str, ExtractionRunComponentRef]:
    return {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri="repo://source.md",
            sha256="a" * 64,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri="repo://spans.json",
            sha256="b" * 64,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri="repo://graph.json",
            sha256="c" * 64,
        ),
    }


def _recap_basis_and_pair(application_state_dsn: str):
    parent_components = _review_components()
    parent_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://parent.json", sha256="c" * 64,
    )
    child_components = dict(parent_components)
    child_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://child.json", sha256="d" * 64,
    )
    parent = _run(
        run_id="recap_parent", source_artifact_id="artifact:recap:c:s:source",
        source_domain="recap", session_id="s", campaign_id="c",
        profile_id="recap_category_v1@1.0", status=ExtractionRunStatus.REVIEWABLE,
        components=parent_components,
    )
    basis = RecapSemanticBasisV1(
        parent_run_id=parent.run_id, parent_candidate_sha256="c" * 64,
        correction_digest="e" * 64, child_run_id="recap_child",
        candidate_uri="repo://child.json", candidate_sha256="d" * 64,
        source_artifact_id=parent.source_artifact_id,
        source_uri="repo://source.md", source_revision_sha256="a" * 64,
        span_index_uri="repo://spans.json", span_index_sha256="b" * 64,
        profile_id="recap_category_v1@1.0", profile_version="1.0",
        campaign_id="c", session_id="s",
    )
    child = parent.model_copy(deep=True, update={
        "run_id": "recap_child", "components": child_components,
        "lineage": {
            "derivation": "operator_recap_literal_evidence_correction_v1",
            "parent_run_id": parent.run_id,
            "parent_candidate_sha256": "c" * 64,
            "correction_digest": "e" * 64,
            "semantic_disposition": {
                "version": 1, "state": "held", "basis_sha256": basis.digest(),
                "hold_code": "s27_semantic_selection", "hold_ref": "review:s27",
            },
        },
    })
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, parent)
        ingest_repo.insert_run(conn, child)
    return parent, child, basis


def test_exact_candidate_lookup_covers_all_statuses_and_domains(application_state_dsn: str) -> None:
    assert lookup_extraction_run_by_candidate_component(
        uri="repo://graph.json", sha256="c" * 64
    ).kind == "not_found"
    world = _run(
        run_id="world_draft", components=_review_components(),
        status=ExtractionRunStatus.DRAFT,
    )
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, world)
    found = lookup_extraction_run_by_candidate_component(
        uri="repo://graph.json", sha256="sha256:" + "c" * 64
    )
    assert found.kind == "unique" and found.run.run_id == "world_draft"
    rejected = _run(
        run_id="world_rejected", components=_review_components(),
        status=ExtractionRunStatus.REJECTED,
    )
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, rejected)
    assert lookup_extraction_run_by_candidate_component(
        uri="repo://graph.json", sha256="c" * 64
    ).kind == "ambiguous"
    assert lookup_extraction_run_by_candidate_component(
        uri="repo://other.json", sha256="c" * 64
    ).kind == "not_found"


def test_recap_disposition_cas_preserves_run_and_exact_retry(application_state_dsn: str) -> None:
    parent, child, basis = _recap_basis_and_pair(application_state_dsn)
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:1", reviewer_id="local_operator"
    )
    accepted = record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision
    )
    assert accepted.revision == child.revision + 1
    assert accepted.status == child.status
    assert accepted.components == child.components
    assert accepted.source_artifact_id == child.source_artifact_id
    assert accepted.source_domain == child.source_domain
    assert accepted.profile_id == child.profile_id
    assert accepted.campaign_id == child.campaign_id
    assert accepted.session_id == child.session_id
    assert accepted.diagnostics == child.diagnostics
    assert accepted.superseded_by_run_id == child.superseded_by_run_id
    assert accepted.supersedes_run_id == child.supersedes_run_id
    receipt = accepted.lineage["semantic_disposition"]
    assert receipt["state"] == "accepted"
    assert receipt["basis_sha256"] == basis.digest()
    assert receipt["hold_code"] == "s27_semantic_selection"
    assert receipt["from_revision"] == child.revision
    assert receipt["decided_at"]
    assert record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision
    ) == accepted
    assert get_extraction_run(parent.run_id) == parent
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision, basis=basis,
            decision=decision.model_copy(update={"state": "rejected"}),
        )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=accepted.revision, basis=basis, decision=decision
        )


def test_semantic_candidate_basis_cas_is_distinct_and_single_use(application_state_dsn: str) -> None:
    parent_components = _review_components()
    parent_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://candidate-parent.json", sha256="c" * 64,
    )
    child_components = dict(parent_components)
    child_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://candidate-child.json", sha256="d" * 64,
    )
    manifest = {
        "schema": "dmb_recap_semantic_candidate_manifest_v1",
        "node_description_replacements": [{
            "node_id": "node:mira", "original_description": "old",
            "replacement_description": "new",
        }],
        "omitted_edge_ids": ["edge-1"],
    }
    manifest_sha = hashlib.sha256((json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode()).hexdigest()
    parent = _run(
        run_id="candidate_parent", source_artifact_id="artifact:recap:c:s:source",
        source_domain="recap", session_id="s", campaign_id="c",
        profile_id="recap_category_v1@1.0", status=ExtractionRunStatus.REVIEWABLE,
        components=parent_components,
    )
    basis = RecapSemanticBasisV2(
        parent_run_id=parent.run_id, parent_candidate_sha256="c" * 64,
        manifest_sha256=manifest_sha, child_run_id="candidate_child",
        candidate_uri="repo://candidate-child.json", candidate_sha256="d" * 64,
        source_artifact_id=parent.source_artifact_id,
        source_uri="repo://source.md", source_revision_sha256="a" * 64,
        span_index_uri="repo://spans.json", span_index_sha256="b" * 64,
        profile_id="recap_category_v1@1.0", profile_version="1.0",
        campaign_id="c", session_id="s",
    )
    child = parent.model_copy(deep=True, update={
        "run_id": "candidate_child", "components": child_components,
        "lineage": {
            "derivation": "operator_recap_semantic_candidate_correction_v1",
            "parent_run_id": parent.run_id,
            "parent_candidate_sha256": "c" * 64,
            "manifest_sha256": manifest_sha,
            "semantic_candidate_manifest": manifest,
            "semantic_disposition": {
                "version": 1, "state": "held", "basis_sha256": basis.digest(),
            },
        },
    })
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, parent)
        ingest_repo.insert_run(conn, child)
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:candidate",
        reviewer_id="local_operator",
    )
    accepted = record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision
    )
    assert accepted.revision == child.revision + 1
    assert accepted.components == child.components
    assert accepted.lineage["semantic_candidate_manifest"] == manifest
    assert record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision
    ) == accepted
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision, basis=basis,
            decision=decision.model_copy(update={"state": "rejected"}),
        )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=accepted.revision, basis=basis,
            decision=decision,
        )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision,
            basis=basis.model_copy(update={"manifest_sha256": "f" * 64}),
            decision=decision,
        )


def test_semantic_action_basis_v3_cas_and_version_seal(application_state_dsn: str) -> None:
    parent_components = _review_components()
    parent_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://action-parent.json", sha256="c" * 64,
    )
    child_components = dict(parent_components)
    child_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://action-child.json", sha256="d" * 64,
    )
    manifest = {
        "schema": "dmb_recap_semantic_candidate_manifest_v2",
        "node_description_replacements": [], "omitted_edge_ids": [],
        "session_action_replacements": [{
            "node_id": "node:mira", "action_index": 1,
            "expected_old_text": "wrong", "replacement_text": "right",
        }],
    }
    manifest_sha = hashlib.sha256((json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode()).hexdigest()
    parent = _run(
        run_id="action_parent", source_artifact_id="artifact:recap:c:s:source",
        source_domain="recap", session_id="s", campaign_id="c",
        profile_id="recap_category_v1@1.0", status=ExtractionRunStatus.REVIEWABLE,
        components=parent_components,
    )
    basis = RecapSemanticBasisV3(
        parent_run_id=parent.run_id, parent_candidate_sha256="c" * 64,
        manifest_sha256=manifest_sha, child_run_id="action_child",
        candidate_uri="repo://action-child.json", candidate_sha256="d" * 64,
        source_artifact_id=parent.source_artifact_id,
        source_uri="repo://source.md", source_revision_sha256="a" * 64,
        span_index_uri="repo://spans.json", span_index_sha256="b" * 64,
        profile_id="recap_category_v1@1.0", profile_version="1.0",
        campaign_id="c", session_id="s",
        derivation="operator_recap_semantic_candidate_correction_v2",
        manifest_schema="dmb_recap_semantic_candidate_manifest_v2",
    )
    child = parent.model_copy(deep=True, update={
        "run_id": "action_child", "components": child_components,
        "lineage": {
            "derivation": basis.derivation, "parent_run_id": parent.run_id,
            "parent_candidate_sha256": "c" * 64,
            "manifest_sha256": manifest_sha, "semantic_candidate_manifest": manifest,
            "semantic_disposition": {"version": 1, "state": "held", "basis_sha256": basis.digest()},
        },
    })
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, parent)
        ingest_repo.insert_run(conn, child)
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:action", reviewer_id="local_operator",
    )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision,
            basis=basis.model_copy(update={"manifest_schema": "dmb_recap_semantic_candidate_manifest_v1"}),
            decision=decision,
        )
    accepted = record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision,
    )
    assert accepted.revision == child.revision + 1
    assert accepted.components == child.components
    assert accepted.lineage["semantic_candidate_manifest"] == manifest
    assert record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision,
    ) == accepted
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision, basis=basis,
            decision=decision.model_copy(update={"state": "rejected"}),
        )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=accepted.revision, basis=basis,
            decision=decision,
        )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision,
            basis=basis.model_copy(update={"manifest_sha256": "f" * 64}),
            decision=decision,
        )


def test_semantic_edge_tuple_basis_v4_cas_and_manifest_allowlist(
    application_state_dsn: str,
) -> None:
    parent_components = _review_components()
    parent_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://tuple-parent.json", sha256="c" * 64,
    )
    child_components = dict(parent_components)
    child_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://tuple-child.json", sha256="d" * 64,
    )
    operation = {
        "edge_id": "edge-1",
        "expected_tuple": {
            "from_node_id": "chamber", "relationship_type": "located_in",
            "to_node_id": "tunnel", "label": "inside",
        },
        "replacement_tuple": {
            "from_node_id": "tunnel", "relationship_type": "leads_to",
            "to_node_id": "chamber", "label": "opens into",
        },
    }
    manifest = {
        "schema": "dmb_recap_semantic_candidate_manifest_v3",
        "edge_tuple_replacements": [operation],
    }
    manifest_sha = hashlib.sha256((json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode()).hexdigest()
    parent = _run(
        run_id="tuple_parent", source_artifact_id="artifact:recap:c:s:source",
        source_domain="recap", session_id="s", campaign_id="c",
        profile_id="recap_category_v1@1.0", status=ExtractionRunStatus.REVIEWABLE,
        components=parent_components,
    )
    basis = RecapSemanticBasisV4(
        parent_run_id=parent.run_id, parent_candidate_sha256="c" * 64,
        manifest_sha256=manifest_sha, child_run_id="tuple_child",
        candidate_uri="repo://tuple-child.json", candidate_sha256="d" * 64,
        source_artifact_id=parent.source_artifact_id,
        source_uri="repo://source.md", source_revision_sha256="a" * 64,
        span_index_uri="repo://spans.json", span_index_sha256="b" * 64,
        profile_id="recap_category_v1@1.0", profile_version="1.0",
        campaign_id="c", session_id="s",
        derivation="operator_recap_semantic_candidate_correction_v3",
        manifest_schema="dmb_recap_semantic_candidate_manifest_v3",
    )
    child = parent.model_copy(deep=True, update={
        "run_id": "tuple_child", "components": child_components,
        "lineage": {
            "derivation": basis.derivation, "parent_run_id": parent.run_id,
            "parent_candidate_sha256": "c" * 64,
            "manifest_sha256": manifest_sha, "semantic_candidate_manifest": manifest,
            "semantic_disposition": {"version": 1, "state": "held", "basis_sha256": basis.digest()},
        },
    })
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, parent)
        ingest_repo.insert_run(conn, child)
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:tuple", reviewer_id="local_operator",
    )
    accepted = record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision,
    )
    assert accepted.revision == child.revision + 1
    assert accepted.components == child.components
    assert accepted.lineage["semantic_candidate_manifest"] == manifest
    assert record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision,
    ) == accepted
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=accepted.revision, basis=basis,
            decision=decision,
        )

    bad_manifest = copy.deepcopy(manifest)
    bad_manifest["edge_tuple_replacements"][0]["arbitrary_patch"] = {"label": "forged"}
    bad_sha = hashlib.sha256((json.dumps(
        bad_manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode()).hexdigest()
    bad_basis = basis.model_copy(update={"manifest_sha256": bad_sha})
    bad_child = child.model_copy(deep=True, update={
        "lineage": {**child.lineage, "manifest_sha256": bad_sha,
                    "semantic_candidate_manifest": bad_manifest},
    })
    from application_state.ingest.service import _assert_recap_semantic_basis
    with pytest.raises(ApplicationStateConflictError, match="edge tuple manifest is malformed"):
        _assert_recap_semantic_basis(bad_child, parent, bad_basis)


def test_semantic_evidence_batch_basis_v6_cas_and_duplicate_target_rejection(
    application_state_dsn: str,
) -> None:
    parent_components = _review_components()
    parent_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://evidence-batch-parent.json", sha256="c" * 64,
    )
    child_components = dict(parent_components)
    child_components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://evidence-batch-child.json", sha256="d" * 64,
    )
    artifact_id = "artifact:recap:c:s:source"
    span_id = f"{artifact_id}:span:source:1-1"
    operation = {
        "record_kind": "node", "record_id": "node:mira", "evidence_index": 0,
        "expected_source_ref_id": "source-ref:mira",
        "expected_source_artifact_id": artifact_id,
        "expected_source_span_ref_id": span_id,
        "replacement_source_span_ref_id": span_id,
        "expected_anchor_quotes": ["old literal"],
        "replacement_anchor_quotes": ["new literal"],
    }
    second_operation = {
        **operation, "record_kind": "edge", "record_id": "edge:travel",
        "expected_source_ref_id": "source-ref:travel",
    }
    manifest = {
        "schema": "dmb_recap_semantic_candidate_manifest_v5",
        "evidence_span_replacements": [operation, second_operation],
    }
    manifest_sha = hashlib.sha256((json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode()).hexdigest()
    suffix = uuid4().hex[:12]
    parent = _run(
        run_id=f"evidence_batch_parent_{suffix}", source_artifact_id=artifact_id,
        source_domain="recap", session_id="s", campaign_id="c",
        profile_id="recap_category_v1@1.0", status=ExtractionRunStatus.REVIEWABLE,
        components=parent_components,
    )
    child_id = f"evidence_batch_child_{suffix}"
    basis = RecapSemanticBasisV6(
        parent_run_id=parent.run_id, parent_candidate_sha256="c" * 64,
        manifest_sha256=manifest_sha, child_run_id=child_id,
        candidate_uri=child_components["candidate_graph"].uri, candidate_sha256="d" * 64,
        source_artifact_id=artifact_id,
        source_uri="repo://source.md", source_revision_sha256="a" * 64,
        span_index_uri="repo://spans.json", span_index_sha256="b" * 64,
        profile_id="recap_category_v1@1.0", profile_version="1.0",
        campaign_id="c", session_id="s",
        derivation="operator_recap_semantic_candidate_correction_v5",
        manifest_schema="dmb_recap_semantic_candidate_manifest_v5",
    )
    child = parent.model_copy(deep=True, update={
        "run_id": child_id, "components": child_components,
        "lineage": {
            "derivation": basis.derivation, "parent_run_id": parent.run_id,
            "parent_candidate_sha256": "c" * 64,
            "manifest_sha256": manifest_sha, "semantic_candidate_manifest": manifest,
            "semantic_disposition": {"version": 1, "state": "held", "basis_sha256": basis.digest()},
        },
    })
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, parent)
        ingest_repo.insert_run(conn, child)
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:evidence-batch", reviewer_id="local_operator",
    )
    accepted = record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision,
    )
    assert accepted.revision == child.revision + 1
    assert accepted.lineage["semantic_candidate_manifest"] == manifest
    assert record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision,
    ) == accepted

    duplicated_manifest = copy.deepcopy(manifest)
    duplicated_manifest["evidence_span_replacements"].append(copy.deepcopy(operation))
    duplicated_sha = hashlib.sha256((json.dumps(
        duplicated_manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ) + "\n").encode()).hexdigest()
    duplicate_basis = basis.model_copy(update={"manifest_sha256": duplicated_sha})
    duplicate_child = child.model_copy(deep=True, update={
        "lineage": {
            **child.lineage, "manifest_sha256": duplicated_sha,
            "semantic_candidate_manifest": duplicated_manifest,
        },
    })
    from application_state.ingest.service import _assert_recap_semantic_basis
    with pytest.raises(ApplicationStateConflictError, match="duplicate targets"):
        _assert_recap_semantic_basis(duplicate_child, parent, duplicate_basis)


def test_recap_disposition_rejects_changed_basis_and_unmarked(application_state_dsn: str) -> None:
    _parent, child, basis = _recap_basis_and_pair(application_state_dsn)
    decision = RecapSemanticDispositionCommandV1(
        state="rejected", review_decision_ref="review:2", reviewer_id="local_operator"
    )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision,
            basis=basis.model_copy(update={"candidate_sha256": "f" * 64}),
            decision=decision,
        )
    assert get_extraction_run(child.run_id).revision == child.revision
    world = _run(run_id="ordinary", components=_review_components(), status=ExtractionRunStatus.REVIEWABLE)
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, world)
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            world.run_id, expected_revision=world.revision,
            basis=basis.model_copy(update={"child_run_id": world.run_id}),
            decision=decision,
        )


def test_marked_child_remains_findable_after_status_or_domain_drift(
    application_state_dsn: str,
) -> None:
    _parent, child, basis = _recap_basis_and_pair(application_state_dsn)
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:3", reviewer_id="local_operator"
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.run SET status = 'rejected' WHERE run_id = %s", (child.run_id,))
        conn.commit()
    lookup = lookup_extraction_run_by_candidate_component(
        uri=basis.candidate_uri, sha256=basis.candidate_sha256
    )
    assert lookup.kind == "unique" and lookup.run.status == ExtractionRunStatus.REJECTED
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision, basis=basis, decision=decision
        )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE ingest.run SET status = 'reviewable', source_domain = 'worldbuilding', session_id = NULL WHERE run_id = %s",
            (child.run_id,),
        )
        conn.commit()
    lookup = lookup_extraction_run_by_candidate_component(
        uri=basis.candidate_uri, sha256=basis.candidate_sha256
    )
    assert lookup.kind == "unique" and lookup.run.source_domain == "worldbuilding"
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision, basis=basis, decision=decision
        )


def test_rejected_semantic_decision_is_single_use(application_state_dsn: str) -> None:
    _parent, child, basis = _recap_basis_and_pair(application_state_dsn)
    decision = RecapSemanticDispositionCommandV1(
        state="rejected", review_decision_ref="review:reject", reviewer_id="local_operator"
    )
    result = record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision
    )
    assert result.lineage["semantic_disposition"]["state"] == "rejected"
    assert record_recap_semantic_disposition(
        child.run_id, expected_revision=child.revision, basis=basis, decision=decision
    ) == result
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision, basis=basis,
            decision=decision.model_copy(update={"review_decision_ref": "different"}),
        )


def test_recap_decision_rejects_matching_unknown_profile(application_state_dsn: str) -> None:
    parent, child, basis = _recap_basis_and_pair(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE ingest.run SET profile_id = 'unknown_profile@1.0' WHERE run_id = ANY(%s)",
            ([parent.run_id, child.run_id],),
        )
        conn.commit()
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:profile", reviewer_id="local_operator"
    )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision,
            basis=basis.model_copy(update={"profile_id": "unknown_profile@1.0"}),
            decision=decision,
        )


def test_recap_decision_rejects_mutable_parent(application_state_dsn: str) -> None:
    parent, child, basis = _recap_basis_and_pair(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE ingest.run SET status = 'draft' WHERE run_id = %s",
            (parent.run_id,),
        )
        conn.commit()
    decision = RecapSemanticDispositionCommandV1(
        state="accepted", review_decision_ref="review:parent", reviewer_id="local_operator"
    )
    with pytest.raises(ApplicationStateConflictError):
        record_recap_semantic_disposition(
            child.run_id, expected_revision=child.revision, basis=basis, decision=decision
        )


def _model_valid_terminal_run(status: ExtractionRunStatus) -> ExtractionRun:
    extras: dict = {"status": status}
    if status == ExtractionRunStatus.PROMOTED:
        extras["components"] = _review_components()
    if status == ExtractionRunStatus.SUPERSEDED:
        extras["superseded_by_run_id"] = "er_other"
    return _run(**extras)


def test_alembic_is_at_current_head(application_state_dsn: str) -> None:
    current, head = _current_and_head(application_state_dsn)
    assert current == head


@pytest.mark.parametrize(
    "status",
    [
        ExtractionRunStatus.PROMOTED,
        ExtractionRunStatus.REJECTED,
        ExtractionRunStatus.FAILED,
        ExtractionRunStatus.SUPERSEDED,
    ],
)
def test_create_rejects_terminal_status(
    application_state_dsn: str, status: ExtractionRunStatus
) -> None:
    with pytest.raises(
        ApplicationStateValidationError,
        match="cannot create an extraction run directly in a terminal status",
    ):
        create_extraction_run(_model_valid_terminal_run(status))
    assert list_extraction_runs() == []


def test_supersede_rejects_terminal_successor(application_state_dsn: str) -> None:
    created = create_extraction_run(_run())
    successor = _run(
        run_id="er_terminal_successor",
        status=ExtractionRunStatus.FAILED,
        supersedes_run_id=created.run_id,
    )
    with pytest.raises(
        ApplicationStateValidationError,
        match="cannot create an extraction run directly in a terminal status",
    ):
        supersede_extraction_run(
            created.run_id,
            expected_revision=created.revision,
            successor=successor,
        )
    loaded = get_extraction_run(created.run_id)
    assert loaded.status == ExtractionRunStatus.DRAFT
    assert loaded.superseded_by_run_id is None
    with pytest.raises(ApplicationStateNotFoundError):
        get_extraction_run("er_terminal_successor")


def test_create_list_get_independent_of_worktree_files(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_extraction_run(_run())
    missing_registry = tmp_path / "out/registries/extraction_runs.json"
    missing_runs = tmp_path / "out/graph_memory/runs"
    assert not missing_registry.exists()
    assert not missing_runs.exists()
    loaded = get_extraction_run(created.run_id)
    assert loaded.run_id == created.run_id
    assert loaded.revision == 1
    listed = list_extraction_runs()
    assert [row.run_id for row in listed] == [created.run_id]


def test_mounted_reads_ignore_conflicting_legacy_file(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_extraction_run(_run(run_id="er_db_truth"))
    path = tmp_path / "out/registries/extraction_runs.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schema_version":"dmb_extraction_run_registry_v1","records":[{'
        '"schema_version":"dmb_extraction_run_v1","version":"1.0",'
        '"run_id":"er_file_only","source_artifact_id":"sa_world_1",'
        '"source_domain":"worldbuilding","status":"draft","revision":1,'
        '"campaign_id":"eldyrwild","components":{},"diagnostics":{},'
        '"lineage":{}}]}',
        encoding="utf-8",
    )
    from apps.live_control_server.services.graph_run_registry import get_extraction_run as mounted_get

    loaded = mounted_get(tmp_path, created.run_id)
    assert loaded.run_id == "er_db_truth"
    with pytest.raises(Exception, match="not found"):
        mounted_get(tmp_path, "er_file_only")
    assert list_extraction_runs()[0].run_id == "er_db_truth"


def test_create_does_not_write_legacy_registry(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )
    from apps.live_control_server.services.graph_run_registry import create_extraction_run as mounted_create

    record = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        tmp_path, record.document_id, expected_revision=1
    )
    target = tmp_path / committed.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Lore\n", encoding="utf-8")
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=committed.document_id,
        expected_revision=committed.revision,
    )
    mounted_create(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    assert not (tmp_path / "out/registries/extraction_runs.json").exists()


def test_cas_stale_revision_cannot_overwrite(application_state_dsn: str) -> None:
    created = create_extraction_run(_run())
    first = update_extraction_run(
        created.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=1,
    )
    assert first.revision == 2
    with pytest.raises(ApplicationStateConflictError, match="revision mismatch"):
        update_extraction_run(
            created.run_id,
            status=ExtractionRunStatus.EXTRACTED,
            expected_revision=1,
        )
    loaded = get_extraction_run(created.run_id)
    assert loaded.status == ExtractionRunStatus.PREPARED
    assert loaded.revision == 2


def test_supersede_is_atomic_on_injected_failure(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = create_extraction_run(_run())
    prepared = update_extraction_run(
        created.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=created.revision,
    )

    def boom(_conn, _run):
        raise RuntimeError("injected supersede failure")

    monkeypatch.setattr(
        "application_state.ingest.service.repo.insert_run",
        boom,
    )
    successor = _run(
        run_id="er_successor",
        supersedes_run_id=prepared.run_id,
    )
    with pytest.raises(RuntimeError, match="injected"):
        supersede_extraction_run(
            prepared.run_id,
            expected_revision=prepared.revision,
            successor=successor,
        )
    loaded = get_extraction_run(prepared.run_id)
    assert loaded.status == ExtractionRunStatus.PREPARED
    assert loaded.superseded_by_run_id is None
    with pytest.raises(ApplicationStateNotFoundError):
        get_extraction_run("er_successor")


def test_supersede_commits_reciprocal_lineage(application_state_dsn: str) -> None:
    created = create_extraction_run(_run())
    prepared = update_extraction_run(
        created.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=created.revision,
    )
    successor = _run(
        run_id="er_next",
        source_artifact_id=prepared.source_artifact_id,
        supersedes_run_id=prepared.run_id,
    )
    created_successor = supersede_extraction_run(
        prepared.run_id,
        expected_revision=prepared.revision,
        successor=successor,
    )
    predecessor = get_extraction_run(prepared.run_id)
    assert predecessor.status == ExtractionRunStatus.SUPERSEDED
    assert predecessor.superseded_by_run_id == created_successor.run_id
    assert created_successor.supersedes_run_id == predecessor.run_id
    assert predecessor.revision == prepared.revision + 1


def test_inspect_empty_catalog(application_state_dsn: str) -> None:
    snapshot = inspect_ingest_authority()
    assert snapshot.run_count == 0


def test_malformed_row_is_integrity_not_empty(application_state_dsn: str) -> None:
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            """
            INSERT INTO ingest.run (
                run_id, schema_version, record_version, source_artifact_id,
                source_domain, status, revision, components, diagnostics, lineage
            ) VALUES (
                'er_bad', 'not-a-schema', '1.0', 'sa_world_1',
                'worldbuilding', 'draft', 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb
            )
            """
        )
        conn.commit()
    with pytest.raises(ApplicationStateIntegrityError, match="cannot be interpreted"):
        inspect_ingest_authority()
    with pytest.raises(ApplicationStateIntegrityError):
        get_extraction_run("er_bad")


def test_missing_component_bytes_do_not_hide_catalog_row(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run as mounted_get,
        get_reviewable_extraction_run,
    )
    from application_state.ingest.repository import insert_run
    from application_state.unit_of_work import unit_of_work

    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri="repo://missing-source.md",
            sha256="a" * 64,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri="repo://missing-spans.json",
            sha256="b" * 64,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri="repo://missing-graph.json",
            sha256="c" * 64,
        ),
    }
    run = _run(
        status=ExtractionRunStatus.REVIEWABLE,
        components=components,
    )
    with unit_of_work(application_state_dsn) as conn:
        insert_run(conn, run)
    catalog = mounted_get(tmp_path, run.run_id)
    assert catalog.run_id == run.run_id
    with pytest.raises(GraphRunRegistryError, match="component file missing|unknown source_artifact"):
        get_reviewable_extraction_run(tmp_path, run.run_id)


def test_boot_does_not_migrate_or_import(
    tmp_path: Path, application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.runtime_preflight import run_runtime_preflight

    monkeypatch.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn)
    called = {"upgrade": 0, "import": 0}

    def fake_upgrade(*, dsn=None):
        called["upgrade"] += 1

    def fake_import(*_args, **_kwargs):
        called["import"] += 1
        raise AssertionError("import must not run on boot/preflight")

    monkeypatch.setattr("application_state.cli.upgrade_to_head", fake_upgrade)
    monkeypatch.setattr(
        "application_state.ingest.import_legacy.import_extraction_runs_from_registry",
        fake_import,
    )
    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "EMPTY"
    assert called["upgrade"] == 0
    assert called["import"] == 0
