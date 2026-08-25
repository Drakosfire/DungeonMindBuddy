"""CUTOVER D.2A isolated PostgreSQL witnesses (env-gated).

Requires ``DMB_CUTOVER_TEST_DATABASE_URL`` pointing at a disposable migrated
database. Skips when unset. Reuses the D.1 adoption fixture without changing
Graph Review confirm behavior.
"""

from __future__ import annotations

import pytest

from tests.test_cutover_dungeonmind_world_graph_authority import (
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
    monkeypatch.setattr(wga, "hydrate_world_graph", _explode)
    monkeypatch.setattr(wga, "ensure_hydrated_authority", _explode)


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
    verified = adapter.verify_child(
        receipt=receipt,
        expected=WorldGraphExpectedChildFacts(
            threat_node_id="node:d2a-threat-port",
            decision="create_new",
            accepted_assertion_ids=tuple(accepted_ids),
        ),
    )
    assert verified.status == "passed"

    retry = adapter.publish(request)
    assert retry.published_revision_id == d_b
    assert retry.outcome == "already_applied"
    assert adapter.current_head(WORLD_ID).revision_id == d_b

    recovered = adapter.recover(WORLD_ID, operation_id)
    assert recovered is not None
    assert recovered.published_revision_id == d_b
    assert recovered.parent_revision_id == d_a

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
