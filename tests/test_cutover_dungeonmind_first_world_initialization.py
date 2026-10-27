"""CUTOVER D.2C2: native first-world initialization behind DungeonMind authority."""


from __future__ import annotations


import ast
import hashlib
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
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
    WorldGraphInitializationRequest,
)
from apps.live_control_server.ports.world_graph_initialization_access import (
    get_world_graph_initialization_authority,
)
from apps.live_control_server.services.first_world_graph_publication import (
    _initialization_request,
)
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
)
from tests._cutover_d3a_blocker_safe_fixtures import (
    TRUNCATE_SQL,
    ensure_migrated as _ensure_migrated,
    require_test_dsn as _test_dsn,
)
from tests._cutover_d3a_blocker_safe_fixtures import (
    FIRST_WORLD_CONFIRM_URL,
    FIRST_WORLD_PREPARE_URL,
    first_world_confirm_body as _first_world_confirm_body,
    first_world_decisions as _first_world_decisions,
    first_world_prepare_body as _first_world_prepare_body,
    _mutate_extraction_candidate,
    write_glass_orchard_bld08_run as _write_glass_orchard_bld08_run,
)

pytest_plugins = ("tests.application_state.conftest",)


REPO_ROOT = Path(__file__).resolve().parents[1]
REJECTED_NODE_ID = "obj_rejected_extra"
NATIVE_RESERVED_WORLD_ID = "world:" + "1" * 32
LOCAL_TOKEN = "reviewed-world-provisioning-local-token-long-enough"


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


def test_projection_constructor_consumes_reviewed_world_initializations() -> None:
    source = (
        REPO_ROOT
        / "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py"
    ).read_text(encoding="utf-8")
    assert "reviewed_world_initializations=bundle.reviewed_world_initializations" in source
    assert "WorldGraphProjectionService(" in source


def test_factory_is_dungeonmind_only_and_rejects_alternate_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    prod = tmp_path / "prod"
    other = tmp_path / "other"
    prod.mkdir()
    other.mkdir()
    monkeypatch.setenv(
        config.WORLD_GRAPH_AUTHORITY_ENV, config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(prod))
    native = get_world_graph_initialization_authority(world_root=prod)
    assert isinstance(native, DungeonMindWorldGraphInitializationAdapter)
    with pytest.raises(config.WorldGraphAuthorityConfigurationError, match="alternate"):
        get_world_graph_initialization_authority(world_root=other)


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


@dataclass
class _FakeReceipt:
    initialization_id: str = "init-1"
    published_revision_id: str = "rev:d0"
    initialized_at: datetime = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeReviewedInit:
    def __init__(self, result=None, error: BaseException | None = None) -> None:
        self._result = result
        self._error = error


    def get_for_world(self, world_id: str):
        if self._error is not None:
            raise self._error
        return self._result


class _FakeGraph:
    def __init__(self, head=None, error: BaseException | None = None) -> None:
        self._head = head
        self._error = error


    def get_head(self, world_id: str):
        if self._error is not None:
            raise self._error
        return self._head


class _FakeBundle:
    def __init__(
        self,
        *,
        receipt=None,
        receipt_error: BaseException | None = None,
        head=None,
        head_error: BaseException | None = None,
    ) -> None:
        self.reviewed_world_initializations = _FakeReviewedInit(receipt, receipt_error)
        self.world_graph = _FakeGraph(head, head_error)


def _dummy_initialization_request() -> WorldGraphInitializationRequest:
    return WorldGraphInitializationRequest(
        world_id="the-glass-orchard",
        campaign_id="the-glass-orchard",
        initialization_id="dmb:first-world:test",
        source_plan_schema="dmb_first_world_plan_v1",
        source_plan_id="plan",
        source_plan_sha256="0" * 64,
        actor="live_control:graph_review_confirm",
        source_artifact=object(),
        source_revision_token="rev:src",
        source_uri="object://src",
        reviewed_contribution=object(),
    )


def test_probe_maps_verified_receipt_integrity_not_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dungeonmind.domain.errors import PersistenceIntegrityError


    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")
    bundle = _FakeBundle(
        receipt_error=PersistenceIntegrityError(
            "reviewed-world initialization receipt references a missing revision"
        )
    )
    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)
    with pytest.raises(WorldGraphInitializationError) as exc_info:
        adapter.probe("the-glass-orchard")
    assert type(exc_info.value) is WorldGraphInitializationError
    assert exc_info.value.code == "integrity_failure"


def test_initialize_maps_verified_receipt_integrity_without_leaking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dungeonmind.domain.errors import PersistenceIntegrityError


    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")
    bundle = _FakeBundle(
        receipt_error=PersistenceIntegrityError(
            "reviewed-world initialization receipt references a missing revision"
        )
    )
    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)
    with pytest.raises(WorldGraphInitializationError) as exc_info:
        adapter.initialize(_dummy_initialization_request())
    assert type(exc_info.value) is WorldGraphInitializationError
    assert exc_info.value.code == "integrity_failure"


def test_probe_maps_unavailable_receipt_read_to_authority_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dungeonmind.domain.errors import PersistenceUnavailableError


    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")
    bundle = _FakeBundle(
        receipt_error=PersistenceUnavailableError("initialization repository unavailable")
    )
    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)
    with pytest.raises(WorldGraphInitializationError) as exc_info:
        adapter.probe("the-glass-orchard")
    assert exc_info.value.code == "authority_unavailable"


def test_probe_and_initialize_treat_receipt_without_head_as_integrity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    adapter = DungeonMindWorldGraphInitializationAdapter(database_url="postgresql://unused")
    bundle = _FakeBundle(receipt=_FakeReceipt(), head=None)
    monkeypatch.setattr(adapter, "_bundle", lambda: bundle)
    with pytest.raises(WorldGraphInitializationError) as probe_exc:
        adapter.probe("the-glass-orchard")
    assert probe_exc.value.code == "integrity_failure"
    assert probe_exc.value.details.get("reason") == "reviewed_init_receipt_without_head"
    with pytest.raises(WorldGraphInitializationError) as init_exc:
        adapter.initialize(_dummy_initialization_request())
    assert init_exc.value.code == "integrity_failure"
    assert init_exc.value.details.get("reason") == "reviewed_init_receipt_without_head"


def _add_rejected_node(payload: dict) -> None:
    nodes = list(payload.get("nodes") or [])
    template = dict(nodes[0])
    template["node_id"] = REJECTED_NODE_ID
    template["label"] = "Rejected extra"
    payload["nodes"] = [*nodes, template]


