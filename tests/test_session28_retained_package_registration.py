from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.services import (
    session28_retained_package_registration as registration,
)


def _write_json(path: Path, payload: object) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _synthetic_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    package = tmp_path / "retained"
    package.mkdir()
    source = b"A synthetic retained recap.\n"
    source_sha = hashlib.sha256(source).hexdigest()
    (package / "normalized_recap_source.md").write_bytes(source)
    hashes = {
        "normalized_recap_source.md": source_sha,
        "candidate_graph.json": _write_json(package / "candidate_graph.json", {"synthetic": True}),
        "source_span_index.json": _write_json(package / "source_span_index.json", {"synthetic": True}),
        "candidate_validation_report.json": _write_json(package / "candidate_validation_report.json", {}),
        "known_entity_mentions.json": _write_json(package / "known_entity_mentions.json", {}),
        "provenance_index.json": _write_json(package / "provenance_index.json", {}),
        "source_spans/1.txt": hashlib.sha256(b"span\n").hexdigest(),
    }
    (package / "source_spans").mkdir()
    (package / "source_spans/1.txt").write_bytes(b"span\n")
    manifest_prefix = registration.EXPECTED_MANIFEST_PREFIX
    artifact_specs = {
        "candidate_graph": ("candidate_graph.json", hashes["candidate_graph.json"]),
        "candidate_validation_report": (
            "candidate_validation_report.json",
            hashes["candidate_validation_report.json"],
        ),
        "known_entity_mentions": ("known_entity_mentions.json", hashes["known_entity_mentions.json"]),
        "normalized_recap": ("normalized_recap_source.md", source_sha),
        "provenance_index": ("provenance_index.json", hashes["provenance_index.json"]),
        "source_span_bundle": ("source_spans", None),
        "source_span_index": ("source_span_index.json", hashes["source_span_index.json"]),
    }
    manifest = {
        "schema": "dmb_graph_ingest_run_manifest_v0",
        "run_id": registration.LEGACY_GRAPH_INGEST_RUN_ID,
        "campaign_id": registration.CAMPAIGN_ID,
        "session_id": registration.SESSION_ID,
        "diagnostics": {"extraction_run_id": registration.HISTORICAL_REVIEW_RUN_ID},
        "source": {
            "source_artifact_id": registration.SOURCE_ARTIFACT_ID,
            "source_domain": "recap",
            "normalized_recap_sha256": f"sha256:{source_sha}",
            "normalized_recap_path": f"{manifest_prefix}normalized_recap_source.md",
            "source_span_index_uri": f"{manifest_prefix}source_span_index.json",
            "provenance_index_uri": f"{manifest_prefix}provenance_index.json",
            "source_span_bundle_uri": f"{manifest_prefix}source_spans",
            "input_path_record": "synthetic/input.md",
        },
        "artifacts": {
            kind: {
                "uri": f"{manifest_prefix}{relative}",
                "exists": True,
                **({"sha256": f"sha256:{digest}"} if digest else {}),
            }
            for kind, (relative, digest) in artifact_specs.items()
        },
    }
    review = {
        "schema": "dmb_extract_promote_exact_run_review_v1",
        "runId": registration.HISTORICAL_REVIEW_RUN_ID,
        "derivedFromRunId": None,
        "sourceArtifactId": registration.SOURCE_ARTIFACT_ID,
        "sourceRevisionId": f"sha256:{source_sha}",
        "campaignId": registration.CAMPAIGN_ID,
        "sessionId": registration.SESSION_ID,
        "worldId": None,
        "inspectionStatus": "invalid_evidence",
        "invalidEvidenceCount": 1,
        "promotable": False,
        "firstWorldPublishEligible": False,
        "assertions": [{} for _ in range(registration.EXPECTED_ASSERTION_COUNT)],
    }
    manifest_sha = _write_json(package / "graph_ingest_run_manifest.json", manifest)
    review_sha = _write_json(package / "exact_run_review_package.json", review)
    hashes["graph_ingest_run_manifest.json"] = manifest_sha
    hashes["exact_run_review_package.json"] = review_sha
    pins = tuple(registration.PackageFilePin(path=path, sha256=digest) for path, digest in hashes.items())
    inventory_sha = registration.canonical_inventory_sha256(pins)
    monkeypatch.setattr(registration, "PINNED_INVENTORY_SHA256", inventory_sha)
    monkeypatch.setattr(registration, "PINNED_MANIFEST_SHA256", manifest_sha)
    monkeypatch.setattr(registration, "PINNED_REVIEW_SNAPSHOT_SHA256", review_sha)
    monkeypatch.setattr(registration, "PINNED_SOURCE_SHA256", source_sha)
    monkeypatch.setattr(registration, "PINNED_CANDIDATE_SHA256", hashes["candidate_graph.json"])
    monkeypatch.setattr(registration, "PINNED_SPAN_INDEX_SHA256", hashes["source_span_index.json"])
    monkeypatch.setattr(registration, "PINNED_VALIDATION_REPORT_SHA256", hashes["candidate_validation_report.json"])
    monkeypatch.setattr(registration, "PINNED_KNOWN_ENTITY_MENTIONS_SHA256", hashes["known_entity_mentions.json"])
    monkeypatch.setattr(registration, "PINNED_PROVENANCE_INDEX_SHA256", hashes["provenance_index.json"])
    monkeypatch.setattr(registration, "_URI_TO_PACKAGE_PATH", {
        f"{manifest_prefix}normalized_recap_source.md": "normalized_recap_source.md",
        f"{manifest_prefix}candidate_graph.json": "candidate_graph.json",
        f"{manifest_prefix}candidate_validation_report.json": "candidate_validation_report.json",
        f"{manifest_prefix}known_entity_mentions.json": "known_entity_mentions.json",
        f"{manifest_prefix}provenance_index.json": "provenance_index.json",
        f"{manifest_prefix}source_span_index.json": "source_span_index.json",
        f"{manifest_prefix}source_spans": "source_spans",
    })
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({
        "package_root": str(package),
        "files": [
            {"path": pin.path, "sha256": pin.sha256, "size": (package / pin.path).stat().st_size}
            for pin in pins
        ],
    }))
    return package, inventory


