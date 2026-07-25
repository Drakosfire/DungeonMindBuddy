"""Unit tests for resolve_promotable_ingest_run (PR011A1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    assess_manifest_promotability,
    is_under_ingest_runs,
    is_under_world_store,
    resolve_promotable_ingest_run,
)
from tests.test_live_extract_promote_api import (
    CAMPAIGN_ID,
    SESSION_ID,
    _candidate_graph_payload,
    _write_promotable_run,
)

def test_resolve_promotable_ingest_run_happy(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, digest, source = _write_promotable_run(repo)

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.run_id == run_id
    assert resolved.campaign_id == CAMPAIGN_ID
    assert resolved.session_id == SESSION_ID
    assert resolved.source_revision_id == digest
    assert resolved.source_artifact_id == "artifact:recap:longmont-c2:session-22"
    assert resolved.extraction_profile == "category_v1"
    assert resolved.normalized_recap_path == source.resolve()
    assert resolved.candidate_graph_path.is_file()
    assert resolved.preview_union_store_path.is_file()
    assert resolved.sealed_source_uri.startswith("repo://out/graph_memory/runs/")
    assert is_under_ingest_runs(resolved.normalized_recap_path, root=repo)


def test_resolve_unknown_run(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    _write_promotable_run(repo)
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run("graph-ingest:missing", root=repo)
    assert exc.value.code == "run_not_found"
    assert exc.value.status_code == 404


def test_resolve_scope_mismatch(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    mismatched = "graph-ingest:other:session-1:x"
    _write_promotable_run(repo, run_id=mismatched)
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(mismatched, root=repo)
    assert exc.value.code == "run_scope_mismatch"


def test_resolve_rejects_artifact_outside_run_dir(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    escape = repo / "out/graph_memory/runs/longmont-c2/other/escaped.md"
    escape.parent.mkdir(parents=True, exist_ok=True)
    escape.write_text("escaped\n", encoding="utf-8")
    manifest_path = (
        repo
        / "out/graph_memory/runs/longmont-c2/session-22/fixture-promote"
        / "graph_ingest_run_manifest.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"]["normalized_recap"]["uri"] = (
        "out/graph_memory/runs/longmont-c2/other/escaped.md"
    )
    payload["source"]["normalized_recap_path"] = (
        "out/graph_memory/runs/longmont-c2/other/escaped.md"
    )
    payload["source"]["normalized_recap_sha256"] = (
        f"sha256:{hashlib.sha256(escape.read_bytes()).hexdigest()}"
    )
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert any("escapes" in d for d in exc.value.diagnostics) or "escapes" in str(
        exc.value
    )


def test_resolve_rejects_missing_source_artifact_id(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(
        repo, omit_source_artifact_id=True
    )
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "source_artifact_id" in str(exc.value)


def test_resolve_rejects_missing_preview_union_store(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo, omit_preview=True)
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "preview_union_store" in str(exc.value)


def test_resolve_rejects_deleted_preview_union_store(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    resolved.preview_union_store_path.unlink()
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"


def test_resolve_admits_configured_non_default_registry_root(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    custom_rel = "sandbox/custom_ingest_runs"
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, custom_rel)
    run_id = "graph-ingest:longmont-c2:session-22:custom-root"
    _write_promotable_run(repo, run_id=run_id, runs_rel=custom_rel)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert custom_rel in resolved.sealed_source_uri
    assert is_under_ingest_runs(resolved.normalized_recap_path, root=repo) is True


def test_configured_root_artifact_not_under_default_when_env_differs(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    custom_rel = "sandbox/custom_ingest_runs"
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, custom_rel)
    run_id = "graph-ingest:longmont-c2:session-22:custom-root"
    _write_promotable_run(repo, run_id=run_id, runs_rel=custom_rel)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    source = resolved.normalized_recap_path
    # Default hard-coded root must not admit a custom-root artifact when env differs.
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    assert is_under_ingest_runs(source, root=repo) is False


def test_world_store_detection(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    worlds = repo / "out/graph_memory/worlds/eldyrwild/head.json"
    worlds.parent.mkdir(parents=True, exist_ok=True)
    worlds.write_text("{}\n", encoding="utf-8")
    runs = repo / "out/graph_memory/runs/x/y/z.md"
    runs.parent.mkdir(parents=True, exist_ok=True)
    runs.write_text("ok\n", encoding="utf-8")

    monkeypatch.setattr(
        "apps.live_control_server.services.promotable_ingest_run.world_graph_root",
        lambda: repo / "out/graph_memory/worlds",
    )
    assert is_under_world_store(worlds, root=repo) is True
    assert is_under_world_store(runs, root=repo) is False
    assert is_under_ingest_runs(runs, root=repo) is True


def test_assess_manifest_promotability_uses_prepare_resolver_seam(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    payload = json.loads(resolved.manifest_path.read_text(encoding="utf-8"))
    registry_root = (repo / "out/graph_memory/runs").resolve()

    ok, reason = assess_manifest_promotability(
        repo=repo,
        manifest_path=resolved.manifest_path,
        payload=payload,
        registry_root=registry_root,
    )
    assert ok is True
    assert reason is None

    # Missing candidate artifact: health flags alone must not advertise promotable.
    payload["artifacts"].pop("candidate_graph", None)
    resolved.candidate_graph_path.unlink(missing_ok=True)
    bad, bad_reason = assess_manifest_promotability(
        repo=repo,
        manifest_path=resolved.manifest_path,
        payload=payload,
        registry_root=registry_root,
    )
    assert bad is False
    assert bad_reason is not None
    assert "candidate_graph" in bad_reason


def test_resolve_rejects_alias_shaped_candidate_semantic_state(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    payload = json.loads(resolved.candidate_graph_path.read_text(encoding="utf-8"))
    for node in payload.get("nodes") or []:
        node["semantic_state"] = {
            "canon_status": "preview_only",
            "lifecycle": "candidate",
            "memory_status": "uncommitted",
        }
    for edge in payload.get("edges") or []:
        edge["semantic_state"] = {
            "canon_status": "preview_only",
            "lifecycle": "candidate",
            "memory_status": "uncommitted",
        }
    resolved.candidate_graph_path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "semantic_state" in str(exc.value).lower() or "typed" in str(exc.value).lower()

    manifest_payload = json.loads(resolved.manifest_path.read_text(encoding="utf-8"))
    ok, reason = assess_manifest_promotability(
        repo=repo,
        manifest_path=resolved.manifest_path,
        payload=manifest_payload,
        registry_root=(repo / "out/graph_memory/runs").resolve(),
    )
    assert ok is False
    assert reason is not None


def test_resolve_rejects_stub_only_evidence_refs(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    payload = json.loads(resolved.candidate_graph_path.read_text(encoding="utf-8"))
    stub = {
        "source_span_ref_id": "session-22:recap:paragraph:006",
        "anchor_quotes": ["quote"],
    }
    for node in payload.get("nodes") or []:
        node["evidence_refs"] = [dict(stub)]
    for edge in payload.get("edges") or []:
        edge["evidence_refs"] = [dict(stub)]
    for beat in payload.get("beats") or []:
        beat["evidence_refs"] = [dict(stub)]
    for write in payload.get("proposed_writes") or []:
        write["evidence_refs"] = [dict(stub)]
    resolved.candidate_graph_path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "source_ref_id" in str(exc.value) or "typed" in str(exc.value).lower()

    manifest_payload = json.loads(resolved.manifest_path.read_text(encoding="utf-8"))
    ok, reason = assess_manifest_promotability(
        repo=repo,
        manifest_path=resolved.manifest_path,
        payload=manifest_payload,
        registry_root=(repo / "out/graph_memory/runs").resolve(),
    )
    assert ok is False
    assert reason is not None


def test_resolve_accepts_stamped_promote_evidence_refs(
    tmp_path: Path, monkeypatch
) -> None:
    """Happy-path fixture already has full EvidenceRef; resolve must stay green."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(repo)
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    payload = json.loads(resolved.candidate_graph_path.read_text(encoding="utf-8"))
    ref = payload["nodes"][0]["evidence_refs"][0]
    assert ref["source_ref_id"]
    assert ref["source_artifact_id"]
    assert ref["can_open_source"] is True
    assert ref["can_highlight_span"] is True
    assert resolved.run_id == run_id


