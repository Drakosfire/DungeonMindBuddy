"""Cutover: DungeonMind-backed World Graph authority (HANDOFF §10 evidence).

Two layers:

- **Unit layer (portable)** — no PostgreSQL, no live frozen store. Proves the
  quiescence guard, the translation content-addressing round-trip, replay
  ordering, read routing in the passthrough modes, error mapping, and typed
  V3/V4 receipt binding plus V4 manifest/M1 membership verification.
- **Integration layer (env-gated)** — requires
  ``DMB_CUTOVER_TEST_DATABASE_URL`` (a migrated, disposable PostgreSQL
  database; every table is truncated by the fixture) and the frozen
  pre-switch Eldyrwild store at ``DMB_CUTOVER_FROZEN_ROOT`` (default:
  the conventional operator ``out/`` root when present). Proves the §10
  evidence rows against the real sealed bundle and the real frozen snapshot.

CUTOVER R.3 reclassification: the hydration/read-routing machinery exercised
here is now **legacy/write compatibility** only. In ``dungeonmind`` authority
mode, production reads dispatch to the direct DungeonMind adapter (see
``tests/test_cutover_direct_dungeonmind_world_graph_reads.py``); the hydrated
Buddy graph remains solely as the governed-write/review compatibility path
until its own successor retires it. The write-side proofs in this module are
preserved unchanged.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
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
    """A cache root overlapping the durable graph tree in either direction is
    unsafe: equal/ancestor roots silently exempt every authoritative file from
    the quiescence guard, and a descendant cache (for example
    ``worlds/eldyrwild`` under ``worlds/``) would write derived files into the
    authoritative subtree while bypassing the guard there."""
    durable = tmp_path / "worlds"
    with pytest.raises(ValueError, match="overlaps durable"):
        storage.register_world_graph_cache_root(durable, world_root=durable)
    with pytest.raises(ValueError, match="overlaps durable"):
        storage.register_world_graph_cache_root(tmp_path, world_root=durable)
    # Descendant caches inside the durable graph_memory tree are rejected too.
    with pytest.raises(ValueError, match="overlaps durable"):
        storage.register_world_graph_cache_root(
            durable / "graph_memory", world_root=durable
        )
    with pytest.raises(ValueError, match="overlaps durable"):
        storage.register_world_graph_cache_root(
            durable / "graph_memory" / "worlds" / WORLD_ID, world_root=durable
        )
    # A disjoint sibling cache root remains registerable.
    storage.register_world_graph_cache_root(tmp_path / "cache", world_root=durable)
    storage.register_world_graph_cache_root(durable / "cache", world_root=durable)


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


# ---------------------------------------------------------------------------
# V3/V4 hydrated-authority compatibility (portable; no live DB)
# ---------------------------------------------------------------------------

_COMPAT_NOW = datetime(2026, 8, 23, 18, 0, tzinfo=UTC)
_COMPAT_ART = "src:adopted"
_COMPAT_REV = "srcrev:adopted"
_COMPAT_CONTRIB = "contrib:adopted"
_COMPAT_DECISION = "iddec:adopted"
_COMPAT_DESCENDANT_ART = "src:descendant"
_COMPAT_DESCENDANT_REV = "srcrev:descendant"
_COMPAT_DESCENDANT_ON_ADOPTED_REV = "srcrev:post-adoption-on-adopted"
_COMPAT_DESCENDANT_CONTRIB = "contrib:descendant"
_COMPAT_DESCENDANT_DECISION = "iddec:descendant"
_D_A = "rev:" + "a" * 32
_HEAD = "rev:" + "b" * 32


def _hex64(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _compat_provenance(*, source_world_revision_id: str = FROZEN_HEAD_REVISION):
    from dungeonmind.contracts.existing_world_adoption import (
        ExistingWorldAdoptionSourceProvenanceV1,
    )

    return ExistingWorldAdoptionSourceProvenanceV1(
        producer_id="dungeonmindbuddy",
        producer_revision="test",
        source_world_revision_id=source_world_revision_id,
        source_graph_payload_sha256=_hex64("payload"),
    )


def _compat_artifact(source_artifact_id: str, revision_id: str, *, campaign_id: str | None = None):
    from dungeonmind.contracts.evidence import (
        SourceArtifactV2,
        SourceAuthority,
        SourceDomain,
        SourceStatus,
    )
    from dungeonmind.contracts.vocabulary import Visibility

    return SourceArtifactV2(
        source_artifact_id=source_artifact_id,
        source_domain_key="producer.worldbuilding",
        source_domain=SourceDomain.WORLDBUILDING,
        world_id=WORLD_ID,
        campaign_id=campaign_id,
        session_id=None,
        uri=None,
        current_revision_id=revision_id,
        authority=SourceAuthority.PRIMARY,
        visibility=Visibility.GM,
        artifact_kind="note",
        document_class=None,
        review_state=None,
        source_visibility_state=None,
        workspace_document_ref=None,
        lineage={},
        status=SourceStatus.ACTIVE,
        created_at=_COMPAT_NOW,
        updated_at=_COMPAT_NOW,
    )


def _compat_revision(source_revision_id: str, source_artifact_id: str):
    from dungeonmind.contracts.evidence import SourceRevision

    return SourceRevision(
        source_revision_id=source_revision_id,
        source_artifact_id=source_artifact_id,
        content_sha256=_hex64(source_revision_id),
        body_storage="object_store",
        locator=f"object://{source_revision_id}",
        created_at=_COMPAT_NOW,
    )


def _compat_contribution(
    contribution_id: str, artifact_id: str, revision_id: str, *, authored_by: str | None = None
):
    from dungeonmind.contracts.contribution import (
        AcceptanceState,
        ContributionSourceKind,
        GraphContributionAssertionV2,
        GraphContributionV2,
    )

    return GraphContributionV2(
        contribution_id=contribution_id,
        world_id=WORLD_ID,
        source_kind=ContributionSourceKind.MANUAL_IMPORT,
        source_artifact_id=artifact_id,
        source_revision_id=revision_id,
        produced_at=_COMPAT_NOW,
        campaign_scope=CAMPAIGN_ID,
        authored_by=authored_by,
        assertions=[
            GraphContributionAssertionV2(
                assertion_id=f"asrt:{contribution_id}",
                assertion_kind="attribute",
                subject_object_id="obj:college",
                label="imported",
                source_artifact_id=artifact_id,
                source_revision_id=revision_id,
                campaign_scope=CAMPAIGN_ID,
                acceptance_state=AcceptanceState.ACCEPTED,
            )
        ],
    )


def _compat_decision(decision_id: str):
    from dungeonmind.contracts.identity import (
        IdentityDecisionKind,
        IdentityDecisionRecordV2,
        IdentityDecisionStatus,
    )

    return IdentityDecisionRecordV2(
        decision_id=decision_id,
        world_id=WORLD_ID,
        decision_kind=IdentityDecisionKind.ALIAS_ADD,
        subject_object_ids=["obj:college"],
        alias="College",
        status=IdentityDecisionStatus.ACTIVE,
        created_at=_COMPAT_NOW,
    )


def _compat_membership_digest(*, artifacts, revisions, contributions, decisions):
    from dungeonmind.domain.existing_world_membership import (
        existing_world_adoption_membership_sha256,
    )

    return existing_world_adoption_membership_sha256(
        source_artifacts=artifacts,
        source_revisions=revisions,
        contributions=contributions,
        identity_decisions=decisions,
    )


def _compat_v3_receipt(*, membership_sha256: str):
    from dungeonmind.contracts.existing_world_adoption import (
        ExistingWorldAdoptionReceiptV3,
    )

    return ExistingWorldAdoptionReceiptV3(
        adoption_id="adopt:compat-v3",
        world_id=WORLD_ID,
        bundle_sha256=_hex64("bundle"),
        source_provenance=_compat_provenance(),
        published_revision_id=_D_A,
        graph_schema="dm_union_graph_v6",
        graph_payload_sha256=_hex64("graph"),
        adopted_at=_COMPAT_NOW,
        source_artifact_count=1,
        source_revision_count=1,
        contribution_count=1,
        identity_decision_count=1,
        membership_sha256=membership_sha256,
    )


def _compat_v4_receipt(*, membership_sha256: str, effective_membership_sha256: str):
    from dungeonmind.contracts.existing_world_adoption import (
        ExistingWorldAdoptionMembershipManifestV1,
        ExistingWorldAdoptionReceiptV4,
        ExistingWorldAdoptionSourceArtifactClassificationCorrectionV1,
        ExistingWorldAdoptionSourceClassificationRepairV1,
    )

    return ExistingWorldAdoptionReceiptV4(
        adoption_id="adopt:compat-v4",
        world_id=WORLD_ID,
        bundle_sha256=_hex64("bundle"),
        source_provenance=_compat_provenance(),
        published_revision_id=_D_A,
        graph_schema="dm_union_graph_v6",
        graph_payload_sha256=_hex64("graph"),
        adopted_at=_COMPAT_NOW,
        source_artifact_count=1,
        source_revision_count=1,
        contribution_count=1,
        identity_decision_count=1,
        membership_sha256=membership_sha256,
        effective_membership_sha256=effective_membership_sha256,
        membership_manifest=ExistingWorldAdoptionMembershipManifestV1(
            source_artifact_ids=sorted([_COMPAT_ART]),
            source_revision_ids=sorted([_COMPAT_REV]),
            contribution_ids=sorted([_COMPAT_CONTRIB]),
            identity_decision_ids=sorted([_COMPAT_DECISION]),
        ),
        source_classification_repair=ExistingWorldAdoptionSourceClassificationRepairV1(
            repair_id="repair:compat-v4",
            repaired_at=_COMPAT_NOW,
            observed_pre_repair_membership_sha256=membership_sha256,
            effective_membership_sha256=effective_membership_sha256,
            corrections=[
                ExistingWorldAdoptionSourceArtifactClassificationCorrectionV1(
                    source_artifact_id=_COMPAT_ART,
                    original_record_fingerprint=_hex64("original-fp"),
                    effective_record_fingerprint=_hex64("effective-fp"),
                    changed_fields=["campaign_id"],
                    original_visibility=None,
                    effective_visibility=None,
                    original_campaign_id=CAMPAIGN_ID,
                    effective_campaign_id=None,
                )
            ],
        ),
    )


class _FakeAdoptions:
    def __init__(self, receipt):
        self._receipt = receipt

    def get_for_world(self, world_id: str):
        return self._receipt


class _FakeGraph:
    def __init__(self, head_revision_id: str, stored_revisions: dict | None = None):
        self._head_revision_id = head_revision_id
        self._stored_revisions = dict(stored_revisions or {})

    def get_head(self, world_id: str):
        return type("Head", (), {"head_revision_id": self._head_revision_id})()

    def get_revision(self, world_id: str, revision_id: str):
        return self._stored_revisions.get(revision_id)


class _FakeContributions:
    def __init__(self, rows):
        self._rows = list(rows)

    def list_for_world(self, world_id: str):
        return list(self._rows)


class _FakeIdentity:
    def __init__(self, rows):
        self._rows = list(rows)

    def list_for_world(self, world_id: str):
        return list(self._rows)


class _FakeSources:
    def __init__(self, artifacts, revisions):
        self._artifacts = list(artifacts)
        self._revisions_by_artifact: dict[str, list] = {}
        for revision in revisions:
            self._revisions_by_artifact.setdefault(revision.source_artifact_id, []).append(
                revision
            )

    def list_artifacts_for_world(self, world_id: str):
        return list(self._artifacts)

    def list_revisions(self, artifact_id: str):
        return list(self._revisions_by_artifact.get(artifact_id, []))


class _FakeBundle:
    def __init__(
        self,
        *,
        receipt,
        artifacts,
        revisions,
        contributions,
        decisions,
        head_id=_HEAD,
        stored_revisions: dict | None = None,
    ):
        self.existing_world_adoptions = _FakeAdoptions(receipt)
        self.world_graph = _FakeGraph(head_id, stored_revisions)
        self.contributions = _FakeContributions(contributions)
        self.identity_decisions = _FakeIdentity(decisions)
        self.sources = _FakeSources(artifacts, revisions)


def _write_frozen_store(root: Path, *, contribution_ids: list[str], decision_ids: list[str]) -> Path:
    world = root / "graph_memory/worlds" / WORLD_ID
    world.mkdir(parents=True)
    (world / "head.json").write_text(json.dumps({"head_revision_id": FROZEN_HEAD_REVISION}))
    (world / "contribution_index.json").write_text(
        json.dumps(
            {
                "world_id": WORLD_ID,
                "all_contribution_ids": contribution_ids,
                "active_contribution_ids": contribution_ids,
                "superseded_contribution_ids": [],
                "retracted_contribution_ids": [],
                "failed_contribution_ids": [],
            }
        )
    )
    (world / "identity_decision_index.json").write_text(
        json.dumps({"world_id": WORLD_ID, "all_decision_ids": decision_ids})
    )
    return root


_HYDRATE_ART = "src:hydrate-adopted"
_HYDRATE_REV = "srcrev:hydrate-adopted"
_HYDRATE_CONTRIB = "contribution:" + "c" * 16
_HYDRATE_NODE = "obj:college"


def _hydratable_assertion_id() -> str:
    from graph_memory.kernel.contributions import compute_assertion_id

    return compute_assertion_id(
        assertion_kind="node",
        subject_node_id=_HYDRATE_NODE,
        target_node_id=None,
        predicate=None,
        label="College",
        value={},
        campaign_scope=CAMPAIGN_ID,
        temporal_scope=None,
        epistemic_kind="asserted",
        visibility="gm",
    )


def _hydratable_contribution():
    from dungeonmind.contracts.contribution import (
        AcceptanceState,
        ContributionSourceKind,
        GraphContributionAssertionV2,
        GraphContributionV2,
    )

    return GraphContributionV2(
        contribution_id=_HYDRATE_CONTRIB,
        world_id=WORLD_ID,
        source_kind=ContributionSourceKind.MANUAL_IMPORT,
        source_artifact_id=_HYDRATE_ART,
        source_revision_id=_HYDRATE_REV,
        produced_at=_COMPAT_NOW,
        campaign_scope=CAMPAIGN_ID,
        assertions=[
            GraphContributionAssertionV2(
                assertion_id=_hydratable_assertion_id(),
                assertion_kind="node",
                subject_object_id=_HYDRATE_NODE,
                label="College",
                source_artifact_id=_HYDRATE_ART,
                source_revision_id=_HYDRATE_REV,
                campaign_scope=CAMPAIGN_ID,
                acceptance_state=AcceptanceState.ACCEPTED,
            )
        ],
    )


def _hydratable_v4_receipt(
    *,
    membership_sha256: str,
    effective_membership_sha256: str,
    source_world_revision_id: str,
):
    from dungeonmind.contracts.existing_world_adoption import (
        ExistingWorldAdoptionMembershipManifestV1,
        ExistingWorldAdoptionReceiptV4,
        ExistingWorldAdoptionSourceArtifactClassificationCorrectionV1,
        ExistingWorldAdoptionSourceClassificationRepairV1,
    )

    return ExistingWorldAdoptionReceiptV4(
        adoption_id="adopt:compat-v4-hydrate",
        world_id=WORLD_ID,
        bundle_sha256=_hex64("bundle"),
        source_provenance=_compat_provenance(
            source_world_revision_id=source_world_revision_id
        ),
        published_revision_id=_D_A,
        graph_schema="dm_union_graph_v6",
        graph_payload_sha256=_hex64("graph"),
        adopted_at=_COMPAT_NOW,
        source_artifact_count=1,
        source_revision_count=1,
        contribution_count=1,
        identity_decision_count=0,
        membership_sha256=membership_sha256,
        effective_membership_sha256=effective_membership_sha256,
        membership_manifest=ExistingWorldAdoptionMembershipManifestV1(
            source_artifact_ids=sorted([_HYDRATE_ART]),
            source_revision_ids=sorted([_HYDRATE_REV]),
            contribution_ids=sorted([_HYDRATE_CONTRIB]),
            identity_decision_ids=[],
        ),
        source_classification_repair=ExistingWorldAdoptionSourceClassificationRepairV1(
            repair_id="repair:compat-v4-hydrate",
            repaired_at=_COMPAT_NOW,
            observed_pre_repair_membership_sha256=membership_sha256,
            effective_membership_sha256=effective_membership_sha256,
            corrections=[
                ExistingWorldAdoptionSourceArtifactClassificationCorrectionV1(
                    source_artifact_id=_HYDRATE_ART,
                    original_record_fingerprint=_hex64("original-fp"),
                    effective_record_fingerprint=_hex64("effective-fp"),
                    changed_fields=["campaign_id"],
                    original_visibility=None,
                    effective_visibility=None,
                    original_campaign_id=CAMPAIGN_ID,
                    effective_campaign_id=None,
                )
            ],
        ),
    )


def _stored_adoption_revision(*, graph_payload: dict):
    from types import SimpleNamespace

    return SimpleNamespace(
        graph_payload=graph_payload,
        revision=SimpleNamespace(
            revision_id=_D_A,
            parent_revision_id=None,
            operation_ids=[],
        ),
    )


def _write_hydratable_frozen_store(root: Path, *, contribution_id: str) -> tuple[Path, str]:
    """Publish a minimal frozen Buddy head with a real replay manifest."""
    from graph_memory.union_supergraph.model import ContributionReplayManifestEntry

    store = _minimal_store()
    store = store.model_copy(
        update={
            "campaign_id": CAMPAIGN_ID,
            "focus_session_id": "compat-session",
            "contribution_replay_manifest": [
                ContributionReplayManifestEntry(
                    contribution_id=contribution_id,
                    status="active",
                    source_payload_sha256=_hex64("hydrate-source"),
                )
            ],
        }
    )
    result = storage.publish_world_graph_revision(
        root, WORLD_ID, store, operation_ids=["compat:hydrate-frozen"]
    )
    frozen_head = result.revision.revision_id
    world = root / "graph_memory/worlds" / WORLD_ID
    (world / "contribution_index.json").write_text(
        json.dumps(
            {
                "world_id": WORLD_ID,
                "all_contribution_ids": [contribution_id],
                "active_contribution_ids": [contribution_id],
                "superseded_contribution_ids": [],
                "retracted_contribution_ids": [],
                "failed_contribution_ids": [],
            }
        )
    )
    (world / "identity_decision_index.json").write_text(
        json.dumps({"world_id": WORLD_ID, "all_decision_ids": []})
    )
    return root, frozen_head


def _compat_world_rows(*, include_descendants: bool = True, omit_adopted_artifact: bool = False):
    adopted_artifact = _compat_artifact(_COMPAT_ART, _COMPAT_REV)
    adopted_revision = _compat_revision(_COMPAT_REV, _COMPAT_ART)
    adopted_contribution = _compat_contribution(_COMPAT_CONTRIB, _COMPAT_ART, _COMPAT_REV)
    adopted_decision = _compat_decision(_COMPAT_DECISION)
    artifacts = [] if omit_adopted_artifact else [adopted_artifact]
    revisions = [adopted_revision]
    contributions = [adopted_contribution]
    decisions = [adopted_decision]
    if include_descendants:
        artifacts.append(_compat_artifact(_COMPAT_DESCENDANT_ART, _COMPAT_DESCENDANT_REV))
        revisions.extend(
            [
                _compat_revision(_COMPAT_DESCENDANT_REV, _COMPAT_DESCENDANT_ART),
                _compat_revision(_COMPAT_DESCENDANT_ON_ADOPTED_REV, _COMPAT_ART),
            ]
        )
        contributions.append(
            _compat_contribution(
                _COMPAT_DESCENDANT_CONTRIB, _COMPAT_DESCENDANT_ART, _COMPAT_DESCENDANT_REV
            )
        )
        decisions.append(_compat_decision(_COMPAT_DESCENDANT_DECISION))
    return {
        "adopted": (adopted_artifact, adopted_revision, adopted_contribution, adopted_decision),
        "artifacts": artifacts,
        "revisions": revisions,
        "contributions": contributions,
        "decisions": decisions,
    }


def test_dungeonmind_pin_exposes_typed_v4_receipt_contract():
    """Exact current DungeonMind pin still exposes the public V4/manifest types."""
    from dungeonmind.contracts.existing_world_adoption import (
        EXISTING_WORLD_ADOPTION_RECEIPT_V4_SCHEMA,
        ExistingWorldAdoptionMembershipManifestV1,
        ExistingWorldAdoptionReceiptV4,
    )

    pin = "c5d3688587b0f5d506e0f7d64f33eb0628bac896"
    assert pin in (REPO_ROOT / "pyproject.toml").read_text()
    assert pin in (REPO_ROOT / "uv.lock").read_text()
    assert ExistingWorldAdoptionReceiptV4.model_fields["schema_version"].default == (
        EXISTING_WORLD_ADOPTION_RECEIPT_V4_SCHEMA
    )
    assert "source_artifact_ids" in ExistingWorldAdoptionMembershipManifestV1.model_fields
    assert "effective_membership_sha256" in ExistingWorldAdoptionReceiptV4.model_fields


def test_v3_binder_uses_membership_sha256_and_no_manifest(tmp_path):
    """§9.2: typed V3 bind still serves membership_sha256 and keeps V3 selection."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    rows = _compat_world_rows()
    adopted = rows["adopted"]
    m0 = _compat_membership_digest(
        artifacts=[adopted[0]],
        revisions=[adopted[1]],
        contributions=[adopted[2]],
        decisions=[adopted[3]],
    )
    receipt = _compat_v3_receipt(membership_sha256=m0)
    frozen = _write_frozen_store(
        tmp_path, contribution_ids=[_COMPAT_CONTRIB], decision_ids=[_COMPAT_DECISION]
    )
    bundle = _FakeBundle(
        receipt=receipt,
        artifacts=rows["artifacts"],
        revisions=rows["revisions"],
        contributions=rows["contributions"],
        decisions=rows["decisions"],
    )
    binding = wga.bind_world_authority(bundle, WORLD_ID, frozen_root=frozen)
    assert binding.membership_sha256 == receipt.membership_sha256
    assert binding.membership_manifest is None
    wga._verify_adopted_membership(bundle, WORLD_ID, binding=binding, frozen_root=frozen)


