from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from apps.live_control_server.services import source_artifact_registry as inputs
from application_state.source.types import SourceMarkdownRecord
from apps.live_control_server.services import graph_run_registry as runs
from apps.live_control_server.services import worldbuilding_source_span_read as reader
from apps.live_control_server.services.source_artifact_registry import (
    create_source_artifact_from_workspace_document,
    source_span_index_path,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document,
)
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
from graph_memory.ingestion.extraction_run import ExtractionRunStatus
from graph_memory.retrieval.errors import WorldGraphRetrievalError
from graph_memory.retrieval.models import WorldGraphRetrievalSnapshot
from graph_memory.source_span import build_source_span_index_for_text

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _save_source(root, document, markdown: str):
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document.document_id,
            markdown=markdown,
            expected_revision=document.revision,
        ),
    )
    assert prepared.writer_ok
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document.document_id,
            markdown=markdown,
            expected_revision=document.revision,
            writer_confirm_token=prepared.writer_confirm_token,
        ),
    )
    return get_workspace_document(root, document.document_id)


def _registered_source(tmp_path, monkeypatch):
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )

    registry_root = tmp_path / "managed-registry"
    registry_root.mkdir()
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(registry_root))
    world = create_world_container(registry_root, name="Managed World")
    registry_path = registry_root / "out/registries/world_containers.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["records"][0]["native_graph_binding"] = {
        "native_world_id": "native-world",
        "binding_version": 1,
        "status": "active",
        "validated_at": "2026-10-14T00:00:00Z",
        "validated_head_revision_id": "rev:accepted",
    }
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    markdown = "# Lore\n\nThe tower watches the river.\n"
    document = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id=world.world_id,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    document = _save_source(tmp_path, document, markdown)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=document.document_id,
        expected_revision=document.revision,
    )
    return document, artifact, markdown


def _durable_record(artifact: GraphMemorySourceArtifact, markdown: str):
    return SourceMarkdownRecord(
        source_revision_id=uuid4(),
        source_artifact_id=artifact.source_artifact_id,
        source_domain=str(artifact.source_domain),
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        world_id=artifact.world_id,
        content_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        media_type="text/markdown",
        encoding="utf-8",
        markdown=markdown,
        lineage={},
        created_at=datetime.now(UTC),
    )


def _span_id(artifact: GraphMemorySourceArtifact, markdown: str) -> str:
    index = build_source_span_index_for_text(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256 or "",
        text=markdown,
    )
    return index.spans[-1].source_span_id


def _open(root, artifact, span_id, batch=None):
    snapshot = WorldGraphRetrievalSnapshot(
        world_id="native-world",
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
        source_span_ref_id=span_id,
        graph_content_sha256=artifact.content_sha256,
        max_chars=1000,
        anchor_id="anchor:accepted",
        snapshot=snapshot,
        graph_artifact=artifact,
        _source_batch=batch,
    )


def test_worldbuilding_registration_owns_storage_not_run_creation(monkeypatch, tmp_path):
    from application_state.source import service as sources
    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    stored = sources.get_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256,
    )
    assert stored is not None
    assert stored.markdown == markdown
    assert stored.world_id == artifact.world_id
    monkeypatch.setattr(sources, "persist_source_markdown", lambda **kwargs: pytest.fail("run adopted source again"))
    monkeypatch.setattr(runs.ingest_service, "create_extraction_run", lambda run: run)
    run = runs.create_extraction_run(
        tmp_path, source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding", campaign_id=artifact.campaign_id,
        components={}, status=ExtractionRunStatus.DRAFT,
    )
    assert run.source_artifact_id == artifact.source_artifact_id


def test_missing_durable_body_prevents_run_creation(monkeypatch, tmp_path, application_state_dsn):
    import psycopg
    _document, artifact, _markdown = _registered_source(tmp_path, monkeypatch)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (artifact.source_artifact_id,))
    monkeypatch.setattr(runs.ingest_service, "create_extraction_run", lambda run: pytest.fail("created run without durable input"))
    with pytest.raises(runs.GraphRunRegistryError, match="durable worldbuilding source"):
        runs.create_extraction_run(
            tmp_path, source_artifact_id=artifact.source_artifact_id,
            source_domain="worldbuilding", campaign_id=artifact.campaign_id,
            components={}, status=ExtractionRunStatus.DRAFT,
        )


