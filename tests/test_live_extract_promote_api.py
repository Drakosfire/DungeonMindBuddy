"""HTTP-boundary tests for extract → World Supergraph promote (PR011A1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.config as live_config
import apps.live_control_server.services.extract_promote as promote_svc
import apps.live_control_server.services.promotable_ingest_run as promotable_mod
import graph_memory.extract_promote_ops as ops
import graph_memory.kernel as kernel
from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
)
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
)
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.ingestion.graph_ingest_run import GRAPH_INGEST_RUN_MANIFEST_SCHEMA
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
SESSION_ID = "session-22"
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
WORLD_BUILDING_PREPARE_URL = "/api/live/extract-promote/worldbuilding/prepare"
WORLD_BUILDING_CONFIRM_URL = "/api/live/extract-promote/worldbuilding/confirm"
CONFIRM_URL = "/api/live/extract-promote/confirm"
RUN_ID = "graph-ingest:longmont-c2:session-22:fixture-promote"


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


def _candidate_graph_payload(
    *,
    campaign_id: str = CAMPAIGN_ID,
    session_id: str = SESSION_ID,
) -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:http-promote-vial",
        "session_id": session_id,
        "campaign_id": campaign_id,
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


def _write_promotable_run(
    repo: Path,
    *,
    run_id: str = RUN_ID,
    campaign_id: str = CAMPAIGN_ID,
    session_id: str = SESSION_ID,
    status: str = "preview_union_store_ready",
    candidate_graph_valid: bool = True,
    preview_union_store_valid: bool = True,
    digest_override: str | None = None,
    omit_candidate: bool = False,
    omit_preview: bool = False,
    omit_source_artifact_id: bool = False,
    extraction_profile: str | None = "category_v1",
    runs_rel: str = "out/graph_memory/runs",
    candidate_campaign_id: str | None = None,
    candidate_session_id: str | None = None,
    registry_context: dict | None = None,
    registry_filename: str = "registry_context_graph.json",
) -> tuple[str, str, Path]:
    run_dir = (
        repo / Path(runs_rel) / campaign_id / session_id / "fixture-promote"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    source = run_dir / "normalized_recap_source.md"
    source.write_text("session 22 promote fixture\n", encoding="utf-8")
    digest_hex = hashlib.sha256(source.read_bytes()).hexdigest()
    digest = digest_override or f"sha256:{digest_hex}"
    candidate = run_dir / "candidate_graph.json"
    if not omit_candidate:
        candidate.write_text(
            json.dumps(
                _candidate_graph_payload(
                    campaign_id=candidate_campaign_id or campaign_id,
                    session_id=candidate_session_id or session_id,
                ),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    preview = run_dir / "preview_union_supergraph.json"
    if not omit_preview:
        preview.write_text("{}\n", encoding="utf-8")

    def rel(path: Path) -> str:
        return path.relative_to(repo).as_posix()

    artifacts: dict = {
        "normalized_recap": {
            "kind": "normalized_recap",
            "uri": rel(source),
            "sha256": digest,
            "exists": True,
            "preview_only": True,
        },
    }
    if not omit_preview:
        artifacts["preview_union_store"] = {
            "kind": "preview_union_store",
            "uri": rel(preview),
            "exists": True,
            "preview_only": True,
        }
    if not omit_candidate:
        artifacts["candidate_graph"] = {
            "kind": "candidate_graph",
            "uri": rel(candidate),
            "exists": True,
            "preview_only": True,
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        }
    if registry_context is not None:
        registry_path = run_dir / registry_filename
        registry_path.write_text(
            json.dumps(registry_context, indent=2) + "\n", encoding="utf-8"
        )
        artifacts["registry_context_graph"] = {
            "kind": "registry_context_graph",
            "uri": rel(registry_path),
            "exists": True,
            "preview_only": True,
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        }

    source_block: dict = {
        "source_domain": "recap",
        "normalized_recap_path": rel(source),
        "normalized_recap_sha256": digest,
        "source_label": "fixture promote recap",
    }
    if not omit_source_artifact_id:
        source_block["source_artifact_id"] = "artifact:recap:longmont-c2:session-22"

    diagnostics: dict = {
        "preview_only": True,
        "candidate_extraction": False,
        "preview_import": True,
        "canon_promotion": False,
        "approved_memory_write": False,
        "corpus_mutation": False,
        "production_retrieval": False,
        "agent_interaction_connected": False,
        "runtime_projection_connected": False,
    }
    if extraction_profile:
        diagnostics["extraction_profile"] = extraction_profile

    manifest: dict = {
        "schema": GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
        "version": "0.1",
        "run_id": run_id,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "status": status,
        "created_at": "2026-07-17T00:00:00Z",
        "updated_at": "2026-07-17T00:00:00Z",
        "source": source_block,
        "artifacts": artifacts,
        "health": {
            "candidate_graph_valid": candidate_graph_valid,
            "preview_union_store_valid": preview_union_store_valid,
            "node_count": 2,
            "edge_count": 1,
            "evidence_ref_count": 2,
            "resolvable_evidence_ref_count": 2,
            "openable_evidence_ref_count": 2,
            "highlightable_evidence_ref_count": 2,
        },
        "diagnostics": diagnostics,
        "steps": [],
        "warnings": [],
        "errors": [],
        "next_actions": ["open_projection_preview"],
    }
    if extraction_profile:
        manifest["extraction_profile"] = extraction_profile
    manifest_path = run_dir / "graph_ingest_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return run_id, digest, source


def _write_bld08_reviewable_run(
    repo: Path,
    *,
    campaign_id: str | None = CAMPAIGN_ID,
    profile_id: str = "worldbuilding_shepherds_flock_v0@0.1",
    session_id: str | None = None,
) -> tuple[str, Path]:
    """Adapt the canonical run fixture to the checked-in BLD-08 profile."""
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    from apps.live_control_server.services.graph_run_registry import (
        extraction_runs_path,
        get_extraction_run,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        _resolve_extraction_component_path,
    )
    from src.live_play.live_store import load_json, write_json
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        DEFAULT_SEMANTIC_STATE,
    )

    resolved_id, source = _write_reviewable_extraction_run(
        repo,
        campaign_id=campaign_id,
    )
    run = get_extraction_run(repo, resolved_id)
    candidate_path = _resolve_extraction_component_path(
        repo,
        run.components["candidate_graph"].uri,
        label="candidate_graph",
    )
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["session_id"] = session_id
    for index, node in enumerate(candidate.get("nodes") or []):
        node["node_type"] = "character" if index == 0 else "location"
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
    for edge in candidate.get("edges") or []:
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()

    registry_path = extraction_runs_path(repo)
    registry = load_json(registry_path)
    for record in registry["records"]:
        if record["run_id"] == resolved_id:
            record["profile_id"] = profile_id
            record["components"]["candidate_graph"]["sha256"] = digest
            break
    write_json(registry_path, registry)
    return resolved_id, source


def _prepare_body(run_id: str, *, node_ids: list[str] | None = None) -> dict:
    body: dict = {
        "schema": "dmb_extract_promote_prepare_request_v2",
        "runId": run_id,
    }
    if node_ids is not None:
        body["nodeIds"] = node_ids
    return body


def _selectable_assertion_ids(prepared: dict) -> list[str]:
    return [
        item["sliceQualifiedId"]
        for item in prepared["reviewItems"]
        if item.get("selectable") and item.get("sliceQualifiedId")
    ]


def _sealed_source_domains(payload: object) -> set[str]:
    """Every source_domain / source_domains value sealed anywhere in a response."""
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "source_domain" and isinstance(value, str) and value.strip():
                found.add(value.strip())
            elif key == "source_domains" and isinstance(value, list):
                found.update(str(item).strip() for item in value if str(item).strip())
            else:
                found |= _sealed_source_domains(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= _sealed_source_domains(item)
    return found


def _confirm_body(package: dict, assertion_ids: list[str]) -> dict:
    return {
        "schema": "dmb_extract_promote_confirm_request_v2",
        "reviewPackage": package,
        "assertionIds": assertion_ids,
    }


@pytest.fixture
def world_client(tmp_path: Path, loaded_bundle, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    _initialize(world_root, loaded_bundle)

    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
    monkeypatch.setenv(
        "DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT",
        str(tmp_path / "_designated_live_not_used"),
    )
    monkeypatch.delenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", raising=False)
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")

    monkeypatch.setattr(live_config, "repo_root", lambda: repo)
    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)
    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)
    monkeypatch.setattr(promotable_mod, "world_graph_root", lambda: world_root)

    run_id, digest, source = _write_promotable_run(repo)
    client = TestClient(create_app())
    return client, world_root, repo, run_id, digest, source


def test_status_reports_initialized_head(world_client) -> None:
    client, *_rest = world_client
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
    client, world_root, _repo, run_id, _digest, source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(
            run_id, node_ids=["obj_session22_vial", "mystery_puddles"]
        ),
    )
    assert prepare.status_code == 200, prepare.text
    prepared = prepare.json()
    assert prepared["schema"] == "dmb_extract_promote_prepare_v1"
    assert prepared["acceptedProposalsCount"] >= 1
    assert prepared["proposalDigest"]
    assert prepared["runId"] == run_id
    assert prepared["campaignId"] == CAMPAIGN_ID
    assert prepared["sessionId"] == SESSION_ID
    package = prepared["reviewPackage"]
    sealed_uri = package["effect"]["verified_source_uri"]
    assert sealed_uri.startswith("repo://out/graph_memory/runs/")
    assert sealed_uri.endswith("normalized_recap_source.md")
    assert package["effect"]["contribution_meta"]["extraction_profile"] == "category_v1"
    assert (
        package["effect"]["contribution_meta"]["source_artifact_id"]
        == "artifact:recap:longmont-c2:session-22"
    )
    review_items = prepared["reviewItems"]
    assert isinstance(review_items, list) and review_items
    selectable = [item for item in review_items if item["selectable"]]
    assert selectable
    assert all(item["selectedByDefault"] is True for item in selectable)
    assert all("assertionId" in item and "summary" in item for item in review_items)
    assert all("dependsOnAssertionIds" in item for item in review_items)
    assert all("sliceQualifiedId" in item for item in review_items)
    assert all("contributionSliceId" in item for item in review_items)
    assert all("dependsOnSliceQualifiedIds" in item for item in review_items)
    assert all(
        item["sliceQualifiedId"].startswith(item["contributionSliceId"])
        for item in selectable
        if item.get("contributionSliceId")
    )
    relationships = [item for item in selectable if item["kind"] == "relationship"]
    if relationships:
        assert any("—" in item["label"] and "→" in item["label"] for item in relationships)
    summary = prepared["reviewSummary"]
    assert summary["newObjectCount"] + summary["connectExistingCount"] >= 1
    # Presentation model must not require clients to parse sealed effect internals.
    assert "accepted_proposals" not in prepared

    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assertion_ids = _selectable_assertion_ids(prepared)
    confirm = client.post(
        CONFIRM_URL,
        json=_confirm_body(package, assertion_ids),
    )
    assert confirm.status_code == 200, confirm.text
    confirmed = confirm.json()
    assert confirmed["schema"] == "dmb_extract_promote_confirm_v2"
    assert confirmed["outcome"] == "committed"
    assert confirmed["headAdvanced"] is True
    assert "ok" not in confirmed
    assert "result" not in confirmed
    assert "dryRun" not in confirmed
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after != head_before
    assert confirmed["committedRevisionId"] == head_after
    assert confirmed["affectedObjectIds"]
    assert confirmed["appliedAssertionCount"] >= 1

    # Exact retry after head advanced: already_applied, no second revision.
    retry = client.post(
        CONFIRM_URL,
        json=_confirm_body(package, assertion_ids),
    )
    assert retry.status_code == 200, retry.text
    retried = retry.json()
    assert retried["schema"] == "dmb_extract_promote_confirm_v2"
    assert retried["outcome"] == "already_applied"
    assert retried["headAdvanced"] is False
    assert retried["proposalDigest"] == confirmed["proposalDigest"]
    head_retry = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_retry == head_after
    assert retried["committedRevisionId"] == head_after


def test_confirm_rejects_tampered_package(world_client) -> None:
    client, _world, _repo, run_id, _digest, _source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
    )
    assert prepare.status_code == 200, prepare.text
    package = prepare.json()["reviewPackage"]
    package["effect"]["contribution_meta"]["authored_by"] = "attacker"

    confirm = client.post(
        CONFIRM_URL,
        json=_confirm_body(
            package,
            _selectable_assertion_ids(prepare.json()),
        ),
    )
    assert confirm.status_code == 409
    assert confirm.json()["code"] == "proposal_verification_failed"


def test_confirm_rejects_forbidden_operator_fields(world_client) -> None:
    client, _world, _repo, run_id, _digest, _source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
    )
    assert prepare.status_code == 200, prepare.text
    prepared = prepare.json()
    package = prepared["reviewPackage"]
    assertion_ids = _selectable_assertion_ids(prepared)

    for forbidden in (
        {"confirmingPrincipal": "gm@attacker"},
        {"allowLiveWorld": True},
    ):
        body = _confirm_body(package, assertion_ids)
        body.update(forbidden)
        confirm = client.post(CONFIRM_URL, json=body)
        assert confirm.status_code == 422, confirm.text
        assert confirm.json()["code"] == "invalid_request"


def test_confirm_succeeds_against_live_world_root(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, world_root, _repo, run_id, _digest, _source = world_client
    monkeypatch.setenv("DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT", str(world_root.resolve()))

    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
    )
    assert prepare.status_code == 200, prepare.text
    prepared = prepare.json()
    package = prepared["reviewPackage"]
    assertion_ids = _selectable_assertion_ids(prepared)

    confirm = client.post(
        CONFIRM_URL,
        json=_confirm_body(package, assertion_ids),
    )
    assert confirm.status_code == 200, confirm.text
    payload = confirm.json()
    assert payload["schema"] == "dmb_extract_promote_confirm_v2"
    assert payload["outcome"] == "committed"
    assert payload["headAdvanced"] is True


def test_confirm_published_false_returns_failure_proof(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _world, _repo, run_id, _digest, _source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
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
        json=_confirm_body(
            package,
            _selectable_assertion_ids(prepare.json()),
        ),
    )
    assert confirm.status_code == 409
    payload = confirm.json()
    assert payload["code"] == "merge_did_not_publish"
    assert payload["failureResult"]["ok"] is False


def test_confirm_empty_assertion_ids_does_not_advance_head(world_client) -> None:
    client, world_root, _repo, run_id, _digest, _source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(
            run_id, node_ids=["obj_session22_vial", "mystery_puddles"]
        ),
    )
    assert prepare.status_code == 200, prepare.text
    package = prepare.json()["reviewPackage"]
    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id

    confirm = client.post(
        CONFIRM_URL,
        json=_confirm_body(package, []),
    )
    assert confirm.status_code == 422
    assert confirm.json()["code"] == "empty_assertion_selection"
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_prepare_rejects_legacy_path_fields(world_client) -> None:
    client, _world, _repo, run_id, digest, source = world_client
    response = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v2",
            "runId": run_id,
            "candidateGraphPath": str(source),
            "sourceUri": str(source),
            "sourceRevisionId": digest,
            "preparedBy": "gm@http-prepare",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_prepare_rejects_body_world_id(world_client) -> None:
    client, _world, _repo, run_id, *_rest = world_client
    response = client.post(
        PREPARE_URL,
        json={
            "schema": "dmb_extract_promote_prepare_request_v2",
            "runId": run_id,
            "worldId": "foreign-world",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_prepare_rejects_candidate_scope_mismatch(world_client) -> None:
    client, _world, repo, *_rest = world_client
    bad_id = "graph-ingest:longmont-c2:session-22:scope-cand"
    _write_promotable_run(
        repo,
        run_id=bad_id,
        candidate_campaign_id="other-campaign",
        candidate_session_id="session-99",
    )
    response = client.post(PREPARE_URL, json=_prepare_body(bad_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_scope_mismatch"


def test_prepare_rejects_missing_manifest_source_artifact_id(world_client) -> None:
    client, _world, repo, *_rest = world_client
    bad_id = "graph-ingest:longmont-c2:session-22:no-source-artifact"
    _write_promotable_run(repo, run_id=bad_id, omit_source_artifact_id=True)
    response = client.post(PREPARE_URL, json=_prepare_body(bad_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_not_promotable"
    assert "source_artifact_id" in response.json()["message"]


def test_prepare_admits_configured_non_default_registry_root(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _world, repo, *_rest = world_client
    # Must not sit under corpus/Docs/evals/tmp allowlist — only registry admission.
    custom_rel = "sandbox/custom_ingest_runs"
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, custom_rel)
    custom_id = "graph-ingest:longmont-c2:session-22:custom-root"
    _write_promotable_run(
        repo,
        run_id=custom_id,
        runs_rel=custom_rel,
        extraction_profile="custom_root_profile",
    )
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(custom_id, node_ids=["obj_session22_vial"]),
    )
    assert prepare.status_code == 200, prepare.text
    package = prepare.json()["reviewPackage"]
    sealed = package["effect"]["verified_source_uri"]
    assert sealed.startswith(f"repo://{custom_rel}/")
    assert (
        package["effect"]["contribution_meta"]["extraction_profile"]
        == "custom_root_profile"
    )


def test_prepare_unknown_run_id(world_client) -> None:
    client, world_root, *_rest = world_client
    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    response = client.post(
        PREPARE_URL,
        json=_prepare_body("graph-ingest:longmont-c2:session-22:missing"),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "run_not_found"
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_prepare_rejects_failed_run(world_client) -> None:
    client, _world, repo, *_rest = world_client
    failed_id = "graph-ingest:longmont-c2:session-22:failed-run"
    _write_promotable_run(repo, run_id=failed_id, status="failed")
    response = client.post(PREPARE_URL, json=_prepare_body(failed_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_not_promotable"


def test_prepare_rejects_non_preview_ready_run(world_client) -> None:
    client, _world, repo, *_rest = world_client
    early_id = "graph-ingest:longmont-c2:session-22:candidate-only"
    _write_promotable_run(
        repo, run_id=early_id, status="candidate_validation_ready"
    )
    response = client.post(PREPARE_URL, json=_prepare_body(early_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_not_promotable"


def test_prepare_rejects_scope_mismatch(world_client) -> None:
    client, _world, repo, *_rest = world_client
    mismatched = "graph-ingest:other-campaign:session-99:fixture-promote"
    _write_promotable_run(
        repo,
        run_id=mismatched,
        campaign_id=CAMPAIGN_ID,
        session_id=SESSION_ID,
    )
    response = client.post(PREPARE_URL, json=_prepare_body(mismatched))
    assert response.status_code == 422
    assert response.json()["code"] == "run_scope_mismatch"


def test_prepare_rejects_missing_candidate(world_client) -> None:
    client, _world, repo, *_rest = world_client
    missing_id = "graph-ingest:longmont-c2:session-22:no-candidate"
    _write_promotable_run(repo, run_id=missing_id, omit_candidate=True)
    response = client.post(PREPARE_URL, json=_prepare_body(missing_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_not_promotable"


def test_prepare_rejects_malformed_registry_context_sibling(world_client) -> None:
    """Present but invalid registry sibling must fail closed (not recap-only)."""
    client, _world, repo, run_id, *_rest = world_client
    run_dir = (
        repo
        / "out/graph_memory/runs"
        / CAMPAIGN_ID
        / SESSION_ID
        / "fixture-promote"
    )
    sibling = run_dir / "registry_context_graph.json"
    sibling.write_text("{not-json", encoding="utf-8")
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "invalid_request"
    assert "registry context" in body["message"]


def test_prepare_rejects_empty_object_registry_context_sibling(world_client) -> None:
    """Wrong-schema {} sibling must fail closed — not silent recap-only."""
    client, _world, repo, run_id, *_rest = world_client
    run_dir = (
        repo
        / "out/graph_memory/runs"
        / CAMPAIGN_ID
        / SESSION_ID
        / "fixture-promote"
    )
    sibling = run_dir / "registry_context_graph.json"
    sibling.write_text("{}\n", encoding="utf-8")
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "invalid_request"
    assert "registry context" in body["message"]


def test_prepare_rejects_wrong_campaign_registry_context_sibling(world_client) -> None:
    """Typed registry with a foreign campaign_id must not be relabeled."""
    client, _world, repo, run_id, *_rest = world_client
    run_dir = (
        repo
        / "out/graph_memory/runs"
        / CAMPAIGN_ID
        / SESSION_ID
        / "fixture-promote"
    )
    sibling = run_dir / "registry_context_graph.json"
    wrong = _candidate_graph_payload(campaign_id="other-campaign")
    sibling.write_text(json.dumps(wrong, indent=2) + "\n", encoding="utf-8")
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "invalid_request"
    assert "campaign_id" in body["message"]


def test_prepare_rejects_blank_campaign_registry_context_sibling(world_client) -> None:
    """Unscoped registry (missing/blank campaign_id) must not inherit the run campaign."""
    client, _world, repo, run_id, *_rest = world_client
    run_dir = (
        repo
        / "out/graph_memory/runs"
        / CAMPAIGN_ID
        / SESSION_ID
        / "fixture-promote"
    )
    sibling = run_dir / "registry_context_graph.json"
    unscoped = _candidate_graph_payload()
    unscoped.pop("campaign_id", None)
    sibling.write_text(json.dumps(unscoped, indent=2) + "\n", encoding="utf-8")
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "invalid_request"
    assert "campaign_id is required" in body["message"]


def test_prepare_uses_manifest_declared_registry_path_not_only_sibling(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Declared registry under a non-sibling filename must still reach prepare."""
    client, _world, repo, *_rest = world_client
    alt_id = "graph-ingest:longmont-c2:session-22:declared-alt-registry"
    registry = _candidate_graph_payload()
    registry["preview_id"] = "preview:standing-party-alt"
    registry["nodes"] = [
        {
            **registry["nodes"][0],
            "node_id": "char_standing_pippa",
            "label": "Pippa",
            "node_type": "character",
            "description": "Standing party PC",
            "proposed_action": "create",
        }
    ]
    registry["edges"] = []
    _write_promotable_run(
        repo,
        run_id=alt_id,
        registry_context=registry,
        registry_filename="party_standing_context.json",
    )
    run_dir = (
        repo
        / "out/graph_memory/runs"
        / CAMPAIGN_ID
        / SESSION_ID
        / "fixture-promote"
    )
    assert (run_dir / "party_standing_context.json").is_file()
    assert not (run_dir / "registry_context_graph.json").exists()

    captured: dict[str, object] = {}

    def _capture_prepare(**kwargs):  # type: ignore[no-untyped-def]
        captured["registry_context_graph"] = kwargs.get("registry_context_graph")
        raise CandidateGraphMappingError(
            "stop-after-declared-registry-load-for-test"
        )

    monkeypatch.setattr(promote_svc, "prepare_extract_promote", _capture_prepare)

    response = client.post(PREPARE_URL, json=_prepare_body(alt_id))
    assert response.status_code == 409, response.text
    assert "stop-after-declared-registry-load-for-test" in response.json()["message"]
    loaded = captured.get("registry_context_graph")
    assert isinstance(loaded, dict)
    assert loaded["preview_id"] == "preview:standing-party-alt"
    assert loaded["nodes"][0]["node_id"] == "char_standing_pippa"


