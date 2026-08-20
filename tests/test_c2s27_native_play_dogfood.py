from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from apps.live_control_server.services.play_run_reference_manifest import (
    derive_play_run_reference_elements,
)
from apps.live_control_server.services.workspace_document_registry import (
    REGISTRY_SCHEMA,
    create_workspace_document,
    discard_workspace_document,
    list_workspace_documents,
    workspace_documents_path,
)
from scripts.c2s27_native_play_dogfood import (
    CAMPAIGN_ID,
    EXPECTED_ARTIFACT_SHA256,
    TARGET_RELPATH,
    TARGET_SESSION,
    TITLE,
    DogfoodSetupError,
    canonical_artifact_sha256,
    setup_c2s27_runbook,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ARTIFACT = REPO_ROOT / TARGET_RELPATH
HELPER_SOURCE = REPO_ROOT / "scripts/c2s27_native_play_dogfood.py"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    dest = tmp_path / TARGET_RELPATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(CANONICAL_ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_artifact_sha_pin_matches_checked_in_session_27_file() -> None:
    text = CANONICAL_ARTIFACT.read_text(encoding="utf-8")
    assert canonical_artifact_sha256(text) == EXPECTED_ARTIFACT_SHA256


def test_marker_structure_is_one_scene_and_five_beats() -> None:
    markdown = CANONICAL_ARTIFACT.read_text(encoding="utf-8")
    elements = derive_play_run_reference_elements(markdown)
    assert [(el.kind, el.element_id, el.scene_id) for el in elements] == [
        ("scene", "scene:mireward-climax", None),
        ("beat", "beat:survive-breach", "scene:mireward-climax"),
        ("beat", "beat:town-wide-siege", "scene:mireward-climax"),
        ("beat", "beat:thrin-memory", "scene:mireward-climax"),
        ("beat", "beat:wall-hinge", "scene:mireward-climax"),
        ("beat", "beat:aftermath-fork", "scene:mireward-climax"),
    ]
    assert all(el.kind not in {"choice", "option"} for el in elements)


def test_artifact_has_no_plain_markdown_blockquotes() -> None:
    """Native Play treats plain `>` blockquotes as blocking P1 warnings."""
    for line_no, line in enumerate(CANONICAL_ARTIFACT.read_text(encoding="utf-8").splitlines(), start=1):
        assert not line.startswith(">"), f"plain blockquote at line {line_no}"


def test_dry_run_with_no_record_mutates_nothing(root: Path) -> None:
    before = list(list_workspace_documents(root, status=None))
    result = setup_c2s27_runbook(root=root, apply=False)
    after = list(list_workspace_documents(root, status=None))
    assert result["status"] == "would_create_and_commit"
    assert result["created_this_run"] is False
    assert result["committed_this_run"] is False
    assert before == after
    assert not workspace_documents_path(root).exists() or after == []


def test_apply_creates_exactly_one_committed_runbook(root: Path) -> None:
    result = setup_c2s27_runbook(root=root, apply=True)
    records = list_workspace_documents(root, status=None)
    assert result["status"] == "created_and_committed"
    assert result["created_this_run"] is True
    assert result["committed_this_run"] is True
    assert result["content_status"] == "committed"
    assert result["target_session"] == TARGET_SESSION
    assert result["content_sha256"] == EXPECTED_ARTIFACT_SHA256
    assert len(records) == 1
    assert records[0].document_id == result["document_id"]
    assert records[0].kind == "runbook"
    assert records[0].title == TITLE
    assert records[0].campaign_id == CAMPAIGN_ID
    assert not (root / "out/runtime/play/runs").exists()


def test_second_apply_is_noop_same_id_and_revision(root: Path) -> None:
    first = setup_c2s27_runbook(root=root, apply=True)
    second = setup_c2s27_runbook(root=root, apply=True)
    assert second["status"] == "ready_existing"
    assert second["document_id"] == first["document_id"]
    assert second["revision"] == first["revision"]
    assert second["created_this_run"] is False
    assert second["committed_this_run"] is False
    assert len(list_workspace_documents(root, status=None)) == 1


def test_existing_exact_draft_is_committed_not_replaced(root: Path) -> None:
    draft = create_workspace_document(
        root,
        title=TITLE,
        campaign_id=CAMPAIGN_ID,
        kind="runbook",
        target_session=TARGET_SESSION,
        target_relpath=TARGET_RELPATH,
    )
    result = setup_c2s27_runbook(root=root, apply=True)
    records = list_workspace_documents(root, status=None)
    assert result["status"] == "committed_existing_draft"
    assert result["document_id"] == draft.document_id
    assert result["content_status"] == "committed"
    assert result["created_this_run"] is False
    assert result["committed_this_run"] is True
    assert len(records) == 1


def test_discarded_owner_fails_closed_without_second_record(root: Path) -> None:
    discarded = create_workspace_document(
        root,
        title=TITLE,
        campaign_id=CAMPAIGN_ID,
        kind="runbook",
        target_session=TARGET_SESSION,
        target_relpath=TARGET_RELPATH,
    )
    discard_workspace_document(root, discarded.document_id)
    with pytest.raises(DogfoodSetupError) as caught:
        setup_c2s27_runbook(root=root, apply=True)
    assert caught.value.code == "discarded_owner"
    records = list_workspace_documents(root, status=None)
    assert [record.document_id for record in records] == [discarded.document_id]
    assert records[0].status == "discarded"
    assert records[0].content_status == "draft"


@pytest.mark.parametrize(
    ("override", "conflict_key"),
    [
        ({"campaign_id": "longmont-c1"}, "campaign_id"),
        ({"target_session": 26}, "target_session"),
        ({"title": "Wrong Session 27 title"}, "title"),
    ],
)
def test_wrong_metadata_fails_closed(
    root: Path, override: dict[str, object], conflict_key: str
) -> None:
    kwargs: dict[str, object] = {
        "title": TITLE,
        "campaign_id": CAMPAIGN_ID,
        "kind": "runbook",
        "target_session": TARGET_SESSION,
        "target_relpath": TARGET_RELPATH,
        **override,
    }
    owner = create_workspace_document(root, **kwargs)  # type: ignore[arg-type]
    with pytest.raises(DogfoodSetupError) as caught:
        setup_c2s27_runbook(root=root, apply=True)
    assert caught.value.code == "metadata_conflict"
    assert caught.value.extra["document_id"] == owner.document_id
    assert conflict_key in caught.value.extra["conflicts"]
    remaining = list_workspace_documents(root, status=None)
    assert [record.document_id for record in remaining] == [owner.document_id]
    assert remaining[0].content_status == "draft"


def test_wrong_kind_fails_closed(root: Path) -> None:
    owner = create_workspace_document(
        root,
        title=TITLE,
        campaign_id=CAMPAIGN_ID,
        kind="runbook",
        target_session=TARGET_SESSION,
        target_relpath=TARGET_RELPATH,
    )
    path = workspace_documents_path(root)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["records"][0]["kind"] = "plan"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(DogfoodSetupError) as caught:
        setup_c2s27_runbook(root=root, apply=True)
    assert caught.value.code == "metadata_conflict"
    assert caught.value.extra["document_id"] == owner.document_id
    assert "kind" in caught.value.extra["conflicts"]
    remaining = list_workspace_documents(root, status=None)
    assert [record.document_id for record in remaining] == [owner.document_id]
    assert remaining[0].kind == "plan"
    assert remaining[0].content_status == "draft"


def test_missing_artifact_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(DogfoodSetupError) as caught:
        setup_c2s27_runbook(root=tmp_path, apply=True)
    assert caught.value.code == "missing_artifact"
    assert list_workspace_documents(tmp_path, status=None) == []


def test_sha_mismatch_fails_before_registry_mutation(root: Path) -> None:
    (root / TARGET_RELPATH).write_text("# tampered\n", encoding="utf-8")
    with pytest.raises(DogfoodSetupError) as caught:
        setup_c2s27_runbook(root=root, apply=True)
    assert caught.value.code == "sha_mismatch"
    assert list_workspace_documents(root, status=None) == []


def test_multiple_owners_fail_closed(root: Path) -> None:
    first = create_workspace_document(
        root,
        title=TITLE,
        campaign_id=CAMPAIGN_ID,
        kind="runbook",
        target_session=TARGET_SESSION,
        target_relpath=TARGET_RELPATH,
    )
    path = workspace_documents_path(root)
    document = json.loads(path.read_text(encoding="utf-8"))
    clone = dict(document["records"][0])
    clone["document_id"] = str(uuid.uuid4())
    document["records"].append(clone)
    document["schema_version"] = REGISTRY_SCHEMA
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(DogfoodSetupError) as caught:
        setup_c2s27_runbook(root=root, apply=True)
    assert caught.value.code == "multiple_owners"
    ids = {record.document_id for record in list_workspace_documents(root, status=None)}
    assert first.document_id in ids
    assert len(ids) == 2


def test_helper_source_does_not_create_play_run_or_manifest_state() -> None:
    source = HELPER_SOURCE.read_text(encoding="utf-8")
    forbidden = (
        "play_run_registry",
        "play_run_reference_manifest",
        "play_run_progress",
        "play_run_rebase",
        "create_play_run",
        "putPlayRun",
    )
    for token in forbidden:
        assert token not in source