def test_v4_binder_uses_effective_checkpoint_and_exact_manifest(tmp_path):
    """§9.3: typed V4 bind serves M1 and carries the receipt manifest."""
    from dungeonmind.contracts.existing_world_adoption import ExistingWorldAdoptionReceiptV4

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    rows = _compat_world_rows()
    adopted = rows["adopted"]
    m0 = _hex64("historical-m0")
    m1 = _compat_membership_digest(
        artifacts=[adopted[0]],
        revisions=[adopted[1]],
        contributions=[adopted[2]],
        decisions=[adopted[3]],
    )
    receipt = _compat_v4_receipt(membership_sha256=m0, effective_membership_sha256=m1)
    assert isinstance(receipt, ExistingWorldAdoptionReceiptV4)
    frozen = _write_frozen_store(
        tmp_path,
        contribution_ids=[_COMPAT_CONTRIB, _COMPAT_DESCENDANT_CONTRIB],
        decision_ids=[_COMPAT_DECISION, _COMPAT_DESCENDANT_DECISION],
    )
    bundle = _FakeBundle(
        receipt=receipt,
        artifacts=rows["artifacts"],
        revisions=rows["revisions"],
        contributions=rows["contributions"],
        decisions=rows["decisions"],
    )
    binding = wga.bind_world_authority(bundle, WORLD_ID, frozen_root=frozen)
    assert binding.membership_sha256 == receipt.effective_membership_sha256
    assert binding.membership_sha256 != receipt.membership_sha256
    assert binding.membership_manifest is receipt.membership_manifest
    assert list(binding.membership_manifest.source_artifact_ids) == [_COMPAT_ART]


