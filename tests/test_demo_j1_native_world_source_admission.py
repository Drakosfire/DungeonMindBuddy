from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as native
from apps.live_control_server.routes import workspace_documents
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
)
from apps.live_control_server.services.world_container_registry import create_world_container
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository


def _committed_source(root: Path, *, markdown: str = "# Source\n\nA private world source.\n"):
    world = create_world_container(root, name="J1 Test World")
    record = create_workspace_document(
        root,
        title="Test Source",
        campaign_id=world.world_id,
        world_id=world.world_id,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    committed = commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    return world, committed.committed_record


@pytest.fixture
def memory_repository(monkeypatch: pytest.MonkeyPatch) -> InMemoryNativeSourceEvidenceRepository:
    repository = InMemoryNativeSourceEvidenceRepository()
    monkeypatch.setattr(native, "_repository", lambda: repository)
    return repository


def test_admission_is_exact_replayable_and_exposes_the_committed_whole_span(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    world, record = _committed_source(tmp_path, markdown="# Exact\n\nNo inference.\n")

    first = native.admit_native_world_source(
        tmp_path, record.document_id, expected_revision=record.revision
    )
    head_after_first = memory_repository.get_head(world.world_id)
    replay = native.admit_native_world_source(
        tmp_path, record.document_id, expected_revision=record.revision
    )
    status = native.get_native_world_source_status(
        tmp_path, record.document_id, expected_revision=record.revision
    )

    snapshot = native.get_workspace_document_snapshot(tmp_path, record.document_id)
    body = snapshot.markdown.encode("utf-8")
    assert first.state == replay.state == status.state == "admitted"
    assert first.admission_id == replay.admission_id == status.admission_id
    assert first.published_revision_id == replay.published_revision_id
    assert memory_repository.get_head(world.world_id) == head_after_first
    assert status.world_id == status.space_id == world.world_id
    assert status.document_id == record.document_id
    assert status.body_sha256 == sha256(body).hexdigest()
    assert status.span_start_byte == 0
    assert status.span_end_byte == len(body)


def test_status_is_pending_before_admission_and_revision_change_fails_closed(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    _world, record = _committed_source(tmp_path)

    pending = native.get_native_world_source_status(tmp_path, record.document_id)
    assert pending.state == "pending"
    assert pending.code == "native_admission_pending"
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        native.admit_native_world_source(
            tmp_path, record.document_id, expected_revision=record.revision - 1
        )
    assert error.value.code == "source_revision_changed"


def test_status_preserves_exact_retry_identity_when_authority_is_temporarily_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _world, record = _committed_source(tmp_path)

    def unavailable():
        raise native.NativeWorldSourceAdmissionError(
            "authority_unavailable", "no local authority", status_code=503
        )

    monkeypatch.setattr(native, "_repository", unavailable)
    status = native.get_native_world_source_status(tmp_path, record.document_id)
    assert status.state == "pending"
    assert status.code == "authority_unavailable"
    assert status.loaded_revision == record.revision
    assert status.admission_id


def test_status_is_pending_when_stored_receipt_readback_is_temporarily_unavailable(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _world, record = _committed_source(tmp_path)
    admitted = native.admit_native_world_source(
        tmp_path, record.document_id, expected_revision=record.revision
    )

    class PersistenceUnavailableError(RuntimeError):
        pass

    def unavailable(**_kwargs):
        raise PersistenceUnavailableError("temporary outage")

    monkeypatch.setattr(native, "open_native_text_source_access_context", unavailable)
    status = native.get_native_world_source_status(tmp_path, record.document_id)

    assert status.state == "pending"
    assert status.code == "authority_unavailable"
    assert status.admission_id == admitted.admission_id
    assert status.message and "readback" in status.message


def test_genesis_survives_admission_failure_and_exact_retry_completes(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world, record = _committed_source(tmp_path)
    publish = native.publish_native_text_source_evidence

    def fail_once(**_kwargs):
        raise RuntimeError("simulated publication interruption")

    monkeypatch.setattr(native, "publish_native_text_source_evidence", fail_once)
    with pytest.raises(native.NativeWorldSourceAdmissionError) as failure:
        native.admit_native_world_source(
            tmp_path, record.document_id, expected_revision=record.revision
        )
    assert failure.value.code == "native_admission_failed"
    genesis_head = memory_repository.get_head(world.world_id)
    assert genesis_head is not None
    assert memory_repository.get_native_source_admission_receipt(
        world.world_id,
        native._stable_id(
            "dmb-world-source",
            world.world_id,
            record.document_id,
            str(record.revision),
            sha256(b"# Source\n\nA private world source.\n").hexdigest(),
        ),
    ) is None

    monkeypatch.setattr(native, "publish_native_text_source_evidence", publish)
    recovered = native.admit_native_world_source(
        tmp_path, record.document_id, expected_revision=record.revision
    )
    assert recovered.state == "admitted"


def test_non_worldbuilding_or_player_safe_documents_are_rejected(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    _world, record = _committed_source(tmp_path)
    original = native.get_workspace_document_snapshot

    class SnapshotProxy:
        def __init__(self, snapshot, *, kind=None, visibility=None):
            self._snapshot = snapshot
            self._kind = kind
            self._visibility = visibility

        def __getattr__(self, name):
            return getattr(self._snapshot, name)

        @property
        def record(self):
            value = self._snapshot.record.model_copy(deep=True)
            if self._kind is not None:
                value.kind = self._kind
            if self._visibility is not None:
                value.visibility_state = self._visibility
            return value

    snapshot = original(tmp_path, record.document_id)
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            native,
            "get_workspace_document_snapshot",
            lambda *_args: SnapshotProxy(snapshot, kind="plan"),
        )
        with pytest.raises(native.NativeWorldSourceAdmissionError) as kind_error:
            native.get_native_world_source_status(tmp_path, record.document_id)
        assert kind_error.value.code == "unsupported_source"

        monkeypatch.setattr(
            native,
            "get_workspace_document_snapshot",
            lambda *_args: SnapshotProxy(snapshot, visibility="player_safe"),
        )
        with pytest.raises(native.NativeWorldSourceAdmissionError) as visibility_error:
            native.get_native_world_source_status(tmp_path, record.document_id)
        assert visibility_error.value.code == "unsupported_visibility"
    finally:
        monkeypatch.undo()


def test_route_accepts_only_expected_revision_and_returns_typed_status(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _world, record = _committed_source(tmp_path)
    monkeypatch.setattr(workspace_documents, "repo_root", lambda: tmp_path)
    with pytest.raises(ValidationError):
        workspace_documents.NativeWorldSourceAdmissionRequest.model_validate(
            {"expected_revision": record.revision, "markdown": "client text is forbidden"}
        )

    admitted = workspace_documents.post_native_world_source_admission(
        record.document_id,
        workspace_documents.NativeWorldSourceAdmissionRequest(
            expected_revision=record.revision
        ),
    )
    assert admitted["state"] == "admitted"
    assert admitted["world_id"] == admitted["space_id"] == "j1-test-world"
