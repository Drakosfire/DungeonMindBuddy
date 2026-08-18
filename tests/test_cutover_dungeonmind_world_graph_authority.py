"""Cutover: DungeonMind-backed World Graph authority (HANDOFF §10 evidence).

Two layers:

- **Unit layer (portable)** — no PostgreSQL, no frozen store. Proves the
  quiescence guard, the translation content-addressing round-trip, replay
  ordering, read routing in the passthrough modes, and error mapping.
- **Integration layer (env-gated)** — requires
  ``DMB_CUTOVER_TEST_DATABASE_URL`` (a migrated, disposable PostgreSQL
  database; every table is truncated by the fixture) and the frozen
  pre-switch Eldyrwild store at ``DMB_CUTOVER_FROZEN_ROOT`` (default:
  the conventional operator ``out/`` root when present). Proves the §10
  evidence rows against the real sealed bundle and the real frozen snapshot.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import graph_memory.kernel as kernel  # noqa: F401  (production import order)
from graph_memory.world_supergraph import storage
from graph_memory.world_supergraph.storage import (
    WorldGraphAuthorityQuiescedError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_existing_world_adoptions/eldyrwild/dungeonmind-v6/bundle.json"
)
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FROZEN_HEAD_REVISION = "rev:0c644e56b45bcaac709012206e3e41c2"

TEST_DSN_ENV = "DMB_CUTOVER_TEST_DATABASE_URL"
FROZEN_ROOT_ENV = "DMB_CUTOVER_FROZEN_ROOT"
DUNGEONMIND_REPO_ENV = "DUNGEONMIND_REPO"

TRUNCATE_SQL = """
TRUNCATE TABLE
    dungeonmind.semantic_documents,
    dungeonmind.active_embedding_runs,
    dungeonmind.embedding_runs,
    dungeonmind.mind_turns,
    dungeonmind.mind_threads,
    dungeonmind.retrieval_sessions,
    dungeonmind.finalized_review_publications,
    dungeonmind.contribution_reviews,
    dungeonmind.identity_decisions,
    dungeonmind.graph_contributions,
    dungeonmind.evidence_refs,
    dungeonmind.source_revisions,
    dungeonmind.source_artifacts,
    dungeonmind.existing_world_adoptions,
    dungeonmind.world_graph_head_events,
    dungeonmind.world_graph_heads,
    dungeonmind.graph_revisions,
    dungeonmind.campaigns,
    dungeonmind.worlds
RESTART IDENTITY CASCADE
"""


@pytest.fixture(autouse=True)
def _clean_authority_state(monkeypatch, tmp_path):
    """Isolate authority env + cache registry for every test."""
    for env in (
        storage.WORLD_GRAPH_AUTHORITY_ENV,
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_CACHE_ROOT",
    ):
        monkeypatch.delenv(env, raising=False)
    storage.clear_world_graph_cache_roots()
    yield
    storage.clear_world_graph_cache_roots()


# ---------------------------------------------------------------------------
# Unit layer: quiescence guard
# ---------------------------------------------------------------------------


def _minimal_store() -> object:
    from graph_memory.union_supergraph.model import UnionSupergraphStore

    return UnionSupergraphStore.model_validate(
        {
            "schema": "dmb_union_supergraph_store_v0",
            "version": "0.1",
            "campaign_id": "test-campaign",
            "focus_session_id": "test-session",
            "graph_id": None,
            "graph_domains": [],
            "source_domains": [],
            "nodes": {},
            "edges": {},
            "evidence": {},
            "source_artifacts": {},
            "aliases": {},
            "identity_redirects": [],
            "identity_merge_records": [],
            "identity_decisions": [],
            "assertion_support": {},
            "contribution_source_payload_sha256": {},
            "contribution_replay_manifest": [],
            "initialization_contribution_ids": [],
            "adjacency": {},
            "diagnostics": {},
        }
    )


def test_authority_mode_defaults_to_buddy_files(monkeypatch):
    assert (
        storage.world_graph_authority_mode()
        == storage.WORLD_GRAPH_AUTHORITY_BUDDY_FILES
    )


def test_authority_mode_unknown_value_fails_closed(monkeypatch):
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, "bogus")
    with pytest.raises(ValueError, match="unsupported"):
        storage.world_graph_authority_mode()


@pytest.mark.parametrize(
    "mode",
    [storage.WORLD_GRAPH_AUTHORITY_QUIESCED, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND],
)
def test_local_mutation_guard_rejects_non_local_modes(tmp_path, monkeypatch, mode):
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, mode)
    with pytest.raises(WorldGraphAuthorityQuiescedError) as excinfo:
        storage.publish_world_graph_revision(
            tmp_path, WORLD_ID, _minimal_store(), operation_ids=["test"]
        )
    assert excinfo.value.mode == mode
    assert excinfo.value.operation == "publish_world_graph_revision"


def test_local_mutation_guard_allows_buddy_files(tmp_path, monkeypatch):
    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_BUDDY_FILES
    )
    result = storage.publish_world_graph_revision(
        tmp_path, WORLD_ID, _minimal_store(), operation_ids=["test"]
    )
    assert result.revision.revision_id


def test_local_mutation_guard_exempts_registered_cache_root(tmp_path, monkeypatch):
    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    cache = tmp_path / "cache"
    storage.register_world_graph_cache_root(cache, world_root=tmp_path / "worlds")
    result = storage.publish_world_graph_revision(
        cache / "nested", WORLD_ID, _minimal_store(), operation_ids=["test"]
    )
    assert result.revision.revision_id
    # A sibling outside the registered root stays frozen.
    with pytest.raises(WorldGraphAuthorityQuiescedError):
        storage.publish_world_graph_revision(
            tmp_path / "elsewhere", WORLD_ID, _minimal_store(), operation_ids=["test"]
        )


def test_register_cache_root_rejects_durable_overlap(tmp_path):
    """A cache root equal to — or an ancestor of — the durable world root would
    silently exempt every authoritative file from the quiescence guard."""
    durable = tmp_path / "worlds"
    with pytest.raises(ValueError, match="overlaps durable"):
        storage.register_world_graph_cache_root(durable, world_root=durable)
    with pytest.raises(ValueError, match="overlaps durable"):
        storage.register_world_graph_cache_root(tmp_path, world_root=durable)
    # A disjoint sibling cache root remains registerable.
    storage.register_world_graph_cache_root(tmp_path / "cache", world_root=durable)


# ---------------------------------------------------------------------------
# Unit layer: translation round-trip over the sealed bundle
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bundle_payload() -> dict:
    return json.loads(BUNDLE_PATH.read_text())


def test_translate_all_bundle_contributions_recover_content_ids(bundle_payload):
    """Every translated assertion recomputes its recorded content-addressed id.

    This is the translation's load-bearing invariant: the forward map's
    visibility collapse is recovered exactly, or the kernel's load-time
    assertion-identity integrity check fails closed.
    """
    from dungeonmind.contracts.contribution import GraphContributionV2

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    contributions = [
        wga.translate_contribution(GraphContributionV2.model_validate(c))
        for c in bundle_payload["contributions"]
    ]
    assert len(contributions) == len(bundle_payload["contributions"])
    assertion_total = sum(
        len(c.candidate_assertions)
        + len(c.accepted_assertions)
        + len(c.rejected_assertions)
        for c in contributions
    )
    assert assertion_total > 1800  # Eldyrwild ledger scale guard


def test_translate_all_bundle_identity_decisions(bundle_payload):
    from dungeonmind.contracts.identity import IdentityDecisionRecordV2

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    decisions = [
        wga.translate_identity_decision(IdentityDecisionRecordV2.model_validate(d))
        for d in bundle_payload["identity_decisions"]
    ]
    assert len(decisions) == len(bundle_payload["identity_decisions"])
    assert all(d.decision_id for d in decisions)


def test_order_contributions_sealed_first_then_new(bundle_payload):
    from dungeonmind.contracts.contribution import GraphContributionV2

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    translated = [
        wga.translate_contribution(GraphContributionV2.model_validate(c))
        for c in bundle_payload["contributions"][:6]
    ]
    sealed = [c.contribution_id for c in translated[:4]]
    ordered = wga.order_contributions_for_replay(
        list(reversed(translated)), sealed_manifest_ids=sealed
    )
    assert [c.contribution_id for c in ordered[:4]] == sealed
    # New (unsealed) contributions append in produced_at order.
    new = ordered[4:]
    assert [c.contribution_id for c in new] == [
        c.contribution_id
        for c in sorted(
            translated[4:], key=lambda c: (c.produced_at, c.contribution_id)
        )
    ]


# ---------------------------------------------------------------------------
# Unit layer: read routing passthrough + error mapping
# ---------------------------------------------------------------------------


def _projection_request(**overrides):
    from graph_memory.projection.world_projection import (
        PROJECTION_REQUEST_SCHEMA,
        WorldGraphProjectionRequest,
    )

    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        **overrides,
    )


def test_route_service_read_passthrough_in_buddy_files(tmp_path):
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    request = _projection_request()
    route = wga.route_service_read(request, None, default_root=tmp_path)
    assert route.graph_root == tmp_path
    assert route.request is request
    assert route.public_revision_id is None


def test_route_service_read_passthrough_in_quiesced(tmp_path, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_QUIESCED
    )
    request = _projection_request()
    route = wga.route_service_read(request, None, default_root=tmp_path)
    assert route.graph_root == tmp_path
    assert route.request is request
    assert route.public_revision_id is None


def test_route_service_read_explicit_root_bypasses_dungeonmind(tmp_path, monkeypatch):
    """A genuinely different explicit root (tests/tooling) bypasses routing."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    explicit = tmp_path / "explicit"
    request = _projection_request()
    route = wga.route_service_read(request, explicit, default_root=tmp_path)
    assert route.graph_root == explicit.resolve()
    assert route.request is request
    assert route.public_revision_id is None