def test_unsupported_receipt_with_effective_checkpoint_is_rejected(tmp_path):
    """§9.4: getattr/lookalike objects and pre-V3 receipts fail closed."""
    from types import SimpleNamespace

    from dungeonmind.contracts.existing_world_adoption import ExistingWorldAdoptionReceiptV2

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    frozen = _write_frozen_store(
        tmp_path, contribution_ids=[_COMPAT_CONTRIB], decision_ids=[_COMPAT_DECISION]
    )
    lookalike = SimpleNamespace(
        schema_version="dm_existing_world_adoption_receipt_lookalike",
        membership_sha256=_hex64("m0"),
        effective_membership_sha256=_hex64("m1"),
        membership_manifest=object(),
        source_provenance=_compat_provenance(),
        adoption_id="adopt:lookalike",
        published_revision_id=_D_A,
        graph_schema="dm_union_graph_v6",
        source_artifact_count=1,
        source_revision_count=1,
        contribution_count=1,
        identity_decision_count=1,
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as lookalike_exc:
        wga.bind_world_authority(
            _FakeBundle(
                receipt=lookalike,
                artifacts=[],
                revisions=[],
                contributions=[],
                decisions=[],
            ),
            WORLD_ID,
            frozen_root=frozen,
        )
    assert lookalike_exc.value.code == "adoption_receipt_not_v3"

    v2 = ExistingWorldAdoptionReceiptV2(
        adoption_id="adopt:compat-v2",
        world_id=WORLD_ID,
        bundle_sha256=_hex64("bundle"),
        source_provenance=_compat_provenance(),
        published_revision_id=_D_A,
        graph_schema="dm_union_graph_v6",
        graph_payload_sha256=_hex64("graph"),
        adopted_at=_COMPAT_NOW,
        source_artifact_count=1,
        source_revision_count=1,
        contribution_count=1,
        identity_decision_count=1,
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as v2_exc:
        wga.bind_world_authority(
            _FakeBundle(
                receipt=v2,
                artifacts=[],
                revisions=[],
                contributions=[],
                decisions=[],
            ),
            WORLD_ID,
            frozen_root=frozen,
        )
    assert v2_exc.value.code == "adoption_receipt_not_v3"


def test_v4_membership_ignores_descendants_and_frozen_store_extras(tmp_path):
    """§9.5: V4 M1 is manifest-selected; descendants and frozen extras do not join."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    rows = _compat_world_rows()
    adopted = rows["adopted"]
    descendant_inclusive = _compat_membership_digest(
        artifacts=rows["artifacts"],
        revisions=rows["revisions"],
        contributions=rows["contributions"],
        decisions=rows["decisions"],
    )
    m1 = _compat_membership_digest(
        artifacts=[adopted[0]],
        revisions=[adopted[1]],
        contributions=[adopted[2]],
        decisions=[adopted[3]],
    )
    assert m1 != descendant_inclusive
    receipt = _compat_v4_receipt(
        membership_sha256=_hex64("historical-m0"),
        effective_membership_sha256=m1,
    )
    frozen = _write_frozen_store(
        tmp_path,
        contribution_ids=[_COMPAT_CONTRIB, _COMPAT_DESCENDANT_CONTRIB],
        decision_ids=[_COMPAT_DECISION, _COMPAT_DESCENDANT_DECISION],
    )
    bundle = _FakeBundle(
        receipt=receipt,
        artifacts=rows["artifacts"],
        revisions=rows["revisions"],
        contributions=rows["contributions"],
        decisions=rows["decisions"],
    )
    binding = wga.bind_world_authority(bundle, WORLD_ID, frozen_root=frozen)
    wga._verify_adopted_membership(bundle, WORLD_ID, binding=binding, frozen_root=frozen)


def test_v4_missing_or_mutated_member_or_wrong_checkpoint_fails_closed(tmp_path):
    """§9.6: missing member, mutated member, and wrong M1 all refuse service."""
    from dataclasses import replace

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    rows = _compat_world_rows()
    adopted = rows["adopted"]
    m1 = _compat_membership_digest(
        artifacts=[adopted[0]],
        revisions=[adopted[1]],
        contributions=[adopted[2]],
        decisions=[adopted[3]],
    )
    receipt = _compat_v4_receipt(
        membership_sha256=_hex64("historical-m0"),
        effective_membership_sha256=m1,
    )
    frozen = _write_frozen_store(
        tmp_path, contribution_ids=[_COMPAT_CONTRIB], decision_ids=[_COMPAT_DECISION]
    )

    missing_rows = _compat_world_rows(omit_adopted_artifact=True)
    missing_bundle = _FakeBundle(
        receipt=receipt,
        artifacts=missing_rows["artifacts"],
        revisions=missing_rows["revisions"],
        contributions=missing_rows["contributions"],
        decisions=missing_rows["decisions"],
    )
    missing_binding = wga.bind_world_authority(
        missing_bundle, WORLD_ID, frozen_root=frozen
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as missing_exc:
        wga._verify_adopted_membership(
            missing_bundle, WORLD_ID, binding=missing_binding, frozen_root=frozen
        )
    assert missing_exc.value.code == "adopted_membership_incomplete"

    mutated_contribution = _compat_contribution(
        _COMPAT_CONTRIB, _COMPAT_ART, _COMPAT_REV, authored_by="tampered:intruder"
    )
    mutated_bundle = _FakeBundle(
        receipt=receipt,
        artifacts=rows["artifacts"],
        revisions=rows["revisions"],
        contributions=[mutated_contribution, rows["contributions"][1]],
        decisions=rows["decisions"],
    )
    mutated_binding = wga.bind_world_authority(
        mutated_bundle, WORLD_ID, frozen_root=frozen
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as mutated_exc:
        wga._verify_adopted_membership(
            mutated_bundle, WORLD_ID, binding=mutated_binding, frozen_root=frozen
        )
    assert mutated_exc.value.code == "adopted_membership_mismatch"

    valid_bundle = _FakeBundle(
        receipt=receipt,
        artifacts=rows["artifacts"],
        revisions=rows["revisions"],
        contributions=rows["contributions"],
        decisions=rows["decisions"],
    )
    valid_binding = wga.bind_world_authority(valid_bundle, WORLD_ID, frozen_root=frozen)
    wrong_binding = replace(valid_binding, membership_sha256=_hex64("wrong-m1"))
    with pytest.raises(wga.WorldGraphAuthorityError) as wrong_exc:
        wga._verify_adopted_membership(
            valid_bundle, WORLD_ID, binding=wrong_binding, frozen_root=frozen
        )
    assert wrong_exc.value.code == "adopted_membership_mismatch"


def test_v4_hydrated_route_stays_on_legacy_path_when_direct_read_absent(
    tmp_path, monkeypatch
):
    """§9.7: valid V4 hydrates through the real cache/replay path; direct reads stay off."""
    import sys

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    frozen, frozen_head = _write_hydratable_frozen_store(
        tmp_path / "frozen", contribution_id=_HYDRATE_CONTRIB
    )
    adopted_artifact = _compat_artifact(_HYDRATE_ART, _HYDRATE_REV)
    adopted_revision = _compat_revision(_HYDRATE_REV, _HYDRATE_ART)
    adopted_contribution = _hydratable_contribution()
    descendant_artifact = _compat_artifact(_COMPAT_DESCENDANT_ART, _COMPAT_DESCENDANT_REV)
    descendant_revision = _compat_revision(_COMPAT_DESCENDANT_REV, _COMPAT_DESCENDANT_ART)
    descendant_contribution = _compat_contribution(
        _COMPAT_DESCENDANT_CONTRIB, _COMPAT_DESCENDANT_ART, _COMPAT_DESCENDANT_REV
    )
    m1 = _compat_membership_digest(
        artifacts=[adopted_artifact],
        revisions=[adopted_revision],
        contributions=[adopted_contribution],
        decisions=[],
    )
    receipt = _hydratable_v4_receipt(
        membership_sha256=_hex64("historical-m0"),
        effective_membership_sha256=m1,
        source_world_revision_id=frozen_head,
    )
    bundle = _FakeBundle(
        receipt=receipt,
        artifacts=[adopted_artifact, descendant_artifact],
        revisions=[adopted_revision, descendant_revision],
        contributions=[adopted_contribution, descendant_contribution],
        decisions=[],
        head_id=_D_A,
        stored_revisions={
            _D_A: _stored_adoption_revision(
                graph_payload={
                    "objects": [{"object_id": _HYDRATE_NODE}],
                    "relationships": [],
                }
            )
        },
    )
    cache_root = tmp_path / "authority-cache"
    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        "postgresql://dungeonmind:test@127.0.0.1:1/test",
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(frozen))
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_CACHE_ROOT", str(cache_root))
    monkeypatch.delenv("DUNGEONMIND_WORLD_GRAPH_DIRECT_READ", raising=False)
    monkeypatch.setattr(wga, "_open_repository_bundle", lambda database_url: bundle)
    # Other R.3 tests import the direct adapter in-process. Pop it so this
    # assertion proves *this* hydrated route did not import it, not that the
    # module has never existed in the pytest session.
    sys.modules.pop(
        "apps.live_control_server.integrations.dungeonmind.world_graph_reads",
        None,
    )

    route = wga.route_service_read(_projection_request(), None, default_root=frozen)
    metadata = wga.read_hydration_metadata(route.graph_root)
    assert metadata is not None
    assert metadata["translation_version"] == wga.HYDRATION_TRANSLATION_VERSION
    assert metadata["membership_sha256"] == receipt.effective_membership_sha256
    assert metadata["dungeonmind_revision_id"] == _D_A
    buddy_revision_id = metadata["buddy_hydrated_revision_id"]
    assert str(buddy_revision_id).startswith("rev:")
    hydrated = storage.load_world_graph_revision(
        route.graph_root, WORLD_ID, str(buddy_revision_id)
    )
    assert _HYDRATE_NODE in hydrated.nodes
    assert route.graph_root.is_relative_to(cache_root.resolve())
    assert route.public_revision_id == _D_A
    assert route.public_head_revision_id == _D_A
    assert "apps.live_control_server.integrations.dungeonmind.world_graph_reads" not in (
        sys.modules
    )


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


def test_edge_predicate_qualification_round_trip():
    """The confirm path injects the explicit ``dm_predicate`` (swapping
    endpoints for reverse-mapped predicates); the hydration inverse strips
    exactly the derived qualification and un-swaps, so the Buddy
    content-addressed assertion id recomputes. Unmapped predicates fail
    closed — no invented mapping."""
    import json as _json
    from types import SimpleNamespace

    from graph_memory.kernel.contributions import compute_assertion_id

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    def _assertion(*, predicate: str, value: dict, subject: str, target: str):
        return SimpleNamespace(
            assertion_id=compute_assertion_id(
                assertion_kind="edge",
                subject_node_id=subject,
                target_node_id=target,
                predicate=predicate,
                label=predicate,
                value=value,
                campaign_scope=CAMPAIGN_ID,
                temporal_scope=None,
                epistemic_kind="asserted",
                visibility=None,
            ),
            assertion_kind="edge",
            subject_object_id=subject,
            object_object_id=target,
            predicate=predicate,
            label=predicate,
            value=_json.dumps(value),
        )

    # Direct-mapped predicate: qualify in place, no endpoint swap. The
    # endpoint kinds are admitted: npc → dnd5e:located_in → location.
    direct_value = {
        "edge_id": "edge:node:a:located_in:node:b",
        "predicate": "located_in",
        "session_ids": ["session-26"],
    }
    direct = _assertion(
        predicate="located_in", value=direct_value, subject="node:a", target="node:b"
    )
    update = wga._qualified_edge_update(
        direct, endpoint_kinds={"node:a": "npc", "node:b": "location"}
    )
    qualified_value = _json.loads(update["value"])
    assert qualified_value["dm_predicate"] == "dnd5e:located_in"
    assert qualified_value["edge_id"] == direct_value["edge_id"]
    assert "subject_object_id" not in update
    assert "object_object_id" not in update
    qualified = SimpleNamespace(**{**vars(direct), "value": update["value"]})
    stripped_value, subject, target = wga._strip_derived_dm_predicate(
        qualified, qualified_value
    )
    assert stripped_value == direct_value
    assert (subject, target) == ("node:a", "node:b")
    assert (
        compute_assertion_id(
            assertion_kind="edge",
            subject_node_id=subject,
            target_node_id=target,
            predicate="located_in",
            label="located_in",
            value=stripped_value,
            campaign_scope=CAMPAIGN_ID,
            temporal_scope=None,
            epistemic_kind="asserted",
            visibility=None,
        )
        == direct.assertion_id
    )

    # Reverse-mapped predicate: swap endpoints forward, un-swap on recovery.
    # Admitted orientation: dnd5e:owns is faction/group/npc/party/pc →
    # creature/item/location, so a location belonging to a faction qualifies.
    reverse_value = {
        "edge_id": "edge:node:a:belongs_to:node:b",
        "predicate": "belongs_to",
    }
    reverse = _assertion(
        predicate="belongs_to", value=reverse_value, subject="node:a", target="node:b"
    )
    reverse_update = wga._qualified_edge_update(
        reverse, endpoint_kinds={"node:a": "location", "node:b": "faction"}
    )
    assert _json.loads(reverse_update["value"])["dm_predicate"] == "dnd5e:owns"
    assert reverse_update["subject_object_id"] == "node:b"
    assert reverse_update["object_object_id"] == "node:a"
    qualified_reverse = SimpleNamespace(
        **{
            **vars(reverse),
            "value": reverse_update["value"],
            "subject_object_id": "node:b",
            "object_object_id": "node:a",
        }
    )
    stripped_reverse, r_subject, r_target = wga._strip_derived_dm_predicate(
        qualified_reverse, _json.loads(reverse_update["value"])
    )
    assert stripped_reverse == reverse_value
    assert (r_subject, r_target) == ("node:a", "node:b")
    assert (
        compute_assertion_id(
            assertion_kind="edge",
            subject_node_id=r_subject,
            target_node_id=r_target,
            predicate="belongs_to",
            label="belongs_to",
            value=stripped_reverse,
            campaign_scope=CAMPAIGN_ID,
            temporal_scope=None,
            epistemic_kind="asserted",
            visibility=None,
        )
        == reverse.assertion_id
    )

    # Intentionally unresolved predicates fail closed; nothing is invented.
    unmapped = _assertion(
        predicate="same_as",
        value={"edge_id": "edge:node:a:same_as:node:b"},
        subject="node:a",
        target="node:b",
    )
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga._qualified_edge_update(unmapped, endpoint_kinds={})
    assert excinfo.value.code == "governed_write_inexpressible"


def test_edge_endpoint_admission_enforced():
    """The name mapping alone does not admit an edge: the concrete endpoint
    kinds must be admitted for the qualified predicate by world-object-v5
    (``dnd5e:leads_to`` is Location→Location; ``dnd5e:owns`` is
    faction/group/npc/party/pc → creature/item/location). Inadmitted,
    unknown, or unmapped endpoint kinds fail closed — reverse-mapped
    predicates admit the swapped orientation."""
    import json as _json
    from types import SimpleNamespace

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    def _edge(*, predicate: str, subject: str, target: str):
        return SimpleNamespace(
            assertion_id=f"assertion:{subject}:{predicate}:{target}",
            assertion_kind="edge",
            subject_object_id=subject,
            object_object_id=target,
            predicate=predicate,
            label=predicate,
            value=_json.dumps(
                {
                    "edge_id": f"edge:{subject}:{predicate}:{target}",
                    "predicate": predicate,
                }
            ),
        )

    # Admitted: location leads_to location qualifies.
    update = wga._qualified_edge_update(
        _edge(predicate="leads_to", subject="node:a", target="node:b"),
        endpoint_kinds={"node:a": "location", "node:b": "location"},
    )
    assert _json.loads(update["value"])["dm_predicate"] == "dnd5e:leads_to"

    # Inadmitted subject/object kinds fail closed.
    for kinds in (
        {"node:a": "npc", "node:b": "location"},  # npc cannot lead_to
        {"node:a": "location", "node:b": "npc"},  # object must be a location
    ):
        with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
            wga._qualified_edge_update(
                _edge(predicate="leads_to", subject="node:a", target="node:b"),
                endpoint_kinds=kinds,
            )
        assert excinfo.value.code == "governed_write_inexpressible"
        assert excinfo.value.details.get("reason") == "endpoint_kind_not_admitted"

    # Unknown endpoint (absent from the hydrated head and the candidate) and
    # unmapped Buddy endpoint kind (job has no world-object-v5 term) fail.
    for kinds in ({"node:a": "location"}, {"node:a": "job", "node:b": "location"}):
        with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
            wga._qualified_edge_update(
                _edge(predicate="leads_to", subject="node:a", target="node:b"),
                endpoint_kinds=kinds,
            )
        assert excinfo.value.code == "governed_write_inexpressible"

    # Reverse-mapped admission uses the swapped orientation: a creature
    # belonging to an npc qualifies (dnd5e:owns — npc owns creature); an npc
    # belonging to a creature does not (a creature cannot own).
    reverse_ok = wga._qualified_edge_update(
        _edge(predicate="belongs_to", subject="node:a", target="node:b"),
        endpoint_kinds={"node:a": "creature", "node:b": "npc"},
    )
    assert _json.loads(reverse_ok["value"])["dm_predicate"] == "dnd5e:owns"
    assert reverse_ok["subject_object_id"] == "node:b"
    assert reverse_ok["object_object_id"] == "node:a"
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga._qualified_edge_update(
            _edge(predicate="belongs_to", subject="node:a", target="node:b"),
            endpoint_kinds={"node:a": "npc", "node:b": "creature"},
        )
    assert excinfo.value.code == "governed_write_inexpressible"
    assert excinfo.value.details.get("reason") == "endpoint_kind_not_admitted"


def test_edge_reverse_direction_audit_enforced():
    """The conformance contract's full-edge direction audit also gates
    accepted writes: an edge id carrying a reverse-qualifier pattern for its
    Buddy predicate (``is-threatened-by``) marks a relationship authored in
    the reverse direction, so name mapping plus admission-valid endpoints
    would publish inverted semantics. The writer fails closed before
    automatic translation — the same audit the conformance contract applies
    (``edge_has_reverse_direction_qualifier_v4``), keyed on the Buddy
    predicate and casefolded. A clean edge id with the same predicate and
    endpoint kinds qualifies."""
    import json as _json
    from types import SimpleNamespace

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    def _edge(*, predicate: str, edge_id: str, subject: str, target: str):
        return SimpleNamespace(
            assertion_id=f"assertion:{edge_id}",
            assertion_kind="edge",
            subject_object_id=subject,
            object_object_id=target,
            predicate=predicate,
            label=predicate,
            value=_json.dumps({"edge_id": edge_id, "predicate": predicate}),
        )

    # dnd5e:threatens admits npc → location, so only the direction audit can
    # fail these: the endpoint pair is valid for the qualified predicate.
    kinds = {"node:a": "npc", "node:b": "location"}
    for edge_id in (
        "edge:node:a:threatens:node:b:is-threatened-by-b",
        "edge:node:a:threatens:node:b:IS-THREATENED-BY-b",  # casefolded
        "edge:node:a:threatens:node:b:threatened-by-b",
    ):
        with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
            wga._qualified_edge_update(
                _edge(
                    predicate="threatens",
                    edge_id=edge_id,
                    subject="node:a",
                    target="node:b",
                ),
                endpoint_kinds=kinds,
            )
        assert excinfo.value.code == "governed_write_inexpressible"
        assert excinfo.value.details.get("reason") == "reverse_direction_qualifier"
        assert excinfo.value.details.get("dm_predicate") == "dnd5e:threatens"

    # The audit keys on the Buddy predicate: an attacks edge is audited
    # against the attacks patterns. dnd5e:attacks admits npc → npc, so here
    # too only the direction audit can fail the write.
    attack_kinds = {"node:a": "npc", "node:b": "npc"}
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga._qualified_edge_update(
            _edge(
                predicate="attacks",
                edge_id="edge:node:a:attacks:node:b:attacked-by-b",
                subject="node:a",
                target="node:b",
            ),
            endpoint_kinds=attack_kinds,
        )
    assert excinfo.value.details.get("reason") == "reverse_direction_qualifier"

    # Control: the same predicates and admitted endpoint kinds with clean
    # edge ids qualify.
    for predicate, control_kinds in (("threatens", kinds), ("attacks", attack_kinds)):
        update = wga._qualified_edge_update(
            _edge(
                predicate=predicate,
                edge_id=f"edge:node:a:{predicate}:node:b",
                subject="node:a",
                target="node:b",
            ),
            endpoint_kinds=control_kinds,
        )
        assert _json.loads(update["value"])["dm_predicate"] == f"dnd5e:{predicate}"


def test_temporal_scope_session_hint_round_trip():
    """Buddy's edge producer encodes real-world session provenance as
    ``temporal_scope={"session_id": ...}``. The confirm path normalizes the
    hint to ``None`` (DungeonMind carries real-world sessions as session
    refs, never as temporal scope), and the hydration inverse reconstructs
    the hint from the value's single ``session_ids`` entry so the
    content-addressed assertion id recomputes exactly."""
    import json as _json
    from types import SimpleNamespace

    from graph_memory.kernel.contributions import compute_assertion_id

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    value = {
        "edge_id": "edge:node:a:located_in:node:b",
        "predicate": "located_in",
        "session_ids": ["session-26"],
    }
    buddy_temporal = {"session_id": "session-26"}
    assertion_id = compute_assertion_id(
        assertion_kind="edge",
        subject_node_id="node:a",
        target_node_id="node:b",
        predicate="located_in",
        label="located_in",
        value=value,
        campaign_scope=CAMPAIGN_ID,
        temporal_scope=buddy_temporal,
        epistemic_kind="asserted",
        visibility=None,
    )

    # Forward: the session hint normalizes to None; other shapes pass through.
    assert wga._normalized_temporal_scope(buddy_temporal) is None
    assert wga._normalized_temporal_scope(None) is None
    assert wga._normalized_temporal_scope({"kind": "unknown"}) == {"kind": "unknown"}

    # Inverse: the stored assertion (temporal_scope None) recovers the hint,
    # so the content-addressed id recomputes exactly.
    stored = SimpleNamespace(
        assertion_id=assertion_id,
        assertion_kind="edge",
        subject_object_id="node:a",
        object_object_id="node:b",
        predicate="located_in",
        label="located_in",
        value=_json.dumps(value),
        campaign_scope=CAMPAIGN_ID,
        temporal_scope=None,
        epistemic_kind="asserted",
        evidence_refs=[],
        source_artifact_id="artifact:recap:longmont-c2:session-26",
        source_revision_id=None,
        acceptance_state="accepted",
        identity_resolution_outcome=None,
    )
    translated = wga._translate_assertion(
        stored, {assertion_id: "asserted"}, "contribution:1"
    )
    assert translated["assertion_id"] == assertion_id
    assert translated["temporal_scope"] == buddy_temporal


def test_build_v2_candidate_temporal_normalization_is_accept_only():
    """Buddy's real-world-session temporal hint (``{"session_id": ...}``) is
    normalized away only for assertions the GM accepted: DungeonMind carries
    that provenance as session refs at materialization, and only accepted
    assertions ever materialize. A rejected assertion is preserved in the
    durable review record exactly as adjudicated — session hint included —
    because it never needs materialization and must not be rewritten. The
    rejected edge here also has endpoints unknown to the hydrated head, so
    qualification would fail closed if it were attempted."""
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from graph_memory.kernel.contributions import (
        build_assertion,
        create_graph_contribution,
    )

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    artifact_id = "artifact:recap:longmont-c2:session-26"
    buddy_revision = "sha256:session-26-recap"
    session_hint = {"session_id": "session-26"}

    def _edge_assertion(*, acceptance: str, subject: str, target: str, edge_id: str):
        return build_assertion(
            assertion_kind="edge",
            acceptance_state=acceptance,
            subject_node_id=subject,
            target_node_id=target,
            predicate="located_in",
            label="located_in",
            value={
                "edge_id": edge_id,
                "predicate": "located_in",
                "session_ids": ["session-26"],
            },
            evidence_ref_ids=[],
            source_artifact_id=artifact_id,
            source_revision_id=buddy_revision,
            campaign_scope=CAMPAIGN_ID,
            epistemic_kind="asserted",
            temporal_scope=dict(session_hint),
        )

    accepted = _edge_assertion(
        acceptance="accepted",
        subject="node:a",
        target="node:b",
        edge_id="edge:node:a:located_in:node:b",
    )
    rejected = _edge_assertion(
        acceptance="rejected",
        subject="node:c",
        target="node:d",
        edge_id="edge:node:c:located_in:node:d",
    )
    contribution = create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id=artifact_id,
        source_revision_id=buddy_revision,
        campaign_scope=CAMPAIGN_ID,
        candidate_assertions=[],
        accepted_assertions=[accepted],
        rejected_assertions=[rejected],
    )
    store = SimpleNamespace(
        nodes={
            "node:a": SimpleNamespace(kind="npc"),
            "node:b": SimpleNamespace(kind="location"),
        }
    )
    candidate, verdict_states = wga._build_v2_candidate(
        contribution,
        store=store,
        pair_to_dm={(artifact_id, buddy_revision): "dm-source-revision"},
        produced_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
    )

    by_id = {assertion.assertion_id: assertion for assertion in candidate.assertions}
    assert set(by_id) == {accepted.assertion_id, rejected.assertion_id}
    # Accepted: qualified (dm_predicate injected) and the session hint is
    # normalized away — DungeonMind expresses it as session refs.
    accepted_out = by_id[accepted.assertion_id]
    assert accepted_out.temporal_scope is None
    import json as _json

    assert _json.loads(accepted_out.value)["dm_predicate"] == "dnd5e:located_in"
    # Rejected: preserved exactly as adjudicated — no qualification, and the
    # session hint survives in the durable review record.
    rejected_out = by_id[rejected.assertion_id]
    assert rejected_out.temporal_scope == session_hint
    assert "dm_predicate" not in _json.loads(rejected_out.value)
    assert verdict_states[accepted.assertion_id].name == "ACCEPTED"
    assert verdict_states[rejected.assertion_id].name == "REJECTED"


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


def _preview_node(
    artifact_id: str, *, node_id: str, label: str, node_type: str, span: str
) -> dict:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
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
                "source_ref_id": f"ref:{node_id}",
                "source_artifact_id": artifact_id,
                "source_anchor_id": f"anchor:{node_id}",
                "label": "span",
                "evidence_role": "source_evidence",
                "can_open_source": True,
                "can_highlight_span": True,
                "source_span_ref_id": span,
                "anchor_quotes": [label],
            }
        ],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _preview_edge(
    artifact_id: str,
    *,
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    predicate: str,
    span: str,
) -> dict:
    return {
        "edge_id": edge_id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "label": predicate,
        "relationship_type": predicate,
        "semantic_state": {
            "canon_state": "played_canon",
            "lifecycle_state": "candidate",
            "evidence_role": "source_evidence",
            "authority_state": "system_derived",
            "visibility_state": "gm_private",
        },
        "evidence_refs": [
            {
                "source_ref_id": f"ref:{edge_id}",
                "source_artifact_id": artifact_id,
                "source_anchor_id": f"anchor:{edge_id}",
                "label": "span",
                "evidence_role": "source_evidence",
                "can_open_source": True,
                "can_highlight_span": True,
                "source_span_ref_id": span,
                "anchor_quotes": [predicate],
            }
        ],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _seal_tinker_package(
    cache_world_root: Path,
    tmp_path: Path,
    *,
    preview_slug: str,
    node_id: str,
    label: str,
    extra_nodes: list[dict] | None = None,
    edges: list[dict] | None = None,
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
            _preview_node(
                artifact_id,
                node_id=node_id,
                label=label,
                node_type="npc",
                span="session-26:recap:paragraph:001",
            ),
            *list(extra_nodes or []),
        ],
        "edges": list(edges or []),
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


@pytest.mark.integration
def test_warm_cache_reverifies_adopted_membership(write_world, monkeypatch):
    """§3 repair: a valid existing hydration cache is never trusted on its
    own — the exact V3 adopted-membership verification reruns on every cache
    hit, so tampering with durable adopted rows after hydration fails closed
    instead of remaining invisible behind the warm cache."""
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
    cache_root = write_world["cache_root"]
    frozen_root = write_world["frozen_root"]

    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    # Sanity: the second call is a warm cache hit serving the same revision.
    again = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    assert again.buddy_revision_id == handle.buddy_revision_id
    assert again.selected_revision_id == handle.selected_revision_id

    # Tamper with an adopted row (payload + fingerprint, so the row still reads).
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

    # The warm-cache path must fail closed BEFORE any rebuild: the cached
    # directory still matches the revision, so only the re-verification can
    # see the tampering.
    def _no_rebuild(*args, **kwargs):
        raise AssertionError("warm cache hit must not rebuild from durable state")

    monkeypatch.setattr(wga, "hydrate_world_graph", _no_rebuild)
    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.ensure_hydrated_authority(
            WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
        )
    assert excinfo.value.code == "adopted_membership_mismatch"


@pytest.mark.integration
def test_governed_write_preserves_gm_partition_and_publishes_edges(write_world):
    """§3 repair: the DungeonMind writer preserves the GM's adjudication
    partition — a gate-rejected assertion receives a REJECTED verdict, is
    covered by no identity proposal, and never materializes — and ordinary
    Buddy edges publish through the explicit predicate mapping, both
    direct-mapped (``located_in`` → ``dnd5e:located_in``) and reverse-mapped
    (``belongs_to`` → ``dnd5e:owns`` with swapped endpoints). The hydrated
    Buddy read model recovers the original edge orientation and predicate."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)

    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    slug = "session-26-cutover-partition"
    artifact_id = f"artifact:recap:longmont-c2:{slug}"
    package, accepted_ids = _seal_tinker_package(
        handle.cache_world_root,
        write_world["tmp_path"],
        preview_slug=slug,
        node_id="node:cutover-edge-a",
        label="Edge Anchor",
        extra_nodes=[
            _preview_node(
                artifact_id,
                node_id="node:cutover-edge-b",
                label="Edge Target",
                node_type="location",
                span="session-26:recap:paragraph:002",
            ),
            _preview_node(
                artifact_id,
                node_id="node:cutover-edge-c",
                label="Edge Owner",
                node_type="faction",
                span="session-26:recap:paragraph:003",
            ),
            # Cross-kind label collision with the existing location:mireward:
            # the identity gate rejects this node (blocked_collision).
            _preview_node(
                artifact_id,
                node_id="node:cutover-mireward-clash",
                label="Mireward",
                node_type="npc",
                span="session-26:recap:paragraph:004",
            ),
        ],
        edges=[
            _preview_edge(
                artifact_id,
                edge_id="edge:cutover-a-located-in-b",
                from_node_id="node:cutover-edge-a",
                to_node_id="node:cutover-edge-b",
                predicate="located_in",
                span="session-26:recap:paragraph:005",
            ),
            _preview_edge(
                artifact_id,
                edge_id="edge:cutover-b-belongs-to-c",
                from_node_id="node:cutover-edge-b",
                to_node_id="node:cutover-edge-c",
                predicate="belongs_to",
                span="session-26:recap:paragraph:006",
            ),
        ],
    )
    # The gate produced both partitions: 5 accepted (3 nodes + 2 edges) and
    # exactly 1 rejected (the colliding node).
    assert len(accepted_ids) == 5

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

    # The durable review record preserves the GM's partition exactly.
    operation_id = wga._derive_confirm_operation_id(
        world_id=WORLD_ID, package=package, assertion_ids=None
    )
    publication = bundle.finalized_review_publications.get(WORLD_ID, operation_id)
    assert publication is not None
    review_state = bundle.contribution_reviews.get(WORLD_ID, publication.review_id)
    assert review_state is not None
    verdict_by_id = {
        verdict.assertion_id: str(verdict.acceptance_state)
        for verdict in review_state.record.assertion_verdicts
    }
    reviewed_by_id = {
        assertion.assertion_id: assertion
        for assertion in review_state.reviewed_contribution.assertions
    }
    assert set(verdict_by_id) == set(reviewed_by_id)
    rejected_ids = {
        assertion_id
        for assertion_id, assertion in reviewed_by_id.items()
        if assertion.subject_object_id == "node:cutover-mireward-clash"
    }
    assert len(rejected_ids) == 1
    for assertion_id in accepted_ids:
        assert verdict_by_id[assertion_id] == "accepted"
        assert str(reviewed_by_id[assertion_id].acceptance_state) == "accepted"
    for assertion_id in rejected_ids:
        assert verdict_by_id[assertion_id] == "rejected"
        assert str(reviewed_by_id[assertion_id].acceptance_state) == "rejected"

    # Accepted edges: the Buddy session hint is normalized away in the
    # durable review record (DungeonMind expresses real-world session
    # provenance as session refs); the value's session_ids carry that
    # provenance into materialization. Rejected assertions are preserved
    # exactly as the sealed package adjudicated them.
    import json as _json

    package_temporal_by_id = {
        str(item["assertion_id"]): item.get("temporal_scope") or None
        for item in package["effect"]["rejected_assertions"]
    }
    for assertion_id in accepted_ids:
        reviewed = reviewed_by_id[assertion_id]
        assert reviewed.temporal_scope is None
        if reviewed.assertion_kind == "edge":
            assert _json.loads(reviewed.value)["session_ids"] == ["session-26"]
    for assertion_id in rejected_ids:
        assert (
            reviewed_by_id[assertion_id].temporal_scope
            == package_temporal_by_id[assertion_id]
        )

    # Identity proposals cover exactly the accepted node/alias targets — the
    # rejected node's target demands no adjudication.
    proposal_targets = {
        proposal.target_object_id for proposal in review_state.record.identity_proposals
    }
    assert proposal_targets == {
        "node:cutover-edge-a",
        "node:cutover-edge-b",
        "node:cutover-edge-c",
    }

    # The published DungeonMind graph: accepted nodes and both edges
    # materialized with qualified predicates; the rejected node is absent.
    stored = bundle.world_graph.get_revision(WORLD_ID, d_b)
    assert stored is not None
    object_ids = {
        obj.get("object_id") for obj in stored.graph_payload.get("objects") or []
    }
    assert {
        "node:cutover-edge-a",
        "node:cutover-edge-b",
        "node:cutover-edge-c",
    } <= object_ids
    assert "node:cutover-mireward-clash" not in object_ids
    relationships = {
        rel.get("relationship_id"): rel
        for rel in stored.graph_payload.get("relationships") or []
    }
    direct = relationships["edge:node:cutover-edge-a:located_in:node:cutover-edge-b"]
    assert direct["predicate"] == "dnd5e:located_in"
    assert direct["source_object_id"] == "node:cutover-edge-a"
    assert direct["target_object_id"] == "node:cutover-edge-b"
    reverse = relationships["edge:node:cutover-edge-b:belongs_to:node:cutover-edge-c"]
    assert reverse["predicate"] == "dnd5e:owns"
    # Reverse-mapped: the materialized direction follows dnd5e:owns semantics
    # (the faction owns the location — an admitted owns endpoint pair).
    assert reverse["source_object_id"] == "node:cutover-edge-c"
    assert reverse["target_object_id"] == "node:cutover-edge-b"

    # The hydrated Buddy read model recovers the original Buddy edge
    # orientation and predicate (the inverse translation un-swaps and strips
    # the derived dm_predicate), and the rejected node stays absent.
    storage.clear_world_graph_cache_roots()
    handle_b = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    assert handle_b.selected_revision_id == d_b
    from graph_memory.world_supergraph.storage import load_world_graph_revision

    store_b = load_world_graph_revision(
        handle_b.cache_world_root, WORLD_ID, handle_b.buddy_revision_id
    )
    assert "node:cutover-mireward-clash" not in store_b.nodes
    buddy_direct = store_b.edges[
        "edge:node:cutover-edge-a:located_in:node:cutover-edge-b"
    ]
    assert buddy_direct.predicate == "located_in"
    assert buddy_direct.source_node_id == "node:cutover-edge-a"
    assert buddy_direct.target_node_id == "node:cutover-edge-b"
    buddy_reverse = store_b.edges[
        "edge:node:cutover-edge-b:belongs_to:node:cutover-edge-c"
    ]
    assert buddy_reverse.predicate == "belongs_to"
    assert buddy_reverse.source_node_id == "node:cutover-edge-b"
    assert buddy_reverse.target_node_id == "node:cutover-edge-c"

    assert _tree_digest(frozen_root) == frozen_digest_before


@pytest.mark.integration
def test_governed_write_unmapped_edge_predicate_fails_closed(write_world):
    """§3 repair: an accepted edge whose Buddy predicate has no explicit
    DungeonMind mapping fails closed (``governed_write_inexpressible``) with
    zero mutation — no head advance, no new revision, no review rows, and the
    frozen Buddy store untouched. No predicate mapping is ever invented."""
    import psycopg

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)
    revisions_before = _graph_revision_ids(dsn)

    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    slug = "session-26-cutover-unmapped"
    artifact_id = f"artifact:recap:longmont-c2:{slug}"
    package, accepted_ids = _seal_tinker_package(
        handle.cache_world_root,
        write_world["tmp_path"],
        preview_slug=slug,
        node_id="node:cutover-unmapped-a",
        label="Unmapped Anchor",
        extra_nodes=[
            _preview_node(
                artifact_id,
                node_id="node:cutover-unmapped-b",
                label="Unmapped Target",
                node_type="location",
                span="session-26:recap:paragraph:002",
            ),
        ],
        edges=[
            _preview_edge(
                artifact_id,
                edge_id="edge:cutover-unmapped-same-as",
                from_node_id="node:cutover-unmapped-a",
                to_node_id="node:cutover-unmapped-b",
                predicate="same_as",  # intentionally unresolved predicate
                span="session-26:recap:paragraph:003",
            ),
        ],
    )
    assert len(accepted_ids) == 3

    class _Request:
        review_package = package
        assertion_ids = None

    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.confirm_via_dungeonmind(
            _Request(),
            world_root=frozen_root,
            database_url=dsn,
            cache_root=cache_root,
            frozen_root=frozen_root,
            confirming_principal="gm@confirm",
            assertion_ids=None,
            repo_root=write_world["tmp_path"],
        )
    assert excinfo.value.code == "governed_write_inexpressible"

    # Zero mutation: head, revisions, reviews, and the frozen store unchanged.
    head = write_world["bundle"].world_graph.get_head(WORLD_ID)
    assert head is not None and head.head_revision_id == d_a
    assert _graph_revision_ids(dsn) == revisions_before
    with psycopg.connect(dsn) as conn:
        review_rows = conn.execute(
            "SELECT count(*) FROM dungeonmind.contribution_reviews"
        ).fetchone()[0]
        publication_rows = conn.execute(
            "SELECT count(*) FROM dungeonmind.finalized_review_publications"
        ).fetchone()[0]
    assert review_rows == 0
    assert publication_rows == 0
    assert _tree_digest(frozen_root) == frozen_digest_before


@pytest.mark.integration
def test_governed_write_endpoint_admission_fails_closed(write_world):
    """§3 repair: an accepted edge whose Buddy predicate has an explicit
    DungeonMind mapping but whose concrete endpoint kinds are not admitted for
    the qualified predicate fails closed (``governed_write_inexpressible``)
    with zero mutation. world-object-v5 defines ``dnd5e:leads_to`` as
    Location→Location; an NPC→Location ``leads_to`` edge must never become
    authoritative. The name mapping alone is not admission."""
    import psycopg

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)
    revisions_before = _graph_revision_ids(dsn)

    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    slug = "session-26-cutover-admission"
    artifact_id = f"artifact:recap:longmont-c2:{slug}"
    package, accepted_ids = _seal_tinker_package(
        handle.cache_world_root,
        write_world["tmp_path"],
        preview_slug=slug,
        node_id="node:cutover-admit-a",
        label="Admission Anchor",
        extra_nodes=[
            _preview_node(
                artifact_id,
                node_id="node:cutover-admit-b",
                label="Admission Target",
                node_type="location",
                span="session-26:recap:paragraph:002",
            ),
        ],
        edges=[
            _preview_edge(
                artifact_id,
                edge_id="edge:cutover-admit-leads-to",
                from_node_id="node:cutover-admit-a",  # npc — not a Location
                to_node_id="node:cutover-admit-b",
                predicate="leads_to",
                span="session-26:recap:paragraph:003",
            ),
        ],
    )
    # Buddy's identity gate admits the edge; DungeonMind endpoint admission is
    # the writer's governed responsibility.
    assert len(accepted_ids) == 3

    class _Request:
        review_package = package
        assertion_ids = None

    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.confirm_via_dungeonmind(
            _Request(),
            world_root=frozen_root,
            database_url=dsn,
            cache_root=cache_root,
            frozen_root=frozen_root,
            confirming_principal="gm@confirm",
            assertion_ids=None,
            repo_root=write_world["tmp_path"],
        )
    assert excinfo.value.code == "governed_write_inexpressible"
    assert excinfo.value.details.get("reason") == "endpoint_kind_not_admitted"

    # Zero mutation: head, revisions, reviews, and the frozen store unchanged.
    head = write_world["bundle"].world_graph.get_head(WORLD_ID)
    assert head is not None and head.head_revision_id == d_a
    assert _graph_revision_ids(dsn) == revisions_before
    with psycopg.connect(dsn) as conn:
        review_rows = conn.execute(
            "SELECT count(*) FROM dungeonmind.contribution_reviews"
        ).fetchone()[0]
        publication_rows = conn.execute(
            "SELECT count(*) FROM dungeonmind.finalized_review_publications"
        ).fetchone()[0]
    assert review_rows == 0
    assert publication_rows == 0
    assert _tree_digest(frozen_root) == frozen_digest_before


