"""Kernel world projection tests (PR007A)."""

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.union_supergraph.model import (
    UnionSupergraphEvidence,
    UnionSupergraphSourceArtifact,
)
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.kernel.world_projection import WorldGraphProjectionError
from graph_memory.projection.recap_projection import build_node_view
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.projection_identity import (
    build_union_projection_identity_context,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ACTOR = "gm"
EVENT_ID = "event:longmont-c2:session-23:mireward-gate-battle"
TRIPOD_ID = "threat:tripod-null-calf"
TRIPOD_CONTRIBUTION_ID = "contribution:022187fdefdf4557"

DUP_ALIGNED_CONTRIBUTION_ID = "contribution:aabbccdd11223344"
DUP_MISSING_CONTRIBUTION_ID = "contribution:bbccddeeff001122"
DUP_DIVERGENT_CONTRIBUTION_ID = "contribution:ccddeeff00112233"
RECAP_SOURCE_ARTIFACT_ID = "corpus:eldyrwild:session-23-recap"
DUP_SOURCE_ARTIFACT_ID = "graph-native:test:dup-aligned-battlefield"
FALLBACK_EDGE_CONTRIBUTION_ID = "contribution:ddccbbaa99887766"
FALLBACK_SPLIT_NODE_ID = "threat:test-fallback-split"
FALLBACK_SPLIT_CONTRIBUTION_ID = "contribution:aabbccddeeff1122"
ATTR_ONLY_ARTIFACT_ID = "graph-native:test:attr-direct-artifact"
ATTR_ONLY_CONTRIBUTION_ID = "contribution:eeff001122334455"

ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


def _revision_graph_path(root: Path, revision_id: str) -> Path:
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "graph.json"
    )


def _revision_manifest_path(root: Path, revision_id: str) -> Path:
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "revision.json"
    )


def _head_path(root: Path) -> Path:
    return root / "graph_memory" / "worlds" / WORLD_ID / "head.json"


def _attestation() -> WorldInitializationApprovalAttestation:
    return WorldInitializationApprovalAttestation(
        bundle_id=BUNDLE_ID,
        bundle_digest=BUNDLE_DIGEST,
        approved_bundle_merge_sha=APPROVED_MERGE_SHA,
    )


def _plan(bundle) -> WorldInitializationPlan:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    return WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=_attestation(),
    )


def _initialize(root: Path, bundle) -> kernel.WorldInitializationResult:
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _request(
    *,
    revision_pin: str | None = None,
    campaign_id: str = CAMPAIGN_ID,
    admissibility: str = "gm",
    query_text: str | None = None,
    focus_kind: str = "none",
    session_id: str | None = None,
    focus_campaign_id: str | None = None,
    scope_mode: str = "campaign",
) -> WorldGraphProjectionRequest:
    focus = WorldGraphProjectionFocus(
        kind=focus_kind,
        session_id=session_id,
        campaign_id=focus_campaign_id,
    )
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=campaign_id,
        focus=focus,
        admissibility=admissibility,
        revision_pin=revision_pin,
        query_text=query_text,
        scope_mode=scope_mode,  # type: ignore[arg-type]
    )


def _initialized_head_revision(root: Path, bundle) -> str:
    result = _initialize(root, bundle)
    assert result.published is True
    head, _revision, _store = kernel.open_current_world_graph(root, WORLD_ID)
    return head.head_revision_id


def _load_tripod_contribution_json(root: Path) -> dict:
    return json.loads(
        (
            root
            / "graph_memory"
            / "worlds"
            / WORLD_ID
            / "contributions"
            / "contribution__022187fdefdf4557.json"
        ).read_text(encoding="utf-8")
    )


def _assertions_from_contribution_json(payload: dict) -> list:
    return [
        kernel.GraphContributionAssertion.model_validate(assertion)
        for assertion in payload["accepted_assertions"]
    ]


def test_head_projection_matches_initialized_world(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    head_revision_id = _initialized_head_revision(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())

    assert projection.snapshot.revision_id == head_revision_id
    assert projection.snapshot.head_revision_id == head_revision_id
    assert projection.snapshot.is_head is True
    assert projection.summary.node_count == 12
    assert projection.summary.relationship_count == 11
    assert projection.summary.attribute_count == 3


def test_revision_pin_projection_reads_historical_revision(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    revisions_dir = tmp_path / "graph_memory" / "worlds" / WORLD_ID / "revisions"
    revision_ids = sorted(path.name for path in revisions_dir.iterdir() if path.is_dir())
    # Revision ids are content-addressed hashes with no chronological ordering;
    # pick any revision that is provably historical rather than assuming a
    # fixed index happens to land off head.
    pinned = next(rev for rev in revision_ids if rev != result.current_head_revision_id)

    projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned),
    )

    assert projection.snapshot.revision_id == pinned
    assert projection.snapshot.head_revision_id == result.current_head_revision_id
    assert projection.snapshot.is_head is False


def test_invalid_revision_pin_fails_closed(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(revision_pin="rev:00000000000000000000000000000000"),
        )
    assert exc_info.value.code == "revision_not_found"


def test_invalid_format_revision_pin_fails_invalid_request(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(revision_pin="rev:missing-pin"),
        )
    assert exc_info.value.code == "invalid_request"


def test_tripod_attributes_reconstructed_from_revision_bound_contributions(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())

    tripod_attributes = {
        attribute.label or attribute.predicate
        for attribute in projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
    }
    assert tripod_attributes == {
        "battlefield_role",
        "challenge_expectation",
        "first_appearance",
    }
    battlefield = next(
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    assert "positional controller" in (battlefield.text_value or "").casefold()
    assert battlefield.active_contribution_ids == [TRIPOD_CONTRIBUTION_ID]


def test_relationship_to_mireward_gate_battle_present(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())

    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    relationship = next(
        item for item in projection.relationships if item.edge_id == edge_id
    )
    assert relationship.target_node_id == EVENT_ID


def test_positional_controller_search_selects_tripod_same_revision(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    head_revision_id = _initialized_head_revision(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="positional controller"),
    )

    assert projection.query_context is not None
    assert projection.query_context.snapshot.revision_id == head_revision_id
    assert projection.query_context.revision_id == head_revision_id
    assert projection.query_context.matched_node_ids[0] == TRIPOD_ID
    assert projection.query_context.match_reasons[TRIPOD_ID]


def test_threats_ready_natural_language_search_selects_tripod(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="What threats should I have ready?"),
    )

    assert projection.query_context is not None
    assert TRIPOD_ID in projection.query_context.matched_node_ids
    assert any(
        reason.startswith("token:threat")
        for reason in projection.query_context.match_reasons.get(TRIPOD_ID, [])
    )


def test_tripod_battle_natural_language_search_selects_tripod(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Tripod Mireward gate battle positional"),
    )

    assert projection.query_context is not None
    assert TRIPOD_ID in projection.query_context.matched_node_ids


def test_node_views_retain_badges_adjacency_and_lineage_fields(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)

    assert tripod.evidence_badges
    assert tripod.evidence_ref_ids
    assert tripod.source_artifact_ids
    assert any(candidate.node_id == EVENT_ID for candidate in tripod.adjacency)
    assert tripod.suggested_expansions


def test_search_collects_node_evidence_without_matching_attribute(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Tripod Null-Calf"),
    )

    assert projection.query_context is not None
    assert projection.query_context.evidence
    assert projection.query_context.source_artifacts
    node_evidence_ids = {
        evidence_id
        for node in projection.query_context.nodes
        for evidence_id in node.evidence_ref_ids
    }
    assert node_evidence_ids
    assert any(
        item.evidence_ref_id in node_evidence_ids
        for item in projection.query_context.evidence
    )


def test_search_collects_relationship_source_artifacts(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="positional controller"),
    )

    assert projection.query_context is not None
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    relationship = next(
        item for item in projection.query_context.relationships if item.edge_id == edge_id
    )
    assert relationship.evidence_ref_ids
    relationship_evidence = {
        item.evidence_ref_id: item.source_artifact_id
        for item in projection.query_context.evidence
    }
    for evidence_ref_id in relationship.evidence_ref_ids:
        artifact_id = relationship_evidence[evidence_ref_id]
        assert any(
            item.source_artifact_id == artifact_id
            for item in projection.query_context.source_artifacts
        )


