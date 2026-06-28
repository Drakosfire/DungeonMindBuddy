from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import apps.live_control_server.services.union_supergraph_projection_adapter as adapter_module
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    TWO_SESSION_PREVIEW_SOURCE,
    build_plan_union_supergraph_projection,
    build_plan_union_supergraph_projection_payload,
)
from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    run_graph_preview_extraction,
)
from graph_memory.ingestion import GraphIngestRunStatus
from graph_memory.projection import RecapGraphProjection
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH
from graph_memory.union_supergraph.preview_run_materialize import (
    PreviewUnionMaterializeOptions,
    materialize_preview_union_store_from_graph_ingest_run,
)


def test_adapter_builds_projection_for_session_23() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    assert isinstance(projection, RecapGraphProjection)
    assert projection.session_id == "session-23"
    assert projection.campaign_id == "longmont-c2"
    assert projection.graph_id == "longmont-c2:union-supergraph"


def test_adapter_projection_contains_global_pc_caelynn() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    assert caelynn.node_id == "pc_caelynn"
    assert caelynn.label == "Caelynn"
    assert caelynn.kind == "pc"
    assert caelynn.role == "pc"
    assert caelynn.anchored_to_focus_session is True


def test_adapter_projection_preserves_focus_and_non_focus_evidence() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    badges = {badge.evidence_ref_id: badge for badge in caelynn.evidence_badges}

    assert (
        badges["evidence:session-23:caelynn:recap-mention"].is_focus_session_evidence
        is True
    )
    assert badges["evidence:session-23:caelynn:recap-mention"].source_domain == "recap"
    assert (
        badges[
            "evidence:worldbuilding:caelynn:character-note"
        ].is_focus_session_evidence
        is False
    )
    assert (
        badges["evidence:worldbuilding:caelynn:character-note"].source_domain
        == "worldbuilding"
    )


def test_adapter_projection_preserves_focus_and_non_focus_adjacency() -> None:
    projection = build_plan_union_supergraph_projection(session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    candidates = {candidate.node_id: candidate for candidate in caelynn.adjacency}

    session_event = candidates["event_session_23_mireward_gate"]
    assert session_event.anchored_to_focus_session is True
    assert session_event.predicate == "participated_in"

    mirathorn = candidates["loc_mirathorn"]
    assert mirathorn.anchored_to_focus_session is False
    assert mirathorn.source_domains == ["worldbuilding"]


def test_adapter_payload_is_json_safe_dict() -> None:
    payload = build_plan_union_supergraph_projection_payload(session_id="session-23")

    assert isinstance(payload, dict)
    assert payload["session_id"] == "session-23"
    assert payload["node_views"]["pc_caelynn"]["node_id"] == "pc_caelynn"
    json.dumps(payload)
    assert _is_json_safe(payload)


def test_adapter_accepts_explicit_store_path() -> None:
    projection = build_plan_union_supergraph_projection(
        session_id="session-23",
        store_path=DEFAULT_FIXTURE_PATH,
    )

    assert projection.node_views["pc_caelynn"].node_id == "pc_caelynn"


def test_adapter_builds_two_session_preview_source() -> None:
    projection = build_plan_union_supergraph_projection(
        session_id="session-23",
        preview_source=TWO_SESSION_PREVIEW_SOURCE,
    )
    lysandro = projection.node_views["character_lysandro"]

    assert projection.graph_id == "longmont-c2:preview-union-supergraph"
    assert projection.markdown
    assert "[Lysandro](dmb-node:character_lysandro)" in projection.markdown
    assert lysandro.anchored_to_focus_session is True
    assert lysandro.suggested_expansions
    assert lysandro.suggested_expansions[0].rank == 1
    assert any(
        badge.evidence_ref_id.startswith("evidence:session-22:")
        and not badge.is_focus_session_evidence
        for badge in lysandro.evidence_badges
    )
    assert any(
        badge.evidence_ref_id.startswith("evidence:session-23:")
        and badge.is_focus_session_evidence
        for badge in lysandro.evidence_badges
    )


def test_adapter_preview_payload_is_json_safe() -> None:
    payload = build_plan_union_supergraph_projection_payload(
        session_id="session-23",
        preview_source=TWO_SESSION_PREVIEW_SOURCE,
    )

    assert payload["node_views"]["character_lysandro"]["anchored_to_focus_session"] is True
    assert _is_json_safe(payload)


def test_adapter_raises_for_missing_store_path(tmp_path: Path) -> None:
    missing_store_path = tmp_path / "missing-union-supergraph.json"

    with pytest.raises(FileNotFoundError):
        build_plan_union_supergraph_projection(
            session_id="session-23",
            store_path=missing_store_path,
        )


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


def test_adapter_builds_projection_from_graph_ingest_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(tmp_path, monkeypatch)

    projection = build_plan_union_supergraph_projection(
        session_id="session-24",
        graph_run_manifest_path=result.manifest_path,
    )

    assert projection.session_id == "session-24"
    assert projection.graph_id == "longmont-c2:preview-union-supergraph"
    assert "npc_elara_voss" in projection.node_views
    assert isinstance(projection.mentions, list)


def test_adapter_rejects_manifest_not_preview_union_store_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _candidate_ready_manifest(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="preview_union_store_ready"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=manifest_path,
        )


def test_adapter_rejects_manifest_missing_preview_union_store_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(tmp_path, monkeypatch)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"].pop("preview_union_store")
    result.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="artifacts.preview_union_store"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=result.manifest_path,
        )


def test_adapter_rejects_unsafe_graph_run_manifest_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_adapter_repo_root(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="unsafe repo-contained path"):
        build_plan_union_supergraph_projection(
            session_id="session-24",
            graph_run_manifest_path=Path("../escape/graph_ingest_run_manifest.json"),
        )


def test_projection_from_graph_run_manifest_does_not_require_projection_locator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _preview_union_ready_run(tmp_path, monkeypatch)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["projection"] is None

    projection = build_plan_union_supergraph_projection(
        session_id="session-24",
        graph_run_manifest_path=result.manifest_path,
    )

    assert projection.session_id == "session-24"


def _preview_union_ready_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    manifest_path = _candidate_ready_manifest(tmp_path, monkeypatch)
    return materialize_preview_union_store_from_graph_ingest_run(
        PreviewUnionMaterializeOptions(manifest_path=manifest_path)
    )


def _candidate_ready_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    _patch_adapter_repo_root(monkeypatch, tmp_path)
    source = tmp_path / "session_24_normalized_recap.md"
    candidate = tmp_path / "candidate_graph_fixture.json"
    source.write_text(
        CATEGORY_RECAP_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidate.write_text(
        CATEGORY_CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/candidate_ready"),
            candidate_graph_path=candidate,
        )
    )
    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    return result.manifest_path


def _patch_adapter_repo_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(adapter_module, "repo_root", lambda: root)
