"""Tests for graph preview surface API."""
from __future__ import annotations

from json import JSONDecodeError, dumps
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV, repo_root
from apps.live_control_server.main import create_app
from apps.live_control_server.services import graph_preview_surface
from apps.live_control_server.services.graph_preview_surface import (
    build_graph_preview_surface,
    build_latest_graph_preview_surface,
    build_recap_graph_presentation,
    discover_graph_preview_runs,
)
from apps.live_control_server.services.recap_artifacts import sync_recap_artifacts_registry

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
VALID_RUN = (
    "evals/graph_memory_layer/artifacts/category_graph_model_study/"
    "2026-06-26/session_22_gpt-5-4-mini_run1"
)


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        import shutil

        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def test_discover_graph_preview_runs_includes_committed_cohort() -> None:
    runs = discover_graph_preview_runs(repo_root())
    assert runs
    assert any("session_22" in r.run_dir for r in runs)


def test_discover_graph_preview_runs_empty_when_session_has_no_graph_runs() -> None:
    sync_recap_artifacts_registry(repo_root())
    runs = discover_graph_preview_runs(
        repo_root(),
        campaign_id="longmont-c2",
        session_id="session-21",
    )
    assert runs == []


def test_unbounded_graph_preview_run_catalog_route_is_removed(client: TestClient) -> None:
    response = client.get("/api/live/graph-preview/runs")
    assert response.status_code == 404


def test_build_graph_preview_surface_enriches_paragraph_evidence() -> None:
    fallback_run = (
        "evals/graph_memory_layer/artifacts/category_graph_model_study/"
        "2026-06-26/anchor_quote_n3/session_22_gpt-5-4-mini_run3"
    )
    run_dir = VALID_RUN
    if not (repo_root() / run_dir / "validation_report.json").is_file():
        if (repo_root() / fallback_run / "candidate_output.json").is_file():
            run_dir = fallback_run
        else:
            pytest.skip("category study artifact not present locally")
    payload = build_graph_preview_surface(repo_root(), run_dir)
    assert payload.schema_version == "dmb_graph_preview_surface_v1"
    assert payload.candidates
    with_evidence = [c for c in payload.candidates if c.evidence_refs]
    assert with_evidence
    has_spref = any(ref.source_span_ref_id for c in with_evidence for ref in c.evidence_refs)
    if has_spref:
        assert any(ref.paragraph_text for c in with_evidence for ref in c.evidence_refs)


@pytest.mark.parametrize("pinned_uri", [None, "pinned-run"])
def test_latest_surface_discovers_only_when_unpinned(tmp_path, monkeypatch, pinned_uri) -> None:
    record = SimpleNamespace(
        artifact_id="artifact", campaign_id="campaign", session_id="session",
        run_bundle_uri="bundle", default_graph_run_uri=pinned_uri,
    )
    discovery = Mock(return_value=[SimpleNamespace(run_dir="discovered-run", canonical_ir_valid=True)])
    build = Mock()
    monkeypatch.setattr(graph_preview_surface, "_resolve_recap_artifact", Mock(return_value=record))
    monkeypatch.setattr(graph_preview_surface, "discover_graph_preview_runs", discovery)
    monkeypatch.setattr(graph_preview_surface, "build_graph_preview_surface", build)

    assert build_latest_graph_preview_surface(tmp_path) is build.return_value
    build.assert_called_once_with(
        tmp_path, pinned_uri or "discovered-run", run_bundle_dir=tmp_path / "bundle", artifact_record=record, _loaded_run=None,
    )
    if pinned_uri:
        discovery.assert_not_called()
    else:
        discovery.assert_called_once_with(
            tmp_path, artifact_id="artifact", campaign_id="campaign", session_id="session",
        )
        discovery.return_value = []
        with pytest.raises(graph_preview_surface.GraphPreviewSurfaceError) as error:
            build_latest_graph_preview_surface(tmp_path)
        assert error.value.status_code == 404


