"""Kernel World Graph retrieval + source-anchor admission tests (PR010A)."""

from __future__ import annotations

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
from graph_memory.projection.world_projection import WorldGraphProjectionFocus
from graph_memory.retrieval.models import (
    RETRIEVAL_RESULT_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphEvidenceTarget,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalBounds,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
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
        "world_id": world_id,
        "campaign_id": campaign_id,
        "focus": WorldGraphProjectionFocus(),
        "admissibility": admissibility,
        "revision_pin": revision_pin,
    }


def _search_request(query_text: str, **overrides) -> WorldGraphSearchRequest:
    return WorldGraphSearchRequest(query_text=query_text, **{**_context(), **overrides})


def _object_request(node_id: str, **overrides) -> WorldGraphObjectRequest:
    return WorldGraphObjectRequest(node_id=node_id, **{**_context(), **overrides})


def _neighborhood_request(
    seed_node_ids: list[str], *, max_depth: int = 1, **overrides
) -> WorldGraphNeighborhoodRequest:
    return WorldGraphNeighborhoodRequest(
        seed_node_ids=seed_node_ids,
        max_depth=max_depth,
        **{**_context(), **overrides},
    )


def _evidence_request(target: WorldGraphEvidenceTarget, **overrides) -> WorldGraphEvidenceRequest:
    return WorldGraphEvidenceRequest(target=target, **{**_context(), **overrides})


def _anchor_read_request(anchor_id: str, **overrides) -> WorldGraphSourceAnchorReadRequest:
    return WorldGraphSourceAnchorReadRequest(anchor_id=anchor_id, **{**_context(), **overrides})


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

    monkeypatch.setattr(
        "graph_memory.kernel.world_retrieval.read_graph_data_json_pointer_anchor",
        _boom,
        raising=True,
    )
    monkeypatch.setattr(
        "graph_memory.kernel.world_retrieval.read_repo_heading_anchor", _boom, raising=True
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
            bounds=WorldGraphRetrievalBounds(max_nodes=1),
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
    result = kernel.get_object_neighborhood(
        tmp_path, _neighborhood_request([TRIPOD_ID], max_depth=1)
    )
    edge_id = (
        "edge:threat:tripod-null-calf:appeared_in:"
        "event:longmont-c2:session-23:mireward-gate-battle"
    )
    relationship = next(r for r in result.relationships if r.edge_id == edge_id)
    assert relationship.source_node_id == TRIPOD_ID
    assert relationship.target_node_id == EVENT_ID


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
            {**_context(), "seedNodeIds": [TRIPOD_ID], "maxDepth": 3}
        )


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


def test_read_source_anchor_repo_heading_with_digest(
    tmp_path: Path, loaded_bundle, tmp_path_factory: pytest.TempPathFactory
) -> None:
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

    read_result = kernel.read_source_anchor(
        tmp_path,
        _anchor_read_request(anchor.anchor_id),
        repo_root=fake_repo_root,
    )
    # The Mirathorn document has no heading exactly matching the admitted
    # heading locator text; it falls back to the frontmatter-title match and
    # returns the whole (long) body, which exceeds even the hard-max bound.
    assert read_result.outcome == "truncated"
    assert read_result.truncated is True
    assert read_result.media_type == "text/markdown"
    assert "Mirathorn" in (read_result.content or "")
    assert read_result.content_sha256 == (
        "70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342"
    )


def test_read_source_anchor_fails_closed_after_source_mutation(
    tmp_path: Path, loaded_bundle, tmp_path_factory: pytest.TempPathFactory
) -> None:
    _initialize(tmp_path, loaded_bundle)
    anchor = _first_anchor_for_node(
        tmp_path, MIRATHORN_ID, evidence_ref_id=MIRATHORN_EVIDENCE_REF_ID
    )

    fake_repo_root = tmp_path_factory.mktemp("fake-repo-root-mutate")
    dest = fake_repo_root / MIRATHORN_RELATIVE_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((REPO_ROOT / MIRATHORN_RELATIVE_PATH).read_bytes())

    first_read = kernel.read_source_anchor(
        tmp_path,
        _anchor_read_request(anchor.anchor_id),
        repo_root=fake_repo_root,
    )
    assert first_read.outcome in ("enough", "truncated")

    dest.write_text("---\ntitle: \"The City of Mirathorn\"\n---\nTampered content.\n")

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
            focus=WorldGraphProjectionFocus(kind="session", session_id=FOCUS_SESSION_ID),
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
            {**_context(), "anchorId": "source-anchor:v1:" + "0" * 64, "path": "/etc/passwd"}
        )


def test_source_anchor_read_max_chars_hard_max_enforced() -> None:
    with pytest.raises(ValidationError):
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                **_context(),
                "anchorId": "source-anchor:v1:" + "0" * 64,
                "maxChars": 999_999,
            }
        )