@pytest.fixture
def native_first_world_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
):
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn
    )
    dsn = _test_dsn()
    _ensure_migrated(dsn)
    from dungeonmind.infrastructure.postgres import PostgresDatabase


    database = PostgresDatabase(dsn)
    with database.connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()


    from apps.live_control_server import config as wg_config


    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    monkeypatch.setenv(
        wg_config.WORLD_GRAPH_AUTHORITY_ENV,
        wg_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
    )
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
    from apps.live_control_server.services import world_container_registry
    from uuid import UUID
    monkeypatch.setattr(world_container_registry, "uuid4", lambda: UUID("1" * 32))
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", LOCAL_TOKEN)
    client = TestClient(create_app(), client=("127.0.0.1", 50000), headers={"Authorization": f"Bearer {LOCAL_TOKEN}"})
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


def _sealed_native_request(repo: Path, plan: dict) -> WorldGraphInitializationRequest:
    from apps.live_control_server.services.extract_promote import (
        _load_typed_worldbuilding_preview_for_run,
    )
    from apps.live_control_server.services.first_world_graph import (
        materialize_first_world_plan,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from graph_memory.worldbuilding_write_plan import WorldbuildingDispositionInput


    resolved = resolve_promotable_ingest_run(plan["runId"], root=repo)
    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(resolved)
    rematerialized = materialize_first_world_plan(
        preview=typed_preview,
        world_id=plan["worldId"],
        native_target=FirstWorldGraphConfirmRequest.model_validate(_first_world_confirm_body(plan)).plan.native_target,
        run_id=plan["runId"],
        source_artifact_id=plan["sourceArtifactId"],
        source_revision_id=plan["sourceRevisionId"],
        source_uri=resolved.sealed_source_uri,
        source_evidence_sha256=plan["sourceEvidenceSha256"],
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
    return _initialization_request(
        plan=FirstWorldGraphConfirmRequest.model_validate(
            _first_world_confirm_body(plan)
        ).plan,
        rematerialized=rematerialized,
        resolved=resolved,
    )


def _bundle(dsn: str):
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresRepositoryBundle,
    )


    return PostgresRepositoryBundle(PostgresDatabase(dsn))


def _project_native(dsn: str, *, world_id: str, campaign_id: str | None):
    from dungeonmind.application.world_graph_projection import WorldGraphProjectionService
    from dungeonmind.contracts.projection import Admissibility
    from dungeonmind.contracts.projection_v2 import ScopeModeV2, WorldGraphProjectionRequestV2


    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _build_graph_reader,
    )


    bundle = _bundle(dsn)
    result = WorldGraphProjectionService(
        world_graph=bundle.world_graph,
        sources=bundle.sources,
        graph_reader=_build_graph_reader(),
        reviewed_world_initializations=bundle.reviewed_world_initializations,
    ).project(
        WorldGraphProjectionRequestV2(
            world_id=world_id,
            campaign_id=campaign_id,
            admissibility=Admissibility.GM,
            scope_mode=ScopeModeV2.WORLD if campaign_id is None else ScopeModeV2.CAMPAIGN,
        )
    )
    return result, bundle


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


def _admit_recap_source_fixture(dsn: str, world_id: str, source: Path, artifact_id: str, session_id: str):
    """Use the real source owner before preparing or publishing recap fixtures."""
    from types import SimpleNamespace
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.ports.world_graph_source_admission import WorldGraphSourceAdmissionRequest

    content_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    now = datetime.now(UTC)
    artifact = SimpleNamespace(
        source_artifact_id=artifact_id, source_domain="recap", campaign_id="longmont-c2",
        session_id=session_id, uri=str(source), content_sha256=content_sha256,
        artifact_kind="markdown", document_class="recap", authority_state="reviewed",
        visibility_state="internal", world_id=world_id, workspace_document_id=None,
        workspace_document_revision=None, lineage={}, status="active", created_at=now, updated_at=now,
    )
    authority = DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn)
    admitted = authority.prove_or_admit(WorldGraphSourceAdmissionRequest(
        world_id=world_id, campaign_id="longmont-c2", source_artifact=artifact,
        source_revision_token="sha256:" + content_sha256, source_uri=str(source),
    ))
    assert admitted.source_artifact_id == artifact_id
    assert admitted.content_sha256 == content_sha256
    return artifact, authority


@pytest.mark.integration
def test_native_recap_genesis_is_atomic_and_replays_exactly(
    native_first_world_client,
) -> None:
    """Real PostgreSQL witness for the party-registry zero-parent profile."""
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisConfirmRequest,
        RecapWorldGenesisPrepareRequest,
    )
    from apps.live_control_server.services.recap_world_genesis import (
        RecapWorldGenesisError,
        confirm_recap_world_genesis,
        prepare_recap_world_genesis,
    )
    from apps.live_control_server.ports.world_graph_authority import WorldGraphPublishRequest
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
    from tests._cutover_d3a_blocker_safe_fixtures import _seal_tinker_package

    _client, _world_root, repo, dsn = native_first_world_client
    registry = repo / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json"
    registry.parent.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json",
        registry,
    )
    world_id = "world:recap-genesis-c1"
    authority = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    plan = prepare_recap_world_genesis(
        RecapWorldGenesisPrepareRequest(
            world_id=world_id, campaign_id="longmont-c1", baseline_roster_key="1", requested_by="test"
        ), repo=repo, authority=authority,
    )
    assert _counts(dsn, world_id) == {
        "heads": 0, "revisions": 0, "receipts": 0, "contributions": 0,
        "artifacts": 0, "revisions_src": 0, "adoptions": 0,
    }
    first = confirm_recap_world_genesis(
        RecapWorldGenesisConfirmRequest(plan=plan, confirming_principal="test"), repo=repo, authority=authority
    )
    assert first.source_domain_key == "party_registry"
    assert first.contribution_payload_sha256 == plan.contribution_payload_sha256
    assert first.parent_revision_id is None
    assert first.command_sha256
    assert first.confirmed_by == "test"
    assert first.initialized_at is not None
    assert _counts(dsn, world_id) == {
        "heads": 1, "revisions": 1, "receipts": 1, "contributions": 1,
        "artifacts": 1, "revisions_src": 1, "adoptions": 0,
    }
    bundle = _bundle(dsn)
    revision = bundle.world_graph.get_revision(world_id, first.published_revision_id)
    assert revision is not None
    assert revision.revision.parent_revision_id is None
    assert {item["object_id"] for item in revision.graph_payload["objects"]} == set(plan.pc_object_ids)
    artifact = bundle.sources.get_artifact(plan.source_artifact_id)
    assert artifact is not None
    assert artifact.source_domain_key == "party_registry"
    assert artifact.source_domain.value == "other"
    second = confirm_recap_world_genesis(
        RecapWorldGenesisConfirmRequest(plan=plan, confirming_principal="test"), repo=repo, authority=authority
    )
    assert second.published_revision_id == first.published_revision_id
    assert second.outcome == "already_initialized"
    assert _counts(dsn, world_id)["revisions"] == 1
    with pytest.raises(RecapWorldGenesisError) as changed_actor:
        confirm_recap_world_genesis(
            RecapWorldGenesisConfirmRequest(
                plan=plan, confirming_principal="other-actor"
            ),
            repo=repo,
            authority=authority,
        )
    assert changed_actor.value.code == "idempotency_conflict"
    assert _counts(dsn, world_id)["revisions"] == 1

    graph_authority = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    d0 = first.published_revision_id
    mutation_context = graph_authority.mutation_context(world_id, d0)
    assert mutation_context.revision_id == d0
    assert mutation_context.head_revision_id == d0
    package, accepted_ids = _seal_tinker_package(
        mutation_context,
        repo,
        preview_slug="recap-genesis-child",
        node_id="obj_recap_genesis_child",
        label="Recap Genesis Child",
    )
    _admit_recap_source_fixture(
        dsn, world_id, repo / "recap-genesis-child-recap.md",
        "artifact:recap:longmont-c2:recap-genesis-child", "session-26",
    )
    _, contribution = resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal="test",
        world_id_hint=world_id,
        root=None,
        mutation_context=mutation_context,
        expected_parent_revision_id=d0,
        assertion_ids=None,
        verify_source=True,
        repo_root=repo,
    )
    child = graph_authority.publish(
        WorldGraphPublishRequest(
            world_id=world_id,
            expected_parent_revision_id=d0,
            authority_operation_id=contribution.contribution_id,
            actor="test",
            contribution=contribution,
            accepted_assertion_ids=tuple(accepted_ids),
            decision="create_new",
            threat_node_id="obj_recap_genesis_child",
            operation_namespace="threat",
        )
    )
    assert child.published is True
    assert child.parent_revision_id == d0
    assert graph_authority.read_revision(world_id, child.published_revision_id).parent_revision_id == d0


