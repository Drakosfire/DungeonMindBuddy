"""CUTOVER R.3: direct DungeonMind World Graph read path tests.

Two layers, mirroring the cutover authority test module:

- **Unit layer (portable)** — no PostgreSQL, no frozen Buddy store. A
  synthetic ``dm_union_graph_v6`` world is published into DungeonMind's
  in-memory repositories; the direct adapter and the service dispatch are
  exercised against it. Explosion stubs prove the direct path never invokes
  the legacy Buddy graph kernel or the hydration adapter.
- **Integration layer (env-gated)** — requires
  ``DMB_CUTOVER_TEST_DATABASE_URL`` pointing at the live cutover database for
  the real-current parity witness (see
  ``scripts/compare_direct_dungeonmind_world_graph_reads.py``); not needed
  here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.services import world_graph_projection as projection_service
from apps.live_control_server.services import world_graph_retrieval as retrieval_service
from apps.live_control_server.services import world_graph_prewarm as prewarm_service
from apps.live_control_server.services import world_graph_projection_recipes as recipes_service
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
from graph_memory.retrieval.models import (
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
)
from graph_memory.world_supergraph import storage

from dungeonmind.contracts.evidence import (
    SourceArtifactV2,
    SourceDomain,
    SourceRevision,
    SourceStatus,
)
from dungeonmind.contracts.existing_world_adoption import (
    ExistingWorldAdoptionReceiptV3,
    ExistingWorldAdoptionSourceProvenanceV1,
)
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.contracts.vocabulary import Visibility
from dungeonmind.infrastructure.memory import (
    InMemorySourceRepository,
    InMemoryWorldGraphRepository,
)

WORLD_ID = "world:r3-direct-test"
CAMPAIGN_ONE = "camp:one"
NOW = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
LEGACY_BUDDY_A_REVISION = "rev:buddy-adopted-head"
DUMMY_DIGEST = hashlib.sha256(b"r3-direct-test").hexdigest()

# Anchor round-trip fixture: the world-lore revision's content digest matches
# ANCHOR_CONTENT so the digest-verified product-local read succeeds.
ANCHOR_CONTENT = "# Tavern\n\nThe Prancing Tavern at the crossroads.\n"
ANCHOR_CONTENT_DIGEST = hashlib.sha256(ANCHOR_CONTENT.encode("utf-8")).hexdigest()

PROJECTION_REQUEST_SCHEMA = "dmb_world_graph_projection_request_v1"


# ---------------------------------------------------------------------------
# Synthetic v6 world fixture (in-memory DungeonMind repositories)
# ---------------------------------------------------------------------------


def _meta(
    assertion_id: str,
    *,
    evidence: tuple[str, ...],
    visibility: str = "gm",
    campaign_scope: str | None = None,
) -> dict:
    return {
        "schema_version": "dm_knowledge_assertion_metadata_v1",
        "assertion_id": assertion_id,
        "campaign_scope": campaign_scope,
        "visibility": visibility,
        "epistemic_kind": "fact",
        "canon_state": "canonical",
        "evidence_ref_ids": list(evidence),
        "session_refs": [],
        "temporal_scope": {"schema_version": "dm_temporal_scope_ref_v1", "kind": "unknown"},
    }


def _evidence_row(
    evidence_ref_id: str,
    artifact_id: str,
    revision_id: str,
    *,
    session_id: str | None = None,
    locator: str | None = None,
) -> dict:
    return {
        "schema_version": "dm_evidence_ref_v2",
        "evidence_ref_id": evidence_ref_id,
        "source_artifact_id": artifact_id,
        "source_revision_id": revision_id,
        "source_domain_key": "buddy.worldbuilding",
        "source_domain": "worldbuilding",
        "evidence_role": "support",
        "can_open_source": True,
        "can_highlight_span": False,
        "session_id": session_id,
        "source_span_ref_id": None,
        "locator": locator,
        "uri": None,
        "source_locator": None,
        "line_ref": None,
    }


def _payload() -> dict:
    objects = [
        {
            "object_id": "obj:tavern",
            "kind": "dnd5e:location",
            "label": "The Prancing Tavern",
            "assertion_metadata": _meta("asrt:obj:tavern", evidence=("ev:tavern",)),
            "aliases": [],
            "summary": None,
            "properties": [],
            "aspects": [],
        },
        {
            "object_id": "obj:hidden-cellar",
            "kind": "dnd5e:location",
            "label": "Hidden Cellar",
            "assertion_metadata": _meta("asrt:obj:cellar", evidence=("ev:cellar",)),
            "aliases": [],
            "summary": None,
            "properties": [],
            "aspects": [],
        },
        {
            "object_id": "obj:hero",
            "kind": "dnd5e:npc",
            "label": "Retired Hero",
            "assertion_metadata": _meta(
                "asrt:obj:hero", evidence=("ev:hero",), campaign_scope=CAMPAIGN_ONE
            ),
            "aliases": [],
            "summary": None,
            "properties": [],
            "aspects": [],
        },
        {
            "object_id": "obj:road-sign",
            "kind": "dnd5e:location",
            "label": "Crossroads Sign",
            "assertion_metadata": _meta(
                "asrt:obj:sign", evidence=("ev:sign",), visibility="player"
            ),
            "aliases": [],
            "summary": None,
            "properties": [],
            "aspects": [],
        },
    ]
    relationships = [
        {
            "relationship_id": "rel:tavern-cellar",
            "source_object_id": "obj:tavern",
            "target_object_id": "obj:hidden-cellar",
            "predicate": "dnd5e:contains",
            "assertion_metadata": _meta("asrt:rel:cellar", evidence=("ev:cellar",)),
        },
        {
            "relationship_id": "rel:hero-tavern",
            "source_object_id": "obj:hero",
            "target_object_id": "obj:tavern",
            "predicate": "dnd5e:located_in",
            "assertion_metadata": _meta(
                "asrt:rel:hero", evidence=("ev:hero",), campaign_scope=CAMPAIGN_ONE
            ),
        },
    ]
    evidence = [
        _evidence_row("ev:tavern", "src:one-recap", "srcrev:one-recap-v1",
                      session_id="session-9", locator="heading:Tavern"),
        _evidence_row("ev:cellar", "src:world-lore", "srcrev:world-lore-v1"),
        _evidence_row("ev:hero", "src:one-notes", "srcrev:one-notes-v1",
                      session_id="session-3"),
        _evidence_row("ev:sign", "src:player-sign", "srcrev:player-sign-v1"),
    ]
    return {
        "world_id": WORLD_ID,
        "semantic_profile": _profile_ref(),
        "relationship_endpoint_aspect_schema": "dm_relationship_endpoint_aspect_v1",
        "objects": objects,
        "relationships": relationships,
        "evidence_refs": evidence,
    }


def _profile_ref() -> dict:
    from dungeonmind.application.semantic_profiles import descriptor_sha256
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    descriptor = load_builtin_v3_descriptor()
    return {
        "schema_version": "dm_semantic_profile_ref_v1",
        "profile_id": descriptor.profile_id,
        "profile_revision": descriptor.profile_revision,
        "descriptor_sha256": descriptor_sha256(descriptor),
    }


class _FakeAdoptionRepository:
    def __init__(
        self,
        receipt: ExistingWorldAdoptionReceiptV3 | None,
        *,
        error: BaseException | None = None,
    ) -> None:
        self._receipt = receipt
        self._error = error

    def get_for_world(self, world_id: str):
        if self._error is not None:
            raise self._error
        if self._receipt is not None and self._receipt.world_id == world_id:
            return self._receipt
        return None


class _FakeReviewedInitReceipt:
    def __init__(self, world_id: str, published_revision_id: str) -> None:
        self.world_id = world_id
        self.published_revision_id = published_revision_id


class _FakeReviewedInitRepository:
    def __init__(
        self,
        receipt: _FakeReviewedInitReceipt | None,
        *,
        error: BaseException | None = None,
    ) -> None:
        self._receipt = receipt
        self._error = error

    def get_for_world(self, world_id: str):
        if self._error is not None:
            raise self._error
        if self._receipt is not None and self._receipt.world_id == world_id:
            return self._receipt
        return None


class _FakeBundle:
    """Duck-typed repository bundle: real in-memory repos + genesis fakes."""

    def __init__(
        self,
        world_graph: InMemoryWorldGraphRepository,
        sources: InMemorySourceRepository,
        receipt: ExistingWorldAdoptionReceiptV3 | None,
        init_receipt: _FakeReviewedInitReceipt | None = None,
        *,
        adoption_error: BaseException | None = None,
        init_error: BaseException | None = None,
    ) -> None:
        self.world_graph = world_graph
        self.sources = sources
        self.existing_world_adoptions = _FakeAdoptionRepository(
            receipt, error=adoption_error
        )
        self.reviewed_world_initializations = _FakeReviewedInitRepository(
            init_receipt, error=init_error
        )


def _seed_sources() -> InMemorySourceRepository:
    sources = InMemorySourceRepository()
    for artifact_id, revision_id, campaign_id, uri, digest, visibility in (
        ("src:world-lore", "srcrev:world-lore-v1", None, None, DUMMY_DIGEST, Visibility.GM),
        ("src:one-notes", "srcrev:one-notes-v1", CAMPAIGN_ONE, None, DUMMY_DIGEST, Visibility.GM),
        ("src:one-recap", "srcrev:one-recap-v1", CAMPAIGN_ONE,
         "repo://corpus/world_lore.md", ANCHOR_CONTENT_DIGEST, Visibility.GM),
        ("src:player-sign", "srcrev:player-sign-v1", None, None, DUMMY_DIGEST, Visibility.PLAYER),
    ):
        sources.put_artifact(
            SourceArtifactV2(
                source_artifact_id=artifact_id,
                source_domain_key="buddy.worldbuilding",
                source_domain=SourceDomain.WORLDBUILDING,
                world_id=WORLD_ID,
                campaign_id=campaign_id,
                session_id=None,
                uri=uri,
                current_revision_id=revision_id,
                authority=None,
                visibility=visibility,
                artifact_kind=None,
                document_class=None,
                review_state=None,
                source_visibility_state=None,
                workspace_document_ref=None,
                lineage={},
                status=SourceStatus.ACTIVE,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        sources.put_revision(
            SourceRevision(
                source_revision_id=revision_id,
                source_artifact_id=artifact_id,
                content_sha256=digest,
                body_storage="external",
                locator=f"test://{artifact_id}",
                created_at=NOW,
            )
        )
    return sources


def _receipt(world_id: str, published_revision_id: str) -> ExistingWorldAdoptionReceiptV3:
    return ExistingWorldAdoptionReceiptV3(
        adoption_id="adopt:r3-direct-test",
        world_id=world_id,
        bundle_sha256=DUMMY_DIGEST,
        source_provenance=ExistingWorldAdoptionSourceProvenanceV1(
            producer_id="dungeonmindbuddy",
            producer_revision="r3-test",
            source_world_revision_id=LEGACY_BUDDY_A_REVISION,
            source_graph_payload_sha256=DUMMY_DIGEST,
        ),
        published_revision_id=published_revision_id,
        graph_schema="dm_union_graph_v6",
        graph_payload_sha256=DUMMY_DIGEST,
        adopted_at=NOW,
        source_artifact_count=4,
        source_revision_count=4,
        contribution_count=0,
        identity_decision_count=0,
        membership_sha256=DUMMY_DIGEST,
    )


@pytest.fixture()
def services():
    """Direct read services over the synthetic in-memory world."""
    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:r3-test"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        _receipt(WORLD_ID, published.revision_id),
    )
    return direct.direct_services_from_bundle(bundle, WORLD_ID), published.revision_id


def _projection_request(**overrides) -> WorldGraphProjectionRequest:
    fields = {
        "schema": PROJECTION_REQUEST_SCHEMA,
        "world_id": WORLD_ID,
        "campaign_id": CAMPAIGN_ONE,
        "admissibility": "gm",
        "scope_mode": "campaign",
    }
    fields.update(overrides)
    return WorldGraphProjectionRequest(**fields)


def _retrieval_context(**overrides) -> dict:
    fields = {
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ONE,
        "admissibility": "gm",
        "scopeMode": "campaign",
    }
    fields.update(overrides)
    return fields


# ---------------------------------------------------------------------------
# Adapter: projection mapping and response adaptation
# ---------------------------------------------------------------------------


def test_direct_projection_admits_expected_objects(services):
    svc, head_revision = services
    projection = direct.project_world_graph_direct(svc, _projection_request())
    node_ids = {node.node_id for node in projection.nodes}
    # World-owned + campaign-one objects admitted under the campaign lens.
    assert node_ids == {"obj:tavern", "obj:hidden-cellar", "obj:hero", "obj:road-sign"}
    assert projection.snapshot.revision_id == head_revision
    assert projection.snapshot.head_revision_id == head_revision
    assert projection.snapshot.is_head is True
    assert projection.snapshot.scope_mode == "campaign"
    assert projection.snapshot.admissibility == "gm"


def test_direct_projection_strips_dnd_vocabulary_prefix(services):
    svc, _ = services
    projection = direct.project_world_graph_direct(svc, _projection_request())
    kinds = {node.kind for node in projection.nodes}
    roles = {node.role for node in projection.nodes}
    predicates = {rel.predicate for rel in projection.relationships}
    assert kinds == {"location", "npc"}
    assert roles == {"location", "npc"}
    assert predicates == {"contains", "located_in"}


def test_direct_projection_world_scope_is_cross_campaign(services):
    svc, _ = services
    projection = direct.project_world_graph_direct(
        svc, _projection_request(scope_mode="world")
    )
    assert projection.snapshot.scope_mode == "world"
    assert {node.node_id for node in projection.nodes} == {
        "obj:tavern",
        "obj:hidden-cellar",
        "obj:hero",
        "obj:road-sign",
    }


def test_direct_projection_maps_player_admissibility(services):
    """R.3: PLAYER maps through the closed DND GM/PLAYER vocabulary.

    DungeonMind's fail-closed visibility gate hides GM-only material; the
    adapter must not reject PLAYER outright. Player-visible objects are served.
    """
    svc, _ = services
    projection = direct.project_world_graph_direct(
        svc, _projection_request(admissibility="player")
    )
    assert {node.node_id for node in projection.nodes} == {"obj:road-sign"}
    assert projection.snapshot.admissibility == "player"


def test_direct_projection_rejects_unknown_admissibility(services):
    """Unknown admissibility values fail closed."""
    svc, _ = services
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.project_world_graph_direct(svc, _projection_request(admissibility="unknown"))
    assert excinfo.value.code == "unsupported_admissibility"
    assert excinfo.value.status_code == 422


def test_direct_projection_cross_campaign_player_hides_gm_only(services):
    """R.3: cross-campaign PLAYER still does not leak GM-only rows.

    The handoff requires that PLAYER under the cross-campaign world lens
    does not expose GM-only material. The player-visible road sign is served;
    GM-only tavern/cellar/hero remain hidden.
    """
    svc, _ = services
    projection = direct.project_world_graph_direct(
        svc, _projection_request(admissibility="player", scope_mode="world")
    )
    assert {node.node_id for node in projection.nodes} == {"obj:road-sign"}
    assert projection.snapshot.admissibility == "player"
    assert projection.snapshot.scope_mode == "world"


def test_revision_pin_bridge_legacy_to_adoption(services):
    """The historical Buddy-A pin resolves to D_A from the receipt alone."""
    svc, head_revision = services
    projection = direct.project_world_graph_direct(
        svc, _projection_request(revision_pin=LEGACY_BUDDY_A_REVISION)
    )
    assert projection.snapshot.revision_id == head_revision
    assert projection.snapshot.is_head is True


def test_revision_pin_exact_dungeonmind_passthrough(services):
    svc, head_revision = services
    projection = direct.project_world_graph_direct(
        svc, _projection_request(revision_pin=head_revision)
    )
    assert projection.snapshot.revision_id == head_revision


def test_revision_pin_unknown_fails_closed(services):
    svc, _ = services
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.project_world_graph_direct(
            svc, _projection_request(revision_pin="rev:never-existed")
        )
    assert excinfo.value.code == "revision_not_bridged"
    assert excinfo.value.status_code == 404


def test_uninitialized_world_is_not_integrity():
    world_graph = InMemoryWorldGraphRepository()
    bundle = _FakeBundle(world_graph, _seed_sources(), None)
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.direct_services_from_bundle(bundle, WORLD_ID)
    assert excinfo.value.code == "authority_receipt_missing"
    assert excinfo.value.status_code == 503


def test_head_without_genesis_is_integrity():
    world_graph = InMemoryWorldGraphRepository()
    world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:r3-test"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(world_graph, _seed_sources(), None)
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.direct_services_from_bundle(bundle, WORLD_ID)
    assert excinfo.value.code == "authority_integrity"
    assert excinfo.value.status_code == 500
    assert excinfo.value.diagnostics[0]["reason"] == "head_without_genesis"


def test_adoption_receipt_without_head_is_integrity():
    world_graph = InMemoryWorldGraphRepository()
    bundle = _FakeBundle(
        world_graph, _seed_sources(), _receipt(WORLD_ID, "rev:never-published")
    )
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.direct_services_from_bundle(bundle, WORLD_ID)
    assert excinfo.value.code == "authority_integrity"
    assert excinfo.value.status_code == 500
    assert excinfo.value.diagnostics[0]["reason"] == "genesis_receipt_without_head"


def test_reviewed_init_receipt_without_head_is_integrity():
    world_graph = InMemoryWorldGraphRepository()
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        None,
        _FakeReviewedInitReceipt(WORLD_ID, "rev:never-published"),
    )
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.direct_services_from_bundle(bundle, WORLD_ID)
    assert excinfo.value.code == "authority_integrity"
    assert excinfo.value.diagnostics[0]["reason"] == "genesis_receipt_without_head"


def test_both_genesis_receipts_are_integrity():
    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:r3-test"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        _receipt(WORLD_ID, published.revision_id),
        _FakeReviewedInitReceipt(WORLD_ID, published.revision_id),
    )
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.direct_services_from_bundle(bundle, WORLD_ID)
    assert excinfo.value.code == "authority_integrity"
    assert excinfo.value.diagnostics[0]["reason"] == "both_genesis_receipts"


def test_reviewed_init_binding_has_no_legacy_bridge():
    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:r3-test"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        None,
        _FakeReviewedInitReceipt(WORLD_ID, published.revision_id),
    )
    svc = direct.direct_services_from_bundle(bundle, WORLD_ID)
    assert svc.binding.genesis == "reviewed_world_initialization"
    assert svc.binding.legacy_buddy_revision_id is None
    assert svc.binding.dungeonmind_first_revision_id == published.revision_id
    assert svc.binding.dungeonmind_head_revision_id == published.revision_id
    projection = direct.project_world_graph_direct(
        svc, _projection_request(revision_pin=published.revision_id)
    )
    assert projection.snapshot.revision_id == published.revision_id


def test_adoption_binding_preserves_legacy_bridge(services):
    svc, head_revision = services
    assert svc.binding.genesis == "existing_world_adoption"
    assert svc.binding.legacy_buddy_revision_id == LEGACY_BUDDY_A_REVISION
    assert svc.binding.dungeonmind_first_revision_id == head_revision
    assert (
        direct._resolve_revision_pin(LEGACY_BUDDY_A_REVISION, svc.binding)
        == head_revision
    )
    assert direct._resolve_revision_pin(head_revision, svc.binding) == head_revision


def test_provider_receipt_integrity_is_not_unavailable():
    from dungeonmind.domain.errors import PersistenceIntegrityError

    world_graph = InMemoryWorldGraphRepository()
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        None,
        adoption_error=PersistenceIntegrityError(
            "existing-world adoption receipt references a missing revision"
        ),
    )
    with pytest.raises(direct.DirectWorldGraphReadError) as excinfo:
        direct.direct_services_from_bundle(bundle, WORLD_ID)
    assert excinfo.value.code == "authority_integrity"
    assert excinfo.value.status_code == 500


# ---------------------------------------------------------------------------
# Adapter: retrieval operations
# ---------------------------------------------------------------------------


def test_direct_search_by_label_text(services):
    svc, _ = services
    result = direct.search_world_graph_direct(
        svc,
        WorldGraphSearchRequest(
            schema="dmb_world_graph_search_request_v1",
            queryText="tavern",
            **_retrieval_context(),
        ),
    )
    labels = [node.label for node in result.nodes]
    assert "The Prancing Tavern" in labels


def test_direct_get_object_hit_and_miss(services):
    svc, _ = services
    hit = direct.get_object_direct(
        svc,
        WorldGraphObjectRequest(
            schema="dmb_world_graph_object_request_v1",
            nodeId="obj:tavern",
            **_retrieval_context(),
        ),
    )
    assert [node.node_id for node in hit.nodes] == ["obj:tavern"]

    miss = direct.get_object_direct(
        svc,
        WorldGraphObjectRequest(
            schema="dmb_world_graph_object_request_v1",
            nodeId="obj:no-such-node",
            **_retrieval_context(),
        ),
    )
    assert miss.nodes == []


def test_direct_neighborhood_depth_one(services):
    svc, _ = services
    result = direct.get_neighborhood_direct(
        svc,
        WorldGraphNeighborhoodRequest(
            schema="dmb_world_graph_neighborhood_request_v1",
            seedNodeIds=["obj:tavern"],
            maxDepth=1,
            **_retrieval_context(),
        ),
    )
    node_ids = {node.node_id for node in result.nodes}
    assert "obj:tavern" in node_ids
    assert "obj:hidden-cellar" in node_ids  # via contains edge
    assert "obj:hero" in node_ids  # via located_in edge


def test_direct_neighborhood_depth_two_is_coherent(services):
    """Native depth-2 neighborhood is independently proven.

    The Buddy kernel's depth-2 KeyError is a retired oracle defect. Native
    success must not depend on legacy success.
    """
    svc, _ = services
    result = direct.get_neighborhood_direct(
        svc,
        WorldGraphNeighborhoodRequest(
            schema="dmb_world_graph_neighborhood_request_v1",
            seedNodeIds=["obj:hidden-cellar"],
            maxDepth=2,
            **_retrieval_context(),
        ),
    )
    node_ids = {node.node_id for node in result.nodes}
    assert "obj:hidden-cellar" in node_ids
    assert "obj:tavern" in node_ids  # depth 1 via contains
    assert "obj:hero" in node_ids  # depth 2 via tavern
    assert result.outcome in {"enough", "partial", "truncated"}


def test_direct_evidence_lists_source_anchors(services):
    svc, _ = services
    result = direct.get_evidence_direct(
        svc,
        WorldGraphEvidenceRequest(
            schema="dmb_world_graph_evidence_request_v1",
            target={"kind": "node", "id": "obj:tavern"},
            **_retrieval_context(),
        ),
    )
    anchors = result.source_anchors
    assert anchors, "expected at least one source anchor for obj:tavern"
    assert all(a.anchor_id.startswith("source-anchor:v1:") for a in anchors)


def test_anchor_emit_revalidate_open_round_trip(services, tmp_path):
    """Anchor ids emitted by reads revalidate and open digest-verified content."""
    svc, _ = services
    # The one-recap artifact uri is repo://corpus/world_lore.md and its
    # revision digest matches ANCHOR_CONTENT; write the product-local file.
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus" / "world_lore.md").write_text(ANCHOR_CONTENT, encoding="utf-8")

    evidence = direct.get_evidence_direct(
        svc,
        WorldGraphEvidenceRequest(
            schema="dmb_world_graph_evidence_request_v1",
            target={"kind": "node", "id": "obj:tavern"},
            **_retrieval_context(),
        ),
    )
    anchor_id = evidence.source_anchors[0].anchor_id
    opened = direct.read_source_anchor_direct(
        svc,
        WorldGraphSourceAnchorReadRequest(
            schema="dmb_world_graph_source_anchor_read_request_v1",
            anchorId=anchor_id,
            **_retrieval_context(),
        ),
        repo_root=tmp_path,
    )
    assert opened.outcome == "enough"
    assert "Prancing Tavern" in (opened.content or "")
    assert opened.content_sha256 == ANCHOR_CONTENT_DIGEST


def test_anchor_id_prefix_round_trip():
    buddy_id = "source-anchor:v1:abc123"
    dnd_id = "dm-source-anchor:v1:abc123"
    assert direct._dnd_anchor_id(buddy_id) == dnd_id
    assert direct._buddy_anchor_id(dnd_id) == buddy_id
    # Non-prefixed ids pass through untouched.
    assert direct._dnd_anchor_id("other") == "other"
    assert direct._buddy_anchor_id("other") == "other"


def test_focus_presentation_recomputed_from_admitted_provenance(services):
    """Session focus flags derive from admitted evidence session identity."""
    svc, _ = services
    request = _projection_request(
        scope_mode="world",
        focus={"kind": "session", "session_id": "session-9", "campaign_id": CAMPAIGN_ONE},
    )
    projection = direct.project_world_graph_direct(svc, request)
    tavern = next(n for n in projection.nodes if n.node_id == "obj:tavern")
    hero = next(n for n in projection.nodes if n.node_id == "obj:hero")
    # ev:tavern carries session_id=session-9 → focus-anchored; ev:hero does not.
    assert tavern.anchored_to_focus_session is True
    assert hero.anchored_to_focus_session is False


# ---------------------------------------------------------------------------
# Service dispatch (authority-mode routing)
# ---------------------------------------------------------------------------


@pytest.fixture()
def _dungeonmind_mode(monkeypatch, tmp_path):
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()
    yield
    storage.clear_world_graph_cache_roots()


def _explode(*_args, **_kwargs):
    raise AssertionError("legacy Buddy graph read machinery must not run on the direct path")


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_projection_service_dispatches_direct_without_kernel(
    monkeypatch, services, tmp_path
):
    svc, _ = services
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)
    monkeypatch.setattr(kernel, "project_world_graph_from_context", _explode)
    monkeypatch.setattr(kernel, "resolve_projection_read_context", _explode)
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    monkeypatch.setattr(world_graph_authority, "route_read_request", _explode)
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    monkeypatch.setattr(world_graph_authority, "ensure_hydrated_authority", _explode)
    monkeypatch.setattr(storage, "load_current_world_graph", _explode)

    projection = projection_service.project_world_graph(_projection_request())
    assert {n.node_id for n in projection.nodes} == {
        "obj:tavern",
        "obj:hidden-cellar",
        "obj:hero",
        "obj:road-sign",
    }


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_retrieval_service_dispatches_all_operations_direct(monkeypatch, services):
    svc, _ = services
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)
    monkeypatch.setattr(kernel, "search_campaign_graph", _explode)
    monkeypatch.setattr(kernel, "get_campaign_object", _explode)
    monkeypatch.setattr(kernel, "get_object_neighborhood", _explode)
    monkeypatch.setattr(kernel, "get_object_evidence", _explode)
    monkeypatch.setattr(kernel, "resolve_admitted_anchor_match", _explode)
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    monkeypatch.setattr(world_graph_authority, "route_read_request", _explode)
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    monkeypatch.setattr(world_graph_authority, "ensure_hydrated_authority", _explode)
    monkeypatch.setattr(storage, "load_current_world_graph", _explode)

    search = retrieval_service.search_campaign_graph(
        WorldGraphSearchRequest(
            schema="dmb_world_graph_search_request_v1",
            queryText="tavern",
            **_retrieval_context(),
        )
    )
    assert any(n.label == "The Prancing Tavern" for n in search.nodes)

    obj = retrieval_service.get_campaign_object(
        WorldGraphObjectRequest(
            schema="dmb_world_graph_object_request_v1",
            nodeId="obj:tavern",
            **_retrieval_context(),
        )
    )
    assert [n.node_id for n in obj.nodes] == ["obj:tavern"]

    neighborhood = retrieval_service.get_object_neighborhood(
        WorldGraphNeighborhoodRequest(
            schema="dmb_world_graph_neighborhood_request_v1",
            seedNodeIds=["obj:tavern"],
            maxDepth=1,
            **_retrieval_context(),
        )
    )
    assert "obj:hidden-cellar" in {n.node_id for n in neighborhood.nodes}

    evidence = retrieval_service.get_object_evidence(
        WorldGraphEvidenceRequest(
            schema="dmb_world_graph_evidence_request_v1",
            target={"kind": "node", "id": "obj:tavern"},
            **_retrieval_context(),
        )
    )
    assert evidence.source_anchors

    anchor = retrieval_service.read_source_anchor(
        WorldGraphSourceAnchorReadRequest(
            schema="dmb_world_graph_source_anchor_read_request_v1",
            anchorId=evidence.source_anchors[0].anchor_id,
            **_retrieval_context(),
        ),
        repo_root=Path("/nonexistent-r3-repo-root"),
    )
    # Content join fails (no repo files) but revalidation succeeds.
    assert anchor.outcome in {"enough", "partial", "unavailable"}


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_source_span_anchor_composes_registry_backed_opener(monkeypatch, services):
    """R.3: source_span anchors compose the registry-backed opener end-to-end.

    The direct adapter revalidates admission via DungeonMind, then delegates
    to the same product-local registry-backed opener the legacy path uses.
    """
    svc, _ = services
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)

    # Mock the registry-backed opener to prove it is composed.
    captured: dict = {}

    def _fake_open(**kwargs):
        captured.update(kwargs)
        from graph_memory.retrieval.models import (
            WorldGraphRetrievalTrustBoundary,
            WorldGraphSourceAnchorReadResult,
        )

        return WorldGraphSourceAnchorReadResult(
            outcome="enough",
            snapshot=kwargs.get("snapshot"),
            anchor_id=kwargs["anchor_id"],
            evidence_ref_id=kwargs.get("evidence_ref_id"),
            source_artifact_id=kwargs["source_artifact_id"],
            source_domain="worldbuilding",
            source_span_ref_id=kwargs["source_span_ref_id"],
            locator_kind="source_span",
            media_type="text/markdown",
            content="span content",
            content_sha256=kwargs.get("graph_content_sha256"),
            line_start=None,
            line_end=None,
            truncated=False,
            trust_boundary=WorldGraphRetrievalTrustBoundary(
                can_trust=[], cannot_trust=[]
            ),
            diagnostics=[],
        )

    # Patch the adapter's lazy import of the opener.
    import apps.live_control_server.services.worldbuilding_source_span_read as span_mod

    monkeypatch.setattr(span_mod, "read_admitted_worldbuilding_span", _fake_open)

    # Build a source_span anchor resolution directly.
    from dungeonmind.application.world_graph_retrieval import (
        SourceAnchorMetadata,
        SourceAnchorResolution,
    )
    from dungeonmind.contracts.evidence import EvidenceRefV2

    span_evidence = EvidenceRefV2(
        schema_version="dm_evidence_ref_v2",
        evidence_ref_id="ev:span-anchor",
        source_artifact_id="src:one-recap",
        source_revision_id="srcrev:one-recap-v1",
        source_domain_key="buddy.worldbuilding",
        source_domain="worldbuilding",
        evidence_role="support",
        can_open_source=True,
        can_highlight_span=True,
        session_id=None,
        source_span_ref_id="span:para-1",
        locator=None,
        uri=None,
        source_locator=None,
        line_ref=None,
    )

    # Get the artifact from the seeded repository.
    artifact = svc.bundle.sources.get_artifact("src:one-recap")

    anchor_meta = SourceAnchorMetadata(
        anchor_id="dm-source-anchor:v1:test",
        evidence_ref_id="ev:span-anchor",
        source_artifact_id="src:one-recap",
        source_revision_id="srcrev:one-recap-v1",
        locator_identity="span:para-1",
        source_span_ref_id="span:para-1",
        can_open_source=True,
        can_highlight_span=True,
        supporting_object_ids=(),
        supporting_relationship_ids=(),
        supporting_assertion_ids=(),
        evidence=span_evidence,
        artifact=artifact,
    )
    # Build a minimal valid snapshot for the resolution.
    from datetime import datetime, timezone

    from dungeonmind.contracts.projection import ProjectionFocus
    from dungeonmind.contracts.projection_v2 import (
        Admissibility,
        ProjectionSnapshotV2,
        ScopeModeV2,
    )

    snapshot = ProjectionSnapshotV2(
        world_id="eldyrwild",
        campaign_id="longmont-c1",
        focus=ProjectionFocus(kind="none"),
        admissibility=Admissibility.GM,
        scope_mode=ScopeModeV2.CAMPAIGN,
        revision_id="rev:test",
        head_revision_id="rev:test",
        is_head=True,
        projected_at=datetime.now(timezone.utc),
    )

    resolution = SourceAnchorResolution(
        snapshot=snapshot,
        found=True,
        anchor_id="dm-source-anchor:v1:test",
        anchor=anchor_meta,
    )

    result = direct._anchor_read_view(
        svc,
        resolution,
        request=WorldGraphSourceAnchorReadRequest(
            schema="dmb_world_graph_source_anchor_read_request_v1",
            anchorId="source-anchor:v1:test",
            **_retrieval_context(),
        ),
        repo_root=Path("/nonexistent-r3-repo-root"),
    )
    assert result.outcome == "enough"
    assert result.content == "span content"
    assert captured["source_span_ref_id"] == "span:para-1"
    assert captured["source_artifact_id"] == "src:one-recap"


def test_source_span_anchor_cross_campaign_world_scope(monkeypatch, services):
    """R.3: cross-campaign world-scope reads open campaign-owned source spans.

    A campaign-owned source artifact (e.g. campaign_id=longmont-c2) may be
    correctly admitted by DND's cross-campaign projection. The product opener
    must not reject it because the snapshot represents cross-campaign scope
    with campaign_id="".
    """
    svc, _ = services
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)

    # Mock the registry-backed opener to prove it is composed.
    captured: dict = {}

    def _fake_open(**kwargs):
        captured.update(kwargs)
        from graph_memory.retrieval.models import (
            WorldGraphRetrievalTrustBoundary,
            WorldGraphSourceAnchorReadResult,
        )

        return WorldGraphSourceAnchorReadResult(
            outcome="enough",
            snapshot=kwargs.get("snapshot"),
            anchor_id=kwargs["anchor_id"],
            evidence_ref_id=kwargs.get("evidence_ref_id"),
            source_artifact_id=kwargs["source_artifact_id"],
            source_domain="worldbuilding",
            source_span_ref_id=kwargs["source_span_ref_id"],
            locator_kind="source_span",
            media_type="text/markdown",
            content="span content",
            content_sha256=kwargs.get("graph_content_sha256"),
            line_start=None,
            line_end=None,
            truncated=False,
            trust_boundary=WorldGraphRetrievalTrustBoundary(
                can_trust=[], cannot_trust=[]
            ),
            diagnostics=[],
        )

    # Patch the adapter's lazy import of the opener.
    import apps.live_control_server.services.worldbuilding_source_span_read as span_mod

    monkeypatch.setattr(span_mod, "read_admitted_worldbuilding_span", _fake_open)

    # Build a source_span anchor resolution directly.
    from dungeonmind.application.world_graph_retrieval import (
        SourceAnchorMetadata,
        SourceAnchorResolution,
    )
    from dungeonmind.contracts.evidence import EvidenceRefV2

    span_evidence = EvidenceRefV2(
        schema_version="dm_evidence_ref_v2",
        evidence_ref_id="ev:span-anchor",
        source_artifact_id="src:one-recap",
        source_revision_id="srcrev:one-recap-v1",
        source_domain_key="buddy.worldbuilding",
        source_domain="worldbuilding",
        evidence_role="support",
        can_open_source=True,
        can_highlight_span=True,
        session_id=None,
        source_span_ref_id="span:para-1",
        locator=None,
        uri=None,
        source_locator=None,
        line_ref=None,
    )

    # Get the artifact from the seeded repository.
    artifact = svc.bundle.sources.get_artifact("src:one-recap")

    anchor_meta = SourceAnchorMetadata(
        anchor_id="dm-source-anchor:v1:test",
        evidence_ref_id="ev:span-anchor",
        source_artifact_id="src:one-recap",
        source_revision_id="srcrev:one-recap-v1",
        locator_identity="span:para-1",
        source_span_ref_id="span:para-1",
        can_open_source=True,
        can_highlight_span=True,
        supporting_object_ids=(),
        supporting_relationship_ids=(),
        supporting_assertion_ids=(),
        evidence=span_evidence,
        artifact=artifact,
    )
    # Build a cross-campaign world-scope snapshot for the resolution.
    from datetime import datetime, timezone

    from dungeonmind.contracts.projection import ProjectionFocus
    from dungeonmind.contracts.projection_v2 import (
        Admissibility,
        ProjectionSnapshotV2,
        ScopeModeV2,
    )

    snapshot = ProjectionSnapshotV2(
        world_id="eldyrwild",
        campaign_id=None,  # Cross-campaign world scope
        focus=ProjectionFocus(kind="none"),
        admissibility=Admissibility.GM,
        scope_mode=ScopeModeV2.WORLD_CROSS_CAMPAIGN,
        revision_id="rev:test",
        head_revision_id="rev:test",
        is_head=True,
        projected_at=datetime.now(timezone.utc),
    )

    resolution = SourceAnchorResolution(
        snapshot=snapshot,
        found=True,
        anchor_id="dm-source-anchor:v1:test",
        anchor=anchor_meta,
    )

    result = direct._anchor_read_view(
        svc,
        resolution,
        request=WorldGraphSourceAnchorReadRequest(
            schema="dmb_world_graph_source_anchor_read_request_v1",
            anchorId="source-anchor:v1:test",
            **_retrieval_context(scopeMode="world"),
        ),
        repo_root=Path("/nonexistent-r3-repo-root"),
    )
    assert result.outcome == "enough"
    assert result.content == "span content"
    assert captured["source_span_ref_id"] == "span:para-1"
    assert captured["source_artifact_id"] == "src:one-recap"
    # The snapshot passed to the opener must represent cross-campaign scope.
    assert captured["snapshot"].scope_mode == "world"
    assert captured["snapshot"].campaign_id == ""


def _write_recap_parent(tmp_path: Path, body: str) -> tuple[Path, str]:
    recap_dir = tmp_path / "out" / "graph_memory" / "runs" / "c1" / "session-1"
    recap_dir.mkdir(parents=True)
    (recap_dir / "normalized_recap_source.md").write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return recap_dir, digest


def _open_recap_span(services, tmp_path: Path, *, digest: str, span_id: str):
    svc, _ = services
    svc.bundle.sources.put_artifact(
        SourceArtifactV2(
            source_artifact_id="artifact:recap:c1:session-1",
            source_domain_key="buddy.recap",
            source_domain=SourceDomain.SESSION_RECAP,
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ONE,
            session_id="session-1",
            uri="repo://out/graph_memory/runs/c1/session-1/normalized_recap_source.md",
            current_revision_id="srcrev:recap-s1",
            authority=None,
            visibility=Visibility.GM,
            artifact_kind=None,
            document_class=None,
            review_state=None,
            source_visibility_state=None,
            workspace_document_ref=None,
            lineage={},
            status=SourceStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    svc.bundle.sources.put_revision(
        SourceRevision(
            source_revision_id="srcrev:recap-s1",
            source_artifact_id="artifact:recap:c1:session-1",
            content_sha256=digest,
            body_storage="external",
            locator="test://recap-s1",
            created_at=NOW,
        )
    )
    from dungeonmind.application.world_graph_retrieval import (
        SourceAnchorMetadata,
        SourceAnchorResolution,
    )
    from dungeonmind.contracts.evidence import EvidenceRefV2
    from dungeonmind.contracts.projection import ProjectionFocus
    from dungeonmind.contracts.projection_v2 import (
        Admissibility,
        ProjectionSnapshotV2,
        ScopeModeV2,
    )

    recap_evidence = EvidenceRefV2(
        schema_version="dm_evidence_ref_v2",
        evidence_ref_id="ev:recap-span",
        source_artifact_id="artifact:recap:c1:session-1",
        source_revision_id="srcrev:recap-s1",
        source_domain_key="buddy.recap",
        source_domain="session_recap",
        evidence_role="support",
        can_open_source=True,
        can_highlight_span=True,
        session_id="session-1",
        source_span_ref_id=span_id,
        locator=None,
        uri=None,
        source_locator=None,
        line_ref=None,
    )
    artifact = svc.bundle.sources.get_artifact("artifact:recap:c1:session-1")
    snapshot = ProjectionSnapshotV2(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ONE,
        focus=ProjectionFocus(kind="none"),
        admissibility=Admissibility.GM,
        scope_mode=ScopeModeV2.CAMPAIGN,
        revision_id="rev:test",
        head_revision_id="rev:test",
        is_head=True,
        projected_at=NOW,
    )
    resolution = SourceAnchorResolution(
        snapshot=snapshot,
        found=True,
        anchor_id="dm-source-anchor:v1:recap-test",
        anchor=SourceAnchorMetadata(
            anchor_id="dm-source-anchor:v1:recap-test",
            evidence_ref_id="ev:recap-span",
            source_artifact_id="artifact:recap:c1:session-1",
            source_revision_id="srcrev:recap-s1",
            locator_identity=span_id,
            source_span_ref_id=span_id,
            can_open_source=True,
            can_highlight_span=True,
            supporting_object_ids=(),
            supporting_relationship_ids=(),
            supporting_assertion_ids=(),
            evidence=recap_evidence,
            artifact=artifact,
        ),
    )
    return direct._anchor_read_view(
        svc,
        resolution,
        request=WorldGraphSourceAnchorReadRequest(
            schema="dmb_world_graph_source_anchor_read_request_v1",
            anchorId="source-anchor:v1:recap-test",
            **_retrieval_context(),
        ),
        repo_root=tmp_path,
    )


def test_recap_source_span_opens_digest_pinned_parent_paragraph(services, tmp_path):
    """R.3 Case A: recap emit → revalidate → slice digest-pinned parent bytes.

    Session-recap spans are not worldbuilding registry artifacts. After
    DungeonMind revalidation, paragraph N is taken from the parent recap
    whose digest matches DungeonMind. Sidecar files are unbound and ignored.
    """
    parent_body = (
        "---\ntitle: Session 1\n---\n\n"
        "# Session 1 Recap\n\n"
        "After traveling together the party reached Stone Bridge.\n\n"
        "The town is hardly known.\n\n"
        "They drank at the River's Edge.\n\n"
        "Directions led west along the river.\n\n"
        "The trail reached Wizard's Tower Brewing Co.\n\n"
        "Within they met Glowkindle and agreed to clear the rats.\n\n"
        "A fine first combat.\n\n"
        "Finally they found a tiled hallway.\n"
    )
    recap_dir, digest = _write_recap_parent(tmp_path, parent_body)
    tampered = "TAMPERED SIDECAR — must not be served"
    (recap_dir / "source_spans").mkdir()
    (recap_dir / "source_spans" / "recap_paragraph_007.md").write_text(
        tampered, encoding="utf-8"
    )
    (recap_dir / "source_span_index.json").write_text(
        json.dumps(
            {
                "content_sha256": digest,
                "spans": [
                    {
                        "source_span_id": "session-1:recap:paragraph:007",
                        "start_line": 1,
                        "end_line": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = _open_recap_span(
        services,
        tmp_path,
        digest=digest,
        span_id="session-1:recap:paragraph:007",
    )
    assert result.outcome == "enough"
    assert result.locator_kind == "source_span"
    assert result.content == "Within they met Glowkindle and agreed to clear the rats."
    assert result.content_sha256 == digest
    assert tampered not in (result.content or "")


def test_recap_span_refuses_sidecar_content_missing_from_parent(services, tmp_path):
    """Parent digest is valid, but the paragraph exists only in a sidecar."""
    parent_body = "---\ntitle: Session 1\n---\n\n# Session 1 Recap\n\nOnly one body paragraph.\n"
    recap_dir, digest = _write_recap_parent(tmp_path, parent_body)
    (recap_dir / "source_spans").mkdir()
    (recap_dir / "source_spans" / "recap_paragraph_007.md").write_text(
        "Sidecar-only Glowkindle paragraph that is not in the parent.",
        encoding="utf-8",
    )
    result = _open_recap_span(
        services,
        tmp_path,
        digest=digest,
        span_id="session-1:recap:paragraph:007",
    )
    assert result.outcome == "unavailable"
    assert result.content is None or result.content == ""


def test_recap_line_span_fails_closed_on_digest_prefix_mismatch(services, tmp_path):
    parent_body = "line one\nline two\nline three\n"
    _, digest = _write_recap_parent(tmp_path, parent_body)
    result = _open_recap_span(
        services,
        tmp_path,
        digest=digest,
        span_id=f"artifact:recap:c1:session-1:span:{'0'*12}:1-1",
    )
    assert result.outcome == "unavailable"


def test_recap_line_span_slices_digest_prefixed_parent_lines(services, tmp_path):
    parent_body = "alpha\nbeta\ngamma\n"
    _, digest = _write_recap_parent(tmp_path, parent_body)
    result = _open_recap_span(
        services,
        tmp_path,
        digest=digest,
        span_id=f"artifact:recap:c1:session-1:span:{digest[:12]}:2-2",
    )
    assert result.outcome == "enough"
    assert result.content == "beta"
    assert result.line_start == 2
    assert result.line_end == 2
    assert result.content_sha256 == digest


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_explicit_nonproduction_root_bypasses_direct(monkeypatch, services, tmp_path):
    """Tests/tooling with an explicit non-production root stay on the file path."""
    svc, _ = services
    monkeypatch.setattr(
        direct,
        "direct_services_from_config",
        lambda world_id: (_ for _ in ()).throw(
            AssertionError("direct path must not run for explicit test roots")
        ),
    )
    request = _projection_request()
    with pytest.raises(projection_service.WorldGraphProjectionServiceError):
        # No graph store under tmp_path → legacy path fails closed, proving
        # the read did not dispatch to DungeonMind.
        projection_service.project_world_graph(request, root=tmp_path / "empty-store")


def test_buddy_files_mode_never_dispatches_direct(monkeypatch, services, tmp_path):
    monkeypatch.delenv(storage.WORLD_GRAPH_AUTHORITY_ENV, raising=False)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()
    monkeypatch.setattr(
        direct,
        "direct_services_from_config",
        lambda world_id: (_ for _ in ()).throw(
            AssertionError("direct path must not run outside dungeonmind mode")
        ),
    )
    with pytest.raises(projection_service.WorldGraphProjectionServiceError):
        projection_service.project_world_graph(_projection_request())


@pytest.mark.parametrize("direct_read_value", [None, "0", "1", "garbage"])
def test_obsolete_direct_read_env_does_not_control_routing(
    monkeypatch, services, tmp_path, direct_read_value
):
    """Retired ``DUNGEONMIND_WORLD_GRAPH_DIRECT_READ`` has no routing power."""
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    if direct_read_value is None:
        monkeypatch.delenv("DUNGEONMIND_WORLD_GRAPH_DIRECT_READ", raising=False)
    else:
        monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_DIRECT_READ", direct_read_value)
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()
    svc, _ = services
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    monkeypatch.setattr(world_graph_authority, "ensure_hydrated_authority", _explode)
    monkeypatch.setattr(storage, "load_current_world_graph", _explode)
    projection = projection_service.project_world_graph(_projection_request())
    assert projection.nodes, "dungeonmind production reads stay native regardless of retired env"


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_explicit_production_root_still_dispatches_native(monkeypatch, services):
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    svc, _ = services
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    projection = projection_service.project_world_graph(
        _projection_request(), root=config.world_graph_root()
    )
    assert projection.nodes


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_direct_read_fails_closed_when_database_unconfigured(monkeypatch):
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    monkeypatch.delenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL")
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    monkeypatch.setattr(world_graph_authority, "ensure_hydrated_authority", _explode)
    monkeypatch.setattr(storage, "load_current_world_graph", _explode)
    with pytest.raises(projection_service.WorldGraphProjectionServiceError) as excinfo:
        projection_service.project_world_graph(_projection_request())
    assert excinfo.value.code == "authority_unavailable"
    assert excinfo.value.status_code == 503


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_unknown_pin_fails_closed_without_hydration(monkeypatch, services):
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    svc, _ = services
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    monkeypatch.setattr(world_graph_authority, "ensure_hydrated_authority", _explode)
    monkeypatch.setattr(storage, "load_current_world_graph", _explode)
    with pytest.raises(projection_service.WorldGraphProjectionServiceError) as excinfo:
        projection_service.project_world_graph(
            _projection_request(revision_pin="rev:never-existed")
        )
    assert excinfo.value.code == "revision_not_bridged"
    assert excinfo.value.status_code == 404


# ---------------------------------------------------------------------------
# Frozen-root independence (R.3 merge invariant)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_direct_reads_succeed_with_frozen_buddy_store_missing(
    monkeypatch, services, tmp_path
):
    """Production reads never open the frozen Buddy graph store.

    The configured World Graph root points at a directory that does not exist;
    projection and retrieval still succeed because the direct path derives the
    A→D_A bridge from the DungeonMind adoption receipt, not from Buddy files.
    """
    svc, _ = services
    missing_root = tmp_path / "definitely-no-frozen-store"
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(missing_root))
    storage.clear_world_graph_cache_roots()
    monkeypatch.setattr(direct, "direct_services_from_config", lambda world_id: svc)

    assert not missing_root.exists()
    projection = projection_service.project_world_graph(_projection_request())
    assert projection.nodes, "projection must serve from DungeonMind authority alone"
    result = retrieval_service.search_campaign_graph(
        WorldGraphSearchRequest(
            schema="dmb_world_graph_search_request_v1",
            queryText="tavern",
            **_retrieval_context(),
        )
    )
    assert any(n.label == "The Prancing Tavern" for n in result.nodes)


# ---------------------------------------------------------------------------
# Prewarm / recipe gating in dungeonmind mode
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_prewarm_coordinator_is_a_noop_in_dungeonmind_mode():
    coordinator = prewarm_service.WorldGraphPrewarmCoordinator()
    assert coordinator.start() is True
    assert coordinator.is_running is False  # no worker thread was started
    assert coordinator.stop() is True


@pytest.mark.usefixtures("_dungeonmind_mode")
def test_projection_recipes_do_not_register_or_warm(tmp_path):
    recipes_service.reset_projection_recipes_for_tests()
    recipes_service.register_projection_recipe(
        _projection_request(), root=tmp_path
    )
    # Registry stays empty: registration is a no-op in dungeonmind mode.
    assert recipes_service._snapshot_recipes(root=tmp_path, world_id=WORLD_ID) == []
    # Warm replay is likewise a no-op (would explode touching the kernel).
    monkeypatch_kernel = kernel.open_world_graph_head
    kernel.open_world_graph_head = _explode
    try:
        recipes_service.warm_projection_recipes_for_ready_revision(
            root=tmp_path,
            world_id=WORLD_ID,
            revision_id="rev:anything",
            still_current=lambda: True,
        )
    finally:
        kernel.open_world_graph_head = monkeypatch_kernel


# ---------------------------------------------------------------------------
# Error mapping observability + witness vocabulary v2
# ---------------------------------------------------------------------------


def test_map_direct_error_preserves_underlying_cause():
    original = RuntimeError("span opener exploded")
    mapped = direct._map_direct_error(original)
    assert mapped.code == "projection_internal_error"
    assert mapped.cause_type == "RuntimeError"
    assert mapped.cause_message == "span opener exploded"
    assert "RuntimeError: span opener exploded" in str(mapped)


def test_map_direct_error_preserves_dungeonmind_cause():
    from dungeonmind.domain.errors import DungeonMindError

    original = DungeonMindError("resolve_source_anchor refused")
    mapped = direct._map_direct_error(original)
    assert mapped.cause_type == "DungeonMindError"
    assert "resolve_source_anchor refused" in str(mapped)


def _load_r3_witness():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "r3_compare_witness",
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "compare_direct_dungeonmind_world_graph_reads.py",
    )
    witness = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = witness
    spec.loader.exec_module(witness)
    return witness


def test_witness_vocabulary_v2_is_sealed_to_ratified_identities():
    witness = _load_r3_witness()
    assert witness.VOCABULARY_VERSION == "v2"

    mireward_c1, _ = witness.classify_legacy_only_node(
        "location:mireward", "location", case="projection:campaign:c1"
    )
    canary_c2, _ = witness.classify_legacy_only_node(
        "node:cutover-canary", "npc", case="projection:campaign:c2"
    )
    ext_cls, _ = witness.classify_legacy_only_node(
        "res:statblock", "external_resource", case="projection:campaign:c1"
    )
    latchling_desc, _ = witness.classify_legacy_only_attribute(
        "threat:authored:d16d43d376833e38caf46dd19b1dd17f", "description"
    )
    session_cls, _ = witness.classify_legacy_only_attribute(
        "obj:anything", "session_observation"
    )
    known_evidence, _ = witness.classify_legacy_only_evidence(
        "evidence:corpus:worldbuilding:mireward",
        case="projection:campaign:c1",
    )

    assert mireward_c1 == witness.CLASS_APPROVED_DIVERGENCE
    assert canary_c2 == witness.CLASS_APPROVED_DIVERGENCE
    assert ext_cls == witness.CLASS_RETIRED_LEGACY
    assert latchling_desc == witness.CLASS_APPROVED_DIVERGENCE
    assert session_cls == witness.CLASS_RETIRED_LEGACY
    assert known_evidence == witness.CLASS_APPROVED_DIVERGENCE
    assert "player-rejected" not in (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "compare_direct_dungeonmind_world_graph_reads.py"
    ).read_text(encoding="utf-8")


def test_witness_vocabulary_v2_unknown_differences_stay_blocking():
    witness = _load_r3_witness()
    mireward_c2, _ = witness.classify_legacy_only_node(
        "location:mireward", "location", case="projection:campaign:c2"
    )
    mireward_world, _ = witness.classify_legacy_only_node(
        "location:mireward", "location", case="projection:world"
    )
    unexpected_node, _ = witness.classify_legacy_only_node(
        "location:unexpected", "location", case="projection:campaign:c1"
    )
    unrelated_description, _ = witness.classify_legacy_only_attribute(
        "obj:unrelated-subject", "description"
    )
    unknown_field, _ = witness.classify_legacy_only_attribute(
        "threat:tripod-null-calf", "unratified_field"
    )
    new_evidence, _ = witness.classify_legacy_only_evidence(
        "evidence:arbitrary-new-id", case="projection:campaign:c1"
    )
    known_id_wrong_case, _ = witness.classify_legacy_only_evidence(
        "evidence:corpus:worldbuilding:mireward",
        case="neighborhood:depth-1",
    )

    assert mireward_c2 == witness.CLASS_BLOCKING
    assert mireward_world == witness.CLASS_BLOCKING
    assert unexpected_node == witness.CLASS_BLOCKING
    assert unrelated_description == witness.CLASS_BLOCKING
    assert unknown_field == witness.CLASS_BLOCKING
    assert new_evidence == witness.CLASS_BLOCKING
    assert known_id_wrong_case == witness.CLASS_BLOCKING


def test_player_leak_detector_does_not_treat_subset_as_safe():
    witness = _load_r3_witness()
    gm_only = {"obj:tavern", "obj:hidden-cellar", "obj:hero"}
    # PLAYER returning every GM-only node is a subset of GM and must still leak.
    assert witness.player_gm_only_leaks(gm_only, gm_only) == sorted(gm_only)
    assert witness.player_gm_only_leaks(set(), gm_only) == []
    assert witness.player_gm_only_leaks({"obj:road-sign"}, gm_only) == []
    assert witness.player_gm_only_leaks({"obj:tavern", "obj:road-sign"}, gm_only) == [
        "obj:tavern"
    ]


def test_player_witness_excludes_authoritative_gm_only(services):
    witness = _load_r3_witness()
    svc, _ = services
    gm_request = _projection_request(admissibility="gm")
    player = direct.project_world_graph_direct(
        svc, _projection_request(admissibility="player")
    )
    native_gm = svc.projection.project(
        direct._map_projection_request(gm_request, svc.binding)
    )
    gm_only = witness.gm_only_object_ids_from_native_graph(native_gm.graph)
    assert "obj:tavern" in gm_only
    assert "obj:hidden-cellar" in gm_only
    assert "obj:hero" in gm_only
    assert "obj:road-sign" not in gm_only
    player_ids = {node.node_id for node in player.nodes}
    assert player_ids == {"obj:road-sign"}
    assert witness.player_gm_only_leaks(player_ids, set(gm_only)) == []
    assert witness.player_gm_only_leaks(player_ids | {"obj:tavern"}, set(gm_only)) == [
        "obj:tavern"
    ]
