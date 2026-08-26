"""CUTOVER D.2C2: native first-world initialization behind DungeonMind authority."""

from __future__ import annotations

import ast
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.config as live_config
import apps.live_control_server.services.extract_promote as promote_svc
import apps.live_control_server.services.promotable_ingest_run as promotable_mod
from apps.live_control_server.main import create_app
from apps.live_control_server.models.extract_promote import FirstWorldGraphConfirmRequest
from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationError,
)
from apps.live_control_server.ports.world_graph_initialization_access import (
    get_world_graph_initialization_authority,
)
from apps.live_control_server.services.first_world_graph import first_world_initialization_id
from apps.live_control_server.services.first_world_graph_publication import (
    confirm_first_world,
)
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
)
from tests.test_cutover_dungeonmind_world_graph_authority import (
    TRUNCATE_SQL,
    _ensure_migrated,
    _test_dsn,
)
from tests.test_live_extract_promote_api import (
    FIRST_WORLD_CONFIRM_URL,
    FIRST_WORLD_PREPARE_URL,
    GLASS_ORCHARD_WORLD_ID,
    _first_world_confirm_body,
    _first_world_decisions,
    _first_world_prepare_body,
    _mutate_extraction_candidate,
    _write_glass_orchard_bld08_run,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DUNGEONMIND_PIN = "bf40e933bdedf3cf08bb23a07a135958bdb7cc6b"
REJECTED_NODE_ID = "obj_rejected_extra"


def _forbidden_imports(path: Path, names: tuple[str, ...]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in names or any(
                    alias.name.startswith(f"{item}.") for item in names
                ):
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module in names or any(
                node.module.startswith(f"{item}.") for item in names
            ):
                found.append(node.module)
    return found


def test_dungeonmind_pin_is_exact_pr46_merge() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lock = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    assert DUNGEONMIND_PIN in pyproject
    assert DUNGEONMIND_PIN in lock


def test_initialization_id_is_deterministic() -> None:
    first = first_world_initialization_id("the-glass-orchard", "plan-a")
    second = first_world_initialization_id("the-glass-orchard", "plan-a")
    other = first_world_initialization_id("the-glass-orchard", "plan-b")
    assert first == second
    assert first.startswith("dmb:first-world:")
    assert first != other
    payload = json.dumps(
        {"world_id": "the-glass-orchard", "plan_id": "plan-a"},
        sort_keys=True,
        separators=(",", ":"),
    )
    assert first == "dmb:first-world:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_factory_selects_native_only_for_production_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.integrations.buddy_files.world_graph_initialization_adapter import (
        BuddyFilesWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from graph_memory.world_supergraph import storage

    prod = tmp_path / "prod"
    other = tmp_path / "other"
    prod.mkdir()
    other.mkdir()
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(prod))
    native = get_world_graph_initialization_authority(world_root=prod)
    compat = get_world_graph_initialization_authority(world_root=other)
    assert isinstance(native, DungeonMindWorldGraphInitializationAdapter)
    assert isinstance(compat, BuddyFilesWorldGraphInitializationAdapter)


def test_product_services_do_not_import_postgres_infrastructure() -> None:
    forbidden = (
        "dungeonmind.infrastructure.postgres",
        "dungeonmind.infrastructure.postgres.reviewed_world_initialization",
    )
    for rel in (
        "apps/live_control_server/services/first_world_graph_publication.py",
        "apps/live_control_server/services/extract_promote.py",
        "apps/live_control_server/services/first_world_graph.py",
        "apps/live_control_server/ports/world_graph_initialization.py",
        "apps/live_control_server/ports/world_graph_initialization_access.py",
    ):
        found = _forbidden_imports(REPO_ROOT / rel, forbidden)
        assert found == [], f"{rel} imports {found}"


def test_mounted_first_world_path_has_no_kernel_initialization_authority() -> None:
    forbidden = (
        "graph_memory.kernel.reviewed_world_initialization",
        "graph_memory.kernel.world_initialization",
        "graph_memory.world_supergraph.storage",
        "graph_memory.world_supergraph.paths",
    )
    for rel in (
        "apps/live_control_server/services/first_world_graph_publication.py",
        "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
        "apps/live_control_server/services/extract_promote.py",
    ):
        found = _forbidden_imports(REPO_ROOT / rel, forbidden)
        assert found == [], f"{rel} still imports {found}"


def test_genesis_semantic_profile_is_builtin_worldbuilding_descriptor() -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        _genesis_semantic_profile,
    )
    from dungeonmind.application.semantic_profiles import descriptor_sha256
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    descriptor = load_builtin_v3_descriptor()
    profile = _genesis_semantic_profile()
    assert profile.profile_id == descriptor.profile_id
    assert profile.profile_revision == descriptor.profile_revision
    assert profile.descriptor_sha256 == descriptor_sha256(descriptor)


