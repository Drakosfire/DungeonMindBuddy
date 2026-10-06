from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from apps.live_control_server.config import MANAGED_WORLD_DATA_ROOT_ENV, SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.session_store import load_session
from src.live_play.projections import build_session_plan_projection

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/c2_live_prep/live/schemas/plan_view.schema.json"
SAMPLE_PATH = ROOT / "evals/c2_live_prep/live/session_22/plan_view.sample.json"
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
ALLOWED_TARGET_TYPES = {
    "event",
    "roll_table",
    "npc",
    "location",
    "runbook_section",
    "job",
    "open_loop",
    "source_packet",
}


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def test_builder_returns_non_authoritative_payload() -> None:
    packet, _, events, jobs = load_session(SEED_SESSION)
    projection = build_session_plan_projection(
        packet,
        events,
        jobs,
        generated_at="2026-05-28T00:00:00Z",
    )
    assert projection["authoritative"] is False
    assert projection["campaign_id"] == packet["campaign_id"]
    assert projection["session"] == packet["session"]
    assert projection["timeline"]
    _validator().validate(projection)


def test_builder_rows_have_human_labels_and_typed_refs() -> None:
    packet, _, events, jobs = load_session(SEED_SESSION)
    projection = build_session_plan_projection(packet, events, jobs, generated_at="2026-05-28T00:00:00Z")
    for row in projection["timeline"]:
        assert isinstance(row["label"], str) and row["label"].strip()
        assert isinstance(row["summary"], str) and row["summary"].strip()
        for ref in row["refs"]:
            assert ref["target_type"] in ALLOWED_TARGET_TYPES
            assert isinstance(ref["target_id"], str) and ref["target_id"].strip()
            assert isinstance(ref["label"], str) and ref["label"].strip()


def test_sample_fixture_validates_against_schema() -> None:
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    _validator().validate(sample)
    assert sample["authoritative"] is False
    assert 5 <= len(sample["timeline"]) <= 8


def test_get_plan_view_endpoint_returns_valid_payload(client: TestClient) -> None:
    response = client.get("/api/live/plan-view")
    assert response.status_code == 200
    body = response.json()
    _validator().validate(body)
    assert body["authoritative"] is False
    assert body["timeline"]


def test_managed_world_plan_context_v2_has_no_campaign_or_session_sentinel(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.routes import live
    from apps.live_control_server.services.world_container_registry import create_world_container

    world = create_world_container(tmp_path, name="Context Test World")
    monkeypatch.setattr(live, "repo_root", lambda: tmp_path)

    response = client.get(
        "/api/live/plan-view",
        params={"scope_mode": "world", "world_id": world.world_id},
    )

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "dmb_managed_world_plan_context_v2",
        "scope_mode": "world",
        "world_id": world.world_id,
        "campaign_id": None,
        "session": None,
        "authoritative": False,
        "generated_at": response.json()["generated_at"],
        "derived_from": ["managed_world_container"],
        "timeline": [],
    }


def test_managed_world_plan_context_v2_rejects_missing_world_id(client: TestClient) -> None:
    response = client.get("/api/live/plan-view", params={"scope_mode": "world"})
    assert response.status_code == 422


def test_plan_view_reopens_operator_world_from_separate_code_checkout(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.routes import live
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
        world_containers_path,
    )

    code_root = tmp_path / "clean-checkout"
    code_root.mkdir()
    operator_root = tmp_path / "operator-data"
    world = create_world_container(operator_root, name="Existing World")
    registry = world_containers_path(operator_root)
    original = registry.read_bytes()
    monkeypatch.setattr(live, "repo_root", lambda: code_root)
    monkeypatch.setenv(MANAGED_WORLD_DATA_ROOT_ENV, str(operator_root))

    scoped = client.get(
        "/api/live/plan-view",
        params={"scope_mode": "world", "world_id": world.world_id},
    )
    compatible = client.get(
        "/api/live/plan-view", params={"world_id": world.world_id},
    )
    unknown = client.get(
        "/api/live/plan-view",
        params={"scope_mode": "world", "world_id": "unknown-world"},
    )

    assert scoped.status_code == 200
    assert scoped.json()["schema_version"] == "dmb_managed_world_plan_context_v2"
    assert scoped.json()["world_id"] == world.world_id
    assert compatible.status_code == 200
    assert compatible.json()["schema_version"] == "dmb_managed_world_plan_context_v1"
    assert compatible.json()["world_id"] == world.world_id
    assert unknown.status_code == 404
    assert registry.read_bytes() == original
    assert not world_containers_path(code_root).exists()


def test_plan_view_invalid_explicit_world_root_fails_closed(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MANAGED_WORLD_DATA_ROOT_ENV, str(tmp_path / "missing"))

    response = client.get(
        "/api/live/plan-view",
        params={"scope_mode": "world", "world_id": "existing-world"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Managed World storage is unavailable."


def test_builder_uses_planning_beats_when_present(tmp_path: Path) -> None:
    import shutil

    from src.live_play.session_bootstrap import bootstrap_session_workspace
    from src.live_play.session_paths import live_sessions_root

    fixture = ROOT / "tests/fixtures/live_bootstrap/session_22_fresh_recap.md"
    out = live_sessions_root() / "_pytest" / tmp_path.name / "session_23"
    if out.exists():
        shutil.rmtree(out)
    bootstrap_session_workspace(
        recap_path=fixture,
        campaign_id="longmont-c2",
        session=23,
        output_dir=out,
        source_session=22,
    )
    try:
        packet, _, events, jobs = load_session(out)
        projection = build_session_plan_projection(packet, events, jobs, generated_at="2026-05-29T00:00:00Z")
        assert len(projection["timeline"]) >= 2
        assert projection["timeline"][0]["id"].startswith("beat-")
    finally:
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)


def test_get_plan_view_endpoint_is_read_only(client: TestClient, isolated_session: Path) -> None:
    events_before = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8")
    jobs_before = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8")

    response = client.get("/api/live/plan-view")
    assert response.status_code == 200

    events_after = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8")
    jobs_after = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8")
    assert events_after == events_before
    assert jobs_after == jobs_before
