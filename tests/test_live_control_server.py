from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

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
    assert body["retrieval_freshness"]["schema"] == "dmb_retrieval_freshness_decision_v1"
    assert body["retrieval_freshness"]["decision"] in {"fresh_retrieval", "insufficient_grounding"}
    assert "text_excerpt" not in json.dumps(body["retrieval_freshness"])
    assert "Hail dent" not in body["answer"]



def test_live_context_lookup_response_includes_source_line_evidence_snapshots(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace
    from apps.live_control_server.services import live_agent_loop

    citation_path = "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"

    def fake_context_lookup_turn(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            response={
                "schema": "dmb_live_query_response_v1",
                "query_id": "live-query-snapshot-test",
                "session": 22,
                "mode": "context_lookup",
                "status": "ok",
                "answer": "Grounded answer [e1].",
                "classification": {"latency_mode": "context_lookup", "event_type": "context_question"},
                "events_written": [],
                "jobs_queued": [],
                "next_suggestions": [],
                "diagnostics": [],
                "provenance": {},
                "citations": [{
                    "evidence_id": "e1",
                    "path": citation_path,
                    "line_start": 14,
                    "line_end": 14,
                    "source_role": "play_recap",
                    "authority": "canon_play",
                }],
                "context_packet": {
                    "admitted_evidence": [{"evidence_id": "e1", "text_excerpt": "source text must not persist"}],
                    "rejected_evidence": [],
                },
                "warnings": [],
                "mutations": [],
            },
            events_to_write=[],
            jobs_to_queue=[],
        )

    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", fake_context_lookup_turn)
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "live",
            "text": "What is Lysandra feeling at the gate?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_snapshots"]
    snapshot = body["evidence_snapshots"][0]
    assert snapshot["schema"] == "dmb_agent_evidence_snapshot_v1"
    assert snapshot["fingerprint_algorithm"] == "sha256:source-lines-v1"
    assert snapshot["path"] == citation_path
    assert "text_excerpt" not in json.dumps(body["evidence_snapshots"])
    assert "source text must not persist" not in json.dumps(body["evidence_snapshots"])

def test_query_can_route_through_hermes_backend(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import hermes_agent_runtime as hermes_agent_runtime_mod
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphAgentTurnResult,
        HermesGraphToolEvent,
    )

    class _Host:
        def execute(self, request, *, timeout_s=None):  # type: ignore[no-untyped-def]
            assert request.conversation_history is None
            assert request.session_id is None
            assert request.capability_policy is not None
            assert request.revision_pin == "rev:route"
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response="Tripod stands at the North Gate.",
                messages=[{"role": "assistant", "content": "ignored transcript"}],
                hermes_session_id="hermes-obs",
                tool_events=[
                    HermesGraphToolEvent(
                        tool_name="search_campaign_graph",
                        state="completion",
                        world_id="eldyrwild",
                        campaign_id="longmont-c2",
                        focus={"kind": "session", "sessionId": "session-21"},
                        admissibility="gm",
                        revision_pin="rev:route",
                        outcome="enough",
                        matched_node_ids=["threat:tripod-null-calf"],
                        source_anchor_ids=["anchor:route-1"],
                    )
                ],
                process_isolation="process_exclusive",
            )

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "ready",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "revision_id": "rev:route",
            "head_revision_id": "rev:route",
            "is_head": True,
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "query_text": "What happened at the end of session 22?",
            "matched_node_ids": ["threat:tripod-null-calf"],
            "nodes": [],
            "relationships": [],
            "attributes": [],
            "projection_truncated": False,
            "diagnostics": [],
            "warning_codes": [],
            "trust_boundary": {
                "graph_role": "structured_campaign_memory_and_navigation",
                "citation_authority": "corpus_source_evidence",
                "graph_citations_permitted": False,
            },
        },
    )
    monkeypatch.setattr(hermes_agent_runtime_mod, "get_hermes_graph_agent_host", lambda: _Host())
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "What happened at the end of session 22?",
            "world_graph_context": _GRAPH_NESTED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hermes_graph_agent"
    assert body["classification"]["intent"] == "hermes_graph_agent"
    assert body["status"] == "ok"
    assert body["grounding"]["state"] == "grounded"
    assert body["citations"] == [
        {
            "schema": "dmb_world_graph_anchor_citation_v1",
            "kind": "world_graph_anchor",
            "anchor_id": "anchor:route-1",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "revision_id": "rev:route",
        }
    ]
    assert body["context_packet"] is None
    assert body["hermes_session"] is not None
    assert body["hermes_session"]["sessionId"].startswith("hptr-")
    assert body["events_written"] == []
    assert body["jobs_queued"] == []
    assert body["agent_trace"]["runtime"] == "process_isolated"
    assert body["agent_trace"]["tool_events"][0]["source_anchor_ids"] == ["anchor:route-1"]
    assert "ignored transcript" not in json.dumps(body)
    assert (isolated_session / "event_log.jsonl").read_text(encoding="utf-8") == ""
    assert (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8") == ""


def test_query_hermes_cli_env_does_not_invoke_subprocess(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import hermes_agent_runtime as hermes_agent_runtime_mod
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphAgentTurnResult,
        HermesGraphToolEvent,
    )

    monkeypatch.setenv("DUNGEONMIND_LIVE_HERMES_MODE", "cli")

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "ready",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "revision_id": "rev:cli-blocked",
            "head_revision_id": "rev:cli-blocked",
            "is_head": True,
            "focus": {"kind": "none", "session_id": None},
            "admissibility": "gm",
            "query_text": "q",
            "matched_node_ids": [],
            "nodes": [],
            "relationships": [],
            "attributes": [],
            "projection_truncated": False,
            "diagnostics": [],
            "warning_codes": [],
            "trust_boundary": {
                "graph_role": "structured_campaign_memory_and_navigation",
                "citation_authority": "corpus_source_evidence",
                "graph_citations_permitted": False,
            },
        },
    )

    class _Host:
        def execute(self, request, *, timeout_s=None):  # type: ignore[no-untyped-def]
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response="host answer",
                messages=[],
                hermes_session_id="",
                tool_events=[
                    HermesGraphToolEvent(
                        tool_name="search_campaign_graph",
                        state="completion",
                        world_id="eldyrwild",
                        campaign_id="longmont-c2",
                        focus={"kind": "none", "sessionId": None},
                        admissibility="gm",
                        revision_pin="rev:cli-blocked",
                        outcome="enough",
                        source_anchor_ids=["anchor:cli-blocked"],
                    )
                ],
                process_isolation="process_exclusive",
            )

    monkeypatch.setattr(hermes_agent_runtime_mod, "get_hermes_graph_agent_host", lambda: _Host())
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "What happened at the end of session 22?",
            "world_graph_context": _GRAPH_NESTED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hermes_graph_agent"
    assert body["answer"] == "host answer"
    assert body["agent_trace"]["runtime"] == "process_isolated"
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
        "/api/live/citation-freshness",
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



