"""Current/history partition and v2 history proofs for the Eldyrwild adoption bundle."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import subprocess

import pytest

from dungeonmind.contracts.evidence import EvidenceRef, EvidenceRole, SourceDomain

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
    ALIAS_PACKAGE_LOCKED_FIXTURE_SHA256,
    ALIAS_PACKAGE_PROOF_SHA256,
    BUDDY_BASE_SHA,
    EXPECTED_CURRENT_SEMANTIC,
    EXPECTED_HISTORY_ONLY,
    EXPECTED_MECHANICS,
    EXPECTED_RAW_EDGE_COUNT,
    FALSE_STOP_EDGE_IDS,
    HIRES_CORRECTION_ARTIFACT_ID,
    HIRES_CORRECTION_RAW_ARTIFACT_SHA256,
    HIRES_CORRECTION_SOURCE_PAYLOAD_SHA256,
    PRODUCER_REVISION,
    EldyrwildAdoptionBundleV2Error,
    assert_contribution_evidence_identity_closed,
    build_eldyrwild_existing_world_adoption_bundle_v2,
    contribution_evidence_v1_binding_payload,
    evaluate_false_stop_edges,
    exported_contribution_evidence_ref_id,
    partition_raw_stored_edges,
    raw_buddy_evidence_ref_id,
    raw_edges_would_create_vocabulary_blockers,
    read_source_revision_body,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    resolve_buddy_predicate_mapping_v4,
)
from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
    DEFERRED_RESIDUAL_EDGE_IDS,
    KIND_REPAIR_SPECS,
    STAGE_B_REMAINING_RESIDUAL_EDGE_IDS,
)
from dungeonmind.application.existing_world_adoption import parse_existing_world_adoption_bundle
from dungeonmind.application.graph_snapshot import VersionedUnionGraphSnapshotReader
from dungeonmind.contracts.existing_world_adoption import EXISTING_WORLD_ADOPTION_BUNDLE_V2_SCHEMA
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_vocabulary import load_builtin_v3_descriptor
from graph_memory.world_supergraph.contribution_store import list_contribution_records

ROOT = world_graph_root()
REPO = repo_root()
WORLD_ID = "eldyrwild"
REV = "rev:0c644e56b45bcaac709012206e3e41c2"
HIRES_EDGE_ID = "edge:pc:ephanna:hires:node:thrin-branchborn"
REPORTS_THREAT_EDGE_ID = (
    "edge:faction:town-guards-mireward-gate:reports_threat_in:"
    "mystery:session25:west-wall-screaming-and-dark-shapes-below"
)


@pytest.fixture(scope="module")
def loaded_store():
    manifest, store = _load_exact_buddy_revision(root=ROOT, world_id=WORLD_ID, revision_id=REV)
    return manifest, store


@pytest.fixture(scope="module")
def built_bundle():
    digest_before = snapshot_world_graph_tree_digest(ROOT, WORLD_ID)
    built = build_eldyrwild_existing_world_adoption_bundle_v2(root=ROOT, repo=REPO)
    digest_after = snapshot_world_graph_tree_digest(ROOT, WORLD_ID)
    assert digest_before == digest_after
    return built


def test_raw_current_mechanics_history_partition(loaded_store) -> None:
    _manifest, store = loaded_store
    partition = partition_raw_stored_edges(store)
    current = set(partition.current_semantic_ids)
    mechanics = set(partition.mechanics_ids)
    history = set(partition.history_ids)
    raw = set(store.edges)
    assert len(raw) == EXPECTED_RAW_EDGE_COUNT
    assert len(current) == EXPECTED_CURRENT_SEMANTIC
    assert len(mechanics) == EXPECTED_MECHANICS
    assert len(history) == EXPECTED_HISTORY_ONLY
    assert current & mechanics == set()
    assert current & history == set()
    assert mechanics & history == set()
    assert current | mechanics | history == raw


def test_prior_false_stop_sixteen_are_history_only(loaded_store) -> None:
    _manifest, store = loaded_store
    contributions = list_contribution_records(ROOT, WORLD_ID)
    reports = evaluate_false_stop_edges(store, contributions=contributions)
    partition = partition_raw_stored_edges(store)
    assert len(reports) == 16
    assert {item.edge_id for item in reports} == set(FALSE_STOP_EDGE_IDS)
    assert all(item.raw_stored for item in reports)
    assert all(item.current_semantic is False for item in reports)
    assert all(item.final_disposition == "SOURCE_MIGRATION_HISTORY" for item in reports)
    assert set(FALSE_STOP_EDGE_IDS) <= set(partition.history_ids)
    assert set(FALSE_STOP_EDGE_IDS).isdisjoint(partition.current_semantic_ids)


def test_raw_store_scan_is_the_false_positive_that_caused_the_stop(loaded_store) -> None:
    _manifest, store = loaded_store
    blockers = raw_edges_would_create_vocabulary_blockers(store)
    assert set(FALSE_STOP_EDGE_IDS) <= set(blockers)
    assert resolve_buddy_predicate_mapping_v4("hires") is None
    assert resolve_buddy_predicate_mapping_v4("reports_threat_in") is None
    partition = partition_raw_stored_edges(store)
    assert HIRES_EDGE_ID in partition.history_ids
    assert REPORTS_THREAT_EDGE_ID in partition.history_ids
    assert HIRES_EDGE_ID not in partition.current_semantic_ids


def test_residual_progression_nine_to_five_to_zero(built_bundle) -> None:
    built = built_bundle
    kind_repair_ids = {
        edge_id
        for spec in KIND_REPAIR_SPECS
        for edge_id in spec["affected_deferred_edge_ids"]
    }
    assert built.residual_before_projections == 9
    assert set(DEFERRED_RESIDUAL_EDGE_IDS) == kind_repair_ids | set(
        STAGE_B_REMAINING_RESIDUAL_EDGE_IDS
    )
    assert built.represented_after_kind_repair == 318
    assert built.residual_after_kind_repair == 5
    assert {item.edge_id for item in built.mapped_relationships if item.resolution == "kind_repair"} == kind_repair_ids
    assert {
        item.edge_id for item in built.mapped_relationships if item.resolution == "aspect_selection"
    } == set(STAGE_B_REMAINING_RESIDUAL_EDGE_IDS)
    assert built.current_unrepresentable_count == 0
    assert built.v6_relationship_count == EXPECTED_CURRENT_SEMANTIC


def test_historical_hires_omitted_from_graph_but_retained_in_v2_history(
    loaded_store, built_bundle
) -> None:
    _manifest, store = loaded_store
    built = built_bundle
    assert HIRES_EDGE_ID in store.edges
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert HIRES_EDGE_ID not in graph_ids
    assert HIRES_EDGE_ID not in set(built.partition.current_semantic_ids)
    hires_assertion = None
    hires_correction = None
    for contribution in built.bundle.contributions:
        for assertion in contribution.assertions:
            if assertion.predicate == "hires" and assertion.subject_object_id == "pc:ephanna":
                hires_assertion = assertion
        for correction in contribution.assertion_corrections:
            if hires_assertion and correction.target_assertion_id == hires_assertion.assertion_id:
                hires_correction = correction
    assert hires_assertion is not None
    assert hires_correction is not None
    assert hires_correction.correction_kind.value == "contradicts"


def test_session25_reports_threat_in_is_history_with_correction(built_bundle) -> None:
    built = built_bundle
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert REPORTS_THREAT_EDGE_ID not in graph_ids
    report = next(item for item in built.false_stop_reports if item.edge_id == REPORTS_THREAT_EDGE_ID)
    assert report.current_support_state == "contradicted"
    assert report.correction_contribution_ids
    assert "contradicts" in report.correction_kinds or "contradicts_and_replaces" in report.correction_kinds


def test_parser_accepts_canonical_v2_bundle(built_bundle) -> None:
    built = built_bundle
    descriptor = load_builtin_v3_descriptor()
    parsed = parse_existing_world_adoption_bundle(
        built.canonical_bytes,
        graph_reader=VersionedUnionGraphSnapshotReader(
            StaticSemanticProfileRegistry([descriptor])
        ),
    )
    assert parsed.schema_version == EXISTING_WORLD_ADOPTION_BUNDLE_V2_SCHEMA
    assert parsed.graph_schema == "dm_union_graph_v6"
    assert len(parsed.contributions) == built.contribution_count
    assert parsed.graph_payload["relationship_endpoint_aspect_schema"] == (
        "dm_relationship_endpoint_aspect_v1"
    )


def test_history_edge_with_unknown_predicate_does_not_block_vocabulary(built_bundle) -> None:
    built = built_bundle
    assert built.current_unrepresentable_count == 0
    graph_predicates = {row["predicate"] for row in built.bundle.graph_payload["relationships"]}
    assert "dnd5e:hires" not in graph_predicates
    assert "hires" not in graph_predicates
    assert "reports_threat_in" not in graph_predicates


def test_correction_targets_exist_in_bundled_history(built_bundle) -> None:
    built = built_bundle
    contributions = {item.contribution_id: item for item in built.bundle.contributions}
    for contribution in built.bundle.contributions:
        assertion_ids = {item.assertion_id for item in contribution.assertions}
        for correction in contribution.assertion_corrections:
            target = contributions[correction.target_contribution_id]
            target_ids = {item.assertion_id for item in target.assertions}
            assert correction.target_assertion_id in target_ids
            if correction.replacement_assertion_id is not None:
                assert correction.replacement_assertion_id in assertion_ids


def test_source_derived_candidate_is_preserved(built_bundle) -> None:
    kinds = [
        assertion.epistemic_kind.value
        for contribution in built_bundle.bundle.contributions
        for assertion in contribution.assertions
    ]
    assert "source_derived_candidate" in kinds
    assert kinds.count("source_derived_candidate") == 1389


def test_mechanics_remain_outside_generic_relationships(built_bundle) -> None:
    built = built_bundle
    assert len(built.mechanics_proofs) == EXPECTED_MECHANICS
    assert all(item.disposition == "A" for item in built.mechanics_proofs)
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert set(built.partition.mechanics_ids).isdisjoint(graph_ids)


def test_graph_contains_only_current_semantic_relationships(built_bundle) -> None:
    built = built_bundle
    graph_ids = {row["relationship_id"] for row in built.bundle.graph_payload["relationships"]}
    assert graph_ids == set(built.partition.current_semantic_ids)
    assert graph_ids.isdisjoint(built.partition.history_ids)
    assert graph_ids.isdisjoint(built.partition.mechanics_ids)
    assert set(built.partition.current_semantic_ids).isdisjoint(built.partition.history_ids)


def test_producer_does_not_import_adoption_persistence() -> None:
    source = Path(
        "apps/live_control_server/integrations/dungeonmind_kernel/"
        "eldyrwild_existing_world_adoption_bundle_v2.py"
    ).read_text(encoding="utf-8")
    assert "adopt_existing_world" not in source
    assert "ExistingWorldAdoptionCommandV2" not in source


def test_contribution_source_revision_is_first_class_not_diagnostics(built_bundle) -> None:
    built = built_bundle
    revision_ids = {item.source_revision_id for item in built.bundle.source_revisions}
    artifact_ids = {item.source_artifact_id for item in built.bundle.source_artifacts}
    assert all(item.current_revision_id for item in built.bundle.source_artifacts)
    assert all(item.uri for item in built.bundle.source_artifacts)
    assert all(item.locator for item in built.bundle.source_revisions)
    assert "producer_reconstruction" not in json.dumps(
        [item.lineage for item in built.bundle.source_artifacts], ensure_ascii=True
    )
    for contribution in built.bundle.contributions:
        assert contribution.source_revision_id
        assert contribution.source_revision_id in revision_ids
        assert contribution.source_artifact_id in artifact_ids
        assert "buddy_source_revision_id" not in contribution.diagnostics
        assert "buddy_assertion_source_revision_id" not in contribution.diagnostics
        for assertion in contribution.assertions:
            assert assertion.source_revision_id
            assert assertion.source_revision_id in revision_ids
            assert assertion.source_artifact_id in artifact_ids


def test_hires_correction_keeps_graph_native_source_revision(built_bundle) -> None:
    built = built_bundle
    correction = next(
        item
        for item in built.bundle.contributions
        if item.source_artifact_id == HIRES_CORRECTION_ARTIFACT_ID
    )
    assert (
        correction.source_revision_id
        == "correction:eldyrwild:session25-ephanna-thrin-false-hires-v1"
    )
    revision = next(
        item
        for item in built.bundle.source_revisions
        if item.source_revision_id == correction.source_revision_id
    )
    artifact = next(
        item
        for item in built.bundle.source_artifacts
        if item.source_artifact_id == correction.source_artifact_id
    )
    assert revision.source_artifact_id == correction.source_artifact_id
    assert revision.content_sha256 == HIRES_CORRECTION_RAW_ARTIFACT_SHA256
    assert revision.locator.startswith("graph-data://")
    assert revision.locator.endswith("session25-ephanna-thrin-false-hires-v1.json")
    assert artifact.uri == revision.locator
    assert (
        artifact.lineage.get("buddy_source_payload_sha256")
        == HIRES_CORRECTION_SOURCE_PAYLOAD_SHA256
    )
    assert HIRES_CORRECTION_SOURCE_PAYLOAD_SHA256 != HIRES_CORRECTION_RAW_ARTIFACT_SHA256


def test_source_revision_content_sha256_hashes_located_body(built_bundle) -> None:
    built = built_bundle
    resolved = 0
    for revision in built.bundle.source_revisions:
        locator = revision.locator
        assert locator
        body = read_source_revision_body(locator, repo=REPO, world_root=ROOT)
        if locator.startswith("graph-data://"):
            assert body is not None
        if body is None:
            continue
        resolved += 1
        assert hashlib.sha256(body).hexdigest() == revision.content_sha256
    assert resolved > 0
    by_artifact: dict[str, set[str]] = {}
    for revision in built.bundle.source_revisions:
        by_artifact.setdefault(revision.source_artifact_id, set()).add(revision.content_sha256)
    assert all(len(digests) == 1 for digests in by_artifact.values())


def test_captain_and_thrin_aliases_use_sealed_587_authority(built_bundle) -> None:
    built = built_bundle
    objects = {item["object_id"]: item for item in built.bundle.graph_payload["objects"]}
    captain = objects["node:captain-lysandra-ironveil"]["aliases"]
    thrin = objects["node:thrin-branchborn"]["aliases"]
    assert len(captain) == 1
    assert len(thrin) == 1
    captain_meta = captain[0]["assertion_metadata"]
    thrin_meta = thrin[0]["assertion_metadata"]
    assert captain[0]["value"] == "Captain"
    assert thrin[0]["value"] == "Thrin Branchborn"
    assert captain_meta["campaign_scope"] == "longmont-c2"
    assert thrin_meta["campaign_scope"] == "longmont-c2"
    assert captain_meta["epistemic_kind"] == "source_derived_candidate"
    assert thrin_meta["epistemic_kind"] == "source_derived_candidate"
    assert captain_meta["session_refs"] == ["session-25"]
    assert thrin_meta["session_refs"] == ["session-25"]
    assert captain_meta["assertion_id"] == "assertion:cutover-alias:efac2be8dcac08b80b6a71ee"
    assert thrin_meta["assertion_id"] == "assertion:cutover-alias:ed979aedbe0b7885e4ef1471"
    refs = {(item.schema_, item.identifier, item.sha256) for item in built.bundle.source_provenance.authority_refs}
    assert (
        "dmb_cutover_alias_assertion_package_after_shadow_alias_remove_v1",
        "eldyrwild-cutover-alias-assertion-package-after-shadow-alias-remove-v1",
        ALIAS_PACKAGE_LOCKED_FIXTURE_SHA256,
    ) in refs
    assert ALIAS_PACKAGE_PROOF_SHA256
    other_alias_nodes = [
        item["object_id"]
        for item in built.bundle.graph_payload["objects"]
        if item["aliases"]
        and item["object_id"]
        not in {"node:captain-lysandra-ironveil", "node:thrin-branchborn"}
    ]
    assert other_alias_nodes == []


def test_producer_revision_identifies_producer_not_dispatch_base(built_bundle) -> None:
    built = built_bundle
    assert built.bundle.source_provenance.producer_revision == PRODUCER_REVISION
    assert PRODUCER_REVISION != BUDDY_BASE_SHA
    assert len(PRODUCER_REVISION) == 40


def test_shared_buddy_revision_tokens_are_scoped_per_artifact(built_bundle) -> None:
    built = built_bundle
    revision_ids = [item.source_revision_id for item in built.bundle.source_revisions]
    assert len(revision_ids) == len(set(revision_ids))
    scoped = [item for item in revision_ids if "::" in item]
    assert scoped
    assert all(item.startswith("sha256:") or item.startswith("bundle-revision:") for item in scoped)
    for contribution in built.bundle.contributions:
        if "::" in (contribution.source_revision_id or ""):
            artifact_id = contribution.source_artifact_id
            assert contribution.source_revision_id.endswith(f"::{artifact_id}")


PRE_FIX_BUNDLE_BLOB = "14cbe3394cd622fd58f321da1a6dfbcd6a3b97d3"
PRE_FIX_INTRA_CONTRIBUTION_COLLISIONS = 15
PRE_FIX_CONFLICTING_RAW_EVIDENCE_IDS = 57
PRE_FIX_AFFECTED_CONTRIBUTIONS = frozenset(
    {
        "contribution:2807888820d76c78",
        "contribution:400ffb3a229f2b13",
        "contribution:4e0276b24db50ee5",
        "contribution:55047c991813532c",
        "contribution:66f9834c455c7818",
        "contribution:86ea8a3d97dd18cc",
        "contribution:8b046da9ec0f4275",
        "contribution:97f5ef69b6c6d14e",
        "contribution:a5f8e745364e182c",
        "contribution:a7ba15b146d7af1f",
        "contribution:b8d6018f51828276",
        "contribution:cc2574b7d2d274a9",
        "contribution:d3d244474789879c",
        "contribution:dfadb94646dd9d3c",
        "contribution:f43a2446902be8a9",
    }
)
WITNESS_RAW_EVIDENCE_ID = (
    "evidence:artifact:recap:longmont-c1:session-10:session-10:recap:paragraph:002"
)
WITNESS_CONTRIBUTION_ID = "contribution:2807888820d76c78"
WITNESS_SOURCE_REVISIONS = frozenset(
    {
        "sha256:04e6b145f64e4c2788f1afbb8a820b9be1222039471e343419bf247fbc6b96bf",
        "sha256:f0f49045df06f7baf61aa9c43f3739d16483eeb20ac8ed1bbf29f8209474af25",
    }
)


def _pre_fix_bundle() -> dict:
    raw = subprocess.check_output(
        ["git", "cat-file", "-p", PRE_FIX_BUNDLE_BLOB],
        cwd=REPO,
    )
    assert hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() == (
        PRE_FIX_BUNDLE_BLOB
    )
    return json.loads(raw.decode("utf-8"))


def _intra_contribution_evidence_collisions(bundle: dict) -> tuple[set[str], set[str]]:
    contributions: set[str] = set()
    raw_ids: set[str] = set()
    for contribution in bundle["contributions"]:
        by_id: dict[str, set[str]] = {}
        for assertion in contribution["assertions"]:
            for ref in assertion.get("evidence_refs") or []:
                payload = json.dumps(ref, sort_keys=True, separators=(",", ":"))
                by_id.setdefault(ref["evidence_ref_id"], set()).add(payload)
        for evidence_id, payloads in by_id.items():
            if len(payloads) > 1:
                contributions.add(contribution["contribution_id"])
                raw_ids.add(evidence_id)
    return contributions, raw_ids


def _evidence_ref(
    *,
    evidence_ref_id: str,
    source_revision_id: str | None,
    source_artifact_id: str = "artifact:recap:example",
    can_highlight_span: bool = False,
) -> EvidenceRef:
    return EvidenceRef(
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        source_domain=SourceDomain.SESSION_RECAP,
        evidence_role=EvidenceRole.SUPPORT,
        can_open_source=True,
        can_highlight_span=can_highlight_span,
        locator=None,
        uri=None,
    )


def test_pre_fix_bundle_reproduces_fifteen_contribution_evidence_collisions() -> None:
    bundle = _pre_fix_bundle()
    contributions, raw_ids = _intra_contribution_evidence_collisions(bundle)
    assert contributions == PRE_FIX_AFFECTED_CONTRIBUTIONS
    assert len(contributions) == PRE_FIX_INTRA_CONTRIBUTION_COLLISIONS
    assert len(raw_ids) == PRE_FIX_CONFLICTING_RAW_EVIDENCE_IDS
    assert WITNESS_RAW_EVIDENCE_ID in raw_ids
    witness_revs = {
        ref["source_revision_id"]
        for contribution in bundle["contributions"]
        if contribution["contribution_id"] == WITNESS_CONTRIBUTION_ID
        for assertion in contribution["assertions"]
        for ref in assertion.get("evidence_refs") or []
        if ref["evidence_ref_id"] == WITNESS_RAW_EVIDENCE_ID
    }
    assert witness_revs == WITNESS_SOURCE_REVISIONS


def test_witness_source_revisions_export_distinct_durable_evidence_ids(built_bundle) -> None:
    contribution = next(
        item
        for item in built_bundle.bundle.contributions
        if item.contribution_id == WITNESS_CONTRIBUTION_ID
    )
    by_revision: dict[str, set[str]] = {}
    for assertion in contribution.assertions:
        for ref in assertion.evidence_refs:
            if raw_buddy_evidence_ref_id(ref.evidence_ref_id) != WITNESS_RAW_EVIDENCE_ID:
                continue
            assert ref.source_revision_id in WITNESS_SOURCE_REVISIONS
            by_revision.setdefault(ref.source_revision_id, set()).add(ref.evidence_ref_id)
            assert ref.evidence_ref_id.startswith(WITNESS_RAW_EVIDENCE_ID + ":dmv1:")
    assert set(by_revision) == WITNESS_SOURCE_REVISIONS
    exported = [next(iter(ids)) for ids in by_revision.values()]
    assert len(set(exported)) == 2


def test_final_bundle_contribution_evidence_ids_are_payload_unique(built_bundle) -> None:
    assert_contribution_evidence_identity_closed(built_bundle.bundle.contributions)
    payloads: dict[str, str] = {}
    raw_ids_in_affected: set[str] = set()
    for contribution in built_bundle.bundle.contributions:
        for assertion in contribution.assertions:
            for ref in assertion.evidence_refs:
                dumped = json.dumps(ref.model_dump(mode="json"), sort_keys=True)
                prior = payloads.get(ref.evidence_ref_id)
                if prior is None:
                    payloads[ref.evidence_ref_id] = dumped
                else:
                    assert prior == dumped
                if contribution.contribution_id in PRE_FIX_AFFECTED_CONTRIBUTIONS:
                    raw_ids_in_affected.add(raw_buddy_evidence_ref_id(ref.evidence_ref_id))
    assert PRE_FIX_AFFECTED_CONTRIBUTIONS <= {
        item.contribution_id for item in built_bundle.bundle.contributions
    }
    assert WITNESS_RAW_EVIDENCE_ID in raw_ids_in_affected


def test_contribution_evidence_identity_helper_is_stable_and_discriminating() -> None:
    raw_a = "evidence:artifact:recap:example:paragraph:001"
    raw_b = "evidence:artifact:recap:example:paragraph:002"
    first = _evidence_ref(evidence_ref_id="tmp", source_revision_id="sha256:" + "aa" * 32)
    same = _evidence_ref(evidence_ref_id="other-tmp", source_revision_id="sha256:" + "aa" * 32)
    changed_rev = _evidence_ref(
        evidence_ref_id="tmp",
        source_revision_id="sha256:" + "bb" * 32,
    )
    changed_flag = _evidence_ref(
        evidence_ref_id="tmp",
        source_revision_id="sha256:" + "aa" * 32,
        can_highlight_span=True,
    )
    id_same = exported_contribution_evidence_ref_id(raw_a, first)
    id_same_again = exported_contribution_evidence_ref_id(raw_a, same)
    reversed_binding = {
        "uri": None,
        "locator": None,
        "can_highlight_span": False,
        "can_open_source": True,
        "evidence_role": "support",
        "source_domain": "session_recap",
        "source_revision_id": "sha256:" + "aa" * 32,
        "source_artifact_id": "artifact:recap:example",
        "schema_version": "dm_evidence_ref_v1",
    }
    id_reversed = exported_contribution_evidence_ref_id(raw_a, reversed_binding)
    assert id_same == id_same_again == id_reversed
    assert exported_contribution_evidence_ref_id(raw_a, changed_rev) != id_same
    assert exported_contribution_evidence_ref_id(raw_a, changed_flag) != id_same
    assert exported_contribution_evidence_ref_id(raw_b, first) != id_same
    assert raw_buddy_evidence_ref_id(id_same) == raw_a
    digest = id_same.rsplit(":dmv1:", 1)[1]
    assert len(digest) == 64
    assert digest == hashlib.sha256(
        json.dumps(
            contribution_evidence_v1_binding_payload(first),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def test_contribution_evidence_preflight_stops_on_payload_collision() -> None:
    shared_id = "evidence:collision:dmv1:" + ("ab" * 32)
    first = _evidence_ref(evidence_ref_id=shared_id, source_revision_id="sha256:" + "aa" * 32)
    second = _evidence_ref(evidence_ref_id=shared_id, source_revision_id="sha256:" + "bb" * 32)
    contributions = [
        SimpleNamespace(
            contribution_id="contribution:left",
            assertions=[SimpleNamespace(assertion_id="assertion:left", evidence_refs=[first])],
        ),
        SimpleNamespace(
            contribution_id="contribution:right",
            assertions=[SimpleNamespace(assertion_id="assertion:right", evidence_refs=[second])],
        ),
    ]
    with pytest.raises(EldyrwildAdoptionBundleV2Error, match="conflicting evidence_ref"):
        assert_contribution_evidence_identity_closed(contributions)  # type: ignore[arg-type]


def test_contribution_evidence_revisions_are_not_nulled(built_bundle) -> None:
    pre_fix = _pre_fix_bundle()
    pre_populated = 0
    for contribution in pre_fix["contributions"]:
        for assertion in contribution["assertions"]:
            for ref in assertion.get("evidence_refs") or []:
                if ref.get("source_revision_id"):
                    pre_populated += 1
    post_populated = 0
    for contribution in built_bundle.bundle.contributions:
        assert contribution.source_revision_id
        for assertion in contribution.assertions:
            assert assertion.source_revision_id
            for ref in assertion.evidence_refs:
                if ref.source_revision_id:
                    post_populated += 1
    assert post_populated == pre_populated
    assert post_populated > 0


def test_repeated_generation_is_byte_identical() -> None:
    first = build_eldyrwild_existing_world_adoption_bundle_v2(root=ROOT, repo=REPO)
    second = build_eldyrwild_existing_world_adoption_bundle_v2(root=ROOT, repo=REPO)
    assert first.canonical_bytes == second.canonical_bytes