def test_preview_verifies_complete_package_and_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, inventory = _synthetic_package(tmp_path, monkeypatch)
    first = registration.preview_retained_package(
        package_root=package,
        inventory_path=inventory,
        expected_inventory_sha256=registration.PINNED_INVENTORY_SHA256,
    )
    second = registration.preview_retained_package(
        package_root=package,
        inventory_path=inventory,
        expected_inventory_sha256=registration.PINNED_INVENTORY_SHA256,
    )

    assert first.run_id == second.run_id
    assert first.preview_fingerprint == second.preview_fingerprint
    assert first.run_id != registration.HISTORICAL_REVIEW_RUN_ID
    assert first.as_preview()["mode"] == "preview"


def test_preview_rejects_mutated_or_unlisted_package_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, inventory = _synthetic_package(tmp_path, monkeypatch)
    (package / "normalized_recap_source.md").write_text("changed\n")
    with pytest.raises(registration.RetainedPackageRegistrationError, match="mismatch"):
        registration.preview_retained_package(
            package_root=package,
            inventory_path=inventory,
            expected_inventory_sha256=registration.PINNED_INVENTORY_SHA256,
        )


def test_apply_requires_current_preview_fingerprint_before_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, inventory = _synthetic_package(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(registration.RetainedPackageRegistrationError, match="fingerprint"):
        registration.register_retained_package(
            package_root=package,
            inventory_path=inventory,
            repo_root=repo,
            expected_preview_fingerprint="0" * 64,
            expected_inventory_sha256=registration.PINNED_INVENTORY_SHA256,
        )
    assert not (repo / "out").exists()


def test_apply_stages_and_registers_through_server_facades_with_stubbed_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package, inventory = _synthetic_package(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    preview = registration.preview_retained_package(
        package_root=package,
        inventory_path=inventory,
        expected_inventory_sha256=registration.PINNED_INVENTORY_SHA256,
    )
    with pytest.raises(
        registration.RetainedPackageRegistrationError,
        match="no verified native World binding",
    ):
        registration.register_retained_package(
            package_root=package,
            inventory_path=inventory,
            repo_root=repo,
            expected_preview_fingerprint=preview.preview_fingerprint,
            expected_inventory_sha256=registration.PINNED_INVENTORY_SHA256,
        )

    assert not (repo / "out").exists()
