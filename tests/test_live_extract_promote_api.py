"""HTTP-boundary tests for extract → World Supergraph promote."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import graph_memory.extract_promote_ops as ops
import graph_memory.kernel as kernel
from apps.live_control_server.main import create_app
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
)
from graph_memory.contribution_bundles import load_contribution_bundle
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

STATUS_URL = "/api/live/extract-promote/status"
PREPARE_URL = "/api/live/extract-promote/prepare"
CONFIRM_URL = "/api/live/extract-promote/confirm"


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


def _candidate_graph_payload() -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:http-promote-vial",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "status": "preview",
        "nodes": [
            {
                "node_id": "obj_session22_vial",
                "label": "vial",
                "node_type": "item",
                "description": "Puddle sample vial",
                "importance": "medium",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("006")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
            {
                "node_id": "mystery_puddles",
                "label": "Magic puddles",
                "node_type": "mystery",
                "description": "Delayed reflections",
                "importance": "medium",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
        ],
        "edges": [
            {
                "edge_id": "e33",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "mystery_puddles",
                "relationship_type": "linked_to",
                "label": "linked to",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
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


@pytest.fixture
def world_client(tmp_path: Path, loaded_bundle, monkeypatch: pytest.MonkeyPatch):
    _initialize(tmp_path, loaded_bundle)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path))
    source = tmp_path / "source_fixture.md"
    source.write_text("session 22 promote fixture\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    graph_path = tmp_path / "candidate_graph.json"
    graph_path.write_text(
        json.dumps(_candidate_graph_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    return client, tmp_path, graph_path, source, f"sha256:{digest}"


def test_status_reports_initialized_head(world_client) -> None:
    client, _tmp, _graph, _source, _digest = world_client
    response = client.get(STATUS_URL)
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "dmb_extract_promote_status_v1"
    assert payload["worldId"] == WORLD_ID
    assert payload["initialized"] is True
    assert payload["headRevisionId"].startswith("rev:")
    assert "head_revision_id" not in json.dumps(payload)


def test_prepare_confirm_success(world_client) -> None:
    client, tmp_path, graph_path, source, digest = world_client
    prepare = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(source),
            "sourceRevisionId": digest,
            "preparedBy": "gm@http-prepare",
            "nodeIds": ["obj_session22_vial", "mystery_puddles"],
        },
    )
    assert prepare.status_code == 200, prepare.text
    prepared = prepare.json()
    assert prepared["schema"] == "dmb_extract_promote_prepare_v1"
    assert prepared["acceptedProposalsCount"] >= 1
    assert prepared["proposalDigest"]
    package = prepared["reviewPackage"]

    head_before = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0].head_revision_id
    confirm = client.post(
        CONFIRM_URL,
        json={
            "schema": "dmb_extract_promote_confirm_request_v1",
            "reviewPackage": package,
            "confirmingPrincipal": "gm@http-confirm",
        },
    )
    assert confirm.status_code == 200, confirm.text
    confirmed = confirm.json()
    assert confirmed["ok"] is True
    assert confirmed["dryRun"] is False
    assert confirmed["result"]["ok"] is True
    assert confirmed["result"]["merge"]["published"] is True
    head_after = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0].head_revision_id
    assert head_after != head_before


def test_confirm_rejects_tampered_package(world_client) -> None:
    client, _tmp, graph_path, source, digest = world_client
    prepare = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(source),
            "sourceRevisionId": digest,
            "preparedBy": "gm@http-prepare",
            "nodeIds": ["obj_session22_vial", "mystery_puddles"],
            "nodesOnly": True,
        },
    )
    assert prepare.status_code == 200, prepare.text
    package = prepare.json()["reviewPackage"]
    package["effect"]["contribution_meta"]["authored_by"] = "attacker"

    confirm = client.post(
        CONFIRM_URL,
        json={
            "schema": "dmb_extract_promote_confirm_request_v1",
            "reviewPackage": package,
            "confirmingPrincipal": "gm@http-confirm",
        },
    )
    assert confirm.status_code == 409
    payload = confirm.json()
    assert payload["schema"] == "dmb_extract_promote_error_v1"
    assert payload["code"] == "proposal_verification_failed"


def test_confirm_refuses_live_world_without_allow(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, tmp_path, graph_path, source, digest = world_client
    prepare = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(source),
            "sourceRevisionId": digest,
            "preparedBy": "gm@http-prepare",
            "nodeIds": ["obj_session22_vial"],
            "nodesOnly": True,
        },
    )
    assert prepare.status_code == 200, prepare.text
    package = prepare.json()["reviewPackage"]

    # Make the configured world root appear as the live root.
    monkeypatch.setattr(
        "apps.live_control_server.services.extract_promote.default_live_root",
        lambda *, repo_root: tmp_path.resolve(),
    )

    confirm = client.post(
        CONFIRM_URL,
        json={
            "schema": "dmb_extract_promote_confirm_request_v1",
            "reviewPackage": package,
            "confirmingPrincipal": "gm@http-confirm",
            "allowLiveWorld": False,
        },
    )
    assert confirm.status_code == 403
    assert confirm.json()["code"] == "live_world_refused"


def test_confirm_published_false_returns_failure_proof(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _tmp, graph_path, source, digest = world_client
    prepare = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(source),
            "sourceRevisionId": digest,
            "preparedBy": "gm@http-prepare",
            "nodeIds": ["obj_session22_vial"],
            "nodesOnly": True,
        },
    )
    assert prepare.status_code == 200, prepare.text
    package = prepare.json()["reviewPackage"]

    class FakeResult:
        published = False
        revision_id = None
        accepted_assertion_ids: list[str] = []
        diagnostics = ["merge_failed:simulated"]

        def model_dump(self, mode: str = "json"):
            return {
                "published": False,
                "revision_id": None,
                "accepted_assertion_ids": [],
                "diagnostics": self.diagnostics,
            }

    monkeypatch.setattr(
        ops.kernel,
        "merge_contribution_to_revision",
        lambda *a, **k: FakeResult(),
    )

    confirm = client.post(
        CONFIRM_URL,
        json={
            "schema": "dmb_extract_promote_confirm_request_v1",
            "reviewPackage": package,
            "confirmingPrincipal": "gm@http-confirm",
        },
    )
    assert confirm.status_code == 409
    payload = confirm.json()
    assert payload["code"] == "merge_did_not_publish"
    assert payload["failureResult"]["ok"] is False
    assert payload["failureResult"]["failure_reason"] == "merge_did_not_publish"


def test_prepare_rejects_query_selectors(world_client) -> None:
    client, _tmp, graph_path, source, digest = world_client
    response = client.post(
        f"{PREPARE_URL}?worldId=foreign",
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(source),
            "sourceRevisionId": digest,
            "preparedBy": "gm@http-prepare",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