def test_prepare_rejects_missing_preview_union_store(world_client) -> None:
    """Ready flags alone are not enough — the preview store must exist on disk."""
    client, _world, repo, *_rest = world_client
    missing_id = "graph-ingest:longmont-c2:session-22:missing-preview"
    _write_promotable_run(repo, run_id=missing_id, omit_preview=True)
    response = client.post(PREPARE_URL, json=_prepare_body(missing_id))
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "run_not_promotable"
    assert "preview_union_store" in body["message"]


def test_prepare_rejects_deleted_preview_union_store(world_client) -> None:
    """Stale ready manifests fail when the referenced preview store was deleted."""
    client, _world, repo, *_rest = world_client
    stale_id = "graph-ingest:longmont-c2:session-22:deleted-preview"
    _write_promotable_run(repo, run_id=stale_id)
    preview = (
        repo
        / "out/graph_memory/runs/longmont-c2/session-22/fixture-promote"
        / "preview_union_supergraph.json"
    )
    assert preview.is_file()
    preview.unlink()
    response = client.post(PREPARE_URL, json=_prepare_body(stale_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_not_promotable"


def test_prepare_source_mismatch_does_not_disclose_computed_digest(
    world_client,
) -> None:
    client, _world, repo, *_rest = world_client
    bad_id = "graph-ingest:longmont-c2:session-22:bad-digest"
    _write_promotable_run(
        repo,
        run_id=bad_id,
        digest_override="sha256:" + ("0" * 64),
    )
    response = client.post(PREPARE_URL, json=_prepare_body(bad_id))
    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "source_revision_mismatch"
    dumped = json.dumps(payload)
    assert "computed=" not in dumped
    source = (
        repo
        / "out/graph_memory/runs/longmont-c2/session-22/fixture-promote"
        / "normalized_recap_source.md"
    )
    real = hashlib.sha256(source.read_bytes()).hexdigest()
    assert real not in dumped


def test_confirm_post_publication_verification_failure_reports_committed_revision(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, world_root, _repo, run_id, _digest, _source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
    )
    assert prepare.status_code == 200, prepare.text
    package = prepare.json()["reviewPackage"]
    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id

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
        json=_confirm_body(
            package,
            _selectable_assertion_ids(prepare.json()),
        ),
    )
    assert confirm.status_code == 200, confirm.text
    payload = confirm.json()
    assert payload["schema"] == "dmb_extract_promote_confirm_v2"
    assert payload["outcome"] == "published_audit_degraded"
    assert payload["auditStatus"] == "degraded"
    assert payload["committedRevisionId"]
    assert payload["headAdvanced"] is True
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after != head_before
    assert head_after == payload["committedRevisionId"]


def test_prepare_rejects_query_selectors(world_client) -> None:
    client, _world, _repo, run_id, *_rest = world_client
    response = client.post(
        f"{PREPARE_URL}?worldId=foreign",
        json=_prepare_body(run_id),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_prepare_rejects_invalid_candidate_health(world_client) -> None:
    client, _world, repo, *_rest = world_client
    bad_id = "graph-ingest:longmont-c2:session-22:invalid-candidate"
    _write_promotable_run(repo, run_id=bad_id, candidate_graph_valid=False)
    response = client.post(PREPARE_URL, json=_prepare_body(bad_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_not_promotable"


def test_confirm_already_applied_keeps_published_false(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, world_root, _repo, run_id, _digest, _source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
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
        json=_confirm_body(
            package,
            _selectable_assertion_ids(prepare.json()),
        ),
    )
    assert confirm.status_code == 200, confirm.text
    payload = confirm.json()
    assert payload["schema"] == "dmb_extract_promote_confirm_v2"
    assert payload["outcome"] == "already_applied"
    assert payload["headAdvanced"] is False
    assert "published" not in payload
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_confirm_audit_pins_projection_to_committed_revision(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, world_root, _repo, run_id, _digest, _source = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
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
        json=_confirm_body(
            package,
            _selectable_assertion_ids(prepare.json()),
        ),
    )
    assert confirm.status_code == 200, confirm.text
    receipt = confirm.json()
    committed = receipt["committedRevisionId"]
    assert committed
    assert seen["compare_revision_id"] == committed
    assert seen["revision_pin"] == committed
    assert receipt["outcome"] == "committed"


def test_path_contract_still_rejects_world_store_sources(world_client) -> None:
    """Browser path contract must not admit world-store evidence."""
    _client, world_root, _repo, _run_id, _digest, _source = world_client
    planted = world_root / "planted_source.md"
    planted.write_text("must not be evidentiary authority\n", encoding="utf-8")
    with pytest.raises(promote_svc.ExtractPromoteError) as exc:
        promote_svc.resolve_promote_source_uri(str(planted))
    assert exc.value.code == "invalid_source_uri"
    assert "world graph store" in str(exc.value) or "ingest-run" in str(exc.value)


def test_campaignless_worldbuilding_run_is_inspect_only(world_client) -> None:
    """Campaignless worldbuilding loads for review but cannot prepare/confirm."""
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(
        repo, campaign_id=None, candidate_campaign_id=None
    )
    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 200, review.text
    body = review.json()
    assert body.get("campaignId") in (None, "")
    assert body.get("sessionId") in (None, "")
    assert body["promotable"] is False
    assert "inspect-only" in (body.get("promotableReason") or "").lower()

    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial", "mystery_puddles"]),
    )
    assert prepare.status_code == 422, prepare.text
    assert prepare.json()["code"] == "not_promote_eligible"
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_prepare_rejects_worldbuilding_draft_extraction_run(world_client) -> None:
    """Real worldbuilding-profile semantics are inspect-only — not publishable."""
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(repo)

    # Fixture stamps the profile's worldbuilding_draft semantic, not played_canon.
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    candidate = json.loads(resolved.candidate_graph_path.read_text(encoding="utf-8"))
    assert candidate["nodes"][0]["semantic_state"]["canon_state"] == "worldbuilding_draft"

    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 200, review.text
    assert review.json()["promotable"] is False

    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial", "mystery_puddles"]),
    )
    assert prepare.status_code == 422, prepare.text
    body = prepare.json()
    assert body["code"] == "not_promote_eligible"
    assert "worldbuilding" in body["message"].lower()
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_exact_recap_confirm_replay_is_a_truthful_no_op(world_client) -> None:
    """Response-loss retry reuses the existing receipt; the head advances once."""
    client, world_root, _repo, run_id, *_rest = world_client
    prepare = client.post(
        PREPARE_URL, json=_prepare_body(run_id, node_ids=["obj_session22_vial"])
    )
    assert prepare.status_code == 200, prepare.text
    prepared = prepare.json()
    body = _confirm_body(prepared["reviewPackage"], _selectable_assertion_ids(prepared))

    first = client.post(CONFIRM_URL, json=body)
    assert first.status_code == 200, first.text
    assert first.json()["outcome"] == "committed"
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id

    replay = client.post(CONFIRM_URL, json=body)
    assert replay.status_code == 200, replay.text
    replayed = replay.json()
    assert replayed["outcome"] == "already_applied"
    assert replayed["headAdvanced"] is False
    assert replayed["committedRevisionId"] == head_after
    assert (
        kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
        == head_after
    )


def test_exact_recap_confirm_rejects_tampered_package(world_client) -> None:
    """Sealed-proposal protection remains for the recap publication path."""
    client, world_root, _repo, run_id, *_rest = world_client
    prepare = client.post(
        PREPARE_URL, json=_prepare_body(run_id, node_ids=["obj_session22_vial"])
    )
    assert prepare.status_code == 200, prepare.text
    prepared = prepare.json()
    package = prepared["reviewPackage"]
    package["effect"]["contribution_meta"]["authored_by"] = "attacker"
    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id

    confirm = client.post(
        CONFIRM_URL, json=_confirm_body(package, _selectable_assertion_ids(prepared))
    )
    assert confirm.status_code == 409
    assert confirm.json()["code"] == "proposal_verification_failed"
    assert (
        kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
        == head_before
    )


def test_recap_prepare_still_seals_recap_source_domain(world_client) -> None:
    """The generic source_domain seam must not relabel existing recap runs."""
    client, _world, _repo, run_id, *_rest = world_client
    prepare = client.post(
        PREPARE_URL,
        json=_prepare_body(run_id, node_ids=["obj_session22_vial"]),
    )
    assert prepare.status_code == 200, prepare.text
    domains = _sealed_source_domains(prepare.json()["reviewPackage"])
    assert "recap" in domains
    assert "worldbuilding" not in domains


def test_prepare_rejects_non_reviewable_extraction_run(world_client) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(repo, status="prepared")
    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_not_promotable"
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == head_before


def test_exact_run_review_package_includes_source_prose_and_evidence(
    world_client,
) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, source = _write_reviewable_extraction_run(repo, campaign_id=None)
    response = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema"] == "dmb_extract_promote_exact_run_review_v1"
    assert body["runId"] == run_id
    assert body["sourceDomain"] == "worldbuilding"
    assert body.get("campaignId") in (None, "")
    assert body.get("sessionId") in (None, "")
    assert body["promotable"] is False
    assert body.get("promotableReason")
    assert "Worldbuilding source for promote." in body["sourceProse"]
    assert body["sourceProse"] == source.read_text(encoding="utf-8")
    assert body["assertions"]
    vial = next(item for item in body["assertions"] if item["assertionId"] == "obj_session22_vial")
    assert vial["evidence"]
    evidence = vial["evidence"][0]
    assert evidence["paragraphText"] == "Worldbuilding source for promote."
    assert "Worldbuilding source for promote." in evidence["anchorQuotes"]
    assert evidence["sourceSpanRefId"]
    assert evidence["startLine"] is not None


def _mutate_extraction_candidate(repo, run_id: str, mutator) -> None:
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    from apps.live_control_server.services.promotable_ingest_run import (
        _resolve_extraction_component_path,
    )

    run = get_extraction_run(repo, run_id)
    candidate_path = _resolve_extraction_component_path(
        repo, run.components["candidate_graph"].uri, label="candidate_graph"
    )
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    mutator(payload)
    candidate_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # Digest must match the component seal or reviewable evidence fails before
    # our span checks. Re-seal the component digest on the registry record.
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    from apps.live_control_server.services.graph_run_registry import (
        extraction_runs_path,
    )
    from src.live_play.live_store import load_json, write_json

    path = extraction_runs_path(repo)
    document = load_json(path)
    for record in document["records"]:
        if record["run_id"] == run_id:
            record["components"]["candidate_graph"]["sha256"] = digest
            break
    write_json(path, document)


def test_review_and_prepare_reject_unknown_span_ref(world_client) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(repo)

    def mutate(payload: dict) -> None:
        for holder in (*(payload.get("nodes") or []), *(payload.get("edges") or [])):
            for ref in holder.get("evidence_refs") or []:
                ref["source_span_ref_id"] = "span:does-not-exist"

    _mutate_extraction_candidate(repo, run_id, mutate)
    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 422, review.text
    assert review.json()["code"] == "run_not_promotable"
    assert "unknown" in review.json()["message"].lower() or any(
        "unknown_span_ref" in (d.get("code") or "")
        for d in review.json().get("diagnostics") or []
    )
    prepare = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert prepare.status_code == 422, prepare.text
    assert prepare.json()["code"] == "run_not_promotable"


def test_review_and_prepare_reject_wrong_source_artifact_on_evidence(
    world_client,
) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(repo)

    def mutate(payload: dict) -> None:
        for holder in (*(payload.get("nodes") or []), *(payload.get("edges") or [])):
            for ref in holder.get("evidence_refs") or []:
                ref["source_artifact_id"] = "artifact:worldbuilding:other"

    _mutate_extraction_candidate(repo, run_id, mutate)
    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 422
    prepare = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert prepare.status_code == 422


def test_review_and_prepare_reject_missing_evidence_refs(world_client) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(repo)

    def mutate(payload: dict) -> None:
        for node in payload.get("nodes") or []:
            if node.get("node_id") == "obj_session22_vial":
                node["evidence_refs"] = []

    _mutate_extraction_candidate(repo, run_id, mutate)
    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 422
    prepare = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert prepare.status_code == 422


def test_review_and_prepare_reject_false_anchor_quotes(world_client) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(repo)

    def mutate(payload: dict) -> None:
        for holder in (*(payload.get("nodes") or []), *(payload.get("edges") or [])):
            for ref in holder.get("evidence_refs") or []:
                ref["anchor_quotes"] = ["this quote is not in the source paragraph"]

    _mutate_extraction_candidate(repo, run_id, mutate)
    review = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert review.status_code == 422, review.text
    assert any(
        "false_anchor_quote" in (d.get("code") or "")
        for d in review.json().get("diagnostics") or []
    ) or "anchor quote" in review.json()["message"].lower()
    prepare = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert prepare.status_code == 422


def test_prepare_rejects_session_invention_for_sessionless_extraction_run(
    world_client,
) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(
        repo, invent_session_in_candidate=True
    )
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_scope_mismatch"


def test_prepare_rejects_campaign_invention_for_campaignless_extraction_run(
    world_client,
) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(
        repo,
        campaign_id=None,
        candidate_campaign_id=CAMPAIGN_ID,
    )
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "run_scope_mismatch"
    assert "invents a campaign" in body["message"]


def test_prepare_rejects_both_campaignless_worldbuilding_extraction_run(
    world_client,
) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(
        repo,
        campaign_id=None,
        candidate_campaign_id=None,
    )
    response = client.post(
        PREPARE_URL, json=_prepare_body(run_id, node_ids=["obj_session22_vial"])
    )
    assert response.status_code == 422
    assert response.json()["code"] == "not_promote_eligible"


def test_prepare_rejects_campaign_bound_worldbuilding_extraction_run(
    world_client,
) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(repo)
    response = client.post(
        PREPARE_URL, json=_prepare_body(run_id, node_ids=["obj_session22_vial"])
    )
    assert response.status_code == 422
    assert response.json()["code"] == "not_promote_eligible"


def test_prepare_rejects_campaign_bound_run_with_missing_candidate_campaign(
    world_client,
) -> None:
    """A campaign-bound run still requires the candidate to carry the run's campaign."""
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(
        repo, candidate_campaign_id=None
    )
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_scope_mismatch"


def test_prepare_rejects_campaign_bound_run_with_different_candidate_campaign(
    world_client,
) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(
        repo, candidate_campaign_id="other-campaign"
    )
    response = client.post(PREPARE_URL, json=_prepare_body(run_id))
    assert response.status_code == 422
    assert response.json()["code"] == "run_scope_mismatch"


def test_prepare_maps_missing_world_graph_head_to_world_not_initialized(
    world_client,
) -> None:
    """Missing head is a diagnosable 409, not an opaque 500."""
    client, world_root, _repo, run_id, *_rest = world_client
    head = world_root / "graph_memory" / "worlds" / WORLD_ID / "head.json"
    assert head.is_file()
    head.unlink()

    response = client.post(
        PREPARE_URL, json=_prepare_body(run_id, node_ids=["obj_session22_vial"])
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "world_not_initialized"
    assert "not initialized" in body["message"].lower()
    # Public diagnostics must stay non-sensitive (no traceback / absolute paths).
    for item in body.get("diagnostics") or []:
        message = str(item.get("message") or "")
        assert "Traceback" not in message
        assert "/tmp/" not in message


def test_review_package_uses_run_pinned_span_index_component(world_client) -> None:
    """Evidence validation must follow the run-pinned span-index URI, not the registry canonical path."""
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, _world, repo, *_rest = world_client
    run_id, _source = _write_reviewable_extraction_run(
        repo, pin_noncanonical_span_index=True
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        source_span_index_path,
    )

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.source_span_index_path is not None
    assert resolved.source_span_index_path.name == "alt_source_span_index.json"
    pinned_span_id = json.loads(
        resolved.source_span_index_path.read_text(encoding="utf-8")
    )["spans"][0]["source_span_id"]
    canonical_ids = {
        span["source_span_id"]
        for span in json.loads(
            source_span_index_path(repo, resolved.source_artifact_id).read_text(
                encoding="utf-8"
            )
        )["spans"]
    }
    assert pinned_span_id not in canonical_ids

    response = client.get(f"/api/live/extract-promote/runs/{run_id}/review-package")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assertions"]
    evidence_span_ids = {
        item["evidence"][0]["sourceSpanRefId"]
        for item in body["assertions"]
        if item.get("evidence")
    }
    assert pinned_span_id in evidence_span_ids


def _worldbuilding_prepare_body(
    run_id: str,
    parent_revision_id: str,
    *,
    dispositions: list[dict[str, str]],
) -> dict:
    return {
        "schema": "dmb_worldbuilding_write_plan_prepare_request_v1",
        "runId": run_id,
        "expectedParentRevisionId": parent_revision_id,
        "dispositions": dispositions,
    }


def test_worldbuilding_prepare_returns_deterministic_inert_plan(world_client) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    before_world = {
        path.relative_to(world_root).as_posix(): path.read_bytes()
        for path in world_root.rglob("*")
        if path.is_file()
    }
    dispositions = [
        {"assertionId": "obj_session22_vial", "decision": "create_new"},
        {"assertionId": "mystery_puddles", "decision": "create_new"},
        {"assertionId": "e33", "decision": "accept"},
    ]
    first = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id, parent, dispositions=dispositions
        ),
    )
    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert first_payload["schema"] == "dmb_worldbuilding_write_plan_v1"
    assert first_payload["version"] == 1
    assert first_payload["confirmable"] is False
    assert first_payload["sourceDomain"] == "worldbuilding"
    assert first_payload["extractionProfile"] == "worldbuilding_shepherds_flock_v0@0.1"
    assert first_payload["effect"]["contributionMeta"]["authoredBy"] == (
        "live_control:worldbuilding_write_plan"
    )
    assert first_payload["effect"]["contributionMeta"]["sourceKind"] == (
        "source_extraction"
    )
    assert first_payload["effect"]["nodeIdMap"] == {
        "mystery_puddles": "mystery_puddles",
        "obj_session22_vial": "obj_session22_vial",
    }
    assert first_payload["summary"]["acceptedEdgeCount"] == 1
    assert first_payload["effect"]["acceptedProposals"]
    assert all(
        item["value"]["source_domains"] == ["worldbuilding"]
        for item in first_payload["effect"]["acceptedProposals"]
    )

    second = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=list(reversed(dispositions)),
        ),
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()
    for key in (
        "planId",
        "planDigest",
        "decisionDigest",
        "parentRevisionId",
        "runId",
        "sourceArtifactId",
        "sourceRevisionId",
        "candidatePreviewId",
        "effect",
        "summary",
    ):
        assert second_payload[key] == first_payload[key]
    after_world = {
        path.relative_to(world_root).as_posix(): path.read_bytes()
        for path in world_root.rglob("*")
        if path.is_file()
    }
    assert after_world == before_world
    assert kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id == parent