@pytest.mark.integration
def test_native_review_prepare_confirm_with_buddy_graph_absent(
    native_first_world_client,
) -> None:
    client, world_root, repo, dsn = native_first_world_client
    glass_dir = world_root / "graph_memory" / "worlds" / NATIVE_RESERVED_WORLD_ID
    run_id, plan = _prepare_native_plan(client, repo, with_rejected=True)
    assert not glass_dir.exists()
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["receipts"] == 0


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
    counts = _counts(dsn, NATIVE_RESERVED_WORLD_ID)
    assert counts["heads"] == 1
    assert counts["revisions"] == 1
    assert counts["receipts"] == 1
    assert counts["contributions"] == 1
    assert counts["artifacts"] == 1
    assert counts["revisions_src"] == 1
    assert counts["adoptions"] == 0
    assert not (world_root / "graph_memory" / "worlds" / NATIVE_RESERVED_WORLD_ID).exists()


    bundle = _bundle(dsn)
    head = bundle.world_graph.get_head(NATIVE_RESERVED_WORLD_ID)
    assert head is not None
    assert head.head_revision_id == published
    stored = bundle.world_graph.get_revision(NATIVE_RESERVED_WORLD_ID, published)
    assert stored is not None
    assert stored.revision.parent_revision_id is None
    payload = stored.graph_payload
    object_ids = {item["object_id"] for item in payload.get("objects") or []}
    assert "obj_session22_vial" in object_ids
    assert "mystery_puddles" in object_ids
    assert REJECTED_NODE_ID not in object_ids


    init = bundle.reviewed_world_initializations.get_for_world(NATIVE_RESERVED_WORLD_ID)
    assert init is not None
    contribution = bundle.contributions.get(
        NATIVE_RESERVED_WORLD_ID, init.reviewed_contribution_id
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
    artifact_ids = {row[0] for row in _artifact_ids(dsn, NATIVE_RESERVED_WORLD_ID)}
    revision_ids = {row[0] for row in _revision_ids(dsn, NATIVE_RESERVED_WORLD_ID)}
    assert artifact_ids
    assert revision_ids
    for assertion in contribution.assertions:
        assert assertion.source_artifact_id in artifact_ids
        assert assertion.source_revision_id in revision_ids
        for ref in assertion.evidence_refs:
            assert ref.source_artifact_id in artifact_ids
            assert ref.source_revision_id in revision_ids
            assert ref.source_domain.value == "worldbuilding"


    from dungeonmind.contracts.evidence import SourceDomain


    stored_artifact = bundle.sources.get_artifact(next(iter(artifact_ids)))
    assert stored_artifact is not None
    assert stored_artifact.source_domain is SourceDomain.WORLDBUILDING
    assert stored_artifact.source_domain_key == "worldbuilding"
    for record in payload.get("evidence_refs") or []:
        assert record["source_domain"] == "worldbuilding"
        assert record["source_domain_key"] == "worldbuilding"
    for ref in contribution.assertions[0].evidence_refs:
        assert ref.schema_version == "dm_evidence_ref_v2"
        assert ref.source_span_ref_id and ref.can_open_source and ref.can_highlight_span
        assert ":dm-extraction-v3:" in ref.evidence_ref_id


    projected, _ = _project_native(
        dsn,
        world_id=NATIVE_RESERVED_WORLD_ID,
        campaign_id=None,
    )
    admitted = set(projected.graph.objects)
    assert "obj_session22_vial" in admitted
    assert "mystery_puddles" in admitted


@pytest.mark.integration
def test_current_command_carries_only_exact_readable_typed_spans(native_first_world_client):
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import _build_command
    client, _world, repo, _dsn = native_first_world_client
    _run, plan = _prepare_native_plan(client, repo, with_rejected=True)
    command = _build_command(_sealed_native_request(repo, plan), requested_initialized_at=datetime(2026, 8, 27, tzinfo=UTC))
    assert command.schema_version == "dm_reviewed_world_initialization_command_v2"
    assert command.producer_profile == "worldbuilding_extraction"
    assert command.reviewed_contribution.schema_version == "dm_graph_contribution_v3"
    refs = [ref for a in command.reviewed_contribution.assertions for ref in a.evidence_refs]
    assert refs and all(ref.source_span_ref_id and ref.can_open_source and ref.can_highlight_span for ref in refs)
    assert all(ref.source_domain_key == "worldbuilding" for ref in refs)


@pytest.mark.integration
def test_native_exact_retry_reuses_receipt_timestamp(
    native_first_world_client,
) -> None:
    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    bundle = _bundle(dsn)
    original = bundle.reviewed_world_initializations.get_for_world(NATIVE_RESERVED_WORLD_ID)
    assert original is not None
    retry = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert retry.status_code == 200, retry.text
    assert retry.json()["outcome"] == "already_initialized"
    assert retry.json()["committedRevisionId"] == first.json()["committedRevisionId"]
    assert retry.json()["baselineRevisionId"] is None
    replayed = bundle.reviewed_world_initializations.get_for_world(NATIVE_RESERVED_WORLD_ID)
    assert replayed is not None
    assert replayed.command_sha256 == original.command_sha256
    assert replayed.initialized_at == original.initialized_at
    assert replayed.published_revision_id == original.published_revision_id
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["revisions"] == 1
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["receipts"] == 1


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
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["revisions"] == 1
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["receipts"] == 1


@pytest.mark.integration
def test_native_synchronized_identical_confirms_recover_via_timestamp_conflict(
    native_first_world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dungeonmind.application import reviewed_world_initialization as rwi
    from dungeonmind.domain.errors import IdempotencyConflictError


    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_initialization_adapter as init_mod,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    request = _sealed_native_request(repo, plan)
    first_stamp = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
    second_stamp = first_stamp + timedelta(seconds=7)
    barrier = threading.Barrier(2, timeout=20)
    receipt_reads: list[str | None] = []
    provider_calls: list[dict[str, object]] = []


    real_verified = init_mod._get_verified_reviewed_init_receipt


    def tracking_verified(repository, world_id):
        receipt = real_verified(repository, world_id)
        receipt_reads.append(None if receipt is None else str(receipt.initialization_id))
        return receipt


    monkeypatch.setattr(init_mod, "_get_verified_reviewed_init_receipt", tracking_verified)


    real_provider = rwi.initialize_reviewed_world


    def tracking_provider(command, **kwargs):
        record: dict[str, object] = {
            "requested_initialized_at": command.requested_initialized_at,
            "outcome": "ok",
        }
        try:
            result = real_provider(command, **kwargs)
        except IdempotencyConflictError:
            record["outcome"] = "conflict"
            provider_calls.append(record)
            raise
        provider_calls.append(record)
        return result


    monkeypatch.setattr(rwi, "initialize_reviewed_world", tracking_provider)


    adapters = [
        DungeonMindWorldGraphInitializationAdapter(
            database_url=dsn,
            now=lambda stamp=first_stamp: stamp,
            after_uninitialized_receipt=barrier.wait,
        ),
        DungeonMindWorldGraphInitializationAdapter(
            database_url=dsn,
            now=lambda stamp=second_stamp: stamp,
            after_uninitialized_receipt=barrier.wait,
        ),
    ]


    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda adapter: adapter.initialize(request), adapters))


    outcomes = sorted(item.outcome for item in results)
    assert outcomes == ["already_initialized", "initialized"]
    published = {item.published_revision_id for item in results}
    assert len(published) == 1
    assert {item.command_sha256 for item in results} == {
        results[0].command_sha256
    }
    first_attempt_stamps = {
        call["requested_initialized_at"]
        for call in provider_calls
        if call["requested_initialized_at"] in {first_stamp, second_stamp}
    }
    assert first_attempt_stamps == {first_stamp, second_stamp}
    conflicts = [call for call in provider_calls if call["outcome"] == "conflict"]
    successes = [call for call in provider_calls if call["outcome"] == "ok"]
    assert len(conflicts) == 1
    assert len(provider_calls) == 3
    assert len(successes) == 2
    winner_stamp = next(
        call["requested_initialized_at"]
        for call in provider_calls
        if call["outcome"] == "ok"
        and call["requested_initialized_at"] in {first_stamp, second_stamp}
    )
    replay_stamps = [
        call["requested_initialized_at"]
        for call in successes
        if call["requested_initialized_at"] == winner_stamp
    ]
    assert len(replay_stamps) == 2
    assert receipt_reads.count(None) == 2
    assert sum(1 for item in receipt_reads if item is not None) == 1
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["revisions"] == 1
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["receipts"] == 1