def _add_rejected_node(payload: dict) -> None:
    nodes = list(payload.get("nodes") or [])
    template = dict(nodes[0])
    template["node_id"] = REJECTED_NODE_ID
    template["label"] = "Rejected extra"
    payload["nodes"] = [*nodes, template]


@pytest.fixture
def native_first_world_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dsn = _test_dsn()
    _ensure_migrated(dsn)
    from dungeonmind.infrastructure.postgres import PostgresDatabase

    database = PostgresDatabase(dsn)
    with database.connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()

    from graph_memory.world_supergraph import storage

    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
    monkeypatch.setenv(
        "DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT",
        str(tmp_path / "_designated_live_not_used"),
    )
    monkeypatch.delenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", raising=False)
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    monkeypatch.setattr(live_config, "repo_root", lambda: repo)
    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)
    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)
    client = TestClient(create_app())
    return client, world_root, repo, dsn


def _prepare_native_plan(client, repo: Path, *, with_rejected: bool = False) -> tuple[str, dict]:
    run_id, _source = _write_glass_orchard_bld08_run(repo)
    decisions = _first_world_decisions()
    if with_rejected:
        _mutate_extraction_candidate(repo, run_id, _add_rejected_node)
        decisions = [*decisions, {"assertionId": REJECTED_NODE_ID, "decision": "reject"}]
    prepare = client.post(
        FIRST_WORLD_PREPARE_URL,
        json=_first_world_prepare_body(run_id, decisions),
    )
    assert prepare.status_code == 200, prepare.text
    return run_id, prepare.json()


def _bundle(dsn: str):
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresRepositoryBundle,
    )

    return PostgresRepositoryBundle(PostgresDatabase(dsn))


def _counts(dsn: str, world_id: str) -> dict[str, int]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        def count(sql_text: str, params: tuple = (world_id,)) -> int:
            row = conn.execute(sql_text, params).fetchone()
            return int(row[0])

        return {
            "heads": count(
                "SELECT count(*) FROM dungeonmind.world_graph_heads WHERE world_id = %s"
            ),
            "revisions": count(
                "SELECT count(*) FROM dungeonmind.graph_revisions WHERE world_id = %s"
            ),
            "receipts": count(
                "SELECT count(*) FROM dungeonmind.reviewed_world_initializations "
                "WHERE world_id = %s"
            ),
            "contributions": count(
                "SELECT count(*) FROM dungeonmind.graph_contributions WHERE world_id = %s"
            ),
            "artifacts": count(
                "SELECT count(*) FROM dungeonmind.source_artifacts WHERE world_id = %s"
            ),
            "revisions_src": count(
                "SELECT count(*) FROM dungeonmind.source_revisions r "
                "JOIN dungeonmind.source_artifacts a "
                "ON a.source_artifact_id = r.source_artifact_id "
                "WHERE a.world_id = %s"
            ),
            "adoptions": count(
                "SELECT count(*) FROM dungeonmind.existing_world_adoptions "
                "WHERE world_id = %s"
            ),
        }


def _artifact_ids(dsn: str, world_id: str) -> list[tuple[str]]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        return conn.execute(
            "SELECT source_artifact_id FROM dungeonmind.source_artifacts WHERE world_id = %s",
            (world_id,),
        ).fetchall()


def _revision_ids(dsn: str, world_id: str) -> list[tuple[str]]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        return conn.execute(
            "SELECT r.source_revision_id FROM dungeonmind.source_revisions r "
            "JOIN dungeonmind.source_artifacts a "
            "ON a.source_artifact_id = r.source_artifact_id "
            "WHERE a.world_id = %s",
            (world_id,),
        ).fetchall()