def test_worldbuilding_prepare_rejects_incomplete_and_invalid_dispositions(
    world_client,
) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id

    incomplete = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
            ],
        ),
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["code"] == "invalid_disposition_set"

    duplicate = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "obj_session22_vial", "decision": "reject"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "defer"},
            ],
        ),
    )
    assert duplicate.status_code == 422
    assert duplicate.json()["code"] == "invalid_disposition_set"

    kind_mismatch = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "accept"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "defer"},
            ],
        ),
    )
    assert kind_mismatch.status_code == 422
    assert kind_mismatch.json()["code"] == "invalid_disposition"


def test_worldbuilding_prepare_rejects_stale_parent_without_mutation(world_client) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    response = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            "rev:" + ("0" * 32),
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "accept"},
            ],
        ),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "stale_parent_revision"
    assert kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id == before


def test_worldbuilding_prepare_concurrent_head_advancement_returns_409(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    real_verify = promote_svc.verify_worldbuilding_write_plan

    def _advance_head_then_verify(*args, **kwargs):
        head, _revision, store = kernel.open_current_world_graph(world_root, WORLD_ID)
        advanced = kernel.publish_world_graph_revision(
            world_root,
            WORLD_ID,
            store,
            operation_ids=["op:worldbuilding-prepare-concurrent-head"],
            expected_parent_revision_id=head.head_revision_id,
        )
        assert advanced.revision.revision_id != parent
        return real_verify(*args, **kwargs)

    monkeypatch.setattr(
        promote_svc,
        "verify_worldbuilding_write_plan",
        _advance_head_then_verify,
    )
    response = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "accept"},
            ],
        ),
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "stale_parent_revision"


