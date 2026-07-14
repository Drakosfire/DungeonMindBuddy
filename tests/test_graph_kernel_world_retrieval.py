"""Kernel World Graph retrieval + source-anchor admission tests (PR010A)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import graph_memory.kernel as kernel
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.kernel.world_retrieval import WorldGraphRetrievalError
from graph_memory.retrieval.models import (
    RETRIEVAL_RESULT_SCHEMA,
    RETRIEVAL_SEARCH_REQUEST_SCHEMA,
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
    RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphEvidenceTarget,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalBounds,
    WorldGraphRetrievalFocus,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
)
from graph_memory.retrieval.source_reader import (
    SourceReadError,
    read_graph_data_json_pointer_anchor,
    read_repo_heading_anchor,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = "c8eb7e6ca7e735c40822cb1e6835f9949f2cd915b57f5704e7b4daeb72cf2fca"
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "f69c69f271c427209860d902636347b70fea5920"
ACTOR = "gm"

TRIPOD_ID = "threat:tripod-null-calf"
TRIPOD_CONTRIBUTION_ID = "contribution:022187fdefdf4557"
EVENT_ID = "event:longmont-c2:session-23:mireward-gate-battle"
LOCATION_MIREWARD_ID = "location:mireward"
PARTY_ID = "party:questionable-company"
MIRATHORN_ID = "location:mirathorn"

TRIPOD_NODE_EVIDENCE_REF_ID = "evidence:bundle:v1:statblock:tripod-null-calf"
MIRATHORN_EVIDENCE_REF_ID = "evidence:corpus:worldbuilding:mirathorn"
MIRATHORN_RELATIVE_PATH = (
    "corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/"
    "The City of Mirathorn.md"
)

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


def _initialization_receipt_path(root: Path) -> Path:
    return root / "graph_memory" / "worlds" / WORLD_ID / "initialization" / "initial.json"


def _initialize(root: Path, bundle) -> kernel.WorldInitializationResult:
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _context(
    *,
    world_id: str = WORLD_ID,
    campaign_id: str = CAMPAIGN_ID,
    admissibility: str = "gm",
    revision_pin: str | None = None,
) -> dict:
    return {
        "worldId": world_id,
        "campaignId": campaign_id,
        "focus": {"kind": "none"},
        "admissibility": admissibility,
        "revisionPin": revision_pin,
    }


def _wire_overrides(**overrides) -> dict:
    """Map Python helper kwargs onto camelCase wire keys for alias-only models."""
    alias_map = {
        "world_id": "worldId",
        "campaign_id": "campaignId",
        "revision_pin": "revisionPin",
        "query_text": "queryText",
        "node_id": "nodeId",
        "seed_node_ids": "seedNodeIds",
        "max_depth": "maxDepth",
        "anchor_id": "anchorId",
        "max_chars": "maxChars",
        "admissibility": "admissibility",
        "focus": "focus",
        "bounds": "bounds",
        "target": "target",
        "schema": "schema",
    }
    payload: dict = {}
    for key, value in overrides.items():
        wire_key = alias_map.get(key, key)
        if hasattr(value, "model_dump"):
            payload[wire_key] = value.model_dump(mode="json", by_alias=True)
        else:
            payload[wire_key] = value
    return payload


def _bounds(**overrides) -> WorldGraphRetrievalBounds:
    payload = {
        "maxNodes": 8,
        "maxRelationships": 16,
        "maxAttributes": 24,
        "maxSourceAnchors": 24,
        **{
            {
                "max_nodes": "maxNodes",
                "max_relationships": "maxRelationships",
                "max_attributes": "maxAttributes",
                "max_source_anchors": "maxSourceAnchors",
            }.get(key, key): value
            for key, value in overrides.items()
        },
    }
    return WorldGraphRetrievalBounds.model_validate(payload)


def _search_request(query_text: str, **overrides) -> WorldGraphSearchRequest:
    payload = {
        "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
        "queryText": query_text,
        **_context(),
        **_wire_overrides(**overrides),
    }
    return WorldGraphSearchRequest.model_validate(payload)


def _object_request(node_id: str, **overrides) -> WorldGraphObjectRequest:
    payload = {
        "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        "nodeId": node_id,
        **_context(),
        **_wire_overrides(**overrides),
    }
    return WorldGraphObjectRequest.model_validate(payload)


def _neighborhood_request(
    seed_node_ids: list[str], *, max_depth: int = 1, **overrides
) -> WorldGraphNeighborhoodRequest:
    payload = {
        "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
        "seedNodeIds": seed_node_ids,
        "maxDepth": max_depth,
        **_context(),
        **_wire_overrides(**overrides),
    }
    return WorldGraphNeighborhoodRequest.model_validate(payload)


def _evidence_request(target: WorldGraphEvidenceTarget, **overrides) -> WorldGraphEvidenceRequest:
    payload = {
        "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
        "target": target.model_dump(mode="json", by_alias=True),
        **_context(),
        **_wire_overrides(**overrides),
    }
    return WorldGraphEvidenceRequest.model_validate(payload)


def _anchor_read_request(anchor_id: str, **overrides) -> WorldGraphSourceAnchorReadRequest:
    payload = {
        "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
        "anchorId": anchor_id,
        **_context(),
        **_wire_overrides(**overrides),
    }
    return WorldGraphSourceAnchorReadRequest.model_validate(payload)


# --- Search ---------------------------------------------------------------


def test_search_natural_language_question_selects_tripod(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.search_campaign_graph(
        tmp_path,
        _search_request("What do we know about Tripod Null-Calf at the North Gate?"),
    )

    assert result.schema_ == RETRIEVAL_RESULT_SCHEMA
    assert result.operation == "search"
    assert result.outcome in ("enough", "partial")
    assert result.matched_node_ids[0] == TRIPOD_ID
    assert result.match_reasons[TRIPOD_ID]
    assert result.snapshot is not None
    assert result.snapshot.world_id == WORLD_ID


def test_search_absent_phrase_returns_empty(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.search_campaign_graph(
        tmp_path,
        _search_request("Completely unrelated phrase not present anywhere in the graph"),
    )
    assert result.outcome == "empty"
    assert result.matched_node_ids == []


def test_search_absent_phrase_never_calls_legacy_manifest_lookup(
    tmp_path: Path, loaded_bundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR010A retrieval must be graph-only: it must never fall back to a
    manifest/corpus-index lookup, even when the graph has no match."""
    _initialize(tmp_path, loaded_bundle)

    def _boom(*_args, **_kwargs):
        raise AssertionError("legacy manifest/corpus lookup must never be called")

    monkeypatch.setattr("src.live_play.manifest_context_query.run_query", _boom, raising=True)
    monkeypatch.setattr(
        "src.live_play.manifest_context_query.retrieve_candidates", _boom, raising=True
    )
    monkeypatch.setattr(
        "src.live_play.manifest_context_query.build_context_packet", _boom, raising=True
    )
    monkeypatch.setattr(
        "src.live_play.live_query_context.run_context_lookup_turn", _boom, raising=True
    )

    result = kernel.search_campaign_graph(
        tmp_path,
        _search_request("Completely unrelated phrase not present anywhere in the graph"),
    )
    assert result.outcome == "empty"


