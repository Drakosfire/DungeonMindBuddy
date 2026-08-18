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
    storage.register_world_graph_cache_root(cache)
    result = storage.publish_world_graph_revision(
        cache / "nested", WORLD_ID, _minimal_store(), operation_ids=["test"]
    )
    assert result.revision.revision_id
    # A sibling outside the registered root stays frozen.
    with pytest.raises(WorldGraphAuthorityQuiescedError):
        storage.publish_world_graph_revision(
            tmp_path / "elsewhere", WORLD_ID, _minimal_store(), operation_ids=["test"]
        )


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
    root, routed = wga.route_service_read(request, None, default_root=tmp_path)
    assert root == tmp_path
    assert routed is request


def test_route_service_read_passthrough_in_quiesced(tmp_path, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_QUIESCED
    )
    request = _projection_request()
    root, routed = wga.route_service_read(request, None, default_root=tmp_path)
    assert root == tmp_path
    assert routed is request


def test_route_service_read_explicit_root_bypasses_dungeonmind(tmp_path, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    explicit = tmp_path / "explicit"
    request = _projection_request()
    root, routed = wga.route_service_read(request, explicit, default_root=tmp_path)
    assert root == explicit.resolve()
    assert routed is request


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


def test_v1_review_expressibility_blockers():
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    node_assertion = {
        "assertion_id": "assertion:node1",
        "assertion_kind": "node",
        "subject_node_id": "node:x",
        "label": "X",
        "value": {"kind": "npc"},
        "evidence_ref_ids": ["evidence:1"],
        "acceptance_state": "accepted",
        "contribution_id": "contribution:1",
    }
    edge_with_label = {
        "assertion_id": "assertion:edge1",
        "assertion_kind": "edge",
        "subject_node_id": "node:x",
        "target_node_id": "node:y",
        "predicate": "knows",
        "label": "knows",
        "value": {},
        "evidence_ref_ids": ["evidence:1"],
        "acceptance_state": "accepted",
        "contribution_id": "contribution:1",
    }
    plain_alias = {
        "assertion_id": "assertion:alias1",
        "assertion_kind": "alias",
        "subject_node_id": "node:x",
        "value": {"alias": "X the Elder"},
        "evidence_ref_ids": ["evidence:1"],
        "acceptance_state": "accepted",
        "contribution_id": "contribution:1",
    }
    from graph_memory.kernel.contribution_models import GraphContribution

    contribution = GraphContribution.model_validate(
        {
            "contribution_id": "contribution:1",
            "world_id": WORLD_ID,
            "source_kind": "source_extraction",
            "produced_at": "2026-08-18T00:00:00Z",
            "accepted_assertions": [node_assertion, edge_with_label, plain_alias],
        }
    )
    blockers = wga._v1_review_expressibility_blockers(contribution)
    blocked_ids = {b["assertion_id"] for b in blockers}
    assert "assertion:node1" in blocked_ids  # node kind is not v1-reviewable
    assert "assertion:edge1" in blocked_ids  # edge kind is not v1-reviewable
    assert "assertion:alias1" not in blocked_ids  # bare alias is v1-expressible


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
def test_projection_read_served_from_dungeonmind(hydrated):
    """§10: the normal projection service returns Eldyrwild data backed by DungeonMind.

    Called rootless: the service itself routes through the configured
    authority, proving the routing seam rather than just the cache content.
    """
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph,
    )

    projected = project_world_graph(_projection_request())
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
    # The served snapshot revision is the hydrated head, not a Buddy file rev.
    assert projected.snapshot.revision_id == hydrated["handle"].buddy_revision_id


