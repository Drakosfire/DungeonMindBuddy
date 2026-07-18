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
    world_root = tmp_path / "world"
    source_root = tmp_path / "promote_source_artifacts"
    world_root.mkdir()
    source_root.mkdir()
    _initialize(world_root, loaded_bundle)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
    monkeypatch.setenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", str(source_root))
    # Sandbox mutation root is distinct from the designated live root.
    monkeypatch.setenv(
        "DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT",
        str(tmp_path / "_designated_live_not_used"),
    )
    source = source_root / "source_fixture.md"
    source.write_text("session 22 promote fixture\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # Candidate IR may live under the world root; source evidence must not.
    graph_path = world_root / "candidate_graph.json"
    graph_path.write_text(
        json.dumps(_candidate_graph_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    return client, world_root, graph_path, source, f"sha256:{digest}"


def test_status_reports_initialized_head(world_client) -> None:
    client, _tmp, _graph, _source, _digest = world_client
    response = client.get(STATUS_URL)
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "dmb_extract_promote_status_v1"
    assert payload["worldId"] == WORLD_ID
    assert payload["initialized"] is True
    assert payload["worldState"] == "initialized"
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
    sealed_uri = package["effect"]["verified_source_uri"]
    assert sealed_uri == str(source.resolve())

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
    assert confirmed["result"]["published"] is True
    assert confirmed["result"]["outcome"] == "published"
    assert confirmed["result"]["merge"]["published"] is True
    assert confirmed["result"]["post_publication_verification"] == "passed"
    head_after = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0].head_revision_id
    assert head_after != head_before
    assert confirmed["result"]["committed_revision_id"] == head_after
    assert confirmed["result"]["projection_revision_id"] == head_after
    assert confirmed["result"]["rebuild_equivalent_to_committed_revision"] is True
    assert "rebuild_equivalent_to_head" not in confirmed["result"]
    assert any(
        str(item).startswith("rebuild_replay_pinned_to_revision:")
        for item in confirmed["result"].get("rebuild_diagnostics") or []
    )
    assert confirmed["result"].get("head_advanced_before_verification") is False


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
    # Designate the configured mutation root as live.
    monkeypatch.setenv("DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT", str(tmp_path.resolve()))

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


def test_confirm_empty_assertion_ids_does_not_advance_head(world_client) -> None:
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
    package = prepare.json()["reviewPackage"]
    head_before = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0].head_revision_id

    confirm = client.post(
        CONFIRM_URL,
        json={
            "schema": "dmb_extract_promote_confirm_request_v1",
            "reviewPackage": package,
            "confirmingPrincipal": "gm@http-confirm",
            "assertionIds": [],
        },
    )
    assert confirm.status_code == 422
    payload = confirm.json()
    assert payload["code"] == "empty_assertion_selection"
    head_after = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_prepare_rejects_arbitrary_filesystem_source_and_hides_digest(
    world_client, tmp_path: Path
) -> None:
    client, _world, graph_path, _source, _digest = world_client
    outside = Path("/etc/passwd")
    if not outside.is_file():
        pytest.skip("/etc/passwd not available")

    response = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(outside),
            "sourceRevisionId": "sha256:deadbeef",
            "preparedBy": "gm@http-prepare",
        },
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "invalid_source_uri"
    dumped = json.dumps(payload)
    assert "computed=" not in dumped
    assert "sha256:" not in dumped or "deadbeef" in dumped


def test_prepare_source_mismatch_does_not_disclose_computed_digest(
    world_client,
) -> None:
    client, _tmp, graph_path, source, _digest = world_client
    response = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(source),
            "sourceRevisionId": "sha256:" + ("0" * 64),
            "preparedBy": "gm@http-prepare",
        },
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "source_revision_mismatch"
    dumped = json.dumps(payload)
    assert "computed=" not in dumped
    # Must not leak the real file digest.
    real = hashlib.sha256(source.read_bytes()).hexdigest()
    assert real not in dumped