def test_search_relationship_and_related_node_text_participates_in_ranking(
    tmp_path: Path, loaded_bundle
) -> None:
    """A query matching only the connected event node's label / edge predicate
    (never Tripod's own label, aliases, kind, role, or attribute text) must
    still surface Tripod through the relationship-extended ranking."""
    _initialize(tmp_path, loaded_bundle)
    result = kernel.search_campaign_graph(tmp_path, _search_request("Mireward Gate Battle"))

    assert TRIPOD_ID in result.matched_node_ids
    reasons = result.match_reasons.get(TRIPOD_ID, [])
    assert any("relationship_or_related_node" in reason for reason in reasons)


def test_search_seed_node_ids_are_prioritized_and_missing_seeds_reported(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.search_campaign_graph(
        tmp_path,
        _search_request(
            "irrelevant text",
            seed_node_ids=[TRIPOD_ID, "threat:does-not-exist"],
        ),
    )
    assert result.matched_node_ids[0] == TRIPOD_ID
    assert result.coverage.missing_seed_node_ids == ["threat:does-not-exist"]
    assert result.outcome == "partial"


def test_search_respects_bounds_and_reports_truncation(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.search_campaign_graph(
        tmp_path,
        _search_request(
            "location event party threat",
            bounds=_bounds(max_nodes=1),
        ),
    )
    assert len(result.nodes) <= 1


def test_search_unknown_world_returns_unavailable_outcome(tmp_path: Path) -> None:
    result = kernel.search_campaign_graph(tmp_path, _search_request("anything"))
    assert result.outcome == "unavailable"
    assert result.snapshot is None


def test_search_invalid_revision_pin_format_raises_422(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.search_campaign_graph(
            tmp_path,
            _search_request("anything", revision_pin="rev:not-a-valid-revision-id"),
        )
    assert exc_info.value.status_code == 422


def test_search_unsupported_admissibility_raises_422(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.search_campaign_graph(
            tmp_path,
            _search_request("anything", admissibility="player"),
        )
    assert exc_info.value.status_code == 422


def test_search_campaign_mismatch_raises_409(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.search_campaign_graph(
            tmp_path,
            _search_request("anything", campaign_id="foreign-campaign"),
        )
    assert exc_info.value.status_code == 409


def test_search_extra_field_is_rejected_by_model() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                **_context(),
                "queryText": "hello",
                "unexpectedField": "nope",
            }
        )


def test_replayed_search_is_deterministic(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    first = kernel.search_campaign_graph(tmp_path, _search_request("Tripod Null-Calf"))
    second = kernel.search_campaign_graph(tmp_path, _search_request("Tripod Null-Calf"))
    assert first.matched_node_ids == second.matched_node_ids
    assert [a.anchor_id for a in first.source_anchors] == [
        a.anchor_id for a in second.source_anchors
    ]


# --- Object lookup ---------------------------------------------------------


def test_object_exact_lookup_returns_tripod(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_campaign_object(tmp_path, _object_request(TRIPOD_ID))
    assert result.outcome == "enough"
    assert result.resolved_node_id == TRIPOD_ID
    assert result.nodes[0].node_id == TRIPOD_ID
    assert any(r.target_node_id == EVENT_ID for r in result.relationships)


def test_object_lookup_by_label_text_never_resolves(tmp_path: Path, loaded_bundle) -> None:
    """Object lookup is durable-ID only; a label string must never rebind."""
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_campaign_object(tmp_path, _object_request("Tripod Null-Calf"))
    assert result.outcome == "empty"
    assert result.resolved_node_id is None
    assert result.nodes == []


def test_object_lookup_unknown_id_returns_empty(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_campaign_object(tmp_path, _object_request("threat:does-not-exist"))
    assert result.outcome == "empty"
    assert result.requested_node_id == "threat:does-not-exist"


def test_object_lookup_follows_active_identity_redirect(
    tmp_path: Path, loaded_bundle
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    merged_store, _decision = kernel.merge_identity(
        store,
        world_id=WORLD_ID,
        source_node_id=LOCATION_MIREWARD_ID,
        target_node_id=PARTY_ID,
        actor=ACTOR,
        reason="test redirect for PR010A object lookup",
    )
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        merged_store,
        operation_ids=["op:test-pr010a-merge-redirect"],
    )

    lookup = kernel.get_campaign_object(tmp_path, _object_request(LOCATION_MIREWARD_ID))
    assert lookup.requested_node_id == LOCATION_MIREWARD_ID
    assert lookup.resolved_node_id == PARTY_ID
    assert lookup.nodes[0].node_id == PARTY_ID
    assert any(d.code == "active_identity_redirect" for d in lookup.diagnostics)

    # The merge must not make the survivor resolvable by the merged-away
    # node's former label text -- durable-ID-only lookup still applies.
    label_lookup = kernel.get_campaign_object(tmp_path, _object_request("Mireward"))
    assert label_lookup.outcome == "empty"
    _ = result


def test_object_unknown_world_returns_unavailable_outcome(tmp_path: Path) -> None:
    result = kernel.get_campaign_object(tmp_path, _object_request(TRIPOD_ID))
    assert result.outcome == "unavailable"


# --- Neighborhood -----------------------------------------------------------


def test_neighborhood_depth_one_reaches_event(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([TRIPOD_ID], max_depth=1)
    )
    node_ids = {node.node_id for node in result.nodes}
    assert TRIPOD_ID in node_ids
    assert EVENT_ID in node_ids
    assert LOCATION_MIREWARD_ID not in node_ids


def test_neighborhood_depth_two_reaches_gate_battle_context(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([TRIPOD_ID], max_depth=2)
    )
    node_ids = {node.node_id for node in result.nodes}
    assert {TRIPOD_ID, EVENT_ID, LOCATION_MIREWARD_ID, PARTY_ID}.issubset(node_ids)


def test_neighborhood_is_cycle_safe(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    # Traversing from both endpoints of the same edge at depth 2 must not
    # infinite-loop or duplicate nodes/edges.
    result = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([TRIPOD_ID, EVENT_ID], max_depth=2)
    )
    node_ids = [node.node_id for node in result.nodes]
    assert len(node_ids) == len(set(node_ids))
    edge_ids = [rel.edge_id for rel in result.relationships]
    assert len(edge_ids) == len(set(edge_ids))


def test_neighborhood_direction_is_endpoint_relative(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )

    from_tripod = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([TRIPOD_ID], max_depth=1)
    )
    from_event = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([EVENT_ID], max_depth=1)
    )

    tripod_edge = next(r for r in from_tripod.relationships if r.edge_id == edge_id)
    event_edge = next(r for r in from_event.relationships if r.edge_id == edge_id)
    assert tripod_edge.direction == "outbound"
    assert event_edge.direction == "inbound"


def test_neighborhood_missing_seed_is_partial(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_object_neighborhood(
        tmp_path,
        _neighborhood_request([TRIPOD_ID, "threat:does-not-exist"], max_depth=1),
    )
    assert result.coverage.missing_seed_node_ids == ["threat:does-not-exist"]
    assert result.outcome == "partial"


def test_neighborhood_max_depth_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        WorldGraphNeighborhoodRequest.model_validate(
            {
                "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                **_context(),
                "seedNodeIds": [TRIPOD_ID],
                "maxDepth": 3,
            }
        )


def test_neighborhood_depth_ordered_cap_prefers_depth_one_before_depth_two(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_object_neighborhood(
        tmp_path,
        _neighborhood_request(
            [TRIPOD_ID],
            max_depth=2,
            bounds=_bounds(max_nodes=2),
        ),
    )
    node_ids = [node.node_id for node in result.nodes]
    assert node_ids == [TRIPOD_ID, EVENT_ID]
    assert result.outcome == "truncated"
    assert "nodes" in result.coverage.truncated_fields


def test_neighborhood_seed_cap_truncates_in_request_order(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_object_neighborhood(
        tmp_path,
        _neighborhood_request(
            [TRIPOD_ID, EVENT_ID, LOCATION_MIREWARD_ID],
            max_depth=1,
            bounds=_bounds(max_nodes=2),
        ),
    )
    assert [node.node_id for node in result.nodes] == [TRIPOD_ID, EVENT_ID]
    assert result.outcome == "truncated"


# --- Evidence ---------------------------------------------------------------


def test_evidence_for_node_returns_opaque_anchors(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="node", id=TRIPOD_ID)),
    )
    assert result.outcome in ("enough", "partial", "truncated")
    assert result.source_anchors
    anchor = result.source_anchors[0]
    assert anchor.anchor_id.startswith("source-anchor:v1:")
    assert anchor.revision_id == result.snapshot.revision_id
    # Anchors are opaque: no caller-usable path/uri field is exposed.
    dumped = anchor.model_dump(mode="json", by_alias=True)
    assert "uri" not in dumped
    assert "path" not in dumped
    assert "locator" not in dumped
    assert any(
        a.evidence_ref_id == TRIPOD_NODE_EVIDENCE_REF_ID for a in result.source_anchors
    )


def test_evidence_for_unknown_target_returns_empty(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="node", id="threat:does-not-exist")),
    )
    assert result.outcome == "empty"
    assert result.source_anchors == []


def test_evidence_for_relationship_returns_opaque_anchors(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    result = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="relationship", id=edge_id)),
    )
    assert result.outcome in ("enough", "partial", "truncated")
    assert len(result.relationships) == 1
    assert result.relationships[0].edge_id == edge_id
    assert result.source_anchors
    dumped = result.source_anchors[0].model_dump(mode="json", by_alias=True)
    assert "uri" not in dumped
    assert "path" not in dumped
    assert edge_id in result.source_anchors[0].supporting_graph_object_ids


def test_evidence_for_anchorless_node_returns_partial_with_missing_source_anchors(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    node_id = "location:anchorless-evidence-target"
    source_artifact_id = "graph-native:test:anchorless-evidence-target"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label="Anchorless Evidence Target",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "kind": "location",
            "role": "location",
            "source_domains": ["manual_seed"],
            "aliases": ["Anchorless Evidence Target"],
            "canon_state": "canonical",
            "evidence": [],
            "source_artifacts": [],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=source_artifact_id,
        source_revision_id="anchorless-evidence-target-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True

    result = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="node", id=node_id)),
    )
    assert result.outcome == "partial"
    assert result.nodes
    assert result.nodes[0].node_id == node_id
    assert result.source_anchors == []
    diagnostic_codes = {d.code for d in result.diagnostics}
    assert "missing_source_anchors" in diagnostic_codes or "missing_evidence_ref_ids" in diagnostic_codes