def test_route_service_read_dungeonmind_requires_database_url(tmp_path, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.route_service_read(_projection_request(), None, default_root=tmp_path)
    assert excinfo.value.code == "authority_unavailable"
    assert wga.authority_error_status_code(excinfo.value) == 503


def test_route_service_read_dungeonmind_unreachable_fails_closed(tmp_path, monkeypatch):
    """No silent fallback: an unavailable DungeonMind never serves Buddy files."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        "postgresql://dungeonmind:wrong@127.0.0.1:1/nowhere",
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.route_service_read(_projection_request(), None, default_root=tmp_path)
    assert excinfo.value.code == "authority_unavailable"


def test_projection_service_unreachable_authority_fails_closed(tmp_path, monkeypatch):
    """§10 no-silent-fallback, service level: the projection service surfaces
    the typed authority error instead of reading the Buddy file store."""
    from apps.live_control_server.services.world_graph_projection import (
        WorldGraphProjectionServiceError,
        project_world_graph,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        "postgresql://dungeonmind:wrong@127.0.0.1:1/nowhere",
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path))
    with pytest.raises(WorldGraphProjectionServiceError) as excinfo:
        project_world_graph(_projection_request())
    assert excinfo.value.code == "authority_unavailable"
    assert excinfo.value.status_code == 503


def test_derive_confirm_operation_id_is_deterministic_and_selection_bound():
    """Stable retry identity: same package + selection ⇒ same operation id; a
    different selection or package is a genuinely different operation. The id
    is parent-independent because the sealed package pins the parent."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    package = {"proposal_id": "proposal:1", "proposal_digest": "a" * 64}
    base = wga._derive_confirm_operation_id(
        world_id=WORLD_ID, package=package, assertion_ids=("assertion:1",)
    )
    again = wga._derive_confirm_operation_id(
        world_id=WORLD_ID, package=package, assertion_ids=("assertion:1",)
    )
    assert base == again
    assert base.startswith("reviewop:")
    assert base != wga._derive_confirm_operation_id(
        world_id=WORLD_ID, package=package, assertion_ids=("assertion:2",)
    )
    assert base != wga._derive_confirm_operation_id(
        world_id=WORLD_ID, package=package, assertion_ids=None
    )
    assert base != wga._derive_confirm_operation_id(
        world_id=WORLD_ID,
        package={"proposal_id": "proposal:2", "proposal_digest": "b" * 64},
        assertion_ids=("assertion:1",),
    )


# ---------------------------------------------------------------------------
# Integration layer (env-gated)
# ---------------------------------------------------------------------------


def _test_dsn() -> str:
    dsn = os.environ.get(TEST_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(f"{TEST_DSN_ENV} unset")
    db_name = dsn.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name:
        pytest.skip(
            f"{TEST_DSN_ENV} database name {db_name!r} must contain 'test' "
            "(the fixture truncates every dungeonmind table)"
        )
    return dsn


def _frozen_root() -> Path:
    override = os.environ.get(FROZEN_ROOT_ENV, "").strip()
    candidates = (
        [Path(override)]
        if override
        else [Path.home() / "Projects/DungeonOverMind/DungeonMindBuddy/out"]
    )
    for candidate in candidates:
        head = candidate / "graph_memory/worlds" / WORLD_ID / "head.json"
        if head.is_file():
            try:
                payload = json.loads(head.read_text())
            except ValueError:
                continue
            if payload.get("head_revision_id") == FROZEN_HEAD_REVISION:
                return candidate
    pytest.skip(
        f"frozen pre-switch store (head {FROZEN_HEAD_REVISION}) not found; "
        f"set {FROZEN_ROOT_ENV}"
    )


def _ensure_migrated(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'dungeonmind' AND table_name = 'worlds'"
        ).fetchone()
    if row is not None:
        return
    repo = os.environ.get(DUNGEONMIND_REPO_ENV, "").strip()
    if not repo:
        pytest.skip(
            f"test database is not migrated and {DUNGEONMIND_REPO_ENV} is unset "
            "(point it at a DungeonMind checkout to auto-migrate)"
        )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=repo,
        env={**os.environ, "DUNGEONMIND_DATABASE_URL": dsn},
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}")


@pytest.fixture(scope="module")
def adopted_world():
    """A migrated test DB with the sealed Eldyrwild bundle adopted at V3."""
    from datetime import UTC, datetime

    from dungeonmind.application.existing_world_adoption import (
        adopt_existing_world,
        promote_existing_world_adoption_receipt_v3,
    )
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresRepositoryBundle,
    )

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = _test_dsn()
    _ensure_migrated(dsn)
    database = PostgresDatabase(dsn)
    with database.connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()
    bundle = PostgresRepositoryBundle(database)
    raw = BUNDLE_PATH.read_bytes()
    receipt = adopt_existing_world(
        raw,
        adopted_at=datetime.now(UTC),
        adoption_repository=bundle.existing_world_adoptions,
        graph_reader=wga.build_authority_graph_reader(),
    )
    if receipt.schema_version != "dm_existing_world_adoption_receipt_v3":
        receipt = promote_existing_world_adoption_receipt_v3(
            raw,
            world_id=WORLD_ID,
            adoption_repository=bundle.existing_world_adoptions,
        )
    return {
        "dsn": dsn,
        "bundle": bundle,
        "receipt": receipt,
        "raw_bundle": raw,
        "frozen_root": _frozen_root(),
    }


