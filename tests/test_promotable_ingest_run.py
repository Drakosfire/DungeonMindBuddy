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
    is_under_ingest_runs,
    is_under_world_store,
    resolve_promotable_ingest_run,
)
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
)
from graph_memory.ingestion.graph_ingest_run import GRAPH_INGEST_RUN_MANIFEST_SCHEMA
from tests._cutover_d3a_blocker_safe_fixtures import _write_reviewable_extraction_run

CAMPAIGN_ID = "longmont-c2"
SESSION_ID = "session-22"
RUN_ID = "graph-ingest:longmont-c2:session-22:fixture-promote"


def _semantic() -> dict:
    return {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _evidence(suffix: str) -> dict:
    return {
        "source_ref_id": f"ref:{suffix}",
        "source_artifact_id": "artifact:recap:longmont-c2:session-22",
        "source_anchor_id": f"anchor:{suffix}",
        "label": "span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-22:recap:paragraph:{suffix}",
        "anchor_quotes": ["quote"],
    }


def _candidate_graph_payload(
    *,
    campaign_id: str = CAMPAIGN_ID,
    session_id: str = SESSION_ID,
) -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:http-promote-vial",
        "session_id": session_id,
        "campaign_id": campaign_id,
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "status": "preview",
        "nodes": [
            {
                "node_id": "obj_session22_vial",
                "label": "vial",
                "node_type": "item",
                "description": "Puddle sample vial",
                "importance": "medium",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("006")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
            {
                "node_id": "mystery_puddles",
                "label": "Magic puddles",
                "node_type": "mystery",
                "description": "Delayed reflections",
                "importance": "medium",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
        ],
        "edges": [
            {
                "edge_id": "e33",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "mystery_puddles",
                "relationship_type": "linked_to",
                "label": "linked to",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }


def _write_promotable_run(
    repo: Path,
    *,
    run_id: str = RUN_ID,
    campaign_id: str = CAMPAIGN_ID,
    session_id: str = SESSION_ID,
    status: str = "preview_union_store_ready",
    candidate_graph_valid: bool = True,
    preview_union_store_valid: bool = True,
    digest_override: str | None = None,
    omit_candidate: bool = False,
    omit_preview: bool = False,
    omit_source_artifact_id: bool = False,
    extraction_profile: str | None = "category_v1",
    runs_rel: str = "out/graph_memory/runs",
    candidate_campaign_id: str | None = None,
    candidate_session_id: str | None = None,
    registry_context: dict | None = None,
    registry_filename: str = "registry_context_graph.json",
) -> tuple[str, str, Path]:
    run_dir = repo / Path(runs_rel) / campaign_id / session_id / "fixture-promote"
    run_dir.mkdir(parents=True, exist_ok=True)
    source = run_dir / "normalized_recap_source.md"
    source.write_text("session 22 promote fixture\n", encoding="utf-8")
    digest_hex = hashlib.sha256(source.read_bytes()).hexdigest()
    digest = digest_override or f"sha256:{digest_hex}"
    candidate = run_dir / "candidate_graph.json"
    if not omit_candidate:
        candidate.write_text(
            json.dumps(
                _candidate_graph_payload(
                    campaign_id=candidate_campaign_id or campaign_id,
                    session_id=candidate_session_id or session_id,
                ),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    preview = run_dir / "preview_union_supergraph.json"
    if not omit_preview:
        preview.write_text("{}\n", encoding="utf-8")

    def rel(path: Path) -> str:
        return path.relative_to(repo).as_posix()

    artifacts: dict = {
        "normalized_recap": {
            "kind": "normalized_recap",
            "uri": rel(source),
            "sha256": digest,
            "exists": True,
            "preview_only": True,
        },
    }
    if not omit_preview:
        artifacts["preview_union_store"] = {
            "kind": "preview_union_store",
            "uri": rel(preview),
            "exists": True,
            "preview_only": True,
        }
    if not omit_candidate:
        artifacts["candidate_graph"] = {
            "kind": "candidate_graph",
            "uri": rel(candidate),
            "exists": True,
            "preview_only": True,
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        }
    if registry_context is not None:
        registry_path = run_dir / registry_filename
        registry_path.write_text(
            json.dumps(registry_context, indent=2) + "\n", encoding="utf-8"
        )
        artifacts["registry_context_graph"] = {
            "kind": "registry_context_graph",
            "uri": rel(registry_path),
            "exists": True,
            "preview_only": True,
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        }

    source_block: dict = {
        "source_domain": "recap",
        "normalized_recap_path": rel(source),
        "normalized_recap_sha256": digest,
        "source_label": "fixture promote recap",
    }
    if not omit_source_artifact_id:
        source_block["source_artifact_id"] = "artifact:recap:longmont-c2:session-22"

    diagnostics: dict = {
        "preview_only": True,
        "candidate_extraction": False,
        "preview_import": True,
        "canon_promotion": False,
        "approved_memory_write": False,
        "corpus_mutation": False,
        "production_retrieval": False,
        "agent_interaction_connected": False,
        "runtime_projection_connected": False,
    }
    if extraction_profile:
        diagnostics["extraction_profile"] = extraction_profile

    manifest: dict = {
        "schema": GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
        "version": "0.1",
        "run_id": run_id,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "status": status,
        "created_at": "2026-07-17T00:00:00Z",
        "updated_at": "2026-07-17T00:00:00Z",
        "source": source_block,
        "artifacts": artifacts,
        "health": {
            "candidate_graph_valid": candidate_graph_valid,
            "preview_union_store_valid": preview_union_store_valid,
            "node_count": 2,
            "edge_count": 1,
            "evidence_ref_count": 2,
            "resolvable_evidence_ref_count": 2,
            "openable_evidence_ref_count": 2,
            "highlightable_evidence_ref_count": 2,
        },
        "diagnostics": diagnostics,
        "steps": [],
        "warnings": [],
        "errors": [],
        "next_actions": ["open_projection_preview"],
    }
    if extraction_profile:
        manifest["extraction_profile"] = extraction_profile
    manifest_path = run_dir / "graph_ingest_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return run_id, digest, source


@pytest.fixture(autouse=True)
def _ingest_application_state(application_state_dsn: str) -> str:
    return application_state_dsn

@pytest.mark.parametrize("manifest_options", [{}, {"status": "failed"}, {"omit_candidate": True}])
def test_file_manifest_cannot_authorize_promotion(tmp_path, monkeypatch, manifest_options):
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _, _ = _write_promotable_run(tmp_path, **manifest_options)
    monkeypatch.setattr(Path, "rglob", lambda *a, **k: pytest.fail("promotion scanned files"))
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=tmp_path)
    assert exc.value.code == "run_not_found"
    assert exc.value.status_code == 404


def test_historical_catalog_never_offers_file_manifest_promotion(tmp_path, monkeypatch):
    from apps.live_control_server.services.graph_ingest_run_registry import discover_graph_ingest_runs
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    _write_promotable_run(tmp_path)
    rows = discover_graph_ingest_runs(tmp_path)
    assert len(rows) == 1
    assert rows[0].promotable is False
    assert "inspection-only" in rows[0].promotable_reason


def test_database_unavailability_does_not_fall_back_to_manifest(tmp_path, monkeypatch):
    from application_state.errors import ApplicationStateUnavailableError
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    run_id, _, _ = _write_promotable_run(tmp_path)
    def unavailable(*a, **k):
        raise ApplicationStateUnavailableError("input owner unavailable")
    monkeypatch.setattr("apps.live_control_server.services.graph_run_registry.ingest_service.get_extraction_run", unavailable)
    monkeypatch.setattr(Path, "rglob", lambda *a, **k: pytest.fail("promotion scanned files"))
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=tmp_path)
    assert exc.value.status_code == 503
    assert "input owner unavailable" in str(exc.value)


@pytest.mark.parametrize("failure_at", ["evidence", "resolved_metadata"])
def test_source_owner_unavailability_remains_503(tmp_path, monkeypatch, failure_at):
    from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError
    run_id, _ = _write_reviewable_extraction_run(tmp_path)
    def unavailable(*a, **k):
        raise SourceArtifactRegistryError("source owner unavailable", status_code=503)
    target = ("graph_run_registry" if failure_at == "evidence" else "source_artifact_registry")
    monkeypatch.setattr(f"apps.live_control_server.services.{target}.get_source_artifact", unavailable)
    monkeypatch.setattr(Path, "rglob", lambda *a, **k: pytest.fail("promotion scanned files"))
    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=tmp_path)
    assert exc.value.status_code == 503
    assert "source owner unavailable" in str(exc.value)


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
    assert resolved.world_id == CAMPAIGN_ID  # legacy fixture stamps campaign as world identity
    assert "world_id=" + CAMPAIGN_ID in resolved.diagnostics
    assert resolved.source_revision_id == f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    assert resolved.candidate_graph_path.is_file()
    assert resolved.sealed_source_uri.startswith("repo://out/graph_memory/runs/promote_seals/")
    assert resolved.normalized_recap_path.is_file()
    assert resolved.source_span_index_path is not None
    assert resolved.source_span_index_path.is_file()
    assert resolved.source_span_index_sha256 == hashlib.sha256(resolved.source_span_index_path.read_bytes()).hexdigest()
    assert "session_scope=null" in resolved.diagnostics
    # Registry-owned source bytes are sealed by digest, not read in place, and the
    # run's own artifact directory is never mutated to make that possible.
    assert resolved.normalized_recap_path != source.resolve()
    assert resolved.normalized_recap_path.read_bytes() == source.read_bytes()
    assert not (resolved.run_dir / "normalized_source.md").exists()


def test_resolve_managed_worldbuilding_run_preserves_source_artifact_world_id(
    tmp_path: Path,
) -> None:
    """Canonical Build run must preserve SourceArtifact W != Eldyrwild."""
    repo = tmp_path / "repo"
    repo.mkdir()
    world_id = "the-glass-orchard"
    run_id, _source = _write_reviewable_extraction_run(
        repo,
        campaign_id=world_id,
        world_id=world_id,
    )

    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    assert resolved.world_id == world_id
    assert resolved.campaign_id == world_id
    assert resolved.session_id == ""
    assert resolved.world_id != "eldyrwild"
    assert f"world_id={world_id}" in resolved.diagnostics


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
        repo / "out" / "graph_memory" / "runs" / "extraction" / run_id / "candidate_graph.json"
    )
    candidate.unlink()

    with pytest.raises(PromotableIngestRunError) as exc:
        resolve_promotable_ingest_run(run_id, root=repo)
    assert exc.value.code == "run_not_promotable"


def test_resolve_rejects_reviewable_candidate_byte_drift(tmp_path: Path) -> None:
    """A child run cannot prepare from bytes changed after its candidate SHA seal."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_id, _source = _write_reviewable_extraction_run(repo)
    candidate = (
        repo / "out" / "graph_memory" / "runs" / "extraction" / run_id / "candidate_graph.json"
    )
    candidate.write_bytes(candidate.read_bytes() + b"\n")

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
    assert resolved.source_span_index_sha256 == hashlib.sha256(resolved.source_span_index_path.read_bytes()).hexdigest()
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
