from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.services.union_supergraph_projection_adapter as adapter_module
from apps.live_control_server.main import create_app
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    TWO_SESSION_PREVIEW_SOURCE,
)
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    run_graph_preview_extraction,
)
from graph_memory.ingestion import GraphIngestRunStatus
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH
from graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)


def test_union_supergraph_projection_api_returns_session_23_payload() -> None:
    payload = _get_projection_payload()

    assert payload["session_id"] == "session-23"
    assert payload["campaign_id"] == "longmont-c2"
    assert payload["graph_id"] == "longmont-c2:union-supergraph"
    assert {
        "campaign_id",
        "session_id",
        "graph_id",
        "markdown",
        "focus",
        "node_views",
        "mentions",
        "source_spans",
        "union_identity_diagnostics",
        "union_identity_applied_assertion_ids",
    }.issubset(set(payload))


def test_union_supergraph_projection_api_contains_global_pc_caelynn() -> None:
    payload = _get_projection_payload()

    caelynn = payload["node_views"]["pc_caelynn"]
    assert caelynn["node_id"] == "pc_caelynn"
    assert caelynn["label"] == "Caelynn"
    assert caelynn["kind"] == "pc"
    assert caelynn["role"] == "pc"
    assert caelynn["anchored_to_focus_session"] is True


def test_union_supergraph_projection_api_returns_projected_recap_markdown() -> None:
    payload = _get_projection_payload()

    assert payload["markdown"]
    assert not payload["markdown"].lstrip().startswith("---")
    assert "[Caelynn](dmb-node:pc_caelynn)" in payload["markdown"]
    assert payload["mentions"]
    assert any(mention["node_id"] == "pc_caelynn" for mention in payload["mentions"])


def test_union_supergraph_projection_api_preserves_focus_and_non_focus_evidence() -> None:
    payload = _get_projection_payload()

    badges = {
        badge["evidence_ref_id"]: badge
        for badge in payload["node_views"]["pc_caelynn"]["evidence_badges"]
    }

    focus_badge = badges["evidence:session-23:caelynn:recap-mention"]
    assert focus_badge["is_focus_session_evidence"] is True
    assert focus_badge["source_domain"] == "recap"

    worldbuilding_badge = badges["evidence:worldbuilding:caelynn:character-note"]
    assert worldbuilding_badge["is_focus_session_evidence"] is False
    assert worldbuilding_badge["source_domain"] == "worldbuilding"


def test_union_supergraph_projection_api_preserves_focus_and_non_focus_adjacency() -> None:
    payload = _get_projection_payload()

    adjacency = {
        candidate["node_id"]: candidate
        for candidate in payload["node_views"]["pc_caelynn"]["adjacency"]
    }

    session_event = adjacency["event_session_23_mireward_gate"]
    assert session_event["anchored_to_focus_session"] is True
    assert session_event["predicate"] == "participated_in"
    assert session_event["source_domains"] == ["recap"]

    mirathorn = adjacency["loc_mirathorn"]
    assert mirathorn["anchored_to_focus_session"] is False
    assert mirathorn["predicate"] == "connected_to"
    assert mirathorn["source_domains"] == ["worldbuilding"]


def test_union_supergraph_projection_api_includes_suggested_expansions() -> None:
    payload = _get_projection_payload()
    caelynn = payload["node_views"]["pc_caelynn"]

    assert caelynn["suggested_expansions"]
    assert caelynn["suggested_expansions"][0]["node_id"] == "event_session_23_mireward_gate"
    assert caelynn["suggested_expansions"][0]["rank_reason"] == "current session"
    assert caelynn["suggested_expansions"][1]["node_id"] == "loc_mirathorn"


def test_union_supergraph_projection_api_preserves_focus_metadata() -> None:
    payload = _get_projection_payload()

    focus = payload["focus"]
    assert focus["focus_session_id"] == "session-23"
    assert "pc_caelynn" in focus["focused_node_ids"]
    assert "event_session_23_mireward_gate" in focus["focused_node_ids"]
    assert (
        "evidence:session-23:caelynn:recap-mention"
        in focus["focused_evidence_ref_ids"]
    )


def test_union_supergraph_projection_api_returns_json_safe_payload() -> None:
    payload = _get_projection_payload()

    json.dumps(payload)
    assert _is_json_safe(payload)


def test_union_supergraph_projection_api_accepts_explicit_store_path() -> None:
    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={"session_id": "session-23", "store_path": str(DEFAULT_FIXTURE_PATH)},
    )

    assert response.status_code == 200
    assert response.json()["node_views"]["pc_caelynn"]["node_id"] == "pc_caelynn"


def test_union_supergraph_projection_api_missing_store_returns_404(
    tmp_path: Path,
) -> None:
    missing_store_path = tmp_path / "missing-union-supergraph.json"

    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={"session_id": "session-23", "store_path": str(missing_store_path)},
    )

    assert response.status_code == 404
    assert str(missing_store_path) in response.json()["detail"]


def _get_projection_payload() -> dict[str, Any]:
    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={"session_id": "session-23"},
    )
    assert response.status_code == 200
    return response.json()


def _client() -> TestClient:
    return TestClient(create_app())


def _is_json_safe(value: Any) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_safe(item)
            for key, item in value.items()
        )
    return False