@pytest.mark.integration
def test_v3_precondition_membership_digest(adopted_world):
    """§10: target test DB adopts/promotes A and verifies exact membership."""
    receipt = adopted_world["receipt"]
    assert receipt.schema_version == "dm_existing_world_adoption_receipt_v3"
    assert receipt.world_id == WORLD_ID
    assert receipt.membership_sha256
    assert receipt.source_provenance.source_world_revision_id == FROZEN_HEAD_REVISION


@pytest.mark.integration
def test_correspondence_reports_corresponding(adopted_world):
    """§10: exact A reports CORRESPONDING through the merged evaluator."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    result = wga.check_world_correspondence(
        adopted_world["bundle"], WORLD_ID, bundle_bytes=adopted_world["raw_bundle"]
    )
    assert result.classification == "CORRESPONDING"


@pytest.mark.integration
def test_identity_bridge_exact_and_fail_closed(adopted_world, tmp_path):
    """§10: only the exact adopted receipt maps legacy Buddy A to D_A."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    binding = wga.bind_world_authority(
        adopted_world["bundle"], WORLD_ID, frozen_root=adopted_world["frozen_root"]
    )
    assert binding.legacy_buddy_revision_id == FROZEN_HEAD_REVISION
    assert binding.dungeonmind_first_revision_id == (
        adopted_world["receipt"].published_revision_id
    )

    # A frozen store whose head is not the adopted snapshot fails closed.
    wrong_root = tmp_path / "wrong"
    wrong_world = wrong_root / "graph_memory/worlds" / WORLD_ID
    wrong_world.mkdir(parents=True)
    (wrong_world / "head.json").write_text(
        json.dumps({"head_revision_id": "rev:" + "0" * 32})
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.bind_world_authority(
            adopted_world["bundle"], WORLD_ID, frozen_root=wrong_root
        )
    assert excinfo.value.code == "frozen_store_mismatch"


@pytest.fixture()
def hydrated(adopted_world, tmp_path, monkeypatch):
    """A hydrated cache root for the adopted world, with the process fully
    configured for ``dungeonmind`` authority mode (per-test isolation)."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", adopted_world["dsn"]
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_ROOT", str(adopted_world["frozen_root"])
    )
    cache_root = tmp_path / "authority-cache"
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_CACHE_ROOT", str(cache_root))
    handle = wga.ensure_hydrated_authority(
        WORLD_ID,
        database_url=adopted_world["dsn"],
        cache_root=cache_root,
        frozen_root=adopted_world["frozen_root"],
    )
    return {
        "handle": handle,
        "cache_root": cache_root,
        "frozen_root": adopted_world["frozen_root"],
        "dsn": adopted_world["dsn"],
    }


@pytest.mark.integration
def test_hydration_fingerprint_exact_against_frozen_snapshot(hydrated):
    """The hydrated store is fingerprint-equal to the frozen pre-switch head."""
    from graph_memory.kernel.contribution_rebuild import _canonical_graph_fingerprint
    from graph_memory.world_supergraph.storage import load_world_graph_revision

    handle = hydrated["handle"]
    hydrated_store = load_world_graph_revision(
        handle.cache_world_root, WORLD_ID, handle.buddy_revision_id
    )
    frozen_store = load_world_graph_revision(
        hydrated["frozen_root"], WORLD_ID, FROZEN_HEAD_REVISION
    )
    assert _canonical_graph_fingerprint(hydrated_store) == _canonical_graph_fingerprint(
        frozen_store
    )


@pytest.mark.integration
def test_projection_read_served_from_dungeonmind(hydrated, monkeypatch):
    """§10: the normal projection service returns Eldyrwild data backed by DungeonMind.

    Called rootless: the service itself routes through the configured
    authority, proving the routing seam rather than just the cache content.
    The frozen comparison read runs in ``quiesced`` mode: in ``dungeonmind``
    mode the configured root is not an override, so an explicit frozen-root
    read would route back to DungeonMind.
    """
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph,
    )

    projected = project_world_graph(_projection_request())
    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_QUIESCED
    )
    frozen_projection = project_world_graph(
        _projection_request(), root=hydrated["frozen_root"]
    )
    assert (
        projected.model_dump(mode="json")["relationships"]
        == (frozen_projection.model_dump(mode="json")["relationships"])
    )
    assert (
        projected.model_dump(mode="json")["attributes"]
        == (frozen_projection.model_dump(mode="json")["attributes"])
    )
    # Node sets are identical; per-node adjacency list order follows Buddy's
    # own rebuild semantics (the frozen head's adjacency is a stale accretion
    # artifact — Buddy's rebuild of the frozen ledger produces the hydrated
    # order), and the canonical fingerprint excludes adjacency.
    assert {n.node_id for n in projected.nodes} == {
        n.node_id for n in frozen_projection.nodes
    }
    # Public identity is the exact DungeonMind head revision, not the private
    # hydrated-cache Buddy revision.
    assert projected.snapshot.revision_id == hydrated["handle"].selected_revision_id
    assert projected.snapshot.revision_id != hydrated["handle"].buddy_revision_id
    assert projected.snapshot.head_revision_id == hydrated["handle"].head_revision_id
    assert projected.snapshot.is_head is True


@pytest.mark.integration
def test_retrieval_read_served_from_dungeonmind(hydrated, monkeypatch):
    """§10: the normal object/evidence/neighborhood path returns exact data.

    Called rootless: the service routes through the configured authority. The
    frozen comparison read runs in ``quiesced`` mode (the configured root is
    not an authority override in ``dungeonmind`` mode).
    """
    from graph_memory.retrieval.models import (
        RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
        RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        WorldGraphNeighborhoodRequest,
        WorldGraphObjectRequest,
    )

    from apps.live_control_server.services import world_graph_retrieval as retrieval

    frozen = hydrated["frozen_root"]
    node_id = "location:mireward"

    object_request = WorldGraphObjectRequest.model_validate(
        {
            "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "nodeId": node_id,
        }
    )
    neighborhood_request = WorldGraphNeighborhoodRequest.model_validate(
        {
            "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "seedNodeIds": [node_id],
        }
    )
    routed_object = retrieval.get_campaign_object(object_request)
    routed_neighborhood = retrieval.get_object_neighborhood(neighborhood_request)

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_QUIESCED
    )
    frozen_object = retrieval.get_campaign_object(object_request, root=frozen)
    frozen_neighborhood = retrieval.get_object_neighborhood(
        neighborhood_request, root=frozen
    )

    assert routed_object.outcome == frozen_object.outcome
    assert (
        routed_object.model_dump(mode="json")["nodes"]
        == (frozen_object.model_dump(mode="json")["nodes"])
    )
    assert (
        routed_object.model_dump(mode="json")["attributes"]
        == (frozen_object.model_dump(mode="json")["attributes"])
    )
    assert routed_object.snapshot is not None
    assert routed_object.snapshot.revision_id == (
        hydrated["handle"].selected_revision_id
    )
    assert (
        routed_neighborhood.model_dump(mode="json")["nodes"]
        == (frozen_neighborhood.model_dump(mode="json")["nodes"])
    )
    assert (
        routed_neighborhood.model_dump(mode="json")["relationships"]
        == (frozen_neighborhood.model_dump(mode="json")["relationships"])
    )


@pytest.mark.integration
def test_legacy_a_reference_resolves_through_bridge(hydrated):
    """§10: a real exact-A reference remains openable after the switch, and its
    public identity is the receipt-bound adoption revision D_A."""
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph,
    )

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    binding = wga.bind_world_authority(
        wga._open_repository_bundle(hydrated["dsn"]),
        WORLD_ID,
        frozen_root=hydrated["frozen_root"],
    )

    # Service-level: a pinned exact-A projection resolves through the bridge.
    projected = project_world_graph(
        _projection_request(revision_pin=FROZEN_HEAD_REVISION)
    )
    assert projected.snapshot.revision_id == binding.dungeonmind_first_revision_id
    assert projected.snapshot.head_revision_id == binding.dungeonmind_head_revision_id
    assert projected.snapshot.is_head is (
        binding.dungeonmind_first_revision_id == binding.dungeonmind_head_revision_id
    )

    # An unbridged historical revision fails closed rather than reading files.
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.route_read_request(
            _projection_request(revision_pin="rev:" + "1" * 32),
            world_id=WORLD_ID,
            database_url=hydrated["dsn"],
            cache_root=hydrated["cache_root"],
            frozen_root=hydrated["frozen_root"],
        )
    assert excinfo.value.code == "revision_not_bridged"


@pytest.mark.integration
def test_mounted_caller_explicit_configured_root_routes_to_dungeonmind(hydrated):
    """§3: a mounted caller passing the configured production root explicitly
    is routed to DungeonMind exactly like a rootless call — the configured
    root is not an authority override in ``dungeonmind`` mode."""
    from apps.live_control_server.config import world_graph_root
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph,
    )

    assert world_graph_root() == hydrated["frozen_root"]
    projected = project_world_graph(_projection_request(), root=world_graph_root())
    assert projected.snapshot.revision_id == hydrated["handle"].selected_revision_id
    assert projected.snapshot.revision_id != hydrated["handle"].buddy_revision_id


@pytest.mark.integration
def test_mounted_hermes_tool_and_threat_query_route_to_dungeonmind(hydrated):
    """§7: the mounted Hermes tool seam (expansion executor → retrieval
    service) and the Threat hydration query both receive the configured
    production root explicitly from their callers. In ``dungeonmind`` mode
    the shared router serves DungeonMind state with public DungeonMind
    revision identity — the frozen store is never selected."""
    from apps.live_control_server.config import world_graph_root
    from apps.live_control_server.models.threat_query_hydration import (
        ThreatQueryHydrationRequestV1,
    )
    from apps.live_control_server.services.threat_query_hydration import (
        query_threats_with_hydration,
    )
    from graph_memory.interaction.expansion_executor import (
        execute_expand_graph_retrieval,
    )
    from graph_memory.interaction.initial_resolve import (
        create_session_from_preflight,
    )

    configured_root = world_graph_root()
    assert configured_root == hydrated["frozen_root"]
    d_a = hydrated["handle"].selected_revision_id

    # Hermes tool seam: the host dispatches expand_graph_retrieval with the
    # explicit configured root taken from the turn request.
    session = create_session_from_preflight(
        {
            "world_id": WORLD_ID,
            "campaign_id": CAMPAIGN_ID,
            "revision_id": d_a,
            "matched_node_ids": [],
            "nodes": [],
            "attributes": [],
            "focus": {"kind": "none"},
            "admissibility": "gm",
        },
        question="Tripod",
    )
    hermes_result = execute_expand_graph_retrieval(
        {
            "operation": "search",
            "query_text": "Tripod",
            "retrieval_session_id": session.id,
        },
        root=configured_root,
    )
    assert hermes_result.get("schema") != "dmb_world_graph_retrieval_error_v1", (
        hermes_result
    )
    assert hermes_result["snapshot"]["revisionId"] == d_a
    assert "threat:tripod-null-calf" in hermes_result["matchedNodeIds"]

    # Threat path: the mounted route passes world_graph_root() explicitly.
    threat_response = query_threats_with_hydration(
        ThreatQueryHydrationRequestV1(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            revision_pin=d_a,
            query_text="Tripod",
            include_mechanics=False,
        ),
        root=configured_root,
    )
    assert threat_response.revision_id == d_a
    assert any(
        hit.threat.node_id == "threat:tripod-null-calf" for hit in threat_response.hits
    )


@pytest.mark.integration
def test_restart_rereads_same_dungeonmind_revision(hydrated, monkeypatch):
    """§10: a fresh process reads the DungeonMind revision, not local state."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    # Simulate a fresh process: drop the cache-root registry and re-resolve
    # against the same on-disk cache (a hit, not a rebuild).
    storage.clear_world_graph_cache_roots()
    handle = wga.ensure_hydrated_authority(
        WORLD_ID,
        database_url=hydrated["dsn"],
        cache_root=hydrated["cache_root"],
        frozen_root=hydrated["frozen_root"],
    )
    assert handle.buddy_revision_id == hydrated["handle"].buddy_revision_id
    assert handle.selected_revision_id == hydrated["handle"].selected_revision_id
    assert handle.head_revision_id == hydrated["handle"].head_revision_id


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def adopted_world_contributions(dsn: str) -> list[str]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT contribution_id FROM dungeonmind.graph_contributions ORDER BY 1"
        ).fetchall()
    return [row[0] for row in rows]


