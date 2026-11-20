import copy
from types import SimpleNamespace
from tests._cutover_direct_dungeonmind_read_helpers import (
    _payload,
    _seed_sources,
    _meta,
    NOW,
    WORLD_ID,
    LEGACY_BUDDY_A_REVISION,
)
from dungeonmind.infrastructure.memory.repositories import (
    InMemoryWorldGraphRepository,
    InMemoryContributionRepository,
    InMemoryIdentityDecisionRepository,
    InMemoryExistingWorldAdoptionRepository,
    InMemorySourceRepository,
    InMemoryReviewedWorldInitializationRepository,
)
from dungeonmind.application.graph_snapshot import VersionedUnionGraphSnapshotReader
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_v3_descriptor,
)
from dungeonmind.application.existing_world_adoption import adopt_existing_world
from dungeonmind.contracts.existing_world_adoption import (
    ExistingWorldAdoptionBundleV2,
    ExistingWorldAdoptionSourceProvenanceV1,
)
from dungeonmind.application.existing_world_adoption_repair import (
    repair_existing_world_adoption_source_classification,
)
from dungeonmind.contracts.existing_world_adoption_repair import (
    ExistingWorldAdoptionSourceClassificationRepairIntentV1,
)
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.contracts.adopted_assertion_withdrawal import (
    AdoptedAssertionWithdrawalCommandV2,
    ADOPTED_ASSERTION_WITHDRAWAL_TOOL,
)
from dungeonmind.application.adopted_assertion_withdrawal import (
    withdraw_adopted_assertion,
)
from dungeonmind.contracts.capability import (
    CapabilityPolicy,
    GraphScope,
    ToolCapabilityRule,
    CapabilityCategory,
    CapabilityEffect,
)
from dungeonmind.contracts.projection import Admissibility
from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
import os
from urllib.parse import urlparse

import pytest
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresRepositoryBundle,
)
from dungeonmind.contracts.projection_v2 import (
    ScopeModeV2,
    WorldGraphProjectionRequestV2,
)
from dungeonmind.application.world_graph_retrieval import EvidenceTarget
from graph_memory.retrieval.models import (
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
)
from tests._cutover_direct_dungeonmind_read_helpers import (
    ANCHOR_CONTENT,
    ANCHOR_CONTENT_DIGEST,
)


@pytest.fixture(params=["memory", "postgres"])
def stores(request):
    if request.param == "postgres":
        dsn = os.environ.get("DMB_CORE_A501_TEST_DATABASE_URL")
        if not dsn:
            pytest.skip("set an isolated synthetic Core0014 test database")
        parsed = urlparse(dsn)
        assert parsed.hostname == "127.0.0.1" and parsed.port not in (54330, 54331)
        assert parsed.path.lstrip("/").startswith("dmb_core_a501_test_")
        bundle = PostgresRepositoryBundle(PostgresDatabase(dsn))
        with bundle.database.connect() as conn:
            assert (
                conn.execute(
                    "SELECT version_num FROM dungeonmind.alembic_version"
                ).fetchone()["version_num"]
                == "0014_adopted_withdrawal_v2"
            )
            assert (
                conn.execute(
                    "SELECT count(*) AS n FROM dungeonmind.world_graph_heads"
                ).fetchone()["n"]
                == 0
            )
            assert (
                conn.execute(
                    "SELECT count(*) AS n FROM dungeonmind.source_artifacts"
                ).fetchone()["n"]
                == 0
            )
        return bundle
    graph = InMemoryWorldGraphRepository()
    sources = InMemorySourceRepository()
    contributions = InMemoryContributionRepository()
    identity = InMemoryIdentityDecisionRepository()
    return SimpleNamespace(
        world_graph=graph,
        sources=sources,
        existing_world_adoptions=InMemoryExistingWorldAdoptionRepository(
            graph, sources, contributions, identity
        ),
        reviewed_world_initializations=InMemoryReviewedWorldInitializationRepository(
            graph, sources, contributions, identity
        ),
    )