@pytest.mark.integration
def test_retrieval_read_served_from_dungeonmind(hydrated):
    """§10: the normal object/evidence/neighborhood path returns exact data.

    Called rootless: the service routes through the configured authority.
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
    routed_object = retrieval.get_campaign_object(object_request)
    frozen_object = retrieval.get_campaign_object(object_request, root=frozen)
    assert routed_object.outcome == frozen_object.outcome
    assert (
        routed_object.model_dump(mode="json")["nodes"]
        == (frozen_object.model_dump(mode="json")["nodes"])
    )
    assert (
        routed_object.model_dump(mode="json")["attributes"]
        == (frozen_object.model_dump(mode="json")["attributes"])
    )
    assert routed_object.snapshot.revision_id == hydrated["handle"].buddy_revision_id

    neighborhood_request = WorldGraphNeighborhoodRequest.model_validate(
        {
            "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "seedNodeIds": [node_id],
        }
    )
    routed_neighborhood = retrieval.get_object_neighborhood(neighborhood_request)
    frozen_neighborhood = retrieval.get_object_neighborhood(
        neighborhood_request, root=frozen
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
    """§10: a real exact-A reference remains openable after the switch."""
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph,
    )

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    # Service-level: a pinned exact-A projection resolves through the bridge.
    projected = project_world_graph(
        _projection_request(revision_pin=FROZEN_HEAD_REVISION)
    )
    assert projected.snapshot.revision_id == hydrated["handle"].buddy_revision_id

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
    assert handle.dungeonmind_head_revision_id == (
        hydrated["handle"].dungeonmind_head_revision_id
    )


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.mark.integration
def test_governed_write_fails_closed_and_changes_nothing(
    hydrated, tmp_path, monkeypatch
):
    """§10: the normal confirmed-publication path routes into DungeonMind and
    fails closed at the characterized governed-write gap; neither the frozen
    Buddy store nor the DungeonMind ledger is mutated."""
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

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    frozen_digest_before = _tree_digest(hydrated["frozen_root"])
    contributions_before = adopted_world_contributions(hydrated["dsn"])

    cache_root = hydrated["handle"].cache_world_root
    parent = hydrated["handle"].buddy_revision_id

    source = tmp_path / "session-26-recap.md"
    source.write_text("A new traveling tinker arrives in Mireward.\n")
    source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    artifact_id = "artifact:recap:longmont-c2:session-26-cutover-test"
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:cutover-write-test",
        "session_id": "session-26",
        "campaign_id": CAMPAIGN_ID,
        "source_artifact_ids": [artifact_id],
        "status": "preview",
        "nodes": [
            {
                "node_id": "node:cutover-tinker",
                "label": "Cutover Tinker",
                "node_type": "npc",
                "description": "A traveling tinker.",
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
                        "source_ref_id": "ref:tinker",
                        "source_artifact_id": artifact_id,
                        "source_anchor_id": "anchor:tinker",
                        "label": "span",
                        "evidence_role": "source_evidence",
                        "can_open_source": True,
                        "can_highlight_span": True,
                        "source_span_ref_id": "session-26:recap:paragraph:001",
                        "anchor_quotes": ["traveling tinker"],
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
        root=cache_root,
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
        world_root=str(cache_root),
    )

    class _Request:
        review_package = package
        assertion_ids = None

    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.confirm_via_dungeonmind(
            _Request(),
            world_root=hydrated["frozen_root"],
            database_url=hydrated["dsn"],
            cache_root=hydrated["cache_root"],
            frozen_root=hydrated["frozen_root"],
            confirming_principal="gm@confirm",
            assertion_ids=None,
            repo_root=tmp_path,
        )
    # The Buddy node assertion cannot be expressed in DungeonMind's v1 review
    # contract; the write fails closed before any mutation on either side.
    assert excinfo.value.code == "governed_write_inexpressible"

    assert _tree_digest(hydrated["frozen_root"]) == frozen_digest_before
    assert adopted_world_contributions(hydrated["dsn"]) == contributions_before


def adopted_world_contributions(dsn: str) -> list[str]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT contribution_id FROM dungeonmind.graph_contributions ORDER BY 1"
        ).fetchall()
    return [row[0] for row in rows]