@pytest.mark.parametrize("field", ["world_id", "campaign_id", "session_id", "source_domain", "content_sha256"])
def test_run_rejects_source_binding_drift_before_creation(monkeypatch, tmp_path, field):
    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    changed = artifact.model_copy(update={field: "changed"})
    monkeypatch.setattr(runs, "load_registered_source_artifact_bytes", lambda *args: (changed, markdown.encode()))
    monkeypatch.setattr(runs.ingest_service, "create_extraction_run", lambda run: pytest.fail("created run from changed binding"))
    with pytest.raises(runs.GraphRunRegistryError, match="binding changed"):
        runs.create_extraction_run(
            tmp_path, source_artifact_id=artifact.source_artifact_id,
            source_domain="worldbuilding", campaign_id=artifact.campaign_id,
            components={}, status=ExtractionRunStatus.DRAFT,
        )


def test_historical_span_reads_from_durable_body_after_workspace_edit_and_sidecar_loss(
    monkeypatch, tmp_path
):
    document, artifact, original = _registered_source(tmp_path, monkeypatch)
    record = _durable_record(artifact, original)
    monkeypatch.setattr(
        inputs.source_service,
        "get_source_markdown",
        lambda **kwargs: record
        if kwargs
        == {
            "source_artifact_id": artifact.source_artifact_id,
            "content_sha256": artifact.content_sha256,
        }
        else pytest.fail("lookup must bind the exact artifact and digest"),
    )

    span_id = _span_id(artifact, original)
    _save_source(tmp_path, document, "# Lore\n\nThe tower has fallen.\n")
    source_span_index_path(tmp_path, artifact.source_artifact_id).unlink()

    result = _open(tmp_path, artifact, span_id)
    assert result.content == "The tower watches the river."
    assert result.source_span_ref_id == span_id
    assert result.content_sha256 == artifact.content_sha256
    assert result.line_start == 3
    assert result.line_end == 3


@pytest.mark.parametrize(
    "updates",
    [
        {"world_id": "foreign-world"},
        {"campaign_id": "foreign-campaign"},
        {"source_domain": "recap"},
        {"content_sha256": "0" * 64},
        {"markdown": "# Forged\n"},
    ],
)
def test_durable_source_mismatch_fails_closed(monkeypatch, tmp_path, updates):
    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    record = _durable_record(artifact, markdown).model_copy(update=updates)
    monkeypatch.setattr(
        inputs.source_service,
        "get_source_markdown",
        lambda **_kwargs: record,
    )

    with pytest.raises(WorldGraphRetrievalError, match="database source body"):
        _open(tmp_path, artifact, _span_id(artifact, markdown))


def test_batch_reuses_validated_body_index_and_revalidates_next_batch(monkeypatch, tmp_path):
    from unittest.mock import Mock
    document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    record = _durable_record(artifact, markdown)
    load = Mock(return_value=record)
    index = Mock(wraps=reader.build_source_span_index_for_text)
    monkeypatch.setattr(inputs.source_service, 'get_source_markdown', load)
    monkeypatch.setattr(reader, 'build_source_span_index_for_text', index)
    batch = reader.WorldbuildingSourceReadBatch()
    span_id = _span_id(artifact, markdown)
    before = _open(tmp_path, artifact, span_id, batch)
    _save_source(tmp_path, document, '# Lore\n\nA newer draft.\n')
    source_span_index_path(tmp_path, artifact.source_artifact_id).unlink()
    after = _open(tmp_path, artifact, span_id, batch)
    assert after.model_dump() == before.model_dump()
    assert load.call_count == index.call_count == 1
    # A new operation must not inherit cached success or bypass byte verification.
    load.return_value = record.model_copy(update={'markdown': '# Corrupted\n'})
    with pytest.raises(WorldGraphRetrievalError, match='database source body digest'):
        _open(tmp_path, artifact, span_id, reader.WorldbuildingSourceReadBatch())
    assert load.call_count == 2


