"""Eldyrwild initial contribution bundle dry-run proof tests (PR006C)."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.contribution_bundles import (
    load_contribution_bundle,
    validate_contribution_bundle,
)
from graph_memory.contribution_bundles.load import compute_bundle_digest
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.union_supergraph.validate import validate_union_supergraph_fixture

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "c8eb7e6ca7e735c40822cb1e6835f9949f2cd915b57f5704e7b4daeb72cf2fca"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
MIREWARD_ASSERTION_ID = "assertion:3e2a37249f847f60"
QUESTIONABLE_COMPANY_ASSERTION_ID = "assertion:e43e22317e459bac"

REQUIRED_NODE_IDS = {
    "location:mirathorn",
    "location:mireward",
    "party:questionable-company",
    "pc:bonogo",
    "pc:baergrom",
    "pc:ephanna",
    "pc:caelynn",
    "pc:stafl",
    "pc:karsemine",
    "event:longmont-c2:session-22:mireward-road",
    "event:longmont-c2:session-23:mireward-gate-battle",
    "threat:tripod-null-calf",
}

REQUIRED_EDGE_IDS = {
    "edge:pc:bonogo:member_of:party:questionable-company",
    "edge:pc:baergrom:member_of:party:questionable-company",
    "edge:pc:ephanna:member_of:party:questionable-company",
    "edge:pc:caelynn:member_of:party:questionable-company",
    "edge:pc:stafl:member_of:party:questionable-company",
    "edge:pc:karsemine:member_of:party:questionable-company",
    "edge:party:questionable-company:participated_in:event:longmont-c2:session-22:mireward-road",
    "edge:event:longmont-c2:session-22:mireward-road:occurred_at:location:mireward",
    "edge:party:questionable-company:participated_in:event:longmont-c2:session-23:mireward-gate-battle",
    "edge:event:longmont-c2:session-23:mireward-gate-battle:occurred_at:location:mireward",
    "edge:threat:tripod-null-calf:appeared_in:event:longmont-c2:session-23:mireward-gate-battle",
}

EXPECTED_SOURCE_DOMAINS = {
    "manual_seed",
    "recap",
    "statblock",
    "worldbuilding",
}

ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",  # 001 mirathorn world hub
    "contribution:43782369bd717d32",  # 002 mireward world hub
    "contribution:33d7cdb0ff623f28",  # 003 roster
    "contribution:c086a0b72324ff16",  # 004 session 22
    "contribution:1227841724520c18",  # 005 session 23
    "contribution:022187fdefdf4557",  # 006 tripod
]

MIREWARD_CONTRIBUTION_IDS = {
    "contribution:43782369bd717d32",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
}

QUESTIONABLE_COMPANY_CONTRIBUTION_IDS = {
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
}

SENTINEL_NODE_IDS = {
    "sentinel:technical-alpha",
    "sentinel:technical-beta",
}
FOCUS_SESSION_ID = "session-22"
CAMPAIGN_ID = "longmont-c2"

TRIPOD_ATTRIBUTE_PREDICATES = {
    "battlefield_role",
    "challenge_expectation",
    "first_appearance",
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_manifest(bundle_root: Path) -> dict:
    return _read_json(bundle_root / "manifest.json")


def _write_manifest(
    bundle_root: Path,
    manifest: dict,
    *,
    update_digest: bool = True,
) -> None:
    if update_digest:
        manifest["bundle_digest"] = compute_bundle_digest(manifest)
    _write_json(bundle_root / "manifest.json", manifest)


def _sync_entry_sha(manifest: dict, bundle_root: Path, rel_path: str) -> None:
    file_path = bundle_root / rel_path
    digest = _sha256_bytes(file_path.read_bytes())
    for entry in manifest["ordered_contributions"]:
        if entry["path"] == rel_path:
            entry["sha256"] = digest
            return
    raise KeyError(rel_path)


def _copy_bundle(tmp_path: Path) -> Path:
    dest = tmp_path / "bundle"
    shutil.copytree(BUNDLE_PATH, dest)
    return dest


def _build_sentinel_union_store() -> UnionSupergraphStore:
    """Minimal valid union store using unrelated sentinel IDs only."""
    payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": CAMPAIGN_ID,
        "focus_session_id": FOCUS_SESSION_ID,
        "nodes": {
            "sentinel:technical-alpha": {
                "node_id": "sentinel:technical-alpha",
                "label": "Technical Alpha",
                "kind": "npc",
                "role": "npc",
                "aliases": ["Technical Alpha"],
                "source_domains": ["recap", "worldbuilding"],
                "evidence_ref_ids": [
                    "evidence:sentinel:session-22:alpha:recap",
                    "evidence:sentinel:worldbuilding:alpha:note",
                ],
                "state": {
                    "memory_state": "graph_read_model",
                    "canon_state": "not_canon_promotion",
                    "approval_state": "not_approval_write",
                },
            },
            "sentinel:technical-beta": {
                "node_id": "sentinel:technical-beta",
                "label": "Technical Beta",
                "kind": "location",
                "role": "location",
                "aliases": ["Technical Beta"],
                "source_domains": ["worldbuilding"],
                "evidence_ref_ids": ["evidence:sentinel:worldbuilding:beta:note"],
                "state": {
                    "memory_state": "graph_read_model",
                    "canon_state": "not_canon_promotion",
                    "approval_state": "not_approval_write",
                },
            },
        },
        "edges": {
            "edge:sentinel:technical-alpha:participated_in:sentinel:technical-beta": {
                "edge_id": "edge:sentinel:technical-alpha:participated_in:sentinel:technical-beta",
                "source_node_id": "sentinel:technical-alpha",
                "target_node_id": "sentinel:technical-beta",
                "predicate": "participated_in",
                "label": "participated in",
                "direction": "outbound",
                "source_domains": ["recap"],
                "session_ids": [FOCUS_SESSION_ID],
                "evidence_ref_ids": ["evidence:sentinel:session-22:alpha:recap"],
                "state": {
                    "memory_state": "graph_read_model",
                    "canon_state": "not_canon_promotion",
                    "approval_state": "not_approval_write",
                },
            },
            "edge:sentinel:technical-alpha:connected_to:sentinel:technical-beta": {
                "edge_id": "edge:sentinel:technical-alpha:connected_to:sentinel:technical-beta",
                "source_node_id": "sentinel:technical-alpha",
                "target_node_id": "sentinel:technical-beta",
                "predicate": "connected_to",
                "label": "connected to",
                "direction": "outbound",
                "source_domains": ["worldbuilding"],
                "session_ids": [],
                "evidence_ref_ids": ["evidence:sentinel:worldbuilding:alpha:note"],
                "state": {
                    "memory_state": "graph_read_model",
                    "canon_state": "not_canon_promotion",
                    "approval_state": "not_approval_write",
                },
            },
        },
        "evidence": {
            "evidence:sentinel:session-22:alpha:recap": {
                "evidence_ref_id": "evidence:sentinel:session-22:alpha:recap",
                "source_artifact_id": "artifact:sentinel:recap:session-22",
                "source_domain": "recap",
                "evidence_role": "focus_session_recap_mention",
                "session_id": FOCUS_SESSION_ID,
                "source_span_ref_id": "spref:sentinel:session-22:p001",
                "can_open_source": True,
                "can_highlight_span": True,
            },
            "evidence:sentinel:worldbuilding:alpha:note": {
                "evidence_ref_id": "evidence:sentinel:worldbuilding:alpha:note",
                "source_artifact_id": "artifact:sentinel:worldbuilding:alpha",
                "source_domain": "worldbuilding",
                "evidence_role": "character_context",
                "locator": "sentinel/alpha.md#baseline",
                "can_open_source": True,
                "can_highlight_span": False,
            },
            "evidence:sentinel:worldbuilding:beta:note": {
                "evidence_ref_id": "evidence:sentinel:worldbuilding:beta:note",
                "source_artifact_id": "artifact:sentinel:worldbuilding:beta",
                "source_domain": "worldbuilding",
                "evidence_role": "location_context",
                "locator": "sentinel/beta.md#baseline",
                "can_open_source": True,
                "can_highlight_span": False,
            },
        },
        "source_artifacts": {
            "artifact:sentinel:recap:session-22": {
                "source_artifact_id": "artifact:sentinel:recap:session-22",
                "source_domain": "recap",
                "campaign_id": CAMPAIGN_ID,
                "session_id": FOCUS_SESSION_ID,
                "uri": "fixture://sentinel/recap/session-22.json",
            },
            "artifact:sentinel:worldbuilding:alpha": {
                "source_artifact_id": "artifact:sentinel:worldbuilding:alpha",
                "source_domain": "worldbuilding",
                "campaign_id": CAMPAIGN_ID,
                "uri": "fixture://sentinel/worldbuilding/alpha.md",
            },
            "artifact:sentinel:worldbuilding:beta": {
                "source_artifact_id": "artifact:sentinel:worldbuilding:beta",
                "source_domain": "worldbuilding",
                "campaign_id": CAMPAIGN_ID,
                "uri": "fixture://sentinel/worldbuilding/beta.md",
            },
        },
        "adjacency": {
            "sentinel:technical-alpha": [
                {
                    "edge_id": "edge:sentinel:technical-alpha:participated_in:sentinel:technical-beta",
                    "node_id": "sentinel:technical-beta",
                    "label": "participated in",
                    "direction": "outbound",
                    "anchored_to_focus_session": True,
                },
                {
                    "edge_id": "edge:sentinel:technical-alpha:connected_to:sentinel:technical-beta",
                    "node_id": "sentinel:technical-beta",
                    "label": "connected to",
                    "direction": "outbound",
                    "anchored_to_focus_session": False,
                },
            ],
            "sentinel:technical-beta": [
                {
                    "edge_id": "edge:sentinel:technical-alpha:participated_in:sentinel:technical-beta",
                    "node_id": "sentinel:technical-alpha",
                    "label": "participated in",
                    "direction": "inbound",
                    "anchored_to_focus_session": True,
                },
                {
                    "edge_id": "edge:sentinel:technical-alpha:connected_to:sentinel:technical-beta",
                    "node_id": "sentinel:technical-alpha",
                    "label": "connected to",
                    "direction": "inbound",
                    "anchored_to_focus_session": False,
                },
            ],
        },
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
        "identity_redirects": [],
    }
    validate_union_supergraph_fixture(payload)
    return UnionSupergraphStore.model_validate(payload)


def _load_validate(bundle_root: Path):
    bundle = load_contribution_bundle(bundle_root)
    report = validate_contribution_bundle(bundle)
    return bundle, report


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


@pytest.fixture
def validated_bundle(loaded_bundle):
    report = validate_contribution_bundle(loaded_bundle)
    assert report.ok is True
    return loaded_bundle, report


@pytest.fixture
def seeded_root(tmp_path: Path):
    store = _build_sentinel_union_store()
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:sentinel-baseline-seed"],
    )
    return tmp_path


def _merge_bundle_contributions(root: Path, bundle) -> str:
    _head, revision, _store = kernel.open_current_world_graph(root, WORLD_ID)
    parent = revision.revision_id
    for contribution in bundle.contributions:
        result = kernel.merge_contribution_to_revision(
            root,
            world_id=WORLD_ID,
            contribution=contribution,
            expected_parent_revision_id=parent,
        )
        assert result.published is True
        parent = result.revision_id
    return parent


def test_exact_bundle_digest(validated_bundle) -> None:
    _bundle, report = validated_bundle
    assert report.bundle_digest == BUNDLE_DIGEST
    assert report.bundle_id == BUNDLE_ID


def test_exactly_six_contributions(validated_bundle) -> None:
    bundle, report = validated_bundle
    assert report.contribution_count == 6
    assert len(bundle.contributions) == 6
    assert [item.contribution_id for item in bundle.contributions] == ORDERED_CONTRIBUTION_IDS


def test_each_manual_import_has_single_source_lineage(loaded_bundle) -> None:
    for contribution in loaded_bundle.contributions:
        if contribution.source_kind != "manual_import":
            continue
        artifact_ids = {
            assertion.source_artifact_id
            for assertion in contribution.accepted_assertions
        }
        revision_ids = {
            assertion.source_revision_id
            for assertion in contribution.accepted_assertions
        }
        assert artifact_ids == {contribution.source_artifact_id}
        assert revision_ids == {contribution.source_revision_id}


def test_zero_identity_decisions_rejected_unresolved(validated_bundle) -> None:
    _bundle, report = validated_bundle
    assert report.identity_decision_count == 0
    assert report.rejected_assertion_count == 0
    assert report.unresolved_mention_count == 0


def test_required_node_and_edge_counts(validated_bundle) -> None:
    _bundle, report = validated_bundle
    assert report.required_node_count == 12
    assert report.required_edge_count == 11


def test_expected_source_domains(validated_bundle) -> None:
    _bundle, report = validated_bundle
    assert set(report.source_domains) == EXPECTED_SOURCE_DOMAINS


def test_exact_required_node_ids(loaded_bundle) -> None:
    observed_nodes: set[str] = set()
    for contribution in loaded_bundle.contributions:
        for assertion in contribution.accepted_assertions:
            if assertion.assertion_kind == "node" and assertion.subject_node_id:
                observed_nodes.add(assertion.subject_node_id)
    assert observed_nodes == REQUIRED_NODE_IDS


def test_exact_required_edge_ids(loaded_bundle) -> None:
    observed_edges: set[str] = set()
    for contribution in loaded_bundle.contributions:
        for assertion in contribution.accepted_assertions:
            if assertion.assertion_kind != "edge":
                continue
            value = dict(assertion.value or {})
            edge_id = value.get("edge_id")
            if edge_id:
                observed_edges.add(str(edge_id))
    assert observed_edges == REQUIRED_EDGE_IDS


def test_mireward_shared_semantic_support(loaded_bundle) -> None:
    assertion_ids: set[str] = set()
    for contribution in loaded_bundle.contributions:
        if contribution.contribution_id not in MIREWARD_CONTRIBUTION_IDS:
            continue
        for assertion in contribution.accepted_assertions:
            if (
                assertion.assertion_kind == "node"
                and assertion.subject_node_id == "location:mireward"
            ):
                assertion_ids.add(assertion.assertion_id)
    assert assertion_ids == {MIREWARD_ASSERTION_ID}


def test_questionable_company_shared_semantic_support(loaded_bundle) -> None:
    assertion_ids: set[str] = set()
    for contribution in loaded_bundle.contributions:
        if contribution.contribution_id not in QUESTIONABLE_COMPANY_CONTRIBUTION_IDS:
            continue
        for assertion in contribution.accepted_assertions:
            if (
                assertion.assertion_kind == "node"
                and assertion.subject_node_id == "party:questionable-company"
            ):
                assertion_ids.add(assertion.assertion_id)
    assert assertion_ids == {QUESTIONABLE_COMPANY_ASSERTION_ID}


def test_kernel_merge_identity_safe_baseline(
    seeded_root: Path,
    loaded_bundle,
) -> None:
    root = seeded_root
    _merge_bundle_contributions(root, loaded_bundle)
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)

    assert "loc_mirathorn" not in store.nodes
    assert "pc_caelynn" not in store.nodes
    assert "event_session_23_mireward_gate" not in store.nodes

    mirathorn_nodes = [
        node_id for node_id in store.nodes if node_id == "location:mirathorn"
    ]
    caelynn_nodes = [node_id for node_id in store.nodes if node_id == "pc:caelynn"]
    gate_nodes = [
        node_id
        for node_id in store.nodes
        if node_id == "event:longmont-c2:session-23:mireward-gate-battle"
    ]
    assert len(mirathorn_nodes) == 1
    assert len(caelynn_nodes) == 1
    assert len(gate_nodes) == 1

    assert SENTINEL_NODE_IDS.issubset(store.nodes)
    bundle_owned_nodes = set(store.nodes) - SENTINEL_NODE_IDS
    assert bundle_owned_nodes == REQUIRED_NODE_IDS


def test_kernel_merge_mireward_support_record(seeded_root: Path, loaded_bundle) -> None:
    root = seeded_root
    _merge_bundle_contributions(root, loaded_bundle)
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)

    supports = [
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == "location:mireward"
    ]
    assert len(supports) == 1
    support = supports[0]
    assert support["assertion_id"] == MIREWARD_ASSERTION_ID
    assert set(support["active_contribution_ids"]) == MIREWARD_CONTRIBUTION_IDS
    assert set(store.nodes["location:mireward"].source_domains) == {
        "worldbuilding",
        "recap",
    }


def test_kernel_merge_questionable_company_support_record(
    seeded_root: Path,
    loaded_bundle,
) -> None:
    root = seeded_root
    _merge_bundle_contributions(root, loaded_bundle)
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)

    supports = [
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == "party:questionable-company"
    ]
    assert len(supports) == 1
    support = supports[0]
    assert support["assertion_id"] == QUESTIONABLE_COMPANY_ASSERTION_ID
    assert set(support["active_contribution_ids"]) == QUESTIONABLE_COMPANY_CONTRIBUTION_IDS
    assert set(store.nodes["party:questionable-company"].source_domains) == {
        "manual_seed",
        "recap",
    }


def test_support_records_retain_source_artifacts_and_evidence(
    seeded_root: Path,
    loaded_bundle,
) -> None:
    root = seeded_root
    _merge_bundle_contributions(root, loaded_bundle)
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)

    mireward_support = next(
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == "location:mireward"
    )
    assert mireward_support["evidence_ref_ids"]
    assert mireward_support["source_artifact_ids"]

    qc_support = next(
        support
        for support in store.assertion_support.values()
        if support["graph_object_id"] == "party:questionable-company"
    )
    assert qc_support["evidence_ref_ids"]
    assert qc_support["source_artifact_ids"]


def test_session_22_and_23_temporal_separation(loaded_bundle) -> None:
    session_scopes: dict[str, set[str | None]] = {
        "event:longmont-c2:session-22:mireward-road": set(),
        "event:longmont-c2:session-23:mireward-gate-battle": set(),
    }
    for contribution in loaded_bundle.contributions:
        for assertion in contribution.accepted_assertions:
            node_id = assertion.subject_node_id
            if node_id in session_scopes:
                temporal = assertion.temporal_scope or {}
                session_scopes[node_id].add(temporal.get("session_id"))

    assert session_scopes["event:longmont-c2:session-22:mireward-road"] == {
        "session-22"
    }
    assert session_scopes["event:longmont-c2:session-23:mireward-gate-battle"] == {
        "session-23"
    }


def test_tripod_attribute_assertions_on_final_contribution(loaded_bundle) -> None:
    tripod = loaded_bundle.contributions[-1]
    predicates = {
        assertion.predicate
        for assertion in tripod.accepted_assertions
        if assertion.assertion_kind == "attribute"
    }
    assert predicates == TRIPOD_ATTRIBUTE_PREDICATES


def test_rebuild_from_contributions_equivalent_to_head(
    seeded_root: Path,
    loaded_bundle,
) -> None:
    root = seeded_root
    _merge_bundle_contributions(root, loaded_bundle)
    result = kernel.rebuild_from_contributions(root, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in result.diagnostics


def test_deterministic_reload_ids_and_digest() -> None:
    first = load_contribution_bundle(BUNDLE_PATH)
    second = load_contribution_bundle(BUNDLE_PATH)
    assert first.manifest.bundle_digest == second.manifest.bundle_digest == BUNDLE_DIGEST

    first_contrib_ids = [item.contribution_id for item in first.contributions]
    second_contrib_ids = [item.contribution_id for item in second.contributions]
    assert first_contrib_ids == second_contrib_ids

    first_assertion_ids = sorted(
        {
            assertion.assertion_id
            for contribution in first.contributions
            for assertion in contribution.accepted_assertions
        }
    )
    second_assertion_ids = sorted(
        {
            assertion.assertion_id
            for contribution in second.contributions
            for assertion in contribution.accepted_assertions
        }
    )
    assert first_assertion_ids == second_assertion_ids


def test_corpus_and_graph_data_provenance_uris(loaded_bundle) -> None:
    authored_ids = {
        "contribution:33d7cdb0ff623f28",
        "contribution:022187fdefdf4557",
    }
    corpus_uris: list[str] = []
    graph_data_uris: list[str] = []
    for contribution in loaded_bundle.contributions:
        for assertion in contribution.accepted_assertions:
            artifacts = (assertion.value or {}).get("source_artifacts") or []
            for artifact in artifacts:
                uri = str(artifact.get("uri") or "")
                if not uri:
                    continue
                domains = set((assertion.value or {}).get("source_domains") or [])
                if domains & {"worldbuilding", "recap"}:
                    corpus_uris.append(uri)
                if contribution.contribution_id in authored_ids:
                    graph_data_uris.append(uri)

    assert corpus_uris
    assert graph_data_uris
    assert all(uri.startswith("repo://corpus/") for uri in corpus_uris)
    assert all(uri.startswith("graph-data://") for uri in graph_data_uris)


def test_tamper_label_without_assertion_id_fails_validation(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/002-mireward-world-hub.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["label"] = "Mireward Renamed"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("stale assertion_id" in error for error in report.validation_errors)


def test_tamper_evidence_ref_removed_fails_validation(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/004-session-22-mireward-road.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["evidence_ref_ids"] = []
    payload["accepted_assertions"][0]["value"]["evidence"] = []
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("missing evidence" in error for error in report.validation_errors)


def test_tamper_checksum_stale_fails_load(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/005-session-23-mireward-gate-battle.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["label"] = "Mireward Tampered"
    _write_json(bundle_root / rel_path, payload)

    with pytest.raises(ValueError, match="sha256 mismatch"):
        load_contribution_bundle(bundle_root)


def test_tamper_manifest_reorder_fails_validation(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    entries = manifest["ordered_contributions"]
    entries[1], entries[2] = entries[2], entries[1]
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("wrong contribution order" in error for error in report.validation_errors)


def test_tamper_mireward_campaign_scope_in_one_contribution_fails(
    tmp_path: Path,
) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/004-session-22-mireward-road.json"
    payload = _read_json(bundle_root / rel_path)
    for assertion in payload["accepted_assertions"]:
        if assertion.get("subject_node_id") == "location:mireward":
            assertion["campaign_scope"] = "other-campaign"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "stale assertion_id" in error or "invalid campaign_scope" in error
        for error in report.validation_errors
    )


def test_tamper_mireward_temporal_scope_in_one_contribution_fails(
    tmp_path: Path,
) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/005-session-23-mireward-gate-battle.json"
    payload = _read_json(bundle_root / rel_path)
    for assertion in payload["accepted_assertions"]:
        if assertion.get("subject_node_id") == "location:mireward":
            assertion["temporal_scope"] = {"session_id": "session-99"}
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("stale assertion_id" in error for error in report.validation_errors)


def test_tamper_extra_node_outside_locked_scope_fails_validation(
    tmp_path: Path,
) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/003-questionable-company-roster.json"
    payload = _read_json(bundle_root / rel_path)
    template = payload["accepted_assertions"][0]
    extra = json.loads(json.dumps(template))
    extra["subject_node_id"] = "npc:bundle-extra"
    extra["label"] = "Bundle Extra"
    extra["assertion_id"] = "assertion:0000000000000001"
    payload["accepted_assertions"].append(extra)
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "extra nodes outside locked scope" in error
        for error in report.validation_errors
    )
