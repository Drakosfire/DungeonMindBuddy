"""PostgreSQL owning-boundary witnesses for DFC-1 inventory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from application_state.content.service import commit_plan, create_plan, exact_committed_revision
from application_state.content.types import sha256_utf8
from application_state.ingest.service import create_extraction_run
from graph_memory.ingestion.extraction_run import ExtractionRun, ExtractionRunStatus
from product_continuity.inventory import run_inventory


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_w1_unavailable_app_state_never_false_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:59999/missing",
    )
    root = tmp_path / "hist"
    doc_id = "66666666-6666-4666-8666-666666666666"
    target = root / "out/workspace/plan" / f"{doc_id}.md"
    target.parent.mkdir(parents=True)
    target.write_text("# hist\n", encoding="utf-8")
    _write_json(
        root / "out/registries/workspace_documents.json",
        {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [
                {
                    "schema_version": "dmb_workspace_document_record_v1",
                    "document_id": doc_id,
                    "title": "Hist",
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
    current = tmp_path / "current"
    current.mkdir()
    report = run_inventory(
        current_repo_root=current, historical_roots=[("hist", root)]
    )
    item = next(i for i in report.items if i.identity == doc_id)
    assert item.classification == "COMPARISON_UNAVAILABLE"
    assert item.classification != "RECOVERABLE_EXACT"
    assert report.incomplete is True


def test_w3_w4_plan_history_and_recoverable(
    application_state_dsn: str, tmp_path: Path
) -> None:
    created = create_plan(title="Continuity Plan", campaign_id="longmont-c2")
    doc_id = str(created.work_object_id)
    rev1_md = "# revision one\n"
    _, rev1 = commit_plan(doc_id, rev1_md)
    rev2_md = "# revision two\n"
    commit_plan(doc_id, rev2_md, expected_revision=created.object_revision + 1)
    # Prove historical rev1 retained.
    exact_committed_revision(doc_id, 1, kind="plan", expected_sha256=sha256_utf8(rev1_md))

    hist = tmp_path / "hist"
    target = hist / "out/workspace/plan" / f"{doc_id}.md"
    target.parent.mkdir(parents=True)
    target.write_text(rev1_md, encoding="utf-8")
    _write_json(
        hist / "out/registries/workspace_documents.json",
        {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [
                {
                    "schema_version": "dmb_workspace_document_record_v1",
                    "document_id": doc_id,
                    "title": "Continuity Plan",
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

    absent_id = "77777777-7777-4777-8777-777777777777"
    absent_target = hist / "out/workspace/plan" / f"{absent_id}.md"
    absent_target.write_text("# only historical\n", encoding="utf-8")
    # append absent plan into same registry
    registry = json.loads((hist / "out/registries/workspace_documents.json").read_text())
    registry["records"].append(
        {
            "schema_version": "dmb_workspace_document_record_v1",
            "document_id": absent_id,
            "title": "Absent",
            "campaign_id": "longmont-c2",
            "kind": "plan",
            "target_relpath": f"out/workspace/plan/{absent_id}.md",
            "status": "active",
            "content_status": "committed",
            "revision": 1,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
    )
    _write_json(hist / "out/registries/workspace_documents.json", registry)

    current = tmp_path / "current"
    current.mkdir()
    before_plans = len(
        __import__("application_state.content.service", fromlist=["list_plans"]).list_plans(
            status=None
        )
    )
    report = run_inventory(
        current_repo_root=current, historical_roots=[("hist", hist)]
    )
    after_plans = len(
        __import__("application_state.content.service", fromlist=["list_plans"]).list_plans(
            status=None
        )
    )
    assert before_plans == after_plans  # W11 no mutation

    contains = next(i for i in report.items if i.identity == doc_id)
    assert contains.classification == "CURRENT_CONTAINS_HISTORY"
    recoverable = next(i for i in report.items if i.identity == absent_id)
    assert recoverable.classification == "RECOVERABLE_EXACT"
    assert rev1.revision_n == 1


def test_w6_w9_w11_ingest_and_play_inventory(
    application_state_dsn: str, tmp_path: Path
) -> None:
    present = ExtractionRun.model_validate(
        {
            "run_id": "er_present_exact",
            "source_artifact_id": "sa_present",
            "source_domain": "worldbuilding",
            "status": ExtractionRunStatus.DRAFT,
            "revision": 1,
            "campaign_id": "eldyrwild",
            "session_id": None,
            "created_at": "2026-09-02T18:00:00Z",
            "updated_at": "2026-09-02T18:00:00Z",
        }
    )
    create_extraction_run(present)
    absent_payload = {
        "schema_version": "dmb_extraction_run_v1",
        "version": "1.0",
        "run_id": "er_absent_exact",
        "source_artifact_id": "sa_absent",
        "source_domain": "worldbuilding",
        "status": "draft",
        "revision": 1,
        "campaign_id": "eldyrwild",
        "session_id": None,
        "components": {},
        "lineage": {},
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }

    hist = tmp_path / "hist"
    _write_json(
        hist / "out/registries/extraction_runs.json",
        {
            "schema_version": "dmb_extraction_run_registry_v1",
            "records": [
                present.model_dump(mode="json"),
                absent_payload,
            ],
        },
    )
    play_id = "88888888-8888-4888-8888-888888888888"
    _write_json(
        hist / "out/runtime/play/runs" / f"{play_id}.json",
        {
            "schema_version": "dmb_play_run_record_v1",
            "run_id": play_id,
            "campaign_id": "longmont-c2",
            "playable_artifact_id": "99999999-9999-4999-8999-999999999999",
            "playable_revision": 1,
            "playable_content_sha256": "b" * 64,
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

    from application_state.ingest.service import list_extraction_runs
    from application_state.play.service import list_play_run_aggregates

    before_ingest = len(list_extraction_runs())
    before_play = len(list_play_run_aggregates())
    current = tmp_path / "current"
    current.mkdir()
    report = run_inventory(
        current_repo_root=current, historical_roots=[("hist", hist)]
    )
    assert len(list_extraction_runs()) == before_ingest
    assert len(list_play_run_aggregates()) == before_play

    present_item = next(i for i in report.items if i.identity == "er_present_exact")
    absent_item = next(i for i in report.items if i.identity == "er_absent_exact")
    play_item = next(i for i in report.items if i.identity == play_id)
    assert present_item.classification == "CURRENT_EXACT"
    assert absent_item.classification == "RECOVERABLE_EXACT"
    assert play_item.classification == "NEEDS_ADAPTER"