def _graph_revision_ids(dsn: str) -> list[str]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT revision_id FROM dungeonmind.graph_revisions ORDER BY 1"
        ).fetchall()
    return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# Integration layer: mutation proofs (function-scoped fresh adoption)
#
# These tests mutate the shared test database (publications advance the head;
# the tamper test corrupts a row). Each uses its own fresh adoption fixture,
# and all are defined after the read-only integration tests so the
# module-scoped ``adopted_world`` state stays at D_A for them.
# ---------------------------------------------------------------------------


@pytest.fixture()
def write_world(tmp_path, monkeypatch):
    """A fresh V3 adoption plus full ``dungeonmind`` authority env config."""
    from datetime import UTC, datetime

    from dungeonmind.application.existing_world_adoption import (
        adopt_existing_world,
        promote_existing_world_adoption_receipt_v3,
    )
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresRepositoryBundle,
    )

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = _test_dsn()
    _ensure_migrated(dsn)
    database = PostgresDatabase(dsn)
    with database.connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()
    bundle = PostgresRepositoryBundle(database)
    raw = BUNDLE_PATH.read_bytes()
    receipt = adopt_existing_world(
        raw,
        adopted_at=datetime.now(UTC),
        adoption_repository=bundle.existing_world_adoptions,
        graph_reader=wga.build_authority_graph_reader(),
    )
    if receipt.schema_version != "dm_existing_world_adoption_receipt_v3":
        receipt = promote_existing_world_adoption_receipt_v3(
            raw,
            world_id=WORLD_ID,
            adoption_repository=bundle.existing_world_adoptions,
        )
    frozen_root = _frozen_root()
    cache_root = tmp_path / "authority-cache"
    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(frozen_root))
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_CACHE_ROOT", str(cache_root))
    # The product confirm service re-checks the sealed sourceUri against
    # server-owned source roots; allow the test's tmp source directory.
    monkeypatch.setenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", str(tmp_path))
    return {
        "dsn": dsn,
        "bundle": bundle,
        "receipt": receipt,
        "frozen_root": frozen_root,
        "cache_root": cache_root,
        "tmp_path": tmp_path,
    }


