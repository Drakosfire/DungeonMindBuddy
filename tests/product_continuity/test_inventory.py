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


def test_w2_content_status_disagreement_is_conflict_scan_order_independent(
    tmp_path: Path,
) -> None:
    """Same ID/revision/digest but committed vs draft must CONFLICT (§3.5)."""
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    doc_id = "13131313-1313-4131-8131-131313131313"
    body = "# same bytes\n"
    for root, status in ((root_a, "committed"), (root_b, "draft")):
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
                        "title": "Status Split",
                        "campaign_id": "longmont-c2",
                        "kind": "plan",
                        "target_relpath": f"out/workspace/plan/{doc_id}.md",
                        "status": "active",
                        "content_status": status,
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
    assert any("content_status" in reason for reason in item_ab.reason)
    assert [o.root_label for o in item_ab.historical_observations] == [
        o.root_label for o in item_ba.historical_observations
    ]


def test_equivalent_same_content_status_still_collapses(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    doc_id = "14141414-1414-4141-8141-141414141414"
    body = "# identical committed\n"
    for root in (root_a, root_b):
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
                        "title": "Same Status",
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
    items = reconcile(
        scan_historical_root(root_a, root_label="a")
        + scan_historical_root(root_b, root_label="b"),
        CurrentAuthoritySnapshot(readable=True, detail=None, schema_head_status="at_head"),
    )
    item = next(i for i in items if i.identity == doc_id)
    assert item.classification == "RECOVERABLE_EXACT"
    assert item.classification != "CONFLICT"
    registry_obs = [
        o for o in item.historical_observations if o.source_kind == "workspace_documents_registry"
    ]
    assert len(registry_obs) == 2
    assert {o.content_status for o in registry_obs} == {"committed"}


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


def test_orphan_bytes_alone_are_needs_adapter_not_recoverable(tmp_path: Path) -> None:
    root = tmp_path / "hist"
    doc_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    target = root / "out/workspace/plan" / f"{doc_id}.md"
    target.parent.mkdir(parents=True)
    target.write_text("# orphan only\n", encoding="utf-8")
    items = reconcile(
        scan_historical_root(root, root_label="hist"),
        CurrentAuthoritySnapshot(readable=True, detail=None, schema_head_status="at_head"),
    )
    item = next(i for i in items if i.identity == doc_id)
    assert item.classification == "NEEDS_ADAPTER"
    assert item.classification != "RECOVERABLE_EXACT"


def test_committed_registry_without_bytes_is_needs_adapter(tmp_path: Path) -> None:
    root = tmp_path / "hist"
    doc_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    _write_json(
        root / "out/registries/workspace_documents.json",
        {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [
                {
                    "schema_version": "dmb_workspace_document_record_v1",
                    "document_id": doc_id,
                    "title": "Missing Bytes",
                    "campaign_id": "longmont-c2",
                    "kind": "plan",
                    "target_relpath": f"out/workspace/plan/{doc_id}.md",
                    "status": "active",
                    "content_status": "committed",
                    "revision": 3,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        },
    )
    items = reconcile(
        scan_historical_root(root, root_label="hist"),
        CurrentAuthoritySnapshot(readable=True, detail=None, schema_head_status="at_head"),
    )
    item = next(i for i in items if i.identity == doc_id)
    assert item.classification == "NEEDS_ADAPTER"


def test_w5_build_historical_vs_current_registry(tmp_path: Path) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    body = "# worldbuilding source\n"
    target = hist / "out/workspace/worldbuilding" / f"{doc_id}.md"
    target.parent.mkdir(parents=True)
    target.write_text(body, encoding="utf-8")
    _write_json(
        hist / "out/registries/workspace_documents.json",
        {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [
                {
                    "schema_version": "dmb_workspace_document_record_v1",
                    "document_id": doc_id,
                    "title": "Historical Build",
                    "campaign_id": "longmont-c2",
                    "kind": "worldbuilding_source",
                    "target_relpath": f"out/workspace/worldbuilding/{doc_id}.md",
                    "status": "active",
                    "content_status": "committed",
                    "revision": 1,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        },
    )
    import os

    os.environ.pop("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", None)
    report = run_inventory(
        current_repo_root=current, historical_roots=[("hist", hist)]
    )
    item = next(i for i in report.items if i.identity == doc_id)
    assert item.domain == "build"
    assert item.classification == "RECOVERABLE_EXACT"


def test_current_build_registry_unreadable_is_comparison_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    target = hist / "out/workspace/worldbuilding" / f"{doc_id}.md"
    target.parent.mkdir(parents=True)
    target.write_text("# build\n", encoding="utf-8")
    _write_json(
        hist / "out/registries/workspace_documents.json",
        {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [
                {
                    "schema_version": "dmb_workspace_document_record_v1",
                    "document_id": doc_id,
                    "title": "Build",
                    "campaign_id": "longmont-c2",
                    "kind": "worldbuilding_source",
                    "target_relpath": f"out/workspace/worldbuilding/{doc_id}.md",
                    "status": "active",
                    "content_status": "committed",
                    "revision": 1,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        },
    )
    bad = current / "out/registries/workspace_documents.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not-valid-registry", encoding="utf-8")
    report = run_inventory(
        current_repo_root=current, historical_roots=[("hist", hist)]
    )
    item = next(i for i in report.items if i.identity == doc_id)
    assert item.classification == "COMPARISON_UNAVAILABLE"
    assert item.classification != "RECOVERABLE_EXACT"
    assert report.incomplete is True


def test_current_exact_requires_content_match_when_digest_available(tmp_path: Path) -> None:
    """Identity alone must not become CURRENT_EXACT when historical digest disagrees."""
    from application_state.content.types import sha256_utf8

    build_id = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    hist_body = "# historical orphan\n"
    hist_digest = sha256_utf8(hist_body)
    build_root = tmp_path / "build_hist"
    build_target = build_root / "out/workspace/worldbuilding" / f"{build_id}.md"
    build_target.parent.mkdir(parents=True)
    build_target.write_text(hist_body, encoding="utf-8")
    items = reconcile(
        scan_historical_root(build_root, root_label="hist"),
        CurrentAuthoritySnapshot(
            readable=True,
            detail=None,
            schema_head_status="at_head",
            builds={
                build_id: {
                    "revision": 1,
                    "campaign_id": "longmont-c2",
                    "title": "Present Build",
                    "content_sha256": "a" * 64,
                    "target_relpath": f"out/workspace/worldbuilding/{build_id}.md",
                }
            },
        ),
    )
    item = next(i for i in items if i.identity == build_id)
    assert item.classification == "CONFLICT"
    assert hist_digest != "a" * 64


def test_w7_manifest_era_adapts_without_synthesized_identity(tmp_path: Path) -> None:
    root = tmp_path / "hist"
    manifest_dir = root / "out/graph_memory/runs/run-ok"
    manifest_dir.mkdir(parents=True)
    run_id = "graph-ingest:longmont-c2:session-99:fixture-ok"
    _write_json(
        manifest_dir / "graph_ingest_run_manifest.json",
        {
            "schema": "dmb_graph_ingest_run_manifest_v0",
            "version": "0.1",
            "run_id": run_id,
            "campaign_id": "longmont-c2",
            "session_id": "session-99",
            "status": "candidate_extraction_ready",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "source": {
                "source_domain": "recap",
                "source_artifact_id": "artifact:recap:longmont-c2:session-99:fixture",
                "normalized_recap_path": "out/graph_memory/runs/run-ok/normalized_recap_source.md",
                "normalized_recap_sha256": "sha256:" + ("c" * 64),
            },
            "artifacts": {
                "candidate_graph": {
                    "kind": "candidate_graph",
                    "uri": "out/graph_memory/runs/run-ok/candidate_graph.json",
                    "sha256": "sha256:" + ("d" * 64),
                    "exists": True,
                }
            },
        },
    )
    items = reconcile(
        scan_historical_root(root, root_label="hist"),
        CurrentAuthoritySnapshot(readable=True, detail=None, schema_head_status="at_head"),
    )
    item = next(i for i in items if i.domain == "ingest")
    assert item.identity == run_id
    assert item.classification == "RECOVERABLE_EXACT"
    assert any(o.parse_status == "adapted" for o in item.historical_observations)
    assert "invent" not in " ".join(item.reason).lower()


def test_app_state_integrity_error_is_comparison_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    from application_state.errors import ApplicationStateIntegrityError
    import product_continuity.inventory as inv

    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonbuddy_application_state",
    )
    monkeypatch.setattr(
        inv,
        "list_plans",
        lambda status=None: (_ for _ in ()).throw(
            ApplicationStateIntegrityError("corrupt plan row")
        ),
    )
    root = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "12121212-1212-4121-8121-121212121212"
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
                    "title": "Integrity",
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
        current_repo_root=current, historical_roots=[("hist", root)]
    )
    item = next(i for i in report.items if i.identity == doc_id)
    assert item.classification == "COMPARISON_UNAVAILABLE"
    assert report.incomplete is True
    assert report.authority.schema_head_status == "integrity_error"
