"""PostgreSQL owning-boundary witnesses for DFC-2a Plan adoption."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from application_state.content.import_plans import import_plans_from_registry
from application_state.content.service import commit_plan, create_plan, list_plans, snapshot_plan
from application_state.content.types import sha256_utf8
from application_state.errors import ApplicationStateUnavailableError
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    get_workspace_document_snapshot,
    list_workspace_documents,
)
from product_continuity import plan_adoption as plan_adoption_mod
from product_continuity.plan_adoption import (
    ESCAPING_TARGET_REASON,
    MISSING_TARGET_BYTES_REASON,
    apply_plan_adoption,
    historical_root_digest,
    preview_plan_adoption,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _historical_plan(
    root: Path,
    *,
    document_id: str,
    body: str,
    title: str = "Recoverable Plan",
    campaign_id: str = "longmont-c2",
    target_session: int | None = 27,
    revision: int = 3,
    content_status: str = "committed",
    status: str = "active",
    relpath: str | None = None,
    write_bytes: bool = True,
) -> WorkspaceDocumentRecord:
    if relpath is None:
        relpath = f"out/workspace/plan/{document_id}.md"
    if write_bytes:
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    record = {
        "schema_version": "dmb_workspace_document_record_v1",
        "document_id": document_id,
        "title": title,
        "campaign_id": campaign_id,
        "target_session": target_session,
        "kind": "plan",
        "target_relpath": relpath,
        "status": status,
        "content_status": content_status,
        "revision": revision,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    registry_path = root / "out/registries/workspace_documents.json"
    if registry_path.is_file():
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        payload["records"] = [
            existing
            for existing in payload["records"]
            if existing["document_id"] != document_id
        ]
        payload["records"].append(record)
    else:
        payload = {
            "schema_version": "dmb_workspace_document_registry_v1",
            "records": [record],
        }
    _write_json(registry_path, payload)
    return WorkspaceDocumentRecord.model_validate(record)


def test_w1_preview_does_not_change_plan_count(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "11111111-1111-4111-8111-111111111111"
    _historical_plan(hist, document_id=doc_id, body="# preview\n")
    before = len(list_plans())
    report = preview_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.applied is False
    assert report.blocked is False
    assert report.dispositions[0].action == "adopt"
    assert report.dispositions[0].classification == "RECOVERABLE_EXACT"
    assert len(list_plans()) == before == 0


def test_w2_w7_recoverable_exact_preserves_identity_and_product_seam(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "22222222-2222-4222-8222-222222222222"
    body = "# recovered exactly\n"
    record = _historical_plan(
        hist,
        document_id=doc_id,
        body=body,
        title="C2 Session 27 Prep",
        target_session=27,
        revision=4,
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is False
    assert report.applied is True
    assert report.importer_imported == 1
    assert report.product_verification == "passed"
    listed = list_workspace_documents(current, kind="plan")
    assert [row.document_id for row in listed] == [doc_id]
    snapshot = get_workspace_document_snapshot(current, doc_id)
    assert snapshot.record.document_id == doc_id
    assert snapshot.record.revision == 4
    assert snapshot.record.campaign_id == "longmont-c2"
    assert snapshot.record.title == "C2 Session 27 Prep"
    assert snapshot.record.target_session == 27
    assert snapshot.record.status == "active"
    assert snapshot.markdown == body
    assert snapshot.content_sha256 == sha256_utf8(body)
    assert snapshot.record.revision == record.revision


def test_w3_replay_is_idempotent_noop(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "33333333-3333-4333-8333-333333333333"
    _historical_plan(hist, document_id=doc_id, body="# once\n", revision=2)
    first = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert first.importer_imported == 1
    objects_after_first = list_plans()
    second = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert second.blocked is False
    assert second.applied is True
    assert second.dispositions[0].action == "noop"
    assert second.dispositions[0].classification == "CURRENT_EXACT"
    assert second.importer_imported == 0
    assert len(list_plans()) == len(objects_after_first) == 1
    assert list_plans()[0].object_revision == objects_after_first[0].object_revision


def test_w4_one_unsafe_id_blocks_entire_set(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    recoverable = "44444444-4444-4444-8444-444444444444"
    orphan = "55555555-5555-4555-8555-555555555555"
    _historical_plan(hist, document_id=recoverable, body="# keep me out\n")
    orphan_path = hist / f"out/workspace/plan/{orphan}.md"
    orphan_path.write_text("# orphan only\n", encoding="utf-8")
    before = historical_root_digest(hist)
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[recoverable, orphan],
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert list_plans() == []
    assert historical_root_digest(hist) == before
    by_id = {row.document_id: row for row in report.dispositions}
    assert by_id[recoverable].classification == "RECOVERABLE_EXACT"
    assert by_id[orphan].action == "block"
    assert by_id[orphan].classification == "NEEDS_ADAPTER"


def test_w4_missing_id_blocks_recoverable_sibling(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    recoverable = "66666666-6666-4666-8666-666666666666"
    missing = "77777777-7777-4777-8777-777777777777"
    _historical_plan(hist, document_id=recoverable, body="# sibling\n")
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[recoverable, missing],
    )
    assert report.blocked is True
    assert report.applied is False
    assert list_plans() == []


def test_w5_toc_tou_conflict_blocks_entire_set(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    first_id = "88888888-8888-4888-8888-888888888888"
    second_id = "99999999-9999-4999-8999-999999999999"
    _historical_plan(hist, document_id=first_id, body="# first\n", title="First")
    _historical_plan(hist, document_id=second_id, body="# second\n", title="Second")
    preview = preview_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[first_id, second_id],
    )
    assert preview.blocked is False
    assert {row.action for row in preview.dispositions} == {"adopt"}

    conflict_root = tmp_path / "conflict-source"
    conflict_record = _historical_plan(
        conflict_root,
        document_id=first_id,
        body="# different current bytes\n",
        title="First",
        revision=3,
    )
    import_plans_from_registry(conflict_root, [conflict_record])
    assert len(list_plans()) == 1

    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[first_id, second_id],
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    remaining = list_plans()
    assert len(remaining) == 1
    assert str(remaining[0].work_object_id) == first_id
    listed_second = [
        row for row in list_workspace_documents(current, kind="plan") if row.document_id == second_id
    ]
    assert listed_second == []
    snapshot = get_workspace_document_snapshot(current, first_id)
    assert snapshot.markdown == "# different current bytes\n"


def test_w6_apply_does_not_mutate_historical_root(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "12121212-1212-4121-8121-121212121212"
    _historical_plan(hist, document_id=doc_id, body="# untouched root\n")
    before = historical_root_digest(hist)
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.applied is True
    assert report.historical_root_unchanged is True
    assert historical_root_digest(hist) == before


def test_mixed_already_current_and_recoverable_imports_safe_subset(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    existing_id = "13131313-1313-4131-8131-131313131313"
    new_id = "14141414-1414-4141-8141-141414141414"
    existing = _historical_plan(hist, document_id=existing_id, body="# already\n")
    _historical_plan(hist, document_id=new_id, body="# new\n", title="New Plan")
    import_plans_from_registry(hist, [existing])
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[existing_id, new_id],
    )
    assert report.blocked is False
    assert report.applied is True
    by_id = {row.document_id: row for row in report.dispositions}
    assert by_id[existing_id].action == "noop"
    assert by_id[new_id].action == "adopt"
    assert report.importer_imported == 1
    listed_ids = {row.document_id for row in list_workspace_documents(current, kind="plan")}
    assert listed_ids == {existing_id, new_id}


def test_current_contains_history_is_noop_not_overwrite(
    application_state_dsn: str, tmp_path: Path
) -> None:
    created = create_plan(title="Continuity Plan", campaign_id="longmont-c2")
    doc_id = str(created.work_object_id)
    rev1 = "# revision one\n"
    commit_plan(doc_id, rev1)
    commit_plan(doc_id, "# revision two\n", expected_revision=created.object_revision + 1)
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _historical_plan(
        hist,
        document_id=doc_id,
        body=rev1,
        title="Continuity Plan",
        revision=1,
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is False
    assert report.dispositions[0].classification == "CURRENT_CONTAINS_HISTORY"
    assert report.dispositions[0].action == "noop"
    assert report.importer_imported == 0
    snapshot = get_workspace_document_snapshot(current, doc_id)
    assert snapshot.markdown == "# revision two\n"


def test_discarded_plan_verifies_on_discarded_list_not_default_active(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "15151515-1515-4151-8151-151515151515"
    _historical_plan(
        hist,
        document_id=doc_id,
        body="# discarded probe\n",
        title="probe",
        status="discarded",
        content_status="draft",
        revision=2,
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is False
    assert report.applied is True
    assert report.product_verification == "passed"
    active = list_workspace_documents(current, kind="plan")
    assert [row.document_id for row in active] == []
    discarded = list_workspace_documents(current, kind="plan", status="discarded")
    assert [row.document_id for row in discarded] == [doc_id]
    snapshot = get_workspace_document_snapshot(current, doc_id)
    assert snapshot.record.status == "discarded"
    assert snapshot.record.document_id == doc_id


def test_missing_target_bytes_blocks_recoverable_sibling(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    recoverable = "16161616-1616-4161-8161-161616161616"
    empty = "17171717-1717-4171-8171-171717171717"
    _historical_plan(hist, document_id=recoverable, body="# keep out\n")
    _historical_plan(
        hist,
        document_id=empty,
        body="",
        title="Draft without bytes",
        content_status="draft",
        write_bytes=False,
    )
    before = historical_root_digest(hist)
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[recoverable, empty],
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert report.importer_skipped_empty == 0
    assert list_plans() == []
    assert historical_root_digest(hist) == before
    by_id = {row.document_id: row for row in report.dispositions}
    assert by_id[recoverable].classification == "RECOVERABLE_EXACT"
    assert by_id[recoverable].action == "adopt"
    assert by_id[empty].classification == "RECOVERABLE_EXACT"
    assert by_id[empty].action == "block"
    assert MISSING_TARGET_BYTES_REASON in by_id[empty].reason


def test_empty_target_file_blocks(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "18181818-1818-4181-8181-181818181818"
    _historical_plan(
        hist,
        document_id=doc_id,
        body="",
        content_status="draft",
        write_bytes=True,
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is True
    assert report.applied is False
    assert list_plans() == []
    assert report.dispositions[0].classification == "RECOVERABLE_EXACT"
    assert report.dispositions[0].action == "block"


def test_absolute_target_relpath_blocks_entire_set(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    recoverable = "19191919-1919-4191-8191-191919191919"
    escaped = "20202020-2020-4202-8202-202020202020"
    _historical_plan(hist, document_id=recoverable, body="# stay\n")
    outside = tmp_path / "outside.md"
    outside.write_text("# escaped bytes\n", encoding="utf-8")
    _historical_plan(
        hist,
        document_id=escaped,
        body="# unused\n",
        relpath=str(outside),
        write_bytes=False,
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[recoverable, escaped],
    )
    assert report.blocked is True
    assert report.applied is False
    assert list_plans() == []
    by_id = {row.document_id: row for row in report.dispositions}
    assert by_id[escaped].action == "block"
    assert ESCAPING_TARGET_REASON in by_id[escaped].reason[0]


def test_parent_escape_target_relpath_blocks_entire_set(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    recoverable = "21212121-2121-4121-8121-212121212121"
    escaped = "22222222-2222-4222-8222-222222222222"
    _historical_plan(hist, document_id=recoverable, body="# stay\n")
    outside = tmp_path / "outside.md"
    outside.write_text("# parent escape\n", encoding="utf-8")
    _historical_plan(
        hist,
        document_id=escaped,
        body="# unused\n",
        relpath="../outside.md",
        write_bytes=False,
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[recoverable, escaped],
    )
    assert report.blocked is True
    assert report.applied is False
    assert list_plans() == []
    by_id = {row.document_id: row for row in report.dispositions}
    assert by_id[escaped].action == "block"
    assert ESCAPING_TARGET_REASON in by_id[escaped].reason[0]


def test_w5_historical_bytes_change_after_preflight_blocks_zero_writes(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "23232323-2323-4232-8232-232323232323"
    original = "# classified bytes A\n"
    _historical_plan(hist, document_id=doc_id, body=original)
    original_revalidate = plan_adoption_mod._revalidate_pinned_evidence

    def mutate_then_revalidate(historical_root: Path, pins: list[object]):
        target = historical_root / "out/workspace/plan" / f"{doc_id}.md"
        target.write_text("# mutated bytes B\n", encoding="utf-8")
        return original_revalidate(historical_root, pins)

    monkeypatch.setattr(
        plan_adoption_mod, "_revalidate_pinned_evidence", mutate_then_revalidate
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert list_plans() == []
    listed = list_workspace_documents(current, kind="plan")
    assert listed == []


def test_w5_historical_bytes_deleted_after_preflight_blocks_zero_writes(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "24242424-2424-4242-8242-242424242424"
    _historical_plan(hist, document_id=doc_id, body="# classified bytes A\n")
    original_revalidate = plan_adoption_mod._revalidate_pinned_evidence

    def delete_then_revalidate(historical_root: Path, pins: list[object]):
        target = historical_root / "out/workspace/plan" / f"{doc_id}.md"
        target.unlink()
        return original_revalidate(historical_root, pins)

    monkeypatch.setattr(
        plan_adoption_mod, "_revalidate_pinned_evidence", delete_then_revalidate
    )
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is True
    assert report.applied is False
    assert list_plans() == []


def test_importer_consumes_pinned_snapshot_not_live_root(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "25252525-2525-4252-8252-252525252525"
    original = "# classified bytes A\n"
    _historical_plan(hist, document_id=doc_id, body=original)
    captured: dict[str, str] = {}
    real_import = import_plans_from_registry

    def spy(root: Path, records: list[object]):
        relpath = getattr(records[0], "target_relpath")
        captured["root"] = str(Path(root).resolve())
        captured["hist"] = str(hist.resolve())
        captured["bytes"] = (Path(root) / relpath).read_text(encoding="utf-8")
        live = hist / relpath
        live.write_text("# live bytes B after pin\n", encoding="utf-8")
        return real_import(root, records)

    monkeypatch.setattr(plan_adoption_mod, "import_plans_from_registry", spy)
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is False
    assert report.applied is True
    assert captured["root"] != captured["hist"]
    assert captured["bytes"] == original
    snapshot = get_workspace_document_snapshot(current, doc_id)
    assert snapshot.markdown == original
    assert snapshot.markdown != "# live bytes B after pin\n"


def test_w5_bytes_and_metadata_change_before_pin_blocks_zero_writes(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "26262626-2626-4262-8262-262626262626"
    original = "# classified bytes A\n"
    _historical_plan(hist, document_id=doc_id, body=original, title="Original Title")
    original_pin = plan_adoption_mod._pin_selected_adoptions

    def mutate_then_pin(historical_root: Path, dispositions: list[object], inventory: object):
        target = historical_root / "out/workspace/plan" / f"{doc_id}.md"
        target.write_text("# mutated bytes B\n", encoding="utf-8")
        registry = historical_root / "out/registries/workspace_documents.json"
        payload = json.loads(registry.read_text(encoding="utf-8"))
        for rec in payload["records"]:
            if rec["document_id"] == doc_id:
                rec["title"] = "Mutated Title"
                rec["revision"] = 99
        registry.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return original_pin(historical_root, dispositions, inventory)

    monkeypatch.setattr(plan_adoption_mod, "_pin_selected_adoptions", mutate_then_pin)
    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert list_plans() == []
    assert "does not match the classified" in (report.detail or "")


def test_current_exact_missing_historical_bytes_verifies_without_inventing_empty(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "27272727-2727-4272-8272-272727272727"
    body = "# already current non-empty\n"
    record = _historical_plan(
        hist,
        document_id=doc_id,
        body=body,
        title="Current Plan",
        revision=2,
    )
    first = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert first.blocked is False
    assert first.importer_imported == 1
    assert first.product_verification == "passed"
    (hist / record.target_relpath).unlink()
    second = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert second.blocked is False
    assert second.applied is True
    assert second.dispositions[0].classification == "CURRENT_EXACT"
    assert second.dispositions[0].action == "noop"
    assert second.importer_imported == 0
    assert second.product_verification == "passed"
    snapshot = get_workspace_document_snapshot(current, doc_id)
    assert snapshot.markdown == body
    assert snapshot.content_sha256 == sha256_utf8(body)
    assert snapshot.content_sha256 != sha256_utf8("")


def test_post_commit_product_seam_failure_keeps_committed_state(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    doc_id = "28282828-2828-4282-8282-282828282828"
    body = "# committed then seam failed\n"
    _historical_plan(hist, document_id=doc_id, body=body, title="Durable After Verify Fail")
    raise_on_seam = {"on": False}

    original_list = plan_adoption_mod.list_workspace_documents
    original_snapshot = plan_adoption_mod.get_workspace_document_snapshot
    original_import = plan_adoption_mod.import_plans_from_registry

    def exploding_list(*args, **kwargs):
        if raise_on_seam["on"]:
            raise ApplicationStateUnavailableError(
                "injected product-seam unavailability after commit"
            )
        return original_list(*args, **kwargs)

    def exploding_snapshot(*args, **kwargs):
        if raise_on_seam["on"]:
            raise ApplicationStateUnavailableError(
                "injected product-seam unavailability after commit"
            )
        return original_snapshot(*args, **kwargs)

    def import_then_arm(*args, **kwargs):
        result = original_import(*args, **kwargs)
        raise_on_seam["on"] = True
        return result

    monkeypatch.setattr(plan_adoption_mod, "list_workspace_documents", exploding_list)
    monkeypatch.setattr(
        plan_adoption_mod, "get_workspace_document_snapshot", exploding_snapshot
    )
    monkeypatch.setattr(plan_adoption_mod, "import_plans_from_registry", import_then_arm)

    report = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert report.blocked is False
    assert report.applied is True
    assert report.importer_imported == 1
    assert report.product_verification == "failed"
    assert report.detail == "adoption committed; product verification failed"
    objects = list_plans()
    assert len(objects) == 1
    assert str(objects[0].work_object_id) == doc_id
    durable = snapshot_plan(doc_id)
    assert durable.markdown == body
    assert durable.content_sha256 == sha256_utf8(body)

    raise_on_seam["on"] = False
    replay = apply_plan_adoption(
        current_repo_root=current,
        historical_root=hist,
        document_ids=[doc_id],
    )
    assert replay.blocked is False
    assert replay.applied is True
    assert replay.dispositions[0].classification == "CURRENT_EXACT"
    assert replay.dispositions[0].action == "noop"
    assert replay.importer_imported == 0
    assert replay.product_verification == "passed"
    assert len(list_plans()) == 1
    assert list_plans()[0].object_revision == objects[0].object_revision
    snapshot = get_workspace_document_snapshot(current, doc_id)
    assert snapshot.markdown == body