def test_v4_v2_withdrawn_child_preserves_existing_consumer_reads(stores, tmp_path):
    seed_sources = _seed_sources()
    payload = _payload()
    next(e for e in payload["evidence_refs"] if e["evidence_ref_id"] == "ev:cellar")[
        "source_span_ref_id"
    ] = "span:cellar"
    control = copy.deepcopy(payload["relationships"][0])
    control["relationship_id"] = "rel:control"
    control["target_object_id"] = "obj:road-sign"
    control["assertion_metadata"] = _meta("asrt:rel:control", evidence=("ev:cellar",))
    payload["relationships"].append(control)
    ids = [
        ("src:one-recap", "srcrev:one-recap-v1"),
        ("src:one-notes", "srcrev:one-notes-v1"),
        ("src:world-lore", "srcrev:world-lore-v1"),
        ("src:player-sign", "srcrev:player-sign-v1"),
    ]
    bundle = ExistingWorldAdoptionBundleV2(
        adoption_id="adoption:consumer-fixture",
        world_id=WORLD_ID,
        source_provenance=ExistingWorldAdoptionSourceProvenanceV1(
            producer_id="dungeonmindbuddy",
            producer_revision="consumer-fixture",
            source_world_revision_id=LEGACY_BUDDY_A_REVISION,
            source_graph_payload_sha256=canonical_sha256(payload),
        ),
        graph_schema="dm_union_graph_v6",
        graph_payload=payload,
        source_artifacts=[seed_sources.get_artifact(a) for a, r in ids],
        source_revisions=[seed_sources.get_revision(r) for a, r in ids],
        contributions=[],
        identity_decisions=[],
    )
    from dungeonmind.contracts.existing_world_adoption import (
        existing_world_adoption_bundle_v2_canonical_bytes,
    )

    raw = existing_world_adoption_bundle_v2_canonical_bytes(bundle)
    graph = stores.world_graph
    adoptions = stores.existing_world_adoptions
    reader = VersionedUnionGraphSnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )
    adopt = adopt_existing_world(
        raw, adopted_at=NOW, adoption_repository=adoptions, graph_reader=reader
    )
    intent = ExistingWorldAdoptionSourceClassificationRepairIntentV1(
        world_id=WORLD_ID,
        adoption_id=adopt.adoption_id,
        repairs=[{"source_artifact_id": "src:one-notes", "clear_campaign_id": True}],
    )
    repaired = repair_existing_world_adoption_source_classification(
        raw,
        repair_intent=intent,
        repaired_at=NOW,
        adoption_repository=adoptions,
        graph_reader=reader,
        apply=True,
    )
    parent = graph.get_revision(WORLD_ID, graph.get_head(WORLD_ID).head_revision_id)
    head = parent.revision.revision_id
    cmd = AdoptedAssertionWithdrawalCommandV2(
        operation_id="withdrawal:consumer-fixture",
        world_id=WORLD_ID,
        adoption_id=adopt.adoption_id,
        expected_parent_revision_id=head,
        relationship_id="rel:tavern-cellar",
        assertion_id="asrt:rel:cellar",
        subject_object_id="obj:tavern",
        predicate="dnd5e:contains",
        object_object_id="obj:hidden-cellar",
        evidence_ref_id="ev:cellar",
        source_artifact_id="src:world-lore",
        source_revision_id="srcrev:world-lore-v1",
        source_span_ref_id="span:cellar",
        source_locator=None,
        parent_payload_sha256=canonical_sha256(parent.graph_payload),
        actor="synthetic-consumer",
        requested_at=NOW,
    )
    policy = CapabilityPolicy(
        policy_id="policy:consumer-fixture",
        graph_scope=GraphScope(
            world_id=WORLD_ID, admissibility=Admissibility.GM, revision_pin=head
        ),
        enabled_tools=[ADOPTED_ASSERTION_WITHDRAWAL_TOOL],
        tool_rules=[
            ToolCapabilityRule(
                tool_name=ADOPTED_ASSERTION_WITHDRAWAL_TOOL,
                category=CapabilityCategory.CONFIRM_COMMIT,
                allowed_effects=[CapabilityEffect.COMMIT],
            )
        ],
    )
    receipt = withdraw_adopted_assertion(
        cmd, capability_policy=policy, repository=adoptions
    )

    assert repaired.schema_version == "dm_existing_world_adoption_receipt_v4"
    assert receipt.schema_version == "dm_adopted_assertion_withdrawal_receipt_v2"
    child_id = graph.get_head(WORLD_ID).head_revision_id
    assert child_id != head
    parent_again = graph.get_revision(WORLD_ID, head)
    assert parent_again.graph_payload == parent.graph_payload
    child = graph.get_revision(WORLD_ID, child_id)
    parent_evidence = next(
        e
        for e in parent.graph_payload["evidence_refs"]
        if e["evidence_ref_id"] == "ev:cellar"
    )
    child_evidence = next(
        e
        for e in child.graph_payload["evidence_refs"]
        if e["evidence_ref_id"] == "ev:cellar"
    )
    assert (
        child_evidence == parent_evidence and child_evidence["source_locator"] is None
    )

    services = direct.direct_services_from_bundle(stores, WORLD_ID)
    request = WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=WORLD_ID,
        campaign_id="",
        scope_mode="world",
    )
    latest = direct.project_world_graph_direct(services, request)
    historical = direct.project_world_graph_direct(
        services, request.model_copy(update={"revision_pin": head})
    )
    assert {r.edge_id for r in latest.relationships} == {
        "rel:control",
        "rel:hero-tavern",
    }
    assert "rel:tavern-cellar" in {r.edge_id for r in historical.relationships}
    assert services.binding.dungeonmind_head_revision_id == child_id
    assert services.binding.legacy_buddy_revision_id == LEGACY_BUDDY_A_REVISION

    sdk_request = WorldGraphProjectionRequestV2.for_authorized(
        world_id=WORLD_ID,
        admissibility=Admissibility.GM,
        scope_mode=ScopeModeV2.WORLD_CROSS_CAMPAIGN,
        revision_pin=child_id,
    )
    support = services.retrieval.get_evidence(
        sdk_request,
        target=EvidenceTarget(kind="assertion", target_id="asrt:rel:control"),
    )
    assert support.found and {e.evidence_ref_id for e in support.evidence} == {
        "ev:cellar"
    }
    assert support.evidence[0].source_locator is None

    search = WorldGraphSearchRequest(
        schema="dmb_world_graph_search_request_v1",
        worldId=WORLD_ID,
        campaignId="",
        scopeMode="world",
        revisionPin=child_id,
        queryText="tavern",
    )
    index = direct.list_source_anchor_index_direct_v2(
        services, search, revision_id=child_id
    )
    assert index.status == "complete"
    assert "ev:cellar" in {pin.evidence_ref_id for pin in index.source_pins}
    pin = next(pin for pin in index.source_pins if pin.evidence_ref_id == "ev:tavern")
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus/world_lore.md").write_text(ANCHOR_CONTENT)
    source = direct.read_source_anchor_direct_v2(
        services,
        WorldGraphSourceAnchorReadRequest(
            schema="dmb_world_graph_source_anchor_read_request_v1",
            worldId=WORLD_ID,
            campaignId="",
            scopeMode="world",
            revisionPin=child_id,
            anchorId=pin.anchor_id,
        ),
        repo_root=tmp_path,
    )
    assert source.result.content == ANCHOR_CONTENT.rstrip("\n")
    assert source.source_revision_id == "srcrev:one-recap-v1"
    assert source.graph_revision == child_id
    assert source.source_revision_sha256 == ANCHOR_CONTENT_DIGEST