@pytest.mark.integration
def test_native_changed_command_conflicts(native_first_world_client) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    request = _sealed_native_request(repo, plan)
    changed = replace(request, actor="attacker:not-the-confirming-principal")
    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    with pytest.raises(WorldGraphInitializationError) as exc_info:
        adapter.initialize(changed)
    assert exc_info.value.code == "idempotency_conflict"
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["revisions"] == 1


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
            (NATIVE_RESERVED_WORLD_ID,),
        )
        conn.commit()
    second = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "native_graph_binding_changed"
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["revisions"] == 1


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
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["receipts"] == 0


@pytest.mark.integration
def test_native_receipt_without_head_is_integrity_not_unavailable(
    native_first_world_client,
) -> None:
    import psycopg


    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    client, _world, repo, dsn = native_first_world_client
    run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "DELETE FROM dungeonmind.world_graph_heads WHERE world_id = %s",
            (NATIVE_RESERVED_WORLD_ID,),
        )
        conn.commit()
    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    with pytest.raises(WorldGraphInitializationError) as probe_exc:
        adapter.probe(NATIVE_RESERVED_WORLD_ID)
    assert type(probe_exc.value) is WorldGraphInitializationError
    assert probe_exc.value.code == "integrity_failure"
    assert probe_exc.value.details.get("reason") == "reviewed_init_receipt_without_head"
    with pytest.raises(WorldGraphInitializationError) as init_exc:
        adapter.initialize(_sealed_native_request(repo, plan))
    assert init_exc.value.code == "integrity_failure"
    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 200, review.text
    assert review.json()["worldState"] != "initialized"
    assert review.json()["firstWorldPublishEligible"] is False
    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 409, confirm.text
    assert confirm.status_code != 503
    assert confirm.json()["code"] == "first_world_initialization_failed"


@pytest.mark.integration
def test_native_corrupt_d0_receipt_is_integrity_not_unavailable(
    native_first_world_client,
) -> None:
    import psycopg


    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )


    client, _world, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE dungeonmind.graph_revisions "
            "SET parent_revision_id = revision_id "
            "WHERE world_id = %s",
            (NATIVE_RESERVED_WORLD_ID,),
        )
        conn.commit()
    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    with pytest.raises(WorldGraphInitializationError) as probe_exc:
        adapter.probe(NATIVE_RESERVED_WORLD_ID)
    assert type(probe_exc.value) is WorldGraphInitializationError
    assert probe_exc.value.code == "integrity_failure"
    with pytest.raises(WorldGraphInitializationError) as init_exc:
        adapter.initialize(_sealed_native_request(repo, plan))
    assert type(init_exc.value) is WorldGraphInitializationError
    assert init_exc.value.code == "integrity_failure"
    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 409, confirm.text
    assert confirm.status_code != 503
    assert confirm.json()["code"] == "first_world_initialization_failed"