@pytest.mark.parametrize(
    ("canonical", "evidence", "winner", "probed"),
    [
        ({0, 2}, {0, 2, 3}, 2, [3, 2]),
        ({0, 2}, {1, 3}, 3, [3, 2, 0]),
        ({0, 2}, set(), 2, [3, 2, 1, 0]),
        (set(), set(), 3, [3, 2, 1, 0]),
    ],
)
def test_preview_ranking_probes_only_runs_that_can_win(tmp_path, monkeypatch, canonical, evidence, winner, probed):
    runs = [SimpleNamespace(run_dir=str(i), canonical_ir_valid=i in canonical) for i in range(4)]
    graph = {"nodes": [{"evidence_refs": [{"source_span_ref_id": "source"}]}]}
    probe = Mock(side_effect=lambda path: ({}, graph if int(path.name) in evidence else None))
    monkeypatch.setattr(graph_preview_surface, "_resolve_run_dir", lambda root, name: root / name)
    monkeypatch.setattr(graph_preview_surface, "_load_run_graph", probe)
    picked = graph_preview_surface._pick_latest_run(tmp_path, runs)
    assert picked[0] is runs[winner]
    assert [int(call.args[0].name) for call in probe.call_args_list] == probed


def test_preview_ranking_skips_malformed_older_artifact_after_top_tier_match(tmp_path, monkeypatch):
    older = SimpleNamespace(run_dir="older", canonical_ir_valid=True)
    newer = SimpleNamespace(run_dir="newer", canonical_ir_valid=True)
    malformed = JSONDecodeError("malformed fixture", "{", 1)

    def probe(path):
        if path.name == older.run_dir:
            raise malformed
        return {}, {"nodes": [{"evidence_refs": [{"source_span_ref_id": "source"}]}]}

    monkeypatch.setattr(graph_preview_surface, "_resolve_run_dir", lambda root, name: root / name)
    monkeypatch.setattr(graph_preview_surface, "_load_run_graph", probe)
    assert graph_preview_surface._pick_latest_run(tmp_path, [older, newer])[0] is newer
    with pytest.raises(JSONDecodeError):
        graph_preview_surface._pick_latest_run(tmp_path, [older])


@pytest.mark.parametrize(("filename", "key"), [
    ("validation_report.json", "reconciled_candidate_graph"),
    ("candidate_output.json", "candidate_graph"),
])
def test_latest_surface_decodes_winning_graph_once(tmp_path, monkeypatch, filename, key):
    run = tmp_path / "run"
    run.mkdir()
    artifact = run / filename
    artifact.write_text(dumps({key: {"nodes": [{"evidence_refs": [{"source_span_ref_id": "source"}]}]}}))
    record = SimpleNamespace(
        artifact_id="artifact", campaign_id="campaign", session_id="session",
        run_bundle_uri="missing-bundle", default_graph_run_uri=None,
    )
    load = Mock(wraps=graph_preview_surface._load_json)
    monkeypatch.setattr(graph_preview_surface, "_resolve_recap_artifact", lambda *args, **kwargs: record)
    monkeypatch.setattr(graph_preview_surface, "discover_graph_preview_runs",
                        lambda *args, **kwargs: [SimpleNamespace(run_dir="run", canonical_ir_valid=True)])
    monkeypatch.setattr(graph_preview_surface, "_resolve_run_dir", lambda root, name: root / name)
    monkeypatch.setattr(graph_preview_surface, "_load_json", load)
    with pytest.raises(graph_preview_surface.GraphPreviewSurfaceError, match="run bundle not found"):
        build_latest_graph_preview_surface(tmp_path)
    load.assert_called_once_with(artifact)


def test_latest_surface_prefers_resolvable_run() -> None:
    runs = discover_graph_preview_runs(repo_root())
    if not runs:
        pytest.skip("no graph preview runs discovered")
    payload = build_latest_graph_preview_surface(repo_root())
    # If any discovered run carries spref-backed evidence, the default pick must be
    # one whose source-highlight panel can render (resolvable > 0), even when its
    # canonical IR is marked invalid.
    any_resolvable = False
    for run in runs:
        try:
            candidate = build_graph_preview_surface(repo_root(), run.run_dir)
        except Exception:
            continue
        if candidate.health.resolvable_evidence_ref_count > 0:
            any_resolvable = True
            break
    if any_resolvable:
        assert payload.health.resolvable_evidence_ref_count > 0