CATEGORY_FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "tests/fixtures/graph_memory/category_preview_runner"
)
CATEGORY_RECAP_PATH = CATEGORY_FIXTURE_DIR / "session_24_normalized_recap.md"
CATEGORY_CANDIDATE_PATH = CATEGORY_FIXTURE_DIR / "candidate_graph_fixture.json"


def test_api_returns_projection_from_graph_run_manifest_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(tmp_path, monkeypatch)

    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={
            "session_id": "session-24",
            "graph_run_manifest_path": str(result.manifest_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-24"
    assert payload["graph_id"] == "longmont-c2:preview-union-supergraph"
    assert "character_mira" in payload["node_views"]


def test_api_preserves_preview_source_fallback() -> None:
    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={
            "session_id": "session-23",
            "preview_source": TWO_SESSION_PREVIEW_SOURCE,
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["node_views"]["character_lysandro"]["node_id"]
        == "character_lysandro"
    )


def test_api_rejects_unsafe_graph_run_manifest_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(adapter_module, "repo_root", lambda: tmp_path)

    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={
            "session_id": "session-24",
            "graph_run_manifest_path": "../escape.json",
        },
    )

    assert response.status_code == 400
    assert "unsafe repo-contained path" in response.json()["detail"]


def test_api_returns_recap_only_projection_when_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    normalized_dir = (
        tmp_path
        / "Longmont Campaign/Campaign 2/Session Recaps/_normalized"
    )
    normalized_dir.mkdir(parents=True)
    (normalized_dir / "Session 24 - Dogfood.md").write_text(
        "---\ntitle: Dogfood\n---\n# Session 24\n\nRecap memory text.",
        encoding="utf-8",
    )
    monkeypatch.setattr(adapter_module, "corpus_root", lambda: tmp_path)

    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={
            "campaign_id": "longmont-c2",
            "session_id": "session-24",
            "allow_recap_only": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"] == "longmont-c2"
    assert payload["session_id"] == "session-24"
    assert payload["graph_id"] is None
    assert payload["markdown"] == "# Session 24\n\nRecap memory text."
    assert payload["focus"]["focus_session_id"] == "session-24"
    assert payload["node_views"] == {}
    assert payload["mentions"] == []


def test_recap_artifacts_registry_discovers_canonical_normalized_recaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(adapter_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr("apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path)
    normalized_dir = (
        tmp_path
        / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized"
    )
    normalized_dir.mkdir(parents=True)
    (normalized_dir / "Session 24 - Constructed.md").write_text(
        "# Session 24\n\nConstructed recap.",
        encoding="utf-8",
    )

    response = _client().get(
        "/api/live/graph-preview/artifacts",
        params={"campaign_id": "longmont-c2"},
    )

    assert response.status_code == 200
    records = response.json()["records"]
    assert [record["session_id"] for record in records] == ["session-24"]
    assert records[0]["source_recap_path"].endswith(
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Constructed.md"
    )


def test_latest_graph_ingest_requires_matching_source_recap_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path)
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", "runs")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    source_sha = manifest["source"]["normalized_recap_sha256"]

    mismatch = _client().get(
        "/api/live/graph-preview/graph-ingest/latest",
        params={
            "campaign_id": "longmont-c2",
            "session_id": "session-24",
            "source_recap_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Real.md",
        },
    )
    match = _client().get(
        "/api/live/graph-preview/graph-ingest/latest",
        params={
            "campaign_id": "longmont-c2",
            "session_id": "session-24",
            "source_recap_sha256": source_sha,
        },
    )

    assert mismatch.status_code == 404
    assert match.status_code == 200
    assert match.json()["run"]["manifest_path"] == "runs/candidate_ready/graph_ingest_run_manifest.json"


def test_api_recap_only_requires_campaign_id() -> None:
    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={
            "session_id": "session-24",
            "allow_recap_only": "true",
        },
    )

    assert response.status_code == 400
    assert "campaign_id is required" in response.json()["detail"]


def test_api_rejects_store_with_recap_path_outside_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(tmp_path, monkeypatch)
    _mutate_preview_store_recap_artifact(
        result.preview_union_store_path,
        recap_path=str(_existing_path_outside_root(tmp_path)),
    )

    response = _client().get(
        "/api/live/graph-preview/union-supergraph/projection",
        params={
            "session_id": "session-24",
            "graph_run_manifest_path": str(result.manifest_path),
        },
    )

    assert response.status_code == 400
    assert "path is outside repo root" in response.json()["detail"]


def _preview_union_ready_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(adapter_module, "repo_root", lambda: tmp_path)
    source = tmp_path / "session_24_normalized_recap.md"
    candidate = tmp_path / "candidate_graph_fixture.json"
    source.write_text(
        CATEGORY_RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidate.write_text(
        CATEGORY_CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    runner_result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/candidate_ready"),
            candidate_graph_path=candidate,
        )
    )
    assert runner_result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    return materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=runner_result.manifest_path)
    )


def _mutate_preview_store_recap_artifact(
    store_path: Path,
    *,
    recap_path: str,
) -> None:
    store = json.loads(store_path.read_text(encoding="utf-8"))
    artifact = next(
        item
        for item in store["source_artifacts"].values()
        if item.get("source_domain") == "recap"
        and item.get("session_id") == "session-24"
    )
    artifact["recap_path"] = recap_path
    store_path.write_text(json.dumps(store), encoding="utf-8")


def _existing_path_outside_root(root: Path) -> Path:
    candidate = Path("/etc/passwd")
    if candidate.exists():
        return candidate
    return root.parent