def test_worldbuilding_prepare_confirm_rejects_plan_without_mutation(
    world_client,
) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    prepared = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "reject"},
                {"assertionId": "mystery_puddles", "decision": "defer"},
                {"assertionId": "e33", "decision": "defer"},
            ],
        ),
    )
    assert prepared.status_code == 200, prepared.text
    package = prepared.json()
    before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    confirm = client.post(
        CONFIRM_URL,
        json=_confirm_body(package, ["assertion:never-used"]),
    )
    assert confirm.status_code == 422
    assert confirm.json()["code"] == "invalid_request"
    assert kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id == before


def _worldbuilding_confirm_body(plan: dict) -> dict:
    return {
        "schema": "dmb_worldbuilding_write_plan_confirm_request_v1",
        "plan": plan,
    }


def _default_worldbuilding_dispositions() -> list[dict[str, str]]:
    return [
        {"assertionId": "obj_session22_vial", "decision": "create_new"},
        {"assertionId": "mystery_puddles", "decision": "create_new"},
        {"assertionId": "e33", "decision": "accept"},
    ]


def test_worldbuilding_prepare_then_confirm_commits_once_and_retry_is_already_applied(
    world_client,
) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    prepared = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=_default_worldbuilding_dispositions(),
        ),
    )
    assert prepared.status_code == 200, prepared.text
    plan = prepared.json()

    first = client.post(WORLD_BUILDING_CONFIRM_URL, json=_worldbuilding_confirm_body(plan))
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["schema"] == "dmb_worldbuilding_write_plan_confirm_v1"
    assert first_body["outcome"] == "committed"
    assert first_body["headAdvanced"] is True
    assert first_body["parentRevisionId"] == parent
    assert first_body["committedRevisionId"] != parent
    assert first_body["appliedAssertionCount"] == plan["summary"]["acceptedAssertionCount"]
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    assert head_after == first_body["committedRevisionId"]

    committed_store = kernel.load_world_graph_revision(
        world_root, WORLD_ID, first_body["committedRevisionId"]
    )
    created_ids = {
        item["subjectNodeId"]
        for item in plan["effect"]["acceptedProposals"]
        if item.get("assertionKind") == "object"
    }
    for node_id in created_ids:
        assert node_id in committed_store.nodes

    second = client.post(WORLD_BUILDING_CONFIRM_URL, json=_worldbuilding_confirm_body(plan))
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["outcome"] == "already_applied"
    assert second_body["headAdvanced"] is False
    assert second_body["contributionId"] == first_body["contributionId"]
    assert (
        kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
        == head_after
    )