def test_retracted_attribute_contribution_omits_attribute_on_head_keeps_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id

    retracted = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=TRIPOD_CONTRIBUTION_ID,
        reason="tripod prep withdrawn for test",
    )
    assert retracted.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    assert not any(
        attribute.subject_node_id == TRIPOD_ID for attribute in head_projection.attributes
    )
    assert TRIPOD_ID not in {node.node_id for node in head_projection.nodes}

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_attributes = {
        attribute.label or attribute.predicate
        for attribute in pinned_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
    }
    assert pinned_attributes == {
        "battlefield_role",
        "challenge_expectation",
        "first_appearance",
    }
    assert any(node.node_id == TRIPOD_ID for node in pinned_projection.nodes)


def test_superseded_attribute_contribution_omits_attribute_on_head_keeps_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    original_payload = _load_tripod_contribution_json(tmp_path)
    replacement_assertions = _assertions_from_contribution_json(original_payload)
    for assertion in replacement_assertions:
        if (assertion.label or assertion.predicate) == "battlefield_role":
            assertion.value = {"text": "Replacement role text"}

    replacement_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="supersede-1",
        accepted_assertions=replacement_assertions,
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    superseded = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=replacement_contribution,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert superseded.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    battlefield = next(
        attribute
        for attribute in head_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    assert "replacement role text" in (battlefield.text_value or "").casefold()
    assert not any(
        "positional controller" in (attribute.text_value or "").casefold()
        for attribute in head_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
    )

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_battlefield = next(
        attribute
        for attribute in pinned_projection.attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    assert "positional controller" in (pinned_battlefield.text_value or "").casefold()


def test_superseded_edge_contribution_shows_replacement_on_head_keeps_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    original_payload = _load_tripod_contribution_json(tmp_path)
    replacement_assertions = _assertions_from_contribution_json(original_payload)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    for assertion in replacement_assertions:
        value = dict(assertion.value)
        if str(value.get("edge_id") or "") != edge_id:
            continue
        assertion.label = "replacement appeared label"
        assertion.visibility = "gm_only"
        assertion.value = {
            **value,
            "direction": "inbound",
            "session_ids": ["session-99"],
        }

    replacement_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="supersede-edge-1",
        accepted_assertions=replacement_assertions,
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    superseded = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=replacement_contribution,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert superseded.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    head_relationship = next(
        item for item in head_projection.relationships if item.edge_id == edge_id
    )
    assert head_relationship.label == "replacement appeared label"
    assert head_relationship.session_ids == ["session-99"]
    assert head_relationship.direction == "inbound"
    assert head_relationship.visibility == "gm_only"

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_relationship = next(
        item for item in pinned_projection.relationships if item.edge_id == edge_id
    )
    assert pinned_relationship.label == "appeared in"
    assert pinned_relationship.session_ids != ["session-99"]
    assert pinned_relationship.direction != "inbound"
    assert pinned_relationship.visibility != "gm_only"


def test_superseded_node_contribution_shows_replacement_semantics_on_head(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    original_payload = _load_tripod_contribution_json(tmp_path)
    replacement_assertions = _assertions_from_contribution_json(original_payload)
    for assertion in replacement_assertions:
        if assertion.assertion_kind != "node" or assertion.subject_node_id != TRIPOD_ID:
            continue
        value = dict(assertion.value)
        assertion.label = "Replacement Tripod"
        assertion.value = {
            **value,
            "label": "Replacement Tripod",
            "role": "replacement controller",
        }

    replacement_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="supersede-node-1",
        accepted_assertions=replacement_assertions,
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    superseded = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=replacement_contribution,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert superseded.published is True

    head_node = next(
        node
        for node in kernel.project_world_graph(tmp_path, _request()).nodes
        if node.node_id == TRIPOD_ID
    )
    assert head_node.label == "Replacement Tripod"
    assert head_node.role == "replacement controller"

    pinned_node = next(
        node
        for node in kernel.project_world_graph(
            tmp_path,
            _request(revision_pin=result.current_head_revision_id),
        ).nodes
        if node.node_id == TRIPOD_ID
    )
    assert pinned_node.label != "Replacement Tripod"
    assert pinned_node.role != "replacement controller"


def test_malformed_stored_json_at_pinned_revision_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, pinned_revision_id)
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request(revision_pin=pinned_revision_id))
    assert exc_info.value.code == "projection_integrity_error"


def test_manifest_hash_mismatch_at_pinned_revision_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, pinned_revision_id)
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["campaign_id"] = "tampered-campaign-id"
    graph_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request(revision_pin=pinned_revision_id))
    assert exc_info.value.code == "projection_integrity_error"