def test_resolve_retains_declared_registry_context_path(
    tmp_path: Path, monkeypatch
) -> None:
    """Manifest-declared registry URI must survive on PromotableIngestRun."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _digest, _source = _write_promotable_run(
        repo,
        registry_context=_candidate_graph_payload(),
        registry_filename="party_standing_context.json",
    )
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.registry_context_graph_path is not None
    assert resolved.registry_context_graph_path.name == "party_standing_context.json"
    assert resolved.registry_context_graph_path.is_file()


def test_resolve_rejects_blank_campaign_declared_registry(
    tmp_path: Path, monkeypatch
) -> None:
    """Declared registry without campaign_id must fail closed (no inherit)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    unscoped = _candidate_graph_payload()
    unscoped.pop("campaign_id", None)
    run_id, _digest, _source = _write_promotable_run(
        repo,
        registry_context=unscoped,
        registry_filename="party_standing_context.json",
    )
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "campaign_id is required" in str(exc.value)


def _write_reviewable_extraction_run(
    repo: Path,
    *,
    status: str = "reviewable",
    campaign_id: str | None = CAMPAIGN_ID,
    invent_session_in_candidate: bool = False,
    candidate_campaign_id: str | None = ...,  # type: ignore[assignment]
    pin_noncanonical_span_index: bool = False,
) -> tuple[str, Path]:
    """Build a canonical worldbuilding ExtractionRun through its owning services.

    Nothing is hand-written into a registry file: the workspace document, its
    committed bytes, the SourceArtifact, the span index, and every run status
    transition go through the same code paths production uses, so the fixture
    cannot drift away from the registry's own validators.

    ``campaign_id=None`` produces a campaignless worldbuilding run/artifact
    (worldbuilding SourceArtifacts may omit campaign). The workspace document
    still needs a storage campaign for the file write; the artifact/run are
    then rewritten to drop that campaign before promotion.

    ``pin_noncanonical_span_index=True`` writes a second valid index for the same
    artifact (different span IDs) and pins the ExtractionRun component to that
    path — used to prove review/prepare load the run-pinned URI, not the
    registry canonical path.
    """
    from apps.live_control_server.services.graph_run_registry import (
        create_extraction_run,
        supersede_extraction_run,
        update_extraction_run_status,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryDocument,
        create_source_artifact_from_workspace_document,
        get_source_artifact,
        source_artifacts_path,
        source_span_index_relpath,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )
    from graph_memory.ingestion.extraction_run import (
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunStatus,
    )
    from graph_memory.source_span import (
        source_span_index_to_dict,
    )
    from src.live_play.live_store import load_json, write_json

    if candidate_campaign_id is ...:
        candidate_campaign_id = campaign_id

    storage_campaign = campaign_id or CAMPAIGN_ID
    document = create_workspace_document(
        repo,
        title="Worldbuilding lore",
        campaign_id=storage_campaign,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        repo, document.document_id, expected_revision=document.revision
    )
    source = repo / committed.target_relpath
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "# Lore\n\nWorldbuilding source for promote.\n\nA second paragraph.\n",
        encoding="utf-8",
    )
    artifact = create_source_artifact_from_workspace_document(
        repo, document_id=committed.document_id, expected_revision=committed.revision
    )

    if campaign_id is None:
        # Worldbuilding SourceArtifacts may omit campaign; rewrite the registry
        # record so the ExtractionRun binds to a truly campaignless artifact.
        path = source_artifacts_path(repo)
        document_payload = SourceArtifactRegistryDocument.model_validate(load_json(path))
        rewritten = []
        for row in document_payload.records:
            if row.source_artifact_id == artifact.source_artifact_id:
                rewritten.append(
                    row.model_copy(update={"campaign_id": None, "world_id": None})
                )
            else:
                rewritten.append(row)
        write_json(
            path,
            SourceArtifactRegistryDocument(
                schema_version=document_payload.schema_version,
                records=rewritten,
            ).model_dump(mode="json"),
        )
        artifact = get_source_artifact(repo, artifact.source_artifact_id)
        assert artifact.campaign_id is None

    span_rel = source_span_index_relpath(artifact.source_artifact_id)
    span_path = repo / span_rel
    span_index = json.loads(span_path.read_text(encoding="utf-8"))
    source_lines = source.read_text(encoding="utf-8").splitlines()
    span_ref_id = str(span_index["spans"][0]["source_span_id"])
    for span in span_index["spans"]:
        start = int(span["start_line"])
        end = int(span["end_line"])
        paragraph = "\n".join(source_lines[start - 1 : end])
        if "Worldbuilding source for promote." in paragraph:
            span_ref_id = str(span["source_span_id"])
            break

    run_dir = repo / "out" / "graph_memory" / "runs" / "extraction" / "wb1"
    run_dir.mkdir(parents=True, exist_ok=True)

    if pin_noncanonical_span_index:
        # Whole-document span → different stable span IDs than the registry
        # paragraph index, but still digest-valid for the same artifact bytes.
        from graph_memory.source_span import (
            SOURCE_SPAN_INDEX_SCHEMA,
            SOURCE_SPAN_INDEX_VERSION,
            SourceSpanIndex,
            SourceSpanIndexEntry,
            build_stable_source_span_id,
            document_source_ref_id,
        )

        digest = artifact.content_sha256 or ""
        n_lines = max(1, len(source_lines))
        source_ref = document_source_ref_id(artifact.source_artifact_id)
        alt_span_id = build_stable_source_span_id(
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=digest,
            start_line=1,
            end_line=n_lines,
        )
        canonical_ids = {str(span["source_span_id"]) for span in span_index["spans"]}
        assert alt_span_id not in canonical_ids
        alt_index = SourceSpanIndex(
            schema=SOURCE_SPAN_INDEX_SCHEMA,
            version=SOURCE_SPAN_INDEX_VERSION,
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=digest,
            source_ref_id=source_ref,
            spans=(
                SourceSpanIndexEntry(
                    source_span_id=alt_span_id,
                    source_ref_id=source_ref,
                    source_artifact_id=artifact.source_artifact_id,
                    content_sha256=digest,
                    start_line=1,
                    end_line=n_lines,
                ),
            ),
        )
        alt_rel = "out/graph_memory/runs/extraction/wb1/alt_source_span_index.json"
        alt_path = repo / alt_rel
        write_json(alt_path, source_span_index_to_dict(alt_index))
        span_component_uri = f"repo://{alt_rel}"
        span_component_path = alt_path
        span_ref_id = alt_span_id
    else:
        span_component_uri = f"repo://{span_rel}"
        span_component_path = span_path

    candidate_payload = _candidate_graph_payload(
        campaign_id=candidate_campaign_id or "",
        session_id="session-99" if invent_session_in_candidate else "",
    )
    if not invent_session_in_candidate:
        candidate_payload["session_id"] = None
    if candidate_campaign_id is None:
        candidate_payload["campaign_id"] = None
    candidate_payload["source_artifact_ids"] = [artifact.source_artifact_id]
    # Stamp the real worldbuilding profile default — not played_canon. BLD-07
    # narrowed worldbuilding to inspect-only; fixtures must not hide the gate.
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
        WORLDBUILDING_PLUMBING_PROFILE,
    )

    worldbuilding_semantic = dict(WORLDBUILDING_PLUMBING_PROFILE.default_semantic_state)
    for holder in (
        *(candidate_payload.get("nodes") or []),
        *(candidate_payload.get("edges") or []),
    ):
        holder["semantic_state"] = dict(worldbuilding_semantic)
        for ref in holder.get("evidence_refs") or []:
            ref["source_artifact_id"] = artifact.source_artifact_id
            ref["source_span_ref_id"] = span_ref_id
            ref["anchor_quotes"] = ["Worldbuilding source for promote."]

    candidate_path = run_dir / "candidate_graph.json"
    candidate_path.write_text(
        json.dumps(candidate_payload, indent=2) + "\n", encoding="utf-8"
    )

    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=artifact.uri,
            sha256=artifact.content_sha256,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=span_component_uri,
            sha256=_digest(span_component_path),
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=f"repo://{candidate_path.relative_to(repo).as_posix()}",
            sha256=_digest(candidate_path),
        ),
    }

    run = create_extraction_run(
        repo,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=campaign_id,
        session_id=None,
        profile_id="worldbuilding_plumbing_v0@0.1",
    )
    reachable = [
        ExtractionRunStatus.PREPARED,
        ExtractionRunStatus.EXTRACTED,
        ExtractionRunStatus.VALIDATED,
        ExtractionRunStatus.REVIEWABLE,
    ]
    stop_at = (
        ExtractionRunStatus.REVIEWABLE
        if status == "superseded"
        else ExtractionRunStatus(status)
    )
    for step in reachable:
        run = update_extraction_run_status(
            repo,
            run.run_id,
            status=step,
            expected_revision=run.revision,
            components=components if step == ExtractionRunStatus.PREPARED else None,
        )
        if step == stop_at:
            break
    if status == "superseded":
        supersede_extraction_run(repo, run.run_id, expected_revision=run.revision)
    return run.run_id, source