@pytest.mark.integration
def test_candidate_admission_real_postgres_sequence(native_first_world_client) -> None:
    """D0 -> D1 -> D2, partial eligibility, fatal integrity, exact retry."""
    import hashlib
    import json

    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        bind_identity_ledger_to_package,
    )
    from apps.live_control_server.models.candidate_graph_admission import (
        CandidateAdmissionIntegrityError,
    )
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisConfirmRequest,
        RecapWorldGenesisPrepareRequest,
    )
    from apps.live_control_server.ports.world_graph_authority import WorldGraphPublishRequest
    from apps.live_control_server.services.candidate_graph_admission import (
        confirm_candidate_graph_admission,
        prepare_candidate_graph_admission,
    )
    from apps.live_control_server.services.recap_world_genesis import (
        confirm_recap_world_genesis,
        prepare_recap_world_genesis,
    )
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
    from tests.test_candidate_graph_admission_contract import _candidate, _node

    _client, _world_root, repo, dsn = native_first_world_client
    registry = repo / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json"
    registry.parent.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json",
        registry,
    )
    world_id = "world:candidate-admission-pg"
    genesis_authority = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    genesis_plan = prepare_recap_world_genesis(
        RecapWorldGenesisPrepareRequest(
            world_id=world_id,
            campaign_id="longmont-c1",
            baseline_roster_key="1",
            requested_by="candidate-admission-test",
        ),
        repo=repo,
        authority=genesis_authority,
    )
    genesis = confirm_recap_world_genesis(
        RecapWorldGenesisConfirmRequest(
            plan=genesis_plan, confirming_principal="candidate-admission-test"
        ),
        repo=repo,
        authority=genesis_authority,
    )
    d0 = genesis.published_revision_id

    source = repo / "session-9.md"
    source.write_text("Brin visits the Medical Wing. Nell waits outside.\n", encoding="utf-8")
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    source_revision = f"sha256:{source_digest}"
    artifact_id = "artifact:recap:longmont-c2:session-9"
    artifact, source_authority = _admit_recap_source_fixture(
        dsn, world_id, source, artifact_id, "session-9",
    )
    graph_authority = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)

    def prepare(candidate: dict, parent: str):
        context = graph_authority.mutation_context(world_id, parent)
        result = prepare_candidate_graph_admission(
            candidate_graph=candidate,
            source_uri=str(source),
            source_revision_id=source_revision,
            prepared_by="candidate-admission-test",
            world_id=world_id,
            source_artifact_id=artifact_id,
            source_artifact=artifact,
            source_admission=source_authority,
            campaign_scope="longmont-c2",
            repo_root=repo,
            mutation_context=context,
        )
        return result, context, bind_identity_ledger_to_package(
            result.review_package, context
        )

    def publish(candidate: dict, package: dict, context):
        _verified, contribution = resolve_merged_contribution_from_package(
            review_package=package,
            confirming_principal="candidate-admission-test",
            world_id_hint=world_id,
            expected_parent_revision_id=context.revision_id,
            assertion_ids=None,
            mutation_context=context,
            verify_source=True,
            repo_root=repo,
        )
        return confirm_candidate_graph_admission(
            review_package=package,
            candidate_graph=candidate,
            governed_confirm=lambda: graph_authority.publish(
                WorldGraphPublishRequest(
                    world_id=world_id,
                    expected_parent_revision_id=context.revision_id,
                    authority_operation_id=contribution.contribution_id,
                    actor="candidate-admission-test",
                    contribution=contribution,
                    accepted_assertion_ids=tuple(
                        item.assertion_id for item in contribution.accepted_assertions
                    ),
                    decision="create_new",
                    threat_node_id=candidate["nodes"][0]["node_id"],
                    operation_namespace="threat",
                )
            ),
        )

    candidate_a = _candidate()
    result_a, context_a, package_a = prepare(candidate_a, d0)
    assert graph_authority.current_head(world_id).revision_id == d0
    published_a = publish(candidate_a, package_a, context_a)
    d1 = published_a.published_revision_id
    retry_a = publish(candidate_a, package_a, context_a)
    assert retry_a.published_revision_id == d1
    assert graph_authority.current_head(world_id).revision_id == d1

    candidate_b = _candidate(unsupported=True)
    # D1 already contains Brin. Exercise a real second admitted fact rather
    # than expecting the host to publish an empty duplicate contribution.
    candidate_b["nodes"][0] = _node("candidate:nell", "character")
    candidate_b["edges"][0]["from_node_id"] = "candidate:nell"
    result_b, context_b, package_b = prepare(candidate_b, d1)
    binding_b = package_b["effect"]["candidate_admission"]
    assert binding_b["exact_candidate_counts"]["nodes"] == 2
    assert {item["reason"] for item in binding_b["dispositions"]} == {
        "unsupported_node_type",
        "endpoint_not_admitted",
    }
    assert graph_authority.current_head(world_id).revision_id == d1
    published_b = publish(candidate_b, package_b, context_b)
    d2 = published_b.published_revision_id
    assert d2 != d1

    candidate_c = _candidate()
    candidate_c["nodes"] = [
        _node("candidate:miss-thistlebottoms-emporium", "location"),
        _node("candidate:miss-thistlebottoms-emporium", "organization"),
    ]
    with pytest.raises(CandidateAdmissionIntegrityError):
        prepare(candidate_c, d2)
    assert graph_authority.current_head(world_id).revision_id == d2
    assert result_a.review_package["effect"]["candidate_admission"]["candidate_digest"]
    assert result_b.review_package["effect"]["candidate_admission"]["candidate_digest"]
    print(
        "candidate_admission_pg_witness="
        + json.dumps(
            {
                "world_id": world_id,
                "source_artifact_id": artifact_id,
                "source_revision_id": source_revision,
                "d0": d0,
                "d1": d1,
                "d2": d2,
                "candidate_a_digest": package_a["effect"]["candidate_admission"][
                    "candidate_digest"
                ],
                "candidate_b_digest": package_b["effect"]["candidate_admission"][
                    "candidate_digest"
                ],
                "candidate_b_dispositions": binding_b["dispositions"],
                "candidate_c_failure": "duplicate_node_id",
                "model_calls": 0,
            },
            sort_keys=True,
        )
    )


@pytest.mark.integration
def test_fresh_source_receipt_survives_reviewed_graph_activation(native_first_world_client):
    from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as native
    from apps.live_control_server.services.world_container_registry import get_world_container
    from apps.live_control_server.services.managed_world_graph_projection import (
        ManagedWorldGraphProjectionRequest, project_managed_world_graph,
    )
    client, _, repo, dsn = native_first_world_client
    _, plan = _prepare_native_plan(client, repo)
    source_id = plan["workspaceDocumentId"]
    snapshot = native.get_workspace_document_snapshot(repo, source_id)
    admitted = native.admit_native_world_source(repo, source_id,
        expected_revision=snapshot.loaded_revision, expected_body_sha256=snapshot.content_sha256)
    before = get_world_container(repo, plan["worldId"]).native_graph_binding
    assert before.status == "provisioning"
    assert _bundle(dsn).world_graph.get_head(before.native_world_id) is None
    assert admitted.space_id == before.native_world_id != plan["worldId"]
    confirmed = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirmed.status_code == 200, confirmed.text
    active = get_world_container(repo, plan["worldId"]).native_graph_binding
    assert active.status == "active"
    assert active.native_world_id == before.native_world_id
    assert active.provisioning_id == before.provisioning_id
    assert active.binding_version == before.binding_version == 1
    assert native.get_native_world_source_status(repo, source_id) == admitted
    projection = project_managed_world_graph(ManagedWorldGraphProjectionRequest.model_validate({
        "schema":"dmb_managed_world_graph_projection_request_v1", "managedWorldId":plan["worldId"],
    }), root=repo)
    assert projection.native_world_id == before.native_world_id
    assert projection.projection.snapshot.revision_id == confirmed.json()["committedRevisionId"]
    assert projection.projection.nodes
    assert _bundle(dsn).world_graph.get_head(plan["worldId"]) is None


