from tests.application_state.world_catalog_fixtures import store_world
import json
import os
import subprocess
import sys

import pytest
import psycopg
from graph_memory.source_span import source_span_index_to_dict

from application_state.source.service import get_source_markdown
from apps.live_control_server.services import graph_run_registry as runs
from apps.live_control_server.services import source_artifact_registry as inputs
from apps.live_control_server.services import worldbuilding_source_span_read as reader
from apps.live_control_server.services.source_artifact_registry import (
    create_source_artifact_from_workspace_document,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWritePrepareRequest,
    TiptapMarkdownWriteCommitRequest,
    prepare_tiptap_markdown_write,
    commit_tiptap_markdown_write,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRunStatus,
)
from graph_memory.retrieval.errors import WorldGraphRetrievalError
from graph_memory.retrieval.models import WorldGraphRetrievalSnapshot


def save(root, doc, text):
    proposal = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=doc.document_id, markdown=text, expected_revision=doc.revision
        ),
    )
    assert proposal.writer_ok
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=doc.document_id,
            markdown=text,
            expected_revision=doc.revision,
            writer_confirm_token=proposal.writer_confirm_token,
        ),
    )
    return get_workspace_document(root, doc.document_id)


def fixture_source(root, monkeypatch):
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    registry_root = root / "managed-registry"
    registry_root.mkdir()
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(registry_root))
    world = create_world_container(registry_root, name="Managed World")
    assert world.world_id == "managed-world"
    store_world(world.model_copy(update={"native_graph_binding": {
        "native_world_id": "native-world",
        "binding_version": 1,
        "status": "active",
        "validated_at": "2026-10-14T00:00:00Z",
        "validated_head_revision_id": "rev:accepted",
    }}))
    doc = create_workspace_document(
        root,
        title="Lore",
        campaign_id="managed-world",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    doc = save(root, doc, "# Lore\n\nThe tower watches the river.\n")
    artifact = create_source_artifact_from_workspace_document(
        root, document_id=doc.document_id, expected_revision=doc.revision
    )
    directory = root / "out/runs/immutable"
    directory.mkdir(parents=True)
    original = (root / doc.target_relpath).read_bytes()
    (directory / "source.md").write_bytes(original)
    index_bytes = json.dumps(source_span_index_to_dict(
        inputs.load_source_span_index(root, artifact.source_artifact_id)), indent=2, ensure_ascii=False).encode() + b"\n"
    (directory / "spans.json").write_bytes(index_bytes)
    return (
        doc,
        artifact,
        json.loads(index_bytes)["spans"][-1]["source_span_id"],
        directory,
    )


def open_span(root, artifact, span, world="native-world"):
    snapshot = WorldGraphRetrievalSnapshot(
        world_id=world,
        campaign_id="managed-world",
        revision_id="rev:accepted",
        head_revision_id="rev:accepted",
        is_head=True,
        focus={},
        admissibility="accepted",
        scope_mode="world",
    )
    return reader.read_admitted_worldbuilding_span(
        root=root,
        source_artifact_id=artifact.source_artifact_id,
        source_span_ref_id=span,
        graph_content_sha256=artifact.content_sha256,
        max_chars=1000,
        anchor_id="anchor:accepted",
        snapshot=snapshot,
    )


def test_registered_historical_passage_after_real_save(
    tmp_path, monkeypatch, application_state_dsn
):
    doc, artifact, span, directory = fixture_source(tmp_path, monkeypatch)
    original_markdown = (tmp_path / doc.target_relpath).read_text(encoding="utf-8")
    durable = get_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256,
    )
    assert durable is not None
    assert durable.markdown == original_markdown
    assert durable.source_domain == "worldbuilding"
    assert durable.campaign_id == artifact.campaign_id
    assert durable.session_id is None
    assert durable.world_id == artifact.world_id

    # Opening a run does not duplicate the exact registered source.
    runs.create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=artifact.campaign_id,
        components={},
        status=ExtractionRunStatus.DRAFT,
    )
    with psycopg.connect(application_state_dsn) as conn:
        count = conn.execute(
            "SELECT count(*) FROM source.revision WHERE source_artifact_id = %s",
            (artifact.source_artifact_id,),
        ).fetchone()
    assert count == (1,)

    opened = open_span(tmp_path, artifact, span)
    assert opened.content == "The tower watches the river."
    assert opened.source_name == doc.title
    save(tmp_path, doc, "# Lore\n\nThe tower has fallen.\n")
    # The immutable DB revision, rather than the current workspace or local
    # derived files, now carries the exact old passage and stable span IDs.
    (directory / "source.md").unlink()
    (directory / "spans.json").unlink()
    (tmp_path / doc.target_relpath).unlink()
    assert open_span(tmp_path, artifact, span).content == "The tower watches the river."
    script = """
import sys
from pathlib import Path
from apps.live_control_server.services.worldbuilding_source_span_read import read_admitted_worldbuilding_span
from graph_memory.retrieval.models import WorldGraphRetrievalSnapshot
snapshot = WorldGraphRetrievalSnapshot(world_id='native-world',campaign_id='managed-world',revision_id='rev:accepted',head_revision_id='rev:accepted',is_head=True,focus={},admissibility='accepted',scope_mode='world')
result = read_admitted_worldbuilding_span(root=Path(sys.argv[1]),source_artifact_id=sys.argv[2],
    source_span_ref_id=sys.argv[3],graph_content_sha256=sys.argv[4],max_chars=1000,anchor_id='anchor:accepted',snapshot=snapshot)
assert result.content == 'The tower watches the river.'
print('historical-passage-opened')
"""
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            artifact.source_artifact_id,
            span,
            artifact.content_sha256,
        ],
        env=dict(os.environ),
        text=True,
        capture_output=True,
    )
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == "historical-passage-opened"
    with pytest.raises(WorldGraphRetrievalError, match="disagrees"):
        open_span(tmp_path, artifact, span, world="other-world")