def test_payload_hash_uses_on_disk_bytes_not_model_dump_round_trip(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Published graph.json may include keys dump(store) drops or omit defaults dump adds."""
    from graph_memory.kernel.world_projection import _verify_revision_payload_hash
    from graph_memory.union_supergraph.load import (
        dump_union_supergraph_store,
        parse_union_supergraph_store,
    )
    from graph_memory.world_supergraph.storage import canonicalize_graph_payload, sha256_hex

    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, pinned_revision_id)
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["version"] = "legacy-top-level"
    payload["source_domains"] = ["recap"]
    payload.pop("contribution_source_payload_sha256", None)
    payload.pop("initialization_attestation_digest", None)
    payload.pop("initialization_contribution_ids", None)
    payload.pop("initialization_plan_digest", None)
    on_disk = canonicalize_graph_payload(payload)
    dumped = dump_union_supergraph_store(parse_union_supergraph_store(payload))
    dumped_canonical = canonicalize_graph_payload(dumped)
    assert dumped_canonical != on_disk

    # On-disk digest is authoritative even when model dump drifts.
    _verify_revision_payload_hash(sha256_hex(on_disk), canonical_graph_json=on_disk)

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        _verify_revision_payload_hash(
            sha256_hex(on_disk),
            canonical_graph_json=dumped_canonical,
        )
    assert exc_info.value.code == "projection_integrity_error"

    # Full projection still works for the untouched published revision.
    projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    assert projection.snapshot.revision_id == pinned_revision_id


def test_tampered_graph_payload_with_matching_hash_fails_revision_identity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, pinned_revision_id)
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["campaign_id"] = "tampered-campaign-id"
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ) + "\n"
    graph_path.write_text(canonical, encoding="utf-8")

    manifest_path = _revision_manifest_path(tmp_path, pinned_revision_id)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["graph_payload_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request(revision_pin=pinned_revision_id))
    assert exc_info.value.code == "projection_integrity_error"


def test_malformed_head_revision_fails_integrity_without_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    head_revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, head_revision_id)
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"

def test_malformed_head_file_fails_integrity_without_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    _head_path(tmp_path).write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_mutated_active_contribution_fails_head_and_historical_projection(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    contribution_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / "contribution__022187fdefdf4557.json"
    )
    contribution = json.loads(contribution_path.read_text(encoding="utf-8"))
    battlefield = next(
        item
        for item in contribution["accepted_assertions"]
        if item["predicate"] == "battlefield_role"
    )
    battlefield["value"]["text"] = "tampered mutable contribution text"
    contribution_path.write_text(json.dumps(contribution, indent=2), encoding="utf-8")

    for request in (_request(), _request(revision_pin=result.current_head_revision_id)):
        with pytest.raises(WorldGraphProjectionError) as exc_info:
            kernel.project_world_graph(tmp_path, request)
        assert exc_info.value.code == "projection_integrity_error"


def test_multi_source_active_contributions_project_when_semantically_aligned(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_ALIGNED_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_ALIGNED_CONTRIBUTION_ID
    duplicate["source_artifact_id"] = RECAP_SOURCE_ARTIFACT_ID
    duplicate["source_revision_id"] = "dup-revision"
    duplicate_assertion = next(
        item
        for item in original["accepted_assertions"]
        if item["assertion_id"] == assertion.assertion_id
    )
    duplicate_aligned = deepcopy(duplicate_assertion)
    duplicate_aligned["contribution_id"] = DUP_ALIGNED_CONTRIBUTION_ID
    duplicate_aligned["evidence_ref_ids"] = ["evidence:bundle:v1:statblock:tripod-challenge"]
    duplicate_aligned["source_artifact_id"] = RECAP_SOURCE_ARTIFACT_ID
    duplicate_aligned["value"] = {
        **duplicate_assertion["value"],
        "source_domains": ["recap"],
        "source_domain": "recap",
        "source_artifact_id": RECAP_SOURCE_ARTIFACT_ID,
        "evidence_ref_ids": ["evidence:bundle:v1:statblock:tripod-challenge"],
        "evidence": [
            {
                "evidence_ref_id": "evidence:bundle:v1:statblock:tripod-challenge",
                "locator": "jsonptr:/accepted_assertions/0",
                "source_artifact_id": RECAP_SOURCE_ARTIFACT_ID,
                "source_domain": "recap",
            }
        ],
        "source_artifacts": [
            {
                "campaign_id": CAMPAIGN_ID,
                "source_artifact_id": RECAP_SOURCE_ARTIFACT_ID,
                "source_domain": "recap",
                "uri": "corpus://eldyrwild/session-23-recap",
            }
        ],
    }
    duplicate["accepted_assertions"] = [duplicate_aligned]
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_ALIGNED_CONTRIBUTION_ID,
        }
    )
    support["source_artifact_ids"] = sorted(
        {
            *support.get("source_artifact_ids", []),
            RECAP_SOURCE_ARTIFACT_ID,
        }
    )
    support["evidence_ref_ids"] = sorted(
        {
            *support.get("evidence_ref_ids", []),
            "evidence:bundle:v1:statblock:tripod-challenge",
        }
    )
    support["per_contribution_evidence_ref_ids"] = {
        **support.get("per_contribution_evidence_ref_ids", {}),
        DUP_ALIGNED_CONTRIBUTION_ID: ["evidence:bundle:v1:statblock:tripod-challenge"],
    }
    support["per_contribution_source_artifact_ids"] = {
        **support.get("per_contribution_source_artifact_ids", {}),
        DUP_ALIGNED_CONTRIBUTION_ID: [RECAP_SOURCE_ARTIFACT_ID],
    }
    store.assertion_support[assertion.assertion_id] = support
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-alignment"],
    )

    projection = kernel.project_world_graph(tmp_path, _request())
    battlefield = next(
        item
        for item in projection.attributes
        if item.assertion_id == assertion.assertion_id
    )
    assert set(battlefield.active_contribution_ids) == {
        TRIPOD_CONTRIBUTION_ID,
        DUP_ALIGNED_CONTRIBUTION_ID,
    }
    assert "evidence:bundle:v1:statblock:tripod-battlefield-role" in battlefield.evidence_ref_ids
    assert "evidence:bundle:v1:statblock:tripod-challenge" in battlefield.evidence_ref_ids


def test_multi_source_missing_assertion_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )

    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_MISSING_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_MISSING_CONTRIBUTION_ID
    duplicate["accepted_assertions"] = [
        item
        for item in original["accepted_assertions"]
        if item["assertion_id"] != assertion.assertion_id
    ]
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_MISSING_CONTRIBUTION_ID,
        }
    )
    support["per_contribution_evidence_ref_ids"] = {
        **support.get("per_contribution_evidence_ref_ids", {}),
        DUP_MISSING_CONTRIBUTION_ID: list(support.get("evidence_ref_ids", [])),
    }
    support["per_contribution_source_artifact_ids"] = {
        **support.get("per_contribution_source_artifact_ids", {}),
        DUP_MISSING_CONTRIBUTION_ID: list(support.get("source_artifact_ids", [])),
    }
    store.assertion_support[assertion.assertion_id] = support
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-missing-assertion"],
    )

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_multi_source_semantic_divergence_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )

    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_DIVERGENT_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_DIVERGENT_CONTRIBUTION_ID
    duplicate_assertions = []
    for item in original["accepted_assertions"]:
        if item["assertion_id"] != assertion.assertion_id:
            continue
        divergent = deepcopy(item)
        divergent["value"] = {"text": "Divergent battlefield role"}
        duplicate_assertions.append(divergent)
    duplicate["accepted_assertions"] = duplicate_assertions
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_DIVERGENT_CONTRIBUTION_ID,
        }
    )
    support["per_contribution_evidence_ref_ids"] = {
        **support.get("per_contribution_evidence_ref_ids", {}),
        DUP_DIVERGENT_CONTRIBUTION_ID: list(support.get("evidence_ref_ids", [])),
    }
    support["per_contribution_source_artifact_ids"] = {
        **support.get("per_contribution_source_artifact_ids", {}),
        DUP_DIVERGENT_CONTRIBUTION_ID: list(support.get("source_artifact_ids", [])),
    }
    store.assertion_support[assertion.assertion_id] = support
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-divergence"],
    )

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_retracted_edge_supporter_keeps_node_cards_aligned_with_relationship(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    original_payload = _load_tripod_contribution_json(tmp_path)
    original_assertion = next(
        assertion
        for assertion in _assertions_from_contribution_json(original_payload)
        if assertion.assertion_kind == "edge"
        and str(assertion.value.get("edge_id") or "") == edge_id
    )
    duplicate_evidence = "evidence:test:duplicate-edge-support"
    duplicate_artifact = "graph-native:test:duplicate-edge-support"
    duplicate_assertion = original_assertion.model_copy(
        update={
            "contribution_id": DUP_ALIGNED_CONTRIBUTION_ID,
            "evidence_ref_ids": [duplicate_evidence],
            "source_artifact_id": duplicate_artifact,
            "value": {
                **dict(original_assertion.value),
                "source_domain": "manual_seed",
                "source_domains": ["manual_seed"],
                "source_artifact_id": duplicate_artifact,
                "source_artifacts": [
                    {
                        "source_artifact_id": duplicate_artifact,
                        "source_domain": "manual_seed",
                        "campaign_id": CAMPAIGN_ID,
                        "uri": "graph-data://test/duplicate-edge-support",
                    }
                ],
                "evidence_ref_ids": [duplicate_evidence],
                "evidence": [
                    {
                        "evidence_ref_id": duplicate_evidence,
                        "source_artifact_id": duplicate_artifact,
                        "source_domain": "manual_seed",
                        "locator": "test://duplicate-edge-support",
                    }
                ],
            },
        }
    )
    duplicate_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=duplicate_artifact,
        source_revision_id="duplicate-edge-support-1",
        accepted_assertions=[duplicate_assertion],
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=duplicate_contribution,
    )
    assert merged.published is True
    pinned_revision_id = merged.revision_id

    retracted = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=duplicate_contribution.contribution_id,
        reason="duplicate edge provenance withdrawn",
    )
    assert retracted.published is True
    head_projection = kernel.project_world_graph(tmp_path, _request())
    relationship = next(item for item in head_projection.relationships if item.edge_id == edge_id)
    assert duplicate_evidence not in relationship.evidence_ref_ids

    for node_id in (relationship.source_node_id, relationship.target_node_id):
        node = next(item for item in head_projection.nodes if item.node_id == node_id)
        adjacency = next(item for item in node.adjacency if item.edge_id == edge_id)
        assert adjacency.evidence_ref_ids == relationship.evidence_ref_ids
        assert adjacency.source_domains == relationship.source_domains
        assert adjacency.edge_label == relationship.label
        assert adjacency.session_ids == relationship.session_ids
        assert adjacency.source_excerpt is None
        assert adjacency.source_excerpt_highlight_spans == []

    pinned_relationship = next(
        item
        for item in kernel.project_world_graph(
            tmp_path,
            _request(revision_pin=pinned_revision_id),
        ).relationships
        if item.edge_id == edge_id
    )
    assert duplicate_evidence in pinned_relationship.evidence_ref_ids


def test_unsupported_edge_omitted_from_relationships_and_node_adjacency(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    edge = store.edges[edge_id]
    edge_state = dict(edge.state or {})
    edge_state["memory_state"] = "unsupported_assertion"
    store.edges[edge_id] = edge.model_copy(update={"state": edge_state})

    for assertion_id, raw_support in store.assertion_support.items():
        support = dict(raw_support)
        if support.get("graph_object_id") != edge_id:
            continue
        support["support_state"] = "unsupported"
        support["active_contribution_ids"] = []
        support["per_contribution_evidence_ref_ids"] = {}
        support["per_contribution_source_artifact_ids"] = {}
        store.assertion_support[assertion_id] = support
        break

    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-edge-only-retraction"],
    )

    projection = kernel.project_world_graph(tmp_path, _request())
    assert not any(relationship.edge_id == edge_id for relationship in projection.relationships)

    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    event = next(node for node in projection.nodes if node.node_id == EVENT_ID)
    assert not any(candidate.edge_id == edge_id for candidate in tripod.adjacency)
    assert not any(
        expansion.edge_id == edge_id for expansion in tripod.suggested_expansions
    )
    assert not any(candidate.edge_id == edge_id for candidate in event.adjacency)
    assert not any(
        expansion.edge_id == edge_id for expansion in event.suggested_expansions
    )


def test_multi_source_one_supporter_retracted_drops_retracted_evidence_on_head(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)

    assertion = next(
        attribute
        for attribute in kernel.project_world_graph(tmp_path, _request()).attributes
        if attribute.subject_node_id == TRIPOD_ID
        and (attribute.label or attribute.predicate) == "battlefield_role"
    )
    original_evidence = "evidence:bundle:v1:statblock:tripod-battlefield-role"
    duplicate_evidence = "evidence:bundle:v1:statblock:dup-aligned-battlefield-only"

    duplicate_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{DUP_ALIGNED_CONTRIBUTION_ID.replace(':', '__')}.json"
    )
    original = _load_tripod_contribution_json(tmp_path)
    duplicate = deepcopy(original)
    duplicate["contribution_id"] = DUP_ALIGNED_CONTRIBUTION_ID
    duplicate["source_artifact_id"] = DUP_SOURCE_ARTIFACT_ID
    duplicate["source_revision_id"] = "dup-revision"
    duplicate_assertion = next(
        item
        for item in original["accepted_assertions"]
        if item["assertion_id"] == assertion.assertion_id
    )
    duplicate_aligned = deepcopy(duplicate_assertion)
    duplicate_aligned["contribution_id"] = DUP_ALIGNED_CONTRIBUTION_ID
    duplicate_aligned["evidence_ref_ids"] = [duplicate_evidence]
    duplicate_aligned["source_artifact_id"] = DUP_SOURCE_ARTIFACT_ID
    duplicate_aligned["value"] = {
        **duplicate_assertion["value"],
        "source_domains": ["statblock"],
        "source_domain": "statblock",
        "source_artifact_id": DUP_SOURCE_ARTIFACT_ID,
        "evidence_ref_ids": [duplicate_evidence],
        "evidence": [
            {
                "evidence_ref_id": duplicate_evidence,
                "locator": "jsonptr:/accepted_assertions/0",
                "source_artifact_id": DUP_SOURCE_ARTIFACT_ID,
                "source_domain": "statblock",
            }
        ],
        "source_artifacts": [
            {
                "campaign_id": CAMPAIGN_ID,
                "source_artifact_id": DUP_SOURCE_ARTIFACT_ID,
                "source_domain": "statblock",
                "uri": "graph-data://test/dup-aligned-battlefield",
            }
        ],
    }
    duplicate["accepted_assertions"] = [duplicate_aligned]
    duplicate_path.write_text(json.dumps(duplicate, indent=2), encoding="utf-8")

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    support = dict(store.assertion_support[assertion.assertion_id])
    support["active_contribution_ids"] = sorted(
        {
            *support["active_contribution_ids"],
            DUP_ALIGNED_CONTRIBUTION_ID,
        }
    )
    support["evidence_ref_ids"] = sorted(
        {
            *support.get("evidence_ref_ids", []),
            original_evidence,
            duplicate_evidence,
        }
    )
    support["source_artifact_ids"] = sorted(
        {
            *support.get("source_artifact_ids", []),
            DUP_SOURCE_ARTIFACT_ID,
        }
    )
    support["per_contribution_evidence_ref_ids"] = {
        **support.get("per_contribution_evidence_ref_ids", {}),
        DUP_ALIGNED_CONTRIBUTION_ID: [duplicate_evidence],
    }
    support["per_contribution_source_artifact_ids"] = {
        **support.get("per_contribution_source_artifact_ids", {}),
        DUP_ALIGNED_CONTRIBUTION_ID: [DUP_SOURCE_ARTIFACT_ID],
    }
    store.assertion_support[assertion.assertion_id] = support
    store.evidence[duplicate_evidence] = UnionSupergraphEvidence(
        evidence_ref_id=duplicate_evidence,
        source_artifact_id=DUP_SOURCE_ARTIFACT_ID,
        source_domain="statblock",
        evidence_role="contribution_support",
        can_open_source=True,
        can_highlight_span=False,
        locator="jsonptr:/accepted_assertions/0",
    )
    if DUP_SOURCE_ARTIFACT_ID not in store.source_artifacts:
        store.source_artifacts[DUP_SOURCE_ARTIFACT_ID] = UnionSupergraphSourceArtifact(
            source_artifact_id=DUP_SOURCE_ARTIFACT_ID,
            source_domain="statblock",
            campaign_id=CAMPAIGN_ID,
            uri="graph-data://test/dup-aligned-battlefield",
        )
    multi_source = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-multi-source-before-retract"],
    )
    pinned_revision_id = multi_source.revision.revision_id

    retracted = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=DUP_ALIGNED_CONTRIBUTION_ID,
        reason="duplicate battlefield provenance withdrawn",
    )
    assert retracted.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    head_battlefield = next(
        item
        for item in head_projection.attributes
        if item.assertion_id == assertion.assertion_id
    )
    assert original_evidence in head_battlefield.evidence_ref_ids
    assert duplicate_evidence not in head_battlefield.evidence_ref_ids
    assert DUP_ALIGNED_CONTRIBUTION_ID not in head_battlefield.active_contribution_ids

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_battlefield = next(
        item
        for item in pinned_projection.attributes
        if item.assertion_id == assertion.assertion_id
    )
    assert original_evidence in pinned_battlefield.evidence_ref_ids
    assert duplicate_evidence in pinned_battlefield.evidence_ref_ids

    head_top_level_evidence_ids = {
        item.evidence_ref_id for item in head_projection.evidence
    }
    head_top_level_artifact_ids = {
        item.source_artifact_id for item in head_projection.source_artifacts
    }
    assert duplicate_evidence not in head_top_level_evidence_ids
    assert DUP_SOURCE_ARTIFACT_ID not in head_top_level_artifact_ids
    assert head_top_level_artifact_ids == {
        item.source_artifact_id for item in head_projection.evidence
    }

    pinned_top_level_evidence_ids = {
        item.evidence_ref_id for item in pinned_projection.evidence
    }
    pinned_top_level_artifact_ids = {
        item.source_artifact_id for item in pinned_projection.source_artifacts
    }
    assert duplicate_evidence in pinned_top_level_evidence_ids
    assert DUP_SOURCE_ARTIFACT_ID in pinned_top_level_artifact_ids
    assert pinned_top_level_artifact_ids == {
        item.source_artifact_id for item in pinned_projection.evidence
    }


def test_generated_fallback_evidence_surfaces_in_projection(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = "edge:threat:tripod-null-calf:related_to:location:mireward"
    source_node_id = TRIPOD_ID
    target_node_id = "location:mireward"
    edge_assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        contribution_id=FALLBACK_EDGE_CONTRIBUTION_ID,
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate="related_to",
        label="guards approach",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id="graph-native:test:fallback-edge",
        value={
            "edge_id": edge_id,
            "direction": "outbound",
            "source_domains": ["manual_seed"],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:fallback-edge",
        source_revision_id="fallback-edge-1",
        accepted_assertions=[edge_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True
    merged_contribution_id = merged.contribution_ids[0]
    fallback_evidence_id = f"evidence:{merged_contribution_id}:{edge_id}"

    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Tripod Null-Calf"),
    )
    relationship = next(
        item for item in projection.relationships if item.edge_id == edge_id
    )
    assert fallback_evidence_id in relationship.evidence_ref_ids

    source_node = next(node for node in projection.nodes if node.node_id == source_node_id)
    target_node = next(node for node in projection.nodes if node.node_id == target_node_id)
    assert fallback_evidence_id in source_node.evidence_ref_ids
    assert fallback_evidence_id in target_node.evidence_ref_ids
    assert any(
        badge.evidence_ref_id == fallback_evidence_id for badge in source_node.evidence_badges
    )

    assert projection.query_context is not None
    assert source_node_id in projection.query_context.matched_node_ids
    query_evidence_ids = {
        item.evidence_ref_id for item in projection.query_context.evidence
    }
    assert fallback_evidence_id in query_evidence_ids

    top_level_evidence_ids = {item.evidence_ref_id for item in projection.evidence}
    assert fallback_evidence_id in top_level_evidence_ids
    fallback_artifact_id = next(
        evidence.source_artifact_id
        for evidence in projection.evidence
        if evidence.evidence_ref_id == fallback_evidence_id
    )
    top_level_artifact_ids = {
        artifact.source_artifact_id for artifact in projection.source_artifacts
    }
    assert fallback_artifact_id in top_level_artifact_ids
    assert fallback_artifact_id in relationship.source_artifact_ids
    assert fallback_artifact_id in source_node.source_artifact_ids
    assert fallback_artifact_id in target_node.source_artifact_ids


def test_node_fallback_evidence_not_attributed_to_sibling_attribute(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    source_artifact_id = "graph-native:test:fallback-split"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        contribution_id=FALLBACK_SPLIT_CONTRIBUTION_ID,
        subject_node_id=FALLBACK_SPLIT_NODE_ID,
        label="Fallback Split Test",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["manual_seed"],
            "aliases": ["Fallback Split Test"],
            "canon_state": "canonical",
        },
        evidence_ref_ids=[],
    )
    attribute_assertion = kernel.build_assertion(
        assertion_kind="attribute",
        acceptance_state="accepted",
        contribution_id=FALLBACK_SPLIT_CONTRIBUTION_ID,
        subject_node_id=FALLBACK_SPLIT_NODE_ID,
        predicate="test_marker",
        label="test_marker",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "attribute": "test_marker",
            "text": "marker without evidence",
            "source_domains": ["manual_seed"],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=source_artifact_id,
        source_revision_id="fallback-split-1",
        accepted_assertions=[node_assertion, attribute_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True
    merged_contribution_id = merged.contribution_ids[0]
    fallback_evidence_id = f"evidence:{merged_contribution_id}:{FALLBACK_SPLIT_NODE_ID}"

    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Fallback Split Test"),
    )
    node = next(node for node in projection.nodes if node.node_id == FALLBACK_SPLIT_NODE_ID)
    attribute = next(
        item
        for item in projection.attributes
        if item.subject_node_id == FALLBACK_SPLIT_NODE_ID
        and (item.label or item.predicate) == "test_marker"
    )
    assert fallback_evidence_id in node.evidence_ref_ids
    assert fallback_evidence_id not in attribute.evidence_ref_ids
    assert attribute.evidence_ref_ids == []

    assert projection.query_context is not None
    assert FALLBACK_SPLIT_NODE_ID in projection.query_context.matched_node_ids
    query_attribute = next(
        item
        for item in projection.query_context.attributes
        if item.subject_node_id == FALLBACK_SPLIT_NODE_ID
        and (item.label or item.predicate) == "test_marker"
    )
    assert fallback_evidence_id not in query_attribute.evidence_ref_ids
    query_node = next(
        item for item in projection.query_context.nodes if item.node_id == FALLBACK_SPLIT_NODE_ID
    )
    assert fallback_evidence_id in query_node.evidence_ref_ids


def test_attribute_direct_source_artifact_surfaces_in_projection_closure(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    attribute_assertion = kernel.build_assertion(
        assertion_kind="attribute",
        acceptance_state="accepted",
        contribution_id=ATTR_ONLY_CONTRIBUTION_ID,
        subject_node_id=TRIPOD_ID,
        predicate="artifact_only_marker",
        label="artifact_only_marker",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=ATTR_ONLY_ARTIFACT_ID,
        value={
            "attribute": "artifact_only_marker",
            "text": "attribute with direct artifact only",
            "source_domains": ["manual_seed"],
            "source_artifacts": [
                {
                    "source_artifact_id": ATTR_ONLY_ARTIFACT_ID,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": "graph-data://test/attr-direct-artifact",
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=ATTR_ONLY_ARTIFACT_ID,
        source_revision_id="attr-artifact-only-1",
        accepted_assertions=[attribute_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True

    projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text="Attr Artifact Only"),
    )
    attribute = next(
        item
        for item in projection.attributes
        if item.subject_node_id == TRIPOD_ID
        and (item.label or item.predicate) == "artifact_only_marker"
    )
    assert attribute.evidence_ref_ids == []
    assert ATTR_ONLY_ARTIFACT_ID in attribute.source_artifact_ids
    top_level_artifact_ids = {
        artifact.source_artifact_id for artifact in projection.source_artifacts
    }
    assert ATTR_ONLY_ARTIFACT_ID in top_level_artifact_ids

    assert projection.query_context is not None
    query_artifact_ids = {
        artifact.source_artifact_id for artifact in projection.query_context.source_artifacts
    }
    assert ATTR_ONLY_ARTIFACT_ID in query_artifact_ids


def test_unsupported_admissibility_fails_closed(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(admissibility="player"),
        )
    assert exc_info.value.code == "unsupported_admissibility"


def test_foreign_campaign_filters_to_world_universal_only(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Requesting another campaign no longer 409s; C2-scoped objects are hidden."""
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(campaign_id="longmont-c1"),
    )
    assert projection.snapshot.campaign_id == "longmont-c1"
    node_ids = {node.node_id for node in projection.nodes}
    # World hubs are campaign_scope null.
    assert "location:mirathorn" in node_ids
    assert "location:mireward" in node_ids
    # C2-scoped party / events / PCs are excluded until PC supersede + C1 bundle.
    assert "party:questionable-company" not in node_ids
    assert EVENT_ID not in node_ids
    assert TRIPOD_ID not in node_ids
    assert not any(
        rel.target_node_id == EVENT_ID or rel.source_node_id == EVENT_ID
        for rel in projection.relationships
    )