@pytest.mark.integration
def test_published_graph_recovers_after_activation_write_failure(native_first_world_client, monkeypatch):
    from apps.live_control_server.services import world_graph_binding as binding
    from apps.live_control_server.services.world_container_registry import get_world_container
    client, _, repo, dsn = native_first_world_client
    run_id, plan = _prepare_native_plan(client, repo)
    reservation = get_world_container(repo, plan["worldId"]).native_graph_binding
    original = binding._save_cas
    def unavailable(*args, **kwargs):
        raise OSError("synthetic registry write interruption")
    monkeypatch.setattr(binding, "_save_cas", unavailable)
    interrupted = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert interrupted.status_code == 503, interrupted.text
    assert interrupted.json()["code"] == "native_graph_activation_pending"
    assert get_world_container(repo, plan["worldId"]).native_graph_binding == reservation
    assert _counts(dsn, reservation.native_world_id)["revisions"] == 1
    # Reconstructing exact reviewed choices after restart retains the operation
    # and command; it cannot mint another World or another D0.
    rebuilt = client.post(FIRST_WORLD_PREPARE_URL, json=_first_world_prepare_body(run_id, _first_world_decisions()))
    assert rebuilt.status_code == 200, rebuilt.text
    assert rebuilt.json() == plan
    monkeypatch.setattr(binding, "_save_cas", original)
    recovered = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(rebuilt.json()))
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["outcome"] == "already_initialized"
    assert get_world_container(repo, plan["worldId"]).native_graph_binding.status == "active"
    assert _counts(dsn, reservation.native_world_id)["revisions"] == 1
    assert _counts(dsn, reservation.native_world_id)["receipts"] == 1


@pytest.mark.integration
@pytest.mark.parametrize("field,value", [("nativeWorldId", "world:"+"f"*32), ("provisioningId", "provision:"+"f"*32), ("bindingVersion", 2)])
def test_first_publication_rejects_tampered_native_target(native_first_world_client, field, value):
    from copy import deepcopy
    from apps.live_control_server.services.world_container_registry import get_world_container
    client, _, repo, dsn = native_first_world_client
    _, plan = _prepare_native_plan(client, repo)
    before = get_world_container(repo, plan["worldId"])
    changed = deepcopy(plan)
    changed["nativeTarget"][field] = value
    rejected = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(changed))
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "native_graph_binding_changed"
    assert _counts(dsn, before.native_graph_binding.native_world_id)["revisions"] == 0
    assert get_world_container(repo, plan["worldId"]) == before


@pytest.mark.integration
def test_first_publication_requires_gm_auth_before_run_resolution(native_first_world_client):
    from fastapi.testclient import TestClient
    client, _, _, _ = native_first_world_client
    unauthenticated = TestClient(create_app(), client=("127.0.0.1",50000))
    response = unauthenticated.post(FIRST_WORLD_PREPARE_URL, json=_first_world_prepare_body("missing", _first_world_decisions()))
    assert response.status_code == 401


class _PreflightSpy:
    def __init__(self, native, *, preflight_error=None, initialize_error=None, probe_error=None):
        self.native = native
        self.preflight_error = preflight_error
        self.initialize_error = initialize_error
        self.probe_error = probe_error
        self.preflights = 0
        self.initializations = 0

    def probe(self, world_id):
        if self.probe_error:
            raise self.probe_error
        return self.native.probe(world_id)

    def preflight(self, request):
        self.preflights += 1
        if self.preflight_error:
            raise self.preflight_error
        self.native.preflight(request)

    def initialize(self, request):
        self.initializations += 1
        if self.initialize_error:
            raise self.initialize_error
        return self.native.initialize(request)


def _install_preflight_spy(monkeypatch, world_root, **kwargs):
    import apps.live_control_server.services.first_world_graph_publication as service
    spy = _PreflightSpy(get_world_graph_initialization_authority(world_root=world_root), **kwargs)
    monkeypatch.setattr(service, "get_world_graph_initialization_authority", lambda **_: spy)
    return spy


def _invalid_endpoint():
    return WorldGraphInitializationError(
        "endpoint kinds are not admitted", code="inexpressible",
        details={"assertion_id": "asrt:invalid", "buddy_predicate": "located_in",
                 "subject_dm_kind": "location", "object_dm_kind": "npc", "reason": "invalid_endpoint_kinds"},
    )


def test_prepare_preflight_rejects_before_sealed_plan_or_initialization(native_first_world_client, monkeypatch):
    client, world_root, repo, _dsn = native_first_world_client
    spy = _install_preflight_spy(monkeypatch, world_root, preflight_error=_invalid_endpoint())
    run_id, _source = _write_glass_orchard_bld08_run(repo)
    response = client.post(FIRST_WORLD_PREPARE_URL, json=_first_world_prepare_body(run_id, _first_world_decisions()))
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "dungeonmind_inexpressible"
    assert body["failureResult"]["schema"] == "dmb_first_world_preflight_failure_v1"
    assert body["failureResult"]["failure"]["buddy_predicate"] == "located_in"
    assert spy.preflights == 1
    assert spy.initializations == 0
    assert spy.native.probe(NATIVE_RESERVED_WORLD_ID).state == "uninitialized"


def test_retained_invalid_confirm_proves_only_this_request_did_not_invoke(native_first_world_client, monkeypatch):
    client, world_root, repo, _dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    spy = _install_preflight_spy(monkeypatch, world_root, preflight_error=_invalid_endpoint())
    response = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "first_world_confirm_not_invoked"
    proof = body["failureResult"]
    assert proof["schema"] == "dmb_first_world_confirm_not_invoked_v1"
    assert proof["initializationInvoked"] is False
    assert proof["worldId"] == plan["worldId"]
    assert proof["nativeWorldId"] == plan["nativeTarget"]["nativeWorldId"]
    assert proof["initializationId"] == plan["nativeTarget"]["provisioningId"]
    assert proof["planId"] == plan["planId"]
    assert proof["planDigest"] == plan["planDigest"]
    assert spy.preflights == 1
    assert spy.initializations == 0