def test_evidence_for_attribute_returns_opaque_anchors(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    object_result = kernel.get_campaign_object(tmp_path, _object_request(TRIPOD_ID))
    assert object_result.attributes, "expected Tripod attributes from published graph"
    assertion_id = object_result.attributes[0].assertion_id
    result = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="attribute", id=assertion_id)),
    )
    assert result.outcome in ("enough", "partial", "truncated")
    assert len(result.attributes) == 1
    assert result.attributes[0].assertion_id == assertion_id
    assert result.source_anchors
    assert assertion_id in result.source_anchors[0].supporting_assertion_ids
    dumped = result.source_anchors[0].model_dump(mode="json", by_alias=True)
    assert "uri" not in dumped
    assert "path" not in dumped


# --- Source anchor read ------------------------------------------------------


def _first_anchor_for_node(root: Path, node_id: str, *, evidence_ref_id: str | None = None):
    result = kernel.get_object_evidence(
        root, _evidence_request(WorldGraphEvidenceTarget(kind="node", id=node_id))
    )
    if evidence_ref_id is None:
        return result.source_anchors[0]
    return next(a for a in result.source_anchors if a.evidence_ref_id == evidence_ref_id)


def test_read_source_anchor_graph_data_json_pointer(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    assert anchor.locator_kind == "json_pointer"
    assert anchor.readable is True

    read_result = kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert read_result.schema_ == RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA
    assert read_result.outcome == "enough"
    assert read_result.media_type == "application/json"
    assert '"label": "Tripod Null-Calf"' in (read_result.content or "")
    assert read_result.content_sha256


def test_repo_heading_anchor_without_admitted_digest_is_unreadable(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    evidence = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="node", id=MIRATHORN_ID)),
    )
    mirathorn_anchor = next(
        a
        for a in evidence.source_anchors
        if a.evidence_ref_id == MIRATHORN_EVIDENCE_REF_ID
    )
    assert mirathorn_anchor.locator_kind == "heading"
    assert mirathorn_anchor.readable is True

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    artifact = store.source_artifacts[mirathorn_anchor.source_artifact_id]
    stripped = artifact.model_copy(update={})
    # Drop revision-bound content digest while keeping the URI/locator shape.
    extra = dict(stripped.model_extra or {})
    extra.pop("content_sha256", None)
    object.__setattr__(stripped, "__pydantic_extra__", extra)
    artifacts = dict(store.source_artifacts)
    artifacts[mirathorn_anchor.source_artifact_id] = stripped
    mutated = store.model_copy(update={"source_artifacts": artifacts})
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        mutated,
        operation_ids=["op:test-pr010a-strip-repo-content-digest"],
    )

    evidence_after = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="node", id=MIRATHORN_ID)),
    )
    after_anchor = next(
        a
        for a in evidence_after.source_anchors
        if a.evidence_ref_id == MIRATHORN_EVIDENCE_REF_ID
    )
    assert after_anchor.readable is False
    assert after_anchor.locator_kind == "heading"
    assert evidence_after.outcome == "partial"

    read_result = kernel.read_source_anchor(
        tmp_path, _anchor_read_request(after_anchor.anchor_id)
    )
    assert read_result.outcome == "partial"
    assert read_result.content is None


