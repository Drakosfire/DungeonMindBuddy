from __future__ import annotations

import builtins
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.live_agent_loop import process_live_query
from src.live_play import live_query_context

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_23"
TEST_MANIFEST_PATH = "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"


@pytest.fixture
def isolated_session_23(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in (
        "live_packet.json",
        "surface_layout.json",
        "current_state.json",
        "recap.md",
    ):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session_23: Path) -> TestClient:
    return TestClient(create_app())


def test_context_lookup_returns_packet_with_admitted_and_rejected_evidence(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "context_lookup"
    assert body["answer"]
    assert body["mutations"] == []
    packet = body["context_packet"]
    assert packet
    assert packet["admitted_evidence"], "expected admitted evidence"
    assert isinstance(packet["rejected_evidence"], list)

    policy = body["provenance"].get("grounding_prompt_policy") or {}
    assert policy == {
        "uses_admitted_evidence": True,
        "forbids_rejected_support": True,
        "requires_evidence_id_citations": True,
        "read_only": True,
    }
    assert "grounded_prompt" not in body["provenance"]
    prompt = live_query_context.render_grounded_prompt(
        "What Session 22 outcomes matter for Session 23 prep?",
        packet,
    )
    assert "ADMITTED EVIDENCE" in prompt
    assert "REJECTED EVIDENCE" in prompt
    assert "Do not use rejected evidence as support." in prompt
    assert "Never claim write capability in this response path; it is read-only." in prompt


def test_context_lookup_citations_reference_admitted_evidence(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    packet = body["context_packet"]
    admitted_ids = {row.get("evidence_id") for row in packet["admitted_evidence"]}
    rejected_ids = {row.get("evidence", {}).get("evidence_id") for row in packet["rejected_evidence"]}
    citations = body.get("citations") or []
    assert citations, "expected at least one citation"
    for row in citations:
        evidence_id = row["evidence_id"]
        assert evidence_id in admitted_ids
        assert evidence_id not in rejected_ids
    assert "ingest_status" not in {row.get("source_role") for row in packet["admitted_evidence"]}
    assert "audit" not in {row.get("authority") for row in packet["admitted_evidence"]}


def test_ingest_question_surfaces_rejected_reason_codes(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "After ingesting Session 22 raw notes, what Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    packet = body["context_packet"]
    assert packet["rejected_evidence"]
    assert all("reason_code" in row for row in packet["rejected_evidence"])


def test_context_lookup_mutation_request_is_refused_read_only(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What should we prep next, and can you create a new Mireward location hub and write it?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "context_lookup"
    assert body["mutations"] == []
    assert "read-only" in body["answer"].lower()


def test_context_lookup_missing_manifest_is_truthful(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": "evals/c2_live_prep/benchmarks/does_not_exist.json",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "missing_context_manifest"
    assert body["context_packet"] is None
    assert "cannot ground this answer" in body["answer"].lower()


def test_context_lookup_does_not_read_gold_or_dogfood_trace(
    isolated_session_23: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_open = builtins.open

    def guarded_open(path, *args, **kwargs):
        lowered = str(path).lower()
        if "gold" in lowered:
            raise AssertionError("live query must not read gold")
        if "c2s23_dogfood_" in lowered or "c2s23_dogfood_planner_summary" in lowered:
            raise AssertionError("live query must not read dogfood traces")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)
    before_events = (isolated_session_23 / "event_log.jsonl").read_text(encoding="utf-8")
    before_jobs = (isolated_session_23 / "job_queue.jsonl").read_text(encoding="utf-8")
    body = process_live_query(
        "What Session 22 outcomes matter for Session 23 prep?",
        base=isolated_session_23,
        root=ROOT,
        request_manifest_path=TEST_MANIFEST_PATH,
    )
    assert body["mode"] == "context_lookup"
    assert (isolated_session_23 / "event_log.jsonl").read_text(encoding="utf-8") == before_events
    assert (isolated_session_23 / "job_queue.jsonl").read_text(encoding="utf-8") == before_jobs


def test_context_lookup_without_manifest_defaults_is_truthful_when_dogfood_off(
    isolated_session_23: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_C2S23_DOGFOOD_DEFAULTS", raising=False)
    packet_path = isolated_session_23 / "live_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    for key in ("planning_manifest_path", "active_manifest_path", "manifest_path"):
        packet.pop(key, None)
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    body = process_live_query(
        "What Session 22 outcomes matter for Session 23 prep?",
        base=isolated_session_23,
        root=ROOT,
    )
    assert body["mode"] == "context_lookup"
    assert body["status"] == "missing_context_manifest"
    assert body["context_packet"] is None


def test_context_lookup_stubbed_llm_path_emits_citations(
    isolated_session_23: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_llm_answer(*, question: str, packet: dict[str, object], root: Path) -> tuple[str | None, list[str]]:
        admitted = list(packet.get("admitted_evidence") or [])
        assert admitted, "expected admitted evidence for stubbed llm test"
        evidence_id = str(admitted[0].get("evidence_id") or "ev-unknown")
        return f"Stub grounded answer citing [{evidence_id}].", []

    monkeypatch.setattr(live_query_context, "_run_llm_grounded_answer", _fake_llm_answer)
    body = process_live_query(
        "What Session 22 outcomes matter for Session 23 prep?",
        base=isolated_session_23,
        root=ROOT,
        request_manifest_path=TEST_MANIFEST_PATH,
    )
    assert body["mode"] == "context_lookup"
    assert body["status"] == "ok"
    assert "stub grounded answer citing" in body["answer"].lower()
    assert body["citations"], "expected citations from stubbed llm answer"
    assert "llm_grounding_call_failed" not in (body.get("warnings") or [])