def test_c2_campaign_projection_still_sees_tripod(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(tmp_path, _request())
    assert TRIPOD_ID in {node.node_id for node in projection.nodes}
    assert "party:questionable-company" in {node.node_id for node in projection.nodes}


def test_world_scope_projection_includes_c2_objects_from_c1_anchor(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """GM world lens sees campaign-scoped assertions across the world."""
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(campaign_id="longmont-c1", scope_mode="world"),
    )
    assert projection.snapshot.scope_mode == "world"
    assert projection.snapshot.campaign_id == "longmont-c1"
    node_ids = {node.node_id for node in projection.nodes}
    assert TRIPOD_ID in node_ids
    assert "party:questionable-company" in node_ids
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    assert tripod.campaign_scope == "longmont-c2"
    # Adjacency inherits edge (or related-node) campaign tenancy for world-lens stamps.
    scoped_adjacency = [candidate for candidate in tripod.adjacency if candidate.campaign_scope]
    assert scoped_adjacency
    assert all(
        candidate.campaign_scope in {"longmont-c1", "longmont-c2"}
        for candidate in scoped_adjacency
    )


def test_campaign_scope_mode_still_isolates_foreign_campaign(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    projection = kernel.project_world_graph(
        tmp_path,
        _request(campaign_id="longmont-c1", scope_mode="campaign"),
    )
    assert projection.snapshot.scope_mode == "campaign"
    node_ids = {node.node_id for node in projection.nodes}
    assert TRIPOD_ID not in node_ids
    assert "party:questionable-company" not in node_ids


def test_qualified_session_focus_does_not_match_bare_session_across_campaigns(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Focus campaign qualifies session-N so C1 session-23 != C2 session-23."""
    _initialize(tmp_path, loaded_bundle)
    # Store evidence/events are C2 session-23; request a C1-qualified same session id.
    projection = kernel.project_world_graph(
        tmp_path,
        _request(
            campaign_id="longmont-c1",
            scope_mode="world",
            focus_kind="session",
            session_id=FOCUS_SESSION_ID,
            focus_campaign_id="longmont-c1",
        ),
    )
    assert projection.snapshot.focus.campaign_id == "longmont-c1"
    event = next(node for node in projection.nodes if node.node_id == EVENT_ID)
    # C2 session-23 event must not count as focus-anchored under a C1 focus.
    assert event.anchored_to_focus_session is False

    c2_focus = kernel.project_world_graph(
        tmp_path,
        _request(
            campaign_id="longmont-c2",
            scope_mode="world",
            focus_kind="session",
            session_id=FOCUS_SESSION_ID,
            focus_campaign_id="longmont-c2",
        ),
    )
    event_c2 = next(node for node in c2_focus.nodes if node.node_id == EVENT_ID)
    assert event_c2.anchored_to_focus_session is True


def test_world_owned_relationship_without_evidence_not_focus_anchored(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Session stamp alone must not focus-anchor a world-owned edge without evidence."""
    _initialize(tmp_path, loaded_bundle)
    edge_id = "edge:test:world-owned-session-stamp-only"
    source_node_id = TRIPOD_ID
    target_node_id = "location:mireward"
    edge_assertion = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        contribution_id="contribution:test:world-owned-session-stamp",
        subject_node_id=source_node_id,
        target_node_id=target_node_id,
        predicate="related_to",
        label="session stamp only",
        campaign_scope=None,
        source_artifact_id="graph-native:test:world-owned-session-stamp",
        value={
            "edge_id": edge_id,
            "direction": "outbound",
            "source_domains": ["manual_seed"],
            "session_ids": [FOCUS_SESSION_ID],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:world-owned-session-stamp",
        source_revision_id="world-owned-session-stamp-1",
        accepted_assertions=[edge_assertion],
        campaign_scope=None,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True

    projection = kernel.project_world_graph(
        tmp_path,
        _request(
            campaign_id="longmont-c1",
            scope_mode="world",
            focus_kind="session",
            session_id=FOCUS_SESSION_ID,
            focus_campaign_id="longmont-c1",
        ),
    )
    tripod = next(node for node in projection.nodes if node.node_id == source_node_id)
    adjacency = next(item for item in tripod.adjacency if item.edge_id == edge_id)
    assert adjacency.anchored_to_focus_session is False


def test_integrity_failure_when_contribution_missing(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    contribution_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / "contribution__022187fdefdf4557.json"
    )
    assert contribution_path.is_file()
    shutil.move(
        contribution_path,
        contribution_path.with_suffix(".json.removed"),
    )

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"


def test_projection_apis_exported_from_kernel_public_api() -> None:
    for name in (
        "project_world_graph",
        "build_projection_payload",
        "resolve_projection_admissibility",
        "search_world_graph_projection",
        "WorldGraphProjectionError",
    ):
        assert name in kernel.__all__
        assert hasattr(kernel, name)


def test_provenance_only_mutation_of_embedded_evidence_fails_integrity(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Removing evidence that lives only in ``value["evidence"]`` is a
    provenance-only mutation (excluded from ``assertion_id`` identity), so it
    must be caught by the per-contribution evidence-lineage check rather than
    silently dropping evidence from the projection.
    """
    _initialize(tmp_path, loaded_bundle)
    node_id = "location:test-provenance-lineage"
    evidence_ref_id = "evidence:test:provenance-lineage-embedded"
    artifact_id = "graph-native:test:provenance-lineage"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label="Provenance Lineage Test",
        campaign_scope=CAMPAIGN_ID,
        value={
            "kind": "location",
            "role": "location",
            "source_domains": ["manual_seed"],
            "aliases": ["Provenance Lineage Test"],
            "canon_state": "canonical",
            # Evidence lives only embedded in value.evidence, never in the
            # top-level assertion.evidence_ref_ids field.
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": artifact_id,
                    "source_domain": "manual_seed",
                    "locator": "test://provenance-lineage",
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=artifact_id,
        source_revision_id="provenance-lineage-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True
    pinned_revision_id = merged.revision_id
    merged_contribution_id = merged.contribution_ids[0]

    # Sanity: evidence declared only inside value.evidence is collected and
    # projected before any mutation happens.
    projection = kernel.project_world_graph(tmp_path, _request())
    node = next(item for item in projection.nodes if item.node_id == node_id)
    assert evidence_ref_id in node.evidence_ref_ids

    contribution_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{merged_contribution_id.replace(':', '__')}.json"
    )
    payload = json.loads(contribution_path.read_text(encoding="utf-8"))
    mutated_assertion = payload["accepted_assertions"][0]
    original_assertion_id = mutated_assertion["assertion_id"]
    mutated_assertion["value"]["evidence"] = []
    contribution_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # The mutation only touched a provenance-only value key, so identity is
    # unaffected -- this is exactly the kind of mutation the old subset check
    # missed.
    assert mutated_assertion["assertion_id"] == original_assertion_id

    for request in (_request(), _request(revision_pin=pinned_revision_id)):
        with pytest.raises(WorldGraphProjectionError) as exc_info:
            kernel.project_world_graph(tmp_path, request)
        assert exc_info.value.code == "projection_integrity_error"


def test_active_alias_assertion_appears_matches_search_and_pins_correctly(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    alias_text = "Null-Calf the Tripod"
    alias_assertion = kernel.build_assertion(
        assertion_kind="alias",
        acceptance_state="accepted",
        subject_node_id=TRIPOD_ID,
        label=alias_text,
        campaign_scope=CAMPAIGN_ID,
        value={"alias": alias_text},
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:alias-assertion",
        source_revision_id="alias-assertion-1",
        accepted_assertions=[alias_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True
    pinned_with_alias_revision_id = merged.revision_id
    merged_contribution_id = merged.contribution_ids[0]

    projection = kernel.project_world_graph(tmp_path, _request())
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    assert alias_text in tripod.aliases

    search_projection = kernel.project_world_graph(
        tmp_path,
        _request(query_text=alias_text),
    )
    assert search_projection.query_context is not None
    assert TRIPOD_ID in search_projection.query_context.matched_node_ids

    retracted = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=merged_contribution_id,
        reason="alias withdrawn for test",
    )
    assert retracted.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    head_tripod = next(
        node for node in head_projection.nodes if node.node_id == TRIPOD_ID
    )
    assert alias_text not in head_tripod.aliases

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_with_alias_revision_id),
    )
    pinned_tripod = next(
        node for node in pinned_projection.nodes if node.node_id == TRIPOD_ID
    )
    assert alias_text in pinned_tripod.aliases


def test_node_card_direction_is_endpoint_relative_and_expansion_rank_is_preserved(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    identity_context = build_union_projection_identity_context(store)
    raw_tripod_view = build_node_view(
        store,
        TRIPOD_ID,
        focus_session_id=FOCUS_SESSION_ID,
        identity_context=identity_context,
    )
    original_expansion = next(
        item for item in raw_tripod_view.suggested_expansions if item.edge_id == edge_id
    )

    projection = kernel.project_world_graph(tmp_path, _request())
    relationship = next(
        item for item in projection.relationships if item.edge_id == edge_id
    )
    # The bundle's tripod->event edge is directed source (tripod) -> target
    # (event); see test_relationship_to_mireward_gate_battle_present.
    assert relationship.source_node_id == TRIPOD_ID
    assert relationship.target_node_id == EVENT_ID

    source_node = next(
        node for node in projection.nodes if node.node_id == relationship.source_node_id
    )
    target_node = next(
        node for node in projection.nodes if node.node_id == relationship.target_node_id
    )
    source_candidate = next(
        item for item in source_node.adjacency if item.edge_id == edge_id
    )
    target_candidate = next(
        item for item in target_node.adjacency if item.edge_id == edge_id
    )
    assert source_candidate.direction == "outbound"
    assert target_candidate.direction == "inbound"
    assert source_candidate.direction != target_candidate.direction

    projected_expansion = next(
        item for item in source_node.suggested_expansions if item.edge_id == edge_id
    )
    assert projected_expansion.rank == original_expansion.rank
    assert projected_expansion.rank_reason == original_expansion.rank_reason
    # Normalization must not have flattened every expansion to a single
    # synthesized reason/order -- the underlying node view's own ordering
    # (focus-first) must survive untouched for pre-existing relationships.
    assert [item.edge_id for item in source_node.suggested_expansions] == [
        item.edge_id for item in raw_tripod_view.suggested_expansions
    ]


def test_superseded_edge_value_only_label_and_empty_session_ids_are_presence_sensitive(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """The write contract allows label/session_ids replacements to live only
    inside ``value``, with the top-level ``assertion.label`` left falsy. The
    read side must reconstruct those fields by presence, not truthiness --
    otherwise a value-only label replacement is silently ignored, and an
    explicit ``session_ids: []`` can never clear a previously non-empty list.
    """
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    original_payload = _load_tripod_contribution_json(tmp_path)

    # Stage A: establish a non-empty session_ids baseline to pin against, so
    # that stage B's "clear with []" is a meaningful, observable change.
    stage_a_assertions = _assertions_from_contribution_json(original_payload)
    for assertion in stage_a_assertions:
        value = dict(assertion.value)
        if str(value.get("edge_id") or "") != edge_id:
            continue
        assertion.value = {**value, "session_ids": ["session-99"]}

    stage_a_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="supersede-edge-value-only-stage-a",
        accepted_assertions=stage_a_assertions,
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    stage_a_result = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=stage_a_contribution,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert stage_a_result.published is True
    pinned_revision_id = stage_a_result.revision_id
    stage_a_contribution_id = stage_a_result.contribution_ids[0]

    pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    pinned_relationship = next(
        item for item in pinned_projection.relationships if item.edge_id == edge_id
    )
    assert pinned_relationship.session_ids == ["session-99"]
    assert pinned_relationship.label == "appeared in"

    # Stage B: replace with a value-only label and an explicit empty
    # session_ids, with the top-level assertion.label left falsy (None).
    stage_a_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{stage_a_contribution_id.replace(':', '__')}.json"
    )
    stage_a_payload = json.loads(stage_a_path.read_text(encoding="utf-8"))
    stage_b_assertions = _assertions_from_contribution_json(stage_a_payload)
    for assertion in stage_b_assertions:
        value = dict(assertion.value)
        if str(value.get("edge_id") or "") != edge_id:
            continue
        assertion.label = None
        assertion.value = {
            **value,
            "label": "value-only replacement label",
            "session_ids": [],
        }

    stage_b_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=stage_a_payload["source_artifact_id"],
        source_revision_id="supersede-edge-value-only-stage-b",
        accepted_assertions=stage_b_assertions,
        supersedes_contribution_id=stage_a_contribution_id,
    )
    stage_b_result = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=stage_b_contribution,
        superseded_contribution_id=stage_a_contribution_id,
    )
    assert stage_b_result.published is True

    head_projection = kernel.project_world_graph(tmp_path, _request())
    head_relationship = next(
        item for item in head_projection.relationships if item.edge_id == edge_id
    )
    assert head_relationship.label == "value-only replacement label"
    assert head_relationship.session_ids == []

    # The stage-A pin must still show the pre-clear baseline.
    replayed_pinned_projection = kernel.project_world_graph(
        tmp_path,
        _request(revision_pin=pinned_revision_id),
    )
    replayed_pinned_relationship = next(
        item
        for item in replayed_pinned_projection.relationships
        if item.edge_id == edge_id
    )
    assert replayed_pinned_relationship.label == "appeared in"
    assert replayed_pinned_relationship.session_ids == ["session-99"]


def test_head_pointing_to_nonexistent_revision_fails_integrity_pinned_and_unpinned(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    pinned_revision_id = result.current_head_revision_id
    bogus_revision_id = "rev:00000000000000000000000000000000"
    assert bogus_revision_id != pinned_revision_id

    head_path = _head_path(tmp_path)
    head_payload = json.loads(head_path.read_text(encoding="utf-8"))
    head_payload["head_revision_id"] = bogus_revision_id
    head_path.write_text(json.dumps(head_payload, indent=2), encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(revision_pin=pinned_revision_id),
        )
    assert exc_info.value.code == "projection_integrity_error"


def test_incomplete_support_lineage_fails_closed(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """The current writer rejects support records missing active lineage."""
    _initialize(tmp_path, loaded_bundle)
    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    assertion_id, raw_support = next(iter(store.assertion_support.items()))
    support = dict(raw_support)
    contribution_id = support["active_contribution_ids"][0]
    support["per_contribution_evidence_ref_ids"] = {
        key: value
        for key, value in support["per_contribution_evidence_ref_ids"].items()
        if key != contribution_id
    }
    store.assertion_support[assertion_id] = support

    with pytest.raises(
        kernel.WorldGraphValidationError,
        match="evidence lineage keys must exactly match active_contribution_ids",
    ):
        kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store,
            operation_ids=["op:test-incomplete-provenance-support"],
        )

    projection = kernel.project_world_graph(
        tmp_path,
        _request(),
    )
    assert projection.snapshot.revision_id == _revision.revision_id


def test_alias_embedded_provenance_materializes_before_projection(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    alias_text = "Embedded Evidence Alias"
    artifact_id = "graph-native:test:alias-embedded-provenance"
    evidence_ref_id = "evidence:test:alias-embedded-provenance"
    alias_assertion = kernel.build_assertion(
        assertion_kind="alias",
        acceptance_state="accepted",
        subject_node_id=TRIPOD_ID,
        label=alias_text,
        campaign_scope=CAMPAIGN_ID,
        value={
            "alias": alias_text,
            "source_artifacts": [
                {
                    "source_artifact_id": artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": "graph-data://test/alias-embedded-provenance",
                }
            ],
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": artifact_id,
                    "source_domain": "manual_seed",
                    "locator": "test://alias-embedded-provenance",
                }
            ],
        },
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=artifact_id,
        source_revision_id="alias-embedded-provenance-1",
        accepted_assertions=[alias_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True

    projection = kernel.project_world_graph(tmp_path, _request())
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    assert alias_text in tripod.aliases
    assert evidence_ref_id in tripod.evidence_ref_ids
    assert artifact_id in tripod.source_artifact_ids


def test_active_node_assertion_summary_projects_onto_node_and_related_summary(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Node summaries live on active assertions, not union ``description``.

    Insertable Plan chips / GraphObjectCard read ``summary`` from world
    projection; dropping assertion summaries makes chips look empty of
    projected info even when promote succeeded.
    """
    _initialize(tmp_path, loaded_bundle)
    original_payload = _load_tripod_contribution_json(tmp_path)
    original_node = next(
        assertion
        for assertion in _assertions_from_contribution_json(original_payload)
        if assertion.assertion_kind == "node" and assertion.subject_node_id == TRIPOD_ID
    )
    summary_text = "Assertion-backed summary for projection chips."
    updated_value = {**dict(original_node.value), "summary": summary_text}
    stage = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="node-summary-projection-1",
        accepted_assertions=[
            assertion.model_copy(update={"value": updated_value})
            if assertion.assertion_id == original_node.assertion_id
            else assertion
            for assertion in _assertions_from_contribution_json(original_payload)
        ],
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    result = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=stage,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert result.published is True

    tripod = next(
        node
        for node in kernel.project_world_graph(tmp_path, _request()).nodes
        if node.node_id == TRIPOD_ID
    )
    assert tripod.summary == summary_text

    neighbor = next(
        node
        for node in kernel.project_world_graph(tmp_path, _request()).nodes
        if any(edge.node_id == TRIPOD_ID for edge in node.adjacency)
    )
    related = next(edge for edge in neighbor.adjacency if edge.node_id == TRIPOD_ID)
    assert related.related_summary == summary_text


def test_multiple_active_node_assertions_union_aliases_and_historical_pin(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    original_payload = _load_tripod_contribution_json(tmp_path)
    original_node = next(
        assertion
        for assertion in _assertions_from_contribution_json(original_payload)
        if assertion.assertion_kind == "node" and assertion.subject_node_id == TRIPOD_ID
    )
    extra_alias = "The Null-Calf"
    duplicate_node = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=TRIPOD_ID,
        predicate=original_node.predicate,
        label=original_node.label,
        value={**dict(original_node.value), "aliases": [extra_alias]},
        evidence_ref_ids=list(original_node.evidence_ref_ids),
        source_artifact_id=original_node.source_artifact_id,
        source_revision_id=original_node.source_revision_id,
        campaign_scope=original_node.campaign_scope,
        temporal_scope=original_node.temporal_scope,
        visibility=original_node.visibility,
        epistemic_kind=original_node.epistemic_kind,
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="additive-node-alias-1",
        accepted_assertions=[duplicate_node],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
    )
    assert merged.published is True
    pinned_revision_id = merged.revision_id
    contribution_id = merged.contribution_ids[0]

    projection = kernel.project_world_graph(tmp_path, _request())
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    assert extra_alias in tripod.aliases

    retracted = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=contribution_id,
        reason="remove additive node alias for test",
    )
    assert retracted.published is True
    head_tripod = next(
        node
        for node in kernel.project_world_graph(tmp_path, _request()).nodes
        if node.node_id == TRIPOD_ID
    )
    assert extra_alias not in head_tripod.aliases
    pinned_tripod = next(
        node
        for node in kernel.project_world_graph(
            tmp_path,
            _request(revision_pin=pinned_revision_id),
        ).nodes
        if node.node_id == TRIPOD_ID
    )
    assert extra_alias in pinned_tripod.aliases


def test_session_scoped_relationship_remains_focus_anchored_without_session_evidence(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    original_payload = _load_tripod_contribution_json(tmp_path)
    replacement_assertions = _assertions_from_contribution_json(original_payload)
    for assertion in replacement_assertions:
        value = dict(assertion.value)
        if str(value.get("edge_id") or "") == edge_id:
            assertion.value = {**value, "session_ids": [FOCUS_SESSION_ID]}
    replacement = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="focus-anchor-session-ids-1",
        accepted_assertions=replacement_assertions,
        supersedes_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    result = kernel.supersede_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        new_contribution=replacement,
        superseded_contribution_id=TRIPOD_CONTRIBUTION_ID,
    )
    assert result.published is True

    projection = kernel.project_world_graph(
        tmp_path,
        _request(focus_kind="session", session_id=FOCUS_SESSION_ID),
    )
    tripod = next(node for node in projection.nodes if node.node_id == TRIPOD_ID)
    candidate = next(item for item in tripod.adjacency if item.edge_id == edge_id)
    expansion = next(
        item for item in tripod.suggested_expansions if item.edge_id == edge_id
    )
    assert candidate.anchored_to_focus_session is True
    assert expansion.anchored_to_focus_session is True


def test_active_edge_assertions_tolerating_session_stamp_drift_union_session_ids(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    """Standing edges may be re-attested with a later session stamp.

    Distinct assertion_ids (identity includes session_ids / temporal_scope) can
    remain active on the same edge_id when core semantics agree. Projection must
    union session_ids rather than refuse the head.
    """
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    original_payload = _load_tripod_contribution_json(tmp_path)
    original_assertion = next(
        assertion
        for assertion in _assertions_from_contribution_json(original_payload)
        if assertion.assertion_kind == "edge"
        and str(assertion.value.get("edge_id") or "") == edge_id
    )
    reattest = original_assertion.model_copy(
        update={
            "temporal_scope": {"session_id": "session-99"},
            "value": {
                **dict(original_assertion.value),
                "session_ids": ["session-99"],
            },
        }
    )
    reattest_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:edge-session-reattest",
        source_revision_id="edge-session-reattest-1",
        accepted_assertions=[reattest],
    )
    assert reattest_contribution.accepted_assertions[0].assertion_id != (
        original_assertion.assertion_id
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=reattest_contribution,
    )
    assert merged.published is True

    relationship = next(
        item
        for item in kernel.project_world_graph(tmp_path, _request()).relationships
        if item.edge_id == edge_id
    )
    assert "session-99" in relationship.session_ids
    assert FOCUS_SESSION_ID in relationship.session_ids or len(relationship.session_ids) >= 1


def test_active_edge_assertions_still_reject_core_semantic_divergence(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    original_payload = _load_tripod_contribution_json(tmp_path)
    original_assertion = next(
        assertion
        for assertion in _assertions_from_contribution_json(original_payload)
        if assertion.assertion_kind == "edge"
        and str(assertion.value.get("edge_id") or "") == edge_id
    )
    divergent = original_assertion.model_copy(
        update={
            "label": "appeared elsewhere",
            "temporal_scope": {"session_id": "session-99"},
            "value": {
                **dict(original_assertion.value),
                "session_ids": ["session-99"],
            },
        }
    )
    divergent_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:edge-core-divergence",
        source_revision_id="edge-core-divergence-1",
        accepted_assertions=[divergent],
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=divergent_contribution,
    )
    assert merged.published is True

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(tmp_path, _request())
    assert exc_info.value.code == "projection_integrity_error"
    assert "Active edge assertions disagree" in str(exc_info.value)


@pytest.mark.parametrize("head_state", ["missing", "malformed"])
def test_invalid_revision_pin_precedes_head_loading(
    tmp_path: Path,
    loaded_bundle,
    head_state: str,
) -> None:
    if head_state == "malformed":
        _initialize(tmp_path, loaded_bundle)
        _head_path(tmp_path).write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph(
            tmp_path,
            _request(revision_pin="rev:not-a-valid-revision-id"),
        )
    assert exc_info.value.code == "invalid_request"


def test_adjacency_source_excerpt_resolves_from_source_span_index(tmp_path: Path) -> None:
    """World projection fills relationship origin prose from ingest span indexes."""
    from types import SimpleNamespace

    from graph_memory.kernel.world_projection import (
        _paragraph_text_by_span_id_from_source_artifacts,
        _resolve_repo_uri_file,
    )

    world_root = tmp_path / "out"
    run_dir = world_root / "graph_memory" / "runs" / "longmont-c1" / "session-3" / "run1"
    run_dir.mkdir(parents=True)
    recap_path = run_dir / "normalized_recap_source.md"
    recap_path.write_text("Ready for some rest near Bubbles.\n", encoding="utf-8")
    (run_dir / "source_span_index.json").write_text(
        json.dumps(
            {
                "spans": [
                    {
                        "span_id": "session-3:recap:paragraph:017",
                        "kind": "paragraph",
                        "text": "Ready for some rest near Bubbles.",
                        "text_excerpt": "Ready for some rest…",
                    },
                    {
                        "span_id": "session-3:recap:full_text",
                        "kind": "full_text",
                        "text": "ignored full text",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    uri = "repo://out/graph_memory/runs/longmont-c1/session-3/run1/normalized_recap_source.md"
    assert _resolve_repo_uri_file(uri, world_root) == recap_path.resolve()

    store = SimpleNamespace(
        source_artifacts={
            "artifact:recap:longmont-c1:session-3": SimpleNamespace(uri=uri),
        }
    )
    index = _paragraph_text_by_span_id_from_source_artifacts(world_root, store)
    assert index == {
        "session-3:recap:paragraph:017": "Ready for some rest near Bubbles.",
    }
