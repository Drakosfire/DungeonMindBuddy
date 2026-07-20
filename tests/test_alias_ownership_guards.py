"""Kernel alias ownership refuse-hijack guards."""

from __future__ import annotations

from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
)
from graph_memory.candidate_graph_to_contribution import (
    map_connect_existing_support_assertions,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.contribution_merge import _apply_alias_assertion
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
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


def _semantic() -> dict:
    return {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _evidence(suffix: str) -> dict:
    return {
        "source_ref_id": f"ref:{suffix}",
        "source_artifact_id": "artifact:recap:longmont-c2:session-22",
        "source_anchor_id": f"anchor:{suffix}",
        "label": "span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-22:recap:paragraph:{suffix}",
        "anchor_quotes": ["quote"],
    }


def _node(node_id: str, label: str, node_type: str, suffix: str, *, aliases: list[str] | None = None) -> dict:
    payload = {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": "test",
        "importance": "medium",
        "semantic_state": _semantic(),
        "evidence_refs": [_evidence(suffix)],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }
    if aliases is not None:
        payload["aliases"] = aliases
    return payload


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


@pytest.fixture
def initialized_store(tmp_path: Path):
    bundle = load_contribution_bundle(BUNDLE_PATH)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
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
    initialize_world_from_contributions(
        tmp_path,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )
    _head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    return store


def test_map_connect_existing_skips_foreign_owned_alias(initialized_store) -> None:
    preview = candidate_graph_preview_from_dict(
        {
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
            "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
            "preview_id": "preview:alias-skip",
            "session_id": "session-22",
            "campaign_id": "longmont-c2",
            "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
            "status": "preview",
            "nodes": [
                _node(
                    "node:caelynn",
                    "Caelynn",
                    "character",
                    "001",
                    aliases=["Baergrom"],
                )
            ],
            "edges": [],
            "beats": [],
            "proposed_writes": [],
            "ignored_items": [],
            "deferred_items": [],
            "diagnostics": _diagnostics(),
        }
    )
    node = preview.nodes[0]
    assertions, skip_diag = map_connect_existing_support_assertions(
        node,
        durable_node_id="pc:caelynn",
        source_revision_id="sha256:testdigest-alias-skip",
        verified_source_artifact_id="artifact:recap:longmont-c2:session-22",
        campaign_scope="longmont-c2",
        alias_owners=dict(initialized_store.aliases),
    )
    alias_assertions = [a for a in assertions if a.assertion_kind == "alias"]
    assert alias_assertions == []
    assert any(d.startswith("alias_ownership_skip:Baergrom->pc:baergrom") for d in skip_diag)
    assert any(a.assertion_kind == "attribute" for a in assertions)


def test_apply_alias_assertion_refuses_hijack(initialized_store) -> None:
    assertion = kernel.build_assertion(
        assertion_kind="alias",
        acceptance_state="accepted",
        subject_node_id="pc:caelynn",
        label="Baergrom",
        value={"alias": "Baergrom"},
        campaign_scope="longmont-c2",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:test",
        source_revision_id="sha256:test",
        accepted_assertions=[assertion],
    )
    with pytest.raises(ValueError, match="would hijack alias 'Baergrom' owned by 'pc:baergrom'"):
        _apply_alias_assertion(initialized_store, assertion, contribution)


def test_apply_alias_assertion_same_owner_reapply_ok(initialized_store) -> None:
    assertion = kernel.build_assertion(
        assertion_kind="alias",
        acceptance_state="accepted",
        subject_node_id="pc:caelynn",
        label="Caellynn",
        value={"alias": "Caellynn"},
        campaign_scope="longmont-c2",
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id="artifact:test",
        source_revision_id="sha256:test",
        accepted_assertions=[assertion],
    )
    updated, graph_object_id = _apply_alias_assertion(
        initialized_store, assertion, contribution
    )
    assert graph_object_id == "pc:caelynn"
    assert updated.aliases["caellynn".casefold()] == "pc:caelynn"
    updated2, graph_object_id2 = _apply_alias_assertion(updated, assertion, contribution)
    assert graph_object_id2 == "pc:caelynn"
    assert updated2.aliases["caellynn".casefold()] == "pc:caelynn"
