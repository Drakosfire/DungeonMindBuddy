from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.schema_validation import LiveRowValidationError, validate_before_append
from apps.live_control_server.services.citation_source_reader import (
    CitationSourceRequest,
    MAX_SOURCE_BYTES,
    read_citation_source,
)
from apps.live_control_server.session_store import events_since
from src.live_play.live_store import append_jsonl, load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "evals/c2_live_prep/live/schemas"
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
COMMITTED_EVENT_LOG = SEED_SESSION / "event_log.jsonl"
COMMITTED_JOB_QUEUE = SEED_SESSION / "job_queue.jsonl"
COMMITTED_SURFACE_LAYOUT = SEED_SESSION / "surface_layout.json"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


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


def test_query_weather_7_persists_event_and_job(
    client: TestClient,
    isolated_session: Path,
) -> None:
    before_events = COMMITTED_EVENT_LOG.read_bytes()
    before_jobs = COMMITTED_JOB_QUEUE.read_bytes()

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Weather 7. Caelynn Nature 19.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "Hail dent" in body["answer"]
    assert body["classification"]["event_type"] == "roll_result"
    assert len(body["events_written"]) >= 1
    assert len(body["jobs_queued"]) >= 1

    events = (isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    jobs = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(events) == 1
    assert len(jobs) == 1

    event_validator = Draft202012Validator(
        _load_schema("live_event.schema.json"),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    job_validator = Draft202012Validator(
        _load_schema("live_job.schema.json"),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    event_row = json.loads(events[0])
    job_row = json.loads(jobs[0])
    event_validator.validate(event_row)
    job_validator.validate(job_row)
    assert event_row["derived_fields"]["skill_check"]["total"] == 19
    assert job_row["job_type"] == "benchmark_candidate"

    assert COMMITTED_EVENT_LOG.read_bytes() == before_events
    assert COMMITTED_JOB_QUEUE.read_bytes() == before_jobs


def test_get_state_and_events_after_query(client: TestClient) -> None:
    client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Weather 16.",
        },
    )
    state = client.get("/api/live/state").json()
    assert state["derived"] is True
    assert state["recent_event_count"] >= 1

    events_body = client.get("/api/live/events").json()
    assert len(events_body["events"]) >= 1
    assert events_body["events"][-1]["event_type"] == "roll_result"


def test_context_question_does_not_resolve_roll(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "What is Lysandra feeling at the gate?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["latency_mode"] == "context_lookup"
    assert body["agent_thread_id"].startswith("agent-thread-")
    assert body["turn_id"].startswith("agent-turn-")
    assert "Hail dent" not in body["answer"]


def test_query_can_route_through_hermes_backend(
    client: TestClient,
    isolated_session: Path,
) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "What happened at the end of session 22?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hermes_context_lookup"
    assert body["classification"]["intent"] == "hermes_context_lookup"
    assert body["provenance"]["backend"] == "hermes"
    assert body["diagnostics"]["hermes_tool"] == "dungeon_context_lookup"
    assert body["context_packet"]["schema"] == "dmb_enriched_planning_context_packet_v1"
    assert body["events_written"] == []
    assert body["jobs_queued"] == []
    trace = body.get("agent_trace")
    assert isinstance(trace, dict)
    assert trace["backend"] == "hermes"
    assert trace["runtime"] == "in_process"
    assert trace["mode"] == "hermes_context_lookup"
    assert trace["status"] == "ok"
    assert trace["elapsed_ms"] >= 0
    assert trace["context_summary"]["admitted_count"] >= 0
    assert trace["context_summary"]["context_payload_kind"] == "manifest_evidence_excerpts"
    assert trace["context_summary"]["total_excerpt_token_estimate"] >= 0
    assert trace["usage"]["available"] is False
    assert (isolated_session / "event_log.jsonl").read_text(encoding="utf-8") == ""
    assert (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8") == ""


def test_query_can_route_through_hermes_cli_backend(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import live_agent_loop

    monkeypatch.setenv(live_agent_loop.HERMES_CLI_MODE_ENV, "cli")
    monkeypatch.setattr(live_agent_loop.shutil, "which", lambda name: "/usr/bin/hermes")

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        assert args[0][0] == "/usr/bin/hermes"
        assert "--oneshot" in args[0]
        assert kwargs["cwd"] == ROOT
        assert kwargs["env"]["DUNGEONBUDDY_REPO"] == str(ROOT)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="Hermes loop answer")

    monkeypatch.setattr(live_agent_loop.subprocess, "run", fake_run)

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "What happened at the end of session 22?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hermes_cli_oneshot"
    assert body["answer"] == "Hermes loop answer"
    assert body["provenance"]["runtime"] == "cli"
    assert body["context_packet"]["schema"] == "dmb_enriched_planning_context_packet_v1"
    assert body["diagnostics"]["preflight_context_lookup"]["success"] is True
    trace = body.get("agent_trace")
    assert isinstance(trace, dict)
    assert trace["runtime"] == "cli"
    assert trace["backend"] == "hermes"
    assert trace["mode"] == "hermes_cli_oneshot"
    assert trace["status"] == "ok"
    assert trace["provider"] == "custom"
    assert trace["model"] == "gpt-5.4-mini"
    assert trace["elapsed_ms"] >= 0
    assert trace["command_summary"]
    assert "oneshot" in trace["command_summary"]
    assert "Retrieved evidence excerpts:" in trace["prompt_preview"]
    assert trace["context_summary"]["admitted_count"] >= 0
    assert trace["context_summary"]["context_payload_kind"] == "manifest_evidence_excerpts"
    assert trace["context_summary"]["total_excerpt_token_estimate"] >= 0
    assert trace["steps"][0]["name"] == "dungeon_context_lookup"
    assert trace["usage"]["available"] is False
    assert body["events_written"] == []
    assert body["jobs_queued"] == []
    assert (isolated_session / "event_log.jsonl").read_text(encoding="utf-8") == ""
    assert (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8") == ""


def test_invalid_campaign_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "wrong-campaign",
            "session": 22,
            "mode": "live",
            "text": "Weather 7.",
        },
    )
    assert response.status_code == 400


def test_get_state_recomputes_after_direct_event_append(
    client: TestClient,
    isolated_session: Path,
) -> None:
    stale_state = load_json(isolated_session / "current_state.json")
    stale_state["recent_event_count"] = 0
    write_json(isolated_session / "current_state.json", stale_state)

    direct_event = {
        "schema_version": "0.1.0",
        "id": "evt-test-direct-append",
        "created_at": "2026-05-25T12:00:00Z",
        "campaign_id": "longmont-c2",
        "session": 22,
        "session_clock": "test",
        "event_type": "state_note",
        "event_origin": "user_input",
        "latency_mode": "fast_live",
        "input_text": "direct append",
        "summary": "Direct JSONL append for state recompute test.",
        "derived_fields": {},
        "provenance": {
            "source_paths": [],
            "generated_by": "test_live_control_server",
            "notes": None,
        },
        "jobs_to_queue": [],
    }
    validate_before_append([direct_event], [])
    append_jsonl(isolated_session / "event_log.jsonl", direct_event)

    state = client.get("/api/live/state").json()
    assert state["recent_event_count"] >= 1


def test_get_events_unknown_since_returns_empty(client: TestClient) -> None:
    client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Weather 7.",
        },
    )
    body = client.get("/api/live/events", params={"since": "evt-does-not-exist"}).json()
    assert body["events"] == []