@pytest.mark.parametrize("stage,code", [("probe", "authority_unavailable"), ("preflight", "authority_unavailable"),
    ("initialize", "inexpressible"), ("initialize", "authority_unavailable")])
def test_unknown_or_post_invoke_failure_never_grants_release(native_first_world_client, monkeypatch, stage, code):
    client, world_root, repo, _dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    spy = _install_preflight_spy(monkeypatch, world_root,
        **{stage + "_error": WorldGraphInitializationError("failure", code=code)})
    response = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert response.status_code >= 400, response.text
    assert response.json()["code"] != "first_world_confirm_not_invoked"
    assert response.json().get("failureResult") is None
    assert spy.initializations == int(stage == "initialize")


def test_matching_receipt_skips_nonapplication_preflight(native_first_world_client, monkeypatch):
    client, world_root, repo, _dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    spy = _install_preflight_spy(monkeypatch, world_root, preflight_error=_invalid_endpoint())
    replay = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert replay.status_code == 200, replay.text
    assert spy.preflights == 0
    assert spy.initializations == 1


def test_adapter_preflight_uses_exact_command_without_opening_storage(native_first_world_client, monkeypatch):
    client, world_root, repo, _dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    adapter = get_world_graph_initialization_authority(world_root=world_root)
    request = _sealed_native_request(repo, plan)
    monkeypatch.setattr(adapter, "_bundle", lambda: pytest.fail("preflight opened storage"))
    adapter.preflight(request)
    from apps.live_control_server.integrations.dungeonmind import world_graph_initialization_adapter as module
    seen = []
    build = module._build_command
    def capture(req, **kwargs):
        seen.append(req)
        return build(req, **kwargs)
    monkeypatch.setattr(module, "_build_command", capture)
    adapter.preflight(request)
    assert seen == [request]


def test_prepare_real_native_endpoint_qualification_identifies_original_choice(native_first_world_client):
    client, world_root, repo, _dsn = native_first_world_client
    run_id, _source = _write_glass_orchard_bld08_run(repo)
    def invalid_relationship(payload):
        edge = payload["edges"][0]
        edge["from_node_id"], edge["to_node_id"] = edge["to_node_id"], edge["from_node_id"]
        edge["relationship_type"] = "located_in"
    _mutate_extraction_candidate(repo, run_id, invalid_relationship)
    response = client.post(FIRST_WORLD_PREPARE_URL, json=_first_world_prepare_body(run_id, _first_world_decisions()))
    assert response.status_code == 409, response.text
    failure = response.json()["failureResult"]["failure"]
    assert failure["buddy_predicate"] == "located_in"
    assert failure["candidate_assertion_ids"] == ["e33"]
    assert get_world_graph_initialization_authority(world_root=world_root).probe(NATIVE_RESERVED_WORLD_ID).state == "uninitialized"


@pytest.mark.parametrize("state,world_id,initialization_id,head", [
    ("unreadable", NATIVE_RESERVED_WORLD_ID, None, None),
    ("uninitialized", "world:"+"f"*32, None, None),
    ("uninitialized", NATIVE_RESERVED_WORLD_ID, "unexpected", None),
    ("initialized", NATIVE_RESERVED_WORLD_ID, "other-initialization", "rev:other"),
])
def test_unreadable_changed_or_initialized_probe_never_releases(native_first_world_client, monkeypatch, state, world_id, initialization_id, head):
    from apps.live_control_server.ports.world_graph_initialization import WorldGraphInitializationState
    client, world_root, repo, _dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    spy = _install_preflight_spy(monkeypatch, world_root, preflight_error=_invalid_endpoint(),
        initialize_error=WorldGraphInitializationError("Already initialized", code="already_initialized"))
    monkeypatch.setattr(spy, "probe", lambda _: WorldGraphInitializationState(world_id, state, initialization_id, head))
    response = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert response.status_code >= 400, response.text
    assert response.json()["code"] != "first_world_confirm_not_invoked"
    assert response.json().get("failureResult") is None
    assert spy.preflights == 0


def test_prepare_unavailability_is_not_invalid_choice_feedback(native_first_world_client, monkeypatch):
    client, world_root, repo, _dsn = native_first_world_client
    spy = _install_preflight_spy(monkeypatch, world_root,
        preflight_error=WorldGraphInitializationError("temporarily unavailable", code="authority_unavailable"))
    run_id, _source = _write_glass_orchard_bld08_run(repo)
    response = client.post(FIRST_WORLD_PREPARE_URL, json=_first_world_prepare_body(run_id, _first_world_decisions()))
    assert response.status_code == 503, response.text
    assert response.json().get("failureResult") is None
    assert spy.initializations == 0


@pytest.mark.integration
@pytest.mark.parametrize("changed", ["commitment", "source", "span_index"])
def test_frozen_source_changes_never_reach_initializer(native_first_world_client, monkeypatch, changed):
    from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
    import json
    client, world_root, repo, dsn = native_first_world_client
    run_id, plan = _prepare_native_plan(client, repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    spy = _install_preflight_spy(monkeypatch, world_root)
    if changed == "commitment":
        plan["sourceEvidenceSha256"] = "sha256:" + "f" * 64
    elif changed == "source":
        read_bytes = Path.read_bytes
        target = resolved.normalized_recap_path
        monkeypatch.setattr(Path, "read_bytes", lambda path, *args, **kwargs: (
            b"Changed frozen source." if path == target else read_bytes(path, *args, **kwargs)
        ))
    else:
        payload = json.loads(resolved.source_span_index_path.read_text())
        payload["spans"][0]["start_line"] += 1
        resolved.source_span_index_path.write_text(json.dumps(payload))
    response = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert response.status_code in {409, 422}, response.text
    assert spy.initializations == spy.preflights == 0
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)["revisions"] == 0


@pytest.mark.integration
def test_old_plan_cannot_be_reposted_or_silently_reprepared(native_first_world_client, monkeypatch):
    client, world_root, repo, _dsn = native_first_world_client
    _run, plan = _prepare_native_plan(client, repo)
    spy = _install_preflight_spy(monkeypatch, world_root)
    plan["schema"] = "dmb_first_world_graph_plan_v2"
    response = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert spy.initializations == spy.preflights == 0


