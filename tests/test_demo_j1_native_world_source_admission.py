from __future__ import annotations

from application_state.world_catalog.service import get_world
from tests.application_state.world_catalog_fixtures import store_world, change_binding, world_snapshot

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


def _committed_source(
    root: Path,
    *,
    markdown: str = "# Source\n\nA private world source.\n",
    world=None,
    provisioned: bool = False,
):
    if world is None:
        world = create_world_container(root, name="J1 Test World")
    if not provisioned:
        world = store_world(world.model_copy(update={"native_graph_binding": {
            "native_world_id": world.world_id, "binding_version": 1,
            "status": "active", "validated_at": "2026-10-14T00:00:00Z",
            "validated_head_revision_id": "rev:fixture",
        }}))
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


def _admit(root: Path, document_id: str, *, expected_revision: int | None = None):
    snapshot = native.get_workspace_document_snapshot(root, document_id)
    return native.admit_native_world_source(
        root,
        document_id,
        expected_revision=(snapshot.loaded_revision if expected_revision is None else expected_revision),
        expected_body_sha256=snapshot.content_sha256,
    )


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

    first = _admit(tmp_path, record.document_id)
    head_after_first = memory_repository.get_head(world.world_id)
    replay = _admit(tmp_path, record.document_id)
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
        _admit(tmp_path, record.document_id, expected_revision=record.revision - 1)
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
    admitted = _admit(tmp_path, record.document_id)

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
        _admit(tmp_path, record.document_id)
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
    recovered = _admit(tmp_path, record.document_id)
    assert recovered.state == "admitted"