def test_durable_world_mismatch_fails_closed(
    tmp_path, monkeypatch, application_state_dsn
):
    _doc, artifact, span, _directory = fixture_source(tmp_path, monkeypatch)
    get_source = inputs.source_service.get_source_markdown

    def wrong_world(**kwargs):
        record = get_source(**kwargs)
        assert record is not None
        return record.model_copy(update={"world_id": "foreign-world"})

    monkeypatch.setattr(inputs.source_service, "get_source_markdown", wrong_world)
    with pytest.raises(WorldGraphRetrievalError, match="database source body scope"):
        open_span(tmp_path, artifact, span)


def test_missing_historical_snapshot_never_opens_current_text(
    tmp_path, monkeypatch, application_state_dsn
):
    doc, artifact, span, directory = fixture_source(tmp_path, monkeypatch)
    save(tmp_path, doc, "# Lore\n\nThe tower has fallen.\n")
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "DELETE FROM source.revision WHERE source_artifact_id = %s",
            (artifact.source_artifact_id,),
        )
    (directory / "source.md").unlink()
    (directory / "spans.json").unlink()
    with pytest.raises(WorldGraphRetrievalError, match="missing from the database"):
        open_span(tmp_path, artifact, span)


def test_inactive_managed_binding_rejects_source(
    tmp_path, monkeypatch, application_state_dsn
):
    doc, artifact, span, directory = fixture_source(tmp_path, monkeypatch)
    from application_state.world_catalog.service import get_world
    world = get_world("managed-world").record
    store_world(world.model_copy(update={"native_graph_binding": world.native_graph_binding.model_copy(update={"status": "inactive"})}))
    with pytest.raises(WorldGraphRetrievalError, match="binding is unavailable"):
        open_span(tmp_path, artifact, span)

pytestmark = pytest.mark.usefixtures("application_state_dsn")
