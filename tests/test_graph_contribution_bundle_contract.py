"""Contribution bundle load/validate contract tests (PR006C)."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from graph_memory.contribution_bundles import (
    load_contribution_bundle,
    validate_contribution_bundle,
)
from graph_memory.contribution_bundles.load import compute_bundle_digest
from graph_memory.kernel.contributions import compute_assertion_id

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)


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


def _load_validate(bundle_root: Path):
    bundle = load_contribution_bundle(bundle_root)
    report = validate_contribution_bundle(bundle)
    return bundle, report


def test_load_real_bundle_ok() -> None:
    bundle = load_contribution_bundle(BUNDLE_PATH)
    report = validate_contribution_bundle(bundle)
    assert report.ok is True
    assert report.validation_errors == []
    assert bundle.manifest.schema_ == "dmb_graph_contribution_bundle_v1"


def test_path_traversal_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    manifest["ordered_contributions"][0]["path"] = "../manifest.json"
    (bundle_root / "contributions/001-world-hubs.json").unlink()
    _write_manifest(bundle_root, manifest)
    with pytest.raises(ValueError, match="path escapes bundle root"):
        load_contribution_bundle(bundle_root)


def test_missing_file_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    missing = bundle_root / "contributions/001-world-hubs.json"
    missing.unlink()
    with pytest.raises(FileNotFoundError, match="contribution file missing"):
        load_contribution_bundle(bundle_root)


def test_unlisted_contribution_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    extra = bundle_root / "contributions/999-extra.json"
    extra.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unlisted contribution file"):
        load_contribution_bundle(bundle_root)


def test_checksum_mismatch_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    manifest["ordered_contributions"][0]["sha256"] = "0" * 64
    _write_manifest(bundle_root, manifest)
    with pytest.raises(ValueError, match="sha256 mismatch"):
        load_contribution_bundle(bundle_root)


def test_duplicate_path_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    manifest["ordered_contributions"][1]["path"] = manifest["ordered_contributions"][0][
        "path"
    ]
    (bundle_root / "contributions/002-questionable-company-roster.json").unlink()
    _write_manifest(bundle_root, manifest)
    with pytest.raises(ValueError, match="duplicate contribution path"):
        load_contribution_bundle(bundle_root)


def test_duplicate_contribution_id_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    manifest["ordered_contributions"][1]["contribution_id"] = manifest[
        "ordered_contributions"
    ][0]["contribution_id"]
    _write_manifest(bundle_root, manifest)
    with pytest.raises(ValueError, match="duplicate contribution_id"):
        load_contribution_bundle(bundle_root)


def test_wrong_world_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["world_id"] = "otherworld"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("world_id mismatch" in error for error in report.validation_errors)


def test_stale_assertion_id_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][1]["label"] = "Mireward Tampered"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("stale assertion_id" in error for error in report.validation_errors)


def test_stale_contribution_id_manifest_vs_file_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/002-questionable-company-roster.json"
    payload = _read_json(bundle_root / rel_path)
    payload["contribution_id"] = "contribution:deadbeefdeadbeef"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    with pytest.raises(ValueError, match="contribution_id mismatch"):
        load_contribution_bundle(bundle_root)


def test_stale_contribution_id_compute_mismatch(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/002-questionable-company-roster.json"
    payload = _read_json(bundle_root / rel_path)
    payload["source_revision_id"] = "tampered-revision"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("stale contribution_id" in error for error in report.validation_errors)


def test_assertion_contribution_ownership_mismatch(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/003-session-22-mireward-road.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["contribution_id"] = "contribution:ffffffffffffffff"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "assertion/contribution ownership mismatch" in error
        for error in report.validation_errors
    )


def test_unknown_source_domain_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["value"]["source_domains"] = ["bogus_domain"]
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("unknown source_domain" in error for error in report.validation_errors)


def test_missing_evidence_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    assertion = payload["accepted_assertions"][0]
    assertion["evidence_ref_ids"] = []
    assertion["value"]["evidence"] = []
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("missing evidence" in error for error in report.validation_errors)


def test_missing_source_artifact_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    assertion = payload["accepted_assertions"][0]
    assertion["source_artifact_id"] = None
    assertion["value"]["source_artifacts"] = []
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "missing source_artifact_id" in error or "missing embedded source_artifacts" in error
        for error in report.validation_errors
    )


def test_absent_epistemic_metadata_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["epistemic_kind"] = None
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "missing epistemic_kind" in error for error in report.validation_errors
    )


def test_absent_visibility_metadata_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["visibility"] = None
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("missing visibility" in error for error in report.validation_errors)


def test_invalid_campaign_scope_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/005-tripod-null-calf-threat-prep.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["campaign_scope"] = "wrong-campaign"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "invalid campaign_scope" in error for error in report.validation_errors
    )


def test_wrong_contribution_order_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    entries = manifest["ordered_contributions"]
    entries[2], entries[3] = entries[3], entries[2]
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any("wrong contribution order" in error for error in report.validation_errors)


def test_bundle_digest_mismatch_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    manifest["bundle_digest"] = "0" * 64
    _write_manifest(bundle_root, manifest, update_digest=False)
    with pytest.raises(ValueError, match="bundle_digest mismatch"):
        load_contribution_bundle(bundle_root)


def test_extra_node_outside_locked_scope_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    template = payload["accepted_assertions"][0]
    extra = json.loads(json.dumps(template))
    extra["subject_node_id"] = "location:contract-extra-node"
    extra["label"] = "Contract Extra Node"
    extra["assertion_id"] = compute_assertion_id(
        assertion_kind=extra["assertion_kind"],
        subject_node_id=extra["subject_node_id"],
        target_node_id=extra["target_node_id"],
        predicate=extra["predicate"],
        label=extra["label"],
        value=extra["value"],
        campaign_scope=extra["campaign_scope"],
        temporal_scope=extra["temporal_scope"],
        epistemic_kind=extra["epistemic_kind"],
        visibility=extra["visibility"],
    )
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


def test_dangling_top_level_evidence_ref_ids_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["evidence_ref_ids"] = ["evidence:does-not-exist"]
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "evidence_ref_ids do not match embedded evidence" in error
        for error in report.validation_errors
    )


def test_evidence_nonexistent_embedded_artifact_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    assertion = payload["accepted_assertions"][0]
    assertion["value"]["evidence"][0]["source_artifact_id"] = (
        "artifact:does-not-exist"
    )
    assertion["assertion_id"] = compute_assertion_id(
        assertion_kind=assertion["assertion_kind"],
        subject_node_id=assertion["subject_node_id"],
        target_node_id=assertion["target_node_id"],
        predicate=assertion["predicate"],
        label=assertion["label"],
        value=assertion["value"],
        campaign_scope=assertion["campaign_scope"],
        temporal_scope=assertion["temporal_scope"],
        epistemic_kind=assertion["epistemic_kind"],
        visibility=assertion["visibility"],
    )
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "points to nonexistent embedded source artifact" in error
        for error in report.validation_errors
    )


def test_duplicate_assertion_id_within_contribution_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/002-questionable-company-roster.json"
    payload = _read_json(bundle_root / rel_path)
    duplicate = json.loads(json.dumps(payload["accepted_assertions"][0]))
    payload["accepted_assertions"].append(duplicate)
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "duplicate assertion_id" in error for error in report.validation_errors
    )


def test_shared_support_missing_mireward_assertion_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/003-session-22-mireward-road.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"] = [
        assertion
        for assertion in payload["accepted_assertions"]
        if assertion.get("subject_node_id") != "location:mireward"
    ]
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "shared-support contributor" in error and "location:mireward" in error
        for error in report.validation_errors
    )


def test_shared_support_manifest_domain_mismatch_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    manifest["expected_shared_support"][0]["source_domains"] = ["worldbuilding"]
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "shared-support domains mismatch for location:mireward" in error
        for error in report.validation_errors
    )


def test_extra_known_source_domain_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    assertion = payload["accepted_assertions"][0]
    assertion["value"]["source_domains"] = [
        "worldbuilding",
        "npc_note",
    ]
    assertion["assertion_id"] = compute_assertion_id(
        assertion_kind=assertion["assertion_kind"],
        subject_node_id=assertion["subject_node_id"],
        target_node_id=assertion["target_node_id"],
        predicate=assertion["predicate"],
        label=assertion["label"],
        value=assertion["value"],
        campaign_scope=assertion["campaign_scope"],
        temporal_scope=assertion["temporal_scope"],
        epistemic_kind=assertion["epistemic_kind"],
        visibility=assertion["visibility"],
    )
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "source domains must exactly match expected_source_domains" in error
        for error in report.validation_errors
    )


def test_empty_bundle_digest_load_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    manifest = _load_manifest(bundle_root)
    manifest["bundle_digest"] = ""
    _write_manifest(bundle_root, manifest, update_digest=False)

    with pytest.raises(ValueError, match="bundle_digest is required"):
        load_contribution_bundle(bundle_root)


def test_accepted_assertion_with_candidate_state_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["acceptance_state"] = "candidate"
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "acceptance_state='accepted'" in error for error in report.validation_errors
    )


def test_unknown_identity_resolution_outcome_rejection(tmp_path: Path) -> None:
    bundle_root = _copy_bundle(tmp_path)
    rel_path = "contributions/001-world-hubs.json"
    payload = _read_json(bundle_root / rel_path)
    payload["accepted_assertions"][0]["identity_resolution_outcome"] = (
        "not_a_real_outcome"
    )
    _write_json(bundle_root / rel_path, payload)
    manifest = _load_manifest(bundle_root)
    _sync_entry_sha(manifest, bundle_root, rel_path)
    _write_manifest(bundle_root, manifest)

    _, report = _load_validate(bundle_root)
    assert report.ok is False
    assert any(
        "unknown identity_resolution_outcome" in error
        for error in report.validation_errors
    )