def test_batch_still_checks_artifact_lineage_on_every_span(monkeypatch, tmp_path):
    from unittest.mock import Mock
    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    load = Mock(return_value=_durable_record(artifact, markdown))
    monkeypatch.setattr(inputs.source_service, 'get_source_markdown', load)
    batch = reader.WorldbuildingSourceReadBatch()
    span_id = _span_id(artifact, markdown)
    _open(tmp_path, artifact, span_id, batch)
    monkeypatch.setattr(reader, 'get_source_artifact', lambda *_: artifact.model_copy(update={'world_id': 'foreign'}))
    with pytest.raises(WorldGraphRetrievalError):
        _open(tmp_path, artifact, span_id, batch)
    assert load.call_count == 1


def test_batch_failed_validation_is_not_cached_and_metadata_keys_are_distinct(monkeypatch, tmp_path):
    from unittest.mock import Mock
    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    valid = _durable_record(artifact, markdown)
    load = Mock(side_effect=[valid.model_copy(update={'world_id': 'foreign'}), valid, valid])
    monkeypatch.setattr(inputs.source_service, 'get_source_markdown', load)
    batch = reader.WorldbuildingSourceReadBatch()
    span_id = _span_id(artifact, markdown)
    with pytest.raises(WorldGraphRetrievalError, match='database source body scope'):
        _open(tmp_path, artifact, span_id, batch)
    assert _open(tmp_path, artifact, span_id, batch).content == 'The tower watches the river.'
    assert load.call_count == 2
    # Even non-lineage artifact metadata changes cannot hit the old key.
    changed = artifact.model_copy(update={'title': 'Changed title'})
    batch.read(changed, artifact.content_sha256)
    assert load.call_count == 3


def test_unavailable_immutable_source_does_not_poison_batch_cache(monkeypatch, tmp_path):
    from unittest.mock import Mock
    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    load = Mock(side_effect=[None, _durable_record(artifact, markdown)])
    monkeypatch.setattr(inputs.source_service, 'get_source_markdown', load)
    batch = reader.WorldbuildingSourceReadBatch()
    with pytest.raises(WorldGraphRetrievalError, match="missing from the database"):
        batch.read(artifact, artifact.content_sha256)
    assert batch.read(artifact, artifact.content_sha256)[0] == markdown
    assert load.call_count == 2


@pytest.mark.parametrize("failure,status", [("missing", 409), ("unavailable", 503), ("corrupt", 409)])
def test_source_failure_never_falls_back_to_valid_markdown(monkeypatch, tmp_path, failure, status):
    from pathlib import Path
    from application_state.errors import ApplicationStateUnavailableError

    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    if failure == "unavailable":
        def load(**kwargs):
            raise ApplicationStateUnavailableError("test-owned source store outage")
    else:
        record = None if failure == "missing" else _durable_record(artifact, markdown).model_copy(update={"markdown": "corrupt"})
        def load(**kwargs):
            return record
    monkeypatch.setattr(inputs.source_service, "get_source_markdown", load)
    original = Path.open
    def deny_markdown(path, *args, **kwargs):
        if path.suffix == ".md":
            pytest.fail("an input failure must not fall back to Markdown")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", deny_markdown)
    with pytest.raises(WorldGraphRetrievalError) as error:
        _open(tmp_path, artifact, _span_id(artifact, markdown))
    assert error.value.status_code == status


def test_source_metadata_outage_is_not_reported_as_missing(monkeypatch, tmp_path):
    _document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    def unavailable(*args, **kwargs):
        raise inputs.SourceArtifactRegistryError("test-owned metadata outage", status_code=503)
    monkeypatch.setattr(reader, "get_source_artifact", unavailable)
    with pytest.raises(WorldGraphRetrievalError) as error:
        _open(tmp_path, artifact, _span_id(artifact, markdown))
    assert error.value.status_code == 503
    assert error.value.code == "source_unavailable"