def test_confirm_post_publication_verification_failure_reports_committed_revision(
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
    head_before = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0].head_revision_id

    real_merge = ops.kernel.merge_contribution_to_revision

    def _merge_then_break(*args, **kwargs):
        result = real_merge(*args, **kwargs)
        monkeypatch.setattr(
            ops.kernel,
            "rebuild_from_contributions",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("audit boom")),
        )
        return result

    monkeypatch.setattr(ops.kernel, "merge_contribution_to_revision", _merge_then_break)

    confirm = client.post(
        CONFIRM_URL,
        json={
            "schema": "dmb_extract_promote_confirm_request_v1",
            "reviewPackage": package,
            "confirmingPrincipal": "gm@http-confirm",
        },
    )
    assert confirm.status_code == 200, confirm.text
    payload = confirm.json()
    assert payload["ok"] is False
    assert payload["failureReason"] == "post_publication_verification_failed"
    assert payload["result"]["published"] is True
    assert payload["result"]["committed_revision_id"]
    assert payload["result"]["post_publication_verification"] == "failed"
    assert payload["result"]["retry_guidance"] == (
        "reload_status_inspect_head_do_not_retry_confirm"
    )
    head_after = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0].head_revision_id
    assert head_after != head_before
    assert head_after == payload["result"]["committed_revision_id"]


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


def test_prepare_rejects_source_inside_world_graph_store(world_client) -> None:
    client, world_root, graph_path, _source, digest = world_client
    planted = world_root / "graph_memory" / "planted_source.md"
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text("must not be evidentiary authority\n", encoding="utf-8")

    response = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v1",
            "candidateGraphPath": str(graph_path),
            "sourceUri": str(planted),
            "sourceRevisionId": digest,
            "preparedBy": "gm@http-prepare",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_source_uri"
    assert "world graph store" in response.json()["message"]


def test_confirm_already_applied_keeps_published_false(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, world_root, graph_path, source, digest = world_client
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
    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id

    class FakeResult:
        published = False
        revision_id = head_before
        accepted_assertion_ids: list[str] = ["assertion:x"]
        diagnostics = ["idempotent_noop:contribution_already_applied"]

        def model_dump(self, mode: str = "json"):
            return {
                "published": False,
                "revision_id": self.revision_id,
                "accepted_assertion_ids": self.accepted_assertion_ids,
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
            "allowIdempotentNoop": True,
        },
    )
    assert confirm.status_code == 200, confirm.text
    payload = confirm.json()
    assert payload["ok"] is True
    assert payload["result"]["ok"] is True
    assert payload["result"]["published"] is False
    assert payload["result"]["outcome"] == "already_applied"
    assert payload["result"]["committed_revision_id"] == head_before
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_confirm_audit_pins_projection_to_committed_revision(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Projection and rebuild must target the committed revision, not mutable head."""
    client, world_root, graph_path, source, digest = world_client
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

    seen: dict[str, object] = {}
    real_rebuild = ops.kernel.rebuild_from_contributions
    real_project = ops.kernel.project_world_graph

    def _rebuild(*args, **kwargs):
        seen["compare_revision_id"] = kwargs.get("compare_revision_id")
        return real_rebuild(*args, **kwargs)

    def _project(root, request):
        seen["revision_pin"] = request.revision_pin
        return real_project(root, request)

    monkeypatch.setattr(ops.kernel, "rebuild_from_contributions", _rebuild)
    monkeypatch.setattr(ops.kernel, "project_world_graph", _project)

    confirm = client.post(
        CONFIRM_URL,
        json={
            "schema": "dmb_extract_promote_confirm_request_v1",
            "reviewPackage": package,
            "confirmingPrincipal": "gm@http-confirm",
        },
    )
    assert confirm.status_code == 200, confirm.text
    committed = confirm.json()["result"]["committed_revision_id"]
    assert committed
    assert seen["compare_revision_id"] == committed
    assert seen["revision_pin"] == committed
    assert confirm.json()["result"]["projection_revision_id"] == committed
    assert confirm.json()["result"]["rebuild_equivalent_to_committed_revision"] is True
    assert "rebuild_equivalent_to_head" not in confirm.json()["result"]