def test_historical_graph_data_read_survives_contribution_retraction(
    tmp_path: Path, loaded_bundle
) -> None:
    """Lifecycle-neutral source digests keep pinned graph-data reads readable.

    After ledger retraction mutates contribution ``status``/``diagnostics``, a
    revision pin that still admits the contribution must verify against the
    lifecycle-neutral source digest, not the full ledger envelope.
    """
    init = _initialize(tmp_path, loaded_bundle)
    pinned_revision = init.initial_head_revision_id
    assert pinned_revision

    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    assert anchor.readable is True

    retract_result = kernel.retract_graph_contribution(
        tmp_path,
        world_id=WORLD_ID,
        contribution_id=TRIPOD_CONTRIBUTION_ID,
        reason="pr010a-historical-lifecycle-read",
    )
    assert retract_result.published is True

    # Current head may no longer expose the retracted object's anchors.
    head_evidence = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="node", id=TRIPOD_ID)),
    )
    assert head_evidence.outcome in ("partial", "unavailable", "enough", "empty")

    pinned_read = kernel.read_source_anchor(
        tmp_path,
        _anchor_read_request(anchor.anchor_id, revision_pin=pinned_revision),
    )
    assert pinned_read.outcome == "enough"
    assert '"label": "Tripod Null-Calf"' in (pinned_read.content or "")


