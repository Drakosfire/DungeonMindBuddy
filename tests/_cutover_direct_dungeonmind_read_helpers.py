"""CUTOVER D.3B: portable in-memory DungeonMind read fixtures (no Buddy graph engine).

Rehomed from deleted ``test_cutover_direct_dungeonmind_world_graph_reads`` helpers
so Hermes / live-agent R.3 boundary tests can run with legacy packages absent.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

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
    def __init__(
        self,
        world_id: str,
        published_revision_id: str,
        *,
        published_graph_schema: str = "dm_union_graph_v6",
        published_graph_payload_sha256: str = "",
    ) -> None:
        self.world_id = world_id
        self.published_revision_id = published_revision_id
        self.published_graph_schema = published_graph_schema
        self.published_graph_payload_sha256 = published_graph_payload_sha256
        self.source_plan_schema = "test_reviewed_init_plan"
        self.initialization_id = "init:test"
        self.actor = "test@local"


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
