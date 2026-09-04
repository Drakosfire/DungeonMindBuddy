"""Unit/adversarial witnesses for DFC-1 product continuity inventory."""

from __future__ import annotations

import json
from pathlib import Path

from product_continuity.inventory import (
    CurrentAuthoritySnapshot,
    reconcile,
    run_inventory,
    scan_historical_root,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_w2_same_id_conflict_is_scan_order_independent(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    doc_id = "11111111-1111-4111-8111-111111111111"
    for root, title, body in (
        (root_a, "Alpha", "# alpha\n"),
        (root_b, "Beta", "# beta\n"),
    ):
        target = root / "out/workspace/plan" / f"{doc_id}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        _write_json(
            root / "out/registries/workspace_documents.json",
            {
                "schema_version": "dmb_workspace_document_registry_v1",
                "records": [
                    {
                        "schema_version": "dmb_workspace_document_record_v1",
                        "document_id": doc_id,
                        "title": title,
                        "campaign_id": "longmont-c2",
                        "kind": "plan",
                        "target_relpath": f"out/workspace/plan/{doc_id}.md",
                        "status": "active",
                        "content_status": "committed",
                        "revision": 1,
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ],
            },
        )

    current = CurrentAuthoritySnapshot(readable=True, detail=None, schema_head_status="at_head")
    ab = reconcile(
        scan_historical_root(root_a, root_label="a")
        + scan_historical_root(root_b, root_label="b"),
        current,
    )
    ba = reconcile(
        scan_historical_root(root_b, root_label="b")
        + scan_historical_root(root_a, root_label="a"),
        current,
    )
    item_ab = next(i for i in ab if i.identity == doc_id)
    item_ba = next(i for i in ba if i.identity == doc_id)
    assert item_ab.classification == "CONFLICT"
    assert item_ba.classification == "CONFLICT"
    assert [o.root_label for o in item_ab.historical_observations] == [
        o.root_label for o in item_ba.historical_observations
    ]


def test_w8_incomplete_manifest_needs_adapter_without_invented_ids(tmp_path: Path) -> None:
    root = tmp_path / "hist"
    manifest_dir = root / "out/graph_memory/runs/run-x"
    manifest_dir.mkdir(parents=True)
    _write_json(
        manifest_dir / "graph_ingest_run_manifest.json",
        {
            "schema": "dmb_graph_ingest_run_manifest_v0",
            "version": "0.1.0",
            "run_id": "graph-ingest:longmont-c2:session-1:fixture",
            "campaign_id": "longmont-c2",
            "session_id": "session-1",
            "status": "candidate_extraction_ready",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "source": {
                "source_domain": "recap",
                # missing source_artifact_id on purpose
            },
            "artifacts": {},
        },
    )
    pending = scan_historical_root(root, root_label="hist")
    current = CurrentAuthoritySnapshot(readable=True, detail=None, schema_head_status="at_head")
    items = reconcile(pending, current)
    item = next(i for i in items if i.domain == "ingest")
    assert item.classification == "NEEDS_ADAPTER"
    assert "invent" not in " ".join(item.reason).lower() or "no generated" in " ".join(
        item.reason
    ).lower()


def test_w10_malformed_artifact_remains_visible(tmp_path: Path) -> None:
    root = tmp_path / "hist"
    runs = root / "out/runtime/play/runs"
    runs.mkdir(parents=True)
    (runs / "bad.json").write_text("{not-json", encoding="utf-8")
    good_id = "22222222-2222-4222-8222-222222222222"
    _write_json(
        runs / f"{good_id}.json",
        {
            "schema_version": "dmb_play_run_record_v1",
            "run_id": good_id,
            "campaign_id": "longmont-c2",
            "playable_artifact_id": "33333333-3333-4333-8333-333333333333",
            "playable_revision": 1,
            "playable_content_sha256": "a" * 64,
            "run_revision": 1,
            "progress": {
                "current_scene_id": None,
                "current_beat_id": None,
                "resolved_beat_ids": [],
                "selections": {},
                "notes_by_element_id": {},
            },
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    )
    items = reconcile(
        scan_historical_root(root, root_label="hist"),
        CurrentAuthoritySnapshot(readable=True, detail=None, schema_head_status="at_head"),
    )
    classes = {i.classification for i in items}
    assert "MALFORMED" in classes
    assert any(i.identity == good_id for i in items)


def test_w12_output_deterministic_under_shuffled_roots(tmp_path: Path) -> None:
    roots = []
    for name in ("r1", "r2"):
        root = tmp_path / name
        doc_id = "44444444-4444-4444-8444-444444444444"
        target = root / "out/workspace/plan" / f"{doc_id}.md"
        target.parent.mkdir(parents=True)
        target.write_text("# same\n", encoding="utf-8")
        _write_json(
            root / "out/registries/workspace_documents.json",
            {
                "schema_version": "dmb_workspace_document_registry_v1",
                "records": [
                    {
                        "schema_version": "dmb_workspace_document_record_v1",
                        "document_id": doc_id,
                        "title": "Same",
                        "campaign_id": "longmont-c2",
                        "kind": "plan",
                        "target_relpath": f"out/workspace/plan/{doc_id}.md",
                        "status": "active",
                        "content_status": "committed",
                        "revision": 1,
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ],
            },
        )
        roots.append(root)

    current_root = tmp_path / "current"
    current_root.mkdir()
    # Force APP-STATE unavailable for this unit test.
    import os

    os.environ.pop("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", None)
    a = run_inventory(
        current_repo_root=current_root,
        historical_roots=[("r1", roots[0]), ("r2", roots[1])],
    )
    b = run_inventory(
        current_repo_root=current_root,
        historical_roots=[("r2", roots[1]), ("r1", roots[0])],
    )
    assert [i.identity for i in a.items] == [i.identity for i in b.items]
    assert [i.classification for i in a.items] == [i.classification for i in b.items]
    assert [i.domain for i in a.items] == [i.domain for i in b.items]


def test_comparison_unavailable_when_app_state_down(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    root = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "55555555-5555-4555-8555-555555555555"
    target = root / "out/workspace/plan" / f"{doc_id}.md"
    target.parent.mkdir(parents=True)
    target.write_text("# plan\n", encoding="utf-8")
    _write_json(
        root / "out/registries/workspace_documents.json",
        {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [
                {
                    "schema_version": "dmb_workspace_document_record_v1",
                    "document_id": doc_id,
                    "title": "Unavailable",
                    "campaign_id": "longmont-c2",
                    "kind": "plan",
                    "target_relpath": f"out/workspace/plan/{doc_id}.md",
                    "status": "active",
                    "content_status": "committed",
                    "revision": 1,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        },
    )
    report = run_inventory(
        current_repo_root=current,
        historical_roots=[("hist", root)],
    )
    item = next(i for i in report.items if i.identity == doc_id)
    assert item.classification == "COMPARISON_UNAVAILABLE"
    assert report.incomplete is True