def test_citation_freshness_line_range_current_changed_and_no_body(client: TestClient, isolated_session: Path) -> None:
    import hashlib

    path = "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    source = Path(path).read_text(encoding="utf-8").splitlines()[13]
    expected = hashlib.sha256(source.encode("utf-8")).hexdigest()

    response = client.post(
        "/api/live/citation-freshness",
        json={
            "path": path,
            "line_start": 14,
            "line_end": 14,
            "expected_fingerprint": expected,
            "fingerprint_algorithm": "sha256:source-lines-v1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "dmb_citation_freshness_v1"
    assert body["status"] == "current"
    assert body["current_fingerprint"] == expected
    assert "content" not in body
    assert "text_excerpt" not in json.dumps(body)
    assert "The group turns their focus" not in json.dumps(body)

    changed = client.post(
        "/api/live/citation-freshness",
        json={
            "path": path,
            "line_start": 14,
            "line_end": 14,
            "expected_fingerprint": "not-the-current-hash",
            "fingerprint_algorithm": "sha256:source-lines-v1",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "changed"
    assert (isolated_session / "event_log.jsonl").read_text(encoding="utf-8") == ""
    assert (isolated_session / "job_queue.jsonl").read_text(encoding="utf-8") == ""


def test_citation_freshness_missing_source_is_unavailable_without_absolute_path(client: TestClient) -> None:
    response = client.post("/api/live/citation-freshness", json={"path": "Docs/does-not-exist.md"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["path"] == "Docs/does-not-exist.md"
    assert str(Path.cwd()) not in json.dumps(body)


@pytest.mark.parametrize("unsafe_path", ["/etc/passwd", "../README.md", "corpus/../README.md", "README.md"])
def test_citation_freshness_rejects_unsafe_paths(client: TestClient, unsafe_path: str) -> None:
    response = client.post("/api/live/citation-freshness", json={"path": unsafe_path})

    assert response.status_code == 422


def test_citation_freshness_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post("/api/live/citation-freshness", json={"path": "evals/planner_slice/batch_eval.py"})

    assert response.status_code == 422

def test_retrieval_freshness_builder_states_are_lightweight() -> None:
    from apps.live_control_server.services.live_agent_loop import build_retrieval_freshness_decision

    packet = {
        "admitted_evidence": [{"text_excerpt": "secret excerpt", "path": "corpus/example.md"}],
        "rejected_evidence": [{"evidence": {"text_excerpt": "rejected excerpt"}}],
    }
    fresh = build_retrieval_freshness_decision(
        context_packet=packet,
        hermes_session_id=None,
        agent_thread_id="agent-thread-test",
    )
    assert fresh["schema"] == "dmb_retrieval_freshness_decision_v1"
    assert fresh["decision"] == "fresh_retrieval"
    assert fresh["used_fresh_retrieval"] is True
    assert fresh["used_thread_context"] is False
    assert fresh["admitted_evidence_count"] == 1
    assert fresh["rejected_evidence_count"] == 1
    serialized = json.dumps(fresh)
    assert "secret excerpt" not in serialized
    assert "rejected excerpt" not in serialized
    assert "prompt" not in serialized

    blended = build_retrieval_freshness_decision(
        context_packet=packet,
        hermes_session_id="hermes-session-test",
        agent_thread_id="agent-thread-test",
    )
    assert blended["decision"] == "blended"
    assert blended["used_thread_context"] is True

    thread_only = build_retrieval_freshness_decision(
        context_packet={"admitted_evidence": [], "rejected_evidence": []},
        hermes_session_id="hermes-session-test",
        agent_thread_id="agent-thread-test",
    )
    assert thread_only["decision"] == "thread_context"
    assert thread_only["warnings"]

    insufficient = build_retrieval_freshness_decision(
        context_packet={"admitted_evidence": [], "rejected_evidence": []},
        hermes_session_id=None,
        agent_thread_id="agent-thread-test",
    )
    assert insufficient["decision"] == "insufficient_grounding"
    assert insufficient["warnings"]


# --- PR008B: Agent World Graph query context ---

_GRAPH_NESTED = {
    "schema": "dmb_agent_world_graph_query_context_request_v1",
    "world_id": "eldyrwild",
    "campaign_id": "longmont-c2",
    "focus": {"kind": "session", "session_id": "session-21"},
    "admissibility": "gm",
    "revision_pin": None,
}


def _pr008b_init_world(tmp_path: Path) -> None:
    import graph_memory.kernel as kernel
    from graph_memory.contribution_bundles import load_contribution_bundle
    from graph_memory.kernel.world_initialization import initialize_world_from_contributions
    from graph_memory.kernel.world_initialization_models import (
        PLAN_SCHEMA,
        WorldInitializationApprovalAttestation,
        WorldInitializationContribution,
        WorldInitializationPlan,
    )

    bundle_path = Path(
        "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
    )
    bundle = load_contribution_bundle(bundle_path)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    ordered = [
        "contribution:82f23934d8eaca8a",
        "contribution:43782369bd717d32",
        "contribution:33d7cdb0ff623f28",
        "contribution:c086a0b72324ff16",
        "contribution:1227841724520c18",
        "contribution:022187fdefdf4557",
    ]
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id="eldyrwild",
        campaign_id="longmont-c2",
        focus_session_id="session-23",
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ordered
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id="eldyrwild-longmont-c2-initial-v1",
            bundle_digest=(
                "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
            ),
            approved_bundle_merge_sha="65ae001e0852d827ecd680200a965a576c705b1d",
        ),
    )
    initialize_world_from_contributions(
        tmp_path,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )


def test_live_query_world_graph_preflight_once_before_backend(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import agent_world_graph_query_context as adapter
    from apps.live_control_server.services import live_agent_loop
    from types import SimpleNamespace

    calls: list[str] = []

    def spy_resolve(nested, *, outer_text, outer_campaign_id, root=None, project_fn=None):
        calls.append(outer_text)
        return {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "ready",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "revision_id": "rev:test",
            "head_revision_id": "rev:test",
            "is_head": True,
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "query_text": outer_text,
            "matched_node_ids": ["threat:tripod-null-calf"],
            "nodes": [],
            "relationships": [],
            "attributes": [],
            "projection_truncated": False,
            "diagnostics": [],
            "warning_codes": [],
            "trust_boundary": {
                "graph_role": "structured_campaign_memory_and_navigation",
                "citation_authority": "corpus_source_evidence",
                "graph_citations_permitted": False,
            },
        }

    def fake_context_lookup_turn(**kwargs: object) -> SimpleNamespace:
        assert kwargs.get("world_graph_prompt_block")
        assert "WORLD GRAPH CONTEXT" in str(kwargs.get("world_graph_prompt_block"))
        return SimpleNamespace(
            response={
                "schema": "dmb_live_query_response_v1",
                "query_id": "live-query-wg",
                "session": 22,
                "mode": "context_lookup",
                "status": "ok",
                "answer": "Grounded [ev-1].",
                "classification": {
                    "latency_mode": "context_lookup",
                    "event_type": "context_question",
                },
                "events_written": [],
                "jobs_queued": [],
                "next_suggestions": [],
                "diagnostics": [],
                "provenance": {},
                "citations": [
                    {
                        "evidence_id": "ev-1",
                        "path": "corpus/example.md",
                        "line_start": 1,
                        "line_end": 1,
                        "source_role": "play_recap",
                        "authority": "canon_play",
                    }
                ],
                "context_packet": {"admitted_evidence": [], "rejected_evidence": []},
                "warnings": [],
                "mutations": [],
            },
            events_to_write=[],
            jobs_to_queue=[],
        )

    monkeypatch.setattr(adapter, "resolve_agent_world_graph_query_context", spy_resolve)
    monkeypatch.setattr(live_agent_loop, "resolve_agent_world_graph_query_context", spy_resolve)
    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", fake_context_lookup_turn)

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "live",
            "text": "What should I remember about the Tripod Null-Calf?",
            "world_graph_context": _GRAPH_NESTED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(calls) == 1
    assert body["world_graph_context"]["status"] == "ready"
    assert body["world_graph_context"]["matched_node_ids"] == ["threat:tripod-null-calf"]
    assert all(c.get("evidence_id", "").startswith("ev-") for c in body["citations"])


def test_live_and_hermes_receive_equivalent_graph_context(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import hermes_agent_runtime as hermes_agent_runtime_mod
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphAgentTurnResult,
        HermesGraphToolEvent,
    )
    from types import SimpleNamespace

    envelope = {
        "schema": "dmb_agent_world_graph_query_context_v1",
        "status": "ready",
        "world_id": "eldyrwild",
        "campaign_id": "longmont-c2",
        "revision_id": "rev:parity",
        "head_revision_id": "rev:parity",
        "is_head": True,
        "focus": {"kind": "session", "session_id": "session-21"},
        "admissibility": "gm",
        "query_text": "Tripod Null-Calf",
        "matched_node_ids": ["threat:tripod-null-calf"],
        "nodes": [
            {
                "node_id": "threat:tripod-null-calf",
                "label": "Tripod Null-Calf",
                "kind": "threat",
                "role": "antagonist",
                "summary": "gate pressure",
                "anchored_to_focus_session": False,
            }
        ],
        "relationships": [],
        "attributes": [],
        "projection_truncated": False,
        "diagnostics": [],
        "warning_codes": [],
        "trust_boundary": {
            "graph_role": "structured_campaign_memory_and_navigation",
            "citation_authority": "corpus_source_evidence",
            "graph_citations_permitted": False,
        },
    }

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: dict(envelope),
    )

    def fake_context_lookup_turn(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            response={
                "schema": "dmb_live_query_response_v1",
                "query_id": "live-parity",
                "session": 22,
                "mode": "context_lookup",
                "status": "ok",
                "answer": "live answer",
                "classification": {
                    "latency_mode": "context_lookup",
                    "event_type": "context_question",
                },
                "events_written": [],
                "jobs_queued": [],
                "next_suggestions": [],
                "diagnostics": [],
                "provenance": {},
                "citations": [],
                "context_packet": {"admitted_evidence": [], "rejected_evidence": []},
                "warnings": [],
                "mutations": [],
            },
            events_to_write=[],
            jobs_to_queue=[],
        )

    class _Host:
        def execute(self, request, *, timeout_s=None):  # type: ignore[no-untyped-def]
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response="hermes answer",
                messages=[],
                hermes_session_id="",
                tool_events=[
                    HermesGraphToolEvent(
                        tool_name="search_campaign_graph",
                        state="completion",
                        world_id="eldyrwild",
                        campaign_id="longmont-c2",
                        focus={"kind": "session", "sessionId": "session-21"},
                        admissibility="gm",
                        revision_pin="rev:parity",
                        outcome="enough",
                        source_anchor_ids=["anchor:parity"],
                    )
                ],
                process_isolation="process_exclusive",
            )

    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", fake_context_lookup_turn)
    monkeypatch.setattr(hermes_agent_runtime_mod, "get_hermes_graph_agent_host", lambda: _Host())
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)

    live_body = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "live",
            "text": "Tripod Null-Calf",
            "world_graph_context": _GRAPH_NESTED,
        },
    ).json()

    hermes_body = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Tripod Null-Calf",
            "world_graph_context": _GRAPH_NESTED,
        },
    ).json()

    assert live_body["world_graph_context"] == hermes_body["world_graph_context"]
    assert live_body["world_graph_context"]["revision_id"] == "rev:parity"
    assert hermes_body["mode"] == "hermes_graph_agent"