def test_resolve_reviewable_worldbuilding_extraction_run(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, source = _write_reviewable_extraction_run(repo)

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.run_id == run_id
    assert resolved.campaign_id == CAMPAIGN_ID
    assert resolved.session_id == ""
    assert resolved.source_domain == "worldbuilding"
    assert resolved.source_artifact_id.startswith("artifact:worldbuilding:")
    assert resolved.source_revision_id == f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    assert resolved.candidate_graph_path.is_file()
    assert resolved.sealed_source_uri.startswith("repo://out/graph_memory/runs/promote_seals/")
    assert resolved.normalized_recap_path.is_file()
    assert resolved.source_span_index_path is not None
    assert resolved.source_span_index_path.is_file()
    assert "session_scope=null" in resolved.diagnostics
    # Registry-owned source bytes are sealed by digest, not read in place, and the
    # run's own artifact directory is never mutated to make that possible.
    assert resolved.normalized_recap_path != source.resolve()
    assert resolved.normalized_recap_path.read_bytes() == source.read_bytes()
    assert not (resolved.run_dir / "normalized_source.md").exists()


def test_resolve_extraction_run_seal_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, _source = _write_reviewable_extraction_run(repo)

    first = resolve_promotable_ingest_run(run_id, root=repo)
    stat_before = first.normalized_recap_path.stat()
    second = resolve_promotable_ingest_run(run_id, root=repo)
    assert second.sealed_source_uri == first.sealed_source_uri
    assert second.normalized_recap_path.stat().st_mtime_ns == stat_before.st_mtime_ns


def test_resolve_rejects_extraction_run_after_source_bytes_change(tmp_path: Path) -> None:
    """An out-of-band edit under the same revision must not become sealed evidence."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, source = _write_reviewable_extraction_run(repo)
    source.write_text("# Lore\n\nTampered after extraction.\n", encoding="utf-8")

    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"


def test_resolve_rejects_extraction_run_with_missing_candidate_bytes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, _source = _write_reviewable_extraction_run(repo)
    candidate = (
        repo / "out" / "graph_memory" / "runs" / "extraction" / "wb1" / "candidate_graph.json"
    )
    candidate.unlink()

    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"


def test_resolve_rejects_non_reviewable_extraction_run(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, _source = _write_reviewable_extraction_run(repo, status="prepared")
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "not reviewable" in str(exc.value)


def test_resolve_rejects_superseded_extraction_run(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, _source = _write_reviewable_extraction_run(repo, status="superseded")
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "superseded" in str(exc.value)


def test_resolve_unknown_still_404_without_latest_fallback(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_reviewable_extraction_run(repo)
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run("extraction-run-missing", root=repo)
    assert exc.value.code == "run_not_found"
    assert exc.value.status_code == 404


def test_resolve_prefers_canonical_extraction_run_over_legacy_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    """A colliding legacy manifest must not shadow the ExtractionRun SourceArtifact."""
    from apps.live_control_server.services.graph_run_registry import get_extraction_run

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _source = _write_reviewable_extraction_run(repo)
    run = get_extraction_run(repo, run_id)
    canonical_artifact = run.source_artifact_id

    # Plant a legacy graph-ingest manifest that reuses the same run_id but a
    # different SourceArtifact — the collision this seam must refuse to honor.
    _write_promotable_run(repo, run_id=run_id)
    manifest_path = (
        repo
        / "out/graph_memory/runs/longmont-c2/session-22/fixture-promote"
        / "graph_ingest_run_manifest.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == run_id
    assert payload["source"]["source_artifact_id"] != canonical_artifact

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.source_artifact_id == canonical_artifact
    assert any("canonical ExtractionRun" in item for item in resolved.diagnostics)


def test_resolve_non_reviewable_canonical_run_does_not_fall_back_to_legacy(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _source = _write_reviewable_extraction_run(repo, status="prepared")
    _write_promotable_run(repo, run_id=run_id)

    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"
    assert "not reviewable" in str(exc.value)


def test_resolve_carries_run_pinned_noncanonical_span_index_path(tmp_path: Path) -> None:
    """PromotableIngestRun must expose the ExtractionRun component path, not the registry default."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, _source = _write_reviewable_extraction_run(
        repo, pin_noncanonical_span_index=True
    )

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.source_span_index_path is not None
    assert resolved.source_span_index_path.name == "alt_source_span_index.json"
    from apps.live_control_server.services.source_artifact_registry import (
        source_span_index_path,
    )

    canonical = source_span_index_path(repo, resolved.source_artifact_id)
    assert resolved.source_span_index_path.resolve() != canonical.resolve()
    pinned_ids = {
        span["source_span_id"]
        for span in json.loads(
            resolved.source_span_index_path.read_text(encoding="utf-8")
        )["spans"]
    }
    canonical_ids = {
        span["source_span_id"]
        for span in json.loads(canonical.read_text(encoding="utf-8"))["spans"]
    }
    assert pinned_ids.isdisjoint(canonical_ids)