def test_events_since_unknown_cursor_returns_empty() -> None:
    events = [
        {"id": "evt-a"},
        {"id": "evt-b"},
    ]
    assert events_since(events, "evt-missing") == []


def test_validate_before_append_rejects_invalid_event() -> None:
    with pytest.raises(LiveRowValidationError):
        validate_before_append([{"id": "not-a-valid-event"}], [])


def test_get_jobs_after_canon_fact_input(client: TestClient) -> None:
    client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Lysandro is her father.",
        },
    )
    jobs_body = client.get("/api/live/jobs").json()
    job_types = {row["job_type"] for row in jobs_body["jobs"]}
    known_paths = [
        {"append_staging", "benchmark_candidate"},
        {"manual_review", "post_session_propagation"},
    ]
    assert any(expected <= job_types for expected in known_paths)


def test_get_surface_returns_catalog_layout_state(client: TestClient) -> None:
    body = client.get("/api/live/surface").json()
    assert "catalog" in body
    assert "layout" in body
    assert "state" in body
    catalog_ids = {row["module_id"] for row in body["catalog"]}
    assert "chat" in catalog_ids
    assert "record" in catalog_ids
    layout_ids = {row["module_id"] for row in body["layout"]["modules"] if row.get("enabled")}
    assert "chat" in layout_ids
    assert "record" in layout_ids
    assert body["state"]["derived"] is True


def test_put_surface_layout_persists_valid_layout(
    client: TestClient,
    isolated_session: Path,
) -> None:
    before_layout = COMMITTED_SURFACE_LAYOUT.read_bytes()
    layout = load_json(isolated_session / "surface_layout.json")
    layout["layout_version"] = layout.get("layout_version", 1) + 1

    response = client.put("/api/live/surface/layout", json=layout)
    assert response.status_code == 200
    saved = response.json()["layout"]
    assert saved["layout_version"] == layout["layout_version"]
    on_disk = load_json(isolated_session / "surface_layout.json")
    assert on_disk["layout_version"] == layout["layout_version"]
    assert COMMITTED_SURFACE_LAYOUT.read_bytes() == before_layout


def test_put_surface_layout_rejects_disabled_chat(client: TestClient) -> None:
    layout = client.get("/api/live/surface").json()["layout"]
    for row in layout["modules"]:
        if row["module_id"] == "chat":
            row["enabled"] = False
    response = client.put("/api/live/surface/layout", json=layout)
    assert response.status_code == 422