def _seal_tinker_package(
    cache_world_root: Path,
    tmp_path: Path,
    *,
    preview_slug: str,
    node_id: str,
    label: str,
) -> dict:
    """Build a real sealed Buddy review package against a hydrated cache."""
    from graph_memory.candidate_graph_preview import (
        CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        CANDIDATE_GRAPH_PREVIEW_VERSION,
        candidate_graph_preview_from_dict,
    )
    from graph_memory.extract_identity_gate import gate_candidate_graph_against_head
    from graph_memory.extract_promote_proposal import (
        build_contribution_effect_slice,
        contribution_meta_from_contribution,
        seal_multi_contribution_promote_proposal,
    )

    from graph_memory.world_supergraph.storage import open_world_graph_head

    parent = open_world_graph_head(cache_world_root, WORLD_ID).head_revision_id
    source = tmp_path / f"{preview_slug}-recap.md"
    source.write_text(f"{label} arrives in Mireward.\n")
    source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    artifact_id = f"artifact:recap:longmont-c2:{preview_slug}"
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": f"preview:{preview_slug}",
        "session_id": "session-26",
        "campaign_id": CAMPAIGN_ID,
        "source_artifact_ids": [artifact_id],
        "status": "preview",
        "nodes": [
            {
                "node_id": node_id,
                "label": label,
                "node_type": "npc",
                "description": f"{label}.",
                "importance": "low",
                "semantic_state": {
                    "canon_state": "played_canon",
                    "lifecycle_state": "candidate",
                    "evidence_role": "source_evidence",
                    "authority_state": "system_derived",
                    "visibility_state": "gm_private",
                },
                "evidence_refs": [
                    {
                        "source_ref_id": f"ref:{preview_slug}",
                        "source_artifact_id": artifact_id,
                        "source_anchor_id": f"anchor:{preview_slug}",
                        "label": "span",
                        "evidence_role": "source_evidence",
                        "can_open_source": True,
                        "can_highlight_span": True,
                        "source_span_ref_id": "session-26:recap:paragraph:001",
                        "anchor_quotes": [label],
                    }
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        root=cache_world_root,
        world_id=WORLD_ID,
        source_artifact_id=artifact_id,
        source_revision_id=source_revision,
        source_uri=str(source),
        source_kind="source_extraction",
        source_domain="recap",
        campaign_scope=CAMPAIGN_ID,
    )
    assert gate.parent_revision_id == parent
    slice_body = build_contribution_effect_slice(
        source_revision_id=gate.source_revision_id,
        source_artifact_id=gate.source_artifact_id,
        verified_source_uri=str(gate.verified_source_uri),
        candidate_preview_id=gate.candidate_preview_id,
        candidate_schema=gate.candidate_schema,
        candidate_version=gate.candidate_version,
        contribution_meta=contribution_meta_from_contribution(gate.contribution),
        accepted_proposals=gate.accepted_proposals,
        rejected_assertions=gate.rejected_assertions,
        unresolved_mentions=gate.unresolved_mentions,
        node_id_map=gate.node_id_map,
        identity_outcome_snapshot=gate.identity_outcome_snapshot,
    )
    package = seal_multi_contribution_promote_proposal(
        world_id=WORLD_ID,
        parent_revision_id=parent,
        contribution_slices=[slice_body],
        prepared_by="gm@prepare",
        diagnostics=["cutover_write_test"],
        world_root=str(cache_world_root),
    )
    return package, [a.assertion_id for a in gate.accepted_proposals]


@pytest.mark.integration
def test_governed_write_publishes_d_a_to_d_b_through_real_confirm_path(
    write_world,
):
    """§3: a real Buddy confirmation routes through DungeonMind's v2 finalize +
    v6 materialization + head CAS publication; the head advances D_A → D_B;
    an exact retry returns the same durable publication; the frozen Buddy
    store never mutates."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)
    revisions_before = _graph_revision_ids(dsn)

    handle = wga.ensure_hydrated_authority(
        WORLD_ID,
        database_url=dsn,
        cache_root=cache_root,
        frozen_root=frozen_root,
    )
    assert handle.selected_revision_id == d_a
    package, _accepted_ids = _seal_tinker_package(
        handle.cache_world_root,
        write_world["tmp_path"],
        preview_slug="session-26-cutover-write",
        node_id="node:cutover-tinker",
        label="Cutover Tinker",
    )

    class _Request:
        review_package = package
        assertion_ids = None

    payload = wga.confirm_via_dungeonmind(
        _Request(),
        world_root=frozen_root,
        database_url=dsn,
        cache_root=cache_root,
        frozen_root=frozen_root,
        confirming_principal="gm@confirm",
        assertion_ids=None,
        repo_root=write_world["tmp_path"],
    )
    assert payload["outcome"] == "published"
    assert payload["parent_revision_id"] == d_a
    d_b = payload["committed_revision_id"]
    assert d_b != d_a

    head = bundle.world_graph.get_head(WORLD_ID)
    assert head is not None and head.head_revision_id == d_b
    stored = bundle.world_graph.get_revision(WORLD_ID, d_b)
    assert stored is not None
    assert stored.revision.parent_revision_id == d_a
    assert any(
        obj.get("object_id") == "node:cutover-tinker"
        for obj in stored.graph_payload.get("objects") or []
    )

    # Exact retry: same package + same selection + same parent ⇒ the durable
    # publication is returned; no second child revision is created.
    retry = wga.confirm_via_dungeonmind(
        _Request(),
        world_root=frozen_root,
        database_url=dsn,
        cache_root=cache_root,
        frozen_root=frozen_root,
        confirming_principal="gm@confirm",
        assertion_ids=None,
        repo_root=write_world["tmp_path"],
    )
    assert retry["outcome"] == "already_applied"
    assert retry["committed_revision_id"] == d_b
    assert bundle.world_graph.get_head(WORLD_ID).head_revision_id == d_b  # type: ignore[union-attr]
    assert set(_graph_revision_ids(dsn)) == set(revisions_before) | {d_b}

    # The hydrated read model for D_B contains the confirmed node.
    storage.clear_world_graph_cache_roots()
    handle_b = wga.ensure_hydrated_authority(
        WORLD_ID,
        database_url=dsn,
        cache_root=cache_root,
        frozen_root=frozen_root,
    )
    assert handle_b.selected_revision_id == d_b
    from graph_memory.world_supergraph.storage import load_world_graph_revision

    store_b = load_world_graph_revision(
        handle_b.cache_world_root, WORLD_ID, handle_b.buddy_revision_id
    )
    assert "node:cutover-tinker" in store_b.nodes

    assert _tree_digest(frozen_root) == frozen_digest_before


@pytest.mark.integration
def test_governed_write_through_service_confirm_path(write_world):
    """§3: the actual product confirm service publishes through DungeonMind
    and returns the existing Buddy receipt shape with DungeonMind identity."""
    from apps.live_control_server.models.extract_promote import (
        ExtractPromoteConfirmRequest,
    )
    from apps.live_control_server.services.extract_promote import (
        confirm as confirm_extract_promote,
    )

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)

    handle = wga.ensure_hydrated_authority(
        WORLD_ID,
        database_url=dsn,
        cache_root=cache_root,
        frozen_root=frozen_root,
    )
    package, accepted_ids = _seal_tinker_package(
        handle.cache_world_root,
        write_world["tmp_path"],
        preview_slug="session-26-cutover-service",
        node_id="node:cutover-service-tinker",
        label="Service Tinker",
    )
    receipt = confirm_extract_promote(
        ExtractPromoteConfirmRequest(
            review_package=package,
            assertion_ids=accepted_ids,
        )
    )
    assert receipt.outcome == "committed"
    assert receipt.parent_revision_id == d_a
    assert receipt.applied_assertion_count == len(accepted_ids)
    assert receipt.affected_object_ids == ["node:cutover-service-tinker"]
    committed = receipt.committed_revision_id
    assert committed != d_a
    bundle = write_world["bundle"]
    head = bundle.world_graph.get_head(WORLD_ID)
    assert head is not None and head.head_revision_id == committed
    assert _tree_digest(frozen_root) == frozen_digest_before


def _finalize_minimal_v2_review(
    bundle,
    *,
    parent_stored,
    operation_id: str,
    object_id: str,
    label: str,
):
    """Finalize a minimal one-node v2 review directly through DungeonMind's
    public API (the CAS-loser setup: two durable finalized reviews, one
    parent, only one can publish)."""
    from dungeonmind.application.contribution_review_v2 import (
        finalize_contribution_review_v2,
    )
    from dungeonmind.contracts.contribution import (
        AcceptanceState,
        ContributionSourceKind,
        GraphContributionAssertionV2,
        GraphContributionV2,
    )
    from dungeonmind.contracts.contribution_review import (
        ContributionAssertionVerdict,
        ContributionIdentityProposal,
        ContributionIdentityVerdict,
        ContributionIdentityVerdictKind,
        ContributionPlanRef,
        derive_confirmation_id,
    )
    from dungeonmind.contracts.contribution_review_v2 import (
        FINALIZE_REVIEW_V2_TOOL,
        CommitConfirmationReceiptV2,
        ContributionReviewIntentV2,
        ContributionReviewSubmissionV2,
        contribution_v2_payload_sha256,
        derive_review_intent_sha256_v2,
    )
    from dungeonmind.contracts.evidence import (
        EvidenceRef,
        EvidenceRole,
        SourceDomain,
    )
    from dungeonmind.contracts.identity import IdentityOutcome
    from dungeonmind.contracts.semantic_profile import SemanticProfileRef
    from graph_memory.kernel.contributions import compute_assertion_id

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    parent_envelope = parent_stored.revision
    reviewed_at = parent_envelope.created_at
    # Anchor the synthetic review to a session_recap adopted artifact so the
    # embedded Buddy evidence domain ("recap") matches the hydrated artifact.
    recap_artifact_ids = {
        a.source_artifact_id
        for a in bundle.sources.list_artifacts_for_world(WORLD_ID)
        if a.source_domain == SourceDomain.SESSION_RECAP
    }
    adopted = next(
        c
        for c in bundle.contributions.list_for_world(WORLD_ID)
        if c.source_artifact_id in recap_artifact_ids
    )
    # The assertion id must be a real Buddy content address: hydration's
    # inverse translation recomputes it from the (dm_kind-stripped) value.
    # The value carries the Buddy-shaped embedded evidence list because the
    # Buddy replay registers evidence records from it.
    session_id = adopted.source_artifact_id.rsplit(":", 1)[-1]
    buddy_value = {
        "kind": "npc",
        "aliases": [label],
        "evidence": [
            {
                "evidence_ref_id": f"evidence:{object_id}",
                "source_artifact_id": adopted.source_artifact_id,
                "source_domain": "recap",
                "locator": "paragraph:001",
                "session_id": session_id,
                "source_span_ref_id": f"{session_id}:recap:paragraph:001",
            }
        ],
    }
    assertion_id = compute_assertion_id(
        assertion_kind="node",
        subject_node_id=object_id,
        target_node_id=None,
        predicate=None,
        label=label,
        value=buddy_value,
        campaign_scope=CAMPAIGN_ID,
        temporal_scope=None,
        epistemic_kind="asserted",
        visibility=None,
    )
    candidate = GraphContributionV2(
        contribution_id=f"contrib:{operation_id.removeprefix('reviewop:')}",
        world_id=WORLD_ID,
        source_kind=ContributionSourceKind.GRAPH_REVIEW,
        produced_at=reviewed_at,
        authored_by="buddy:cutover-cas-test",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=adopted.source_artifact_id,
        source_revision_id=adopted.source_revision_id,
        assertions=[
            GraphContributionAssertionV2(
                assertion_id=assertion_id,
                assertion_kind="node",
                subject_object_id=object_id,
                label=label,
                value=json.dumps({"dm_kind": "dnd5e:npc", **buddy_value}),
                evidence_refs=[
                    EvidenceRef(
                        evidence_ref_id=f"evidence:{object_id}",
                        source_artifact_id=adopted.source_artifact_id,
                        source_revision_id=adopted.source_revision_id,
                        source_domain=SourceDomain.SESSION_RECAP,
                        evidence_role=EvidenceRole.SUPPORT,
                        can_open_source=True,
                        can_highlight_span=False,
                        locator="paragraph:001",
                    )
                ],
                epistemic_kind="asserted",
                campaign_scope=CAMPAIGN_ID,
            )
        ],
    )
    plan_ref = ContributionPlanRef(
        source_plan_schema="dmb_promote_extract_review_package_v1",
        source_plan_id=f"plan:{operation_id}",
        source_plan_sha256="1" * 64,
        source_input_sha256="2" * 64,
        preview_content_sha256="3" * 64,
        candidate_contribution_sha256=contribution_v2_payload_sha256(candidate),
        expected_parent_revision_id=parent_envelope.revision_id,
        base_graph_schema=parent_envelope.graph_schema,
        base_graph_payload_sha256=parent_envelope.graph_payload_sha256,
        semantic_profile=SemanticProfileRef.model_validate(
            parent_stored.graph_payload["semantic_profile"]
        ),
    )
    proposals = [
        ContributionIdentityProposal(
            candidate_id=f"identity:{object_id}",
            candidate_kind="object",
            planned_outcome=IdentityOutcome.PROVISIONAL_NEW,
            target_object_id=object_id,
        )
    ]
    verdicts = [
        ContributionIdentityVerdict(
            candidate_id=f"identity:{object_id}",
            verdict=ContributionIdentityVerdictKind.CREATE_NEW,
            target_object_id=object_id,
        )
    ]
    assertion_verdicts = [
        ContributionAssertionVerdict(
            assertion_id=assertion.assertion_id,
            acceptance_state=AcceptanceState.ACCEPTED,
        )
        for assertion in candidate.assertions
    ]
    intent_sha256 = derive_review_intent_sha256_v2(
        operation_id=operation_id,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        plan_ref=plan_ref,
        candidate_contribution=candidate,
        identity_proposals=proposals,
        identity_verdicts=verdicts,
        assertion_verdicts=assertion_verdicts,
        reviewer_id="gm:cas-test",
        reviewed_at=reviewed_at,
    )
    intent = ContributionReviewIntentV2(
        operation_id=operation_id,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        plan_ref=plan_ref,
        candidate_contribution=candidate,
        identity_proposals=proposals,
        identity_verdicts=verdicts,
        assertion_verdicts=assertion_verdicts,
        reviewer_id="gm:cas-test",
        reviewed_at=reviewed_at,
        review_intent_sha256=intent_sha256,
    )
    submission = ContributionReviewSubmissionV2(
        intent=intent,
        confirmation=CommitConfirmationReceiptV2(
            confirmation_id=derive_confirmation_id(
                operation_id=operation_id,
                review_intent_sha256=intent_sha256,
                actor="gm:cas-test",
                confirmed_at=reviewed_at,
            ),
            operation_id=operation_id,
            review_intent_sha256=intent_sha256,
            actor="gm:cas-test",
            tool_name=FINALIZE_REVIEW_V2_TOOL,
            effect="commit",
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            expected_parent_revision_id=parent_envelope.revision_id,
            confirmed_at=reviewed_at,
        ),
    )
    return finalize_contribution_review_v2(
        submission,
        capability_policy=wga._confirm_capability_policy(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            parent_revision_id=parent_envelope.revision_id,
        ),
        world_graph_repository=bundle.world_graph,
        review_repository=bundle.contribution_reviews,
    )


@pytest.mark.integration
def test_hydration_replays_only_published_ancestry(write_world):
    """§3: two finalized reviews race; one wins the head CAS. Hydration of the
    winning head replays the winner and never the durable-but-unpublished
    loser; D_B re-pins by its own id; a cold legacy-A reference still serves
    D_A; the derivative cache can be deleted and rebuilt from durable state."""
    import shutil

    from dungeonmind.application.review_publication import publish_finalized_review
    from dungeonmind.domain.errors import StaleParentRevisionError

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)

    parent = bundle.world_graph.get_revision(WORLD_ID, d_a)
    assert parent is not None
    winner_state = _finalize_minimal_v2_review(
        bundle,
        parent_stored=parent,
        operation_id="reviewop:" + "a" * 32,
        object_id="node:cas-winner",
        label="CAS Winner",
    )
    loser_state = _finalize_minimal_v2_review(
        bundle,
        parent_stored=parent,
        operation_id="reviewop:" + "b" * 32,
        object_id="node:cas-loser",
        label="CAS Loser",
    )

    publication = publish_finalized_review(
        WORLD_ID,
        winner_state.record.review_id,
        published_at=parent.revision.created_at,
        review_repository=bundle.contribution_reviews,
        world_graph_repository=bundle.world_graph,
        publication_repository=bundle.finalized_review_publications,
        graph_reader=wga.build_authority_graph_reader(),
    )
    d_b = publication.published_revision_id
    with pytest.raises(StaleParentRevisionError):
        publish_finalized_review(
            WORLD_ID,
            loser_state.record.review_id,
            published_at=parent.revision.created_at,
            review_repository=bundle.contribution_reviews,
            world_graph_repository=bundle.world_graph,
            publication_repository=bundle.finalized_review_publications,
            graph_reader=wga.build_authority_graph_reader(),
        )
    # The loser stays durable but unpublished.
    assert bundle.contribution_reviews.get(WORLD_ID, loser_state.record.review_id)
    assert (
        bundle.finalized_review_publications.get_for_review(
            WORLD_ID, loser_state.record.review_id
        )
        is None
    )

    # Hydrate the winning head: winner present, loser absent.
    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    assert handle.selected_revision_id == d_b
    from graph_memory.world_supergraph.storage import load_world_graph_revision

    store = load_world_graph_revision(
        handle.cache_world_root, WORLD_ID, handle.buddy_revision_id
    )
    assert "node:cas-winner" in store.nodes
    assert "node:cas-loser" not in store.nodes

    # Derivative-cache deletion: rebuild from DungeonMind durable state alone.
    shutil.rmtree(cache_root)
    storage.clear_world_graph_cache_roots()
    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    assert handle.selected_revision_id == d_b
    store = load_world_graph_revision(
        handle.cache_world_root, WORLD_ID, handle.buddy_revision_id
    )
    assert "node:cas-winner" in store.nodes
    assert "node:cas-loser" not in store.nodes

    # D_B self-repin: a returned DungeonMind revision id is exactly re-pinnable.
    projected = project_world_graph(_projection_request(revision_pin=d_b))
    assert projected.snapshot.revision_id == d_b
    assert projected.snapshot.head_revision_id == d_b
    assert projected.snapshot.is_head is True
    assert any(n.node_id == "node:cas-winner" for n in projected.nodes)
    assert not any(n.node_id == "node:cas-loser" for n in projected.nodes)

    # Cold legacy-A access after D_B: all caches deleted, the A pin still
    # serves the exact adoption revision D_A (winner absent).
    shutil.rmtree(cache_root)
    storage.clear_world_graph_cache_roots()
    projected_a = project_world_graph(
        _projection_request(revision_pin=FROZEN_HEAD_REVISION)
    )
    assert projected_a.snapshot.revision_id == d_a
    assert projected_a.snapshot.head_revision_id == d_b
    assert projected_a.snapshot.is_head is False
    assert not any(n.node_id == "node:cas-winner" for n in projected_a.nodes)

    assert _tree_digest(frozen_root) == frozen_digest_before


@pytest.mark.integration
def test_adopted_membership_tamper_fails_closed(write_world):
    """§3: mutating any adopted DungeonMind row (payload + fingerprint, so the
    row still reads) changes the recomputed V3 membership digest and refuses
    service."""
    import psycopg
    from dungeonmind.infrastructure.postgres.serialization import (
        dump_payload,
        model_fingerprint,
    )

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    victim = bundle.contributions.list_for_world(WORLD_ID)[0]
    tampered = victim.model_copy(update={"authored_by": "tampered:intruder"})
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE dungeonmind.graph_contributions "
            "SET payload = %s, record_fingerprint = %s "
            "WHERE contribution_id = %s",
            (
                json.dumps(dump_payload(tampered)),
                model_fingerprint(tampered),
                victim.contribution_id,
            ),
        )
        conn.commit()

    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.ensure_hydrated_authority(
            WORLD_ID,
            database_url=dsn,
            cache_root=write_world["cache_root"],
            frozen_root=write_world["frozen_root"],
        )
    assert excinfo.value.code == "adopted_membership_mismatch"
    assert wga.authority_error_status_code(excinfo.value) == 409
