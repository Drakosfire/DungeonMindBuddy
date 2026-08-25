"""CUTOVER D.2A isolated PostgreSQL witnesses (env-gated).

Requires ``DMB_CUTOVER_TEST_DATABASE_URL`` pointing at a disposable migrated
database. Skips when unset. Reuses the D.1 adoption fixture without changing
Graph Review confirm behavior.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.test_cutover_dungeonmind_world_graph_authority import (
    CAMPAIGN_ID,
    WORLD_ID,
    _graph_revision_ids,
    _seal_tinker_package,
    _tree_digest,
    write_world as _d1_write_world,
)


@pytest.fixture
def write_world(tmp_path, monkeypatch):
    factory = getattr(_d1_write_world, "__wrapped__", _d1_write_world)
    return factory(tmp_path, monkeypatch)


def _explode_kernel(monkeypatch) -> None:
    import graph_memory.kernel as kernel
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )
    from apps.live_control_server.services import threat_publication_commits as commit_svc

    def _explode(*_args, **_kwargs):
        raise AssertionError("Buddy graph runtime must not run on D.2A native path")

    monkeypatch.setattr(kernel, "open_current_world_graph", _explode)
    monkeypatch.setattr(kernel, "open_world_graph_head", _explode)
    monkeypatch.setattr(kernel, "load_world_graph_revision", _explode)
    monkeypatch.setattr(kernel, "load_world_graph_revision_with_integrity", _explode)
    monkeypatch.setattr(kernel, "merge_contribution_to_revision", _explode)
    monkeypatch.setattr(kernel, "find_world_graph_revisions_by_operation_id", _explode)
    monkeypatch.setattr(kernel, "rebuild_from_contributions", _explode)
    monkeypatch.setattr(kernel, "project_world_graph", _explode)
    monkeypatch.setattr(commit_svc.kernel, "open_current_world_graph", _explode)
    monkeypatch.setattr(commit_svc.kernel, "load_world_graph_revision_with_integrity", _explode)
    monkeypatch.setattr(commit_svc.kernel, "merge_contribution_to_revision", _explode)
    monkeypatch.setattr(commit_svc.kernel, "find_world_graph_revisions_by_operation_id", _explode)
    monkeypatch.setattr(wga, "hydrate_world_graph", _explode)
    monkeypatch.setattr(wga, "ensure_hydrated_authority", _explode)


def _finalized_publication_rows(dsn: str) -> list[tuple[str, str]]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT operation_id, published_revision_id "
            "FROM dungeonmind.finalized_review_publications ORDER BY 1"
        ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


@pytest.mark.integration
def test_authority_port_publishes_d_a_to_d_b_with_retry_recover_and_stale_parent(
    write_world, monkeypatch
):
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.ports.world_graph_authority import (
        WorldGraphAuthorityError,
        WorldGraphExpectedChildFacts,
        WorldGraphPublishRequest,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    frozen_root = write_world["frozen_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_before = _tree_digest(frozen_root)
    revisions_before = _graph_revision_ids(dsn)
    _explode_kernel(monkeypatch)

    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    head = adapter.current_head(WORLD_ID)
    assert head.revision_id == d_a
    parent_view = adapter.read_revision(WORLD_ID, d_a)
    assert parent_view.revision_id == d_a
    assert parent_view.objects

    context = world_graph_writes.load_production_mutation_context(
        WORLD_ID, database_url=dsn
    )
    package, accepted_ids = _seal_tinker_package(
        context,
        write_world["tmp_path"],
        preview_slug="d2a-threat-port-write",
        node_id="node:d2a-threat-port",
        label="D2A Threat Port",
    )
    _verified, contribution = resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal="gm@confirm",
        world_id_hint=WORLD_ID,
        root=None,
        mutation_context=context,
        expected_parent_revision_id=d_a,
        assertion_ids=None,
        verify_source=False,
    )
    operation_id = contribution.contribution_id
    request = WorldGraphPublishRequest(
        world_id=WORLD_ID,
        expected_parent_revision_id=d_a,
        authority_operation_id=operation_id,
        actor="gm@confirm",
        contribution=contribution,
        accepted_assertion_ids=tuple(accepted_ids),
        decision="create_new",
        threat_node_id="node:d2a-threat-port",
    )
    receipt = adapter.publish(request)
    assert receipt.published is True
    assert receipt.parent_revision_id == d_a
    d_b = receipt.published_revision_id
    assert d_b != d_a
    assert adapter.current_head(WORLD_ID).revision_id == d_b

    child = adapter.read_revision(WORLD_ID, d_b)
    assert child.parent_revision_id == d_a
    assert "node:d2a-threat-port" in child.objects
    assert not any(
        rel.predicate.rsplit(":", 1)[-1] == "uses_statblock"
        for rel in child.relationships.values()
    )
    verified = adapter.verify_child(
        receipt=receipt,
        expected=WorldGraphExpectedChildFacts(
            threat_node_id="node:d2a-threat-port",
            decision="create_new",
            accepted_assertion_ids=tuple(accepted_ids),
            expected_object_kind=None,
        ),
    )
    assert verified.status == "passed"

    retry = adapter.publish(request)
    assert retry.published_revision_id == d_b
    assert retry.outcome == "already_applied"
    assert adapter.current_head(WORLD_ID).revision_id == d_b

    recovered = adapter.recover(
        WORLD_ID,
        operation_id,
        expected_parent_revision_id=d_a,
        contribution=contribution,
        actor="gm@confirm",
    )
    assert recovered is not None
    assert recovered.published_revision_id == d_b
    assert recovered.parent_revision_id == d_a

    changed_parent = WorldGraphPublishRequest(
        world_id=WORLD_ID,
        expected_parent_revision_id=d_b,
        authority_operation_id=operation_id,
        actor="gm@confirm",
        contribution=contribution,
        accepted_assertion_ids=tuple(accepted_ids),
        decision="create_new",
        threat_node_id="node:d2a-threat-port",
    )
    with pytest.raises(WorldGraphAuthorityError) as changed_parent_exc:
        adapter.publish(changed_parent)
    assert changed_parent_exc.value.code == "integrity_failure"
    assert adapter.current_head(WORLD_ID).revision_id == d_b

    package2, accepted_ids2 = _seal_tinker_package(
        context,
        write_world["tmp_path"],
        preview_slug="d2a-threat-port-changed",
        node_id="node:d2a-threat-port-changed",
        label="D2A Threat Port Changed",
    )
    _verified2, contribution2 = resolve_merged_contribution_from_package(
        review_package=package2,
        confirming_principal="gm@confirm",
        world_id_hint=WORLD_ID,
        root=None,
        mutation_context=context,
        expected_parent_revision_id=d_a,
        assertion_ids=None,
        verify_source=False,
    )
    changed_contrib = WorldGraphPublishRequest(
        world_id=WORLD_ID,
        expected_parent_revision_id=d_a,
        authority_operation_id=operation_id,
        actor="gm@confirm",
        contribution=contribution2,
        accepted_assertion_ids=tuple(accepted_ids2),
        decision="create_new",
        threat_node_id="node:d2a-threat-port-changed",
    )
    with pytest.raises(WorldGraphAuthorityError) as changed_contrib_exc:
        adapter.publish(changed_contrib)
    assert changed_contrib_exc.value.code == "integrity_failure"
    assert adapter.current_head(WORLD_ID).revision_id == d_b
    with pytest.raises(WorldGraphAuthorityError) as recover_parent_exc:
        adapter.recover(
            WORLD_ID,
            operation_id,
            expected_parent_revision_id=d_b,
            contribution=contribution,
            actor="gm@confirm",
        )
    assert recover_parent_exc.value.code == "integrity_failure"
    with pytest.raises(WorldGraphAuthorityError) as recover_contrib_exc:
        adapter.recover(
            WORLD_ID,
            operation_id,
            expected_parent_revision_id=d_a,
            contribution=contribution2,
            actor="gm@confirm",
        )
    assert recover_contrib_exc.value.code == "integrity_failure"

    stale = WorldGraphPublishRequest(
        world_id=WORLD_ID,
        expected_parent_revision_id=d_a,
        authority_operation_id=f"{operation_id}:stale",
        actor="gm@confirm",
        contribution=contribution,
        accepted_assertion_ids=tuple(accepted_ids),
        decision="create_new",
        threat_node_id="node:d2a-threat-port-stale",
    )
    with pytest.raises(WorldGraphAuthorityError) as excinfo:
        adapter.publish(stale)
    assert excinfo.value.code == "stale_parent"
    assert adapter.current_head(WORLD_ID).revision_id == d_b
    assert _tree_digest(frozen_root) == frozen_before
    assert d_b not in revisions_before
    head_row = bundle.world_graph.get_head(WORLD_ID)
    assert head_row is not None and head_row.head_revision_id == d_b


@pytest.mark.integration
def test_confirm_threat_publication_recovers_native_lost_receipt(
    write_world, monkeypatch
):
    """Handoff §16.7: confirm publishes D_B, receipt save fails, retry recovers."""
    import uuid

    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.models.threat_draft import GraphContextSnapshotV1
    from apps.live_control_server.models.threat_publication import (
        BeginThreatPublicationOperationRequestV1,
    )
    from apps.live_control_server.models.threat_publication_commit import (
        ConfirmThreatPublicationRequestV1,
    )
    from apps.live_control_server.services import threat_publication_commits as commit_svc
    from apps.live_control_server.services import threat_publication_operations as ops_svc
    from apps.live_control_server.services import threat_publication_proposals as proposal_svc
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
    )
    from apps.live_control_server.services.threat_publication_commit_store import (
        ThreatPublicationCommitStorageError,
        load_threat_publication_commit_ledger_unlocked,
    )
    from tests.test_threat_publication_proposals import (
        _create_draft,
        _create_new_resolution,
        _locator,
        _prepare_request,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    session_root = write_world["tmp_path"]
    d_a = write_world["receipt"].published_revision_id
    absent = session_root / "buddy-world-graph-absent"
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(absent))
    _explode_kernel(monkeypatch)

    publish_calls = {"n": 0}
    recover_calls = {"n": 0}
    real_publish = DungeonMindWorldGraphAuthorityAdapter.publish
    real_recover = DungeonMindWorldGraphAuthorityAdapter.recover

    def counting_publish(self, request):
        publish_calls["n"] += 1
        return real_publish(self, request)

    def counting_recover(self, *args, **kwargs):
        recover_calls["n"] += 1
        return real_recover(self, *args, **kwargs)

    monkeypatch.setattr(DungeonMindWorldGraphAuthorityAdapter, "publish", counting_publish)
    monkeypatch.setattr(DungeonMindWorldGraphAuthorityAdapter, "recover", counting_recover)

    draft = _create_draft(
        session_root,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        name="D2A Lost Receipt Brute",
        graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id=d_a),
    )
    ref = AcceptedMechanicsRefV1.from_locator(
        _locator(),
        accepted_from_draft_version=draft.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    draft = attach_accepted_mechanics_ref(
        session_root,
        draft_id=draft.draft_id,
        expected_version=draft.version,
        locator=ref,
    )
    op_id = str(uuid.uuid4())
    begin = ops_svc.begin_publication_operation(
        session_root,
        draft.draft_id,
        BeginThreatPublicationOperationRequestV1.model_validate(
            {
                "operation_id": op_id,
                "expected_draft_version": draft.version,
                "expected_parent_revision_id": d_a,
                "actor": "gm",
            }
        ),
    )
    assert begin.response.result_label == "publication_ready"
    resolution_id, _resolution = _create_new_resolution(
        session_root, draft, op_id, d_a
    )
    proposal_id = str(uuid.uuid4())
    prepared = proposal_svc.prepare_threat_publication_proposal(
        session_root,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(proposal_id),
        world_root=absent,
    )
    assert prepared.response.result_label == "publication_proposal_ready"
    proposal = prepared.response.proposal
    assert proposal is not None
    request = ConfirmThreatPublicationRequestV1.model_validate(
        {
            "commit_id": str(uuid.uuid4()),
            "sealed_proposal_digest": proposal.sealed_proposal_digest,
            "expected_parent_revision_id": proposal.expected_parent_revision_id,
            "actor": "gm",
        }
    )

    real_save = commit_svc._save_commit
    receipt_failures = {"n": 0}

    def flaky_save(root, commit):
        if commit.state == "committed_unverified" and receipt_failures["n"] == 0:
            receipt_failures["n"] += 1
            raise ThreatPublicationCommitStorageError(
                "receipt save failed", kind="unavailable"
            )
        return real_save(root, commit)

    revisions_before = _graph_revision_ids(dsn)
    finalized_before = _finalized_publication_rows(dsn)
    with patch.object(commit_svc, "_save_commit", side_effect=flaky_save):
        first = commit_svc.confirm_threat_publication(
            session_root,
            draft.draft_id,
            op_id,
            proposal.proposal_id,
            request,
            world_root=absent,
        )

    assert first.merge_calls == 1
    assert publish_calls["n"] == 1
    assert first.response.result_label == "publication_commit_storage_unavailable"
    assert first.response.commit is not None
    assert first.response.commit.state == "committing"
    assert first.response.commit.committed_revision_id is None
    assert first.response.retry_allowed is False
    head_after_publish = bundle.world_graph.get_head(WORLD_ID)
    assert head_after_publish is not None
    d_b = head_after_publish.head_revision_id
    assert d_b != d_a
    assert d_b not in revisions_before
    revisions_after_publish = _graph_revision_ids(dsn)
    finalized_after_publish = _finalized_publication_rows(dsn)
    assert len(finalized_after_publish) == len(finalized_before) + 1
    ledger = load_threat_publication_commit_ledger_unlocked(
        session_root, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"

    recover_before_retry = recover_calls["n"]
    replay = commit_svc.confirm_threat_publication(
        session_root,
        draft.draft_id,
        op_id,
        proposal.proposal_id,
        request,
        world_root=absent,
    )
    assert replay.merge_calls == 0
    assert publish_calls["n"] == 1
    assert recover_calls["n"] == recover_before_retry + 1
    assert replay.response.commit is not None
    assert replay.response.commit.committed_revision_id == d_b
    assert replay.response.commit.recovered_via_operation_lookup is True
    assert replay.response.result_label in {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }
    assert replay.response.commit.state in {
        "committed_verified",
        "committed_unverified",
    }
    assert _graph_revision_ids(dsn) == revisions_after_publish
    assert _finalized_publication_rows(dsn) == finalized_after_publish
    head_after_retry = bundle.world_graph.get_head(WORLD_ID)
    assert head_after_retry is not None and head_after_retry.head_revision_id == d_b
    durable = load_threat_publication_commit_ledger_unlocked(
        session_root, draft.draft_id, op_id
    )
    assert durable is not None
    assert durable.commit.committed_revision_id == d_b
    assert not absent.exists()
