"""CLI boundary tests for promote_extract_contribution prepare/confirm."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import argparse
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
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
CLI = REPO_ROOT / "scripts" / "promote_extract_contribution.py"
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


def _candidate_graph_payload() -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:cli-promote-vial",
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
        "diagnostics": _diagnostics(),
    }


def _run_cli(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=check,
    )


def _prepare_world(tmp_path: Path, loaded_bundle) -> tuple[Path, Path, Path, str]:
    world_root = tmp_path / "world"
    _initialize(world_root, loaded_bundle)
    source = tmp_path / "source.md"
    source.write_text("session 22 promote fixture\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    graph_path = tmp_path / "candidate_graph.json"
    graph_path.write_text(
        json.dumps(_candidate_graph_payload(), indent=2) + "\n", encoding="utf-8"
    )
    package_path = tmp_path / "review_package.json"
    result = _run_cli(
        [
            "prepare",
            "--candidate-graph",
            str(graph_path),
            "--world-root",
            str(world_root),
            "--source-uri",
            str(source),
            "--source-revision-id",
            f"sha256:{digest}",
            "--prepared-by",
            "gm@prepare",
            "--node-ids",
            "obj_session22_vial",
            "mystery_puddles",
            "--output",
            str(package_path),
        ]
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert package_path.is_file()
    return world_root, graph_path, package_path, digest


def test_cli_prepare_rejects_bad_source_revision(
    tmp_path: Path, loaded_bundle
) -> None:
    world_root = tmp_path / "world"
    _initialize(world_root, loaded_bundle)
    source = tmp_path / "source.md"
    source.write_text("body\n", encoding="utf-8")
    graph_path = tmp_path / "candidate_graph.json"
    graph_path.write_text(json.dumps(_candidate_graph_payload()), encoding="utf-8")
    result = _run_cli(
        [
            "prepare",
            "--candidate-graph",
            str(graph_path),
            "--world-root",
            str(world_root),
            "--source-uri",
            str(source),
            "--source-revision-id",
            "sha256:deadbeef",
            "--prepared-by",
            "gm@prepare",
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert result.returncode != 0
    assert "source_revision_id mismatch" in (result.stderr + result.stdout)


def test_cli_confirm_rejects_tampered_package(
    tmp_path: Path, loaded_bundle
) -> None:
    world_root, _graph, package_path, _digest = _prepare_world(tmp_path, loaded_bundle)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["effect"]["accepted_proposals"][0]["label"] = "TAMPERED"
    package_path.write_text(json.dumps(package, indent=2), encoding="utf-8")
    result = _run_cli(
        [
            "confirm",
            "--review-package",
            str(package_path),
            "--world-root",
            str(world_root),
            "--confirming-principal",
            "gm@confirm",
            "--output",
            str(tmp_path / "proof.json"),
        ]
    )
    assert result.returncode != 0
    assert "proposal_digest mismatch" in (result.stderr + result.stdout)


def test_cli_confirm_published_false_writes_failure_proof(
    tmp_path: Path, loaded_bundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate Kernel returning published=False without raising."""
    world_root, _graph, package_path, _digest = _prepare_world(tmp_path, loaded_bundle)

    sys_path_inserted = False
    if str(REPO_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        sys_path_inserted = True
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    import importlib.util

    import graph_memory.extract_promote_ops as ops

    spec = importlib.util.spec_from_file_location(
        "promote_extract_contribution", CLI
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

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

    args = argparse.Namespace(
        review_package=str(package_path),
        world_root=str(world_root),
        assertion_ids=None,
        confirming_principal="gm@confirm",
        dry_run=False,
        allow_live_world=False,
        allow_idempotent_noop=False,
        output=str(tmp_path / "proof.json"),
    )
    code = mod.cmd_confirm(args)
    assert code == 1
    proof = json.loads(Path(args.output).read_text(encoding="utf-8"))
    assert proof["ok"] is False
    assert proof["failure_reason"] == "merge_did_not_publish"


def test_cli_prepare_confirm_success(tmp_path: Path, loaded_bundle) -> None:
    world_root, _graph, package_path, _digest = _prepare_world(tmp_path, loaded_bundle)
    proof_path = tmp_path / "promote_proof.json"
    result = _run_cli(
        [
            "confirm",
            "--review-package",
            str(package_path),
            "--world-root",
            str(world_root),
            "--confirming-principal",
            "gm@confirm",
            "--output",
            str(proof_path),
        ]
    )
    assert result.returncode == 0, result.stderr + result.stdout
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    assert proof["ok"] is True
    assert proof["merge"]["published"] is True
    assert proof["rebuild_equivalent_to_head"] is True
    assert "proposal_digest" in proof
    store = kernel.open_current_world_graph(world_root, WORLD_ID)[2]
    assert any("vial" in (n.label or "").lower() for n in store.nodes.values())
