from types import SimpleNamespace
import hashlib
import json
import os
import subprocess
import sys

import pytest

from apps.live_control_server.services import graph_run_registry as runs
from apps.live_control_server.services import managed_world_graph_projection as binding
from apps.live_control_server.services import worldbuilding_source_span_read as reader
from apps.live_control_server.services.source_artifact_registry import (
    create_source_artifact_from_workspace_document,
    source_span_index_path,
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
    ExtractionRunComponentRef,
    ExtractionRunComponentKind,
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


def fixture_source(root):
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
    index_bytes = source_span_index_path(root, artifact.source_artifact_id).read_bytes()
    (directory / "spans.json").write_bytes(index_bytes)
    (directory / "candidate.json").write_text('{"nodes":[],"edges":[]}')
    components = {
        kind.value: ExtractionRunComponentRef(
            kind=kind,
            uri="repo://" + str(path.relative_to(root)),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for kind, path in [
            (ExtractionRunComponentKind.SOURCE_ARTIFACT, directory / "source.md"),
            (ExtractionRunComponentKind.SOURCE_SPAN_INDEX, directory / "spans.json"),
            (ExtractionRunComponentKind.CANDIDATE_GRAPH, directory / "candidate.json"),
        ]
    }
    runs.create_extraction_run(
        root,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=artifact.campaign_id,
        components=components,
        status=ExtractionRunStatus.REVIEWABLE,
    )
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
    doc, artifact, span, directory = fixture_source(tmp_path)
    monkeypatch.setattr(
        binding,
        "resolve_managed_world_binding",
        lambda root, world: SimpleNamespace(native_world_id="native-world"),
    )
    assert open_span(tmp_path, artifact, span).content == "The tower watches the river."
    save(tmp_path, doc, "# Lore\n\nThe tower has fallen.\n")
    assert open_span(tmp_path, artifact, span).content == "The tower watches the river."
    script = """
import sys
from pathlib import Path
from apps.live_control_server.services.worldbuilding_source_span_read import read_admitted_worldbuilding_span
result = read_admitted_worldbuilding_span(root=Path(sys.argv[1]),source_artifact_id=sys.argv[2],
    source_span_ref_id=sys.argv[3],graph_content_sha256=sys.argv[4],max_chars=1000,anchor_id='anchor:accepted')
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
    (directory / "source.md").write_text("tampered")
    with pytest.raises(WorldGraphRetrievalError, match="digest mismatch"):
        open_span(tmp_path, artifact, span)


def test_missing_historical_snapshot_never_opens_current_text(
    tmp_path, monkeypatch, application_state_dsn
):
    doc, artifact, span, directory = fixture_source(tmp_path)
    monkeypatch.setattr(
        binding,
        "resolve_managed_world_binding",
        lambda root, world: SimpleNamespace(native_world_id="native-world"),
    )
    save(tmp_path, doc, "# Lore\n\nThe tower has fallen.\n")
    (directory / "source.md").unlink()
    with pytest.raises(WorldGraphRetrievalError, match="missing"):
        open_span(tmp_path, artifact, span)