def test_post_admission_body_pin_rejects_source_bytes_changed_without_registry_revision_bump(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    world, record = _committed_source(tmp_path)
    snapshot = native.get_workspace_document_snapshot(tmp_path, record.document_id)
    target = tmp_path / record.target_relpath
    target.write_text(snapshot.markdown + "\nChanged outside the registry.\n", encoding="utf-8")

    with pytest.raises(native.NativeWorldSourceAdmissionError) as failure:
        native.admit_native_world_source(
            tmp_path,
            record.document_id,
            expected_revision=snapshot.loaded_revision,
            expected_body_sha256=snapshot.content_sha256,
        )

    assert failure.value.code == "source_body_changed"
    assert memory_repository.get_head(world.world_id) is None
    admission_id = native._stable_id(
        "dmb-world-source",
        world.world_id,
        record.document_id,
        str(snapshot.loaded_revision),
        snapshot.content_sha256,
    )
    assert memory_repository.get_native_source_admission_receipt(
        world.world_id, admission_id
    ) is None


def test_admission_digest_is_for_the_registry_snapshot_newline_representation(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    world, record = _committed_source(
        tmp_path,
        markdown="# Exact source\r\n\r\nCRLF is normalized by the workspace snapshot.\r\n",
    )
    snapshot = native.get_workspace_document_snapshot(tmp_path, record.document_id)

    assert "\r" not in snapshot.markdown
    snapshot_body = snapshot.markdown.encode("utf-8")
    assert snapshot.content_sha256 == sha256(snapshot_body).hexdigest()
    admitted = native.admit_native_world_source(
        tmp_path,
        record.document_id,
        expected_revision=snapshot.loaded_revision,
        expected_body_sha256=snapshot.content_sha256,
    )

    assert admitted.body_sha256 == snapshot.content_sha256
    assert admitted.span_end_byte == len(snapshot_body)
    opened = native.open_admitted_native_text(
        native.open_native_text_source_access_context(
            repository=memory_repository,
            space_id=world.world_id,
            revision_id=admitted.published_revision_id,
            domain_contract=native.dungeonbuddy_world_domain_contract(),
            audience_labels=[native.GM_LABEL],
        ),
        admitted.evidence_ref_id,
    )
    assert opened.body_text == snapshot.markdown
    assert opened.body_sha256 == snapshot.content_sha256


def test_replay_of_older_source_after_descendant_admission_does_not_rewind_head(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    world, first_record = _committed_source(tmp_path, markdown="# First source\n")
    first = _admit(tmp_path, first_record.document_id)
    _same_world, second_record = _committed_source(
        tmp_path, markdown="# Second source\n", world=world
    )
    second = _admit(tmp_path, second_record.document_id)
    descendant_head = memory_repository.get_head(world.world_id)

    replay = _admit(tmp_path, first_record.document_id)

    assert replay.published_revision_id == first.published_revision_id
    assert second.published_revision_id != first.published_revision_id
    assert memory_repository.get_head(world.world_id) == descendant_head


def test_foreign_world_and_descriptor_drift_fail_before_native_mutation(
    tmp_path: Path,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world, record = _committed_source(tmp_path)
    original_snapshot = native.get_workspace_document_snapshot
    snapshot = original_snapshot(tmp_path, record.document_id)

    class ForeignWorldSnapshot:
        def __getattr__(self, name):
            return getattr(snapshot, name)

        @property
        def record(self):
            changed = snapshot.record.model_copy(deep=True)
            changed.world_id = "foreign-world"
            changed.campaign_id = "foreign-world"
            return changed

    monkeypatch.setattr(
        native, "get_workspace_document_snapshot", lambda *_args: ForeignWorldSnapshot()
    )
    with pytest.raises(native.NativeWorldSourceAdmissionError) as foreign:
        native.admit_native_world_source(
            tmp_path,
            record.document_id,
            expected_revision=snapshot.loaded_revision,
            expected_body_sha256=snapshot.content_sha256,
        )
    assert foreign.value.code == "managed_world_missing"
    assert memory_repository.get_head(world.world_id) is None

    monkeypatch.setattr(native, "get_workspace_document_snapshot", original_snapshot)
    from graph_memory.vnext import domain_runtime
    monkeypatch.setattr(domain_runtime, "canonical_sha256", lambda _value: "0" * 64)
    with pytest.raises(native.NativeWorldSourceAdmissionError) as drift:
        _admit(tmp_path, record.document_id)
    assert drift.value.code == "descriptor_drift"
    assert memory_repository.get_head(world.world_id) is None


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
    with pytest.raises(ValidationError):
        workspace_documents.NativeWorldSourceAdmissionRequest.model_validate(
            {"expected_revision": record.revision}
        )

    snapshot = native.get_workspace_document_snapshot(tmp_path, record.document_id)

    admitted = workspace_documents.post_native_world_source_admission(
        record.document_id,
        workspace_documents.NativeWorldSourceAdmissionRequest(
            expected_revision=snapshot.loaded_revision,
            expected_body_sha256=snapshot.content_sha256,
        ),
    )
    assert admitted["state"] == "admitted"
    assert admitted["world_id"] == admitted["space_id"] == "j1-test-world"


def test_source_admission_uses_separate_managed_registry_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    document_root = tmp_path / "documents"
    document_root.mkdir()
    world, record = _committed_source(document_root)
    registry_root = tmp_path / "managed"
    registry_root.mkdir()
    monkeypatch.setenv(native.config.MANAGED_WORLD_DATA_ROOT_ENV, str(registry_root))

    admitted = _admit(document_root, record.document_id)
    status = native.get_native_world_source_status(document_root, record.document_id)
    assert admitted.state == status.state == "admitted"
    assert admitted.world_id == world.world_id
    assert admitted.body_sha256 == native.get_workspace_document_snapshot(
        document_root, record.document_id
    ).content_sha256
    assert _admit(document_root, record.document_id).admission_id == admitted.admission_id


@pytest.mark.parametrize("invalid_root", ["relative", "missing"])
def test_source_admission_invalid_managed_root_fails_without_publication(
    invalid_root: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    world, record = _committed_source(tmp_path)
    configured = {"relative": "relative-root", "missing": str(tmp_path / "missing")}[invalid_root]
    monkeypatch.setenv(native.config.MANAGED_WORLD_DATA_ROOT_ENV, configured)
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        _admit(tmp_path, record.document_id)
    assert error.value.code == "managed_world_unavailable"
    assert error.value.status_code == 503
    assert memory_repository.get_head(world.world_id) is None

    with pytest.raises(native.NativeWorldSourceAdmissionError) as status_error:
        native.get_native_world_source_status(tmp_path, record.document_id)
    assert status_error.value.code == "managed_world_unavailable"
    assert status_error.value.status_code == 503


@pytest.mark.parametrize("native_id", ["native-alpha", "native-beta"])
def test_source_admits_only_to_explicit_native_world(
    tmp_path, monkeypatch, memory_repository, native_id,
):
    world, record = _committed_source(tmp_path)
    change_binding(world.world_id, native_world_id=native_id)
    first = _admit(tmp_path, record.document_id)
    assert first.world_id == world.world_id
    assert first.space_id == native_id
    assert memory_repository.get_head(world.world_id) is None
    assert memory_repository.get_head(native_id) is not None
    assert _admit(tmp_path, record.document_id).admission_id == first.admission_id
    assert native.get_native_world_source_status(tmp_path, record.document_id).space_id == native_id


def test_missing_binding_rejects_before_repository_access(tmp_path, monkeypatch):
    world, record = _committed_source(tmp_path)
    store_world(world.model_copy(update={"native_graph_binding": None}))
    monkeypatch.setattr(native, "_repository", lambda: pytest.fail("unbound native access"))
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        _admit(tmp_path, record.document_id)
    assert error.value.code == "native_graph_binding_missing"


def test_binding_change_before_source_publication_rejects(tmp_path, monkeypatch, memory_repository):
    world, record = _committed_source(tmp_path)
    original = native.initialize_empty_knowledge_space
    def changing_initialize(**kwargs):
        result = original(**kwargs)
        change_binding(world.world_id, binding_version=get_world(world.world_id).record.native_graph_binding.binding_version + 1)
        return result
    monkeypatch.setattr(native, "initialize_empty_knowledge_space", changing_initialize)
    monkeypatch.setattr(native, "publish_native_text_source_evidence",
                        lambda **kwargs: pytest.fail("changed binding published source"))
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        _admit(tmp_path, record.document_id)
    assert error.value.code == "native_graph_binding_changed"


@pytest.mark.parametrize("state", ["inactive", "missing"])
def test_unavailable_binding_blocks_status_and_admission(tmp_path, monkeypatch, state):
    world, record = _committed_source(tmp_path)
    if state == "missing":
        store_world(world.model_copy(update={"native_graph_binding": None}))
    else:
        change_binding(world.world_id, status="inactive")
    monkeypatch.setattr(native, "_repository", lambda: pytest.fail("unbound native access"))
    for operation in [lambda: _admit(tmp_path, record.document_id),
                      lambda: native.get_native_world_source_status(tmp_path, record.document_id)]:
        with pytest.raises(native.NativeWorldSourceAdmissionError):
            operation()


@pytest.mark.parametrize("operation", ["status", "replay"])
def test_binding_change_during_repository_access_rejects_admitted_result(
    tmp_path, monkeypatch, memory_repository, operation,
):
    world, record = _committed_source(tmp_path)
    _admit(tmp_path, record.document_id)
    def changed_repository():
        change_binding(world.world_id, binding_version=get_world(world.world_id).record.native_graph_binding.binding_version + 1)
        return memory_repository
    monkeypatch.setattr(native, "_repository", changed_repository)
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        if operation == "status":
            native.get_native_world_source_status(tmp_path, record.document_id)
        else:
            _admit(tmp_path, record.document_id)
    assert error.value.code == "native_graph_binding_changed"


def test_binding_changes_during_native_readback_rejects(tmp_path, monkeypatch, memory_repository):
    world, record = _committed_source(tmp_path)
    _admit(tmp_path, record.document_id)
    original = native.open_admitted_native_text
    def changed_readback(*args, **kwargs):
        result = original(*args, **kwargs)
        change_binding(world.world_id, binding_version=get_world(world.world_id).record.native_graph_binding.binding_version + 1)
        return result
    monkeypatch.setattr(native, "open_admitted_native_text", changed_readback)
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        native.get_native_world_source_status(tmp_path, record.document_id)
    assert error.value.code == "native_graph_binding_changed"


def test_committed_source_recovery_does_not_hide_binding_change(tmp_path, monkeypatch, memory_repository):
    world, record = _committed_source(tmp_path)
    original = native.publish_native_text_source_evidence
    def committed_then_changed(**kwargs):
        receipt = original(**kwargs)
        change_binding(world.world_id, binding_version=get_world(world.world_id).record.native_graph_binding.binding_version + 1)
        raise RuntimeError("synthetic outcome observation failure")
    monkeypatch.setattr(native, "publish_native_text_source_evidence", committed_then_changed)
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        _admit(tmp_path, record.document_id)
    assert error.value.code == "native_graph_binding_changed"
    assert memory_repository.get_head(world.world_id) is not None


def test_ordinary_fresh_world_source_admission_needs_no_active_graph(
    tmp_path: Path, memory_repository: InMemoryNativeSourceEvidenceRepository,
) -> None:
    from apps.live_control_server.services.world_container_registry import get_world_container
    world, record = _committed_source(tmp_path, provisioned=True)
    reservation = get_world_container(tmp_path, world.world_id).native_graph_binding
    assert reservation.status == "provisioning"
    before = world_snapshot()
    assert memory_repository.get_head(reservation.native_world_id) is None
    admitted = _admit(tmp_path, record.document_id)
    assert admitted.state == "admitted"
    assert admitted.world_id == world.world_id
    assert admitted.space_id == reservation.native_world_id != world.world_id
    assert _admit(tmp_path, record.document_id) == admitted
    assert world_snapshot() == before
    assert get_world_container(tmp_path, world.world_id).native_graph_binding == reservation


def test_reserved_operation_change_during_admission_fails_closed(
    tmp_path, monkeypatch, memory_repository,
):
    world, record = _committed_source(tmp_path, provisioned=True)
    original = native.initialize_empty_knowledge_space
    def changed_operation(**kwargs):
        result = original(**kwargs)
        change_binding(world.world_id, provisioning_id="provision:" + "f" * 32)
        return result
    monkeypatch.setattr(native, "initialize_empty_knowledge_space", changed_operation)
    with pytest.raises(native.NativeWorldSourceAdmissionError) as error:
        _admit(tmp_path, record.document_id)
    assert error.value.code == "native_graph_binding_changed"


@pytest.mark.parametrize("profile_revision", ("1", "2"))
def test_existing_world_preserves_profile_and_original_receipt(
    tmp_path, memory_repository, monkeypatch, profile_revision,
):
    from datetime import UTC, datetime
    from dungeonmind.application.vnext import initialize_empty_knowledge_space
    from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_custom_predicate_profile
    world, record = _committed_source(tmp_path, markdown="# Original source\n")
    profile = (dungeonbuddy_dnd5e_custom_predicate_profile() if profile_revision == "2"
               else native.dungeonbuddy_dnd5e_semantic_profile())
    initialize_empty_knowledge_space(
        repository=memory_repository, space_id=world.world_id,
        initialization_id="existing-world", created_at=datetime(2026, 10, 29, tzinfo=UTC),
        domain_contract=native.dungeonbuddy_world_domain_contract(), semantic_profile=profile,
    )
    def forbidden_genesis(**_):
        raise AssertionError("Existing World must not be reinitialized")
    monkeypatch.setattr(native, "initialize_empty_knowledge_space", forbidden_genesis)
    first = _admit(tmp_path, record.document_id)
    _, second_record = _committed_source(tmp_path, markdown="# Descendant source\n", world=world)
    second = _admit(tmp_path, second_record.document_id)
    head = memory_repository.get_head(world.world_id)
    snapshot = memory_repository.get_revision(world.world_id, head.head_revision_id)
    assert snapshot.revision.semantic_profile_ref.profile_revision == profile_revision
    selected = []
    original = native._descriptors
    def track(repository, space_id, revision_id):
        selected.append(revision_id)
        return original(repository, space_id, revision_id)
    monkeypatch.setattr(native, "_descriptors", track)
    assert _admit(tmp_path, record.document_id) == first
    assert first.evidence_ref_id != second.evidence_ref_id
    assert selected == [first.published_revision_id]
    assert memory_repository.get_head(world.world_id) == head

pytestmark = pytest.mark.usefixtures("application_state_dsn")