@pytest.mark.integration
def test_native_review_prepare_confirm_with_buddy_graph_absent(
    native_first_world_client,
) -> None:
    client, world_root, repo, dsn = native_first_world_client
    glass_dir = world_root / "graph_memory" / "worlds" / GLASS_ORCHARD_WORLD_ID
    run_id, plan = _prepare_native_plan(client, repo, with_rejected=True)
    assert not glass_dir.exists()
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 0

    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["worldState"] == "uninitialized"
    assert body["firstWorldPublishEligible"] is True

    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 200, confirm.text
    receipt = confirm.json()
    assert receipt["outcome"] == "initialized"
    assert receipt["baselineRevisionId"] is None
    assert receipt["committedRevisionId"]
    assert not glass_dir.exists()

    after = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert after.status_code == 200, after.text
    assert after.json()["worldState"] == "initialized"
    assert after.json()["firstWorldPublishEligible"] is False
    assert not glass_dir.exists()


@pytest.mark.integration
def test_native_empty_to_d0_topology_and_source_closure(
    native_first_world_client,
) -> None:
    from dungeonmind.contracts.identity import IdentityOutcome

    client, world_root, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo, with_rejected=True)
    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 200, confirm.text
    published = confirm.json()["committedRevisionId"]
    counts = _counts(dsn, GLASS_ORCHARD_WORLD_ID)
    assert counts["heads"] == 1
    assert counts["revisions"] == 1
    assert counts["receipts"] == 1
    assert counts["contributions"] == 1
    assert counts["artifacts"] == 1
    assert counts["revisions_src"] == 1
    assert counts["adoptions"] == 0
    assert not (world_root / "graph_memory" / "worlds" / GLASS_ORCHARD_WORLD_ID).exists()

    bundle = _bundle(dsn)
    head = bundle.world_graph.get_head(GLASS_ORCHARD_WORLD_ID)
    assert head is not None
    assert head.head_revision_id == published
    stored = bundle.world_graph.get_revision(GLASS_ORCHARD_WORLD_ID, published)
    assert stored is not None
    assert stored.revision.parent_revision_id is None
    payload = stored.graph_payload
    object_ids = {item["object_id"] for item in payload.get("objects") or []}
    assert "obj_session22_vial" in object_ids
    assert "mystery_puddles" in object_ids
    assert REJECTED_NODE_ID not in object_ids

    init = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)
    assert init is not None
    contribution = bundle.contributions.get(
        GLASS_ORCHARD_WORLD_ID, init.reviewed_contribution_id
    )
    assert contribution is not None
    vial = next(
        item
        for item in contribution.assertions
        if item.assertion_kind == "node"
        and item.subject_object_id == "obj_session22_vial"
        and item.acceptance_state.value == "accepted"
    )
    edge = next(item for item in contribution.assertions if item.assertion_kind == "edge")
    rejected = next(
        item
        for item in contribution.assertions
        if item.subject_object_id == REJECTED_NODE_ID
    )
    assert vial.identity_resolution_outcome is IdentityOutcome.CREATED_NEW
    assert edge.identity_resolution_outcome is None
    assert rejected.acceptance_state.value == "rejected"
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        _genesis_semantic_profile,
    )

    profile = _genesis_semantic_profile()
    assert profile.profile_id == "dungeonmind.dnd5e"
    artifact_ids = {row[0] for row in _artifact_ids(dsn, GLASS_ORCHARD_WORLD_ID)}
    revision_ids = {row[0] for row in _revision_ids(dsn, GLASS_ORCHARD_WORLD_ID)}
    assert artifact_ids
    assert revision_ids
    for assertion in contribution.assertions:
        assert assertion.source_artifact_id in artifact_ids
        assert assertion.source_revision_id in revision_ids
        for ref in assertion.evidence_refs:
            assert ref.source_artifact_id in artifact_ids
            assert ref.source_revision_id in revision_ids


@pytest.mark.integration
def test_native_exact_retry_reuses_receipt_timestamp(
    native_first_world_client,
) -> None:
    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    bundle = _bundle(dsn)
    original = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)
    assert original is not None
    retry = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert retry.status_code == 200, retry.text
    assert retry.json()["outcome"] == "already_initialized"
    assert retry.json()["committedRevisionId"] == first.json()["committedRevisionId"]
    assert retry.json()["baselineRevisionId"] is None
    replayed = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)
    assert replayed is not None
    assert replayed.command_sha256 == original.command_sha256
    assert replayed.initialized_at == original.initialized_at
    assert replayed.published_revision_id == original.published_revision_id
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 1