def test_worldbuilding_confirm_rejects_stale_parent_without_mutation(
    world_client,
) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    prepared = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=_default_worldbuilding_dispositions(),
        ),
    )
    assert prepared.status_code == 200, prepared.text
    plan = prepared.json()
    head, _revision, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    advanced = kernel.publish_world_graph_revision(
        world_root,
        WORLD_ID,
        store,
        operation_ids=["op:worldbuilding-confirm-stale-parent"],
        expected_parent_revision_id=head.head_revision_id,
    )
    before_bytes = {
        path.relative_to(world_root).as_posix(): path.read_bytes()
        for path in world_root.rglob("*")
        if path.is_file()
    }
    response = client.post(
        WORLD_BUILDING_CONFIRM_URL, json=_worldbuilding_confirm_body(plan)
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "stale_parent_revision"
    assert (
        kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
        == advanced.revision.revision_id
    )
    after_bytes = {
        path.relative_to(world_root).as_posix(): path.read_bytes()
        for path in world_root.rglob("*")
        if path.is_file()
    }
    assert after_bytes == before_bytes


def test_worldbuilding_confirm_rejects_presentation_and_effect_tamper(
    world_client,
) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    prepared = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=_default_worldbuilding_dispositions(),
        ),
    )
    assert prepared.status_code == 200, prepared.text
    base_plan = prepared.json()

    summary_tamper = json.loads(json.dumps(base_plan))
    summary_tamper["summary"]["acceptedAssertionCount"] = 0
    summary_tamper["summary"]["rejectedCandidateCount"] = 500
    summary_resp = client.post(
        WORLD_BUILDING_CONFIRM_URL, json=_worldbuilding_confirm_body(summary_tamper)
    )
    assert summary_resp.status_code in {409, 422}, summary_resp.text
    assert summary_resp.json()["code"] == "plan_verification_failed"

    diagnostics_tamper = json.loads(json.dumps(base_plan))
    diagnostics_tamper["diagnostics"] = list(diagnostics_tamper["diagnostics"]) + [
        "everything is unsafe"
    ]
    diagnostics_resp = client.post(
        WORLD_BUILDING_CONFIRM_URL,
        json=_worldbuilding_confirm_body(diagnostics_tamper),
    )
    assert diagnostics_resp.status_code in {409, 422}, diagnostics_resp.text
    assert diagnostics_resp.json()["code"] == "plan_verification_failed"

    reason_tamper = json.loads(json.dumps(base_plan))
    reason_tamper["confirmableReason"] = "ready to commit"
    reason_resp = client.post(
        WORLD_BUILDING_CONFIRM_URL, json=_worldbuilding_confirm_body(reason_tamper)
    )
    assert reason_resp.status_code in {409, 422, 422}, reason_resp.text
    # Invalid literal may be request validation (422) or plan verification.
    assert reason_resp.status_code == 422

    effect_tamper = json.loads(json.dumps(base_plan))
    effect_tamper["effect"]["acceptedProposals"][0]["label"] = "tampered-label"
    from graph_memory.worldbuilding_write_plan import _canonical_effect, _digest

    effect = _canonical_effect(effect_tamper["effect"])
    effect_tamper["effect"] = effect
    decision_digest = _digest(effect["decision_snapshot"])
    plan_identity = {
        "world_id": effect_tamper["worldId"],
        "parent_revision_id": effect_tamper["parentRevisionId"],
        "run_id": effect_tamper["runId"],
        "source_domain": "worldbuilding",
        "source_artifact_id": effect_tamper["sourceArtifactId"],
        "source_revision_id": effect_tamper["sourceRevisionId"],
        "extraction_profile": effect_tamper["extractionProfile"],
        "candidate_preview_id": effect_tamper["candidatePreviewId"],
        "candidate_schema": effect_tamper["candidateSchema"],
        "candidate_version": effect_tamper["candidateVersion"],
        "decision_snapshot": effect["decision_snapshot"],
        "effect": effect,
    }
    plan_digest = _digest(plan_identity)
    effect_tamper["decisionDigest"] = decision_digest
    effect_tamper["planDigest"] = plan_digest
    effect_tamper["planId"] = (
        "worldbuilding-write-plan:" f"{plan_digest.removeprefix('sha256:')[:24]}"
    )
    before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    effect_resp = client.post(
        WORLD_BUILDING_CONFIRM_URL, json=_worldbuilding_confirm_body(effect_tamper)
    )
    assert effect_resp.status_code in {409, 422}, effect_resp.text
    assert effect_resp.json()["code"] == "plan_verification_failed"
    assert kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id == before


