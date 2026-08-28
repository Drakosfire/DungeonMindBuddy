"""CUTOVER D.2C3: two-genesis native read/write continuity.

Unit proofs cover parent classification for reviewed-init ``D_0``. The owning
PostgreSQL witness creates a pristine world through the real corrected
first-world confirm path, then exercises the two-genesis binder, admitted
native projection/search/exact-object retrieval, ``WorldGraphAuthority``,
one existing-parent child, and exact retry/recovery. Buddy never rewrites
stored DungeonMind evidence on read.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import apps.live_control_server.config as live_config
import apps.live_control_server.services.extract_promote as promote_svc
import apps.live_control_server.services.promotable_ingest_run as promotable_mod
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    WorldGraphWriteError,
    _classify_parent_revision,
)
from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
)
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository
from fastapi.testclient import TestClient
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
from graph_memory.retrieval.models import (
    WorldGraphObjectRequest,
    WorldGraphSearchRequest,
)
from tests.test_cutover_dungeonmind_first_world_initialization import (
    _bundle,
    _counts,
    _prepare_native_plan,
)
from tests.test_cutover_dungeonmind_world_graph_authority import (
    TRUNCATE_SQL,
    _ensure_migrated,
    _seal_tinker_package,
    _test_dsn,
)
from tests.test_live_extract_promote_api import (
    FIRST_WORLD_CONFIRM_URL,
    GLASS_ORCHARD_WORLD_ID,
    _first_world_confirm_body,
)

NOW = datetime(2026, 8, 26, 18, 0, tzinfo=UTC)
CHILD_NODE_ID = "node:d2c3-continuity-child"


def _graph_payload() -> dict:
    from dungeonmind.application.semantic_profiles import descriptor_sha256
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    descriptor = load_builtin_v3_descriptor()
    return {
        "world_id": "world:d2c3-parent",
        "semantic_profile": {
            "schema_version": "dm_semantic_profile_ref_v1",
            "profile_id": descriptor.profile_id,
            "profile_revision": descriptor.profile_revision,
            "descriptor_sha256": descriptor_sha256(descriptor),
        },
        "relationship_endpoint_aspect_schema": "dm_relationship_endpoint_aspect_v1",
        "objects": [],
        "relationships": [],
        "evidence_refs": [],
    }


def test_classify_parent_accepts_real_d0_when_legacy_absent() -> None:
    world_id = "world:d2c3-parent"
    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=world_id,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:d2c3-parent"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_graph_payload(),
            created_at=NOW,
        )
    )
    kind = _classify_parent_revision(
        SimpleNamespace(world_graph=world_graph),
        world_id,
        published.revision_id,
        legacy_buddy_revision_id=None,
    )
    assert kind == "dungeonmind"


def test_classify_parent_still_rejects_exact_legacy_bridge_id() -> None:
    with pytest.raises(WorldGraphWriteError) as excinfo:
        _classify_parent_revision(
            SimpleNamespace(world_graph=InMemoryWorldGraphRepository()),
            "world:d2c3-parent",
            "rev:buddy-adopted-head",
            legacy_buddy_revision_id="rev:buddy-adopted-head",
        )
    assert excinfo.value.code == "governed_write_legacy_package"
    assert excinfo.value.details["reason"] == "buddy_a_revision"


def test_classify_parent_maps_provider_integrity_not_unavailable() -> None:
    from dungeonmind.domain.errors import (
        PersistenceIntegrityError,
        PersistenceUnavailableError,
    )

    class _CorruptGraph:
        def get_revision(self, world_id: str, revision_id: str):
            raise PersistenceIntegrityError("corrupt revision fingerprint")

    with pytest.raises(WorldGraphWriteError) as excinfo:
        _classify_parent_revision(
            SimpleNamespace(world_graph=_CorruptGraph()),
            "world:d2c3-parent",
            "rev:d0",
            legacy_buddy_revision_id=None,
        )
    assert excinfo.value.code == "authority_integrity"
    assert excinfo.value.details["reason"] == "provider_persistence_integrity"

    class _DownGraph:
        def get_revision(self, world_id: str, revision_id: str):
            raise PersistenceUnavailableError("connection lost")

    with pytest.raises(WorldGraphWriteError) as excinfo:
        _classify_parent_revision(
            SimpleNamespace(world_graph=_DownGraph()),
            "world:d2c3-parent",
            "rev:d0",
            legacy_buddy_revision_id=None,
        )
    assert excinfo.value.code == "authority_unavailable"


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


def _explode_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    import graph_memory.kernel as kernel
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    def _explode(*_args, **_kwargs):
        raise AssertionError("Buddy graph runtime must not run on D.2C3 native path")

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


def _projection_request(*, revision_pin: str | None = None) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=GLASS_ORCHARD_WORLD_ID,
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        admissibility="gm",
        scope_mode="campaign",
        revision_pin=revision_pin,
    )


def _retrieval_context(*, revision_pin: str | None = None) -> dict:
    fields = {
        "worldId": GLASS_ORCHARD_WORLD_ID,
        "campaignId": GLASS_ORCHARD_WORLD_ID,
        "admissibility": "gm",
        "scopeMode": "campaign",
    }
    if revision_pin is not None:
        fields["revisionPin"] = revision_pin
    return fields


@pytest.mark.integration
def test_reviewed_init_d0_native_read_write_continuity(
    native_first_world_client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.ports.world_graph_authority import (
        WorldGraphPublishRequest,
    )
    import tests.test_cutover_dungeonmind_world_graph_authority as authority_tests

    client, world_root, repo, dsn = native_first_world_client
    glass_dir = world_root / "graph_memory" / "worlds" / GLASS_ORCHARD_WORLD_ID
    _run_id, plan = _prepare_native_plan(client, repo)
    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 200, confirm.text
    d0 = confirm.json()["committedRevisionId"]
    assert d0
    assert not glass_dir.exists()

    counts = _counts(dsn, GLASS_ORCHARD_WORLD_ID)
    assert counts["receipts"] == 1
    assert counts["adoptions"] == 0
    assert counts["heads"] == 1
    assert counts["revisions"] == 1

    bundle = _bundle(dsn)
    stored_d0 = bundle.world_graph.get_revision(GLASS_ORCHARD_WORLD_ID, d0)
    assert stored_d0 is not None
    assert stored_d0.revision.parent_revision_id is None
    assert bundle.existing_world_adoptions.get_for_world(GLASS_ORCHARD_WORLD_ID) is None
    init = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)
    assert init is not None
    assert init.published_revision_id == d0
    evidence = stored_d0.graph_payload.get("evidence_refs") or []
    assert evidence
    stored_domains = {item.get("source_domain") for item in evidence}
    assert stored_domains == {"worldbuilding"}
    evidence_ids_before = [item.get("evidence_ref_id") for item in evidence]
    assert all(evidence_ids_before)
    payload_before = copy.deepcopy(stored_d0.graph_payload)

    retry_init = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert retry_init.status_code == 200, retry_init.text
    assert retry_init.json()["outcome"] == "already_initialized"
    assert retry_init.json()["committedRevisionId"] == d0
    replayed = bundle.reviewed_world_initializations.get_for_world(GLASS_ORCHARD_WORLD_ID)
    assert replayed is not None
    assert replayed.command_sha256 == init.command_sha256
    assert replayed.published_revision_id == d0
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["receipts"] == 1

    _explode_kernel(monkeypatch)
    services = direct.direct_services_from_bundle(bundle, GLASS_ORCHARD_WORLD_ID)
    assert services.binding.genesis == "reviewed_world_initialization"
    assert services.binding.legacy_buddy_revision_id is None
    assert services.binding.dungeonmind_first_revision_id == d0
    assert services.binding.dungeonmind_head_revision_id == d0
    assert direct._resolve_revision_pin(d0, services.binding) == d0

    projection = direct.project_world_graph_direct(
        services, _projection_request(revision_pin=d0)
    )
    node_ids = {node.node_id for node in projection.nodes}
    assert "obj_session22_vial" in node_ids
    assert "mystery_puddles" in node_ids
    assert projection.snapshot.revision_id == d0

    reread_d0 = bundle.world_graph.get_revision(GLASS_ORCHARD_WORLD_ID, d0)
    assert reread_d0 is not None
    assert stored_d0.graph_payload == payload_before
    assert reread_d0.graph_payload == payload_before
    assert [item.get("evidence_ref_id") for item in (reread_d0.graph_payload.get("evidence_refs") or [])] == evidence_ids_before

    search = direct.search_world_graph_direct(
        services,
        WorldGraphSearchRequest(
            schema="dmb_world_graph_search_request_v1",
            queryText="vial",
            **_retrieval_context(revision_pin=d0),
        ),
    )
    assert "obj_session22_vial" in set(search.matched_node_ids)

    exact = direct.get_object_direct(
        services,
        WorldGraphObjectRequest(
            schema="dmb_world_graph_object_request_v1",
            nodeId="obj_session22_vial",
            **_retrieval_context(revision_pin=d0),
        ),
    )
    assert [node.node_id for node in exact.nodes] == ["obj_session22_vial"]

    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    assert adapter.current_head(GLASS_ORCHARD_WORLD_ID).revision_id == d0
    d0_view = adapter.read_revision(GLASS_ORCHARD_WORLD_ID, d0)
    assert d0_view.parent_revision_id is None
    assert "obj_session22_vial" in d0_view.objects
    context = adapter.mutation_context(GLASS_ORCHARD_WORLD_ID, d0)
    assert context.revision_id == d0
    assert context.head_revision_id == d0

    monkeypatch.setattr(authority_tests, "WORLD_ID", GLASS_ORCHARD_WORLD_ID)
    monkeypatch.setattr(authority_tests, "CAMPAIGN_ID", GLASS_ORCHARD_WORLD_ID)
    monkeypatch.setenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", str(tmp_path))
    mutation_context = world_graph_writes.load_production_mutation_context(
        GLASS_ORCHARD_WORLD_ID, database_url=dsn
    )
    assert mutation_context.revision_id == d0
    package, accepted_ids = _seal_tinker_package(
        mutation_context,
        tmp_path,
        preview_slug="d2c3-continuity-child",
        node_id=CHILD_NODE_ID,
        label="D2C3 Continuity Child",
    )
    _, contribution = resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal="gm@confirm",
        world_id_hint=GLASS_ORCHARD_WORLD_ID,
        root=None,
        mutation_context=mutation_context,
        expected_parent_revision_id=d0,
        assertion_ids=None,
        verify_source=False,
    )
    operation_id = contribution.contribution_id
    request = WorldGraphPublishRequest(
        world_id=GLASS_ORCHARD_WORLD_ID,
        expected_parent_revision_id=d0,
        authority_operation_id=operation_id,
        actor="gm@confirm",
        contribution=contribution,
        accepted_assertion_ids=tuple(accepted_ids),
        decision="create_new",
        threat_node_id=CHILD_NODE_ID,
        operation_namespace="threat",
    )
    receipt = adapter.publish(request)
    assert receipt.published is True
    assert receipt.parent_revision_id == d0
    d1 = receipt.published_revision_id
    assert d1 != d0
    assert adapter.current_head(GLASS_ORCHARD_WORLD_ID).revision_id == d1

    child = adapter.read_revision(GLASS_ORCHARD_WORLD_ID, d1)
    assert child.parent_revision_id == d0
    assert CHILD_NODE_ID in child.objects
    assert "obj_session22_vial" in child.objects

    retry = adapter.publish(request)
    assert retry.outcome == "already_applied"
    assert retry.published_revision_id == d1
    recovered = adapter.recover(
        GLASS_ORCHARD_WORLD_ID,
        operation_id,
        expected_parent_revision_id=d0,
        contribution=contribution,
        actor="gm@confirm",
        operation_namespace="threat",
    )
    assert recovered is not None
    assert recovered.published_revision_id == d1
    assert recovered.parent_revision_id == d0
    assert adapter.current_head(GLASS_ORCHARD_WORLD_ID).revision_id == d1

    after = _counts(dsn, GLASS_ORCHARD_WORLD_ID)
    assert after["receipts"] == 1
    assert after["adoptions"] == 0
    assert after["revisions"] == 2
    assert after["heads"] == 1
    assert not glass_dir.exists()

    child_services = direct.direct_services_from_bundle(
        _bundle(dsn), GLASS_ORCHARD_WORLD_ID
    )
    assert child_services.binding.genesis == "reviewed_world_initialization"
    assert child_services.binding.legacy_buddy_revision_id is None
    assert child_services.binding.dungeonmind_first_revision_id == d0
    assert child_services.binding.dungeonmind_head_revision_id == d1
    child_projection = direct.project_world_graph_direct(
        child_services, _projection_request(revision_pin=d1)
    )
    child_ids = {node.node_id for node in child_projection.nodes}
    assert "obj_session22_vial" in child_ids
    assert "mystery_puddles" in child_ids
    assert child_projection.snapshot.revision_id == d1