@pytest.mark.integration
def test_native_lost_response_restart_replays_same_d0(
    native_first_world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )

    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    real = DungeonMindWorldGraphInitializationAdapter.initialize
    lost = {"done": False}

    def _lose(self, request):
        receipt = real(self, request)
        if not lost["done"]:
            lost["done"] = True
            raise WorldGraphInitializationError(
                "simulated lost response after provider commit",
                code="initialization_failed",
            )
        return receipt

    monkeypatch.setattr(DungeonMindWorldGraphInitializationAdapter, "initialize", _lose)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 500, first.text
    retry = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert retry.status_code == 200, retry.text
    assert retry.json()["outcome"] == "already_initialized"
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 1


@pytest.mark.integration
def test_native_synchronized_identical_confirms_share_one_d0(
    native_first_world_client,
) -> None:
    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    request = FirstWorldGraphConfirmRequest.model_validate(
        _first_world_confirm_body(plan)
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm_first_world, [request, request]))
    outcomes = sorted(item.outcome for item in results)
    assert outcomes in (
        ["already_initialized", "initialized"],
        ["initialized", "initialized"],
        ["already_initialized", "already_initialized"],
    )
    published = {item.committed_revision_id for item in results}
    assert len(published) == 1
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 1


@pytest.mark.integration
def test_native_changed_command_conflicts(native_first_world_client) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.services.extract_promote import (
        _load_typed_worldbuilding_preview_for_run,
    )
    from apps.live_control_server.services.first_world_graph import (
        materialize_first_world_plan,
    )
    from apps.live_control_server.services.first_world_graph_publication import (
        _initialization_request,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from graph_memory.worldbuilding_write_plan import WorldbuildingDispositionInput

    client, _world, repo, dsn = native_first_world_client
    run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(resolved)
    rematerialized = materialize_first_world_plan(
        preview=typed_preview,
        world_id=plan["worldId"],
        run_id=plan["runId"],
        source_artifact_id=plan["sourceArtifactId"],
        source_revision_id=plan["sourceRevisionId"],
        source_uri=resolved.sealed_source_uri,
        extraction_profile=expected_profile,
        campaign_scope=plan["campaignScope"],
        workspace_document_id=plan["workspaceDocumentId"],
        workspace_document_revision=plan["workspaceDocumentRevision"],
        dispositions=[
            WorldbuildingDispositionInput(
                assertion_id=str(item["assertion_id"]),
                decision=str(item["decision"]),
                target_node_id=item.get("target_node_id"),
            )
            for item in plan["reviewedEffect"]["decision_snapshot"]
        ],
    )
    request = _initialization_request(
        plan=FirstWorldGraphConfirmRequest.model_validate(
            _first_world_confirm_body(plan)
        ).plan,
        rematerialized=rematerialized,
        resolved=resolved,
    )
    changed = replace(request, actor="attacker:not-the-confirming-principal")
    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    with pytest.raises(WorldGraphInitializationError) as exc_info:
        adapter.initialize(changed)
    assert exc_info.value.code == "idempotency_conflict"
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1


@pytest.mark.integration
def test_native_non_pristine_without_receipt_fails_closed(
    native_first_world_client,
) -> None:
    import psycopg

    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "DELETE FROM dungeonmind.reviewed_world_initializations WHERE world_id = %s",
            (GLASS_ORCHARD_WORLD_ID,),
        )
        conn.commit()
    second = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert second.status_code == 409, second.text
    assert second.json()["code"] in {
        "world_already_initialized",
        "first_world_initialization_failed",
        "first_world_idempotency_conflict",
    }
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1


@pytest.mark.integration
def test_native_workspace_drift_fails_before_publication(
    native_first_world_client,
) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        WorkspaceDocumentRegistryDocument,
        get_workspace_document,
        workspace_documents_path,
    )
    from src.live_play.live_store import load_json, write_json

    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    artifact = get_source_artifact(repo, plan["sourceArtifactId"])
    workspace_path = workspace_documents_path(repo)
    workspace_doc = WorkspaceDocumentRegistryDocument.model_validate(load_json(workspace_path))
    rewritten = []
    for row in workspace_doc.records:
        if row.document_id == artifact.workspace_document_id:
            rewritten.append(row.model_copy(update={"revision": int(row.revision) + 1}))
        else:
            rewritten.append(row)
    write_json(
        workspace_path,
        WorkspaceDocumentRegistryDocument(
            schema_version=workspace_doc.schema_version,
            records=rewritten,
        ).model_dump(mode="json"),
    )
    assert get_workspace_document(repo, artifact.workspace_document_id).revision != int(
        plan["workspaceDocumentRevision"]
    )
    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 422, confirm.text
    assert confirm.json()["code"] == "workspace_lineage_mismatch"
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 0