def test_hermes_graph_host_path_ignores_legacy_lookup(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PR354 Hermes path must not call dungeon_context_lookup."""
    from apps.live_control_server.services import hermes_agent_runtime as hermes_agent_runtime_mod
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphAgentTurnResult,
        HermesGraphToolEvent,
    )
    import integrations.hermes.plugins.dungeonbuddy as dungeonbuddy

    envelope = {
        "schema": "dmb_agent_world_graph_query_context_v1",
        "status": "ready",
        "world_id": "eldyrwild",
        "campaign_id": "longmont-c2",
        "revision_id": "rev:honest",
        "head_revision_id": "rev:honest",
        "is_head": True,
        "focus": {"kind": "session", "session_id": "session-21"},
        "admissibility": "gm",
        "query_text": "Tripod Null-Calf",
        "matched_node_ids": ["threat:tripod-null-calf"],
        "nodes": [],
        "relationships": [],
        "attributes": [],
        "projection_truncated": False,
        "diagnostics": [],
        "warning_codes": [],
        "trust_boundary": {
            "graph_role": "structured_campaign_memory_and_navigation",
            "citation_authority": "corpus_source_evidence",
            "graph_citations_permitted": False,
        },
    }
    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: dict(envelope),
    )

    def boom_lookup(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("dungeon_context_lookup must not be called")

    monkeypatch.setattr(dungeonbuddy, "handle_dungeon_context_lookup", boom_lookup)

    class _Host:
        def execute(self, request, *, timeout_s=None):  # type: ignore[no-untyped-def]
            assert request.revision_pin == "rev:honest"
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response="graph-grounded answer",
                messages=[],
                hermes_session_id="obs-only",
                tool_events=[
                    HermesGraphToolEvent(
                        tool_name="search_campaign_graph",
                        state="completion",
                        world_id="eldyrwild",
                        campaign_id="longmont-c2",
                        focus={"kind": "session", "sessionId": "session-21"},
                        admissibility="gm",
                        revision_pin="rev:honest",
                        outcome="enough",
                        source_anchor_ids=["anchor:honest"],
                    )
                ],
                process_isolation="process_exclusive",
            )

    monkeypatch.setattr(hermes_agent_runtime_mod, "get_hermes_graph_agent_host", lambda: _Host())
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Tripod Null-Calf",
            "world_graph_context": _GRAPH_NESTED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["world_graph_context"]["revision_id"] == "rev:honest"
    assert body["mode"] == "hermes_graph_agent"
    assert body["grounding"]["state"] == "grounded"
    assert body["hermes_session"] is not None
    assert body["hermes_session"]["sessionId"].startswith("hptr-")
    assert body["agent_trace"]["hermes_session_id"] == "obs-only"
    assert body["agent_trace"]["usage"]["available"] is False
    assert body["agent_trace"]["steps"] == []
    assert body["agent_trace"]["context_summary"] == {}
    assert body["agent_trace"]["artifact_refs"] == []
    assert body["citations"] == [
        {
            "schema": "dmb_world_graph_anchor_citation_v1",
            "kind": "world_graph_anchor",
            "anchor_id": "anchor:honest",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "revision_id": "rev:honest",
        }
    ]


def test_world_graph_unavailable_allows_corpus_path(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import live_agent_loop
    from types import SimpleNamespace

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "unavailable",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "revision_id": None,
            "head_revision_id": None,
            "is_head": None,
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "query_text": "Tripod?",
            "matched_node_ids": [],
            "nodes": [],
            "relationships": [],
            "attributes": [],
            "projection_truncated": False,
            "diagnostics": [],
            "warning_codes": ["world_graph_unavailable"],
            "trust_boundary": {
                "graph_role": "structured_campaign_memory_and_navigation",
                "citation_authority": "corpus_source_evidence",
                "graph_citations_permitted": False,
            },
        },
    )

    backend_called = {"live": False}

    def fake_context_lookup_turn(**kwargs: object) -> SimpleNamespace:
        backend_called["live"] = True
        return SimpleNamespace(
            response={
                "schema": "dmb_live_query_response_v1",
                "query_id": "live-unavail",
                "session": 22,
                "mode": "context_lookup",
                "status": "ok",
                "answer": "corpus-only answer",
                "classification": {
                    "latency_mode": "context_lookup",
                    "event_type": "context_question",
                },
                "events_written": [],
                "jobs_queued": [],
                "next_suggestions": [],
                "diagnostics": [],
                "provenance": {},
                "citations": [],
                "context_packet": {"admitted_evidence": [], "rejected_evidence": []},
                "warnings": [],
                "mutations": [],
            },
            events_to_write=[],
            jobs_to_queue=[],
        )

    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", fake_context_lookup_turn)
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Tripod?",
            "world_graph_context": _GRAPH_NESTED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert backend_called["live"] is True
    assert body["world_graph_context"]["status"] == "unavailable"
    assert "world_graph_unavailable" in body["warnings"]


def test_invalid_revision_pin_fails_without_backend(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextError,
    )
    from apps.live_control_server.services import live_agent_loop
    from graph_memory.projection.world_projection import WorldGraphProjectionDiagnostic

    backend_called = {"live": False}

    def boom(*args, **kwargs):
        raise AgentWorldGraphQueryContextError(
            "invalid pin",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="invalid_request",
                    message="invalid pin",
                    severity="error",
                )
            ],
        )

    def fake_context_lookup_turn(**kwargs: object):
        backend_called["live"] = True
        raise AssertionError("backend must not run")

    monkeypatch.setattr(live_agent_loop, "resolve_agent_world_graph_query_context", boom)
    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", fake_context_lookup_turn)

    nested = dict(_GRAPH_NESTED)
    nested["revision_pin"] = "not a safe pin!!!"
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Tripod?",
            "world_graph_context": nested,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_request"
    assert backend_called["live"] is False


def test_revision_not_found_fails_without_backend(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextError,
    )
    from apps.live_control_server.services import live_agent_loop
    from graph_memory.projection.world_projection import WorldGraphProjectionDiagnostic

    backend_called = {"live": False}

    def boom(*args, **kwargs):
        raise AgentWorldGraphQueryContextError(
            "missing",
            code="revision_not_found",
            status_code=404,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="revision_not_found",
                    message="missing",
                    severity="error",
                )
            ],
        )

    def fake_context_lookup_turn(**kwargs: object):
        backend_called["live"] = True
        raise AssertionError("backend must not run")

    monkeypatch.setattr(live_agent_loop, "resolve_agent_world_graph_query_context", boom)
    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", fake_context_lookup_turn)

    nested = dict(_GRAPH_NESTED)
    nested["revision_pin"] = "rev:" + ("a" * 32)
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "text": "Tripod?",
            "world_graph_context": nested,
        },
    )
    assert response.status_code == 404
    assert response.json()["code"] == "revision_not_found"
    assert backend_called["live"] is False


def test_hermes_cli_env_cannot_inject_graph_prompt_via_subprocess(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy CLI env is ignored; graph host owns Hermes after Phase 0 demolition."""
    from apps.live_control_server.services import hermes_agent_runtime as hermes_agent_runtime_mod
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphAgentTurnResult,
        HermesGraphToolEvent,
    )

    monkeypatch.setenv("DUNGEONMIND_LIVE_HERMES_MODE", "cli")
    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "ready",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "revision_id": "rev:cli",
            "head_revision_id": "rev:cli",
            "is_head": True,
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "query_text": "Tripod",
            "matched_node_ids": ["threat:tripod-null-calf"],
            "nodes": [],
            "relationships": [],
            "attributes": [],
            "projection_truncated": False,
            "diagnostics": [],
            "warning_codes": [],
            "trust_boundary": {
                "graph_role": "structured_campaign_memory_and_navigation",
                "citation_authority": "corpus_source_evidence",
                "graph_citations_permitted": False,
            },
        },
    )

    class _Host:
        def execute(self, request, *, timeout_s=None):  # type: ignore[no-untyped-def]
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response="host not cli",
                messages=[],
                hermes_session_id="",
                tool_events=[
                    HermesGraphToolEvent(
                        tool_name="search_campaign_graph",
                        state="completion",
                        world_id="eldyrwild",
                        campaign_id="longmont-c2",
                        focus={"kind": "session", "sessionId": "session-21"},
                        admissibility="gm",
                        revision_pin="rev:cli",
                        outcome="enough",
                        source_anchor_ids=["anchor:cli"],
                    )
                ],
                process_isolation="process_exclusive",
            )

    monkeypatch.setattr(hermes_agent_runtime_mod, "get_hermes_graph_agent_host", lambda: _Host())
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Tripod",
            "world_graph_context": _GRAPH_NESTED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hermes_graph_agent"
    assert body["answer"] == "host not cli"
    assert body["world_graph_context"]["revision_id"] == "rev:cli"
    assert "prompt_preview" not in body["agent_trace"]


