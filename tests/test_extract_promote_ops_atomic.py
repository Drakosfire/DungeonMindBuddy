"""End-to-end atomicity + slice-qualified selection tests for confirm_extract_promote.

Covers PR011A3 review P0 (atomic multi-contribution publish: one merge call,
head never advances partially) and P1 (slice-qualified selection disambiguates
assertion ids that collide across independently-sourced contribution slices),
exercised through the public prepare/confirm surface rather than the lower
identity-gate/proposal unit layers.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.extract_identity_gate import gate_candidate_graph_against_head
from graph_memory.extract_promote_ops import confirm_extract_promote
from graph_memory.extract_promote_proposal import (
    SLICE_SELECTOR_DELIMITER,
    build_contribution_effect_slice,
    contribution_meta_from_contribution,
    contribution_slice_id_for,
    seal_multi_contribution_promote_proposal,
)
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
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
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id=BUNDLE_ID,
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )


def _initialize(root: Path, bundle):
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _semantic() -> dict:
    return {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _evidence(suffix: str, *, artifact_id: str) -> dict:
    return {
        "source_ref_id": f"ref:{suffix}",
        "source_artifact_id": artifact_id,
        "source_anchor_id": f"anchor:{suffix}",
        "label": "span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-22:recap:paragraph:{suffix}",
        "anchor_quotes": ["quote"],
    }


def _diagnostics() -> dict:
    return {
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
    }


def _node(
    node_id: str, label: str, node_type: str, suffix: str, description: str, *, artifact_id: str
) -> dict:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": description,
        "importance": "medium",
        "semantic_state": _semantic(),
        "evidence_refs": [_evidence(suffix, artifact_id=artifact_id)],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


SLICE_A_ARTIFACT_ID = "artifact:recap:longmont-c2:session-22-atomic-a"
SLICE_B_ARTIFACT_ID = "artifact:recap:longmont-c2:session-22-atomic-b"


def _slice_a_graph() -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:ops-atomic-slice-a",
        "session_id": "session-22",
        "campaign_id": CAMPAIGN_ID,
        "source_artifact_ids": [SLICE_A_ARTIFACT_ID],
        "status": "preview",
        "nodes": [
            _node(
                "node:atomic-alpha",
                "Atomic Alpha",
                "npc",
                "a01",
                "Slice A standing-context style npc",
                artifact_id=SLICE_A_ARTIFACT_ID,
            ),
        ],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }


def _slice_b_graph() -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:ops-atomic-slice-b",
        "session_id": "session-22",
        "campaign_id": CAMPAIGN_ID,
        "source_artifact_ids": [SLICE_B_ARTIFACT_ID],
        "status": "preview",
        "nodes": [
            _node(
                "node:atomic-beta",
                "Atomic Beta",
                "npc",
                "b01",
                "Slice B recap-style npc",
                artifact_id=SLICE_B_ARTIFACT_ID,
            ),
        ],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }


def _write_source(tmp_path: Path, name: str) -> tuple[str, str]:
    path = tmp_path / name
    path.write_text(f"body for {name}\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return str(path), f"sha256:{digest}"


def _seal_two_slice_package(tmp_path: Path, world_root: Path, parent_revision_id: str) -> dict:
    uri_a, revision_a = _write_source(tmp_path, "slice-a-source.md")
    uri_b, revision_b = _write_source(tmp_path, "slice-b-source.md")

    gate_a = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_slice_a_graph()),
        root=world_root,
        world_id=WORLD_ID,
        source_artifact_id=SLICE_A_ARTIFACT_ID,
        source_revision_id=revision_a,
        source_uri=uri_a,
        source_kind="standing_context",
        source_domain="party_registry",
        campaign_scope=CAMPAIGN_ID,
        extraction_profile="party_registry_standing",
    )
    gate_b = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_slice_b_graph()),
        root=world_root,
        world_id=WORLD_ID,
        source_artifact_id=SLICE_B_ARTIFACT_ID,
        source_revision_id=revision_b,
        source_uri=uri_b,
        source_kind="source_extraction",
        source_domain="recap",
        campaign_scope=CAMPAIGN_ID,
    )
    assert gate_a.parent_revision_id == parent_revision_id
    assert gate_b.parent_revision_id == parent_revision_id

    slice_a = build_contribution_effect_slice(
        source_revision_id=gate_a.source_revision_id,
        source_artifact_id=gate_a.source_artifact_id,
        verified_source_uri=str(gate_a.verified_source_uri),
        candidate_preview_id=gate_a.candidate_preview_id,
        candidate_schema=gate_a.candidate_schema,
        candidate_version=gate_a.candidate_version,
        contribution_meta=contribution_meta_from_contribution(gate_a.contribution),
        accepted_proposals=gate_a.accepted_proposals,
        rejected_assertions=gate_a.rejected_assertions,
        unresolved_mentions=gate_a.unresolved_mentions,
        node_id_map=gate_a.node_id_map,
        identity_outcome_snapshot=gate_a.identity_outcome_snapshot,
    )
    slice_b = build_contribution_effect_slice(
        source_revision_id=gate_b.source_revision_id,
        source_artifact_id=gate_b.source_artifact_id,
        verified_source_uri=str(gate_b.verified_source_uri),
        candidate_preview_id=gate_b.candidate_preview_id,
        candidate_schema=gate_b.candidate_schema,
        candidate_version=gate_b.candidate_version,
        contribution_meta=contribution_meta_from_contribution(gate_b.contribution),
        accepted_proposals=gate_b.accepted_proposals,
        rejected_assertions=gate_b.rejected_assertions,
        unresolved_mentions=gate_b.unresolved_mentions,
        node_id_map=gate_b.node_id_map,
        identity_outcome_snapshot=gate_b.identity_outcome_snapshot,
    )
    package = seal_multi_contribution_promote_proposal(
        world_id=WORLD_ID,
        parent_revision_id=parent_revision_id,
        contribution_slices=[slice_a, slice_b],
        prepared_by="gm@prepare",
        diagnostics=["multi_contribution:standing_context+source_extraction"],
        world_root=str(world_root),
    )
    return package, gate_a, gate_b


def _confirm(
    package: dict,
    *,
    world_root: Path,
    tmp_path: Path,
    assertion_ids=None,
    allow_idempotent_noop: bool = False,
):
    return confirm_extract_promote(
        review_package=package,
        world_root=world_root,
        confirming_principal="gm@confirm",
        assertion_ids=assertion_ids,
        allow_live_world=False,
        allow_idempotent_noop=allow_idempotent_noop,
        live_root=tmp_path / "unused_live_root",
        repo_root=tmp_path,
    )


def test_confirm_publishes_two_slices_atomically_in_one_revision(
    tmp_path: Path, loaded_bundle
) -> None:
    world_root = tmp_path / "world"
    init = _initialize(world_root, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    package, gate_a, gate_b = _seal_two_slice_package(tmp_path, world_root, parent)

    result = _confirm(package, world_root=world_root, tmp_path=tmp_path)
    assert result.ok is True, result.payload
    assert result.payload["outcome"] == "published"
    # Exactly one contribution_id / one merge — never per-slice merges.
    assert result.payload["merge"]["contribution_ids"] == [
        result.payload["contribution_id"]
    ]
    assert len(result.payload["merge"]["merges"]) == 1

    store = kernel.open_current_world_graph(world_root, WORLD_ID)[2]
    assert gate_a.node_id_map["node:atomic-alpha"] in store.nodes
    assert gate_b.node_id_map["node:atomic-beta"] in store.nodes

    head = kernel.open_current_world_graph(world_root, WORLD_ID)[0]
    assert head.head_revision_id == result.payload["committed_revision_id"]
    assert head.head_revision_id != parent


def test_confirm_merge_refused_leaves_head_unchanged_and_retry_succeeds(
    tmp_path: Path, loaded_bundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P0: a refused merge must not advance the head, and a clean retry with
    the same sealed package (no monkeypatch) must succeed afterwards — the
    failed attempt leaves no partial state behind.
    """
    world_root = tmp_path / "world"
    init = _initialize(world_root, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    package, gate_a, gate_b = _seal_two_slice_package(tmp_path, world_root, parent)

    import graph_memory.extract_promote_ops as ops

    class RefusedResult:
        published = False
        revision_id = None
        accepted_assertion_ids: list[str] = []
        diagnostics = ["merge_failed:simulated_refusal"]

        def model_dump(self, mode: str = "json"):
            return {
                "published": False,
                "revision_id": None,
                "accepted_assertion_ids": [],
                "diagnostics": self.diagnostics,
            }

    monkeypatch.setattr(
        ops.kernel, "merge_contribution_to_revision", lambda *a, **k: RefusedResult()
    )

    result = _confirm(package, world_root=world_root, tmp_path=tmp_path)
    assert result.ok is False
    assert result.failure_reason == "merge_refused"
    assert result.payload["outcome"] == "merge_refused"
    # Only one merge attempt for the whole multi-slice selection — the single
    # atomic contribution was refused as a unit, not per-slice.
    head_after_refusal = kernel.open_current_world_graph(world_root, WORLD_ID)[0]
    assert head_after_refusal.head_revision_id == parent

    monkeypatch.undo()
    retry = _confirm(package, world_root=world_root, tmp_path=tmp_path)
    assert retry.ok is True, retry.payload
    assert retry.payload["outcome"] == "published"
    store = kernel.open_current_world_graph(world_root, WORLD_ID)[2]
    assert gate_a.node_id_map["node:atomic-alpha"] in store.nodes
    assert gate_b.node_id_map["node:atomic-beta"] in store.nodes


def test_confirm_slice_qualified_selection_publishes_only_selected_slice(
    tmp_path: Path, loaded_bundle
) -> None:
    """P1: a slice-qualified selector must publish only that slice's
    assertions, leaving the other slice's node entirely unpublished.
    """
    world_root = tmp_path / "world"
    init = _initialize(world_root, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    package, gate_a, gate_b = _seal_two_slice_package(tmp_path, world_root, parent)

    slices = package["effect"]["contributions"]
    slice_a_id = contribution_slice_id_for(0, slices[0])
    alpha_assertion_id = next(
        a["assertion_id"]
        for a in slices[0]["accepted_proposals"]
        if a["assertion_kind"] == "node"
    )
    qualified_selector = f"{slice_a_id}{SLICE_SELECTOR_DELIMITER}{alpha_assertion_id}"

    result = _confirm(
        package,
        world_root=world_root,
        tmp_path=tmp_path,
        assertion_ids=[qualified_selector],
    )
    assert result.ok is True, result.payload

    store = kernel.open_current_world_graph(world_root, WORLD_ID)[2]
    assert gate_a.node_id_map["node:atomic-alpha"] in store.nodes
    assert gate_b.node_id_map["node:atomic-beta"] not in store.nodes


def test_service_projects_multi_slice_assertion_fields_via_shared_helper(
    tmp_path: Path, loaded_bundle
) -> None:
    """The HTTP service layer's pre/post-confirm projection helpers must
    reconstruct the SAME merged contribution as ``confirm_extract_promote``
    (both delegate to ``resolve_merged_contribution_from_package``), so a
    multi-slice selection is projected consistently rather than only
    accounting for one slice (a latent bug the old single-slice
    ``build_accepted_contribution_from_proposals`` call site would have hit).
    """
    import apps.live_control_server.services.extract_promote as promote_service

    world_root = tmp_path / "world"
    init = _initialize(world_root, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    package, gate_a, gate_b = _seal_two_slice_package(tmp_path, world_root, parent)
    all_assertion_ids = tuple(
        a["assertion_id"]
        for slice_body in package["effect"]["contributions"]
        for a in slice_body["accepted_proposals"]
    )

    accepted_ids, affected_object_ids, warnings = promote_service._project_assertion_fields(
        package, all_assertion_ids, world_root=world_root
    )
    assert warnings == []
    assert gate_a.node_id_map["node:atomic-alpha"] in affected_object_ids
    assert gate_b.node_id_map["node:atomic-beta"] in affected_object_ids
    assert len(accepted_ids) == 2

    result = _confirm(package, world_root=world_root, tmp_path=tmp_path)
    assert result.ok is True, result.payload
