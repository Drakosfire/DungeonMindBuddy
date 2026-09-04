"""Selection, preview, and CLI witnesses for DFC-2a Plan adoption."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_continuity.plan_adoption import (
    PlanAdoptionInputError,
    classify_selected_plans,
    historical_root_digest,
    normalize_document_ids,
    preview_plan_adoption,
    run_plan_adoption,
)
from product_continuity.inventory import run_inventory


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _plan_record(
    document_id: str,
    *,
    title: str = "Hist Plan",
    campaign_id: str = "longmont-c2",
    target_session: int | None = 27,
    revision: int = 1,
    content_status: str = "committed",
    relpath: str | None = None,
) -> dict[str, object]:
    if relpath is None:
        relpath = f"out/workspace/plan/{document_id}.md"
    return {
        "schema_version": "dmb_workspace_document_record_v1",
        "document_id": document_id,
        "title": title,
        "campaign_id": campaign_id,
        "target_session": target_session,
        "kind": "plan",
        "target_relpath": relpath,
        "status": "active",
        "content_status": content_status,
        "revision": revision,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _write_plan_root(
    root: Path,
    *,
    document_id: str,
    body: str = "# hist\n",
    title: str = "Hist Plan",
    with_registry: bool = True,
    with_bytes: bool = True,
    kind: str = "plan",
) -> str:
    relpath = f"out/workspace/plan/{document_id}.md"
    if with_bytes:
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    if with_registry:
        record = _plan_record(document_id, title=title, relpath=relpath)
        record["kind"] = kind
        if kind != "plan":
            record["kind"] = kind
            if kind == "worldbuilding_source":
                record["target_relpath"] = f"out/workspace/worldbuilding/{document_id}.md"
        _write_json(
            root / "out/registries/workspace_documents.json",
            {
                "schema_version": "dmb_workspace_document_registry_v1",
                "records": [record],
            },
        )
    return relpath


def test_normalize_rejects_non_uuid_and_duplicates() -> None:
    with pytest.raises(PlanAdoptionInputError, match="not an exact UUID"):
        normalize_document_ids(["C2 Session 27 Prep"])
    with pytest.raises(PlanAdoptionInputError, match="duplicate"):
        normalize_document_ids(
            [
                "11111111-1111-4111-8111-111111111111",
                "11111111-1111-4111-8111-111111111111",
            ]
        )
    assert normalize_document_ids(
        ["11111111-1111-4111-8111-111111111111"]
    ) == ["11111111-1111-4111-8111-111111111111"]


def test_cli_has_no_heuristic_selectors() -> None:
    import importlib.util
    from io import StringIO
    from contextlib import redirect_stderr, redirect_stdout

    script = Path(__file__).resolve().parents[2] / "scripts" / "adopt_historical_plans.py"
    spec = importlib.util.spec_from_file_location("adopt_historical_plans_cli", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(SystemExit):
        module._parse_args([])
    args = module._parse_args(
        [
            "--historical-root",
            "/tmp/hist",
            "--document-id",
            "11111111-1111-4111-8111-111111111111",
        ]
    )
    assert args.apply is False
    buf = StringIO()
    with pytest.raises(SystemExit), redirect_stdout(buf), redirect_stderr(buf):
        module._parse_args(["--help"])
    text = buf.getvalue()
    flags: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            for token in stripped.replace(",", " ").split():
                if token.startswith("--"):
                    flags.append(token)
    assert "--document-id" in flags
    assert "--apply" in flags
    assert "--all" not in flags
    assert "--force" not in flags
    assert "--latest" not in flags


def test_w1_preview_is_read_only_and_exact_id_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:59999/missing",
    )
    hist = tmp_path / "hist"
    doc_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    _write_plan_root(hist, document_id=doc_id, body="# preview only\n")
    current = tmp_path / "current"
    current.mkdir()
    before = historical_root_digest(hist)
    report = preview_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    after = historical_root_digest(hist)
    assert report.mode == "preview"
    assert report.applied is False
    assert report.importer_imported == 0
    assert before == after
    assert report.historical_root_unchanged is True
    # Unavailable APP-STATE is unsafe, so preview must block rather than imply recoverability.
    assert report.blocked is True
    assert report.dispositions[0].action == "block"


def test_missing_selected_id_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:59999/missing",
    )
    hist = tmp_path / "hist"
    present = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    missing = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    _write_plan_root(hist, document_id=present)
    current = tmp_path / "current"
    current.mkdir()
    report = preview_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[present, missing],
    )
    by_id = {row.document_id: row for row in report.dispositions}
    assert report.blocked is True
    assert by_id[missing].action == "block"
    assert "absent from the historical ledger" in by_id[missing].reason[0]


def test_non_plan_selected_id_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:59999/missing",
    )
    hist = tmp_path / "hist"
    build_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    target = hist / f"out/workspace/worldbuilding/{build_id}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# build\n", encoding="utf-8")
    _write_json(
        hist / "out/registries/workspace_documents.json",
        {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [
                {
                    "schema_version": "dmb_workspace_document_record_v1",
                    "document_id": build_id,
                    "title": "Build",
                    "campaign_id": "longmont-c2",
                    "kind": "worldbuilding_source",
                    "target_relpath": f"out/workspace/worldbuilding/{build_id}.md",
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
    inventory = run_inventory(
        current_repo_root=current, historical_roots=[("hist", hist)]
    )
    dispositions = classify_selected_plans(
        inventory, [build_id], historical_root=hist
    )
    assert dispositions[0].action == "block"
    assert dispositions[0].domain == "build"


def test_w6_preview_does_not_mutate_historical_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL",
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:59999/missing",
    )
    hist = tmp_path / "hist"
    doc_id = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    _write_plan_root(hist, document_id=doc_id)
    current = tmp_path / "current"
    current.mkdir()
    before = historical_root_digest(hist)
    run_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
        apply=False,
    )
    assert historical_root_digest(hist) == before


def test_missing_historical_root_is_input_error(tmp_path: Path) -> None:
    current = tmp_path / "current"
    current.mkdir()
    with pytest.raises(PlanAdoptionInputError, match="missing/unreadable"):
        preview_plan_adoption(
            current_repo_root=current,
            historical_root=tmp_path / "nope",
            document_ids=["ffffffff-ffff-4fff-8fff-ffffffffffff"],
        )