def test_hermes_history_accepts_valid_wire_shape(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import hermes_agent_runtime as hermes_agent_runtime_mod
    from apps.live_control_server.services import live_agent_loop
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphAgentTurnResult,
        HermesGraphToolEvent,
    )

    captured: dict[str, Any] = {}

    class _Host:
        def execute(self, request, *, timeout_s=None):  # type: ignore[no-untyped-def]
            captured["history"] = request.conversation_history
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response="Follow-up grounded.",
                messages=[],
                hermes_session_id="hermes-obs",
                tool_events=[
                    HermesGraphToolEvent(
                        tool_name="search_campaign_graph",
                        state="completion",
                        world_id="eldyrwild",
                        campaign_id="longmont-c2",
                        focus={"kind": "session", "sessionId": "session-21"},
                        admissibility="gm",
                        revision_pin="rev:route",
                        outcome="enough",
                        source_anchor_ids=["anchor:route-2"],
                    )
                ],
                process_isolation="process_exclusive",
            )

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "ready",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "revision_id": "rev:route",
            "head_revision_id": "rev:route",
            "is_head": True,
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "query_text": "follow-up",
            "matched_node_ids": [],
            "nodes": [],
            "relationships": [],
            "attributes": [],
            "projection_truncated": False,
            "diagnostics": [],
            "warning_codes": [],
            "trust_boundary": {
                "graph_role": "structured_campaign_memory_and_navigation",
                "citation_authority": "corpus_source_evidence",
                "graph_citations_permitted": False,
            },
        },
    )
    monkeypatch.setattr(hermes_agent_runtime_mod, "get_hermes_graph_agent_host", lambda: _Host())
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)

    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "What is it connected to?",
            "world_graph_context": _GRAPH_NESTED,
            "conversation_history": [
                {
                    "role": "user",
                    "content": "What do we know about Tripod Null-Calf at the North Gate?",
                },
                {
                    "role": "assistant",
                    "content": "Tripod Null-Calf is a siege scout.",
                },
            ],
        },
    )
    assert response.status_code == 200
    assert captured["history"] == [
        {
            "role": "user",
            "content": "What do we know about Tripod Null-Calf at the North Gate?",
        },
        {"role": "assistant", "content": "Tripod Null-Calf is a siege scout."},
    ]