def test_put_surface_layout_rejects_unknown_module(client: TestClient) -> None:
    layout = client.get("/api/live/surface").json()["layout"]
    layout["modules"] = list(layout["modules"]) + [
        {
            "module_id": "bogus_module",
            "slot": "overlay",
            "order": 99,
            "enabled": True,
            "collapsed": True,
            "size": None,
            "config": {},
        }
    ]
    response = client.put("/api/live/surface/layout", json=layout)
    assert response.status_code == 422


def test_complete_job_marks_queued_job_complete(client: TestClient, isolated_session: Path) -> None:
    query = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Weather 7.",
        },
    )
    assert query.status_code == 200
    job_id = query.json()["jobs_queued"][0]

    complete = client.post(f"/api/live/jobs/{job_id}/complete")
    assert complete.status_code == 200
    job = complete.json()["job"]
    assert job["status"] == "complete"
    assert job["id"] == job_id

    jobs_on_disk = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(jobs_on_disk) == 1
    persisted = json.loads(jobs_on_disk[0])
    assert persisted["status"] == "complete"
    assert persisted["job_type"] == "benchmark_candidate"


def test_complete_job_returns_404_for_missing_id(client: TestClient) -> None:
    response = client.post("/api/live/jobs/job-does-not-exist/complete")
    assert response.status_code == 404


def test_resolve_roll_weather_16_without_append(
    client: TestClient,
    isolated_session: Path,
) -> None:
    events_before = len(
        (isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    jobs_before = len(
        (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )

    response = client.post("/api/live/resolve-roll", json={"command": "Weather 16"})
    assert response.status_code == 200
    body = response.json()
    assert body["table_id"] == "T-WX"
    assert body["roll"] == 16
    assert "Fixed-distance front" in body["row_text"]

    events_after = len(
        (isolated_session / "event_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    jobs_after = len(
        (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    assert events_after == events_before
    assert jobs_after == jobs_before


def test_rebuild_packet_queues_packet_rebuild_job(
    client: TestClient,
    isolated_session: Path,
) -> None:
    before_jobs = COMMITTED_JOB_QUEUE.read_bytes()
    response = client.post("/api/live/rebuild-packet")
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["job"]["job_type"] == "packet_rebuild"

    job_validator = Draft202012Validator(
        _load_schema("live_job.schema.json"),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    jobs = (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(jobs) == 1
    job_validator.validate(json.loads(jobs[0]))
    assert COMMITTED_JOB_QUEUE.read_bytes() == before_jobs


def test_openapi_contains_required_live_paths(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = set(spec["paths"])
    required = {
        "/api/live/query",
        "/api/live/state",
        "/api/live/events",
        "/api/live/jobs",
        "/api/live/jobs/{job_id}/complete",
        "/api/live/resolve-roll",
        "/api/live/rebuild-packet",
        "/api/live/surface",
        "/api/live/surface/layout",
        "/api/live/plan-view",
        "/api/live/source-bundle",
        "/api/live/artifact",
        "/api/live/capabilities",
        "/api/live/commands",
        "/api/live/recap-ingest",
        "/api/live/citation-source",
    }
    assert required <= paths


def test_citation_source_reads_current_source_without_events_or_jobs(
    client: TestClient,
    isolated_session: Path,
) -> None:
    response = client.post(
        "/api/live/citation-source",
        json={
            "path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
            "line_start": 14,
            "line_end": 14,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_citation_source_v1"
    assert body["path"].startswith("corpus/")
    assert not Path(body["path"]).is_absolute()
    assert "# Session 22 Recap" in body["content"]
    assert body["highlight"]["match_source"] == "line_range"
    assert "The group turns their focus" in body["highlight"]["text_excerpt"]
    assert body["diagnostics"] == ["read-only source lookup", "no events or jobs written"]
    assert (isolated_session / "event_log.jsonl").read_text(encoding="utf-8") == ""
    assert (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "/etc/passwd",
        "../README.md",
        "corpus/../README.md",
        "README.md",
    ],
)
def test_citation_source_rejects_unsafe_paths(client: TestClient, unsafe_path: str) -> None:
    response = client.post(
        "/api/live/citation-source",
        json={"path": unsafe_path},
    )

    assert response.status_code == 422


def test_citation_source_rejects_unsupported_file_type_under_allowed_root(client: TestClient) -> None:
    response = client.post(
        "/api/live/citation-source",
        json={"path": "evals/planner_slice/batch_eval.py"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "citation source file type is not supported"


def test_citation_source_missing_valid_path_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/live/citation-source",
        json={"path": "Docs/does-not-exist.md"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "citation source not found"


def test_citation_source_truncates_oversized_allowed_file(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    source = root / "Docs" / "oversized.txt"
    source.parent.mkdir(parents=True)
    source.write_text("a" * (MAX_SOURCE_BYTES + 1), encoding="utf-8")

    response = read_citation_source(
        root,
        CitationSourceRequest(path="Docs/oversized.txt"),
    )

    assert response.path == "Docs/oversized.txt"
    assert response.truncated is True
    assert len(response.content.encode("utf-8")) == MAX_SOURCE_BYTES
    assert f"source truncated to {MAX_SOURCE_BYTES} bytes" in response.diagnostics