@pytest.mark.integration
def test_governed_write_reverse_direction_fails_closed(write_world):
    """§3 repair: an accepted edge whose concrete endpoint kinds ARE admitted
    for the qualified predicate but whose edge id carries a reverse-direction
    qualifier (``is-threatened-by``) fails closed with zero mutation. The
    conformance contract rejects reverse-looking edge ids before automatic
    translation because a valid endpoint pair can otherwise be published with
    inverted semantics; the writer applies the same audit to accepted writes.
    ``dnd5e:threatens`` admits NPC→Location, so endpoint admission alone
    would let this through."""
    import psycopg

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)
    revisions_before = _graph_revision_ids(dsn)

    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    slug = "session-26-cutover-direction"
    artifact_id = f"artifact:recap:longmont-c2:{slug}"
    package, accepted_ids = _seal_tinker_package(
        handle.cache_world_root,
        write_world["tmp_path"],
        preview_slug=slug,
        node_id="node:cutover-direction-a",
        label="Direction Anchor",
        extra_nodes=[
            _preview_node(
                artifact_id,
                # The canonicalized value edge id inherits this target id, so
                # the stored edge id reads …threatens…is-threatened-by… — a
                # reverse-looking id for the threatens predicate.
                node_id="node:is-threatened-by-mireward",
                label="Direction Target",
                node_type="location",
                span="session-26:recap:paragraph:002",
            ),
        ],
        edges=[
            _preview_edge(
                artifact_id,
                edge_id="edge:cutover-direction-threatens",
                from_node_id="node:cutover-direction-a",  # npc
                to_node_id="node:is-threatened-by-mireward",  # location
                predicate="threatens",
                span="session-26:recap:paragraph:003",
            ),
        ],
    )
    # Buddy's identity gate admits the edge (2 nodes + 1 edge); the direction
    # audit is the writer's governed responsibility.
    assert len(accepted_ids) == 3

    class _Request:
        review_package = package
        assertion_ids = None

    with pytest.raises(wga.WorldGraphAuthorityError) as excinfo:
        wga.confirm_via_dungeonmind(
            _Request(),
            world_root=frozen_root,
            database_url=dsn,
            cache_root=cache_root,
            frozen_root=frozen_root,
            confirming_principal="gm@confirm",
            assertion_ids=None,
            repo_root=write_world["tmp_path"],
        )
    assert excinfo.value.code == "governed_write_inexpressible"
    assert excinfo.value.details.get("reason") == "reverse_direction_qualifier"

    # Zero mutation: head, revisions, reviews, and the frozen store unchanged.
    head = write_world["bundle"].world_graph.get_head(WORLD_ID)
    assert head is not None and head.head_revision_id == d_a
    assert _graph_revision_ids(dsn) == revisions_before
    with psycopg.connect(dsn) as conn:
        review_rows = conn.execute(
            "SELECT count(*) FROM dungeonmind.contribution_reviews"
        ).fetchone()[0]
        publication_rows = conn.execute(
            "SELECT count(*) FROM dungeonmind.finalized_review_publications"
        ).fetchone()[0]
    assert review_rows == 0
    assert publication_rows == 0
    assert _tree_digest(frozen_root) == frozen_digest_before