def test_read_source_anchor_mirathorn_stop_condition_heading_not_found(
    tmp_path: Path, loaded_bundle, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """STOP CONDITION proof for approved handoff scenario 6 (Mirathorn heading read).

    The admitted Mirathorn locator ``heading:The City of Mirathorn`` does not match
    any Markdown heading in the real corpus file — the title exists only in YAML
    frontmatter. Positive scenario 6 therefore cannot complete without a prerequisite
    data-correction slice or an operator waiver.
    """
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, MIRATHORN_ID, evidence_ref_id=MIRATHORN_EVIDENCE_REF_ID
    )
    assert anchor.locator_kind == "heading"
    assert anchor.readable is True

    fake_repo_root = tmp_path_factory.mktemp("fake-repo-root")
    dest = fake_repo_root / MIRATHORN_RELATIVE_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((REPO_ROOT / MIRATHORN_RELATIVE_PATH).read_bytes())

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(
            tmp_path,
            _anchor_read_request(anchor.anchor_id),
            repo_root=fake_repo_root,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "heading_not_found"


def test_read_source_anchor_repo_heading_exact_match_with_digest(
    tmp_path: Path, loaded_bundle, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Proves the repo heading reader contract only (synthetic exact-match fixture).

    This is NOT the Mirathorn acceptance scenario — see
    ``test_read_source_anchor_mirathorn_stop_condition_heading_not_found``.
    """
    _initialize(tmp_path, loaded_bundle)
    heading_text = "PR010A Synthetic Section"
    relative_path = "corpus/test/pr010a-synthetic-heading.md"
    markdown = (
        "---\n"
        "title: \"Synthetic Doc\"\n"
        "campaign: longmont-c2\n"
        "---\n"
        "\n"
        f"# {heading_text}\n"
        "\n"
        "Synthetic section body for PR010A heading read.\n"
    )
    raw_bytes = markdown.encode("utf-8")
    content_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    fake_repo_root = tmp_path_factory.mktemp("fake-repo-root-synthetic")
    dest = fake_repo_root / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw_bytes)

    source_artifact_id = "graph-native:test:pr010a-synthetic-heading"
    evidence_ref_id = "evidence:test:pr010a-synthetic-heading"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="location:pr010a-synthetic-heading",
        label="PR010A Synthetic Heading",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "kind": "location",
            "role": "location",
            "source_domains": ["manual_seed"],
            "aliases": ["PR010A Synthetic Heading"],
            "canon_state": "canonical",
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": f"heading:{heading_text}",
                }
            ],
            "source_artifacts": [
                {
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": f"repo://{relative_path}",
                    "content_sha256": content_sha256,
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=source_artifact_id,
        source_revision_id="pr010a-synthetic-heading-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True

    anchor = _first_anchor_for_node(
        tmp_path, "location:pr010a-synthetic-heading", evidence_ref_id=evidence_ref_id
    )
    read_result = kernel.read_source_anchor(
        tmp_path,
        _anchor_read_request(anchor.anchor_id),
        repo_root=fake_repo_root,
    )
    assert read_result.outcome == "enough"
    assert read_result.media_type == "text/markdown"
    assert "Synthetic section body" in (read_result.content or "")
    assert read_result.content_sha256 == content_sha256
    assert read_result.line_start == 6
    assert read_result.line_end == 8


def test_read_source_anchor_fails_closed_after_contribution_payload_mutation(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    assert anchor.locator_kind == "json_pointer"

    first_read = kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert first_read.outcome in ("enough", "truncated")
    assert first_read.content

    ledger_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / "contribution__022187fdefdf4557.json"
    )
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger_payload["source_revision_id"] = "tampered-pr010a"
    ledger_path.write_text(
        json.dumps(ledger_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "source_integrity_error"


def test_read_source_anchor_fails_closed_after_source_mutation(
    tmp_path: Path, loaded_bundle, tmp_path_factory: pytest.TempPathFactory
) -> None:
    _initialize(tmp_path, loaded_bundle)
    heading_text = "PR010A Mutation Section"
    relative_path = "corpus/test/pr010a-mutation-heading.md"
    markdown = f"# {heading_text}\nOriginal body.\n"
    raw_bytes = markdown.encode("utf-8")
    content_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    fake_repo_root = tmp_path_factory.mktemp("fake-repo-root-mutate")
    dest = fake_repo_root / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw_bytes)

    source_artifact_id = "graph-native:test:pr010a-mutation-heading"
    evidence_ref_id = "evidence:test:pr010a-mutation-heading"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="location:pr010a-mutation-heading",
        label="PR010A Mutation Heading",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "kind": "location",
            "role": "location",
            "source_domains": ["manual_seed"],
            "aliases": ["PR010A Mutation Heading"],
            "canon_state": "canonical",
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": f"heading:{heading_text}",
                }
            ],
            "source_artifacts": [
                {
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": f"repo://{relative_path}",
                    "content_sha256": content_sha256,
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=source_artifact_id,
        source_revision_id="pr010a-mutation-heading-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True

    anchor = _first_anchor_for_node(
        tmp_path, "location:pr010a-mutation-heading", evidence_ref_id=evidence_ref_id
    )
    first_read = kernel.read_source_anchor(
        tmp_path,
        _anchor_read_request(anchor.anchor_id),
        repo_root=fake_repo_root,
    )
    assert first_read.outcome == "enough"

    dest.write_text(f"# {heading_text}\nTampered content.\n")

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(
            tmp_path,
            _anchor_read_request(anchor.anchor_id),
            repo_root=fake_repo_root,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "source_integrity_error"


def test_read_source_anchor_unknown_anchor_returns_empty(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    fake_anchor_id = "source-anchor:v1:" + "0" * 64
    read_result = kernel.read_source_anchor(tmp_path, _anchor_read_request(fake_anchor_id))
    assert read_result.outcome == "empty"


def test_read_source_anchor_wrong_revision_context_returns_no_content(
    tmp_path: Path, loaded_bundle
) -> None:
    """An anchor id derived at one revision must not resolve at a different
    revision of the same world, even though both are otherwise valid."""
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    original_revision_id = anchor.revision_id

    alias_assertion = kernel.build_assertion(
        assertion_kind="alias",
        acceptance_state="accepted",
        subject_node_id=TRIPOD_ID,
        label="PR010A Revision Bump Alias",
        campaign_scope=CAMPAIGN_ID,
        value={"alias": "PR010A Revision Bump Alias"},
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:test:pr010a-revision-bump",
        source_revision_id="pr010a-revision-bump-1",
        accepted_assertions=[alias_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True
    assert merged.revision_id != original_revision_id

    read_result = kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert read_result.outcome == "empty"


def test_read_source_anchor_wrong_focus_context_returns_no_content(
    tmp_path: Path, loaded_bundle
) -> None:
    """Anchors are bound to focus context; a session focus cannot open a none-focus anchor."""
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    read_result = kernel.read_source_anchor(
        tmp_path,
        _anchor_read_request(
            anchor.anchor_id,
            focus=WorldGraphRetrievalFocus.model_validate(
                {"kind": "session", "sessionId": FOCUS_SESSION_ID}
            ),
        ),
    )
    assert read_result.outcome == "empty"
    assert not read_result.content


def test_read_source_anchor_unsupported_locator_is_partial(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    unsupported_source_artifact_id = "graph-native:test:unsupported-locator-artifact"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="threat:unsupported-locator-test",
        label="Unsupported Locator Test",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=unsupported_source_artifact_id,
        value={
            "kind": "threat",
            "role": "threat",
            "source_domains": ["manual_seed"],
            "aliases": ["Unsupported Locator Test"],
            "canon_state": "canonical",
            "evidence": [
                {
                    "evidence_ref_id": "evidence:test:unsupported-locator",
                    "source_artifact_id": unsupported_source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": "unsupported-scheme:not-a-real-locator",
                }
            ],
            "source_artifacts": [
                {
                    "source_artifact_id": unsupported_source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": "https://example.invalid/not-repo-or-graph-data",
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=unsupported_source_artifact_id,
        source_revision_id="unsupported-locator-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True

    anchor = _first_anchor_for_node(tmp_path, "threat:unsupported-locator-test")
    assert anchor.readable is False
    assert anchor.locator_kind == "unsupported"

    read_result = kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert read_result.outcome == "partial"
    assert read_result.content is None


def test_read_source_anchor_unknown_world_returns_unavailable(tmp_path: Path) -> None:
    fake_anchor_id = "source-anchor:v1:" + "0" * 64
    result = kernel.read_source_anchor(tmp_path, _anchor_read_request(fake_anchor_id))
    assert result.outcome == "unavailable"


def test_anchor_id_is_deterministic_across_replay(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    first = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    second = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    assert first.anchor_id == second.anchor_id


def test_source_anchor_read_request_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                **_context(),
                "anchorId": "source-anchor:v1:" + "0" * 64,
                "path": "/etc/passwd",
            }
        )


def test_source_anchor_read_max_chars_hard_max_enforced() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                **_context(),
                "anchorId": "source-anchor:v1:" + "0" * 64,
                "maxChars": 999_999,
            }
        )


def test_search_request_rejects_snake_case_wire_keys() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "world_id": WORLD_ID,
                "campaign_id": CAMPAIGN_ID,
                "query_text": "hello",
            }
        )


def test_search_request_rejects_schema_underscore_key() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSearchRequest.model_validate(
            {
                "schema_": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                **_context(),
                "queryText": "hello",
            }
        )


def test_search_request_rejects_omitted_schema() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSearchRequest.model_validate(
            {
                **_context(),
                "queryText": "hello",
            }
        )


def test_search_request_rejects_nested_session_id_snake_case() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                **_context(),
                "queryText": "hello",
                "focus": {"kind": "session", "session_id": "session-1"},
            }
        )


# --- Projection-bound admission + source_reader adversarial proofs -----------


def test_read_source_anchor_denies_anchor_for_projection_omitted_object(
    tmp_path: Path, loaded_bundle
) -> None:
    """An active support for a projection-omitted object must not be readable.

    Keeps store-level support/evidence active while marking the object
    ``unsupported_assertion`` so projection omits it. Forge the deterministic
    anchor id for the *current* revision from raw store evidence; admission must
    still refuse content. Clearing support or reusing a pre-publish anchor id
    would only prove support retraction / revision mismatch, not admission.
    """
    from graph_memory.retrieval.models import compute_source_anchor_id

    _initialize(tmp_path, loaded_bundle)
    node_id = "threat:projection-omitted-anchor"
    evidence_ref_id = "evidence:test:projection-omitted-anchor"
    source_artifact_id = "graph-native:test:projection-omitted-anchor"
    locator = "unsupported-scheme:projection-omitted"

    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label="Projection Omitted Anchor",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=source_artifact_id,
        value={
            "kind": "threat",
            "role": "threat",
            "source_domains": ["manual_seed"],
            "aliases": ["Projection Omitted Anchor"],
            "canon_state": "canonical",
            "evidence": [
                {
                    "evidence_ref_id": evidence_ref_id,
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": locator,
                }
            ],
            "source_artifacts": [
                {
                    "source_artifact_id": source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": "https://example.invalid/projection-omitted",
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=source_artifact_id,
        source_revision_id="projection-omitted-anchor-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True

    before = kernel.get_campaign_object(tmp_path, _object_request(node_id))
    assert before.outcome in ("enough", "partial", "truncated")
    assert before.matched_node_ids == [node_id]

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    node = store.nodes[node_id]
    node_state = dict(node.state or {})
    node_state["memory_state"] = "unsupported_assertion"
    store.nodes[node_id] = node.model_copy(update={"state": node_state})

    retained_active_support = False
    for raw_support in store.assertion_support.values():
        support = dict(raw_support)
        if support.get("graph_object_id") != node_id:
            continue
        assert support.get("support_state") == "supported"
        assert support.get("active_contribution_ids")
        retained_active_support = True
        break
    assert retained_active_support, "omission test requires active support to remain"

    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-pr010a-omitted-node-anchor"],
    )

    after = kernel.get_campaign_object(tmp_path, _object_request(node_id))
    assert after.outcome == "empty"

    _head2, revision_after, store_after = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    evidence = store_after.evidence[evidence_ref_id]
    forged_anchor_id = compute_source_anchor_id(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus=WorldGraphRetrievalFocus(),
        admissibility="gm",
        revision_id=revision_after.revision_id,
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=source_artifact_id,
        locator_identity=evidence.locator or locator,
    )

    read_result = kernel.read_source_anchor(
        tmp_path, _anchor_read_request(forged_anchor_id)
    )
    assert read_result.outcome == "empty"
    assert read_result.content is None


def test_object_partial_when_unreadable_source_anchors_present(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    node_id = "threat:object-partial-unreadable"
    unsupported_source_artifact_id = "graph-native:test:object-partial-unreadable"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label="Object Partial Unreadable",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=unsupported_source_artifact_id,
        value={
            "kind": "threat",
            "role": "threat",
            "source_domains": ["manual_seed"],
            "aliases": ["Object Partial Unreadable"],
            "canon_state": "canonical",
            "evidence": [
                {
                    "evidence_ref_id": "evidence:test:object-partial-unreadable",
                    "source_artifact_id": unsupported_source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": "unsupported-scheme:not-readable",
                }
            ],
            "source_artifacts": [
                {
                    "source_artifact_id": unsupported_source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": "https://example.invalid/not-repo-or-graph-data",
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=unsupported_source_artifact_id,
        source_revision_id="object-partial-unreadable-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True

    result = kernel.get_campaign_object(tmp_path, _object_request(node_id))
    assert result.outcome == "partial"
    assert result.coverage.unreadable_anchor_ids


def test_neighborhood_partial_when_unreadable_source_anchors_present(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    node_id = "threat:neighborhood-partial-unreadable"
    unsupported_source_artifact_id = "graph-native:test:neighborhood-partial-unreadable"
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label="Neighborhood Partial Unreadable",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=unsupported_source_artifact_id,
        value={
            "kind": "threat",
            "role": "threat",
            "source_domains": ["manual_seed"],
            "aliases": ["Neighborhood Partial Unreadable"],
            "canon_state": "canonical",
            "evidence": [
                {
                    "evidence_ref_id": "evidence:test:neighborhood-partial-unreadable",
                    "source_artifact_id": unsupported_source_artifact_id,
                    "source_domain": "manual_seed",
                    "locator": "unsupported-scheme:not-readable",
                }
            ],
            "source_artifacts": [
                {
                    "source_artifact_id": unsupported_source_artifact_id,
                    "source_domain": "manual_seed",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": "https://example.invalid/not-repo-or-graph-data",
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=unsupported_source_artifact_id,
        source_revision_id="neighborhood-partial-unreadable-1",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True

    result = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([node_id], max_depth=1)
    )
    assert result.outcome == "partial"
    assert result.coverage.unreadable_anchor_ids


def test_neighborhood_multi_seed_exposes_direction_from_node_id(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    result = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([TRIPOD_ID, EVENT_ID], max_depth=1)
    )
    edge = next(rel for rel in result.relationships if rel.edge_id == edge_id)
    assert edge.direction_from_node_id in {TRIPOD_ID, EVENT_ID}
    assert edge.direction in {"outbound", "inbound"}
    if edge.direction_from_node_id == TRIPOD_ID:
        assert edge.direction == "outbound"
    else:
        assert edge.direction == "inbound"


def test_read_source_anchor_fails_closed_when_receipt_plan_digest_mutated(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    receipt_path = _initialization_receipt_path(tmp_path)
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["plan_digest"] = "deadbeef" * 8
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "source_integrity_error"


def test_read_source_anchor_fails_closed_when_receipt_attestation_mutated(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    receipt_path = _initialization_receipt_path(tmp_path)
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["approval_attestation"]["bundle_digest"] = "deadbeef" * 8
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "source_integrity_error"


def test_read_source_anchor_fails_closed_when_receipt_contributions_mutated(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    receipt_path = _initialization_receipt_path(tmp_path)
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["ordered_contributions"] = receipt_payload["ordered_contributions"][:-1]
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "source_integrity_error"


def test_read_source_anchor_malformed_receipt_returns_409(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    receipt_path = _initialization_receipt_path(tmp_path)
    receipt_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "source_integrity_error"


def test_read_source_anchor_missing_receipt_initial_head_returns_409(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    receipt_path = _initialization_receipt_path(tmp_path)
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["initial_head_revision_id"] = "rev:" + "0" * 32
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorldGraphRetrievalError) as exc_info:
        kernel.read_source_anchor(tmp_path, _anchor_read_request(anchor.anchor_id))
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "source_integrity_error"


def test_graph_data_anchor_without_immutable_digest_is_unreadable(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, TRIPOD_ID, evidence_ref_id=TRIPOD_NODE_EVIDENCE_REF_ID
    )
    assert anchor.locator_kind == "json_pointer"

    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    stripped_digests = dict(store.contribution_source_payload_sha256)
    stripped_digests.pop(TRIPOD_CONTRIBUTION_ID, None)
    mutated = store.model_copy(
        update={"contribution_source_payload_sha256": stripped_digests}
    )
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        mutated,
        operation_ids=["op:test-pr010a-strip-contribution-digest"],
    )

    evidence = kernel.get_object_evidence(
        tmp_path,
        _evidence_request(WorldGraphEvidenceTarget(kind="node", id=TRIPOD_ID)),
    )
    graph_data_anchor = next(
        anchor_item
        for anchor_item in evidence.source_anchors
        if anchor_item.evidence_ref_id == TRIPOD_NODE_EVIDENCE_REF_ID
    )
    assert graph_data_anchor.readable is False
    assert graph_data_anchor.locator_kind == "json_pointer"
    assert evidence.outcome == "partial"


def test_max_source_anchors_cap_does_not_create_anchor_gaps(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    result = kernel.get_campaign_object(
        tmp_path,
        _object_request(
            TRIPOD_ID,
            bounds=_bounds(max_source_anchors=1),
        ),
    )
    assert result.outcome == "truncated"
    assert "source_anchors" in result.coverage.truncated_fields
    assert result.coverage.missing_evidence_ref_ids == []
    assert not any(
        diagnostic.code == "missing_source_anchors" for diagnostic in result.diagnostics
    )


def test_source_reader_rejects_missing_content_digest(tmp_path: Path) -> None:
    relative_path = "docs/no-digest.md"
    dest = tmp_path / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("# Heading\nbody\n", encoding="utf-8")
    with pytest.raises(SourceReadError) as exc_info:
        read_repo_heading_anchor(
            repo_root=tmp_path,
            relative_path=relative_path,
            heading_text="Heading",
            expected_content_sha256=None,  # type: ignore[arg-type]
            max_chars=1000,
        )
    assert exc_info.value.code == "source_integrity_error"


def test_source_reader_rejects_repo_path_escape(tmp_path: Path) -> None:
    with pytest.raises(SourceReadError) as exc_info:
        read_repo_heading_anchor(
            repo_root=tmp_path,
            relative_path="../outside.md",
            heading_text="Escape",
            expected_content_sha256="a" * 64,
            max_chars=1000,
        )
    assert exc_info.value.code == "unsupported_locator"


def test_source_reader_rejects_ambiguous_heading(tmp_path: Path) -> None:
    relative_path = "docs/ambiguous.md"
    markdown = "# Same Heading\none\n# Same Heading\ntwo\n"
    dest = tmp_path / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(markdown, encoding="utf-8")
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    with pytest.raises(SourceReadError) as exc_info:
        read_repo_heading_anchor(
            repo_root=tmp_path,
            relative_path=relative_path,
            heading_text="Same Heading",
            expected_content_sha256=digest,
            max_chars=1000,
        )
    assert exc_info.value.code == "ambiguous_heading"


def test_source_reader_truncated_line_range_covers_returned_bytes_only(
    tmp_path: Path,
) -> None:
    relative_path = "docs/long-section.md"
    lines = ["# Long Section"] + [f"line-{index} {'x' * 40}" for index in range(1, 21)]
    markdown = "\n".join(lines) + "\n"
    dest = tmp_path / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(markdown, encoding="utf-8")
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    outcome = read_repo_heading_anchor(
        repo_root=tmp_path,
        relative_path=relative_path,
        heading_text="Long Section",
        expected_content_sha256=digest,
        max_chars=80,
    )
    assert outcome.truncated is True
    assert outcome.line_start == 1
    assert outcome.line_end is not None
    # Full section would extend well beyond the truncated excerpt.
    assert outcome.line_end < 21
    assert outcome.content is not None
    assert outcome.content.count("\n") + 1 == (
        outcome.line_end - outcome.line_start + 1
    )


def test_source_reader_rejects_malformed_json_pointer_escape() -> None:
    with pytest.raises(SourceReadError) as exc_info:
        read_graph_data_json_pointer_anchor(
            contribution_payload={"values": ["ok"]},
            json_pointer="/values/~",
            max_chars=1000,
        )
    assert exc_info.value.code == "invalid_json_pointer"


def test_source_reader_json_pointer_slash_is_empty_string_key() -> None:
    payload = {"": "root-member", "nested": {"child": "value"}}
    outcome = read_graph_data_json_pointer_anchor(
        contribution_payload=payload,
        json_pointer="/",
        max_chars=1000,
    )
    assert json.loads(outcome.content) == "root-member"
