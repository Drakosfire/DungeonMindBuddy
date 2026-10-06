from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.services import (
    graph_run_registry,
    session28_retained_package_registration as registration,
    source_artifact_registry,
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
    artifact = type("Artifact", (), {
        "source_artifact_id": registration.SOURCE_ARTIFACT_ID,
        "source_domain": "recap",
        "campaign_id": registration.CAMPAIGN_ID,
        "session_id": registration.SESSION_ID,
        "content_sha256": registration.PINNED_SOURCE_SHA256,
        "world_id": None,
        "uri": "repo://out/registries/source_content/recap/synthetic.md",
    })()
    created: dict[str, object] = {}
    review_calls: list[str] = []

    monkeypatch.setattr(source_artifact_registry, "get_source_artifact", lambda *_args: artifact)
    monkeypatch.setattr(registration, "ingest_run_registry_roots", lambda root: [root / "out/graph_memory/runs"])
    monkeypatch.setattr(registration, "is_under_ingest_runs", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(registration, "is_under_world_store", lambda *_args, **_kwargs: False)

    def missing_run(*_args, **_kwargs):
        raise graph_run_registry.GraphRunRegistryError("missing", status_code=404)

    def create_run(_root, **kwargs):
        created.update(kwargs)
        return type("Run", (), {"run_id": kwargs["run_id"], "created_at": "2026-10-06T12:00:00Z"})()

    monkeypatch.setattr(graph_run_registry, "get_extraction_run", missing_run)
    monkeypatch.setattr(graph_run_registry, "create_extraction_run", create_run)

    def exact_review(run_id: str):
        review_calls.append(run_id)
        return type("Review", (), {
            "run_id": run_id,
            "derived_from_run_id": None,
            "campaign_id": registration.CAMPAIGN_ID,
            "session_id": registration.SESSION_ID,
            "source_artifact_id": registration.SOURCE_ARTIFACT_ID,
            "source_revision_id": f"sha256:{registration.PINNED_SOURCE_SHA256}",
            "world_id": None,
            "inspection_status": "invalid_evidence",
            "invalid_evidence_count": registration.EXPECTED_INVALID_EVIDENCE_COUNT,
            "promotable": False,
            "first_world_publish_eligible": False,
            "assertions": [{} for _ in range(registration.EXPECTED_ASSERTION_COUNT)],
        })()

    monkeypatch.setattr(
        "apps.live_control_server.services.extract_promote.get_exact_run_review_package",
        exact_review,
    )

    result = registration.register_retained_package(
        package_root=package,
        inventory_path=inventory,
        repo_root=repo,
        expected_preview_fingerprint=preview.preview_fingerprint,
        expected_inventory_sha256=registration.PINNED_INVENTORY_SHA256,
    )

    assert result["mode"] == "applied"
    assert result["canonical_import_run_id"] == preview.run_id
    assert result["created_at"] == "2026-10-06T12:00:00Z"
    assert created["run_id"] == preview.run_id
    assert created["lineage"]["derivation"] == registration.IMPORT_DERIVATION
    assert created["lineage"]["historical_review_run_id"] == registration.HISTORICAL_REVIEW_RUN_ID
    assert review_calls == [preview.run_id]
    assert result["exact_review"]["assertion_count"] == registration.EXPECTED_ASSERTION_COUNT
    assert result["exact_review"]["inspection_status"] == "invalid_evidence"

    components = created["components"]
    assert components["source_artifact"].sha256 == preview.source_sha256
    assert components["candidate_graph"].sha256 == preview.candidate_sha256
    assert components["source_span_index"].sha256 == preview.span_index_sha256
    assert components["source_span_index"].uri.startswith("repo://out/graph_memory/runs/")
    lineage = created["lineage"]
    assert lineage["import_fingerprint"] == preview.preview_fingerprint
    assert lineage["package_inventory_sha256"] == preview.inventory_sha256
    assert lineage["legacy_graph_ingest_run_id"] == registration.LEGACY_GRAPH_INGEST_RUN_ID
    assert lineage["package_file_sha256"] == preview.as_preview()["package_files"]

    staged_package = (
        repo
        / "out/graph_memory/runs/retained_package_imports"
        / preview.run_id
        / "package"
    )
    staged_files = {
        item.relative_to(staged_package).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in staged_package.rglob("*")
        if item.is_file()
    }
    assert len(staged_files) == len(preview.files)
    assert staged_files == {item.path: item.sha256 for item in preview.files}