@pytest.mark.integration
def test_governed_write_rejected_unmapped_kind_does_not_veto(write_world):
    """§3 repair: a rejected assertion is preserved in the durable review
    record without DungeonMind qualification, so a rejected node whose Buddy
    kind has no DungeonMind mapping (``job``) cannot veto the publication of
    the accepted assertions alongside it. The v6 materializer skips rejected
    assertions; the writer must not demand their materializability."""
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    bundle = write_world["bundle"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    d_a = write_world["receipt"].published_revision_id
    frozen_digest_before = _tree_digest(frozen_root)

    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    slug = "session-26-cutover-rejected-veto"
    artifact_id = f"artifact:recap:longmont-c2:{slug}"
    package, accepted_ids = _seal_tinker_package(
        handle.cache_world_root,
        write_world["tmp_path"],
        preview_slug=slug,
        node_id="node:cutover-veto-a",
        label="Veto Anchor",
        extra_nodes=[
            # Cross-kind label collision with the existing location:mireward:
            # the identity gate rejects this node (blocked_collision). Its
            # Buddy kind "job" has no world-object-v5 mapping — before the
            # repair, qualifying it vetoed the whole confirmation.
            _preview_node(
                artifact_id,
                node_id="node:cutover-mireward-job",
                label="Mireward",
                node_type="quest",
                span="session-26:recap:paragraph:002",
            ),
        ],
    )
    assert len(accepted_ids) == 1

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

    # The durable review record preserves the rejected assertion with a
    # REJECTED verdict; the accepted node is ACCEPTED.
    operation_id = wga._derive_confirm_operation_id(
        world_id=WORLD_ID, package=package, assertion_ids=None
    )
    publication = bundle.finalized_review_publications.get(WORLD_ID, operation_id)
    assert publication is not None
    review_state = bundle.contribution_reviews.get(WORLD_ID, publication.review_id)
    assert review_state is not None
    verdict_by_id = {
        verdict.assertion_id: str(verdict.acceptance_state)
        for verdict in review_state.record.assertion_verdicts
    }
    reviewed_by_id = {
        assertion.assertion_id: assertion
        for assertion in review_state.reviewed_contribution.assertions
    }
    assert set(verdict_by_id) == set(reviewed_by_id)
    rejected_ids = {
        assertion_id
        for assertion_id, assertion in reviewed_by_id.items()
        if assertion.subject_object_id == "node:cutover-mireward-job"
    }
    assert len(rejected_ids) == 1
    for assertion_id in accepted_ids:
        assert verdict_by_id[assertion_id] == "accepted"
    for assertion_id in rejected_ids:
        assert verdict_by_id[assertion_id] == "rejected"

    # Temporal normalization is accept-only: the accepted assertion's Buddy
    # session hint is normalized away (DungeonMind expresses real-world
    # session provenance as session refs at materialization), while every
    # rejected assertion is preserved in the durable review record exactly as
    # the sealed package adjudicated it — the writer never rewrites rejected
    # material that never materializes. (Today's gate emits only rejected
    # nodes, which carry no session hint; the rejected-edge-with-hint shape
    # is proven directly at the writer seam in
    # test_build_v2_candidate_temporal_normalization_is_accept_only.)
    package_rejected_temporal = {
        str(item["assertion_id"]): item.get("temporal_scope") or None
        for item in package["effect"]["rejected_assertions"]
    }
    for assertion_id in accepted_ids:
        assert reviewed_by_id[assertion_id].temporal_scope is None
    for assertion_id in rejected_ids:
        assert (
            reviewed_by_id[assertion_id].temporal_scope
            == package_rejected_temporal[assertion_id]
        )

    # The published graph carries the accepted node; the rejected unmapped
    # node never materializes.
    stored = bundle.world_graph.get_revision(WORLD_ID, d_b)
    assert stored is not None
    object_ids = {
        obj.get("object_id") for obj in stored.graph_payload.get("objects") or []
    }
    assert "node:cutover-veto-a" in object_ids
    assert "node:cutover-mireward-job" not in object_ids

    assert _tree_digest(frozen_root) == frozen_digest_before


@pytest.mark.integration
def test_hermes_latest_recap_compares_dungeonmind_head_not_frozen_store(
    write_world, monkeypatch
):
    """§3 repair: the Hermes latest-recap branch routes its comparison root
    through the World Graph authority. After D_B publishes session-26 state,
    the comparison reads the DungeonMind-backed hydration (latest session
    session-26) and labels it with the DungeonMind revision — it never
    compares the frozen Buddy store (latest session session-25) while
    labeling it with the DungeonMind revision."""
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextRequest,
    )
    from apps.live_control_server.services.recap_artifacts import (
        RecapArtifactRecord,
    )
    from graph_memory.interaction import latest_recap as latest_recap_module
    from graph_memory.world_supergraph.storage import load_world_graph_revision

    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )

    dsn = write_world["dsn"]
    frozen_root = write_world["frozen_root"]
    cache_root = write_world["cache_root"]
    tmp_path = write_world["tmp_path"]

    # Setup invariant: the frozen store's latest session predates session-26,
    # so a frozen read would report memory_lag for a session-26 recap.
    frozen_store = load_world_graph_revision(
        frozen_root, WORLD_ID, FROZEN_HEAD_REVISION
    )
    frozen_sessions = latest_recap_module._graph_session_ids(
        frozen_store.model_dump(mode="json", by_alias=True), CAMPAIGN_ID
    )
    assert frozen_sessions and frozen_sessions[-1] == "session-25"

    # Publish D_B through the real confirm path: a node plus an edge whose
    # value carries session-26 observation provenance.
    handle = wga.ensure_hydrated_authority(
        WORLD_ID, database_url=dsn, cache_root=cache_root, frozen_root=frozen_root
    )
    slug = "session-26-cutover-recap-route"
    artifact_id = f"artifact:recap:longmont-c2:{slug}"
    package, _accepted = _seal_tinker_package(
        handle.cache_world_root,
        tmp_path,
        preview_slug=slug,
        node_id="node:cutover-recap-a",
        label="Recap Anchor",
        extra_nodes=[
            _preview_node(
                artifact_id,
                node_id="node:cutover-recap-b",
                label="Recap Target",
                node_type="location",
                span="session-26:recap:paragraph:002",
            ),
        ],
        edges=[
            _preview_edge(
                artifact_id,
                edge_id="edge:recap-a-located-in-b",
                from_node_id="node:cutover-recap-a",
                to_node_id="node:cutover-recap-b",
                predicate="located_in",
                span="session-26:recap:paragraph:003",
            ),
        ],
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
        repo_root=tmp_path,
    )
    assert payload["outcome"] == "published"
    d_b = payload["committed_revision_id"]

    # The admitted recap registry names session-26; its source file exists.
    (tmp_path / "Session 26 - Recap.md").write_text(
        "The Recap Anchor holds the Recap Target.\n", encoding="utf-8"
    )
    record = RecapArtifactRecord(
        artifact_id="longmont-c2/session-26",
        campaign_id=CAMPAIGN_ID,
        session_id="session-26",
        source_recap_path="Session 26 - Recap.md",
        run_bundle_uri="runs/session-26/bundle.json",
        run_manifest_uri="runs/session-26/manifest.json",
        source_span_index_uri="runs/session-26/spans.json",
        registered_at="2026-08-18T00:00:00Z",
        updated_at="2026-08-18T00:00:00Z",
    )
    monkeypatch.setattr(
        latest_recap_module,
        "list_recap_artifact_records",
        lambda root, campaign_id: [record],
    )

    captured: dict = {}

    def _fake_run_hermes_graph_query(*, graph_envelope, **_kwargs):
        captured["graph_envelope"] = graph_envelope
        return {"answer": "ok", "grounding": {"state": "grounded"}}

    monkeypatch.setattr(
        live_agent_loop, "run_hermes_graph_query", _fake_run_hermes_graph_query
    )
    monkeypatch.setattr(
        live_agent_loop,
        "load_session",
        lambda base: ({"campaign_id": CAMPAIGN_ID, "session": 26}, {}, [], []),
    )
    envelope = {
        "world_id": WORLD_ID,
        "campaign_id": CAMPAIGN_ID,
        "revision_id": d_b,
        "status": "ready",
        "matched_node_ids": [],
        "nodes": [],
    }
    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: dict(envelope),
    )

    live_agent_loop.process_live_query(
        "What changed after the latest ingested recap?",
        base=tmp_path / "live-session",
        root=tmp_path,
        query_backend="hermes",
        world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(
            {
                "schema": "dmb_agent_world_graph_query_context_request_v1",
                "world_id": WORLD_ID,
                "campaign_id": CAMPAIGN_ID,
                "focus": {"kind": "none", "session_id": None},
                "admissibility": "gm",
            }
        ),
        outer_campaign_id=CAMPAIGN_ID,
    )

    change = captured["graph_envelope"]["latest_recap_change"]
    assert change["comparison_boundary"]["graph_revision_id"] == d_b
    # The comparison read the DungeonMind-backed D_B hydration: session-26 is
    # present, so the graph is caught up with the session-26 recap. A frozen
    # Store-A read would have reported memory_lag at session-25 instead.
    assert change["comparison_boundary"]["graph_latest_session_id"] == "session-26"
    assert change["outcome"] == "no_change"
    assert change["memory_lag"] is False