@pytest.mark.integration
def test_first_world_evidence_reaches_actual_buddy_read_pins(native_first_world_client):
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as reads
    client, _world, repo, _dsn = native_first_world_client
    _run, plan = _prepare_native_plan(client, repo)
    response = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert response.status_code == 200, response.text
    request = reads.WorldGraphObjectRequest.model_validate({
        "schema": "dmb_world_graph_object_request_v1", "worldId": NATIVE_RESERVED_WORLD_ID,
        "campaignId": "", "scopeMode": "world", "nodeId": "obj_session22_vial",
        "revisionPin": response.json()["committedRevisionId"], "admissibility": "gm",
    })
    result = reads.get_object_with_reviewed_sources_direct_v3(reads.direct_services_from_config(NATIVE_RESERVED_WORLD_ID), request)
    assert result.result.source_anchors
    assert all(anchor.readable for anchor in result.result.source_anchors)
    assert {anchor.anchor_id for anchor in result.result.source_anchors} == {pin.anchor_id for pin in result.source_pins}
    assert all(pin.graph_revision == request.revision_pin for pin in result.source_pins)


@pytest.mark.integration
def test_historical_receipt_stays_readable_without_current_command_replay(native_first_world_client):
    from dungeonmind.contracts.reviewed_world_initialization import ReviewedWorldInitializationReceiptV1
    from dungeonmind.infrastructure.postgres.serialization import model_fingerprint
    from psycopg.types.json import Jsonb
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import DungeonMindWorldGraphInitializationAdapter
    client, _world, repo, dsn = native_first_world_client
    _run, plan = _prepare_native_plan(client, repo)
    request = _sealed_native_request(repo, plan)
    response = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert response.status_code == 200, response.text
    bundle = _bundle(dsn)
    current = bundle.reviewed_world_initializations.get_for_world(NATIVE_RESERVED_WORLD_ID)
    # Seed an old-format retained receipt only inside this disposable fixture.
    historical = ReviewedWorldInitializationReceiptV1.model_validate({
        **current.model_dump(mode="json"), "schema_version": "dm_reviewed_world_initialization_receipt_v1",
    })
    before = historical.model_dump(mode="json")
    with bundle.database.transaction() as conn:
        conn.execute("UPDATE dungeonmind.reviewed_world_initializations SET schema_version=%s,payload=%s,record_fingerprint=%s WHERE world_id=%s",
                     (historical.schema_version, Jsonb(before), model_fingerprint(historical), NATIVE_RESERVED_WORLD_ID))
    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    assert adapter.probe(NATIVE_RESERVED_WORLD_ID).state == "initialized"
    counts = _counts(dsn, NATIVE_RESERVED_WORLD_ID)
    with pytest.raises(WorldGraphInitializationError) as error:
        adapter.initialize(request)
    assert error.value.code == "already_initialized"
    assert bundle.reviewed_world_initializations.get_for_world(NATIVE_RESERVED_WORLD_ID).model_dump(mode="json") == before
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID) == counts


@pytest.mark.integration
def test_first_world_same_body_in_another_world_has_independent_source_identity(
    native_first_world_client,
) -> None:
    """The global source catalog must not confuse equal bytes with one source."""
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import _build_command

    client, _world_root, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    request = _sealed_native_request(repo, plan)
    command = _build_command(request, requested_initialized_at=datetime.now(UTC))
    bundle = _bundle(dsn)
    original_artifact = command.source_artifacts[0]
    original_revision = command.source_revisions[0]
    other_artifact_id = 'artifact:other-world-same-bytes'
    other_world_id = 'world:other-same-bytes'
    # An already-persisted bare token is authoritative and must stay untouched.
    other_revision = original_revision.model_copy(update={
        'source_revision_id': request.source_revision_token,
        'source_artifact_id': other_artifact_id,
    })
    other_artifact = original_artifact.model_copy(update={
        'source_artifact_id': other_artifact_id, 'world_id': other_world_id,
        'current_revision_id': other_revision.source_revision_id,
    })
    bundle.sources.put_artifact(other_artifact)
    bundle.sources.put_revision(other_revision)
    first = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert first.status_code == 200, first.text
    published = first.json()['committedRevisionId']
    mapped = bundle.sources.list_revisions(original_artifact.source_artifact_id)
    assert [row.source_revision_id for row in mapped] == [
        f'{request.source_revision_token}::{original_artifact.source_artifact_id}'
    ]
    assert mapped[0].content_sha256 == other_revision.content_sha256
    assert bundle.sources.get_revision(other_revision.source_revision_id) == other_revision
    replay = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert replay.status_code == 200, replay.text
    assert replay.json()['committedRevisionId'] == published
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)['revisions'] == 1
    assert bundle.sources.list_revisions(original_artifact.source_artifact_id) == mapped


@pytest.mark.integration
def test_first_world_conflict_without_receipt_preserves_provider_diagnostic(
    native_first_world_client, monkeypatch,
) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import DungeonMindWorldGraphInitializationAdapter
    from dungeonmind.domain.errors import IdempotencyConflictError
    from dungeonmind.application import reviewed_world_initialization

    client, _world_root, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    request = _sealed_native_request(repo, plan)
    conflict = IdempotencyConflictError('source revision belongs to another artifact', details={'source_revision_id': 'revision:collision'})
    def refuse(*args, **kwargs):
        raise conflict
    monkeypatch.setattr(reviewed_world_initialization, 'initialize_reviewed_world', refuse)
    with pytest.raises(WorldGraphInitializationError) as caught:
        DungeonMindWorldGraphInitializationAdapter(database_url=dsn).initialize(request)
    assert str(caught.value) == str(conflict)
    assert caught.value.details == conflict.details
    assert caught.value.code == 'idempotency_conflict'
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)['revisions'] == 0


@pytest.mark.integration
def test_first_world_replay_uses_exact_persisted_unqualified_revision(native_first_world_client):
    from types import SimpleNamespace
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import DungeonMindWorldGraphInitializationAdapter, _build_command
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _build_graph_reader
    from dungeonmind.application.reviewed_world_initialization import initialize_reviewed_world

    client, _world_root, repo, dsn = native_first_world_client
    _run_id, plan = _prepare_native_plan(client, repo)
    request = _sealed_native_request(repo, plan)
    artifact_id = request.source_artifact.source_artifact_id
    catalog = SimpleNamespace(
        list_artifacts_for_world=lambda _: [SimpleNamespace(source_artifact_id=artifact_id)],
        list_revisions=lambda _: [SimpleNamespace(source_revision_id=request.source_revision_token)],
    )
    command = _build_command(request, requested_initialized_at=datetime.now(UTC), sources=catalog)
    bundle = _bundle(dsn)
    original = initialize_reviewed_world(command, initialization_repository=bundle.reviewed_world_initializations, graph_reader=_build_graph_reader())
    replay = DungeonMindWorldGraphInitializationAdapter(database_url=dsn).initialize(request)
    assert replay.published_revision_id == original.published_revision_id
    assert replay.command_sha256 == original.command_sha256
    assert [r.source_revision_id for r in bundle.sources.list_revisions(artifact_id)] == [request.source_revision_token]
    assert _counts(dsn, NATIVE_RESERVED_WORLD_ID)['revisions'] == 1