_TOO_MANY_HISTORY_MESSAGES = [
    item
    for i in range(7)
    for item in (
        {"role": "user", "content": f"q{i}"},
        {"role": "assistant", "content": f"a{i}"},
    )
]


@pytest.mark.parametrize(
    "history,expected_code",
    [
        ("not-a-list", "hermes_history_invalid"),
        ([{"role": "user", "content": "solo"}], "hermes_history_invalid"),
        (
            [
                {"role": "assistant", "content": "wrong order"},
                {"role": "user", "content": "second"},
            ],
            "hermes_history_invalid",
        ),
        (
            [
                {"role": "user", "content": "x", "trace": "HOSTILE_TRACE"},
                {"role": "assistant", "content": "y"},
            ],
            "hermes_history_invalid",
        ),
        (
            [
                {"role": "system", "content": "nope"},
                {"role": "assistant", "content": "y"},
            ],
            "hermes_history_invalid",
        ),
        (
            [
                {"role": "tool", "content": "nope"},
                {"role": "assistant", "content": "y"},
            ],
            "hermes_history_invalid",
        ),
        (
            [
                {"role": "user", "content": ""},
                {"role": "assistant", "content": "y"},
            ],
            "hermes_history_invalid",
        ),
        (
            [
                {"role": "user", "content": 12},
                {"role": "assistant", "content": "y"},
            ],
            "hermes_history_invalid",
        ),
        (
            [
                {"role": "user", "content": "x" * 4001},
                {"role": "assistant", "content": "y"},
            ],
            "hermes_history_invalid",
        ),
        (
            [
                {"role": "user", "content": "a" * 3000},
                {"role": "assistant", "content": "b" * 3000},
                {"role": "user", "content": "c" * 3000},
                {"role": "assistant", "content": "d" * 3000},
                {"role": "user", "content": "e" * 3000},
                {"role": "assistant", "content": "f" * 3000},
            ],
            "hermes_history_invalid",
        ),
        (_TOO_MANY_HISTORY_MESSAGES, "hermes_history_invalid"),
    ],
)
def test_hermes_history_invalid_returns_422_without_execution(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
    history: Any,
    expected_code: str,
) -> None:
    import apps.live_control_server.routes.live as live_routes

    monkeypatch.setattr(
        live_routes,
        "process_live_query",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("process_live_query must not run")
        ),
    )
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "follow-up",
            "world_graph_context": _GRAPH_NESTED,
            "conversation_history": history,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == expected_code
    assert "HOSTILE_TRACE" not in json.dumps(body)


