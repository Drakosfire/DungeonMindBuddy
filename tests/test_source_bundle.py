from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from live_play.source_bundle import build_ingestion_source_bundle


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


def test_live_source_bundle_endpoint_returns_contract(monkeypatch) -> None:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    client = TestClient(create_app(), client=("127.0.0.1", 50000))

    response = client.get("/api/live/source-bundle?campaign_id=longmont-c2")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_ingestion_source_bundle_v1"
    assert body["coverage"]["unitCount"] == len(body["units"])
    assert "read_only_adapter" in body["diagnostics"]


def test_source_session_index_matches_bundle(monkeypatch) -> None:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    client = TestClient(create_app(), client=("127.0.0.1", 50000))
    for campaign_id in ("longmont-c1", "longmont-c2", "unknown"):
        params = {"campaign_id": campaign_id}
        bundle = client.get("/api/live/source-bundle", params=params)
        sessions = client.get("/api/live/source-bundle/sessions", params=params)
        assert bundle.status_code == sessions.status_code == 200
        assert sessions.json() == sorted({
            unit["fields"]["sessionNumber"] for unit in bundle.json()["units"]
            if unit["fields"].get("sessionNumber") is not None
        }, reverse=True)


def test_bundle_preserves_full_library_projection_without_auxiliary_scans(monkeypatch) -> None:
    from live_play import ingested_corpus_library as library_module
    from live_play import source_bundle as bundle_module

    monkeypatch.setattr(library_module, "_utc_now_z", lambda: "2026-11-19T00:00:00Z")
    full_library = library_module.build_library(root=ROOT)
    with monkeypatch.context() as baseline:
        baseline.setattr(bundle_module, "build_library", lambda **_: full_library)
        expected = bundle_module.build_ingestion_source_bundle(root=ROOT).model_dump(mode="json")

    def forbidden(*args, **kwargs):
        raise AssertionError("bundle construction must not scan an unused auxiliary view")

    for name in ("_scan_elderwyld", "_scan_live_workspaces", "_scan_eval_ingest_artifacts"):
        monkeypatch.setattr(library_module, name, forbidden)
    actual = bundle_module.build_ingestion_source_bundle(root=ROOT).model_dump(mode="json")
    assert actual == expected
    assert actual["artifacts"]


def test_bundle_still_observes_source_and_manifest_changes(tmp_path) -> None:
    import json

    from live_play.ingested_corpus_library import C2S23_MANIFEST

    recaps = tmp_path / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized"
    recaps.mkdir(parents=True)
    first = recaps / "Session 1 - Recap.md"
    first.write_text("first", encoding="utf-8")

    def recaps_by_session():
        bundle = build_ingestion_source_bundle(root=tmp_path, campaign_id="longmont-c2")
        return {a.sessionNumber: a for a in bundle.artifacts if a.kind != "reference_index"}

    initial = recaps_by_session()
    assert set(initial) == {1}
    assert initial[1].metadata["sizeBytes"] == 5
    assert initial[1].metadata["activatedInC2S23Slim"] is False
    first.write_text("a longer recap", encoding="utf-8")
    second = recaps / "Session 2 - Recap.md"
    second.write_text("second", encoding="utf-8")
    manifest = tmp_path / C2S23_MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"entries": [{"route": first.relative_to(tmp_path).as_posix()}]}))
    updated = recaps_by_session()
    assert set(updated) == {1, 2}
    assert updated[1].metadata["sizeBytes"] == len("a longer recap")
    assert updated[1].metadata["activatedInC2S23Slim"] is True
    first.unlink()
    manifest.unlink()
    final = recaps_by_session()
    assert set(final) == {2}
    assert final[2].metadata["activatedInC2S23Slim"] is False
    assert all(a.kind != "reference_index" for a in build_ingestion_source_bundle(root=tmp_path).artifacts)
