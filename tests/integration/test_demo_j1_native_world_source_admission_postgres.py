from __future__ import annotations

import os
import uuid
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

import pytest

from apps.live_control_server import config
from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as native
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document_snapshot,
)
from apps.live_control_server.services.world_container_registry import create_world_container
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresNativeSourceEvidenceRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def disposable_database_url(monkeypatch: pytest.MonkeyPatch) -> str:
    url = os.environ.get("DMB_DEMO_J1_DISPOSABLE_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("DMB_DEMO_J1_DISPOSABLE_DATABASE_URL must point at a dedicated disposable database")
    parsed = urlparse(url)
    database_name = parsed.path.removeprefix("/")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or not database_name.startswith(
        "dmb_demo_j1_"
    ):
        pytest.fail("Refusing integration writes outside a loopback dmb_demo_j1_* database")
    monkeypatch.setattr(config, "world_graph_authority_database_url", lambda: url)
    return url


def test_native_source_admission_persists_and_replays_after_repository_recreation(
    tmp_path: Path, disposable_database_url: str
) -> None:
    world = create_world_container(tmp_path, name=f"J1 Integration {uuid.uuid4().hex[:10]}")
    markdown = "# Exact source\n\nThis text remains evidence, not extracted canon.\n"
    record = create_workspace_document(
        tmp_path,
        title="J1 persistent source",
        campaign_id=world.world_id,
        world_id=world.world_id,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    ).committed_record

    snapshot = get_workspace_document_snapshot(tmp_path, committed.document_id)
    first = native.admit_native_world_source(
        tmp_path,
        committed.document_id,
        expected_revision=snapshot.loaded_revision,
        expected_body_sha256=snapshot.content_sha256,
    )
    first_repository = PostgresNativeSourceEvidenceRepository(
        PostgresDatabase(disposable_database_url)
    )
    head_after_admission = first_repository.get_head(world.world_id)
    assert head_after_admission is not None
    receipt = first_repository.get_native_source_admission_receipt(
        world.world_id, first.admission_id
    )
    assert receipt is not None

    # Recreate service/repository objects as after a process restart.
    replay = native.admit_native_world_source(
        tmp_path,
        committed.document_id,
        expected_revision=snapshot.loaded_revision,
        expected_body_sha256=snapshot.content_sha256,
    )
    fresh_repository = PostgresNativeSourceEvidenceRepository(
        PostgresDatabase(disposable_database_url)
    )
    fresh_head = fresh_repository.get_head(world.world_id)
    fresh_receipt = fresh_repository.get_native_source_admission_receipt(
        world.world_id, replay.admission_id
    )
    snapshot = get_workspace_document_snapshot(tmp_path, committed.document_id)
    body = snapshot.markdown.encode("utf-8")
    status = native.get_native_world_source_status(
        tmp_path, committed.document_id, expected_revision=committed.revision
    )

    assert replay.state == status.state == "admitted"
    assert first.admission_id == replay.admission_id == status.admission_id
    assert replay.published_revision_id == first.published_revision_id
    assert fresh_head == head_after_admission
    assert fresh_receipt == receipt
    assert status.body_sha256 == sha256(body).hexdigest()
    assert status.span_start_byte == 0
    assert status.span_end_byte == len(body)
