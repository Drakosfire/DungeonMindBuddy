"""CUTOVER D.2B isolated PostgreSQL witnesses (env-gated).

Requires ``DMB_CUTOVER_TEST_DATABASE_URL`` pointing at a disposable migrated
database. Skips when unset. Reuses the D.1 adoption fixture without changing
Graph Review confirm behavior.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests.test_cutover_dungeonmind_world_graph_authority import (
    WORLD_ID,
    _graph_revision_ids,
    _tree_digest,
    write_world as _d1_write_world,
)
from tests.test_live_extract_promote_api import _write_bld08_reviewable_run


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
        raise AssertionError("Buddy graph runtime must not run on D.2B native path")

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


def _finalized_publication_rows(dsn: str) -> list[tuple[str, str]]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT operation_id, published_revision_id "
            "FROM dungeonmind.finalized_review_publications ORDER BY 1"
        ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def _source_plan_schemas(dsn: str) -> list[str]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            """
            SELECT payload->'plan_ref'->>'source_plan_schema'
            FROM dungeonmind.contribution_reviews
            """
        ).fetchall()
    return [str(row[0]) for row in rows if row[0]]


def _prefix_candidate_ids(repo: Path, run_id: str, prefix: str) -> tuple[str, str, str]:
    from apps.live_control_server.services.graph_run_registry import (
        extraction_runs_path,
        get_extraction_run,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        _resolve_extraction_component_path,
    )
    from src.live_play.live_store import load_json, write_json

    run = get_extraction_run(repo, run_id)
    candidate_path = _resolve_extraction_component_path(
        repo,
        run.components["candidate_graph"].uri,
        label="candidate_graph",
    )
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    node_ids = []
    for node in candidate.get("nodes") or []:
        node["node_id"] = f"{prefix}{node['node_id']}"
        node_ids.append(node["node_id"])
    edge_ids = []
    for edge in candidate.get("edges") or []:
        edge["edge_id"] = f"{prefix}{edge['edge_id']}"
        edge["from_node_id"] = f"{prefix}{edge['from_node_id']}"
        edge["to_node_id"] = f"{prefix}{edge['to_node_id']}"
        edge_ids.append(edge["edge_id"])
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    registry_path = extraction_runs_path(repo)
    registry = load_json(registry_path)
    for record in registry["records"]:
        if record["run_id"] == run_id:
            record["components"]["candidate_graph"]["sha256"] = digest
            break
    write_json(registry_path, registry)
    return node_ids[0], node_ids[1], edge_ids[0]


def _install_native_worldbuilding_repo(monkeypatch, tmp_path: Path, absent: Path) -> Path:
    import apps.live_control_server.config as live_config
    import apps.live_control_server.services.extract_promote as promote_svc
    import apps.live_control_server.services.promotable_ingest_run as promotable_mod
    from apps.live_control_server.services.graph_ingest_run_registry import (
        GRAPH_INGEST_RUNS_ENV,
    )

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(absent))
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    monkeypatch.setattr(live_config, "repo_root", lambda: repo)
    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)
    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)
    monkeypatch.setattr(live_config, "world_graph_root", lambda: absent)
    return repo


def _prepare_plan(
    run_id: str,
    parent: str,
    node_a: str,
    node_b: str,
    edge_id: str,
    *,
    reject_first: bool = False,
):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        prepare_worldbuilding,
    )

    if reject_first:
        dispositions = [
            {"assertionId": node_a, "decision": "reject"},
            {"assertionId": node_b, "decision": "create_new"},
            {"assertionId": edge_id, "decision": "defer"},
        ]
    else:
        dispositions = [
            {"assertionId": node_a, "decision": "create_new"},
            {"assertionId": node_b, "decision": "create_new"},
            {"assertionId": edge_id, "decision": "accept"},
        ]
    return prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": dispositions,
            }
        )
    )


@pytest.mark.integration
def test_worldbuilding_authority_port_publishes_d_a_to_d_b_with_retry_recover_and_stale(
    write_world, monkeypatch
):
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
    )
    from apps.live_control_server.ports.world_graph_authority import (
        WorldGraphAuthorityError,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    frozen_root = write_world["frozen_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_before = _tree_digest(frozen_root)
    revisions_before = _graph_revision_ids(dsn)
    finalized_before = _finalized_publication_rows(dsn)
    absent = write_world["tmp_path"] / "buddy-world-graph-absent"
    repo = _install_native_worldbuilding_repo(
        monkeypatch, write_world["tmp_path"], absent
    )
    _explode_kernel(monkeypatch)

    run_id, _source = _write_bld08_reviewable_run(repo)
    node_a, node_b, edge_id = _prefix_candidate_ids(repo, run_id, "d2b:")
    plan = _prepare_plan(run_id, d_a, node_a, node_b, edge_id)
    assert plan.parent_revision_id == d_a
    assert plan.effect.identity_authority is not None
    distinct_plan = _prepare_plan(
        run_id, d_a, node_a, node_b, edge_id, reject_first=True
    )
    assert distinct_plan.plan_id != plan.plan_id

    real_publish = DungeonMindWorldGraphAuthorityAdapter.publish
    lost = {"n": 0}

    def _publish_then_lose(self, request):
        real_publish(self, request)
        lost["n"] += 1
        raise WorldGraphAuthorityError("lost receipt", code="publication_failed")

    monkeypatch.setattr(
        DungeonMindWorldGraphAuthorityAdapter, "publish", _publish_then_lose
    )
    first = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert first.outcome == "already_applied"
    assert lost["n"] == 1
    d_b = first.committed_revision_id
    assert d_b != d_a
    assert first.parent_revision_id == d_a
    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    assert adapter.current_head(WORLD_ID).revision_id == d_b
    child = adapter.read_revision(WORLD_ID, d_b)
    assert child.parent_revision_id == d_a
    assert node_a in child.objects
    assert node_b in child.objects
    assert any(
        rel.subject_object_id == node_a and rel.target_object_id == node_b
        for rel in child.relationships.values()
    )
    assert len(_finalized_publication_rows(dsn)) == len(finalized_before) + 1
    schemas = _source_plan_schemas(dsn)
    assert "dmb_worldbuilding_publication_contribution_v1" in schemas
    assert "dmb_threat_publication_contribution_v1" not in schemas

    retry = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert retry.outcome == "already_applied"
    assert retry.committed_revision_id == d_b
    assert adapter.current_head(WORLD_ID).revision_id == d_b
    assert lost["n"] == 1
    assert len(_finalized_publication_rows(dsn)) == len(finalized_before) + 1

    with pytest.raises(Exception) as stale_exc:
        confirm_worldbuilding(
            WorldbuildingWritePlanConfirmRequest(plan=distinct_plan)
        )
    assert getattr(stale_exc.value, "code", "") == "stale_parent_revision"
    assert adapter.current_head(WORLD_ID).revision_id == d_b
    assert len(_finalized_publication_rows(dsn)) == len(finalized_before) + 1
    assert _tree_digest(frozen_root) == frozen_before
    assert d_b not in revisions_before
    assert not absent.exists()
    head_row = bundle.world_graph.get_head(WORLD_ID)
    assert head_row is not None and head_row.head_revision_id == d_b


def _add_node_aliases(repo: Path, run_id: str, node_id: str, aliases: list[str]) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        extraction_runs_path,
        get_extraction_run,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        _resolve_extraction_component_path,
    )
    from src.live_play.live_store import load_json, write_json

    run = get_extraction_run(repo, run_id)
    candidate_path = _resolve_extraction_component_path(
        repo,
        run.components["candidate_graph"].uri,
        label="candidate_graph",
    )
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    for node in candidate.get("nodes") or []:
        if node.get("node_id") == node_id:
            node["aliases"] = list(aliases)
            break
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    registry_path = extraction_runs_path(repo)
    registry = load_json(registry_path)
    for record in registry["records"]:
        if record["run_id"] == run_id:
            record["components"]["candidate_graph"]["sha256"] = digest
            break
    write_json(registry_path, registry)


@pytest.mark.integration
def test_worldbuilding_bind_existing_publishes_observation_and_alias(
    write_world, monkeypatch
):
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )

    dsn = write_world["dsn"]
    d_a = write_world["receipt"].published_revision_id
    frozen_root = write_world["frozen_root"]
    frozen_before = _tree_digest(frozen_root)
    absent = write_world["tmp_path"] / "buddy-world-graph-absent"
    repo = _install_native_worldbuilding_repo(
        monkeypatch, write_world["tmp_path"], absent
    )
    _explode_kernel(monkeypatch)

    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    parent = adapter.read_revision(WORLD_ID, d_a)
    target = next(
        obj
        for obj in parent.objects.values()
        if obj.kind.lower() in {"npc", "pc"} and obj.object_id
    )

    run_id, _source = _write_bld08_reviewable_run(repo)
    node_a, node_b, edge_id = _prefix_candidate_ids(repo, run_id, "d2b-bind:")
    _add_node_aliases(repo, run_id, node_a, ["Witness Alias"])
    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": d_a,
                "dispositions": [
                    {
                        "assertionId": node_a,
                        "decision": "bind_existing",
                        "targetNodeId": target.object_id,
                    },
                    {"assertionId": node_b, "decision": "create_new"},
                    {"assertionId": edge_id, "decision": "accept"},
                ],
            }
        )
    )
    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert receipt.outcome == "committed"
    child = adapter.read_revision(WORLD_ID, receipt.committed_revision_id)
    assert child.parent_revision_id == d_a
    bound = child.objects[target.object_id]
    assert "Witness Alias" in bound.aliases
    assert node_b in child.objects
    assert node_a not in child.objects
    accepted = list(plan.effect.accepted_proposals)
    attribute_ids = [
        item.assertion_id for item in accepted if item.assertion_kind == "attribute"
    ]
    alias_ids = [
        item.assertion_id for item in accepted if item.assertion_kind == "alias"
    ]
    assert attribute_ids
    assert alias_ids
    assert all(assertion_id in receipt.accepted_assertion_ids for assertion_id in attribute_ids)
    assert all(assertion_id in receipt.accepted_assertion_ids for assertion_id in alias_ids)
    parent_evidence = set(parent.evidence_refs)
    child_evidence = set(child.evidence_refs)
    added_evidence = child_evidence - parent_evidence
    attribute_evidence_ids = [
        evidence_id
        for item in accepted
        if item.assertion_kind == "attribute"
        for evidence_id in list(item.evidence_ref_ids)
        if evidence_id
    ]
    assert added_evidence
    assert attribute_evidence_ids
    assert any(
        evidence_id == raw or evidence_id.startswith(f"{raw}:dmv1:")
        for raw in attribute_evidence_ids
        for evidence_id in added_evidence
    ), (added_evidence, attribute_evidence_ids)
    schemas = _source_plan_schemas(dsn)
    assert "dmb_worldbuilding_publication_contribution_v1" in schemas
    assert "dmb_threat_publication_contribution_v1" not in schemas
    assert _tree_digest(frozen_root) == frozen_before
    assert not absent.exists()
