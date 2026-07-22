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
    run_id: str = "extraction-run-wb-1",
    status: str = "reviewable",
    campaign_id: str | None = "longmont-c2",
    session_id: str | None = None,
    invent_session_in_candidate: bool = False,
) -> tuple[str, Path]:
    from graph_memory.ingestion.extraction_run import (
        ExtractionRun,
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunStatus,
    )

    run_dir = repo / "out" / "graph_memory" / "runs" / "extraction" / "wb1"
    run_dir.mkdir(parents=True, exist_ok=True)
    source = repo / "out" / "workspace" / "worldbuilding" / "doc.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("worldbuilding source for promote\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    source_artifact_id = "artifact:worldbuilding:doc:r1:abcdef123456"
    candidate_payload = _candidate_graph_payload(
        campaign_id=campaign_id or "",
        session_id="session-99" if invent_session_in_candidate else (session_id or ""),
    )
    if not invent_session_in_candidate and session_id is None:
        candidate_payload["session_id"] = None
    candidate_payload["source_artifact_ids"] = [source_artifact_id]
    for node in candidate_payload.get("nodes") or []:
        for ref in node.get("evidence_refs") or []:
            suffix = str(ref.get("source_ref_id") or "span").rsplit(":", 1)[-1]
            ref["source_artifact_id"] = source_artifact_id
            ref["source_span_ref_id"] = f"span:worldbuilding:{digest[:12]}:p{suffix}"
            ref.pop("session_id", None)
    for edge in candidate_payload.get("edges") or []:
        for ref in edge.get("evidence_refs") or []:
            suffix = str(ref.get("source_ref_id") or "span").rsplit(":", 1)[-1]
            ref["source_artifact_id"] = source_artifact_id
            ref["source_span_ref_id"] = f"span:worldbuilding:{digest[:12]}:p{suffix}"
            ref.pop("session_id", None)
    candidate = run_dir / "candidate_graph.json"
    candidate.write_text(json.dumps(candidate_payload, indent=2) + "\n", encoding="utf-8")
    span = run_dir / "source_span_index.json"
    span.write_text("{}\n", encoding="utf-8")

    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=f"repo://{source.relative_to(repo).as_posix()}",
            exists=True,
            sha256=f"sha256:{digest}",
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=span.as_posix(),
            exists=True,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=candidate.as_posix(),
            exists=True,
        ),
    }
    run = ExtractionRun(
        run_id=run_id,
        source_artifact_id=source_artifact_id,
        source_domain="worldbuilding",
        status=ExtractionRunStatus(status),
        campaign_id=campaign_id,
        session_id=session_id,
        profile_id="worldbuilding_plumbing_v0@0.1",
        components=components,
        lineage={"source_sha256": f"sha256:{digest}"},
    )
    registry = {
        "schema_version": "dmb_extraction_run_registry_v1",
        "records": [run.model_dump(mode="json")],
    }
    registry_path = repo / "out" / "registries" / "extraction_runs.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    return run_id, source


def test_resolve_reviewable_worldbuilding_extraction_run(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, source = _write_reviewable_extraction_run(repo)

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.run_id == run_id
    assert resolved.campaign_id == CAMPAIGN_ID
    assert resolved.session_id == ""
    assert resolved.source_artifact_id.startswith("artifact:worldbuilding:")
    assert resolved.source_revision_id.startswith("sha256:")
    assert resolved.candidate_graph_path.is_file()
    assert resolved.sealed_source_uri.startswith("repo://out/graph_memory/runs/")
    assert resolved.normalized_recap_path.is_file()
    assert "session_scope=null" in resolved.diagnostics
    # Source was copied under the run tree for seal policy.
    assert resolved.normalized_recap_path != source.resolve()


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
    _write_reviewable_extraction_run(repo, run_id="extraction-run-other")
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run("extraction-run-missing", root=repo)
    assert exc.value.code == "run_not_found"
    assert exc.value.status_code == 404