@pytest.mark.parametrize("history", [None, []])
def test_hermes_null_or_empty_history_does_not_422_as_invalid(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
    history: Any,
) -> None:
    import apps.live_control_server.routes.live as live_routes

    captured: dict[str, Any] = {}

    def _capture(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured["history"] = kwargs.get("conversation_history")
        return {
            "schema": "dmb_live_query_response_v1",
            "answer": "ok",
            "status": "ok",
            "mode": "hermes_graph_agent",
            "classification": {
                "intent": "hermes_graph_agent",
                "latency_mode": "hermes_graph_agent",
                "event_type": "hermes_graph_agent",
            },
            "events_written": [],
            "jobs_queued": [],
            "next_suggestions": [],
            "diagnostics": {},
            "provenance": {"backend": "hermes", "runtime": "process_isolated"},
            "citations": [],
            "context_packet": None,
            "agent_thread_id": "t",
            "turn_id": "u",
        }

    monkeypatch.setattr(live_routes, "process_live_query", _capture)
    payload: dict[str, Any] = {
        "campaign_id": "longmont-c2",
        "session": 22,
        "mode": "live",
        "query_backend": "hermes",
        "text": "follow-up",
        "world_graph_context": _GRAPH_NESTED,
    }
    if history is not None:
        payload["conversation_history"] = history
    response = client.post("/api/live/query", json=payload)
    assert response.status_code == 200
    assert captured["history"] is None


def test_live_backend_rejects_non_empty_history(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import apps.live_control_server.routes.live as live_routes

    monkeypatch.setattr(
        live_routes,
        "process_live_query",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("process_live_query must not run")
        ),
    )
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "live",
            "text": "follow-up",
            "conversation_history": [
                {"role": "user", "content": "prior"},
                {"role": "assistant", "content": "answer"},
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "conversation_history_not_supported"


def test_live_backend_allows_null_or_empty_history(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import apps.live_control_server.routes.live as live_routes

    calls = {"n": 0}

    def _ok(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls["n"] += 1
        return {
            "schema": "dmb_live_query_response_v1",
            "answer": "live-ok",
            "status": "ok",
            "mode": "live",
            "classification": {
                "intent": "note",
                "latency_mode": "instant",
                "event_type": "note",
            },
            "events_written": [],
            "jobs_queued": [],
            "next_suggestions": [],
            "diagnostics": {},
            "provenance": {"backend": "live", "runtime": "in_process"},
            "citations": [],
            "context_packet": None,
            "agent_thread_id": "t",
            "turn_id": "u",
        }

    monkeypatch.setattr(live_routes, "process_live_query", _ok)
    for history in (None, []):
        payload: dict[str, Any] = {
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "live",
            "text": "note",
        }
        if history is not None:
            payload["conversation_history"] = history
        response = client.post("/api/live/query", json=payload)
        assert response.status_code == 200
    assert calls["n"] == 2


# --- CUTOVER R.3: live-agent query context on the direct read path ----------


def test_live_agent_query_context_executes_via_direct_dungeonmind_read(
    tmp_path, monkeypatch
):
    """The live-agent graph preflight dispatches to DungeonMind in cutover mode.

    ``resolve_agent_world_graph_query_context`` projects through the projection
    service with the production root; in ``dungeonmind`` authority mode that
    executes natively in DungeonMind. Kernel/hydration explosion stubs prove
    the legacy graph read machinery never runs.
    """
    import graph_memory.kernel as kernel

    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextRequest,
        resolve_agent_world_graph_query_context,
    )
    from graph_memory.world_supergraph import storage
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        CAMPAIGN_ONE,
        NOW,
        _FakeBundle,
        _payload,
        _receipt,
        _seed_sources,
    )
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        WORLD_ID as DIRECT_WORLD_ID,
    )

    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository

    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=DIRECT_WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:live-agent-r3"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        _receipt(DIRECT_WORLD_ID, published.revision_id),
    )
    services = direct.direct_services_from_bundle(bundle, DIRECT_WORLD_ID)

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()
    monkeypatch.setattr(
        direct, "direct_services_from_config", lambda world_id: services
    )

    def _explode(*_args, **_kwargs):
        raise AssertionError("legacy kernel must not run on the direct read path")

    monkeypatch.setattr(kernel, "project_world_graph_from_context", _explode)
    monkeypatch.setattr(kernel, "resolve_projection_read_context", _explode)
    monkeypatch.setattr(world_graph_authority, "route_read_request", _explode)
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)

    envelope = resolve_agent_world_graph_query_context(
        AgentWorldGraphQueryContextRequest(
            **{
                "schema": "dmb_agent_world_graph_query_context_request_v1",
                "world_id": DIRECT_WORLD_ID,
                "campaign_id": CAMPAIGN_ONE,
                "focus": {"kind": "none"},
                "admissibility": "gm",
            }
        ),
        outer_text="Where is the tavern?",
        outer_campaign_id=CAMPAIGN_ONE,
    )
    assert envelope["status"] == "ready"
    assert envelope["revision_id"] == published.revision_id
    assert envelope["is_head"] is True
