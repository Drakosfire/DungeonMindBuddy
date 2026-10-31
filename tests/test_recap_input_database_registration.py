"""Recap input capture owns database bytes, not duplicate source files."""
import hashlib
from pathlib import Path

import pytest

from apps.live_control_server.services import source_artifact_registry as registry

pytestmark = pytest.mark.usefixtures("application_state_dsn")
BODY = "# Original recap\n\nMira’s Arcana check found planar meat.\n"


@pytest.mark.parametrize("mode", ["text", "file", "build"])
def test_capture_needs_no_recap_file_writes(tmp_path, monkeypatch, mode):
    original = tmp_path / "original.md"
    if mode == "file":
        original.write_text(BODY)
    if mode == "build":
        (tmp_path / "corpus/managed-a-markdown").mkdir(parents=True)
        from apps.live_control_server.services.workspace_document_registry import (
            create_workspace_document, mark_workspace_document_committed,
        )
        document = create_workspace_document(
            tmp_path, title="External recap", world_id="managed-a", campaign_id="workspace-campaign",
            kind="worldbuilding_source", source_domain="worldbuilding", document_class="lore",
            authority_state="draft", visibility_state="internal",
        )
        original = tmp_path / document.target_relpath
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_text(BODY)
        document = mark_workspace_document_committed(tmp_path, document.document_id)

    def capture():
        if mode == "build":
            return registry.create_recap_source_artifact_from_workspace_document(
                tmp_path, document_id=document.document_id, expected_revision=document.revision,
                expected_content_sha256=hashlib.sha256(BODY.encode()).hexdigest(),
                managed_world_id="managed-a", native_world_id="native-a",
                campaign_id="source-campaign", session_id="session-8",
            )
        return registry.create_recap_source_artifact(
            tmp_path, world_id="native-a", campaign_id="source-campaign", session_id="session-8",
            **({"recap_path": original} if mode == "file" else {"recap_text": BODY}),
        )

    def files():
        return {str(p.relative_to(tmp_path)): p.read_bytes()
                for p in tmp_path.rglob("*") if p.is_file() and p.suffix != ".lock"}
    before = files()
    open_path = Path.open

    def no_copy_writes(path, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+") and path.suffix != ".lock":
            raise OSError("synthetic recap copy storage unavailable")
        return open_path(path, mode, *args, **kwargs)

    with monkeypatch.context() as guarded:
        guarded.setattr(Path, "open", no_copy_writes)
        artifact = capture()
        assert capture() == artifact
    assert artifact.uri == f"object://{artifact.source_artifact_id}"
    assert files() == before
    assert not (tmp_path / "out/registries/source_content").exists()
    assert registry.load_registered_source_artifact_bytes(tmp_path, artifact.source_artifact_id) == (
        artifact, BODY.encode(),
    )
    if mode != "text":
        assert original.read_text() == BODY
        original.write_text("Newer editable text.\n")
        assert registry.load_registered_source_artifact_text(tmp_path, artifact.source_artifact_id) == (
            artifact, BODY,
        )


def test_existing_frozen_descriptor_replays_without_opening_old_locator(tmp_path, monkeypatch):
    from application_state.source import service as source_service
    from graph_memory.evidence.source_artifact import (
        GraphMemorySourceArtifact, build_world_scoped_recap_source_artifact_id,
    )
    digest = hashlib.sha256(BODY.encode()).hexdigest()
    artifact_id = build_world_scoped_recap_source_artifact_id(
        world_id="native-a", campaign_id="source-campaign", session_id="session-8",
        content_sha256=digest,
    )
    legacy = GraphMemorySourceArtifact(
        source_artifact_id=artifact_id,
        source_domain="recap", world_id="native-a", campaign_id="source-campaign",
        session_id="session-8", uri="repo://missing-retained-recap.md", content_sha256=digest,
        artifact_kind="recap_markdown", document_class="recap", visibility_state="internal",
        lineage={"source_span_index_uri": "repo://" + registry.source_span_index_relpath(artifact_id)},
    )
    stored = registry._register_source_input(artifact=legacy, content=BODY)
    before = source_service.get_source_markdown(
        source_artifact_id=stored.source_artifact_id, content_sha256=digest,
    )
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("replay opened a file"))
    assert registry.create_recap_source_artifact(
        tmp_path, world_id="native-a", campaign_id="source-campaign", session_id="session-8",
        recap_text=BODY,
    ) == stored
    assert registry.load_registered_source_artifact_bytes(tmp_path, stored.source_artifact_id) == (stored, BODY.encode())
    assert source_service.get_source_markdown(
        source_artifact_id=stored.source_artifact_id, content_sha256=digest,
    ) == before


def test_object_locator_uses_existing_native_admission_owner(tmp_path):
    from types import SimpleNamespace
    from dungeonmind.infrastructure.memory.repositories import InMemorySourceRepository
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.ports.world_graph_source_admission import WorldGraphSourceAdmissionRequest

    artifact = registry.create_recap_source_artifact(
        tmp_path, world_id="native-a", campaign_id="source-campaign", session_id="session-8",
        recap_text=BODY,
    )
    sources = InMemorySourceRepository()
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(
        sources=sources, world_graph=SimpleNamespace(
            get_head=lambda world: SimpleNamespace(head_revision_id="rev:source-input-test")),
    )
    request = WorldGraphSourceAdmissionRequest(
        world_id=artifact.world_id, campaign_id=artifact.campaign_id, source_artifact=artifact,
        source_revision_token="sha256:" + artifact.content_sha256,
        source_uri=artifact.uri, source_body=BODY.encode(), expected_head_revision_id="rev:source-input-test",
    )
    admitted = adapter.prove_or_admit(request)
    assert admitted.content_sha256 == artifact.content_sha256
    assert sources.get_revision(admitted.source_revision_id).locator == artifact.uri
    assert adapter.prove_or_admit(request) == admitted