def test_worldbuilding_prepare_rejects_wrong_profile_and_recap_run(world_client) -> None:
    from tests.test_promotable_ingest_run import _write_reviewable_extraction_run

    client, world_root, repo, *_rest = world_client
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    wrong_profile_id, _source = _write_reviewable_extraction_run(
        repo,
    )
    wrong = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            wrong_profile_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "accept"},
            ],
        ),
    )
    assert wrong.status_code == 422
    assert wrong.json()["code"] == "unsupported_worldbuilding_profile"

    recap_id, *_rest = _write_promotable_run(
        repo,
        run_id="graph-ingest:longmont-c2:session-22:worldbuilding-route-recap",
    )
    recap = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            recap_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "accept"},
            ],
        ),
    )
    assert recap.status_code == 422
    assert recap.json()["code"] == "worldbuilding_run_required"


def test_worldbuilding_prepare_has_safe_internal_error_boundary(
    world_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, world_root, repo, *_rest = world_client
    run_id, _source = _write_bld08_reviewable_run(repo)
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id

    def _boom(*_args, **_kwargs):
        raise RuntimeError("private implementation detail")

    monkeypatch.setattr(promote_svc, "build_worldbuilding_write_plan", _boom)
    response = client.post(
        WORLD_BUILDING_PREPARE_URL,
        json=_worldbuilding_prepare_body(
            run_id,
            parent,
            dispositions=[
                {"assertionId": "obj_session22_vial", "decision": "reject"},
                {"assertionId": "mystery_puddles", "decision": "defer"},
                {"assertionId": "e33", "decision": "defer"},
            ],
        ),
    )
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "extract_promote_internal_error"
    assert "private implementation detail" not in response.text
    assert "Reference:" in body["diagnostics"][0]["message"]
