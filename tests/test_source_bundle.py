from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from src.live_play.source_bundle import build_ingestion_source_bundle


ROOT = Path(__file__).resolve().parents[1]


def test_source_bundle_maps_ingested_library_without_corpus_bodies() -> None:
    bundle = build_ingestion_source_bundle(root=ROOT, campaign_id="longmont-c2")

    assert bundle.schema_version == "dmb_ingestion_source_bundle_v1"
    assert bundle.artifacts
    assert bundle.anchors
    assert bundle.units
    assert "corpus_bodies_not_embedded" in bundle.diagnostics
    assert bundle.coverage["ingestRoutesOnDisk"] >= bundle.coverage["ingestRoutesInDogfoodFullManifest"]

    normalized = [
        unit
        for unit in bundle.units
        if unit.unitKind == "recap_document"
        and unit.sourceAnchor.locator.value.endswith(".md")
        and "_normalized/" in unit.sourceAnchor.locator.value
    ]
    assert normalized
    assert any(unit.authorityState == "played_truth" for unit in normalized)

    for unit in bundle.units:
        dumped = unit.model_dump(mode="json")
        assert "body" not in dumped
        assert "text" not in dumped
        assert not unit.sourceAnchor.locator.value.startswith("/")


def test_source_bundle_includes_manifest_reference_units() -> None:
    bundle = build_ingestion_source_bundle(root=ROOT, campaign_id="longmont-c2")

    manifest_units = [unit for unit in bundle.units if unit.unitKind == "diagnostic_record"]
    labels = {unit.label for unit in manifest_units}
    assert "C2S23 slim planning manifest" in labels
    assert "C2S23 dogfood-full manifest" in labels


def test_live_source_bundle_endpoint_returns_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/api/live/source-bundle?campaign_id=longmont-c2")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_ingestion_source_bundle_v1"
    assert body["coverage"]["unitCount"] == len(body["units"])
    assert "read_only_adapter" in body["diagnostics"]