def test_recap_presentation_reuses_preview_source_snapshot(tmp_path, monkeypatch):
    run = tmp_path / "run"
    run.mkdir()
    (run / "candidate_output.json").write_text(dumps({"nodes": [{"node_id": "npc_mara", "node_type": "npc", "label": "Mara"}]}))
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    index_path = bundle / "source_span_index.json"
    index_path.write_text(dumps({"spans": [{"span_id": "span", "line_start": 1, "line_end": 1},
                                                {"span_id": "span", "line_start": 2, "line_end": 2}]}))
    record = SimpleNamespace(default_graph_run_uri="run", run_bundle_uri="bundle", source_recap_path=None)
    read = Mock(wraps=graph_preview_surface._load_json)
    class CountedRecap(str):
        splits = 0

        def splitlines(self, keepends=False):
            self.splits += 1
            return super().splitlines(keepends)

    source = CountedRecap("First line.\r\nAsk Mara.\r\n")
    recap = Mock(return_value=(source, "recap.md"))
    monkeypatch.setattr(graph_preview_surface, "_resolve_recap_artifact", lambda *args, **kwargs: record)
    monkeypatch.setattr(graph_preview_surface, "_resolve_run_dir", lambda root, name: root / name)
    monkeypatch.setattr(graph_preview_surface, "_load_json", read)
    monkeypatch.setattr(graph_preview_surface, "_recap_text_for_run_bundle", recap)
    monkeypatch.setattr(graph_preview_surface, "_route_seed_nodes", lambda *args: ({}, {}))

    payload = build_recap_graph_presentation(tmp_path)

    assert payload.markdown == "First line.\nAsk [Mara](dmb-node:npc_mara)."
    assert [(link.source_span_ref_id, link.char_start, link.char_end) for link in payload.links] == [("span", 4, 8)]
    assert payload.recap_source_path == "recap.md"
    assert sum(call.args == (index_path,) for call in read.call_args_list) == 1
    assert source.splits == 1
    recap.assert_called_once_with(tmp_path, bundle, source_recap_path=None)


def test_build_recap_graph_presentation_links_node_labels() -> None:
    sync_recap_artifacts_registry(repo_root())
    payload = build_recap_graph_presentation(
        repo_root(),
        campaign_id="longmont-c2",
        session_id="session-22",
    )
    assert payload.schema_version == "dmb_recap_graph_presentation_v1"
    assert payload.nodes
    assert payload.links
    assert not payload.markdown.startswith("---")
    assert "[Lysandro](dmb-node:npc_lysandro)" in payload.markdown
    assert "[Caelynn](dmb-node:pc_caelynn)" in payload.markdown
    assert "[Karesmine](dmb-node:pc_karsemine)" in payload.markdown
    assert "[Mireward](dmb-node:loc_mireward)" in payload.markdown
    assert "npc_lysandro" in payload.nodes
    assert "pc_caelynn" in payload.nodes
    assert payload.nodes["pc_caelynn"].role == "pc"
    assert payload.nodes["loc_mireward"].label == "Mireward Reach"
    assert payload.nodes["npc_lysandro"].role == "npc"
    assert any(chip.label.startswith("S22") for chip in payload.nodes["npc_lysandro"].chips)


def test_get_graph_preview_latest(client: TestClient) -> None:
    response = client.get("/api/live/graph-preview/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_graph_preview_surface_v1"
    assert body["health"]["node_count"] >= 1
    assert isinstance(body["candidates"], list)


def test_get_graph_preview_by_run_dir(client: TestClient) -> None:
    if not (repo_root() / VALID_RUN / "validation_report.json").is_file():
        pytest.skip("category study artifact not present locally")
    response = client.get(
        "/api/live/graph-preview/latest",
        params={"run_dir": VALID_RUN},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run_dir"] == VALID_RUN


def test_get_recap_graph_presentation(client: TestClient) -> None:
    response = client.get("/api/live/graph-preview/recap")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_recap_graph_presentation_v1"
    assert "markdown" in body
    assert isinstance(body["nodes"], dict)
