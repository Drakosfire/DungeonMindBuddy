"""Split code/data deployment through the owning source and prepare boundaries."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server import config
from apps.live_control_server.services import extract_promote, graph_run_registry
from apps.live_control_server.services.graph_ingest_run_registry import graph_ingest_output_root
from apps.live_control_server.services.graph_preview_runner import run_recap_production_extraction
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    resolve_promotable_ingest_run,
)
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    create_recap_source_artifact,
    get_source_artifact,
    load_registered_source_artifact_text,
    source_artifacts_path,
    source_span_index_path,
)
from graph_memory.ingestion.extraction_run import ExtractionRun, ExtractionRunComponentRef


def _ingest_context():
    return SimpleNamespace(
        as_lineage=lambda: {
            "schema": "dm_world_campaign_ingest_context_v1",
            "managed_world_id": "managed-fixture-world",
            "native_world_id": "fixture-world",
            "binding_version": 1,
            "campaign_id": "campaign-a",
            "head_revision_id": "revision:fixture",
            "graph_schema": "dm_graph_v1",
            "graph_payload_sha256": "a" * 64,
        }
    )


@pytest.fixture
def split_roots(tmp_path, monkeypatch):
    code, data = tmp_path / "code", tmp_path / "data"
    code.mkdir()
    data.mkdir()
    hermes = code / "out/hermes-agent/marker"
    hermes.parent.mkdir(parents=True)
    hermes.write_bytes(b"unchanged code dependency")
    monkeypatch.setenv(config.ARTIFACT_DATA_ROOT_ENV, str(data))
    monkeypatch.setattr(extract_promote, "repo_root", lambda: code)
    return code, data, hermes


def _run(code, data, monkeypatch):
    artifact = create_recap_source_artifact(
        code, world_id="fixture-world", campaign_id="campaign-a", session_id="session-1",
        recap_text="# Recap\n\nAlice entered the tower.\n",
    )
    candidate = data / "out/graph_memory/runs/extraction/pinned/candidate_graph.json"
    candidate.parent.mkdir(parents=True)
    index = json.loads(source_span_index_path(code, artifact.source_artifact_id).read_text())
    evidence = {
        "source_ref_id": index["source_ref_id"],
        "source_artifact_id": artifact.source_artifact_id,
        "source_anchor_id": "anchor:alice", "label": "recap",
        "evidence_role": "source_evidence", "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": index["spans"][-1]["source_span_id"],
        "anchor_quotes": ["Alice entered the tower."],
    }
    candidate.write_text(json.dumps({
        "schema": "dmb_candidate_graph_preview_v0", "version": "0.1",
        "preview_id": "preview:pinned", "campaign_id": "campaign-a",
        "session_id": "session-1", "source_artifact_ids": [artifact.source_artifact_id],
        "status": "preview", "nodes": [{
            "node_id": "npc_alice", "label": "Alice", "node_type": "npc",
            "description": "Entered the tower", "importance": "medium",
            "semantic_state": {
                "canon_state": "played_canon", "lifecycle_state": "candidate",
                "evidence_role": "source_evidence", "authority_state": "system_derived",
                "visibility_state": "gm_private",
            },
            "evidence_refs": [evidence], "proposed_action": "create",
            "confidence": "medium", "warnings": [],
        }], "edges": [], "beats": [],
        "diagnostics": {
            "preview_only": True, "extraction_performed": False, "llm_used": False,
            "runtime_connected": False, "plan_connected": False,
            "agent_interaction_connected": False, "corpus_scanned": False,
            "corpus_mutated": False, "facts_promoted": False, "canon_promoted": False,
            "unresolved_evidence_refs": 0, "missing_evidence_objects": 0, "warning_count": 0,
        },
    }))
    files = {
        "source_artifact": data / artifact.uri.removeprefix("repo://"),
        "source_span_index": source_span_index_path(code, artifact.source_artifact_id),
        "candidate_graph": candidate,
    }
    components = {
        kind: ExtractionRunComponentRef(
            kind=kind, uri="repo://" + path.relative_to(data).as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        ) for kind, path in files.items()
    }
    run = ExtractionRun(
        run_id="exact-run", status="reviewable", source_domain="recap",
        source_artifact_id=artifact.source_artifact_id,
        campaign_id="campaign-a", session_id="session-1", components=components,
    )
    requested = []
    def canonical(run_id):
        requested.append(run_id)
        assert run_id == run.run_id
        return run
    monkeypatch.setattr(graph_run_registry.ingest_service, "get_extraction_run", canonical)
    return artifact, run, files, requested


def test_unset_preserves_caller_and_code_world_roots(tmp_path, monkeypatch):
    monkeypatch.delenv(config.ARTIFACT_DATA_ROOT_ENV, raising=False)
    assert config.artifact_data_root(tmp_path) == tmp_path.resolve()
    before_code, before_world = config.repo_root(), config.world_graph_root()
    monkeypatch.setenv(config.ARTIFACT_DATA_ROOT_ENV, str(tmp_path))
    assert config.repo_root() == before_code
    assert config.world_graph_root() == before_world


@pytest.mark.parametrize("value", ["relative", "missing", "file", " "])
def test_bad_explicit_root_fails_without_code_fallback(tmp_path, monkeypatch, value):
    path = value if value in {"relative", " "} else str(tmp_path / value)
    if value == "file":
        Path(path).write_text("not a directory")
    monkeypatch.setenv(config.ARTIFACT_DATA_ROOT_ENV, path)
    with pytest.raises(config.ArtifactDataRootError):
        config.artifact_data_root(tmp_path)
    with pytest.raises(extract_promote.ExtractPromoteError) as exc:
        extract_promote._artifact_root()
    assert exc.value.code == "artifact_data_root_unavailable"
    assert exc.value.status_code == 503


def test_missing_registry_is_not_resolved_from_code(split_roots):
    code, data, _ = split_roots
    with pytest.raises(SourceArtifactRegistryError, match="not found"):
        get_source_artifact(code, "absent")
    assert not source_artifacts_path(code).exists()
    assert not (data / "out").exists()


def test_source_and_future_producer_share_data_root(split_roots, monkeypatch):
    code, data, hermes = split_roots
    original = code / "original.md"
    original.write_text("Retained source.\n")
    artifact = create_recap_source_artifact(
        code, world_id="fixture-world", campaign_id="campaign-a", session_id="session-1", recap_path=original,
    )
    assert source_artifacts_path(code) == data / "out/registries/source_artifacts.json"
    assert load_registered_source_artifact_text(code, artifact.source_artifact_id)[1] == original.read_text()
    assert graph_ingest_output_root(code).is_relative_to(data)
    from tests.test_recap_managed_standing_context import seed_binding
    seed_binding(data,"managed-fixture-world","fixture-world")
    calls = []
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_preview_runner.run_production_extraction",
        lambda request: calls.append(request) or SimpleNamespace(),
    )
    run_recap_production_extraction(
        repo_root=code, campaign_id="campaign-a", session_id="session-1",
        recap_path=original, allow_llm=False, output_dir=Path("out/future"),
        ingest_context=_ingest_context(),
    )
    assert calls[0].repo_root == data
    assert calls[0].output_dir == data / "out/future"
    with pytest.raises(ValueError, match="artifact repository"):
        run_recap_production_extraction(
            repo_root=code, campaign_id="campaign-a", session_id="session-1",
            recap_path=original, output_dir=code / "out/extraction",
            ingest_context=_ingest_context(),
        )
    assert len(calls) == 1
    assert original.read_text() == "Retained source.\n"
    assert hermes.read_bytes() == b"unchanged code dependency"
    assert sorted(p.name for p in (code / "out").iterdir()) == ["hermes-agent"]


def test_exact_run_reaches_real_prepare_boundary_with_separate_data(split_roots, monkeypatch):
    code, data, hermes = split_roots
    artifact, run, files, requested = _run(code, data, monkeypatch)
    before = {kind: path.read_bytes() for kind, path in files.items()}
    binding = SimpleNamespace(
        managed_world_id="managed-a", native_world_id="fixture-world",
        binding_version=1,
    )
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _id: binding)
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    class ReachedNativeBoundary(Exception):
        pass
    def native_boundary(world_id):
        assert world_id == "fixture-world"
        raise ReachedNativeBoundary()
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context", native_boundary)
    from apps.live_control_server.models.extract_promote import ExtractPromotePrepareRequest
    with pytest.raises(ReachedNativeBoundary):
        extract_promote.prepare(ExtractPromotePrepareRequest(
            run_id=run.run_id, managed_world_id="managed-a",
        ))
    assert requested and set(requested) == {run.run_id}
    assert {kind: path.read_bytes() for kind, path in files.items()} == before
    seal = data / "out/graph_memory/runs/promote_seals" / artifact.content_sha256 / "normalized_source.md"
    assert seal.read_bytes() == files["source_artifact"].read_bytes()
    assert hermes.read_bytes() == b"unchanged code dependency"
    assert not (code / "out/registries").exists()
    assert not (code / "out/graph_memory").exists()


@pytest.mark.parametrize("kind", ["source_artifact", "source_span_index", "candidate_graph"])
def test_frozen_component_digest_drift_fails(split_roots, monkeypatch, kind):
    code, data, _ = split_roots
    _, run, files, _ = _run(code, data, monkeypatch)
    files[kind].write_bytes(files[kind].read_bytes() + b" ")
    with pytest.raises(PromotableIngestRunError, match="digest mismatch"):
        resolve_promotable_ingest_run(run.run_id, root=code)


@pytest.mark.parametrize("uri", ["repo://../escaped.json", "/absolute.json", "repo://link/body.json"])
def test_component_path_escape_fails(split_roots, tmp_path, uri):
    code, data, _ = split_roots
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "body.json").write_text("{}")
    (data / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(graph_run_registry.GraphRunRegistryError):
        graph_run_registry._resolve_repo_contained_uri(code, uri)


def test_registry_and_seal_symlink_escape_fail(split_roots, monkeypatch, tmp_path):
    code, data, _ = split_roots
    artifact, run, _, _ = _run(code, data, monkeypatch)
    seal_parent = data / "out/graph_memory/runs/promote_seals"
    outside = tmp_path / "outside"
    outside.mkdir()
    seal_parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(PromotableIngestRunError, match="seal escapes"):
        resolve_promotable_ingest_run(run.run_id, root=code)
    registry = source_artifacts_path(code)
    copied = outside / "registry.json"
    copied.write_bytes(registry.read_bytes())
    registry.unlink()
    registry.symlink_to(copied)
    with pytest.raises(SourceArtifactRegistryError, match="escapes"):
        get_source_artifact(code, artifact.source_artifact_id)
    assert not list(outside.glob("*/normalized_source.md"))


def test_confirm_owner_uses_declared_root_and_rejects_relocation(split_roots, monkeypatch):
    code, data, _ = split_roots
    _, run, files, _ = _run(code, data, monkeypatch)
    from application_state.ingest import service
    seen = []
    def owner(*, uri, sha256):
        seen.append((uri, sha256))
        return SimpleNamespace(kind="unique", run=run)
    monkeypatch.setattr(service, "lookup_extraction_run_by_candidate_component", owner)
    assert extract_promote._candidate_owner_for_locator(str(files["candidate_graph"])) is run
    assert seen[1] == (
        run.components["candidate_graph"].uri, run.components["candidate_graph"].sha256,
    )
    monkeypatch.setenv(config.ARTIFACT_DATA_ROOT_ENV, str(code))
    with pytest.raises(extract_promote.ExtractPromoteError) as exc:
        extract_promote._candidate_owner_for_locator(str(files["candidate_graph"]))
    assert exc.value.code == "candidate_binding_invalid"


def test_source_body_symlink_and_scope_drift_fail(split_roots, monkeypatch, tmp_path):
    code, data, _ = split_roots
    artifact, run, files, _ = _run(code, data, monkeypatch)
    source = files["source_artifact"]
    outside = tmp_path / "same-bytes.md"
    outside.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(outside)
    with pytest.raises(SourceArtifactRegistryError, match="escapes"):
        load_registered_source_artifact_text(code, artifact.source_artifact_id)
    with pytest.raises(PromotableIngestRunError, match="escapes"):
        resolve_promotable_ingest_run(run.run_id, root=code)
    source.unlink()
    source.write_bytes(outside.read_bytes())
    metadata = source_artifacts_path(code)
    doc = json.loads(metadata.read_text())
    doc["records"][0]["session_id"] = "session-2"
    metadata.write_text(json.dumps(doc))
    with pytest.raises(
        SourceArtifactRegistryError,
        match="World-scoped recap SourceArtifact ID does not match its identity",
    ):
        get_source_artifact(code, artifact.source_artifact_id)
    with pytest.raises(
        PromotableIngestRunError,
        match="unknown source_artifact_id",
    ):
        resolve_promotable_ingest_run(run.run_id, root=code)


def test_normal_workspace_commit_and_source_share_data_and_lock_owner(split_roots):
    code, data, hermes = split_roots
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document, get_workspace_document, workspace_documents_path,
    )
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWritePrepareRequest, TiptapMarkdownWriteCommitRequest,
        prepare_tiptap_markdown_write, commit_tiptap_markdown_write,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document, resolve_worldbuilding_source_span,
    )
    doc = create_workspace_document(
        code, title="Lore", campaign_id="world-a", kind="worldbuilding_source",
        source_domain="worldbuilding", document_class="lore",
        authority_state="draft", visibility_state="internal",
    )
    markdown = "# Lore\n\nThe tower watches the river.\n"
    prepared = prepare_tiptap_markdown_write(
        root=code, request=TiptapMarkdownWritePrepareRequest(
            document_id=doc.document_id, markdown=markdown, expected_revision=doc.revision,
        ),
    )
    assert prepared.writer_ok
    commit_tiptap_markdown_write(
        root=code, request=TiptapMarkdownWriteCommitRequest(
            document_id=doc.document_id, markdown=markdown,
            expected_revision=doc.revision, writer_confirm_token=prepared.writer_confirm_token,
        ),
    )
    committed = get_workspace_document(code, doc.document_id)
    artifact = create_source_artifact_from_workspace_document(
        code, document_id=doc.document_id, expected_revision=committed.revision,
    )
    assert artifact.workspace_document_revision == committed.revision
    assert artifact.workspace_document_id == committed.document_id
    assert artifact.uri == "repo://" + committed.target_relpath
    assert workspace_documents_path(code) == data / "out/registries/workspace_documents.json"
    assert (data / committed.target_relpath).read_text() == markdown
    assert load_registered_source_artifact_text(code, artifact.source_artifact_id)[1] == markdown
    resolve_worldbuilding_source_span(code, artifact.source_artifact_id)
    from apps.live_control_server.services.worldbuilding_source_span_read import read_admitted_worldbuilding_span
    index = json.loads(source_span_index_path(code, artifact.source_artifact_id).read_text())
    result = read_admitted_worldbuilding_span(
        root=code, source_artifact_id=artifact.source_artifact_id,
        source_span_ref_id=index["spans"][-1]["source_span_id"],
        graph_content_sha256=artifact.content_sha256, max_chars=1000, anchor_id="anchor:workspace",
    )
    assert result.content == "The tower watches the river."
    assert (data / "out/registries/.locks" / f"workspace_document.{doc.document_id}.lock").is_file()
    assert hermes.read_bytes() == b"unchanged code dependency"
    assert sorted(p.name for p in (code / "out").iterdir()) == ["hermes-agent"]


def test_packaging_writes_only_under_declared_root(split_roots, monkeypatch, tmp_path):
    code, data, hermes = split_roots
    monkeypatch.chdir(code)
    from src.graph_memory.extraction import graph_ingest_packaging as packaging
    from apps.live_control_server.services.recap_graph_preview_ingest import _new_run_dir
    output = packaging.ensure_output_dir(Path("out/graph_memory/runs/new"))
    assert output == data / "out/graph_memory/runs/new"
    packaging.write_json(output / "candidate.json", {"unchanged": "payload"})
    assert json.loads((output / "candidate.json").read_text()) == {"unchanged": "payload"}
    assert _new_run_dir(data, "campaign-a", 1).is_relative_to(data)
    with pytest.raises(ValueError, match="escapes"):
        _new_run_dir(data, "../outside", 1)
    outside = tmp_path / "outside"
    outside.mkdir()
    (output / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="outside"):
        packaging.write_json(output / "escape/never.json", {})
    with pytest.raises(ValueError, match="outside"):
        packaging.ensure_output_dir(Path("out/graph_memory/runs/new/escape/nested"))
    assert not list(outside.iterdir())
    assert hermes.read_bytes() == b"unchanged code dependency"


def test_direct_extraction_rejects_split_output_before_run_creation(split_roots, monkeypatch):
    code, data, _ = split_roots
    from src.graph_memory.extraction.graph_preview_runner import (
        ProductionExtractionRequest, _run_output_dir, run_production_extraction,
    )
    monkeypatch.setattr(
        graph_run_registry.ingest_service, "get_extraction_run",
        lambda *_args: pytest.fail("bad output reached APP-STATE"),
    )
    with pytest.raises(ValueError, match="escapes"):
        run_production_extraction(ProductionExtractionRequest(
            repo_root=code, source=None, profile_id="unused", profile_version="unused",
            output_dir=code / "out/new",
        ))
    assert _run_output_dir(data, "run", Path("out/new")) == data / "out/new/run"


def test_unreadable_explicit_root_does_not_fallback(split_roots, monkeypatch):
    code, _data, _ = split_roots
    monkeypatch.setattr(config.os, "access", lambda *_args: False)
    with pytest.raises(config.ArtifactDataRootError):
        config.artifact_data_root(code)
